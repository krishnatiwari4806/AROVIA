"""Health Check Schema Models."""

from pydantic import BaseModel, ConfigDict


class HealthCheckResponse(BaseModel):
    """Response payload for system health check endpoint."""

    status: str
    database: str
    version: str
    environment: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "database": "connected",
                "version": "1.0.0",
                "environment": "development",
            }
        }
    )
