"""Merge embedding clusters into the features a product team tracks, and name them.

Embedding similarity groups different wordings of one name ("bank sync",
"bank connection") but keeps sub-features apart ("startup", "loading speed",
"performance"), and a split feature's complaints are spread over several rows
too small to flag. One LLM call sees every cluster (id, member names, counts)
and returns groups of cluster ids with a feature name. Cluster ids are
restricted to the ids in the prompt; the grouping is applied by code: a
cluster the model leaves out stays a feature of its own, a cluster it lists
twice stays in the first group, and both are recorded.

Developed on the development set only (see docs/eval).
"""

from __future__ import annotations

import copy
from collections import Counter
from typing import Callable

from pydantic import BaseModel

from .extract import normalise_label
from .llm import complete_json

SYSTEM = """You organise what users mention in feedback about one software product into \
the features a product team tracks. You get clusters of aspect names extracted from the \
feedback, each with an id, the names in it and how often each name was mentioned.

Rules:
- Put clusters in one group when they are the same feature: different wordings, a \
sub-feature or detail of it, or a quality of it. For example "markdown", "formatting" and \
"editor" are one feature; "price", "subscription" and "upsells" are one feature.
- Keep clusters in separate groups when a product team would track them as separate \
features, even if their names share a word.
- Every cluster id goes in exactly one group. A cluster that fits no other may be a group \
on its own.
- name: a short, lowercase name for the feature, one to three words, as a product team \
would call it.
- Describe the product, not the people who wrote the feedback."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["features"],
    "properties": {
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "cluster_ids"],
                "properties": {
                    "name": {"type": "string"},
                    "cluster_ids": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}


class Group(BaseModel):
    name: str
    cluster_ids: list[str]


class Grouping(BaseModel):
    features: list[Group]


def schema_for(cluster_ids: list[str]) -> dict:
    schema = copy.deepcopy(SCHEMA)
    schema["properties"]["features"]["items"]["properties"]["cluster_ids"]["items"]["enum"] = cluster_ids
    return schema


def render_prompt(clusters: list[dict], product: str | None) -> str:
    lines = [f"Product: {product}", ""] if product else []
    lines.append("Clusters:")
    for c in clusters:
        names = ", ".join(f'"{label}" ({n})' for label, n in c["labels"].items())
        lines.append(f"[{c['id']}] {names}")
    return "\n".join(lines)


def call(clusters: list[dict], spec: str, product: str | None) -> tuple[Grouping, dict]:
    text, meta = complete_json(SYSTEM, render_prompt(clusters, product), schema_for([c["id"] for c in clusters]),
                               "feature_groups", spec)
    return Grouping.model_validate_json(text), meta


def apply(clusters: list[dict], grouping: Grouping, aspects: list[dict]) -> dict:
    """Merged features (ids reassigned by mention count) and a record of what the
    validator changed. Re-points every aspect's `feature` in place."""
    known = {c["id"]: c for c in clusters}
    placed: dict[str, int] = {}
    repeated = []
    groups: list[tuple[str, list[str]]] = []
    for g in grouping.features:
        ids = []
        for cid in g.cluster_ids:
            if cid not in known:
                continue
            if cid in placed:
                repeated.append(cid)
                continue
            placed[cid] = len(groups)
            ids.append(cid)
        if ids:
            groups.append((normalise_label(g.name) or known[ids[0]]["name"], ids))
    left_out = [cid for cid in known if cid not in placed]
    groups += [(known[cid]["name"], [cid]) for cid in left_out]

    merged = []
    for name, ids in groups:
        labels = Counter()
        for cid in ids:
            labels.update(known[cid]["labels"])
        merged.append({"name": name, "clusters": ids, "labels": dict(labels.most_common()),
                       "mentions": sum(labels.values())})
    merged.sort(key=lambda f: (-f["mentions"], f["name"]))
    old_to_new = {}
    for k, f in enumerate(merged, start=1):
        f["id"] = f"F{k:02d}"
        for cid in f["clusters"]:
            old_to_new[cid] = f["id"]
    for a in aspects:
        a["cluster"] = a["feature"]
        a["feature"] = old_to_new[a["feature"]]
    return {"features": [{k: f[k] for k in ("id", "name", "mentions", "labels", "clusters")} for f in merged],
            "left_out": left_out, "repeated": repeated}


def normalise(cl: dict, aspects: list[dict], spec: str, product: str | None,
              cached: Callable[[str], tuple[Grouping, dict] | None] | None = None) -> tuple[dict, dict]:
    """(clustering result with merged features, LLM call metadata)."""
    clusters = cl["features"]
    prompt = render_prompt(clusters, product)
    hit = cached(prompt) if cached else None
    grouping, meta = hit if hit else call(clusters, spec, product)
    result = apply(clusters, grouping, aspects)
    return {**cl, "features": result["features"], "embedding_clusters": clusters,
            "normalisation": {"left_out": result["left_out"], "repeated": result["repeated"],
                              "grouping": grouping.model_dump(), "prompt": prompt}}, meta
