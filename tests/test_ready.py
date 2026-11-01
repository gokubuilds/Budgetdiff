from unittest.mock import patch

from app.config import Settings, get_settings
from app.main import app


def test_ready_with_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_ready_without_database(client):
    # Simulate database outage
    with patch("app.main.engine.connect") as mock_connect:
        mock_connect.side_effect = ConnectionError("PostgreSQL connection refused at port 5432")

        # /ready must return 503 Service Unavailable
        ready_response = client.get("/ready")
        assert ready_response.status_code == 503
        assert "Database unavailable" in ready_response.json()["detail"]

        # /health must remain 200 OK because it is an independent liveness probe
        health_response = client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"


def test_ready_when_database_not_configured():
    # When deployed on a host with no database configured
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_name="BudgetDiff", environment="test", database_url=""
    )
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        response = c.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "not_configured", "database": "none"}
    app.dependency_overrides.clear()
