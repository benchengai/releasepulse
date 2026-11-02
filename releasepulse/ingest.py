"""Load feedback items, assign each to a release, and collapse copy-pasted duplicates.

Input is a CSV with the columns text, date, version and source (id and rating
are optional). An item belongs to the release its version names; a patch
version (2.1.3) belongs to its minor release (2.1) when only that is listed.
Items without a usable version are assigned by date: the latest release
published on or before the item's date. Releases come from a releases CSV
(version, date, notes) or, without one, are inferred from the versions seen.

Duplicates: one message posted several times (the same rant on two stores and
the issue tracker, or a copy-paste campaign) is counted once, so the loudest
voice does not count several times. Short texts ("Great app!") are never
collapsed: many different people write them.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

REQUIRED = ("text", "date", "version", "source")
DUPLICATE_MIN_TOKENS = 8
DUPLICATE_JACCARD = 0.9

_VERSION_RE = re.compile(r"^\s*v?(\d+(?:\.\d+)*)")
_TOKEN_RE = re.compile(r"[a-z0-9']+")


def version_key(version: str | None) -> tuple[int, ...] | None:
    m = _VERSION_RE.match(version or "")
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip()[:10])
    except (ValueError, AttributeError):
        return None


def load_items(path: Path) -> tuple[list[dict], list[dict]]:
    """Items and the rows that were skipped, with the reason."""
    items, skipped = [], []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column(s) {', '.join(missing)}")
        for i, row in enumerate(reader, start=1):
            item_id = (row.get("id") or "").strip() or f"I{i:04d}"
            text = " ".join((row.get("text") or "").split())
            if not text:
                skipped.append({"id": item_id, "reason": "empty text"})
                continue
            d = parse_date(row.get("date") or "")
            rating = (row.get("rating") or "").strip()
            items.append({
                "id": item_id,
                "text": text,
                "date": d.isoformat() if d else None,
                "version": (row.get("version") or "").strip(),
                "source": (row.get("source") or "").strip() or "unknown",
                "rating": int(rating) if rating.isdigit() else None,
            })
    ids = [it["id"] for it in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate ids")
    return items, skipped


def load_releases(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    releases = []
    for row in rows:
        d = parse_date(row["date"])
        if version_key(row["version"]) is None or d is None:
            raise ValueError(f"{path}: bad release row {row}")
        releases.append({"version": row["version"].strip().lstrip("v"), "date": d.isoformat(),
                         "notes": (row.get("notes") or "").strip()})
    return sorted(releases, key=lambda r: version_key(r["version"]))


def infer_releases(items: list[dict]) -> list[dict]:
    """One release per minor version seen, dated by its earliest feedback item."""
    first: dict[tuple[int, ...], str] = {}
    for it in items:
        key = version_key(it["version"])
        if key is None or it["date"] is None:
            continue
        minor = (key + (0,))[:2]
        if minor not in first or it["date"] < first[minor]:
            first[minor] = it["date"]
    return [{"version": ".".join(map(str, k)), "date": d, "notes": "inferred from feedback versions"}
            for k, d in sorted(first.items())]


def match_release(version: str, releases: list[dict]) -> str | None:
    """The listed release whose version is the longest prefix of this one
    (missing parts count as zero: "2" is "2.0")."""
    key = version_key(version)
    if key is None:
        return None
    best = None
    for r in releases:
        rk = version_key(r["version"])
        padded = key + (0,) * (len(rk) - len(key))
        if padded[:len(rk)] == rk and (best is None or len(rk) > len(version_key(best))):
            best = r["version"]
    return best


def assign_releases(items: list[dict], releases: list[dict]) -> None:
    by_date = sorted(releases, key=lambda r: r["date"])
    for it in items:
        release = match_release(it["version"], releases)
        if release:
            it["release"], it["assigned_by"] = release, "version"
            continue
        earlier = [r for r in by_date if it["date"] and r["date"] <= it["date"]]
        if earlier:
            it["release"], it["assigned_by"] = earlier[-1]["version"], "date"
        else:
            it["release"], it["assigned_by"] = None, "unassigned"


def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def mark_duplicates(items: list[dict]) -> None:
    """Set `duplicate_of` on every item that repeats an earlier one (by date, then id)."""
    order = sorted(items, key=lambda it: (it["date"] or "", it["id"]))
    kept: list[tuple[dict, set[str]]] = []
    for it in order:
        it["duplicate_of"] = None
        toks = _tokens(it["text"])
        if len(it["text"].split()) < DUPLICATE_MIN_TOKENS:
            continue
        for first, ftoks in kept:
            if len(toks & ftoks) / len(toks | ftoks) >= DUPLICATE_JACCARD:
                it["duplicate_of"] = first["id"]
                break
        else:
            kept.append((it, toks))


def prepare(items_csv: Path, releases_csv: Path | None = None) -> dict:
    items, skipped = load_items(items_csv)
    releases = load_releases(releases_csv) if releases_csv else infer_releases(items)
    if not releases:
        raise ValueError("no releases: give a releases CSV or a version column with values")
    assign_releases(items, releases)
    mark_duplicates(items)
    for r in releases:
        members = [it for it in items if it["release"] == r["version"]]
        r["items"] = len(members)
        r["volume"] = sum(1 for it in members if not it["duplicate_of"])
        r["duplicates"] = r["items"] - r["volume"]
        r["assigned_by_date"] = sum(1 for it in members if it["assigned_by"] == "date")
    return {"items": items, "releases": releases, "skipped": skipped,
            "unassigned": [it["id"] for it in items if it["release"] is None]}
