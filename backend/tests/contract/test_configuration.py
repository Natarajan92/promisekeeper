from pathlib import Path
import socket

import pytest

from promisekeeper.config import load_settings
from promisekeeper.diagnostics import diagnostic


def test_live_mode_without_credentials_remains_live_and_reports_unavailable(tmp_path):
    settings = load_settings({"PK_AGENT_MODE": "LIVE"}, workspace=tmp_path)
    assert settings.agent_mode == "LIVE"
    assert settings.capability_available is False
    assert "OPENAI_API_KEY" not in settings.safe_summary()


@pytest.mark.parametrize("env", [
    {"PK_AGENT_MODE": "live"},
    {"PK_AGENT_MODE": "OTHER"},
    {"PK_UNKNOWN_SETTING": "x"},
    {"PK_DB_PATH": "relative.sqlite"},
])
def test_invalid_settings_fail_without_coercion_or_value_echo(env, tmp_path):
    with pytest.raises(ValueError):
        load_settings(env, workspace=tmp_path)


def test_runtime_database_cannot_escape_workspace(tmp_path):
    with pytest.raises(ValueError):
        load_settings({"PK_DB_PATH": str(tmp_path.parent / "outside.sqlite")}, workspace=tmp_path)


def test_secrets_are_not_in_configuration_representation(tmp_path):
    settings = load_settings({"PK_AGENT_MODE": "LIVE", "NEBIUS_API_KEY": "secret-example-value"}, workspace=tmp_path)
    assert settings.capability_available
    assert "secret-example-value" not in repr(settings)
    assert "secret-example-value" not in str(settings.safe_summary())


def test_diagnostics_drop_raw_content_and_redact_allowed_values():
    event = diagnostic("step_failed", {
        "failure_code": "provider leaked secret-example-value",
        "Authorization": "Bearer private-token",
        "raw_response": "customer and credential content",
        "duration_ms": 15,
    }, secrets=("secret-example-value",))
    assert event == {"event": "step_failed", "failure_code": "provider leaked [REDACTED]", "duration_ms": 15}


def test_offline_suite_blocks_external_connections():
    with socket.socket() as sock, pytest.raises(RuntimeError, match="External networking"):
        sock.connect(("203.0.113.10", 443))


def test_execution_and_business_clock_are_independent(business_clock, execution_clock):
    initial = business_clock.now
    execution_clock.advance(60)
    assert business_clock.now == initial
    assert execution_clock.elapsed == 60


def test_subprocess_storage_is_isolated_and_credentials_removed(run_python, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-child")
    result = run_python("import os; print(os.environ['PK_DB_PATH']); print('OPENAI_API_KEY' in os.environ)")
    assert result.returncode == 0
    assert "subprocess.sqlite" in result.stdout
    assert result.stdout.rstrip().endswith("False")


def test_offline_subprocess_cannot_bypass_external_network_blocking(run_python):
    result=run_python("import socket\ns=socket.socket();s.settimeout(0.05)\ntry: s.connect(('203.0.113.10',443))\nexcept RuntimeError: print('BLOCKED')\nexcept OSError: print('NOT_BLOCKED')")
    assert result.returncode==0 and result.stdout.strip()=="BLOCKED"


def test_new_agent_settings_default_and_never_leak(tmp_path):
    settings = load_settings({"PK_AGENT_MODE": "LIVE", "NEBIUS_API_KEY": "nb-secret", "FIREWORKS_API_KEY": "fw-secret",
                              "MEM0_API_KEY": "m0-secret"}, workspace=tmp_path)
    assert settings.reviewer_provider == "NEBIUS"
    assert settings.fireworks_model == "accounts/fireworks/models/gpt-oss-120b"
    for secret in ("fw-secret", "m0-secret", "nb-secret"):
        assert secret not in repr(settings)
        assert secret not in str(settings.safe_summary())
    with pytest.raises(ValueError):
        load_settings({"PK_REVIEWER_PROVIDER": "OTHER"}, workspace=tmp_path)
    with pytest.raises(ValueError):
        load_settings({"PK_TOKEN_RATES": "model-without-rates"}, workspace=tmp_path)


def test_token_rates_parse_per_model(tmp_path):
    settings = load_settings({"PK_TOKEN_RATES": "zai-org/GLM-5.3-Flash=0.1:0.4;accounts/fireworks/models/gpt-oss-120b=0.15:0.6"}, workspace=tmp_path)
    assert settings.token_rates == {"zai-org/GLM-5.3-Flash": (0.1, 0.4), "accounts/fireworks/models/gpt-oss-120b": (0.15, 0.6)}


def test_agent_roster_marks_unconfigured_providers_unavailable(tmp_path):
    stub = {a["role"]: a for a in load_settings({}, workspace=tmp_path).safe_summary()["agents"]}
    assert set(stub) == {"Extractor", "Communicator", "Tone Reviewer", "Briefing", "Memory"}
    assert all(a["available"] and a["provider"] == "SCRIPTED" for a in stub.values())
    live = {a["role"]: a for a in load_settings({"PK_AGENT_MODE": "LIVE", "NEBIUS_API_KEY": "k", "PK_REVIEWER_PROVIDER": "FIREWORKS"},
                                               workspace=tmp_path).safe_summary()["agents"]}
    assert live["Communicator"]["available"] is True and live["Communicator"]["provider"] == "NEBIUS"
    assert live["Tone Reviewer"]["provider"] == "FIREWORKS" and live["Tone Reviewer"]["available"] is False


def test_tracing_settings_are_collected_but_never_summarised(tmp_path):
    settings = load_settings({"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "ls-secret", "LANGSMITH_PROJECT": "pk"}, workspace=tmp_path)
    assert settings.tracing == {"LANGSMITH_TRACING": "true", "LANGSMITH_API_KEY": "ls-secret", "LANGSMITH_PROJECT": "pk"}
    assert "ls-secret" not in repr(settings) and "ls-secret" not in str(settings.safe_summary())


def test_export_tracing_sets_only_langsmith_environment(monkeypatch, tmp_path):
    import os
    from promisekeeper.cli import export_tracing
    monkeypatch.setenv("LANGSMITH_PROJECT", "placeholder")
    export_tracing(load_settings({"LANGSMITH_PROJECT": "pk-demo", "NEBIUS_API_KEY": "nb"}, workspace=tmp_path))
    assert os.environ["LANGSMITH_PROJECT"] == "pk-demo"
    assert os.environ.get("NEBIUS_API_KEY") != "nb"
