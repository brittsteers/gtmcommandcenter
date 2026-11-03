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


class HandoffEvent(BaseModel):
    ts: float
    kind: str
    agent: Optional[str] = None
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    summary: str = ""
    key: Optional[str] = None
    data: Optional[dict] = None
