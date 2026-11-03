"""Single-operator loopback read API. No experiments, approvals or budget mutations."""

import asyncio
import hashlib
import hmac
import json
import secrets
import sqlite3
import threading
import time
from collections.abc import Callable
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.orchestrator.store import StateError
from autodiscover.reporting.views import PageRequest, ReadConflict, ReadService
from autodiscover.security.redaction import sanitize

COOKIE = "adl_operator"
MAX_BODY = 16384


class OperatorAuthority:
    def __init__(self, password: SecretStr, clock: Callable[[], float] = time.monotonic):
        value = password.get_secret_value()
        if not 12 <= len(value) <= 200:
            raise ValueError("Use a temporary operator passphrase of 12–200 characters")
        self._salt, self.clock = secrets.token_bytes(16), clock
        self._password = self._digest(value)
        self._lock = threading.Lock()
        self._attempts: list[float] = []
        self._session: bytes | None = None
        self._csrf, self._expires = "", 0.0

    def _digest(self, value: str) -> bytes:
        return hashlib.scrypt(value.encode(), salt=self._salt, n=16384, r=8, p=1, dklen=32)

    def login(self, password: SecretStr) -> str | None:
        with self._lock:
            self._attempts = [t for t in self._attempts if self.clock() - t < 60]
            if len(self._attempts) >= 5:
                return None
            self._attempts.append(self.clock())
            if not hmac.compare_digest(self._password, self._digest(password.get_secret_value())):
                return None
            token = secrets.token_urlsafe(32)
            self._session = hashlib.sha256(token.encode()).digest()
            self._csrf, self._expires = secrets.token_urlsafe(32), self.clock() + 8 * 3600
            return token

    def session(self, token: str) -> str | None:
        with self._lock:
            if (
                self._session is None
                or self.clock() >= self._expires
                or not hmac.compare_digest(self._session, hashlib.sha256(token.encode()).digest())
            ):
                return None
            return self._csrf

    def logout(self, token: str) -> bool:
        with self._lock:
            if self._session is None or not hmac.compare_digest(
                self._session, hashlib.sha256(token.encode()).digest()
            ):
                return False
            self._session, self._csrf, self._expires = None, "", 0.0
            return True


class OperatorBoundary:
    def __init__(self, app: ASGIApp, *, authority: OperatorAuthority, port: int):
        self.app, self.authority = app, authority
        self.host = f"127.0.0.1:{port}"
        self.origin = f"http://{self.host}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def secured_send(message: Any) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; "
                        b"style-src 'self'; connect-src 'self'; img-src 'self' data:; "
                        b"frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                    ),
                ]
            await send(message)

        async def reject(status: int, code: str) -> None:
            await JSONResponse({"error": code}, status_code=status)(scope, receive, secured_send)

        pairs = scope.get("headers", [])
        headers = {key.lower(): value.decode("latin1") for key, value in pairs}
        for key in (b"host", b"origin", b"cookie", b"content-length", b"x-csrf-token"):
            if sum(name.lower() == key for name, _ in pairs) > 1:
                await reject(400, "DUPLICATE_SECURITY_HEADER")
                return
        if headers.get(b"host") != self.host or scope.get("client", (None,))[0] != "127.0.0.1":
            await reject(403, "LOOPBACK_HOST_REQUIRED")
            return
        if (
            headers.get(b"origin") not in (None, self.origin)
            or headers.get(b"sec-fetch-site") == "cross-site"
        ):
            await reject(403, "ORIGIN_REJECTED")
            return
        method, path = scope["method"], scope["path"]
        mutating = method not in ("GET", "HEAD")
        if mutating and (
            headers.get(b"origin") != self.origin
            or headers.get(b"content-type", "").split(";", 1)[0] != "application/json"
        ):
            await reject(403, "SAME_ORIGIN_JSON_REQUIRED")
            return
        cookies: SimpleCookie = SimpleCookie()
        try:
            cookies.load(headers.get(b"cookie", ""))
        except Exception:
            await reject(401, "OPERATOR_SESSION_REQUIRED")
            return
        token = cookies[COOKIE].value if COOKIE in cookies else ""
        csrf = self.authority.session(token)
        login = path == "/api/session" and method == "POST"
        if not login and csrf is None:
            await reject(401, "OPERATOR_SESSION_REQUIRED")
            return
        if (
            mutating
            and not login
            and not hmac.compare_digest(
                (csrf or "").encode(), headers.get(b"x-csrf-token", "").encode()
            )
        ):
            await reject(403, "CSRF_REJECTED")
            return
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > MAX_BODY:
                        await reject(413, "REQUEST_TOO_LARGE")
                        return
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await reject(408, "REQUEST_TIMEOUT")
            return
        if not mutating and body:
            await reject(400, "READ_BODY_REJECTED")
            return
        delivered = False

        async def replay() -> Any:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        try:
            await self.app(scope, replay, secured_send)
        except Exception:
            # No raw validation/source bodies or private paths are exposed or logged.
            await reject(503, "OPERATOR_READ_FAILED")


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0, le=1000000)] = 0,
    at_cursor: Annotated[int | None, Query(ge=0)] = None,
) -> PageRequest:
    return PageRequest(limit=limit, offset=offset, at_cursor=at_cursor)


