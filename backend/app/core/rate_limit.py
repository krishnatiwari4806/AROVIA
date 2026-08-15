"""Rate limiting configuration using SlowAPI."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],
    headers_enabled=True,
    enabled=(settings.ENVIRONMENT != "testing") if settings else True,
)
