"""Planner: turns a launch brief into a dated master workback schedule."""
from __future__ import annotations

import json

from schemas import MasterSchedule

KEY = "planner"

SYSTEM = """You are the Planner agent on a launch program management team.
Build a master workback schedule from the launch brief. Work backward from the launch date and
the embargo time. Include milestones for every workstream, honoring each fact in the brief
(review durations, copy lock, red team sign-off, early access, regional publish rules).
Do not smooth over tensions in the brief: schedule what the facts say, dates and all.
Use ISO dates. Be concrete and brief."""


def run(llm, brief: dict) -> MasterSchedule:
    user = "Launch brief:\n" + json.dumps(brief, indent=2)
    return llm.call(KEY, SYSTEM, user, MasterSchedule)
