"""Custom Application Exceptions and Global Exception Handlers."""

from typing import Any, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import logger


class AppError(Exception):
    """Base Application Exception class."""

    def __init__(
        self,
        message: str = "An error occurred",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
    ) -> None:
        msg = detail or message
        super().__init__(msg)
        self.message = msg
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class NotFoundError(AppError):
    """Resource Not Found Exception."""

    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "NOT_FOUND",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=detail or message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code=error_code,
            details=details,
        )


class UnauthorizedError(AppError):
    """Authentication Required / Invalid Credentials Exception."""

    def __init__(
        self,
        message: str = "Authentication required",
        error_code: str = "UNAUTHORIZED",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=detail or message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            details=details,
        )


class ForbiddenError(AppError):
    """Permission Denied Exception."""

    def __init__(
        self,
        message: str = "Permission denied",
        error_code: str = "FORBIDDEN",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=detail or message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code=error_code,
            details=details,
        )


class ConflictError(AppError):
    """Resource Conflict Exception."""

    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "CONFLICT",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=detail or message,
            status_code=status.HTTP_409_CONFLICT,
            error_code=error_code,
            details=details,
        )


class ValidationError(AppError):
    """Business Logic Validation Exception (HTTP 400)."""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: str = "VALIDATION_ERROR",
        details: Optional[dict[str, Any]] = None,
        detail: Optional[str] = None,
    ) -> None:
        super().__init__(
            message=detail or message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code=error_code,
            details=details,
        )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom AppError exceptions."""
    logger.warning(
        "AppError on %s %s: %s (code=%s)",
        request.method,
        request.url.path,
        exc.message,
        exc.error_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.error_code,
            **({"details": exc.details} if exc.details else {}),
        },
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI / Pydantic RequestValidationError."""
    logger.warning(
        "Validation error on %s %s: %s", request.method, request.url.path, exc.errors()
    )
    sanitized_errors = []
    for err in exc.errors():
        sanitized_errors.append(
            {
                "field": ".".join(
                    str(loc) for loc in err.get("loc", []) if loc != "body"
                ),
                "message": err.get("msg", "Invalid input"),
                "type": err.get("type", "value_error"),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": sanitized_errors,
        },
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all global exception handler that masks server stack traces."""
    logger.exception(
        "Unhandled server error on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        },
    )
