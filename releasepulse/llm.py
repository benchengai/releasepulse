"""Provider-neutral structured-output and embedding calls.

Every LLM step goes through `complete_json`: a system prompt, a user prompt and
a strict JSON schema in, the raw JSON text out, plus usage metadata (tokens,
latency, cost in USD). Callers validate the result and do all trust-critical
work deterministically. Models are named `provider:model`; only the OpenAI
Responses API is wired up here, and a new provider is one function.

Embeddings are cached on disk by model and text, so re-running a pipeline does
not pay for the same strings twice. The cost of a run is still computed from
the token counts of every text it embedded, cached or not, so runs compare
fairly.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import numpy as np

from .pricing import cost_usd

DEFAULT_MODEL = "openai:gpt-6-luna>openai:gpt-6.1-sol"
EMBEDDING_MODEL = "openai:text-embedding-3-small"
PROVIDERS = ("openai",)


class LLMError(RuntimeError):
    pass


def parse_model_spec(spec: str) -> tuple[str, str]:
    """'openai:gpt-6-luna' -> ('openai', 'gpt-6-luna'). A routed spec ('a>b') is split
    with parse_route first."""
    provider, sep, model = spec.partition(":")
    if not sep or provider not in PROVIDERS or not model:
        raise ValueError(f"model spec must be provider:model with provider in {PROVIDERS}: {spec!r}")
    return provider, model


def parse_route(spec: str) -> tuple[str, str]:
    """'a>b' extracts with model a and organises (merges features, words requirements)
    with model b; a plain spec uses one model for both."""
    extract_spec, _, organise_spec = spec.partition(">")
    return extract_spec, organise_spec or extract_spec


def load_dotenv(path: Path) -> None:
    """Read KEY=VALUE lines into the environment without overriding variables already set."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_client = None
_client_lock = threading.Lock()


def _openai_client():
    global _client
    with _client_lock:
        if _client is None:
            import openai

            _client = openai.OpenAI(max_retries=3, timeout=600)
        return _client


def _openai(system: str, prompt: str, schema: dict, name: str, model: str) -> tuple[str, dict]:
    response = _openai_client().responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text={"format": {"type": "json_schema", "name": name, "schema": schema, "strict": True}},
    )
    if response.status == "incomplete":
        raise LLMError(f"response incomplete: {response.incomplete_details}")
    for item in response.output:
        if item.type == "message":
            for part in item.content:
                if part.type == "refusal":
                    raise LLMError(f"model declined the request ({part.refusal})")
    u = response.usage
    return response.output_text, {
        "provider": "openai",
        "model": response.model,
        "request_id": response._request_id,
        "input_tokens": u.input_tokens,
        "cached_input_tokens": u.input_tokens_details.cached_tokens or 0,
        "output_tokens": u.output_tokens,
        "reasoning_tokens": u.output_tokens_details.reasoning_tokens or 0,
    }


def complete_json(system: str, prompt: str, schema: dict, name: str, spec: str = DEFAULT_MODEL) -> tuple[str, dict]:
    provider, model = parse_model_spec(spec)
    call = {"openai": _openai}[provider]
    started = time.perf_counter()
    text, meta = call(system, prompt, schema, name, model)
    meta["latency_s"] = round(time.perf_counter() - started, 2)
    meta["cost_usd"] = cost_usd(provider, meta["model"], meta["input_tokens"],
                                meta["cached_input_tokens"], meta["output_tokens"])
    return text, meta


class EmbeddingCache:
    """Vectors and token counts on disk, one JSON line per (model, text)."""

    def __init__(self, path: Path | None):
        self.path = path
        self.rows: dict[str, dict] = {}
        self.lock = threading.Lock()
        if path and path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self.rows[row["key"]] = row

    @staticmethod
    def key(model: str, text: str) -> str:
        return hashlib.sha256(f"{model}\n{text}".encode()).hexdigest()

    def get(self, model: str, text: str) -> dict | None:
        return self.rows.get(self.key(model, text))

    def put(self, model: str, text: str, vector: list[float], tokens: int) -> None:
        row = {"key": self.key(model, text), "model": model, "text": text, "tokens": tokens, "vector": vector}
        with self.lock:
            self.rows[row["key"]] = row
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")


def _count_tokens(texts: list[str]) -> list[int]:
    """Token count per text for cost accounting, from the API's own tokenizer when
    tiktoken is installed, otherwise the usual four-characters-per-token estimate."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return [len(enc.encode(t)) for t in texts]
    except ImportError:
        return [max(1, round(len(t) / 4)) for t in texts]


def embed(texts: list[str], spec: str = EMBEDDING_MODEL, cache: EmbeddingCache | None = None) -> tuple[np.ndarray, dict]:
    """Unit-normalised embeddings, one row per text, with usage metadata for the whole batch."""
    provider, model = parse_model_spec(spec)
    cache = cache or EmbeddingCache(None)
    missing = [t for t in dict.fromkeys(texts) if cache.get(model, t) is None]
    started = time.perf_counter()
    api_tokens = 0
    for i in range(0, len(missing), 512):
        chunk = missing[i:i + 512]
        response = _openai_client().embeddings.create(model=model, input=chunk)
        counts = _count_tokens(chunk)
        scale = response.usage.prompt_tokens / max(1, sum(counts))
        api_tokens += response.usage.prompt_tokens
        for text, item, n in zip(chunk, sorted(response.data, key=lambda d: d.index), counts):
            cache.put(model, text, item.embedding, max(1, round(n * scale)))
    rows = [cache.get(model, t) for t in texts]
    vectors = np.array([r["vector"] for r in rows], dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True).clip(min=1e-12)
    tokens = sum(cache.get(model, t)["tokens"] for t in dict.fromkeys(texts))
    meta = {
        "provider": provider, "model": model, "texts": len(set(texts)),
        "input_tokens": tokens, "cached_input_tokens": 0, "output_tokens": 0,
        "api_tokens": api_tokens, "from_cache": len(set(texts)) - len(missing),
        "latency_s": round(time.perf_counter() - started, 2),
    }
    meta["cost_usd"] = cost_usd(provider, model, tokens, 0, 0)
    return vectors, meta
