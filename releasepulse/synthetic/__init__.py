"""Synthetic feedback sets with planted ground truth (fictional apps)."""

from . import kestrel, tallynote

APPS = {"tallynote": tallynote.SPEC, "kestrel": kestrel.SPEC}
DEV, HELD_OUT = "tallynote", "kestrel"
