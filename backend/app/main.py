"""FastAPI Main Application Entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    global_exception_handler,
    validation_error_handler,
)
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown events."""
    yield


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app_title = settings.PROJECT_NAME if settings else "AROVIA API"
    app_version = settings.VERSION if settings else "1.0.0"
    api_prefix = settings.API_V1_PREFIX if settings else "/api/v1"

    app = FastAPI(
        title=app_title,
        version=app_version,
        openapi_url=f"{api_prefix}/openapi.json",
        docs_url=f"{api_prefix}/docs",
        redoc_url=f"{api_prefix}/redoc",
        lifespan=lifespan,
    )

    # Attach Rate Limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    # Configure CORS Middleware
    allowed_origins = settings.ALLOWED_ORIGINS if settings else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Exception Handlers
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, global_exception_handler)

    # Mount API Routers
    app.include_router(api_router, prefix=api_prefix)

    return app


app = create_application()
