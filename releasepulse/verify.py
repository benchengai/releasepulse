"""Check that every cited quote actually appears in its item, and find where.

Matching ignores case, punctuation and spacing, and tolerates tiny differences
(a dropped apostrophe, "log-in" against "log in") through a fuzzy window match.
`locate` returns the character span in the original text, which the evaluation
uses to pair extracted aspects with the planted mentions.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

FUZZY_THRESHOLD = 0.9

_KEEP = re.compile(r"[a-z0-9$%']")


def _normalise_with_map(text: str) -> tuple[str, list[int]]:
    """Lowercased text with punctuation turned into single spaces, plus the
    original index of every output character."""
    out, index = [], []
    pending_space = False
    for i, ch in enumerate(text.lower().replace("’", "'").replace("‘", "'")):
        if _KEEP.match(ch):
            if pending_space and out:
                out.append(" ")
                index.append(i)
            out.append(ch)
            index.append(i)
            pending_space = False
        else:
            pending_space = True
    return "".join(out), index


def normalise(text: str) -> str:
    return _normalise_with_map(text)[0]


def locate(quote: str, text: str) -> tuple[int, int] | None:
    """(start, end) of the quote in `text`, or None if it does not appear."""
    q = normalise(quote)
    s, index = _normalise_with_map(text)
    if not q or not s:
        return None
    pos = s.find(q)
    if pos >= 0:
        return index[pos], index[pos + len(q) - 1] + 1
    qw = q.split()
    starts = [0] + [m.end() for m in re.finditer(" ", s)]
    words = s.split()
    n = len(qw)
    best, best_ratio = None, FUZZY_THRESHOLD
    if n > len(words):
        return (0, len(text)) if SequenceMatcher(None, q, s).ratio() >= FUZZY_THRESHOLD else None
    for i in range(len(words) - n + 1):
        window = " ".join(words[i:i + n])
        ratio = SequenceMatcher(None, q, window).ratio()
        if ratio >= best_ratio:
            best, best_ratio = (starts[i], starts[i] + len(window)), ratio
    if best is None:
        return None
    return index[best[0]], index[best[1] - 1] + 1


def quote_matches(quote: str, text: str) -> bool:
    return locate(quote, text) is not None
