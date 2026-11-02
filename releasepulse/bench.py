"""Compare LLMs on one synthetic app, several runs each.

Each run is the whole pipeline (extract every item, cluster, count, flag,
word the candidate requirements), scored against the planted truth. Results
are reported as mean and range across runs. Finished runs are cached on
disk, so an interrupted bench resumes; a run whose extraction failed entirely
is recorded and counted, not retried. Embeddings are shared through one
cache, so every model's aspect names are embedded the same way.
"""

from __future__ import annotations

import json
import statistics
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .evaluate import oracle, score
from .llm import EmbeddingCache
from .pipeline import analyse, load_dataset


def slug(spec: str) -> str:
    return spec.replace(":", "_").replace("/", "_")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def run_row(analysis: dict, gold: dict, calls: list[dict]) -> dict:
    s = score(analysis, gold)
    llm = analysis["llm"]
    extract_calls = [c for c in calls if c.get("step") == "extract"]
    return {
        "ok": True,
        "mention_precision": s["mentions"]["precision"],
        "mention_strict_precision": s["mentions"]["strict_precision"],
        "mention_recall": s["mentions"]["recall"],
        "mention_f1": s["mentions"]["f1"],
        "item_feature_f1": s["item_features"]["f1"],
        "polarity_agreement": s["polarity_agreement"],
        "complaint_agreement": s["complaint_agreement"],
        "hard_recall": s["hard"]["recall"],
        "hard_polarity": s["hard"]["polarity_agreement"],
        "hard_feature": s["hard"]["feature_agreement"],
        "quote_validity": s["quote_validity"],
        "cue_validity": s["cue_validity"],
        "missing_items": s["missing_items"],
        "purity": s["clusters"]["purity"],
        "inverse_purity": s["clusters"]["inverse_purity"],
        "features_predicted": s["clusters"]["features_predicted"],
        "reg_precision": s["regressions"]["precision"],
        "reg_recall": s["regressions"]["recall"],
        "imp_precision": s["improvements"]["precision"],
        "imp_recall": s["improvements"]["recall"],
        "raw_precision": s["regressions_raw"]["precision"],
        "raw_recall": s["regressions_raw"]["recall"],
        "nodedupe_precision": s["regressions_without_dedupe"]["precision"],
        "traps_flagged": sum(t["flagged"] for t in s["traps"]),
        "traps_flagged_raw": sum(t["flagged_raw"] for t in s["traps"]),
        "top_praised_ok": float(s["top_praised_ok"]),
        "cost_usd": llm["cost_usd"],
        "latency_s": llm["latency_s"],
        "wall_s": llm["wall_s"],
        "call_latency_median_s": statistics.median([c["latency_s"] for c in extract_calls]) if extract_calls else None,
        "input_tokens": llm["input_tokens"],
        "output_tokens": llm["output_tokens"],
        "reasoning_tokens": llm["reasoning_tokens"],
        "regressions": {k: s["regressions"][k] for k in ("tp", "fp", "fn")},
        "improvements": {k: s["improvements"][k] for k in ("tp", "fp", "fn")},
        "raw": {k: s["regressions_raw"][k] for k in ("tp", "fp", "fn")},
    }


def run_once(dataset: dict, spec: str, out: Path, cache: EmbeddingCache, workers: int) -> dict:
    if (out / "row.json").exists():
        return _read(out / "row.json")
    analysis = analyse(dataset, spec, out, cache=cache, workers=workers)
    if analysis["extraction"]["aspects"] == 0:
        row = {"ok": False, "error": "no aspects extracted", "cost_usd": analysis["llm"]["cost_usd"],
               "latency_s": analysis["llm"]["latency_s"]}
    else:
        row = run_row(analysis, dataset["gold"], _read(out / "run.json")["calls"])
    _write(out / "row.json", row)
    return row


