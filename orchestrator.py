"""Runs the agent graph: planner -> 4 workstreams in parallel -> risk -> human gate -> synthesizer.

The graph is split into two stages around the human gate so the gate can be a live button (local
dashboard) or a pull request (GitHub Actions, see cloud.py). Every handoff is emitted as an event.
Nothing is ever sent externally.
"""
from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

from agents import planner, risk, synthesizer, workstreams
from llm import load_env
from schemas import HandoffEvent, MasterSchedule, RiskReport, Status, WorkstreamPlan

load_env()

ROOT = Path(__file__).parent
BRIEF_PATH = ROOT / "data" / "sample_brief.json"
REPLAY_PATH = ROOT / "runs" / "sample_run.json"

Emit = Callable[..., None]


def stage_plan(llm, brief: dict, emit: Emit) -> Tuple[MasterSchedule, List[WorkstreamPlan], RiskReport]:
    """Everything before the human gate."""
    emit("run_start", summary=brief["launch_name"], data={"brief": brief})

    emit("agent_start", agent="Planner", from_agent="orchestrator", to_agent="Planner")
    schedule = planner.run(llm, brief)
    emit("agent_done", agent="Planner", key="schedule", data=schedule.model_dump(),
         summary=f"{len(schedule.milestones)} milestones, launch {schedule.launch_date}")

    for team in workstreams.TEAMS:
        emit("handoff", from_agent="Planner", to_agent=f"{team} agent", summary="brief + master schedule")

    def one(team):
        emit("agent_start", agent=f"{team} agent")
        plan = workstreams.run(llm, team, brief, schedule)
        emit("agent_done", agent=f"{team} agent", key=f"plan:{team}", data=plan.model_dump(),
             summary=f"{len(plan.tasks)} tasks, {len(plan.asks)} asks of other teams")
        return plan

    with ThreadPoolExecutor(max_workers=len(workstreams.TEAMS)) as pool:
        plans = list(pool.map(one, workstreams.TEAMS))

    emit("handoff", from_agent="4 workstream agents", to_agent="Risk agent",
         summary=f"{sum(len(p.tasks) for p in plans)} tasks across {len(plans)} plans")
    emit("agent_start", agent="Risk agent", from_agent="workstreams", to_agent="Risk agent")
    report = risk.run(llm, brief, schedule, plans)
    highs = sum(r.severity == "high" for r in report.risks)
    emit("agent_done", agent="Risk agent", key="risks", data=report.model_dump(),
         summary=f"{len(report.risks)} risks ({highs} high)")
    return schedule, plans, report


def stage_finalize(llm, brief: dict, schedule: MasterSchedule, plans: List[WorkstreamPlan],
                   report: RiskReport, decisions: dict, emit: Emit,
                   reviewer: Optional[str] = None, review_url: Optional[str] = None) -> Status:
    """Everything after the human gate. decisions: {risk_id: {"accepted": bool, "mitigation": str|None}}"""
    accepted, rejected = [], []
    for r in report.risks:
        d = decisions.get(r.id, {"accepted": True})
        if d.get("mitigation"):
            r = r.model_copy(update={"mitigation": d["mitigation"]})
        (accepted if d.get("accepted", True) else rejected).append(r)
    emit("gate_closed", summary=f"{len(accepted)} accepted, {len(rejected)} rejected"
         + (f" by {reviewer}" if reviewer else ""),
         data={"accepted": [r.id for r in accepted], "rejected": [r.id for r in rejected],
               "decisions": decisions, "reviewer": reviewer, "review_url": review_url})

    emit("handoff", from_agent="Program manager", to_agent="Synthesizer", summary="plans + approved risks")
    emit("agent_start", agent="Synthesizer", from_agent="Program manager", to_agent="Synthesizer")
    status = synthesizer.run(llm, brief, schedule, plans, accepted, rejected)
    # Deterministic guardrail: the status may only cite risks the human accepted.
    ok = {r.id for r in accepted}
    status.top_risk_ids = [i for i in status.top_risk_ids if i in ok]
    if rejected and not status.rejected_risk_note:
        status.rejected_risk_note = "PM rejected: " + ", ".join(f"{r.id} ({r.title})" for r in rejected)
    if not rejected:
        status.rejected_risk_note = None
    emit("agent_done", agent="Synthesizer", key="status", data=status.model_dump(),
         summary=f"Overall {status.overall_rag.upper()}")
    emit("run_done", summary="Status ready. Nothing was sent externally.")
    return status


class Run:
    """A local run whose human gate is the dashboard's approve button."""

    def __init__(self, llm, brief: dict) -> None:
        self.llm = llm
        self.brief = brief
        self.events: List[HandoffEvent] = []
        self.cond = threading.Condition()
        self.gate = threading.Event()
        self.decisions: dict = {}
        self.state = "idle"

    def emit(self, kind: str, **kw) -> None:
        with self.cond:
            self.events.append(HandoffEvent(ts=time.time(), kind=kind, **kw))
            self.cond.notify_all()

    def wait_events(self, after: int, timeout: float = 15.0) -> List[HandoffEvent]:
        with self.cond:
            if len(self.events) <= after:
                self.cond.wait(timeout)
            return self.events[after:]

    def approve(self, decisions: dict) -> None:
        self.decisions = decisions
        self.gate.set()

    def execute(self) -> None:
        try:
            self.state = "running"
            schedule, plans, report = stage_plan(self.llm, self.brief, self.emit)
            self.state = "awaiting_approval"
            self.emit("gate_open", summary="Program manager review required before status is written")
            self.gate.wait()
            self.state = "running"
            stage_finalize(self.llm, self.brief, schedule, plans, report, self.decisions, self.emit)
            self.state = "done"
        except Exception as e:  # surface failures in the dashboard instead of hanging
            self.state = "error"
            self.emit("error", summary=f"{type(e).__name__}: {e}")


def make_llm(mode: str):
    from llm import LiveLLM, ReplayLLM

    if mode == "live":
        return LiveLLM(), json.loads(BRIEF_PATH.read_text())
    replay = ReplayLLM(REPLAY_PATH)
    return replay, replay.brief


def main(argv: Optional[Iterable[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="Run the launch orchestrator from the CLI.")
    ap.add_argument("--mode", choices=["live", "replay"], default="replay")
    ap.add_argument("--save", help="Path to save a live run for replay")
    ap.add_argument("--reject", default="", help="Comma-separated risk ids to reject at the gate")
    args = ap.parse_args(argv)

    llm, brief = make_llm(args.mode)
    if args.mode == "replay":
        llm.delay = 0
    run = Run(llm, brief)
    t = threading.Thread(target=run.execute, daemon=True)
    t.start()

    seen = 0
    while t.is_alive() or seen < len(run.events):
        for ev in run.wait_events(seen, timeout=0.5):
            seen += 1
            who = ev.agent or (f"{ev.from_agent} -> {ev.to_agent}" if ev.from_agent else "")
            print(f"[{ev.kind:>13}] {who:<32} {ev.summary}")
            if ev.kind == "gate_open":
                rejected = {x.strip() for x in args.reject.split(",") if x.strip()}
                risks = run.events[-2].data["risks"]
                run.approve({r["id"]: {"accepted": r["id"] not in rejected} for r in risks})

    if args.save and args.mode == "live":
        llm.save(Path(args.save), brief)
        print(f"saved run to {args.save}")


if __name__ == "__main__":
    main()
