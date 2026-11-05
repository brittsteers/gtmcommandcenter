# Launch Command Center

**[Open the live dashboard](https://brittsteers.github.io/gtmcommandcenter/)**

A multi-agent orchestrator for model go-to-market launches. It takes a launch brief and produces a workback schedule, four cross-functional workstream plans, a cross-team risk review, and a one-page leadership status. A red team triage pipeline turns raw tester reports into scored, routed findings and feeds all of them into the risk review. A program manager approves the risks before anything final is written.

It runs two ways:

- **In the cloud:** GitHub Actions runs the agents, signs in to Claude through workload identity federation with no stored API key, and opens a pull request as the approval step. The dashboard is published on GitHub Pages. Setup is in [SETUP.md](SETUP.md).
- **Locally:** a FastAPI dashboard that streams the agents live and has an approve button.

The sample launch is fictional ("Lumen" and "Nova 2" are invented). A second brief rebuilds a real launch, Apple Intelligence, from public reporting as it stood before launch, so a run can be scored against what actually happened. See [cases/apple_intelligence.md](cases/apple_intelligence.md).

## Agent graph

```
            Launch brief                       Red team reports (optional)
                 │                                      │
             Planner            master schedule      Intake      dedupe into findings
                 │                                   Severity    critical / high / medium / low
     ┌─────┬─────┴─────┬───────┐   fan-out           Routing     owner team, next action, date
     PR  Product  Regional  Legal   tasks, asks      Digest      daily summary for leadership
     └─────┴─────┬─────┴───────┘   fan-in               │
            Risk agent  ◄───────────────────────── triaged findings
                 │              cross-plan conflicts, ranked, with evidence
                 │
      Human approval gate       PM accepts, rejects, or edits mitigations
                 │
            Synthesizer         RAG status + decisions needed
```

## Cloud flow

```
Run "1 · Plan launch"  ──►  agents plan  ──►  PR "Risk review" opened
                                                     │
                                  PM edits review.yaml, merges the PR
                                                     │
"2 · Finalize launch status"  ◄──────────────────────┘
        Synthesizer writes status, commits it
                 │
"3 · Publish dashboard"  ──►  GitHub Pages
```

## Design choices

- **Typed handoffs.** Every agent returns a pydantic-validated object (`schemas.py`) through structured outputs, retried once if it fails. Agents never pass free-form prose to each other.
- **Parallel where independent, sequential where dependent.** The workstreams only need the brief and the schedule, so they run concurrently. Risk needs all four plans, so it waits for them.
- **One template, four configs.** All workstream agents share a single prompt template (`agents/workstreams.py`). Adding a team, such as Android or Chrome, takes one line.
- **Stronger model where judgment matters.** The Risk agent uses Opus at high effort, because cross-plan reasoning is the hardest step. The rest use Sonnet.
- **The human gate is a pull request.** The review has an owner, a diff and an audit trail, and merging is the approval. A deterministic guardrail strips any rejected risk from the status, even if the model cites it anyway.
- **No secrets in CI.** GitHub issues each run a short-lived signed token, and Anthropic exchanges it for API access. The federation rule only trusts runs on `main` in this repository, so pull requests from forks can't get a token. Since GitHub's token lasts about 5 minutes and Anthropic accepts each token once, a background loop keeps a fresh one available for long runs.
- **Untrusted input is checked.** The brief path comes from a workflow input, so it's restricted to `.json` files under `data/`, and review decisions must be exactly `accept` or `reject`.
- **Observable.** Every step and handoff is written to an event log. The dashboard streams it live locally and replays it on Pages.
- **Nothing external.** The system drafts only. It sends no messages.

## Red team triage

A brief opts in with `"red_team_findings": "data/<file>.json"`. The pipeline runs alongside the planner, so it adds no wait.

- **Intake** merges duplicate reports (three testers reporting fabricated citations become one finding) and sets aside reports that aren't findings, like feature requests.
- **Severity** uses Opus, since scoring harm is a judgment call. It marks a finding as blocking when it must be fixed before launch or before a pre-launch program, such as early access, puts the model in outside hands.
- **Routing** assigns one owner team, a next action, a needed-by date and a holding line for the tester.
- **Digest** writes the leadership summary.

Two deterministic rules back up the agents: a finding the Severity agent skips is treated as high and blocking until a person triages it, and any critical or blocking finding is escalated to launch leadership, whatever the Routing agent said. The Risk agent sees every finding, so it can still catch a problem with one that wasn't escalated. A finding that only affects a post-launch release gates that release instead of blocking launch. The sample uses 12 fictional reports in [data/redteam_nova2.json](data/redteam_nova2.json). The Apple case has no red team data on purpose, since inventing findings for a real launch would plant the answers.

## Planted conflicts in the sample brief

The brief contains real tensions for the Risk agent to find:

| Risk | What the agent has to notice |
|---|---|
| APAC publishes before the embargo | 09:00 JST/AEDT is 17 to 19 hours before 09:00 PT |
| Legal review after copy lock | 10 business days from submission lands past launch minus 5 |
| Press release overclaims | "Available in the browser today" when the browser ships a week later |
| Early access before red team | Creators onboard 02-01; sign-off is 02-08 |
| Unowned task | Disclaimer localization has owner TBD |

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --port 8765     # then open http://localhost:8765
```

From the CLI, rejecting R6 at the gate:

```bash
.venv/bin/python orchestrator.py --mode replay --reject R6
```

**Replay mode** (default) needs no credentials. It plays `runs/sample_run.json`, a hand-authored set of agent outputs written to demo the flow. It is not a recorded model run. The same sample appears on the Pages dashboard, labeled as a sample.

**Live mode** calls Claude. It uses whichever credential the Anthropic SDK finds, in this order: `ANTHROPIC_API_KEY` (in your shell or a gitignored `.env`), `ANTHROPIC_AUTH_TOKEN`, an `ant auth login` profile, or workload identity federation (`ANTHROPIC_FEDERATION_RULE_ID`, `ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`, plus `ANTHROPIC_IDENTITY_TOKEN_FILE`). The code doesn't change between these.

## Files

| File | Role |
|---|---|
| `schemas.py` | Typed contracts between agents |
| `llm.py` | Live (Claude, structured outputs) and Replay backends; credential detection |
| `agents/` | Planner, workstreams, Risk, Synthesizer and red team triage prompts |
| `orchestrator.py` | The two stages around the gate, plus the local run and CLI |
| `cloud.py` | Cloud stages: plan and write the review file, then finalize from the merged review |
| `build_site.py` | Builds the static Pages dashboard from finished runs |
| `app.py` | Local FastAPI server with SSE event stream |
| `docs/index.html` | Dashboard: live mode locally, replay mode on Pages |
| `.github/workflows/` | Plan, finalize and publish workflows |
| `.github/actions/anthropic-federation/` | Shared step that signs in to Claude with GitHub's token |
| `runs/` | Every run's state, events and review decisions |

## Next

- Re-plan loop: after approval, workstream agents revise their plans based on the accepted mitigations
- Connectors: read the brief from a doc and write tasks to a tracker, with approval before each write
