"""Typed contracts passed between agents. Agents hand off validated data, not prose."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["high", "medium", "low"]
RAG = Literal["red", "yellow", "green"]


class Milestone(BaseModel):
    name: str
    date: str = Field(description="ISO date YYYY-MM-DD")
    owner_team: str
    note: str = ""


class MasterSchedule(BaseModel):
    launch_date: str
    embargo_lifts: str = Field(description="ISO datetime with offset, e.g. 2027-03-10T09:00:00-08:00")
    milestones: List[Milestone]


class Task(BaseModel):
    id: str
    title: str
    due: str = Field(description="ISO date YYYY-MM-DD")
    owner: str = Field(description="Named role or 'TBD' if unassigned")
    depends_on: List[str] = Field(default_factory=list)


class Ask(BaseModel):
    to_team: str
    request: str
    needed_by: str


class WorkstreamPlan(BaseModel):
    team: str
    tasks: List[Task]
    asks: List[Ask] = Field(default_factory=list)


class Risk(BaseModel):
    id: str
    title: str
    severity: Severity
    teams: List[str]
    evidence: str
    mitigation: str
    owner: str


class RiskReport(BaseModel):
    risks: List[Risk]


class WorkstreamStatus(BaseModel):
    team: str
    rag: RAG
    summary: str


class Status(BaseModel):
    headline: str
    overall_rag: RAG
    workstreams: List[WorkstreamStatus]
    top_risk_ids: List[str]
    decisions_needed: List[str]
    rejected_risk_note: Optional[str] = None


# --- Red team triage --------------------------------------------------------------------------

FindingSeverity = Literal["critical", "high", "medium", "low"]
Harm = Literal["safety", "factual accuracy", "privacy and security", "fairness", "claims and IP", "quality"]
Team = Literal["Product", "Legal", "PR", "Regional"]


class Finding(BaseModel):
    id: str = Field(description="F1, F2, ...")
    feature: str
    summary: str
    observed: str = Field(description="What the model did, as close to the tester's words as possible")
    reported_by: List[str]
    first_reported: str = Field(description="ISO date YYYY-MM-DD")
    source_ids: List[str] = Field(description="Raw report ids merged into this finding")


class FindingList(BaseModel):
    findings: List[Finding]
    not_findings: List[str] = Field(default_factory=list,
                                    description="Raw report ids that are not red team findings, with a short reason each")


class FindingScore(BaseModel):
    finding_id: str
    severity: FindingSeverity
    harm: Harm
    blocks_launch: bool
    gates_later_release: str = Field(default="", description="The post-launch release this finding must clear, or empty")
    rationale: str


class ScoreList(BaseModel):
    scores: List[FindingScore]


class FindingRoute(BaseModel):
    finding_id: str
    owner_team: Team
    action: str
    suggested_response: str = Field(description="Holding line or reply to the tester")
    needed_by: str = Field(description="ISO date YYYY-MM-DD")
    escalate: bool


class RouteList(BaseModel):
    routes: List[FindingRoute]


class TriageDigest(BaseModel):
    headline: str
    launch_blockers: List[str] = Field(description="Finding ids")
    notes: List[str]
    decisions_needed: List[str]


class HandoffEvent(BaseModel):
    ts: float
    kind: str
    agent: Optional[str] = None
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    summary: str = ""
    key: Optional[str] = None
    data: Optional[dict] = None
