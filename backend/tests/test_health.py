"""
Week 1 smoke tests — health check and basic API reachability.
These are the only tests for Week 1. Full test suites start in Week 2.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings, Settings


# Override settings for tests — no real secrets needed
def get_test_settings() -> Settings:
    return Settings(
        app_env="test",
        app_secret_key="test-secret-key-not-real",
        database_url="postgresql://postgres:ci@localhost:5432/ci",
        jwt_secret_key="test-jwt-key-not-real-64chars-padding-here-to-reach-length",
        redis_url="redis://localhost:6379/0",
    )


app.dependency_overrides[get_settings] = get_test_settings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


class TestHealthEndpoint:
    def test_healthz_returns_200(self, client: TestClient) -> None:
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_body(self, client: TestClient) -> None:
        data = client.get("/healthz").json()
        assert data["status"] == "ok"
        assert data["env"] == "test"


class TestHelloEndpoint:
    def test_hello_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/hello")
        assert response.status_code == 200

    def test_hello_body(self, client: TestClient) -> None:
        data = client.get("/api/v1/hello").json()
        assert "message" in data
        assert "version" in data


class TestSecurityHeaders:
    """Verify CORS allows only the expected origins (Week 2 expands this)."""

    def test_cors_rejects_unknown_origin(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/hello",
            headers={"Origin": "https://evil.example.com"},
        )
        # CORS header should NOT be present for unlisted origin
        assert "access-control-allow-origin" not in response.headers

    def test_metrics_endpoint_exists(self, client: TestClient) -> None:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "conversx_http_requests_total" in response.text
