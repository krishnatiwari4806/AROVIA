"""Asynchronous Database Session and Engine Management."""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_engine_instance() -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pool and SQLite concurrency pragmas."""
    db_url = settings.DATABASE_URL if settings else "sqlite+aiosqlite:///:memory:"

    # SQLite in-memory / file connection with WAL mode and concurrency resilience
    if "sqlite" in db_url:
        sqlite_engine = create_async_engine(
            db_url,
            connect_args={
                "check_same_thread": False,
                "timeout": 30.0,
            },
        )

        @event.listens_for(sqlite_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.close()

        return sqlite_engine

    return create_async_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


# Engine and session factory instances
engine: AsyncEngine = create_engine_instance()
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for yielding an active async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
