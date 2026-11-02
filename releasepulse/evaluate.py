"""Score an analysis against the planted ground truth of a synthetic set.

Pairing: within each item, extracted aspects and planted mentions are paired
one-to-one by the character spans of the verified quotes, choosing the
assignment with the most overlapping pairs, then the highest total coverage
of the planted spans (an item has at most a handful of each, so this is exact
search). A quote that runs across two sentences therefore still pairs with
the right mention. An unpaired aspect whose quote overlaps an
already-paired mention is a *split* (the model named two aspects where one
was planted); it counts as grounded for precision, and as wrong for strict
precision. Everything else unpaired is *extra* (invented, or a real aspect the
gold does not plant, e.g. in a closing remark).

Features: each predicted cluster is mapped to the planted feature most of its
paired aspects belong to. Item-level feature F1, regression and improvement
precision and recall are computed after that mapping, so they include
clustering errors. Clusters without paired aspects map to nothing.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .ingest import prepare
from .trends import build_counts, detect, detect_raw


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _best_assignment(n_gold: int, preds: list[int], cover: dict) -> list[tuple[int, int]]:
    """One-to-one pairs (gold index, pred index) maximising the number of pairs with any
    overlap, then the summed coverage. Exhaustive; items have few mentions."""
    best: tuple = ((0, 0.0), [])

    def search(gi: int, free: list[int], pairs: list, n: int, total: float) -> None:
        nonlocal best
        if gi == n_gold:
            if (n, total) > best[0]:
                best = ((n, total), list(pairs))
            return
        search(gi + 1, free, pairs, n, total)
        for p in free:
            if cover[(gi, p)] > 0:
                search(gi + 1, [q for q in free if q != p], pairs + [(gi, p)], n + 1, total + cover[(gi, p)])

    search(0, list(preds), [], 0, 0.0)
    return best[1]


def pair_mentions(aspects: list[dict], gold: dict, sent: set[str]) -> dict:
    preds = defaultdict(list)
    for i, a in enumerate(aspects):
        preds[a["item_id"]].append(i)
    matched, splits, extra, missed = [], [], [], []
    for iid, g in gold["items"].items():
        if iid not in sent:
            continue
        gms = g["mentions"]
        ps = preds.get(iid, [])
        cover = {(gi, p): _overlap(tuple(aspects[p]["span"]), (m["start"], m["end"])) / (m["end"] - m["start"])
                 for gi, m in enumerate(gms) for p in ps}
        best = _best_assignment(len(gms), ps, cover)
        used_g, used_p = {gi for gi, _ in best}, {p for _, p in best}
        matched += [{"item_id": iid, "pred": p, "gold": gms[gi]} for gi, p in sorted(best)]
        for p in preds.get(iid, []):
            if p in used_p:
                continue
            parent = next((gms[gi] for gi in sorted(used_g)
                           if _overlap(tuple(aspects[p]["span"]), (gms[gi]["start"], gms[gi]["end"])) > 0), None)
            (splits if parent else extra).append({"item_id": iid, "pred": p, "gold": parent})
        missed += [{"item_id": iid, "gold": gms[gi]} for gi in range(len(gms)) if gi not in used_g]
    return {"matched": matched, "splits": splits, "extra": extra, "missed": missed}


def feature_map(aspects: list[dict], pairs: dict) -> dict[str, str]:
    votes = defaultdict(Counter)
    for m in pairs["matched"]:
        votes[aspects[m["pred"]]["feature"]][m["gold"]["feature"]] += 1
    return {fid: sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for fid, c in votes.items()}


def purity(aspects: list[dict], pairs: dict) -> dict:
    table = defaultdict(Counter)
    for m in pairs["matched"]:
        table[aspects[m["pred"]]["feature"]][m["gold"]["feature"]] += 1
    n = sum(sum(c.values()) for c in table.values())
    if not n:
        return {"purity": None, "inverse_purity": None, "clusters": 0}
    by_gold = defaultdict(Counter)
    for fid, c in table.items():
        for g, k in c.items():
            by_gold[g][fid] += k
    return {"purity": sum(max(c.values()) for c in table.values()) / n,
            "inverse_purity": sum(max(c.values()) for c in by_gold.values()) / n,
            "clusters": len(table)}


def _prf(pred: set, gold: set) -> dict:
    tp = len(pred & gold)
    p = tp / len(pred) if pred else (1.0 if not gold else 0.0)
    r = tp / len(gold) if gold else 1.0
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0,
            "tp": sorted(pred & gold), "fp": sorted(pred - gold), "fn": sorted(gold - pred)}


def _flag_set(flags: list[dict], kind: str, fmap: dict[str, str] | None) -> set[tuple[str, str]]:
    return {(f["release"], fmap.get(f["feature"], f"unmapped:{f['feature']}") if fmap is not None else f["feature"])
            for f in flags if f["kind"] == kind}


def oracle(gold: dict, dataset: dict) -> dict:
    """The detector and the raw-count baseline run on the planted labels: what
    perfect extraction and clustering would give."""
    prepared = prepare(dataset["items_csv"], dataset["releases_csv"])
    mentions = [{"item_id": iid, "feature": m["feature"], "polarity": m["polarity"]}
                for iid, g in gold["items"].items() for m in g["mentions"]]
    counts = build_counts(mentions, prepared["items"], prepared["releases"])
    raw = build_counts(mentions, prepared["items"], prepared["releases"], include_duplicates=True)
    return {"flags": detect(counts), "flags_without_dedupe": detect(raw), "raw_flags": detect_raw(raw)}


def score(analysis: dict, gold: dict) -> dict:
    aspects = analysis["aspects"]
    sent = {iid for iid, it in analysis["items"].items() if it["release"] and not it["duplicate_of"]}
    pairs = pair_mentions(aspects, gold, sent)
    n_pred = len(aspects)
    n_gold = len(pairs["matched"]) + len(pairs["missed"])
    matched, splits = len(pairs["matched"]), len(pairs["splits"])
    precision = (matched + splits) / n_pred if n_pred else 0.0
    recall = matched / n_gold if n_gold else 0.0
    agree = [aspects[m["pred"]]["polarity"] == m["gold"]["polarity"] for m in pairs["matched"]]
    complaint_agree = [(aspects[m["pred"]]["polarity"] in ("negative", "mixed")) == (m["gold"]["polarity"] == "negative")
                       for m in pairs["matched"]]

    hard_matched = [m for m in pairs["matched"] if m["gold"].get("hard")]
    hard_gold = len(hard_matched) + sum(1 for m in pairs["missed"] if m["gold"].get("hard"))

    fmap = feature_map(aspects, pairs)
    pred_if = {(a["item_id"], fmap.get(a["feature"], "unmapped:" + a["feature"])) for a in aspects}
    gold_if = {(iid, m["feature"]) for iid in sent for m in gold["items"][iid]["mentions"]}

    def flags_prf(flags: list[dict], kind: str, mapped: bool = True) -> dict:
        truth = {(g["release"], g["feature"]) for g in gold["regressions" if kind == "regression" else "improvements"]}
        return _prf(_flag_set(flags, kind, fmap if mapped else None), truth)

    traps = []
    for t in gold["traps"]:
        key = (t["release"], t["feature"])
        traps.append({**t, "flagged": key in _flag_set(analysis["flags"], "regression", fmap),
                      "flagged_without_dedupe": key in _flag_set(analysis["flags_without_dedupe"], "regression", fmap),
                      "flagged_raw": key in _flag_set(analysis["raw_flags"], "regression", fmap)})

    pooled = []
    for f in analysis["features"]:
        k = sum(s["praise"]["count"] for s in f["series"])
        n = sum(s["volume"] for s in f["series"])
        pooled.append((k / n if n else 0.0, f["id"]))
    top_praised = fmap.get(max(pooled)[1]) if pooled else None

    gold_dup = {iid: g["duplicate_of"] for iid, g in gold["items"].items()}
    pred_dup = {iid: it["duplicate_of"] for iid, it in analysis["items"].items()}
    gold_rel = {iid: g["release"] for iid, g in gold["items"].items()}
    return {
        "mentions": {"gold": n_gold, "predicted": n_pred, "matched": matched, "splits": splits,
                     "extra": len(pairs["extra"]), "missed": len(pairs["missed"]),
                     "precision": precision, "strict_precision": matched / n_pred if n_pred else 0.0,
                     "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0},
        "polarity_agreement": sum(agree) / len(agree) if agree else None,
        "hard": {
            "gold": hard_gold,
            "recall": len(hard_matched) / hard_gold if hard_gold else None,
            "polarity_agreement": (sum(aspects[m["pred"]]["polarity"] == m["gold"]["polarity"] for m in hard_matched)
                                   / len(hard_matched)) if hard_matched else None,
            "feature_agreement": (sum(fmap.get(aspects[m["pred"]]["feature"]) == m["gold"]["feature"]
                                      for m in hard_matched) / len(hard_matched)) if hard_matched else None,
        },
        "complaint_agreement": sum(complaint_agree) / len(complaint_agree) if complaint_agree else None,
        "item_features": {k: v for k, v in _prf(pred_if, gold_if).items() if k in ("precision", "recall", "f1")},
        "quote_validity": analysis["extraction"]["quote_validity"],
        "cue_validity": analysis["extraction"]["cue_validity"],
        "missing_items": len(analysis["extraction"]["missing_items"]),
        "clusters": {**purity(aspects, pairs), "features_predicted": len(analysis["features"]),
                     "features_gold": len(gold["features"])},
        "feature_map": fmap,
        "regressions": flags_prf(analysis["flags"], "regression"),
        "improvements": flags_prf(analysis["flags"], "improvement"),
        "regressions_without_dedupe": flags_prf(analysis["flags_without_dedupe"], "regression"),
        "regressions_raw": flags_prf(analysis["raw_flags"], "regression"),
        "traps": traps,
        "top_praised_ok": top_praised in gold["praised"],
        "duplicates": _prf({k for k, v in pred_dup.items() if v}, {k for k, v in gold_dup.items() if v}),
        "release_accuracy": sum(analysis["items"][i]["release"] == r for i, r in gold_rel.items()) / len(gold_rel),
        "examples": {
            "missed": [{"item_id": m["item_id"], "feature": m["gold"]["feature"],
                        "text": analysis["items"][m["item_id"]]["text"][m["gold"]["start"]:m["gold"]["end"]]}
                       for m in pairs["missed"][:15]],
            "extra": [{"item_id": e["item_id"], "aspect": aspects[e["pred"]]["aspect"],
                       "polarity": aspects[e["pred"]]["polarity"], "quote": aspects[e["pred"]]["quote"]}
                      for e in pairs["extra"][:15]],
            "polarity_disagreements": [{"item_id": m["item_id"], "gold": m["gold"]["polarity"],
                                        "pred": aspects[m["pred"]]["polarity"], "quote": aspects[m["pred"]]["quote"]}
                                       for m in pairs["matched"]
                                       if aspects[m["pred"]]["polarity"] != m["gold"]["polarity"]][:15],
        },
    }
