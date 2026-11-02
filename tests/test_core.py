import json
from pathlib import Path

import numpy as np
import pytest

from releasepulse import requirements as req
from releasepulse.cluster import agglomerate
from releasepulse.evaluate import oracle, score
from releasepulse.extract import SCHEMA, Extraction, normalise_label, schema_for, verify_batch
from releasepulse.ingest import assign_releases, infer_releases, mark_duplicates, match_release, prepare, version_key
from releasepulse.pipeline import assemble, load_dataset
from releasepulse.prioritise import table
from releasepulse.stats import newcombe_diff, wilson
from releasepulse.synthetic import APPS
from releasepulse.synthetic.engine import generate, to_csv
from releasepulse.trends import build_counts, detect, detect_raw
from releasepulse.verify import locate, quote_matches

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/synthetic"


def _item(iid, text, release="2.0", date="2026-03-03", source="app_store", duplicate_of=None):
    return {"id": iid, "text": text, "release": release, "date": date, "source": source,
            "duplicate_of": duplicate_of, "version": release, "rating": None, "assigned_by": "version"}


# --- quote verification -------------------------------------------------------------

def test_quotes_verify_and_locate():
    text = "Updated yesterday. Since the update it keeps kicking me back to the sign-in screen. Please fix."
    start, end = locate("keeps kicking me back to the sign in screen", text)
    assert text[start:end] == "keeps kicking me back to the sign-in screen"
    assert quote_matches("KEEPS kicking me back!", text)
    assert not quote_matches("the sync is slow", text)
    assert not quote_matches("", text)
    # One dropped letter is tolerated, a different claim is not.
    assert quote_matches("it keeps kicking me bak to the sign-in screen", text)
    assert not quote_matches("it never kicks me back to the sign-in screen", text)


# --- statistics ---------------------------------------------------------------------

def test_wilson_interval():
    low, high = wilson(0, 10)
    assert low == 0.0 and high == pytest.approx(0.2775, abs=1e-4)
    low, high = wilson(5, 10)
    assert (low, high) == (pytest.approx(0.2366, abs=1e-4), pytest.approx(0.7634, abs=1e-4))
    assert wilson(0, 0) == (0.0, 1.0)


def test_newcombe_matches_published_example():
    # Newcombe (1998), example (a): 56/70 against 48/80, hybrid score interval 0.0524 to 0.3339.
    d, low, high = newcombe_diff(56, 70, 48, 80)
    assert d == pytest.approx(0.2)
    assert low == pytest.approx(0.0524, abs=1e-4)
    assert high == pytest.approx(0.3339, abs=1e-4)


# --- ingest -------------------------------------------------------------------------

def test_versions_and_release_assignment():
    assert version_key("v2.1.0") == (2, 1, 0)
    assert version_key("2.10.3") == (2, 10, 3)
    assert version_key("beta") is None
    releases = [{"version": "2.0", "date": "2026-03-02"}, {"version": "2.1", "date": "2026-04-06"}]
    assert match_release("2.1.3", releases) == "2.1"
    assert match_release("v2", releases) == "2.0"
    assert match_release("2.5", releases) is None
    assert match_release("3.0", releases) is None
    items = [{"id": "a", "version": "2.0.1", "date": "2026-05-01"},     # version wins over date
             {"id": "b", "version": "", "date": "2026-04-10"},          # by date
             {"id": "c", "version": "garbage", "date": "2026-01-01"}]   # before the first release
    assign_releases(items, releases)
    assert [(i["release"], i["assigned_by"]) for i in items] == [("2.0", "version"), ("2.1", "date"),
                                                                 (None, "unassigned")]


def test_infer_releases_from_versions():
    items = [{"version": "2.1.1", "date": "2026-04-09"}, {"version": "2.1.0", "date": "2026-04-07"},
             {"version": "2.0", "date": "2026-03-05"}, {"version": "", "date": "2026-01-01"}]
    assert [(r["version"], r["date"]) for r in infer_releases(items)] == [("2.0", "2026-03-05"), ("2.1", "2026-04-07")]


def test_duplicates_collapse_long_copies_only():
    rant = "THE NEW DARK MODE IS BLINDING!!! White panels everywhere, it's like staring into a lamp."
    items = [_item("1", rant, date="2026-05-12"), _item("2", rant.lower() + "!!", date="2026-05-13"),
             _item("3", "Great app!"), _item("4", "Great app!"),
             _item("5", "White panels everywhere in dark mode, otherwise a lovely update to the app.")]
    mark_duplicates(items)
    assert [i["duplicate_of"] for i in items] == [None, "1", None, None, None]


# --- synthetic data -----------------------------------------------------------------

