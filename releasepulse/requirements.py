"""Export the top issues as candidate requirements for ElicitSense's register.

The LLM only words each requirement (statement, type, rationale) from the
evidence it is shown. Which issues are exported, their evidence, status and
uncertainty are decided here: the top rows of the prioritisation table with
at least THIN complaints, the verified quotes behind them, status "proposed".
The output has the shape of an ElicitSense register (`requirements` with id,
type, statement, rationale, acceptance, stakeholder, status, evidence,
quality, uncertainty, history ...), so it can be loaded next to one built from
elicitation meetings and confirmed there.
"""

from __future__ import annotations

import copy
from typing import Literal

from pydantic import BaseModel

from . import quality
from .llm import complete_json
from .prioritise import THIN

TOP = 5
WIDE_INTERVAL = 0.15

SYSTEM = """You turn evidence from user feedback about one software product into candidate \
requirements for a requirements register. For each issue you get the feature, how often it \
is raised and verbatim quotes from users. Write one requirement per issue.

Rules:
- statement: one plain-English sentence of the form "The app shall ...", stating what users \
need, supported by the quotes. Do not invent numbers, limits or causes the quotes do not give.
- type: "functional" for behaviour the product must have; "non_functional" for performance, \
reliability, usability and other quality attributes; "constraint" for limits from outside \
the product.
- rationale: one sentence summarising the evidence (how many items, which releases).
- Do not describe or judge anyone's emotions."""

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["requirements"],
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["issue_id", "statement", "type", "rationale"],
                "properties": {
                    "issue_id": {"type": "string"},
                    "statement": {"type": "string"},
                    "type": {"type": "string", "enum": ["functional", "non_functional", "constraint"]},
                    "rationale": {"type": "string"},
                },
            },
        },
    },
}


class Worded(BaseModel):
    issue_id: str
    statement: str
    type: Literal["functional", "non_functional", "constraint"]
    rationale: str


class Wording(BaseModel):
    requirements: list[Worded]


def top_issues(tbl: dict, top: int = TOP) -> list[dict]:
    return [r for r in tbl["rows"] if r["complaints"]["count"] >= THIN][:top]


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def render_prompt(issues: list[dict], tbl: dict, product: str | None) -> str:
    lines = [f"Product: {product}", ""] if product else []
    lines.append(f"Feedback window: releases {', '.join(tbl['window'])} ({tbl['volume']} items).")
    for r in issues:
        c = r["complaints"]
        status = r["status"] + (f" since {r['since']}" if r["since"] else "")
        lines += ["", f"[{r['feature']}] feature: {r['name']}; {c['count']} of {c['n']} items complain "
                      f"({_pct(c['rate'])}, 95% interval {_pct(c['low'])}-{_pct(c['high'])}); status: {status}"]
        lines += [f'    {q["source"]}, release {q["release"]}: "{q["quote"]}"' for q in r["evidence"]]
    return "\n".join(lines)


def schema_for(issue_ids: list[str]) -> dict:
    schema = copy.deepcopy(SCHEMA)
    schema["properties"]["requirements"]["items"]["properties"]["issue_id"]["enum"] = issue_ids
    return schema


def word(issues: list[dict], tbl: dict, spec: str, product: str | None = None) -> tuple[Wording, dict]:
    text, meta = complete_json(SYSTEM, render_prompt(issues, tbl, product), schema_for([r["feature"] for r in issues]),
                               "candidate_requirements", spec)
    return Wording.model_validate_json(text), meta


def _uncertainty(row: dict) -> dict:
    c = row["complaints"]
    cues = []
    if c["count"] < 2 * THIN:
        cues.append({"kind": "few_items", "detail": f"only {c['count']} items complain"})
    if c["high"] - c["low"] > WIDE_INTERVAL:
        cues.append({"kind": "wide_interval",
                     "detail": f"95% interval {_pct(c['low'])}-{_pct(c['high'])} is wider than {_pct(WIDE_INTERVAL)}"})
    return {"flag": bool(cues), "label": "needs confirmation" if cues else None, "cues": cues}


def to_register(issues: list[dict], wording: Wording | None, tbl: dict, app_id: str, llm_meta: dict | None) -> dict:
    """ElicitSense register shape. Requirements the model did not word are left out
    and listed under `not_worded`."""
    worded = {w.issue_id: w for w in (wording.requirements if wording else [])}
    source_label = f"releasepulse:{app_id}:{tbl['window'][0]}-{tbl['window'][-1]}"
    requirements, not_worded = [], []
    for r in issues:
        w = worded.get(r["feature"])
        if w is None:
            not_worded.append(r["feature"])
            continue
        rid = f"REQ-RP-{app_id}-{len(requirements) + 1:03d}"
        evidence = [{"meeting": f"release-{q['release']}", "segment_id": q["item_id"], "start": None, "end": None,
                     "speaker": q["source"], "quote": q["quote"], "date": q["date"]} for q in r["evidence"]]
        requirements.append({
            "id": rid,
            "type": w.type,
            "statement": w.statement,
            "rationale": w.rationale,
            "acceptance": [],
            "stakeholder": "app users (feedback)",
            "status": "proposed",
            "evidence": evidence,
            "dropped_evidence": [],
            "quality": quality.check(w.statement, w.type, []),
            "uncertainty": _uncertainty(r),
            "meeting": source_label,
            "history": [{"meeting": source_label, "change": "raised as proposed from user feedback"}],
            "merged_from": [],
            "merged_into": None,
            "superseded_by": None,
            "releasepulse": {"feature": r["feature"], "feature_name": r["name"], "rank": r["rank"],
                             "complaints": r["complaints"], "status": r["status"], "since": r["since"],
                             "window": tbl["window"]},
        })
    return {
        "meetings": [source_label],
        "active": [r["id"] for r in requirements],
        "open_conflicts": [],
        "requirements": requirements,
        "relations": [],
        "dropped_links": [],
        "not_worded": not_worded,
        "llm": [llm_meta] if llm_meta else [],
    }
