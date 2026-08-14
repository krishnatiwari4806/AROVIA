"""Integration tests for health endpoint and error handlers."""

import pytest
from app.core.exceptions import NotFoundError
from app.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint(client):
    """Verify that GET /api/v1/health returns 200 OK and connected database."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_custom_app_error_handler(client):
    """Verify that custom AppError returns structured JSON with specific status code."""

    # Temporarily register a test route that raises NotFoundError
    @app.get("/api/v1/test-error")
    async def raise_test_error():
        raise NotFoundError("Candidate profile not found")

    response = await client.get("/api/v1/test-error")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Candidate profile not found"
    assert data["error_code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_global_exception_handler_sanitizes_500(client):
    """Verify that unhandled exceptions return sanitized 500 error without leaking tracebacks."""

    @app.get("/api/v1/test-unhandled")
    async def raise_unhandled():
        raise RuntimeError("Secret database connection credentials failed")

    response = await client.get("/api/v1/test-unhandled")
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "Internal server error"
    assert data["error_code"] == "INTERNAL_ERROR"
    # Ensure sensitive error string is NOT in response body
    assert "Secret database connection" not in response.text
