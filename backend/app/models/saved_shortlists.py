"""
FSP IT-Talent Platform — Saved Shortlist Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §6.3.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.employer_profiles import EmployerProfile
    from app.models.employer_needs import EmployerNeed
    from app.models.shortlist_items import ShortlistItem


class SavedShortlist(Base):
    __tablename__ = "saved_shortlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    need_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employer_needs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    filter_criteria_json: Mapped[dict] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'{}'"),
        default=dict,
        nullable=False,
    )
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

    employer_profile: Mapped["EmployerProfile"] = relationship(
        "EmployerProfile",
        back_populates="saved_shortlists",
    )
    employer_need: Mapped[Optional["EmployerNeed"]] = relationship(
        "EmployerNeed",
        back_populates="saved_shortlists",
    )
    items: Mapped[List["ShortlistItem"]] = relationship(
        "ShortlistItem",
        back_populates="shortlist",
        cascade="all, delete-orphan",
    )