@pytest.mark.parametrize("app", sorted(APPS))
def test_synthetic_data_is_reproducible_and_spans_are_exact(app):
    data = generate(APPS[app])
    committed = (DATA / app / "feedback.csv").read_text(encoding="utf-8")
    assert to_csv(data["items"], ["id", "date", "version", "source", "rating", "text"]) == committed
    gold = json.loads((DATA / app / "gold.json").read_text(encoding="utf-8"))
    assert "SYNTHETIC" in gold["notice"]
    texts = {it["id"]: it["text"] for it in data["items"]}
    for iid, g in gold["items"].items():
        for m in g["mentions"]:
            assert 0 <= m["start"] < m["end"] <= len(texts[iid])
            assert m["feature"] in gold["features"]


@pytest.mark.parametrize("app", sorted(APPS))
def test_planted_truth_is_recoverable_from_gold_labels(app):
    """With perfect extraction the detector finds exactly the planted changes, the raw-count
    rule falls for the volume and duplicate traps, and skipping de-duplication falls for the
    duplicate trap."""
    ds = load_dataset(DATA / app)
    gold = ds["gold"]
    o = oracle(gold, ds)
    found = {(f["kind"], f["release"], f["feature"]) for f in o["flags"]}
    planted = {("regression", g["release"], g["feature"]) for g in gold["regressions"]} | \
              {("improvement", g["release"], g["feature"]) for g in gold["improvements"]}
    assert found == planted
    traps = {t["kind"]: (t["release"], t["feature"]) for t in gold["traps"]}
    raw = {(f["release"], f["feature"]) for f in o["raw_flags"]}
    assert traps["volume_spike"] in raw and traps["duplicate_burst"] in raw
    assert traps["small_sample"] not in raw
    nodedupe = {(f["release"], f["feature"]) for f in o["flags_without_dedupe"] if f["kind"] == "regression"}
    assert traps["duplicate_burst"] in nodedupe
    prepared = prepare(ds["items_csv"], ds["releases_csv"])
    assert all(it["release"] == gold["items"][it["id"]]["release"] for it in prepared["items"])
    assert {it["id"]: it["duplicate_of"] for it in prepared["items"]} == \
           {iid: g["duplicate_of"] for iid, g in gold["items"].items()}


# --- extraction ---------------------------------------------------------------------

def _strict(schema: dict) -> None:
    if schema.get("type") == "object":
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])
        for sub in schema["properties"].values():
            _strict(sub)
    elif schema.get("type") == "array":
        _strict(schema["items"])


def test_schemas_are_strict():
    _strict(SCHEMA)
    _strict(req.SCHEMA)
    assert schema_for(["A", "B"])["properties"]["items"]["items"]["properties"]["item_id"]["enum"] == ["A", "B"]
    assert "enum" not in SCHEMA["properties"]["items"]["items"]["properties"]["item_id"]


def test_verify_batch_keeps_only_grounded_aspects():
    items = [_item("A", "Sync is slow. Love the offline mode."), _item("B", "Great app!"), _item("C", "Meh.")]
    extraction = Extraction.model_validate({"items": [
        {"item_id": "A", "aspects": [
            {"aspect": "Sync", "polarity": "negative", "quote": "Sync is slow", "cues": ["slow", "awful"]},
            {"aspect": "offline mode", "polarity": "positive", "quote": "love the offline mode", "cues": ["Love"]},
            {"aspect": "search", "polarity": "negative", "quote": "search never works", "cues": []}]},
        {"item_id": "B", "aspects": []},
        {"item_id": "Z", "aspects": [{"aspect": "x", "polarity": "neutral", "quote": "Great app", "cues": []}]},
    ]})
    out = verify_batch(items, extraction)
    assert [(a["aspect"], a["polarity"]) for a in out["aspects"]] == [("sync", "negative"), ("offline mode", "positive")]
    assert out["aspects"][0]["cues"] == ["slow"] and out["aspects"][0]["dropped_cues"] == ["awful"]
    assert {r["reason"] for r in out["rejected"]} == {"quote not found in item", "unknown or repeated item"}
    assert out["missing"] == ["C"]
    assert normalise_label(" Dark-Mode. ") == "dark mode"


# --- clustering ---------------------------------------------------------------------

