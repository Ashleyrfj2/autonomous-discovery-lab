import secrets
import socket
import subprocess
import sys
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from pydantic import SecretStr

from autodiscover.orchestrator.lab import Lab
from autodiscover.reporting.web import create_app

ORIGIN = "http://127.0.0.1:8765"
PASSWORD = secrets.token_urlsafe(24)


def fixture(tmp_path, *, clock=time.monotonic):
    lab = Lab(tmp_path)
    run = lab.demo()
    app = create_app(tmp_path, SecretStr(PASSWORD), clock=clock)
    client = TestClient(app, base_url=ORIGIN, client=("127.0.0.1", 12345))
    return lab, run, client


def login(client):
    result = client.post("/api/session", json={"password": PASSWORD}, headers={"Origin": ORIGIN})
    assert result.status_code == 200
    return client.get("/api/session").json()["csrf_token"]


def test_authenticated_real_reads_preserve_state_and_boundaries(tmp_path):
    lab, run, client = fixture(tmp_path)
    with lab.store.connection() as db:
        before = list(db.iterdump())
    reports = {p.name: p.read_bytes() for p in (tmp_path / "reports").iterdir()}
    assert client.get("/api/runs").status_code == 401
    csrf = login(client)
    assert csrf and PASSWORD not in client.get("/api/session").text
    assert client.get("/api/runs?limit=1").json()["items"][0]["run_id"] == run
    for path in (
        run,
        f"{run}/tree",
        f"{run}/jobs",
        f"{run}/stages",
        f"{run}/evidence",
        f"{run}/usage",
    ):
        result = client.get("/api/runs/" + path)
        assert result.status_code == 200, result.text
        assert result.headers["cache-control"] == "no-store"
        assert result.headers["x-content-type-options"] == "nosniff"
    assert client.get("/api/queue").json()["items"] == []
    with lab.store.connection() as db:
        assert list(db.iterdump()) == before
    assert {p.name: p.read_bytes() for p in (tmp_path / "reports").iterdir()} == reports
    assert client.get("/docs").status_code == 404


def test_cookie_rotation_logout_expiry_and_csrf(tmp_path):
    current = [0.0]
    _lab, _run, client = fixture(tmp_path, clock=lambda: current[0])
    response = client.post("/api/session", json={"password": PASSWORD}, headers={"Origin": ORIGIN})
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    old_cookie = client.cookies.get("adl_operator")
    csrf = client.get("/api/session").json()["csrf_token"]
    assert (
        client.post("/api/session/logout", json={}, headers={"Origin": ORIGIN}).status_code == 403
    )
    login(client)
    assert client.cookies.get("adl_operator") != old_cookie
    assert (
        client.post(
            "/api/session/logout", json={}, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}
        ).status_code
        == 403
    )
    current[0] = 8 * 3600 + 1
    assert client.get("/api/runs").status_code == 401
    current[0] += 60
    csrf = login(client)
    result = client.post(
        "/api/session/logout", json={}, headers={"Origin": ORIGIN, "X-CSRF-Token": csrf}
    )
    assert result.status_code == 200
    assert client.get("/api/runs").status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.example:8765"},
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"Sec-Fetch-Site": "cross-site"},
    ],
)
def test_rebinding_cross_origin_and_cross_site_requests_rejected(tmp_path, headers):
    _lab, _run, client = fixture(tmp_path)
    login(client)
    assert client.get("/api/runs", headers=headers).status_code == 403


def test_remote_client_cannot_gain_authority_by_forwarded_headers(tmp_path):
    Lab(tmp_path).store.create_run("local only", {})
    app = create_app(tmp_path, SecretStr(PASSWORD))
    remote = TestClient(app, base_url=ORIGIN, client=("192.0.2.9", 8888))
    assert (
        remote.post(
            "/api/session",
            json={"password": PASSWORD},
            headers={"Origin": ORIGIN, "X-Forwarded-For": "127.0.0.1"},
        ).status_code
        == 403
    )


