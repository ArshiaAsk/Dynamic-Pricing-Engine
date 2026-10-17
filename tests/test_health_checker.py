"""HealthChecker degraded/ready/metrics contracts (ROADMAP R30 / D25).

These are unit-level checks of the reporter the endpoints delegate to: the
model-missing and probe-failure branches must report ``degraded`` (the router
turns that into a 503), readiness must be false only when no model is loaded,
and ``get_metrics`` must keep its documented shape and counters.
"""
from src.monitoring.health_checker import HealthChecker


class _RaisingModel:
    """A model whose probe raises, standing in for a broken artifact."""

    def predict(self, frame):
        raise ValueError("probe failed")


def test_missing_model_reports_degraded_without_loaded():
    health = HealthChecker().check_health(model=None)

    assert health["status"] == "degraded"
    assert health["checks"]["model"] == {"status": "warning", "loaded": False}
    assert set(health["metrics"]) == {
        "total_requests", "total_errors", "error_rate", "last_prediction"
    }


def test_failing_probe_reports_degraded_with_the_error():
    health = HealthChecker().check_health(
        model=_RaisingModel(), feature_columns=["price"]
    )

    assert health["status"] == "degraded"
    model_check = health["checks"]["model"]
    assert model_check["status"] == "error"
    assert model_check["loaded"] is True
    assert model_check["error"] == "probe failed"


def test_health_exposes_the_model_source_and_version_when_supplied():
    health = HealthChecker().check_health(
        model=_RaisingModel(),
        feature_columns=["price"],
        model_source="local",
        model_version=None,
    )

    assert health["checks"]["model"]["source"] == "local"
    assert "version" not in health["checks"]["model"]


def test_readiness_is_false_without_a_model_and_true_with_one():
    checker = HealthChecker()

    missing = checker.check_readiness(model=None)
    assert missing["ready"] is False
    assert missing["reason"] == "Model not loaded"

    loaded = checker.check_readiness(model=object())
    assert loaded["ready"] is True
    assert "reason" not in loaded


def test_get_metrics_tracks_requests_and_errors():
    checker = HealthChecker()
    checker.record_request()
    checker.record_request()
    checker.record_error()

    metrics = checker.get_metrics()

    assert metrics["total_requests"] == 2
    assert metrics["total_errors"] == 1
    assert metrics["error_rate"] == 0.5
    assert metrics["uptime_seconds"] >= 0
    assert metrics["uptime_hours"] >= 0
    assert metrics["requests_per_second"] >= 0
    assert metrics["last_prediction"] is not None


def test_liveness_is_always_true():
    alive = HealthChecker().check_liveness()

    assert alive["alive"] is True
    assert alive["uptime_seconds"] >= 0
