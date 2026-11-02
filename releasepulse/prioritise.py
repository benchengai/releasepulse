"""The prioritisation table: one row per feature, every row with its evidence.

Designed against two biases a feedback dashboard invites.

Loudness: a raw count rewards whoever posts most often and the release that
got the most reviews. Rows count de-duplicated items, rates divide by the
window's de-duplicated volume, and the raw post count (duplicates included)
is shown beside each row but never used for ordering.

Recency: the newest release has the fewest reviews, so its numbers swing
most. The default window is the shortest run of latest releases with at least
MIN_WINDOW_VOLUME items, so a two-week-old release is read together with the
one before it; the latest release's own rate is shown with its (wide)
interval; and a rise is called a regression only when it is significant.

Order and bands: within one window every feature shares the same volume, so
ordering by rate is the same as ordering by de-duplicated count, and a rank
alone would overstate small differences. Rows are therefore grouped into
bands: a row starts a new band only when its rate is significantly lower than
the rate of the first row of the band above (Newcombe's interval for the
difference excludes zero; the two rates come from the same items, so this
treats them as independent, an approximation). Ranks inside a band are not
meaningfully different.
"""

from __future__ import annotations

from .stats import newcombe_diff, rate
from .trends import quotes_for

MIN_WINDOW_VOLUME = 100
THIN = 3
EVIDENCE_QUOTES = 5


def default_window(counts: dict, min_volume: int = MIN_WINDOW_VOLUME) -> int:
    total = 0
    for k, v in enumerate(reversed(counts["releases"]), start=1):
        total += counts["volume"][v]
        if total >= min_volume:
            return k
    return len(counts["releases"])


def _status(feature: str, flags: list[dict], order: list[str], complaints: int) -> dict:
    mine = sorted((f for f in flags if f["feature"] == feature), key=lambda f: order.index(f["release"]))
    last = mine[-1] if mine else None
    if last and last["kind"] == "regression":
        return {"status": "regression", "since": last["release"]}
    if last and last["kind"] == "improvement":
        return {"status": "improved", "since": last["release"]}
    if complaints < THIN:
        return {"status": "thin evidence", "since": None}
    return {"status": "ongoing", "since": None}


def assign_bands(rows: list[dict], n: int) -> None:
    band, top = 0, None
    for r in rows:
        if top is None or newcombe_diff(top["complaints"]["count"], n, r["complaints"]["count"], n)[1] > 0:
            band, top = band + 1, r
        r["band"] = band


def table(counts: dict, raw_counts: dict, features: list[dict], flags: list[dict], mentions_by_item: dict,
          items_by_id: dict, k: int) -> dict:
    order = counts["releases"]
    window = order[-k:]
    latest = order[-1]
    before = order[-k - 1] if len(order) > k else None
    n = sum(counts["volume"][v] for v in window)
    names = {f["id"]: f["name"] for f in features}
    rows = []
    for fid, per in counts["features"].items():
        ids = {c: sorted({i for v in window for i in per[v][c]}) for c in ("complaints", "praise", "requests")}
        if not ids["complaints"] and not ids["praise"] and not ids["requests"]:
            continue
        complaints = rate(len(ids["complaints"]), n)
        change = None
        if before and counts["volume"][before]:
            k0, n0 = len(per[before]["complaints"]), counts["volume"][before]
            d, low, high = newcombe_diff(complaints["count"], n, k0, n0)
            change = {"baseline": before, "baseline_rate": k0 / n0, "baseline_count": k0, "baseline_volume": n0,
                      "diff": d, "low": low, "high": high, "significant": low > 0 or high < 0}
        newest_first = sorted(ids["complaints"], key=lambda i: (-order.index(items_by_id[i]["release"]), i))
        raw = raw_counts["features"].get(fid, {})
        rows.append({
            "feature": fid,
            "name": names.get(fid, fid),
            "complaints": complaints,
            "latest": rate(len(per[latest]["complaints"]), counts["volume"][latest]),
            "praise": rate(len(ids["praise"]), n),
            "requests": len(ids["requests"]),
            "raw_complaint_posts": sum(len(raw.get(v, {}).get("complaints", [])) for v in window),
            "change": change,
            "flags": [f for f in flags if f["feature"] == fid],
            **_status(fid, flags, order, complaints["count"]),
            "evidence": quotes_for(fid, newest_first, mentions_by_item, items_by_id, "complaints", EVIDENCE_QUOTES),
            "praise_evidence": quotes_for(fid, ids["praise"], mentions_by_item, items_by_id, "praise", 2),
            "request_evidence": quotes_for(fid, ids["requests"], mentions_by_item, items_by_id, "requests", 2),
        })
    rows.sort(key=lambda r: (-r["complaints"]["count"], r["status"] != "regression", -r["latest"]["rate"], r["name"]))
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    assign_bands(rows, n)
    by_raw = sorted(rows, key=lambda r: (-r["raw_complaint_posts"], r["name"]))
    for i, r in enumerate(by_raw, start=1):
        r["raw_rank"] = i
    return {"k": k, "window": window, "baseline": before, "volume": n, "latest": latest,
            "latest_volume": counts["volume"][latest], "rows": rows}


def all_tables(counts: dict, raw_counts: dict, features: list[dict], flags: list[dict], mentions_by_item: dict,
               items_by_id: dict) -> dict:
    return {"default": default_window(counts),
            "tables": {str(k): table(counts, raw_counts, features, flags, mentions_by_item, items_by_id, k)
                       for k in range(1, len(counts["releases"]) + 1)}}
