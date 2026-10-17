"""Behaviour-level tests for the API middleware stack (ROADMAP R30 / D25).

Each middleware is mounted on a small FastAPI app and exercised through the
HTTP surface, so the assertions are about status codes, bodies and headers —
not about the middleware internals. The app is fresh per test, which keeps
the in-memory rate-limit window from leaking into the rest of the suite.
"""
import logging
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware import (
    ErrorHandlingMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    TimeoutMiddleware,
)

# Substrings that would indicate internal detail leaked to the client.
_LEAKY = ("Traceback", "RuntimeError", "secret internal detail", "/home/")


def test_rate_limit_returns_429_after_the_limit_is_reached():
    """The N+1th request in the window gets the documented 429 body.

    Requests 1..N are served normally; the next one is rejected with
    ``rate_limit_exceeded`` and no internal detail. A different client is not
    affected, which shows the window is per client.
    """
    app = FastAPI()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, requests_per_minute=2)
    client = TestClient(app)

    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200

    limited = client.get("/ping")
    assert limited.status_code == 429
    body = limited.json()
    assert body["error"] == "rate_limit_exceeded"
    assert "2 requests per minute" in body["message"]
    assert set(body) == {"error", "message"}
    for leaked in _LEAKY:
        assert leaked not in limited.text

    other = TestClient(app, client=("10.0.0.2", 50000))
    assert other.get("/ping").status_code == 200


def test_unhandled_route_exception_returns_generic_500_with_request_id():
    """An exception escaping a route is turned into the generic 500 body.

    The response carries a request id that matches ``X-Request-ID`` and none of
    the exception text. This is the layer that produces the 500 for a route
    exception (``ErrorHandlingMiddleware``), so it must not depend on an
    ``Exception`` exception handler being registered.
    """
    app = FastAPI()

    @app.get("/boom")
    def boom():
        raise RuntimeError("secret internal detail")

    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app)

    response = client.get("/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"] == "internal_server_error"
    assert body["message"] == "An internal error occurred. Please try again later."
    assert body["request_id"]
    assert body["request_id"] == response.headers["X-Request-ID"]
    for leaked in _LEAKY:
        assert leaked not in response.text


def test_request_logging_logs_the_error_branch_and_reraises(caplog):
    """``RequestLoggingMiddleware`` logs an ERROR record and re-raises.

    Without an inner error handler the exception must propagate (the middleware
    never swallows it), and the log record must carry the request id and the
    traceback.
    """
    app = FastAPI()

    @app.get("/boom")
    def boom():
        raise RuntimeError("logged-detail")

    app.add_middleware(RequestLoggingMiddleware)
    client = TestClient(app)

    caplog.set_level(logging.ERROR, logger="src.api.middleware")
    with pytest.raises(RuntimeError, match="logged-detail"):
        client.get("/boom")

    failures = [
        record for record in caplog.records
        if record.name == "src.api.middleware"
        and "Request failed" in record.getMessage()
    ]
    assert failures, [r.getMessage() for r in caplog.records]
    record = failures[0]
    assert record.levelno == logging.ERROR
    assert record.request_id
    assert record.exc_info is not None
    assert "logged-detail" in record.getMessage()


def test_timeout_middleware_returns_504_for_a_slow_route():
    """A route slower than the configured timeout returns the 504 body."""
    app = FastAPI()

    @app.get("/slow")
    def slow():
        time.sleep(0.5)
        return {"ok": True}

    app.add_middleware(TimeoutMiddleware, timeout_seconds=0.05)
    client = TestClient(app)

    started = time.monotonic()
    response = client.get("/slow")
    elapsed = time.monotonic() - started

    assert elapsed < 2.0, f"timeout test took {elapsed:.2f}s"
    assert response.status_code == 504
    body = response.json()
    assert body["error"] == "request_timeout"
    assert "0.05 seconds" in body["message"]
    assert body["request_id"]
