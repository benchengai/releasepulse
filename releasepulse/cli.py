"""Command-line entry point.

    releasepulse synth                                     # regenerate the synthetic sets
    releasepulse run data/synthetic/tallynote -m openai:gpt-6-luna
    releasepulse eval runs/tallynote/analysis.json data/synthetic/tallynote/gold.json
    releasepulse bench data/synthetic/kestrel -m openai:gpt-6-luna openai:gpt-6.1-sol --runs 3
    releasepulse web-export runs/tallynote/analysis.json -o web/public/data/tallynote.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .llm import DEFAULT_MODEL, EmbeddingCache, load_dotenv

RUNS_DIR = Path("runs")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
EMBEDDING_CACHE = RUNS_DIR / "cache" / "embeddings.jsonl"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict, indent: int | None = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=indent, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {path}")


def _pct(x: float) -> str:
    return f"{100 * x:4.1f}%"


def print_summary(a: dict) -> None:
    if a["notice"]:
        print(a["notice"])
    print(f"{a['app'].get('name', a['app']['id'])}: {len(a['items'])} items, {len(a['releases'])} releases, "
          f"{a['extraction']['aspects']} verified aspects in {len(a['features'])} features")
    for f in a["flags"]:
        arrow = "up" if f["kind"] == "regression" else "down"
        name = next(x["name"] for x in a["features"] if x["id"] == f["feature"])
        print(f"  {f['kind']:<11} {f['release']:>5}  {name:<22} complaints {arrow} "
              f"{_pct(f['previous_rate'])} -> {_pct(f['rate'])}  (difference 95% CI {_pct(f['low'])} to {_pct(f['high'])})")
    tbl = a["priority"]["tables"][str(a["priority"]["default"])]
    print(f"\nPriority, releases {', '.join(tbl['window'])} ({tbl['volume']} items), ranked by the lower 95% bound "
          f"of the complaint rate:")
    print(f"  {'#':>2}  {'feature':<22} {'complaints':>10}  {'rate':>6}  {'95% CI':<15} {'raw rank':>8}  status")
    for r in tbl["rows"][:10]:
        c = r["complaints"]
        print(f"  {r['rank']:>2}  {r['name'][:22]:<22} {c['count']:>4} / {c['n']:<4}  {_pct(c['rate'])}  "
              f"{_pct(c['low'])}-{_pct(c['high'])}  {r['raw_rank']:>8}  {r['status']}"
              + (f" since {r['since']}" if r["since"] else ""))
    llm = a["llm"]
    cost = f"${llm['cost_usd']:.4f}" if llm["cost_usd"] is not None else "unknown"
    print(f"\n{llm['calls']} calls, {llm['input_tokens']} input / {llm['output_tokens']} output tokens, "
          f"cost {cost}, {llm['wall_s']}s")


def web_payload(a: dict, results: dict | None = None) -> dict:
    """What the static demo needs: everything except per-call logs."""
    keep = ("notice", "app", "generated", "model", "embedding_model", "settings", "releases", "items", "features",
            "flags", "flags_without_dedupe", "raw_flags", "priority", "requirements", "extraction", "llm")
    out = {k: a[k] for k in keep}
    out["aspects"] = [{k: x[k] for k in ("item_id", "aspect", "polarity", "quote", "cues", "feature")}
                      for x in a["aspects"]]
    if out["requirements"]:
        out["requirements"] = {**out["requirements"], "llm": []}
    if results:
        out["evaluation"] = results
    return out


def main(argv: list[str] | None = None) -> int:
    load_dotenv(Path(".env"))
    load_dotenv(PROJECT_ROOT / ".env")
    if env_file := os.environ.get("RELEASEPULSE_ENV_FILE"):
        load_dotenv(Path(env_file))

    ap = argparse.ArgumentParser(prog="releasepulse", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("synth", help="regenerate the synthetic feedback sets")
    p.add_argument("apps", nargs="*", help="app ids (default: all)")
    p.add_argument("-o", "--out", type=Path, default=Path("data/synthetic"))

    p = sub.add_parser("run", help="analyse a feedback CSV or a dataset folder")
    p.add_argument("dataset", type=Path, help="folder with feedback.csv (and releases.csv), or a CSV file")
    p.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"provider:model (default {DEFAULT_MODEL})")
    p.add_argument("-o", "--out", type=Path, help="run folder (default runs/<dataset>/<model>)")
    p.add_argument("--releases", type=Path, help="releases CSV (version, date, notes)")
    p.add_argument("--product", help="one line naming the product, given to the model")
    p.add_argument("--threshold", type=float, help="clustering similarity threshold")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--no-requirements", action="store_true", help="skip wording candidate requirements")

    p = sub.add_parser("eval", help="score an analysis against planted ground truth")
    p.add_argument("analysis", type=Path)
    p.add_argument("gold", type=Path)

    p = sub.add_parser("bench", help="several models, several runs, scored")
    p.add_argument("app", type=Path, help="synthetic dataset folder with gold.json")
    p.add_argument("-m", "--models", nargs="+", required=True)
    p.add_argument("--runs", type=int, default=3)
    p.add_argument("-o", "--out", type=Path, help="default runs/bench/<app>")
    p.add_argument("--report", type=Path, help="write the markdown table here")
    p.add_argument("--parallel-runs", type=int, default=3)

    p = sub.add_parser("sweep", help="re-cluster a run's aspects at several thresholds and score each (no LLM calls)")
    p.add_argument("analysis", type=Path)
    p.add_argument("dataset", type=Path, help="the synthetic dataset folder the run analysed")
    p.add_argument("--thresholds", type=float, nargs="+", default=[0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7])

    p = sub.add_parser("report", help="markdown tables from a bench results.json")
    p.add_argument("results", type=Path)

    p = sub.add_parser("web-export", help="copy an analysis into the web demo's data folder")
    p.add_argument("analysis", type=Path)
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--results", type=Path, help="bench results.json to include as the evaluation summary")

    args = ap.parse_args(argv)

    if args.cmd == "synth":
        from .synthetic import APPS
        from .synthetic.engine import write

        for app in args.apps or list(APPS):
            data = write(APPS[app], args.out / app)
            print(f"wrote {args.out / app}: {len(data['items'])} items")
        return 0

    if args.cmd == "run":
        from .cluster import THRESHOLD
        from .pipeline import analyse, load_dataset

        ds = load_dataset(args.dataset, args.releases, args.product)
        out = args.out or RUNS_DIR / ds["name"] / args.model.replace(":", "_")
        a = analyse(ds, args.model, out, threshold=args.threshold or THRESHOLD, cache=EmbeddingCache(EMBEDDING_CACHE),
                    workers=args.workers, word_requirements=not args.no_requirements)
        print_summary(a)
        print(f"wrote {out / 'analysis.json'}")
        return 0

    if args.cmd == "eval":
        from .evaluate import score

        s = score(_read(args.analysis), _read(args.gold))
        print(json.dumps({k: v for k, v in s.items() if k != "examples"}, indent=1))
        print(json.dumps(s["examples"], indent=1, ensure_ascii=False))
        return 0

    if args.cmd == "bench":
        from .bench import bench, render_markdown

        out = args.out or RUNS_DIR / "bench" / args.app.name
        results = bench(args.app, args.models, args.runs, out, EMBEDDING_CACHE, args.parallel_runs)
        md = render_markdown(results)
        print(md)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(md, encoding="utf-8")
            print(f"wrote {args.report}")
        return 0

    if args.cmd == "sweep":
        from .cluster import cluster_aspects
        from .evaluate import score
        from .ingest import prepare
        from .pipeline import assemble, load_dataset

        a = _read(args.analysis)
        ds = load_dataset(args.dataset)
        prepared = prepare(ds["items_csv"], ds["releases_csv"])
        cache = EmbeddingCache(EMBEDDING_CACHE)
        ex = {"aspects": a["aspects"], "rejected": [], "missing": a["extraction"]["missing_items"]}
        print("threshold  features  purity  inv.purity  item×feature F1  regressions P/R  improvements P/R")
        for t in args.thresholds:
            cl = cluster_aspects(ex["aspects"], t, cache)
            s = score(assemble(ds, prepared, ex, cl, a["model"], [], None), ds["gold"])
            c, r, i = s["clusters"], s["regressions"], s["improvements"]
            print(f"{t:9.2f}  {c['features_predicted']:8d}  {c['purity']:6.3f}  {c['inverse_purity']:10.3f}  "
                  f"{s['item_features']['f1']:15.3f}  {r['precision']:.2f}/{r['recall']:.2f}        "
                  f"{i['precision']:.2f}/{i['recall']:.2f}")
        return 0

    if args.cmd == "report":
        from .bench import render_markdown

        print(render_markdown(_read(args.results)))
        return 0

    if args.cmd == "web-export":
        results = _read(args.results) if args.results else None
        _write(args.out, web_payload(_read(args.analysis), results), indent=None)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