def test_agglomerate_merges_close_vectors_only():
    v = np.array([[1, 0, 0], [0.95, 0.31, 0], [0, 1, 0], [0, 0.1, 0.99]], dtype=float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    groups = agglomerate(v, 0.8)
    assert sorted(groups) == [[0, 1], [2], [3]]
    assert agglomerate(v, -1.0) == [[0, 1, 2, 3]]
    assert agglomerate(np.zeros((0, 3)), 0.5) == []


# --- trends and prioritisation ------------------------------------------------------

def _scenario():
    """Release 2 has twice the volume, so feature 'b' doubles in count at a flat rate;
    feature 'a' jumps in rate; feature 'c' is new with 2 complaints in release 3."""
    releases = [{"version": v} for v in ("1", "2", "3")]
    items, mentions = [], []

    def add(release, n, feats):
        for k in range(n):
            iid = f"{release}-{k}"
            items.append(_item(iid, "text", release=release))
            for f, upto in feats.items():
                if k < upto:
                    mentions.append({"item_id": iid, "feature": f, "polarity": "negative", "quote": "text"})
    add("1", 50, {"a": 2, "b": 5})
    add("2", 100, {"a": 30, "b": 10})
    add("3", 20, {"a": 1, "b": 2, "c": 2})
    return items, mentions, releases


def test_detect_uses_rates_not_counts():
    items, mentions, releases = _scenario()
    counts = build_counts(mentions, items, releases)
    flags = {(f["kind"], f["release"], f["feature"]) for f in detect(counts)}
    assert flags == {("regression", "2", "a"), ("improvement", "3", "a")}
    raw = {(f["release"], f["feature"]) for f in detect_raw(counts)}
    assert ("2", "b") in raw  # the naive rule mistakes volume for a regression


def test_duplicates_count_once_unless_asked():
    items = [_item("1", "x"), _item("2", "x", duplicate_of="1"), _item("3", "y")]
    mentions = [{"item_id": "1", "feature": "f", "polarity": "mixed", "quote": "x"}]
    releases = [{"version": "2.0"}]
    once = build_counts(mentions, items, releases)
    every = build_counts(mentions, items, releases, include_duplicates=True)
    assert once["volume"]["2.0"] == 2 and once["features"]["f"]["2.0"]["complaints"] == ["1"]
    assert once["features"]["f"]["2.0"]["praise"] == ["1"]
    assert every["volume"]["2.0"] == 3 and every["features"]["f"]["2.0"]["complaints"] == ["1", "2"]


def test_priority_ranks_by_lower_bound_and_shows_raw_rank():
    items, mentions, releases = _scenario()
    counts = build_counts(mentions, items, releases)
    by_item = {}
    for m in mentions:
        by_item.setdefault(m["item_id"], []).append(m)
    feats = [{"id": f, "name": f} for f in "abc"]
    tbl = table(counts, counts, feats, detect(counts), by_item, {it["id"]: it for it in items}, k=1)
    rows = {r["feature"]: r for r in tbl["rows"]}
    # In release 3, 'b' and 'c' both have 2 of 20; 'a' has 1 of 20 and is flagged improved.
    assert rows["c"]["complaints"]["rate"] == pytest.approx(0.1)
    assert rows["c"]["priority"] == pytest.approx(wilson(2, 20)[0])
    assert rows["a"]["status"] == "improved" and rows["a"]["since"] == "3"
    assert rows["c"]["status"] == "thin evidence"
    assert all(r["evidence"] for r in tbl["rows"])
    assert [r["rank"] for r in tbl["rows"]] == [1, 2, 3]
    assert {r["raw_rank"] for r in tbl["rows"]} == {1, 2, 3}


# --- requirement export -------------------------------------------------------------

ELICITSENSE_ITEM_KEYS = {"id", "type", "statement", "rationale", "acceptance", "stakeholder", "status", "evidence",
                         "dropped_evidence", "quality", "uncertainty", "meeting", "history", "merged_from",
                         "merged_into", "superseded_by"}
ELICITSENSE_EVIDENCE_KEYS = {"meeting", "segment_id", "start", "end", "speaker", "quote"}


def test_register_export_has_elicitsense_shape():
    items, mentions, releases = _scenario()
    counts = build_counts(mentions, items, releases)
    by_item = {}
    for m in mentions:
        by_item.setdefault(m["item_id"], []).append(m)
    tbl = table(counts, counts, [{"id": f, "name": f} for f in "abc"], detect(counts), by_item,
                {it["id"]: it for it in items}, k=3)
    issues = req.top_issues(tbl, 2)
    wording = req.Wording.model_validate({"requirements": [
        {"issue_id": issues[0]["feature"], "statement": "The app shall keep users signed in.",
         "type": "functional"}]})
    reg = req.to_register(issues, wording, tbl, "demo", None)
    assert {"meetings", "active", "open_conflicts", "requirements", "relations", "dropped_links"} <= set(reg)
    (item,) = reg["requirements"]
    assert ELICITSENSE_ITEM_KEYS <= set(item)
    assert item["status"] == "proposed" and item["id"] == "REQ-RP-demo-001"
    assert all(ELICITSENSE_EVIDENCE_KEYS <= set(e) for e in item["evidence"]) and item["evidence"]
    assert reg["not_worded"] == [issues[1]["feature"]]
    assert {q["kind"] for q in item["quality"]} == {"missing_acceptance"}
    c = issues[0]["complaints"]
    assert item["rationale"].startswith(f"{c['count']} of {c['n']} feedback items in releases 1 to 3")
    assert "Do not describe or judge anyone's emotions" in req.SYSTEM


# --- evaluation ---------------------------------------------------------------------

def _gold_analysis(app: str) -> tuple[dict, dict]:
    """An analysis whose aspects are the planted mentions themselves."""
    ds = load_dataset(DATA / app)
    gold = ds["gold"]
    prepared = prepare(ds["items_csv"], ds["releases_csv"])
    texts = {it["id"]: it["text"] for it in prepared["items"]}
    aspects = [{"item_id": iid, "aspect": m["feature"], "polarity": m["polarity"],
                "quote": texts[iid][m["start"]:m["end"]], "span": [m["start"], m["end"]], "cues": [],
                "dropped_cues": [], "feature": m["feature"]}
               for iid, g in gold["items"].items() if not g["duplicate_of"] for m in g["mentions"]]
    features = [{"id": f, "name": f, "mentions": 1, "labels": {f: 1}} for f in gold["features"]]
    a = assemble(ds, prepared, {"aspects": aspects, "rejected": [], "missing": []},
                 {"features": features, "threshold": 0.5}, "none:none", [], None)
    return a, gold


@pytest.mark.parametrize("app", sorted(APPS))
def test_scorer_gives_full_marks_to_the_gold_labels(app):
    a, gold = _gold_analysis(app)
    s = score(a, gold)
    assert s["mentions"]["f1"] == 1.0 and s["mentions"]["extra"] == 0
    assert s["item_features"]["f1"] == 1.0
    assert s["polarity_agreement"] == 1.0
    assert s["clusters"]["purity"] == 1.0 and s["clusters"]["inverse_purity"] == 1.0
    assert s["regressions"]["precision"] == 1.0 and s["regressions"]["recall"] == 1.0
    assert s["improvements"]["recall"] == 1.0
    assert s["regressions_raw"]["precision"] == 0.5
    assert not any(t["flagged"] for t in s["traps"])
    assert s["top_praised_ok"] and s["release_accuracy"] == 1.0
    assert s["duplicates"]["f1"] == 1.0


def test_scorer_counts_splits_and_misses():
    a, gold = _gold_analysis("tallynote")
    first = a["aspects"][0]
    start, end = first["span"]
    half = {**first, "span": [start, (start + end) // 2], "aspect": "other", "feature": "other"}
    a["aspects"] = a["aspects"][1:] + [half, {**first}]
    s = score(a, gold)
    assert s["mentions"]["splits"] == 1 and s["mentions"]["missed"] == 0
    assert s["mentions"]["strict_precision"] < 1.0 == s["mentions"]["precision"]


# --- feature normalisation ----------------------------------------------------------

def test_normalise_applies_grouping_and_records_validator_changes():
    from releasepulse import normalise as norm

    clusters = [{"id": "F01", "name": "startup", "labels": {"startup": 4}},
                {"id": "F02", "name": "loading speed", "labels": {"loading speed": 3, "loading": 1}},
                {"id": "F03", "name": "receipts", "labels": {"receipts": 5}},
                {"id": "F04", "name": "ads", "labels": {"ads": 2}}]
    aspects = [{"feature": "F01"}, {"feature": "F02"}, {"feature": "F03"}, {"feature": "F04"}]
    grouping = norm.Grouping.model_validate({"features": [
        {"name": "Performance", "cluster_ids": ["F01", "F02"]},
        {"name": "receipt scanning", "cluster_ids": ["F03", "F01"]}]})
    out = norm.apply(clusters, grouping, aspects)
    feats = {f["name"]: f for f in out["features"]}
    assert feats["performance"]["labels"] == {"startup": 4, "loading speed": 3, "loading": 1}
    assert feats["performance"]["mentions"] == 8 and feats["performance"]["id"] == "F01"
    assert out["repeated"] == ["F01"] and out["left_out"] == ["F04"]
    assert "ads" in feats
    assert [a["feature"] for a in aspects] == ["F01", "F01", "F02", "F03"]
    assert [a["cluster"] for a in aspects] == ["F01", "F02", "F03", "F04"]
    _strict(norm.SCHEMA)
    assert norm.schema_for(["F01"])["properties"]["features"]["items"]["properties"]["cluster_ids"]["items"]["enum"] == ["F01"]
