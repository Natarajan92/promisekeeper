"""Readiness after owned recovery; no worker/provider execution until Gate III."""

from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import TypeAdapter, ValidationError
from starlette.exceptions import HTTPException

from promisekeeper.application.operations import CommandError
from promisekeeper.config import load_settings
from promisekeeper.contracts.common import ErrorDetail, ErrorResponse, Health, Id
from promisekeeper.persistence.sqlite import Database


def error_response(code, status, operation_id=None):
    messages = {"STORAGE_UNAVAILABLE": "Storage is unavailable. Reconcile the operation before retrying.",
                "REVISION_CONFLICT": "The case changed. Refresh and review again.",
                "PREVIEW_CHANGED": "The preview changed. Review a new preview before confirming.",
                "SENDER_REVIEW_REQUIRED": "Older communication needs explicit sender review. Create a new imported workspace from its original files and review each sender before investigating.",
                "NOT_RECORDED": "No committed operation is recorded for this copy.",
                "OPERATION_PAYLOAD_MISMATCH": "This operation ID was already used for another request.",
                "INVESTIGATOR_BUSY": "An investigation is already using the execution slot."}
    body = ErrorResponse(error=ErrorDetail(code=code, message=messages.get(code, "The request could not be completed."),
        operation_id=operation_id, retryable=status == 503, blocking_reasons=[code]))
    return JSONResponse(body.model_dump(), status_code=status)


def create_app(settings=None, *, static_dir=None):
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app):
        with Database(settings.db_path) as db:
            app.state.db = db
            scheduler = None
            if settings.autonomous_review_minutes:
                from promisekeeper.orchestration.autonomy import AutonomyScheduler
                scheduler = AutonomyScheduler(db, app.state.agents, interval_seconds=settings.autonomous_review_minutes * 60)
                scheduler.start()
            try:
                yield
            finally:
                if scheduler:
                    scheduler.stop()

    app = FastAPI(title="PromiseKeeper", version="1", lifespan=lifespan)
    app.state.db = None
    app.state.settings = settings
    from promisekeeper.agents.roster import build_agents
    from promisekeeper.application.provider_usage import usage_recorder
    app.state.agents = build_agents(settings, usage_sink=usage_recorder(
        Path(__file__).resolve().parents[4] / '.runtime' / 'application-provider-usage.jsonl'))

    @app.middleware("http")
    async def local_request(request: Request, call_next):
        request.state.operation_id = None
        host = request.headers.get("host", "")
        try:
            parsed = urlsplit("//" + host)
            valid_host = (parsed.hostname in {"127.0.0.1", "localhost", "::1"}
                          and parsed.username is None and parsed.password is None
                          and not parsed.path and not parsed.query and not parsed.fragment)
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                valid_host = False
        except ValueError:
            valid_host = False
        if not valid_host:
            return error_response("UNSUPPORTED_PAYLOAD", 403)
        origin = request.headers.get("origin")
        allowed_origins = {f"{request.url.scheme}://{host}", "http://127.0.0.1:5173", "http://localhost:5173"}
        if origin is not None and origin not in allowed_origins:
            return error_response("UNSUPPORTED_PAYLOAD", 403)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
                return error_response("UNSUPPORTED_PAYLOAD", 415)
            if request.headers.get("x-promisekeeper-request") != "1":
                return error_response("UNSUPPORTED_PAYLOAD", 403)
            try:
                data = await request.json()
                if isinstance(data, dict):
                    request.state.operation_id = TypeAdapter(Id).validate_python(data.get("operation_id"), strict=True)
            except (ValueError, ValidationError):
                pass
        if app.state.db is None or not app.state.db.ready:
            return error_response("RECOVERY_IN_PROGRESS", 503, request.state.operation_id)
        try:
            return await call_next(request)
        except sqlite3.Error:
            return error_response("STORAGE_UNAVAILABLE", 503, request.state.operation_id)
        except Exception:
            return error_response("INTERNAL_ERROR", 500, request.state.operation_id)

    @app.exception_handler(CommandError)
    async def command_error(request, exc):
        return error_response(exc.code, exc.status, exc.operation_id or request.state.operation_id)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return error_response("INVALID_REQUEST", 422, request.state.operation_id)

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response("NOT_FOUND" if exc.status_code == 404 else "INVALID_REQUEST", exc.status_code, request.state.operation_id)

    @app.get("/api/v1/health", response_model=Health)
    def health():
        return dict(schema_version="1", ready=app.state.db.ready, catalogue_version="release-0.1",
                    agent_mode=settings.agent_mode, configuration=settings.safe_summary())

    from promisekeeper.api import cases, demonstrations, operations, scenarios, investigations, reviews, history, decisions, feedback, morning_reviews, intake
    for router in (operations.router, demonstrations.router, cases.router, scenarios.router, investigations.router, reviews.router, history.router, decisions.router, feedback.router, morning_reviews.router, intake.router):
        app.include_router(router, prefix="/api/v1")
    dist = Path(static_dir) if static_dir else Path(__file__).resolve().parents[4] / "frontend" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
    return app