METRICS = ("mention_precision", "mention_strict_precision", "mention_recall", "mention_f1", "item_feature_f1",
           "polarity_agreement", "complaint_agreement", "hard_recall", "hard_polarity", "hard_feature",
           "quote_validity", "cue_validity", "missing_items",
           "purity", "inverse_purity", "features_predicted", "reg_precision", "reg_recall", "imp_precision",
           "imp_recall", "raw_precision", "raw_recall", "nodedupe_precision", "traps_flagged",
           "traps_flagged_raw", "top_praised_ok", "cost_usd", "latency_s", "wall_s", "call_latency_median_s",
           "input_tokens", "output_tokens", "reasoning_tokens")


def aggregate(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["ok"]]
    summary = {"runs": len(rows), "failed": len(rows) - len(ok)}
    for key in METRICS:
        values = [r[key] for r in (ok if key not in ("cost_usd", "latency_s") else rows) if r.get(key) is not None]
        if values:
            summary[key] = {"mean": statistics.fmean(values), "min": min(values), "max": max(values)}
    return summary


def bench(app_dir: Path, specs: list[str], runs: int, out_root: Path, cache_path: Path,
          parallel_runs: int = 3, workers: int = 4) -> dict:
    dataset = load_dataset(app_dir)
    if not dataset["gold"]:
        raise ValueError(f"{app_dir} has no gold.json")
    cache = EmbeddingCache(cache_path)
    jobs = [(spec, k) for spec in specs for k in range(1, runs + 1)]

    def job(spec_k):
        spec, k = spec_k
        row = run_once(dataset, spec, out_root / slug(spec) / f"run{k}", cache, workers)
        print(f"  {spec} run {k}: {'ok' if row['ok'] else 'FAILED'} "
              f"(${row.get('cost_usd') or 0:.3f}, {row.get('latency_s', 0):.0f}s)", flush=True)
        return spec_k, row

    with ThreadPoolExecutor(parallel_runs) as pool:
        scored = dict(pool.map(job, jobs))
    results = {"app": dataset["name"], "runs_per_model": runs, "models": {},
               "oracle": _oracle_summary(dataset)}
    for spec in specs:
        rows = [scored[(spec, k)] for k in range(1, runs + 1)]
        results["models"][spec] = {"runs": rows, "summary": aggregate(rows)}
    _write(out_root / "results.json", results)
    return results


def _oracle_summary(dataset: dict) -> dict:
    gold = dataset["gold"]
    o = oracle(gold, dataset)
    truth_r = {(g["release"], g["feature"]) for g in gold["regressions"]}
    truth_i = {(g["release"], g["feature"]) for g in gold["improvements"]}

    def prf(flags, kind, truth):
        pred = {(f["release"], f["feature"]) for f in flags if f["kind"] == kind}
        tp = len(pred & truth)
        return {"precision": tp / len(pred) if pred else 1.0, "recall": tp / len(truth) if truth else 1.0,
                "fp": sorted(pred - truth), "fn": sorted(truth - pred)}

    return {"regressions": prf(o["flags"], "regression", truth_r),
            "improvements": prf(o["flags"], "improvement", truth_i),
            "regressions_without_dedupe": prf(o["flags_without_dedupe"], "regression", truth_r),
            "regressions_raw": prf(o["raw_flags"], "regression", truth_r)}


def _cell(summary: dict, key: str, fmt: str = "{:.2f}") -> str:
    if key not in summary:
        return "–"
    v = summary[key]
    if fmt.format(v["min"]) == fmt.format(v["max"]):
        return fmt.format(v["mean"])
    return f"{fmt.format(v['mean'])} ({fmt.format(v['min'])}–{fmt.format(v['max'])})"


