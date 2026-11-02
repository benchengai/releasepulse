"""Per-release, per-feature counts, rates and change flags.

The unit is a feedback item: an item complains about a feature if it has a
negative or mixed aspect in that feature (two aspects of one item in the same
feature count once). A release's volume is its number of items, with
copy-pasted duplicates counted once. Rates are complaints divided by volume,
so a release that gets twice the reviews does not look twice as broken.

Change between consecutive releases uses Newcombe's interval for the
difference in rates. A regression is flagged when the whole 95% interval is
above zero and the newer release has at least MIN_COUNT complaints; an
improvement when the interval is below zero and the older release had at
least MIN_COUNT. The raw-count rule is the naive baseline it is compared with:
"complaints went up by at least 4 and by half", counting every post.
"""

from __future__ import annotations

from collections import defaultdict

from .stats import newcombe_diff, rate

MIN_COUNT = 5
RAW_MIN_INCREASE = 4
RAW_MIN_RATIO = 1.5
CLASSES = ("complaints", "praise", "requests")


def classes_of(polarity: str) -> list[str]:
    return {"negative": ["complaints"], "positive": ["praise"], "mixed": ["complaints", "praise"],
            "neutral": ["requests"]}[polarity]


def build_counts(mentions: list[dict], items: list[dict], releases: list[dict],
                 include_duplicates: bool = False) -> dict:
    """{"volume": {release: n}, "features": {feature: {release: {class: [item ids]}}}}.
    With include_duplicates, every post counts, duplicates repeating their first copy."""
    order = [r["version"] for r in releases]
    by_item = defaultdict(list)
    for m in mentions:
        by_item[m["item_id"]].append(m)
    volume = {v: 0 for v in order}
    features: dict = defaultdict(lambda: {v: {c: set() for c in CLASSES} for v in order})
    for it in items:
        if it.get("release") not in volume or (it.get("duplicate_of") and not include_duplicates):
            continue
        volume[it["release"]] += 1
        source = it["duplicate_of"] or it["id"] if include_duplicates else it["id"]
        for m in by_item.get(source, []):
            for c in classes_of(m["polarity"]):
                features[m["feature"]][it["release"]][c].add(it["id"])
    return {"releases": order, "volume": volume,
            "features": {f: {v: {c: sorted(ids) for c, ids in per.items()} for v, per in rels.items()}
                         for f, rels in sorted(features.items())}}


def series(counts: dict, feature: str) -> list[dict]:
    """Rates with Wilson intervals for every release, for one feature."""
    rows = []
    for v in counts["releases"]:
        n = counts["volume"][v]
        per = counts["features"].get(feature, {}).get(v, {c: [] for c in CLASSES})
        rows.append({"release": v, "volume": n, **{c: rate(len(per[c]), n) for c in CLASSES}})
    return rows


def detect(counts: dict, min_count: int = MIN_COUNT, cls: str = "complaints") -> list[dict]:
    flags = []
    rels = counts["releases"]
    for prev, cur in zip(rels, rels[1:]):
        n0, n1 = counts["volume"][prev], counts["volume"][cur]
        if not n0 or not n1:
            continue
        for f, per in counts["features"].items():
            k0, k1 = len(per[prev][cls]), len(per[cur][cls])
            d, low, high = newcombe_diff(k1, n1, k0, n0)
            kind = None
            if low > 0 and k1 >= min_count:
                kind = "regression"
            elif high < 0 and k0 >= min_count:
                kind = "improvement"
            if kind:
                flags.append({"kind": kind, "feature": f, "release": cur, "previous": prev,
                              "count": k1, "volume": n1, "previous_count": k0, "previous_volume": n0,
                              "rate": k1 / n1, "previous_rate": k0 / n0, "diff": d, "low": low, "high": high})
    return flags


def detect_raw(counts: dict, min_increase: int = RAW_MIN_INCREASE, min_ratio: float = RAW_MIN_RATIO) -> list[dict]:
    """The naive rule: flag when the complaint count rose by at least `min_increase`
    and by `min_ratio` times. Meant to be run on counts that include duplicates."""
    flags = []
    rels = counts["releases"]
    for prev, cur in zip(rels, rels[1:]):
        for f, per in counts["features"].items():
            k0, k1 = len(per[prev]["complaints"]), len(per[cur]["complaints"])
            if k1 - k0 >= min_increase and k1 >= min_ratio * k0:
                flags.append({"kind": "regression", "feature": f, "release": cur, "previous": prev,
                              "count": k1, "previous_count": k0})
    return flags


def _round_robin(cands: list[dict], k: int) -> list[dict]:
    by_source = defaultdict(list)
    for c in sorted(cands, key=lambda c: (abs(len(c["quote"]) - 70), c["item_id"])):
        by_source[c["source"]].append(c)
    out, queues = [], [by_source[s] for s in sorted(by_source)]
    while len(out) < k and any(queues):
        for q in queues:
            if q and len(out) < k:
                out.append(q.pop(0))
    return out


def quotes_for(feature: str, item_ids: list[str], mentions_by_item: dict, items_by_id: dict,
               cls: str, k: int = 3) -> list[dict]:
    """Up to k verified quotes, spread across sources, preferring mid-length ones."""
    cands = []
    for iid in item_ids:
        it = items_by_id[iid]
        source_id = it.get("duplicate_of") or iid
        for m in mentions_by_item.get(source_id, []):
            if m["feature"] == feature and cls in classes_of(m["polarity"]):
                cands.append({"item_id": iid, "release": it["release"], "date": it["date"], "source": it["source"],
                              "polarity": m["polarity"], "quote": m["quote"], "cues": m.get("cues", [])})
                break
    return _round_robin(cands, k)
