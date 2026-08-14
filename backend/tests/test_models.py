"""Tests for Base ORM models and mixins."""

import pytest
from app.db.base import Base, CommonModelMixin
from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column


class SampleItem(Base, CommonModelMixin):
    """Sample ORM model for testing mixin columns."""

    __tablename__ = "test_sample_items"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


@pytest.mark.asyncio
async def test_common_model_mixin_uuid_and_timestamps(test_engine, db_session):
    """Verify that CommonModelMixin automatically generates UUID id and created/updated timestamps."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    item = SampleItem(name="Test Item 1")
    db_session.add(item)
    await db_session.flush()

    assert item.id is not None
    assert len(item.id) == 36
    assert item.created_at is not None
    assert item.updated_at is not None

    # Query back
    result = await db_session.execute(
        select(SampleItem).where(SampleItem.id == item.id)
    )
    fetched_item = result.scalar_one_or_none()
    assert fetched_item is not None
    assert fetched_item.name == "Test Item 1"
