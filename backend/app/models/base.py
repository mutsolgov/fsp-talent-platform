"""
FSP IT-Talent Platform — Declarative Base & Core Model Types.
"""
from __future__ import annotations

from datetime import datetime
import sqlalchemy as sa
from sqlalchemy import DateTime, JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Cross-dialect JSON type: PostgreSQL JSONB, SQLite/Standard JSON
JSON_TYPE = JSON().with_variant(postgresql.JSONB(), "postgresql")


class Base(DeclarativeBase):
    """Declarative Base for all FSP domain models."""
    pass


class TimestampMixin:
    """Mixin for models requiring created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )
