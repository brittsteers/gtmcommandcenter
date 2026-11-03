"""Local dashboard server. One run at a time; events stream to the browser over SSE."""
from __future__ import annotations

import json
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

from llm import credential_source
from orchestrator import Run, make_llm

app = FastAPI(title="Launch Command Center")
WEB = Path(__file__).parent / "docs"
current: dict = {"run": None}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/config")
def config():
    src = credential_source()
    return {"live_available": src is not None, "credential_source": src}


@app.post("/api/run")
def start(mode: str = "replay"):
    if mode not in ("replay", "live"):
        raise HTTPException(400, "mode must be replay or live")
    if mode == "live" and not credential_source():
        raise HTTPException(400, "No Anthropic credentials found; use replay mode")
    prev = current["run"]
    if prev and prev.state in ("running", "awaiting_approval"):
        raise HTTPException(409, "a run is already in progress")
    llm, brief = make_llm(mode)
    run = Run(llm, brief)
    current["run"] = run
    threading.Thread(target=run.execute, daemon=True).start()
    return {"ok": True, "mode": mode}


@app.post("/api/approve")
async def approve(request: Request):
    run = current["run"]
    if not run or run.state != "awaiting_approval":
        raise HTTPException(409, "no run is waiting for approval")
    run.approve(await request.json())
    return {"ok": True}


@app.get("/api/events")
def events():
    run = current["run"]
    if not run:
        raise HTTPException(404, "no run started")

    def stream():
        seen = 0
        while True:
            batch = run.wait_events(seen)
            for ev in batch:
                seen += 1
                yield f"data: {json.dumps(ev.model_dump())}\n\n"
            if not batch:
                yield ": keepalive\n\n"
            if run.state in ("done", "error") and seen >= len(run.events):
                return

    return StreamingResponse(stream(), media_type="text/event-stream")
