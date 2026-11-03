"""Risk agent: reads every plan together and finds what no single team can see."""
from __future__ import annotations

import json
from typing import List

from schemas import MasterSchedule, RiskReport, WorkstreamPlan

KEY = "risk"

SYSTEM = """You are the Risk agent, the program manager's cross-workstream reviewer.
Read all workstream plans against the master schedule and the brief. Find:
- timing conflicts across teams or time zones (check embargo time against each region's local publish time)
- review durations that do not fit the schedule
- claims in drafts that depend on work scheduled after launch
- sequencing problems (programs starting before their gating sign-off)
- tasks with no owner, and asks with no matching task

For each risk give severity, the teams involved, evidence that cites specific dates/tasks, a concrete
mitigation, and a proposed owner. Rank most severe first. Only report risks you can support with evidence.
Ids: R1, R2, ..."""


def run(llm, brief: dict, schedule: MasterSchedule, plans: List[WorkstreamPlan]) -> RiskReport:
    user = (
        "Brief:\n" + json.dumps(brief, indent=2)
        + "\n\nSchedule:\n" + schedule.model_dump_json(indent=2)
        + "\n\nWorkstream plans:\n" + json.dumps([p.model_dump() for p in plans], indent=2)
    )
    return llm.call(KEY, SYSTEM, user, RiskReport, strong=True)
