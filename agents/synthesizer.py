"""Synthesizer: writes the one-page status after the human approval gate."""
from __future__ import annotations

import json
from typing import List

from schemas import MasterSchedule, Risk, Status, WorkstreamPlan

KEY = "synthesizer"

SYSTEM = """You are the Synthesizer agent. Write a one-page launch status for marketing leadership.
Give one headline sentence, an overall RAG, a RAG and one-line summary per workstream, the ids of the
top risks, and the specific decisions leadership needs to make. Only treat risks the program manager
ACCEPTED as live risks. If any were rejected, note that in rejected_risk_note. Be plain and direct."""


def run(llm, brief: dict, schedule: MasterSchedule, plans: List[WorkstreamPlan],
        accepted: List[Risk], rejected: List[Risk]) -> Status:
    user = (
        "Brief:\n" + json.dumps(brief, indent=2)
        + "\n\nSchedule:\n" + schedule.model_dump_json(indent=2)
        + "\n\nPlans:\n" + json.dumps([p.model_dump() for p in plans], indent=2)
        + "\n\nACCEPTED risks:\n" + json.dumps([r.model_dump() for r in accepted], indent=2)
        + "\n\nREJECTED risks:\n" + json.dumps([r.model_dump() for r in rejected], indent=2)
    )
    return llm.call(KEY, SYSTEM, user, Status)
