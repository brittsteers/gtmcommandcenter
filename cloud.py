"""Cloud pipeline: the same agent graph, with a pull request as the human gate.

  python cloud.py plan --brief data/sample_brief.json --run-id ID --branch risk-review/ID
      Runs the planner, workstreams, and risk agent. Writes runs/ID/state.json, runs/ID/review.yaml,
      and a pull request body. GitHub Actions then opens the review PR.

  python cloud.py finalize --reviewer NAME --review-url URL
      For every run whose review was merged but has no status yet, reads the PM's decisions from
      review.yaml and runs the synthesizer.

Add --replay to either command to use the recorded sample instead of calling Claude.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml

from orchestrator import REPLAY_PATH, ROOT, stage_finalize, stage_plan
from schemas import HandoffEvent, MasterSchedule, RiskReport, WorkstreamPlan

RUNS = ROOT / "runs"
DATA = ROOT / "data"


class Recorder:
    def __init__(self, events: Optional[List[dict]] = None) -> None:
        self.events = events if events is not None else []

    def emit(self, kind: str, **kw) -> None:
        ev = HandoffEvent(ts=time.time(), kind=kind, **kw).model_dump()
        self.events.append(ev)
        print(f"[{kind:>13}] {ev.get('agent') or ''} {ev.get('summary') or ''}", flush=True)


def make_llm(replay: bool):
    from llm import LiveLLM, ReplayLLM

    if replay:
        return ReplayLLM(REPLAY_PATH, delay=0)
    return LiveLLM()


def safe_brief_path(raw: str) -> Path:
    # The path comes from a workflow input, so only allow JSON files inside data/.
    path = (ROOT / raw).resolve()
    if path.suffix != ".json" or DATA.resolve() not in path.parents or not path.exists():
        sys.exit(f"brief must be an existing .json file under data/: {raw!r}")
    return path


def review_yaml(run_id: str, report: RiskReport) -> str:
    header = (
        f"# Risk review for run {run_id}\n"
        "#\n"
        "# For each risk, set `decision` to accept or reject. You can also rewrite the mitigation.\n"
        "# Merging this pull request is the approval: the Synthesizer runs only after the merge.\n"
        "# Close the pull request without merging to discard the run.\n\n"
    )
    body = {"risks": [
        {"id": r.id, "title": r.title, "severity": r.severity, "decision": "accept",
         "owner": r.owner, "mitigation": r.mitigation}
        for r in report.risks
    ]}
    return header + yaml.safe_dump(body, sort_keys=False, width=100, allow_unicode=True)


def pr_body(run_id: str, brief: dict, report: RiskReport, branch: str) -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
    edit = f"https://github.com/{repo}/edit/{branch}/runs/{run_id}/review.yaml"
    run_url = os.environ.get("RUN_URL", "")
    lines = [
        f"The agents finished planning **{brief['launch_name']}** and found {len(report.risks)} cross-team risks. "
        "The Synthesizer is waiting on your review before it writes the leadership status.",
        "",
        "### How to review",
        f"1. [Edit `review.yaml`]({edit}) and set `decision: reject` on any risk you don't agree with. "
        "Rewrite a mitigation if you'd handle it differently.",
        "2. Merge this pull request. That merge is the approval, and it starts the Synthesizer.",
        "3. Close without merging to discard the run.",
        "",
        "### Risks",
        "",
        "| ID | Severity | Risk | Teams | Proposed owner |",
        "|---|---|---|---|---|",
    ]
    for r in report.risks:
        lines.append(f"| {r.id} | {r.severity} | {r.title} | {', '.join(r.teams)} | {r.owner} |")
    lines += ["", "<details><summary>Evidence and mitigations</summary>", ""]
    for r in report.risks:
        lines += [f"**{r.id} · {r.title}**", "", f"- Evidence: {r.evidence}", f"- Mitigation: {r.mitigation}", ""]
    lines += ["</details>", ""]
    if run_url:
        lines.append(f"Agent run: {run_url}")
    return "\n".join(lines)


def cmd_plan(args) -> None:
    brief = json.loads(safe_brief_path(args.brief).read_text())
    llm = make_llm(args.replay)
    if args.replay:
        brief = llm.brief
    rec = Recorder()
    schedule, plans, report = stage_plan(llm, brief, rec.emit)
    rec.emit("gate_open", summary="Risk review pull request opened")

    out = RUNS / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    state = {
        "run_id": args.run_id,
        "source": "sample" if args.replay else "live",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "brief": brief,
        "schedule": schedule.model_dump(),
        "plans": [p.model_dump() for p in plans],
        "risks": report.model_dump(),
        "status": None,
        "events": rec.events,
        "github_run_url": os.environ.get("RUN_URL"),
    }
    (out / "state.json").write_text(json.dumps(state, indent=2))
    (out / "review.yaml").write_text(review_yaml(args.run_id, report))
    if args.pr_body:
        Path(args.pr_body).write_text(pr_body(args.run_id, brief, report, args.branch))
    print(f"wrote {out}")


def read_decisions(path: Path, report: RiskReport) -> dict:
    doc = yaml.safe_load(path.read_text()) or {}
    by_id = {r.id: r for r in report.risks}
    decisions = {}
    for item in doc.get("risks", []):
        rid = item.get("id")
        if rid not in by_id:
            sys.exit(f"{path}: unknown risk id {rid!r}")
        decision = str(item.get("decision", "")).strip().lower()
        if decision not in ("accept", "reject"):
            sys.exit(f"{path}: {rid} decision must be accept or reject, got {item.get('decision')!r}")
        mitigation = (item.get("mitigation") or "").strip()
        decisions[rid] = {
            "accepted": decision == "accept",
            "mitigation": mitigation if mitigation and mitigation != by_id[rid].mitigation.strip() else None,
        }
    missing = set(by_id) - set(decisions)
    if missing:
        sys.exit(f"{path}: no decision for {', '.join(sorted(missing))}")
    return decisions


def pending_runs() -> List[Path]:
    """Runs whose review was merged but that have no status yet."""
    return [d for d in sorted(RUNS.iterdir()) if (d / "review.yaml").exists() and (d / "state.json").exists()
            and json.loads((d / "state.json").read_text()).get("status") is None]


def cmd_pending(args) -> None:
    print(len(pending_runs()))


def cmd_finalize(args) -> None:
    pending = pending_runs()
    if not pending:
        print("no runs waiting on finalize")
        return
    llm = make_llm(args.replay)
    for d in pending:
        state = json.loads((d / "state.json").read_text())
        report = RiskReport.model_validate(state["risks"])
        decisions = read_decisions(d / "review.yaml", report)
        rec = Recorder(state["events"])
        status = stage_finalize(
            llm, state["brief"], MasterSchedule.model_validate(state["schedule"]),
            [WorkstreamPlan.model_validate(p) for p in state["plans"]], report, decisions, rec.emit,
            reviewer=args.reviewer or None, review_url=args.review_url or None,
        )
        state["status"] = status.model_dump()
        (d / "state.json").write_text(json.dumps(state, indent=2))
        print(f"finalized {d.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--brief", default="data/sample_brief.json")
    p.add_argument("--run-id", required=True)
    p.add_argument("--branch", default="main")
    p.add_argument("--pr-body")
    p.add_argument("--replay", action="store_true")
    f = sub.add_parser("finalize")
    f.add_argument("--reviewer", default="")
    f.add_argument("--review-url", default="")
    f.add_argument("--replay", action="store_true")
    sub.add_parser("pending", help="print how many reviewed runs are waiting on finalize")
    args = ap.parse_args()
    {"plan": cmd_plan, "finalize": cmd_finalize, "pending": cmd_pending}[args.cmd](args)


if __name__ == "__main__":
    main()
