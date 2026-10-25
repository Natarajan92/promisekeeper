"""Backend-only settings without secret echo or implicit mode substitution."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Literal, Mapping


DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/gpt-oss-120b"
AGENT_ROLES = ("Supervisor", "Extractor", "Communicator", "Tone Reviewer", "Briefing", "Memory")
# Least privilege: AI agents only read and propose. Code and the owner make every change.
CAN_CHANGE = {"Supervisor": ("which case is investigated next",), "Extractor": (), "Communicator": (), "Tone Reviewer": (), "Briefing": (), "Memory": ("client payment notes",)}
MODEL_PATTERN = r"[A-Za-z0-9][A-Za-z0-9_./:\-]{0,199}"


def parse_token_rates(text: str) -> dict:
    """`model=in_per_million:out_per_million;...` in USD; empty means cost is not configured."""
    rates = {}
    for entry in filter(None, (part.strip() for part in text.split(";"))):
        model, separator, pair = entry.partition("=")
        prices = pair.split(":")
        if not separator or len(prices) != 2 or not re.fullmatch(MODEL_PATTERN, model.strip()):
            raise ValueError("PK_TOKEN_RATES is invalid")
        try:
            values = tuple(float(price) for price in prices)
        except ValueError:
            raise ValueError("PK_TOKEN_RATES is invalid") from None
        if any(value < 0 for value in values):
            raise ValueError("PK_TOKEN_RATES is invalid")
        rates[model.strip()] = values
    return rates


@dataclass(frozen=True, slots=True)
class Settings:
    agent_mode: Literal["STUB", "LIVE"]
    model: str
    db_path: Path
    api_key: str | None = field(repr=False)
    provider: str = 'NEBIUS'
    fireworks_api_key: str | None = field(default=None, repr=False)
    mem0_api_key: str | None = field(default=None, repr=False)
    reviewer_provider: Literal["NEBIUS", "FIREWORKS"] = "NEBIUS"
    fireworks_model: str = DEFAULT_FIREWORKS_MODEL
    token_rates: dict = field(default_factory=dict)
    tracing: dict = field(default_factory=dict, repr=False)
    autonomous_review_minutes: int = 0
    # The planning supervisor only picks one of a few validated moves, so a smaller model may suffice.
    supervisor_model: str | None = None

    @property
    def capability_available(self) -> bool:
        return self.agent_mode == "STUB" or bool(self.api_key)

    def safe_summary(self) -> dict:
        return {"agent_mode": self.agent_mode, "model": self.model,
                "capability_available": self.capability_available, "agents": self.agent_roster(),
                "autonomous_review_minutes": self.autonomous_review_minutes}

    def agent_roster(self) -> list[dict]:
        """Role/provider/model availability only; never credentials."""
        if self.agent_mode == "STUB":
            return [dict(role=role, provider="SCRIPTED", model=None, available=True, can_change=list(CAN_CHANGE[role]))
                    for role in AGENT_ROLES]
        nebius = dict(provider="NEBIUS", model=self.model, available=bool(self.api_key))
        if self.reviewer_provider == "FIREWORKS":
            reviewer = dict(provider="FIREWORKS", model=self.fireworks_model, available=bool(self.fireworks_api_key))
        else:
            reviewer = nebius
        memory = dict(provider="MEM0" if self.mem0_api_key else "LOCAL", model=None, available=True)
        supervisor = dict(nebius, model=self.supervisor_model or self.model)
        roster = [dict(role="Supervisor", **supervisor), dict(role="Extractor", **nebius), dict(role="Communicator", **nebius), dict(role="Tone Reviewer", **reviewer),
                  dict(role="Briefing", **nebius), dict(role="Memory", **memory)]
        return [dict(entry, can_change=list(CAN_CHANGE[entry["role"]])) for entry in roster]


def load_settings(env: Mapping[str, str] | None = None, *, workspace: Path | None = None) -> Settings:
    root = (workspace or Path(__file__).resolve().parents[3]).resolve()
    process = os.environ if env is None else env
    file_env = {}
    path = root / '.env'
    if path.is_file():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            name,separator,value=line.partition('=')
            if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name.strip()):
                raise ValueError('Invalid environment file entry')
            value=value.strip()
            if len(value)>=2 and value[0]==value[-1] and value[0] in {'"',"'"}: value=value[1:-1]
            file_env[name.strip()]=value
    env = file_env | dict(process)
    allowed = {"PK_AGENT_MODE", "PK_OPENAI_MODEL", "PK_NEBIUS_MODEL", "PK_DB_PATH", "PK_ALLOW_LIVE_TESTS",
               "PK_REVIEWER_PROVIDER", "PK_FIREWORKS_MODEL", "PK_TOKEN_RATES", "PK_AUTONOMOUS_REVIEW_MINUTES", "PK_SUPERVISOR_MODEL"}
    if any(name.startswith("PK_") and name not in allowed for name in env):
        raise ValueError("Unknown PK configuration field")
    mode = env.get("PK_AGENT_MODE", "STUB")
    if mode not in {"STUB", "LIVE"}:
        raise ValueError("PK_AGENT_MODE must be STUB or LIVE")
    model = env.get("PK_NEBIUS_MODEL", env.get('PK_OPENAI_MODEL', 'Qwen/Qwen3-235B-A22B-Instruct-2507'))
    reviewer_provider = env.get("PK_REVIEWER_PROVIDER", "NEBIUS")
    if reviewer_provider not in {"NEBIUS", "FIREWORKS"}:
        raise ValueError("PK_REVIEWER_PROVIDER must be NEBIUS or FIREWORKS")
    fireworks_model = env.get("PK_FIREWORKS_MODEL", DEFAULT_FIREWORKS_MODEL)
    supervisor_model = env.get("PK_SUPERVISOR_MODEL", "").strip() or None
    if (not re.fullmatch(MODEL_PATTERN, model) or not re.fullmatch(MODEL_PATTERN, fireworks_model)
            or (supervisor_model is not None and not re.fullmatch(MODEL_PATTERN, supervisor_model))):
        raise ValueError("Model configuration is invalid")
    db_path = Path(env.get("PK_DB_PATH", str(root / ".runtime" / "promisekeeper.sqlite")))
    if not db_path.is_absolute():
        raise ValueError("PK_DB_PATH must be absolute")
    db_path = db_path.resolve()
    if not db_path.is_relative_to(root):
        raise ValueError("PK_DB_PATH must stay inside the workspace")
    secret = env.get("NEBIUS_API_KEY", "").strip() or None
    tracing = {name: value for name, value in env.items() if name.startswith("LANGSMITH_")}
    autonomy = env.get("PK_AUTONOMOUS_REVIEW_MINUTES", "0")
    if not re.fullmatch(r"\d{1,4}", autonomy) or int(autonomy) > 1440:
        raise ValueError("PK_AUTONOMOUS_REVIEW_MINUTES must be 0 (off) to 1440")
    return Settings(mode, model, db_path, secret,
                    fireworks_api_key=env.get("FIREWORKS_API_KEY", "").strip() or None,
                    mem0_api_key=env.get("MEM0_API_KEY", "").strip() or None,
                    reviewer_provider=reviewer_provider, fireworks_model=fireworks_model,
                    token_rates=parse_token_rates(env.get("PK_TOKEN_RATES", "")), tracing=tracing,
                    autonomous_review_minutes=int(autonomy), supervisor_model=supervisor_model)
