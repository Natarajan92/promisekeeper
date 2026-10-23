"""Backend-only settings without secret echo or implicit mode substitution."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Literal, Mapping


@dataclass(frozen=True, slots=True)
class Settings:
    agent_mode: Literal["STUB", "LIVE"]
    model: str
    db_path: Path
    api_key: str | None = field(repr=False)

    @property
    def capability_available(self) -> bool:
        return self.agent_mode == "STUB" or bool(self.api_key)

    def safe_summary(self) -> dict:
        return {"agent_mode": self.agent_mode, "model": self.model,
                "capability_available": self.capability_available}


def load_settings(env: Mapping[str, str] | None = None, *, workspace: Path | None = None) -> Settings:
    env = os.environ if env is None else env
    root = (workspace or Path(__file__).resolve().parents[3]).resolve()
    allowed = {"PK_AGENT_MODE", "PK_OPENAI_MODEL", "PK_DB_PATH", "PK_ALLOW_LIVE_TESTS"}
    if any(name.startswith("PK_") and name not in allowed for name in env):
        raise ValueError("Unknown PK configuration field")
    mode = env.get("PK_AGENT_MODE", "STUB")
    if mode not in {"STUB", "LIVE"}:
        raise ValueError("PK_AGENT_MODE must be STUB or LIVE")
    model = env.get("PK_OPENAI_MODEL", "gpt-5.6-terra")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:\-]{0,199}", model):
        raise ValueError("PK_OPENAI_MODEL is invalid")
    db_path = Path(env.get("PK_DB_PATH", str(root / ".runtime" / "promisekeeper.sqlite")))
    if not db_path.is_absolute():
        raise ValueError("PK_DB_PATH must be absolute")
    db_path = db_path.resolve()
    if not db_path.is_relative_to(root):
        raise ValueError("PK_DB_PATH must stay inside the workspace")
    secret = env.get("OPENAI_API_KEY", "").strip() or None
    return Settings(mode, model, db_path, secret)
