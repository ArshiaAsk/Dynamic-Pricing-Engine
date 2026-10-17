"""Health, readiness, liveness and metrics endpoint contracts (R30 / D25).

The application is imported lazily inside the fixtures (CONVENTIONS rule 17):
importing ``src.api.server`` loads the served model, which is absent before the
data/model build step in a clean checkout.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def app():
    from src.api.server import app as fastapi_app

    return fastapi_app


def test_lifespan_starts_and_stops_and_root_responds(app):
    """The startup/shutdown hooks run and ``/`` describes the service."""
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Dynamic Pricing API"
    assert body["status"] == "running"
    assert body["health"] == "/v1/health"


def test_readiness_reports_ready_when_the_model_is_loaded(client):
    response = client.get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_liveness_reports_alive(client):
    response = client.get("/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["alive"] is True
    assert body["uptime_seconds"] >= 0


def test_metrics_reports_health_and_prediction_counters(client):
    response = client.get("/v1/metrics")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"health", "predictions"}
    assert {"uptime_seconds", "total_requests", "total_errors",
            "error_rate"} <= set(body["health"])
    assert {"total_predictions", "total_optimizations",
            "buffer_size"} <= set(body["predictions"])


def test_health_returns_503_when_the_check_is_degraded(client, monkeypatch):
    """A degraded health report is a 503, not a 200 with a bad status."""
    import src.api.router as router

    monkeypatch.setattr(
        router.health_checker,
        "check_health",
        lambda **kwargs: {"status": "degraded", "checks": {"model": {"status": "warning"}}},
    )

    response = client.get("/v1/health")

    assert response.status_code == 503
    assert response.json()["detail"]["status"] == "degraded"


def test_readiness_returns_503_when_the_model_is_not_loaded(client, monkeypatch):
    import src.api.router as router

    monkeypatch.setattr(
        router.health_checker,
        "check_readiness",
        lambda model=None: {"ready": False, "reason": "Model not loaded"},
    )

    response = client.get("/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["ready"] is False
    assert response.json()["detail"]["reason"] == "Model not loaded"
