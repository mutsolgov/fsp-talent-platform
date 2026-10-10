"""
FSP IT-Talent Platform — Shortlist Item Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §6.4.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.saved_shortlists import SavedShortlist
    from app.models.candidate_profiles import CandidateProfile


class ShortlistItem(Base):
    __tablename__ = "shortlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shortlist_id: Mapped[int] = mapped_column(
        ForeignKey("saved_shortlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("false"),
        default=False,
        nullable=False,
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    delta_score: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("0.0"),
        default=0.0,
        nullable=False,
    )
    rank_position: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("1"),
        default=1,
        nullable=False,
    )
    explainability_json: Mapped[dict] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint("shortlist_id", "candidate_profile_id", name="uq_shortlist_cand"),
        CheckConstraint("match_score >= 0.0 AND match_score <= 100.0", name="chk_shortlist_items_score"),
        CheckConstraint("rank_position > 0", name="chk_shortlist_items_rank"),
        Index("ix_shortlist_items_shortlist", "shortlist_id"),
        Index("ix_shortlist_items_pinned", "shortlist_id", "is_pinned"),
        Index("ix_shortlist_items_score", "shortlist_id", "match_score"),
    )

    shortlist: Mapped["SavedShortlist"] = relationship(
        "SavedShortlist",
        back_populates="items",
    )
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="shortlist_items",
    )
