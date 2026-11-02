"""Extract the features each feedback item comments on, with an LLM, then verify.

Items go to the model in batches. For each item it proposes aspects (a short
feature name), a polarity, a quote and the complaint or praise cues, all as
strict JSON. Everything that has to be trustworthy is done deterministically
afterwards: every quote and cue is checked against the item text, and aspects
whose quote is not in the item are dropped and recorded. Item ids in the
schema are restricted to the ids in the batch, so the model cannot attach an
aspect to an item it was not shown.

The output describes what is said about the product. The prompt tells the
model not to describe the writer's emotions, and nothing downstream scores a
person.
"""

from __future__ import annotations

import copy
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from .llm import LLMError, complete_json
from .verify import locate

BATCH_SIZE = 20
MAX_CUES = 3

SYSTEM = """You analyse user feedback about one software product: app-store reviews and \
issue tickets. For each feedback item, list the product features or quality aspects it \
comments on.

Rules:
- An aspect is a specific feature or quality of the product, for example "login", "sync", \
"search", "dark mode", "price". Name it with a short, generic, lowercase noun phrase of one \
to three words. Name the feature, not the problem: "login", not "login loop"; "reminders", \
not "late reminders".
- Name features at the level a product team would track them, and use the same name each \
time the feature comes up: the screen or capability ("editor", "notifications"), not a \
detail of it ("font size", "bullet points", "snooze button").
- One entry per aspect per item. If an item says several things about the same aspect, \
combine them into one entry.
- polarity: "negative" for a complaint, bug or regression; "positive" for praise; "mixed" \
when the item both praises and criticises the same aspect; "neutral" for a feature request \
or question without a judgement.
- quote: copy the words about this aspect verbatim from the item: at least three words, or \
the whole item if it is shorter. Quotes are checked automatically against the item text, and \
aspects whose quote does not match are discarded.
- cues: up to three short phrases copied verbatim from the item that signal the complaint \
or praise, for example "keeps crashing", "love", "too slow". Leave the list empty for \
neutral aspects.
- Overall verdicts with no specific feature ("great app", "used to be better"), star \
ratings, greetings, off-topic text and spam have no aspects: return an empty aspect list \
for such items.
- Return every item you are given, in the same order, even when its aspect list is empty.
- Describe what is said about the product. Do not describe or judge the writer's emotions \
or personality."""

POLARITIES = ("negative", "positive", "mixed", "neutral")

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item_id", "aspects"],
                "properties": {
                    "item_id": {"type": "string"},
                    "aspects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["aspect", "polarity", "quote", "cues"],
                            "properties": {
                                "aspect": {"type": "string"},
                                "polarity": {"type": "string", "enum": list(POLARITIES)},
                                "quote": {"type": "string"},
                                "cues": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                },
            },
        },
    },
}


class Aspect(BaseModel):
    aspect: str
    polarity: Literal["negative", "positive", "mixed", "neutral"]
    quote: str
    cues: list[str]


class ItemAspects(BaseModel):
    item_id: str
    aspects: list[Aspect]


class Extraction(BaseModel):
    items: list[ItemAspects]


def schema_for(item_ids: list[str]) -> dict:
    schema = copy.deepcopy(SCHEMA)
    schema["properties"]["items"]["items"]["properties"]["item_id"]["enum"] = item_ids
    return schema


def render_batch(items: list[dict], product: str | None = None) -> str:
    lines = [f"Product: {product}", ""] if product else []
    lines.append("Feedback items:")
    for it in items:
        lines.append(f"[{it['id']} | {it['source']}] {it['text']}")
    return "\n".join(lines)


def normalise_label(label: str) -> str:
    return " ".join(label.lower().replace("_", " ").replace("-", " ").strip(" .,:;!?\"'").split())


def call_batch(items: list[dict], spec: str, product: str | None = None) -> tuple[Extraction, dict]:
    text, meta = complete_json(SYSTEM, render_batch(items, product), schema_for([it["id"] for it in items]),
                               "feedback_aspects", spec)
    return Extraction.model_validate_json(text), meta


def verify_batch(items: list[dict], extraction: Extraction) -> dict:
    """Verified aspects, rejected ones with the reason, and items the model did not return."""
    by_id = {it["id"]: it for it in items}
    aspects, rejected, seen = [], [], set()
    for entry in extraction.items:
        item = by_id.get(entry.item_id)
        if item is None or entry.item_id in seen:
            rejected += [{"item_id": entry.item_id, **a.model_dump(), "reason": "unknown or repeated item"}
                         for a in entry.aspects]
            continue
        seen.add(entry.item_id)
        for a in entry.aspects:
            label = normalise_label(a.aspect)
            span = locate(a.quote, item["text"])
            if not label or span is None:
                rejected.append({"item_id": item["id"], **a.model_dump(),
                                 "reason": "empty aspect name" if not label else "quote not found in item"})
                continue
            cues = [c for c in a.cues[:MAX_CUES] if locate(c, item["text"])]
            aspects.append({
                "item_id": item["id"], "aspect": label, "polarity": a.polarity, "quote": a.quote,
                "span": list(span), "cues": cues,
                "dropped_cues": [c for c in a.cues if c not in cues],
            })
    return {"aspects": aspects, "rejected": rejected, "missing": [i for i in by_id if i not in seen]}


def _batch_key(items: list[dict], spec: str, product: str | None) -> str:
    payload = json.dumps([spec, product, SYSTEM, [(it["id"], it["text"], it["source"]) for it in items]])
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def extract_items(items: list[dict], spec: str, cache_dir: Path, product: str | None = None,
                  workers: int = 4, batch_size: int = BATCH_SIZE) -> dict:
    """Run every batch (cached on disk, so an interrupted run resumes), then retry
    items the model left out once, in a batch of their own."""
    cache_dir.mkdir(parents=True, exist_ok=True)

    def run(batch: list[dict], name: str) -> dict:
        path = cache_dir / f"{name}.json"
        if path.exists():
            cached = json.loads(path.read_text(encoding="utf-8"))
            if cached["key"] == _batch_key(batch, spec, product):
                return cached
        try:
            extraction, meta = call_batch(batch, spec, product)
            result = {"ok": True, **verify_batch(batch, extraction), "raw": extraction.model_dump()}
        except (LLMError, ValidationError, json.JSONDecodeError) as e:
            meta = {"error": str(e)[:500], "latency_s": 0.0, "cost_usd": 0.0, "input_tokens": 0,
                    "cached_input_tokens": 0, "output_tokens": 0}
            result = {"ok": False, "aspects": [], "rejected": [], "missing": [it["id"] for it in batch]}
        out = {"key": _batch_key(batch, spec, product), "items": [it["id"] for it in batch], "llm": meta, **result}
        path.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        return out

    batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(lambda kb: run(kb[1], f"batch_{kb[0]:03d}"), enumerate(batches)))
    missing = [i for r in results for i in r["missing"]]
    if missing:
        by_id = {it["id"]: it for it in items}
        retry = [by_id[i] for i in missing]
        retried = [run(retry[i:i + batch_size], f"retry_{i // batch_size:03d}")
                   for i in range(0, len(retry), batch_size)]
        results += retried
        missing = [i for r in retried for i in r["missing"]]
    return {
        "aspects": [a for r in results for a in r["aspects"]],
        "rejected": [x for r in results for x in r["rejected"]],
        "missing": missing,
        "calls": [{"step": "extract", "batch": r["items"][0], "items": len(r["items"]), "ok": r["ok"], **r["llm"]}
                  for r in results],
    }
