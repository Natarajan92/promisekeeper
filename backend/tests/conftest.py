from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest
from support.network_guard import install as install_network_guard


@dataclass
class BusinessClock:
    now: datetime

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


@dataclass
class ExecutionClock:
    elapsed: float = 0

    def advance(self, seconds: float) -> None:
        self.elapsed += seconds


@pytest.fixture
def business_clock():
    return BusinessClock(datetime(2026, 10, 23, 4, 30, tzinfo=timezone.utc))


@pytest.fixture
def execution_clock():
    return ExecutionClock()


@pytest.fixture
def isolated_db_path(tmp_path):
    return tmp_path / "isolated.sqlite"


@pytest.fixture
def run_python(tmp_path):
    def run(script: str, *, timeout: float = 5):
        env = {key: value for key, value in os.environ.items()
               if key not in {"OPENAI_API_KEY", "GH_TOKEN", "GITHUB_TOKEN"}}
        env.update(PK_AGENT_MODE="STUB", PK_DB_PATH=str(tmp_path / "subprocess.sqlite"))
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent / "support")
        return subprocess.run([sys.executable, "-c", script], cwd=tmp_path,
                              env=env, capture_output=True, text=True, timeout=timeout)
    return run


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch, request):
    """Local integration is permitted; offline tests cannot reach external hosts."""
    if request.node.get_closest_marker("live"):
        if os.environ.get("PK_ALLOW_LIVE_TESTS") != "1":
            pytest.skip("Live evaluation requires explicit PK_ALLOW_LIVE_TESTS=1")
        return

    install_network_guard(monkeypatch.setattr)
