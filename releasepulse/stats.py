"""Proportions with uncertainty.

A feature's complaint rate in a release is the share of that release's
feedback items that complain about it. Rates come with Wilson score intervals
(Wilson 1927), which behave well for small counts and rates near zero, where
the textbook normal interval breaks down. Changes between releases use
Newcombe's hybrid score interval for a difference of two independent
proportions (Newcombe 1998, method 10), built from the two Wilson intervals.
"""

from __future__ import annotations

import math

Z95 = 1.959963984540054


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def newcombe_diff(k1: int, n1: int, k0: int, n0: int, z: float = Z95) -> tuple[float, float, float]:
    """Difference p1 - p0 with its 95% hybrid score interval: (diff, low, high)."""
    p1 = k1 / n1 if n1 else 0.0
    p0 = k0 / n0 if n0 else 0.0
    l1, u1 = wilson(k1, n1, z)
    l0, u0 = wilson(k0, n0, z)
    d = p1 - p0
    low = d - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    high = d + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    return d, low, high


def rate(k: int, n: int) -> dict:
    low, high = wilson(k, n)
    return {"count": k, "n": n, "rate": k / n if n else 0.0, "low": low, "high": high}
