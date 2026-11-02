"""One full analysis: feedback CSV in, analysis.json out.

    ingest -> extract (LLM, verified) -> cluster (embeddings) -> merge and
    name features (LLM, validated) -> per-release counts -> regression and
    improvement flags -> prioritisation tables -> candidate requirements
    (LLM wording only)

Every LLM and embedding call is logged with tokens, latency and cost. The
extraction batches and the wording call are cached in the run folder, so a
re-run resumes instead of paying again.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from . import normalise as norm
from . import requirements as req
from .cluster import THRESHOLD, cluster_aspects
from .extract import extract_items
from .ingest import prepare
from .llm import EMBEDDING_MODEL, EmbeddingCache, LLMError, parse_route
from .prioritise import all_tables
from .trends import CLASSES, MIN_COUNT, RAW_MIN_INCREASE, RAW_MIN_RATIO, build_counts, detect, detect_raw, \
    quotes_for, series

SYNTHETIC_NOTICE = "Synthetic data: a fictional app and fictional feedback, generated for evaluation."


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def load_dataset(path: Path, releases: Path | None = None, product: str | None = None) -> dict:
    """A folder with feedback.csv (and optionally releases.csv and gold.json), or a CSV file."""
    if path.is_dir():
        items_csv = path / "feedback.csv"
        releases = releases or (path / "releases.csv" if (path / "releases.csv").exists() else None)
        gold = _read(path / "gold.json") if (path / "gold.json").exists() else None
    else:
        items_csv, gold = path, None
    app = (gold or {}).get("app") or {"id": path.stem if not path.is_dir() else path.name, "name": path.stem}
    return {"name": app["id"], "app": app, "items_csv": items_csv, "releases_csv": releases, "gold": gold,
            "product": product or app.get("product"), "synthetic": bool(gold and "notice" in gold)}


def _totals(calls: list[dict]) -> dict:
    costs = [c.get("cost_usd") for c in calls]
    return {
        "calls": len(calls),
        "input_tokens": sum(c.get("input_tokens", 0) for c in calls),
        "output_tokens": sum(c.get("output_tokens", 0) for c in calls),
        "reasoning_tokens": sum(c.get("reasoning_tokens", 0) for c in calls),
        "latency_s": round(sum(c.get("latency_s", 0.0) for c in calls), 2),
        "cost_usd": None if any(x is None for x in costs) else sum(costs),
    }


def analyse(dataset: dict, spec: str, out: Path, threshold: float = THRESHOLD, cache: EmbeddingCache | None = None,
            workers: int = 4, export_top: int = req.TOP, word_requirements: bool = True,
            normalise_features: bool = True, extract_dir: Path | None = None) -> dict:
    """`extract_dir` reads (and fills) extraction batches from another run's folder,
    so later steps can be compared on identical extraction outputs."""
    started = time.perf_counter()
    extract_spec, organise_spec = parse_route(spec)
    prepared = prepare(dataset["items_csv"], dataset["releases_csv"])
    to_extract = [it for it in prepared["items"] if it["release"] and not it["duplicate_of"]]
    ex = extract_items(to_extract, extract_spec, extract_dir or out / "extract", dataset["product"], workers)
    cl = cluster_aspects(ex["aspects"], threshold, cache)
    calls = ex["calls"] + ([cl["embedding"]] if cl["embedding"] else [])
    if normalise_features and cl["features"]:
        cl, meta = norm.normalise(cl, ex["aspects"], organise_spec, dataset["product"], _normalise_cache(out))
        calls.append({"step": "normalise", **meta})
        _write(out / "normalise_llm.json", {"system": norm.SYSTEM, "prompt": cl["normalisation"]["prompt"],
                                            "grouping": cl["normalisation"]["grouping"], "llm": meta})
    _write(out / "aspects.json", {"aspects": ex["aspects"], "rejected": ex["rejected"], "missing": ex["missing"]})
    analysis = assemble(dataset, prepared, ex, cl, spec, calls, out if word_requirements else None, export_top,
                        organise_spec)
    analysis["llm"]["wall_s"] = round(time.perf_counter() - started, 1)
    _write(out / "analysis.json", analysis)
    _write(out / "run.json", {"spec": spec, "ok": len(ex["missing"]) < len(to_extract), "calls": calls,
                              "totals": analysis["llm"]})
    return analysis


def _normalise_cache(out: Path):
    def lookup(prompt: str):
        path = out / "normalise_llm.json"
        if path.exists() and _read(path)["prompt"] == prompt and _read(path)["system"] == norm.SYSTEM:
            saved = _read(path)
            return norm.Grouping.model_validate(saved["grouping"]), saved["llm"]
        return None
    return lookup


def _word(issues: list[dict], tbl: dict, spec: str, dataset: dict, cache_dir: Path) -> tuple:
    cached = cache_dir / "requirements_llm.json"
    key = {"issues": [r["feature"] for r in issues], "prompt": req.render_prompt(issues, tbl, dataset["product"]),
           "system": req.SYSTEM}
    if cached.exists() and {k: _read(cached).get(k) for k in key} == key:
        saved = _read(cached)
        return req.Wording.model_validate(saved["wording"]), saved["llm"]
    if not issues:
        return None, None
    wording, meta = req.word(issues, tbl, spec, dataset["product"])
    _write(cached, {**key, "wording": wording.model_dump(), "llm": meta})
    return wording, meta


def assemble(dataset: dict, prepared: dict, ex: dict, cl: dict, spec: str, calls: list[dict],
             word_in: Path | None, export_top: int = req.TOP, word_spec: str | None = None) -> dict:
    """Everything after extraction and clustering. `word_in` is the run folder for the
    requirement-wording call; None skips the call and exports nothing."""
    items, releases = prepared["items"], prepared["releases"]
    items_by_id = {it["id"]: it for it in items}
    aspects = ex["aspects"]
    counts = build_counts(aspects, items, releases)
    raw_counts = build_counts(aspects, items, releases, include_duplicates=True)
    flags = detect(counts)
    by_item = defaultdict(list)
    for a in aspects:
        by_item[a["item_id"]].append(a)
    priority = all_tables(counts, raw_counts, cl["features"], flags, by_item, items_by_id)

    features = []
    for f in cl["features"]:
        per = counts["features"].get(f["id"], {})
        features.append({**f, "series": series(counts, f["id"]),
                         "quotes": {v: {c: quotes_for(f["id"], per[v][c], by_item, items_by_id, c)
                                        for c in CLASSES} for v in counts["releases"]} if per else {}})

    register, word_error = None, None
    if word_in is not None:
        tbl = priority["tables"][str(priority["default"])]
        issues = req.top_issues(tbl, export_top)
        try:
            wording, meta = _word(issues, tbl, word_spec or spec, dataset, word_in)
            if meta:
                calls.append({"step": "word_requirements", **meta})
            register = req.to_register(issues, wording, tbl, dataset["name"], meta)
        except (LLMError, ValidationError, json.JSONDecodeError) as e:
            word_error = str(e)[:500]

    sent = sum(1 for it in items if it["release"] and not it["duplicate_of"])
    verified = len(aspects)
    bad_quotes = sum(1 for r in ex["rejected"] if r["reason"] == "quote not found in item")
    cues_kept = sum(len(a["cues"]) for a in aspects)
    cues_dropped = sum(len(a["dropped_cues"]) for a in aspects)
    return {
        "notice": SYNTHETIC_NOTICE if dataset["synthetic"] else None,
        "app": dataset["app"],
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": spec,
        "embedding_model": EMBEDDING_MODEL,
        "settings": {"cluster_threshold": cl["threshold"], "normalised": "normalisation" in cl,
                     "min_count": MIN_COUNT, "raw_min_increase": RAW_MIN_INCREASE,
                     "raw_min_ratio": RAW_MIN_RATIO, "export_top": export_top},
        "normalisation": {k: v for k, v in cl.get("normalisation", {}).items() if k != "prompt"} or None,
        "embedding_clusters": cl.get("embedding_clusters"),
        "releases": releases,
        "items": {it["id"]: {k: it[k] for k in ("date", "version", "source", "rating", "release", "assigned_by",
                                                 "duplicate_of", "text")} for it in items},
        "skipped": prepared["skipped"],
        "unassigned": prepared["unassigned"],
        "features": features,
        "aspects": aspects,
        "counts": counts,
        "flags": flags,
        "flags_without_dedupe": detect(raw_counts),
        "raw_flags": detect_raw(raw_counts),
        "priority": priority,
        "requirements": register,
        "requirements_error": word_error,
        "extraction": {
            "items_sent": sent, "aspects": verified, "rejected": len(ex["rejected"]),
            "missing_items": ex["missing"],
            "quote_validity": verified / (verified + bad_quotes) if verified + bad_quotes else None,
            "cue_validity": cues_kept / (cues_kept + cues_dropped) if cues_kept + cues_dropped else None,
        },
        "llm": {**_totals(calls), "wall_s": None},
    }