Pagination = Annotated[PageRequest, Depends(pagination)]


def safe_json(value: Any) -> JSONResponse:
    data = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    data = sanitize(data)
    if len(json.dumps(data).encode()) > 2_000_000:
        return JSONResponse({"error": "RESPONSE_LIMIT"}, status_code=413)
    return JSONResponse(data)


def create_app(
    root: Path,
    password: SecretStr,
    *,
    port: int = 8765,
    clock: Callable[[], float] = time.monotonic,
) -> FastAPI:
    if not 1024 <= port <= 65535:
        raise ValueError("Local operator port must be 1024–65535")
    reads = ReadService(root)
    reads.runs(
        PageRequest(limit=1)
    )  # Fail closed before serving; never initialize/migrate a GET root.
    authority = OperatorAuthority(password, clock)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(OperatorBoundary, authority=authority, port=port)

    @app.exception_handler(RequestValidationError)
    async def invalid(_request: Request, _error: RequestValidationError):
        return JSONResponse({"error": "INVALID_REQUEST"}, status_code=422)

    @app.exception_handler(ValidationError)
    @app.exception_handler(IntegrityError)
    async def integrity(_request: Request, _error: IntegrityError):
        return JSONResponse({"error": "EVIDENCE_INTEGRITY_FAILURE"}, status_code=409)

    @app.exception_handler(StateError)
    async def missing(_request: Request, _error: StateError):
        return JSONResponse({"error": "UNKNOWN_OR_UNAVAILABLE_RUN"}, status_code=404)

    @app.exception_handler(ReadConflict)
    async def conflict(_request: Request, _error: ReadConflict):
        return JSONResponse({"error": "STALE_CURSOR"}, status_code=409)

    @app.exception_handler(sqlite3.Error)
    async def database(_request: Request, _error: sqlite3.Error):
        return JSONResponse({"error": "DATABASE_UNAVAILABLE"}, status_code=503)

    @app.post("/api/session")
    async def login(body: Login):
        value = body.password.get_secret_value()
        if not 12 <= len(value) <= 200:
            return JSONResponse({"error": "LOGIN_REJECTED"}, status_code=401)
        token = await asyncio.to_thread(authority.login, body.password)
        if token is None:
            return JSONResponse({"error": "LOGIN_REJECTED"}, status_code=401)
        response = JSONResponse({"authenticated": True})
        response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=8 * 3600)
        return response

    @app.get("/api/session")
    def session(request: Request):
        return JSONResponse({"csrf_token": authority.session(request.cookies.get(COOKIE, ""))})

    @app.post("/api/session/logout")
    def logout(request: Request):
        if not authority.logout(request.cookies.get(COOKIE, "")):
            return JSONResponse({"error": "OPERATOR_SESSION_REQUIRED"}, status_code=401)
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(COOKIE, httponly=True, samesite="strict")
        return response

    @app.get("/api/runs")
    def runs(page: Pagination):
        return safe_json(reads.runs(page))

    @app.get("/api/runs/{run_id}")
    def detail(run_id: str):
        return safe_json(reads.detail(run_id))

    @app.get("/api/runs/{run_id}/tree")
    def tree(run_id: str):
        return safe_json(reads.tree(run_id))

    @app.get("/api/runs/{run_id}/jobs")
    def jobs(run_id: str, page: Pagination):
        return safe_json(reads.jobs(run_id, page))

    @app.get("/api/runs/{run_id}/stages")
    def stages(run_id: str, page: Pagination):
        return safe_json(reads.stages(run_id, page))

    @app.get("/api/runs/{run_id}/evidence")
    def evidence(run_id: str, page: Pagination):
        return safe_json(reads.evidence(run_id, page))

    @app.get("/api/runs/{run_id}/usage")
    def usage(run_id: str):
        return safe_json(reads.usage(run_id))

    @app.get("/api/queue")
    def queue(page: Pagination):
        return safe_json(reads.queue(page))

    return app