def render_markdown(results: dict) -> str:
    models = results["models"]
    o = results["oracle"]
    lines = [
        f"### {results['app']}: {results['runs_per_model']} runs per model",
        "",
        "Mean across successful runs, range in brackets. Cost and time are per full pipeline run "
        "(every item extracted, aspects embedded and clustered, requirements worded). Time is the sum of "
        "call latencies; wall time is with 4 extraction calls in flight.",
        "",
        "**Extraction and clustering**",
        "",
        "| Model | Mention F1 | Mention precision | Strict precision | Mention recall | Item×feature F1 "
        "| Polarity agr. | Hard: recall | Hard: polarity | Hard: feature | Quotes verified | Cues verified "
        "| Items not returned | Cluster purity | Inverse purity | Features found |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for spec, m in models.items():
        s = m["summary"]
        lines.append(
            f"| `{spec}` | {_cell(s, 'mention_f1')} | {_cell(s, 'mention_precision')} "
            f"| {_cell(s, 'mention_strict_precision')} | {_cell(s, 'mention_recall')} | {_cell(s, 'item_feature_f1')} "
            f"| {_cell(s, 'polarity_agreement')} | {_cell(s, 'hard_recall')} | {_cell(s, 'hard_polarity')} "
            f"| {_cell(s, 'hard_feature')} | {_cell(s, 'quote_validity')} | {_cell(s, 'cue_validity')} "
            f"| {_cell(s, 'missing_items', '{:.1f}')} | {_cell(s, 'purity')} | {_cell(s, 'inverse_purity')} "
            f"| {_cell(s, 'features_predicted', '{:.0f}')} |")
    lines += [
        "",
        "**Regression detection** (release and feature must both match the planted truth)",
        "",
        "| Model | Regression precision | Regression recall | Improvement precision | Improvement recall "
        "| Traps flagged (of 3) | Raw-count baseline precision | Raw-count recall | Raw-count traps flagged "
        "| Cost (USD) | Time (s) | Wall (s) | Failed runs |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for spec, m in models.items():
        s = m["summary"]
        lines.append(
            f"| `{spec}` | {_cell(s, 'reg_precision')} | {_cell(s, 'reg_recall')} | {_cell(s, 'imp_precision')} "
            f"| {_cell(s, 'imp_recall')} | {_cell(s, 'traps_flagged', '{:.1f}')} | {_cell(s, 'raw_precision')} "
            f"| {_cell(s, 'raw_recall')} | {_cell(s, 'traps_flagged_raw', '{:.1f}')} "
            f"| {_cell(s, 'cost_usd', '{:.3f}')} | {_cell(s, 'latency_s', '{:.0f}')} | {_cell(s, 'wall_s', '{:.0f}')} "
            f"| {s['failed']} of {s['runs']} |")
    lines += [
        "",
        f"Oracle (planted labels into the same detector): regression precision "
        f"{o['regressions']['precision']:.2f}, recall {o['regressions']['recall']:.2f}; improvement precision "
        f"{o['improvements']['precision']:.2f}, recall {o['improvements']['recall']:.2f}. Without de-duplication: "
        f"regression precision {o['regressions_without_dedupe']['precision']:.2f}. Raw-count rule: precision "
        f"{o['regressions_raw']['precision']:.2f}, recall {o['regressions_raw']['recall']:.2f} "
        f"(false alarms: {', '.join(f'{r} {f}' for r, f in o['regressions_raw']['fp']) or 'none'}).",
    ]
    errors = [(spec, k, r) for spec, m in models.items() for k, r in enumerate(m["runs"], 1)
              if r["ok"] and (r["regressions"]["fp"] or r["regressions"]["fn"])]
    if errors:
        lines += ["", "Regression errors by run:", ""]
        for spec, k, r in errors:
            fp = ", ".join(f"{a} {b}" for a, b in r["regressions"]["fp"]) or "none"
            fn = ", ".join(f"{a} {b}" for a, b in r["regressions"]["fn"]) or "none"
            lines.append(f"- `{spec}` run {k}: false alarms {fp}; missed {fn}")
    return "\n".join(lines) + "\n"
