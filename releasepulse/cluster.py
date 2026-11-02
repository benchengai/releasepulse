"""Group extracted aspect names into features, with embeddings.

Models name the same feature in different words ("sign in", "login",
"account login"). Each distinct aspect name is embedded with
text-embedding-3-small and the names are merged by average-linkage
agglomerative clustering on cosine similarity until no two clusters are
more similar than the threshold. A feature is named after its most
mentioned member, so names stay in the users' and the model's own words.

The threshold was chosen on the development set only (see docs/eval).
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from .llm import EMBEDDING_MODEL, EmbeddingCache, embed

THRESHOLD = 0.55


def agglomerate(vectors: np.ndarray, threshold: float) -> list[list[int]]:
    """Average-linkage clustering of unit vectors; merge while the best pair's
    mean cosine similarity is at least `threshold`."""
    n = len(vectors)
    if n == 0:
        return []
    sim = vectors @ vectors.T
    np.fill_diagonal(sim, -np.inf)
    sizes = np.ones(n)
    active = np.ones(n, dtype=bool)
    members = [[i] for i in range(n)]
    while active.sum() > 1:
        masked = np.where(active[:, None] & active[None, :], sim, -np.inf)
        a, b = np.unravel_index(np.argmax(masked), masked.shape)
        if masked[a, b] < threshold:
            break
        a, b = min(a, b), max(a, b)
        # Lance-Williams update for average linkage.
        merged = (sizes[a] * sim[a] + sizes[b] * sim[b]) / (sizes[a] + sizes[b])
        sim[a, :], sim[:, a] = merged, merged
        sim[a, a] = -np.inf
        sim[b, :], sim[:, b] = -np.inf, -np.inf
        sizes[a] += sizes[b]
        active[b] = False
        members[a] += members[b]
        members[b] = []
    return [sorted(m) for m in members if m]


def _name(counts: Counter) -> str:
    return sorted(counts.items(), key=lambda kv: (-kv[1], len(kv[0]), kv[0]))[0][0]


def cluster_aspects(aspects: list[dict], threshold: float = THRESHOLD, cache: EmbeddingCache | None = None,
                    spec: str = EMBEDDING_MODEL) -> dict:
    """Assign `feature` to every aspect in place; return the features and the embedding call."""
    label_counts = Counter(a["aspect"] for a in aspects)
    labels = sorted(label_counts)
    if not labels:
        return {"features": [], "threshold": threshold, "embedding": None}
    vectors, meta = embed(labels, spec, cache)
    groups = agglomerate(vectors, threshold)
    clusters = []
    for g in groups:
        counts = Counter({labels[i]: label_counts[labels[i]] for i in g})
        clusters.append({"labels": dict(counts.most_common()), "mentions": sum(counts.values()),
                         "name": _name(counts)})
    clusters.sort(key=lambda c: (-c["mentions"], c["name"]))
    label_to_feature = {}
    for k, c in enumerate(clusters, start=1):
        c["id"] = f"F{k:02d}"
        for label in c["labels"]:
            label_to_feature[label] = c["id"]
    for a in aspects:
        a["feature"] = label_to_feature[a["aspect"]]
    return {"features": [{"id": c["id"], "name": c["name"], "mentions": c["mentions"], "labels": c["labels"]}
                         for c in clusters],
            "threshold": threshold, "embedding": {"step": "embed", **meta}}
