"""Local request guards, strict command decoding, and truthful storage failures."""

import json
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def app_for(path):
    from promisekeeper.api.app import create_app
    from promisekeeper.config import Settings
    return create_app(Settings("STUB", "gpt-5.6-terra", path, None))


def payload():
    return dict(schema_version="1", operation_id=str(uuid4()), catalogue_version="release-0.1",
                variant_id=None, clock_mode="REFERENCE")


HEADERS = {"X-PromiseKeeper-Request": "1"}


def test_health_readiness_unknown_operation_and_safe_validation(tmp_path):
    app = app_for(tmp_path / "api.sqlite")
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        assert client.get("/api/v1/health").json()["ready"] is True
        response = client.get(f"/api/v1/operations/{uuid4()}", params={"demonstration_id": str(uuid4())})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_RECORDED"
        invalid = payload() | {"unexpected": "SECRET_SENTINEL"}
        response = client.post("/api/v1/demonstrations", json=invalid, headers=HEADERS)
        assert response.status_code == 422
        assert "SECRET_SENTINEL" not in response.text
        assert response.json()["error"]["operation_id"] == invalid["operation_id"]
    assert app.state.db.ready is False


@pytest.mark.parametrize("headers,content_type", [({}, "application/json"), (HEADERS, "text/plain"),
    (HEADERS | {"Origin": "https://evil.invalid"}, "application/json"),
    (HEADERS | {"Host": "evil.invalid"}, "application/json"),
    (HEADERS | {"Host": "localhost.evil.invalid:8000"}, "application/json")])
def test_mutation_requires_loopback_json_and_same_origin_header(tmp_path, headers, content_type):
    with TestClient(app_for(tmp_path / "api.sqlite"), base_url="http://127.0.0.1:8000") as client:
        response = client.post("/api/v1/demonstrations", content=json.dumps(payload()),
                               headers=headers | {"Content-Type": content_type})
        assert response.status_code in (403, 415)
        assert client.get("/api/v1/demonstrations").json()["demonstrations"] == []


def test_actual_commit_failure_is_safe_and_retry_reconciles_receipt(tmp_path, monkeypatch):
    app = app_for(tmp_path / "api.sqlite")
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        request = payload()
        original = app.state.db.commit
        def fail(con):
            raise sqlite3.OperationalError("SECRET_SENTINEL")
        monkeypatch.setattr(app.state.db, "commit", fail)
        failed = client.post("/api/v1/demonstrations", json=request, headers=HEADERS)
        assert failed.status_code == 503
        assert failed.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
        assert failed.json()["error"]["operation_id"] == request["operation_id"]
        assert "SECRET_SENTINEL" not in failed.text
        monkeypatch.setattr(app.state.db, "commit", original)
        assert client.get("/api/v1/demonstrations").json()["demonstrations"] == []
        saved = client.post("/api/v1/demonstrations", json=request, headers=HEADERS)
        assert saved.status_code == 201
        did = saved.json()["demonstration_id"]
        receipt = client.get(f"/api/v1/operations/{request['operation_id']}", params={"demonstration_id": did})
        assert receipt.json() == saved.json()
        assert client.get(f"/api/v1/operations/{request['operation_id']}", params={"demonstration_id": str(uuid4())}).status_code == 404


def test_cli_init_creates_new_copies_and_refuses_multiple_workers(run_python):
    result = run_python('''
from promisekeeper.cli import main
main(['init-demo','--catalogue','release-0.1','--clock','REFERENCE'])
main(['init-demo','--catalogue','release-0.1','--clock','REFERENCE'])
''')
    assert result.returncode == 0, result.stderr
    a, b = [json.loads(line) for line in result.stdout.splitlines()]
    assert a["demonstration_id"] != b["demonstration_id"]
    rejected = run_python("from promisekeeper.cli import main; main(['serve','--workers','2'])")
    assert rejected.returncode != 0


@pytest.mark.parametrize("host", ["127.0.0.1/path", "127.0.0.1#fragment", "127.0.0.1?query", "user@127.0.0.1"])
def test_malformed_host_is_rejected_even_with_loopback_hostname(tmp_path, host):
    with TestClient(app_for(tmp_path / "api.sqlite"), base_url="http://127.0.0.1:8000") as client:
        assert client.get("/api/v1/health", headers={"Host": host}).status_code == 403