def test_login_size_schema_content_type_and_rate_limits_without_echoing_secrets(tmp_path):
    _lab, _run, client = fixture(tmp_path)
    assert client.post("/api/session", json={"password": PASSWORD}).status_code == 403
    assert client.post("/api/session", content="x", headers={"Origin": ORIGIN}).status_code == 403
    result = client.post(
        "/api/session",
        json={"password": PASSWORD, "actor_kind": "human"},
        headers={"Origin": ORIGIN},
    )
    assert result.status_code == 422 and PASSWORD not in result.text
    large = client.post(
        "/api/session",
        content="x" * 17000,
        headers={"Origin": ORIGIN, "Content-Type": "application/json"},
    )
    assert large.status_code == 413
    for _ in range(5):
        assert (
            client.post(
                "/api/session",
                json={"password": "incorrect-passphrase"},
                headers={"Origin": ORIGIN},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/session", json={"password": PASSWORD}, headers={"Origin": ORIGIN}
        ).status_code
        == 401
    )


def test_api_corruption_stale_cursor_and_invalid_pages_fail_closed(tmp_path):
    lab, run, client = fixture(tmp_path)
    login(client)
    cursor = client.get("/api/runs").json()["cursor"]["seq"]
    lab.store.create_run("another workflow", {})
    assert client.get(f"/api/runs?at_cursor={cursor}").status_code == 409
    assert client.get("/api/runs?limit=101").status_code == 422
    assert client.get("/api/runs/unknown").status_code == 404
    with lab.store.connection(write=True) as db:
        db.execute("UPDATE runs SET topic='tampered' WHERE id=?", (run,))
    result = client.get("/api/runs/" + run)
    assert result.status_code == 409
    assert result.json() == {"error": "EVIDENCE_INTEGRITY_FAILURE"}
    assert str(tmp_path) not in result.text


def test_serve_requires_interactive_startup_and_does_not_initialize_root(tmp_path):
    result = subprocess.run(  # noqa: S603 - fixed module and temporary test arguments
        [sys.executable, "-m", "autodiscover.cli", "--root", str(tmp_path / "new"), "serve"],
        capture_output=True,
        text=True,
        input="",
        check=False,
    )  # noqa: S603 - fixed CLI
    assert result.returncode == 2 and "interactive terminal" in result.stderr
    assert not (tmp_path / "new").exists()


def test_real_loopback_http_login_and_read_then_bounded_shutdown(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    app = create_app(tmp_path, SecretStr(PASSWORD), port=port)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            proxy_headers=False,
            access_log=False,
            log_level="critical",
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.started
        origin = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=origin, trust_env=False, timeout=2) as client:
            assert client.get("/api/runs").status_code == 401
            assert (
                client.post(
                    "/api/session", json={"password": PASSWORD}, headers={"Origin": origin}
                ).status_code
                == 200
            )
            result = client.get("/api/runs/" + run)
            assert result.status_code == 200 and result.json()["summary"]["run_id"] == run
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive()


def test_duplicate_headers_and_read_body_are_rejected(tmp_path):
    _lab, _run, client = fixture(tmp_path)
    login(client)
    duplicate = client.get(
        "/api/runs", headers=[("Host", "127.0.0.1:8765"), ("Host", "evil.example")]
    )
    assert duplicate.status_code == 400
    assert client.request("GET", "/api/runs", content="unexpected body").status_code == 400


def test_unexpected_read_error_never_exposes_or_logs_exception_body(tmp_path, monkeypatch, caplog):
    from autodiscover.reporting.views import ReadService

    _lab, _run, client = fixture(tmp_path)
    login(client)

    def broken(*args, **kwargs):
        raise RuntimeError("private-source-error-body")

    monkeypatch.setattr(ReadService, "runs", broken)
    result = client.get("/api/runs")
    assert result.status_code == 503
    assert "private-source-error-body" not in result.text + caplog.text
