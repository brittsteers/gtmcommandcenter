"""Builds the static dashboard for GitHub Pages: docs/ plus a data/ folder of finished runs.

Standard library only, so the Pages workflow needs no installs.
  python build_site.py --out _site
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_site")
    out = Path(ap.parse_args().out)

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "docs", out)
    (out / "data" / "runs").mkdir(parents=True)
    (out / ".nojekyll").write_text("")

    index = []
    for state_path in sorted((ROOT / "runs").glob("*/state.json")):
        state = json.loads(state_path.read_text())
        if not state.get("status"):
            continue  # still in review, or discarded
        run_id = state["run_id"]
        index.append({
            "id": run_id,
            "launch_name": state["brief"]["launch_name"],
            "created_at": state["created_at"],
            "source": state["source"],
            "overall_rag": state["status"]["overall_rag"],
        })
        (out / "data" / "runs" / f"{run_id}.json").write_text(json.dumps({
            "run_id": run_id,
            "source": state["source"],
            "created_at": state["created_at"],
            "github_run_url": state.get("github_run_url"),
            "events": state["events"],
        }))

    # Newest live runs first; the sample goes last.
    live =sorted([r for r in index if r["source"] == "live"], key=lambda r: r["created_at"], reverse=True)
    index = live + [r for r in index if r["source"] != "live"]
    (out / "data" / "runs.json").write_text(json.dumps(index, indent=2))
    print(f"built {out} with {len(index)} runs")


if __name__ == "__main__":
    main()
