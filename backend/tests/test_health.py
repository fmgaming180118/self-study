from unittest.mock import AsyncMock, MagicMock
from app.main import app
from app.database import get_db


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["api"] == "/api/v1"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_liveness_endpoint(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "service" in data


def test_readiness_endpoint_success(client):
    mock_db = AsyncMock()
    mock_scalar_result = MagicMock()
    mock_scalar_result.scalar.return_value = 1

    mock_vector_result = MagicMock()
    mock_vector_result.scalar.return_value = "vector"

    mock_db.execute.side_effect = [mock_scalar_result, mock_vector_result]

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["pgvector_extension"] is True
    finally:
        app.dependency_overrides.clear()


def test_readiness_endpoint_failure(client):
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("DB Connection Lost")

    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
    finally:
        app.dependency_overrides.clear()
