"""LLM backends. Live calls Claude with a forced tool call for typed output; Replay serves a recorded run."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def load_env(path: Path = Path(__file__).parent / ".env") -> None:
    """Read KEY=value lines from a local .env (gitignored) without overriding the real environment."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if v:  # an empty ANTHROPIC_API_KEY= would outrank federation and profiles
                os.environ.setdefault(k.strip(), v)


WIF_VARS = ("ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_ORGANIZATION_ID", "ANTHROPIC_SERVICE_ACCOUNT_ID")


def credential_source() -> Optional[str]:
    """Best-effort guess at which credential the SDK will use, mirroring its resolution order."""
    env = os.environ
    if env.get("ANTHROPIC_API_KEY"):
        return "API key"
    if env.get("ANTHROPIC_AUTH_TOKEN"):
        return "auth token"
    if env.get("ANTHROPIC_PROFILE"):
        return f"profile '{env['ANTHROPIC_PROFILE']}'"
    if all(env.get(v) for v in WIF_VARS) and (env.get("ANTHROPIC_IDENTITY_TOKEN_FILE") or env.get("ANTHROPIC_IDENTITY_TOKEN")):
        return "workload identity federation"
    if (Path.home() / ".config" / "anthropic").exists():
        return "ant CLI profile"
    return None

FAST_MODEL = "claude-sonnet-5-5"
STRONG_MODEL = "claude-opus-5-5"


class LiveLLM:
    def __init__(self) -> None:
        import anthropic  # imported lazily so replay works without a key

        self.client = anthropic.Anthropic()
        self.outputs: Dict[str, dict] = {}

    def call(self, key: str, system: str, user: str, model_cls: Type[T], strong: bool = False) -> T:
        # Structured outputs constrain the response to the pydantic schema. (Forced tool_choice
        # is rejected by the current Opus and Sonnet models.)
        last_err = None
        for _ in range(2):
            resp = self.client.messages.parse(
                model=STRONG_MODEL if strong else FAST_MODEL,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": user}],
                output_format=model_cls,
                output_config={"effort": "high" if strong else "medium"},
            )
            if resp.stop_reason == "refusal":
                raise RuntimeError(f"{key}: model declined the request")
            if resp.parsed_output is not None:
                self.outputs[key] = resp.parsed_output.model_dump(mode="json")
                return resp.parsed_output
            last_err = f"stop_reason={resp.stop_reason}"  # e.g. max_tokens; retry once
        raise RuntimeError(f"{key}: no valid structured output after 2 tries ({last_err})")

    def save(self, path: Path, brief: dict) -> None:
        path.write_text(json.dumps({"brief": brief, "outputs": self.outputs}, indent=2))


class ReplayLLM:
    def __init__(self, path: Path, delay: float = 1.4) -> None:
        self.recorded = json.loads(path.read_text())
        self.delay = delay

    @property
    def brief(self) -> dict:
        return self.recorded["brief"]

    def call(self, key: str, system: str, user: str, model_cls: Type[T], strong: bool = False) -> T:
        time.sleep(self.delay)
        return model_cls.model_validate(self.recorded["outputs"][key])
