"""Workstream agents: one prompt template, four team configurations. Run in parallel."""
from __future__ import annotations

import json

from schemas import MasterSchedule, WorkstreamPlan

TEAMS = {
    "PR": "External communications: press announcement, blog post, embargo management, media briefings, creator and influencer comms, launch advertising.",
    "Product": "Product readiness: red teaming, early access program, feature availability, staged feature rollout, integrations and partners, in-product launch moments.",
    "Regional": "Regional marketing across launch markets: localization, translation, regional availability, local publish timing, local press and social.",
    "Legal": "Legal and policy review: performance and safety claims, disclaimers, NDAs for early access, regional regulatory requirements.",
}

SYSTEM_TEMPLATE = """You are the {team} workstream agent on a cross-functional launch program.
Your remit: {remit}

Given the launch brief and master schedule, produce your team's task plan (4-6 tasks) with
owners (a role name, or 'TBD' if the brief gives none), due dates, and dependencies on task ids.
Task ids must be prefixed with '{prefix}-'. List explicit asks of other teams with needed-by dates.
Plan honestly from the brief's facts. Do not hide a conflict to make the plan look clean."""


def key(team: str) -> str:
    return "workstream:" + team


def run(llm, team: str, brief: dict, schedule: MasterSchedule) -> WorkstreamPlan:
    system = SYSTEM_TEMPLATE.format(team=team, remit=TEAMS[team], prefix=team[:3].upper())
    user = (
        "Launch brief:\n" + json.dumps(brief, indent=2)
        + "\n\nMaster schedule:\n" + schedule.model_dump_json(indent=2)
    )
    return llm.call(key(team), system, user, WorkstreamPlan)
