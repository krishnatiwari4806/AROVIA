"""System Health Check Endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.health import HealthCheckResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="System and Database Health Check",
    description="Probes the live database connection and returns system status.",
)
async def check_health(db: Annotated[AsyncSession, Depends(get_db)]) -> HealthCheckResponse:
    """Execute a lightweight query against the database and return health metrics."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        db_status = "connected"
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connectivity check failed: {exc!s}",
        ) from exc

    return HealthCheckResponse(
        status="healthy",
        database=db_status,
        version=settings.VERSION if settings else "1.0.0",
        environment=settings.ENVIRONMENT if settings else "development",
    )
