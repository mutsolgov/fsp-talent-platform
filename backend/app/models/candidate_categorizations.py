"""
FSP IT-Talent Platform — Candidate Categorization Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §3.4.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.candidate_profiles import CandidateProfile
    from app.models.categories import Category
    from app.models.grades import Grade


class CandidateCategorization(Base):
    __tablename__ = "candidate_categorizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    confirmed_grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    test_score: Mapped[float] = mapped_column(Float, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    cooldown_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("true"),
        default=True,
        nullable=False,
    )
    source_session_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("test_score >= 0.0 AND test_score <= 100.0", name="chk_candidate_cat_score"),
        Index("ix_candidate_cat_cand_curr", "candidate_profile_id", "is_current"),
        Index("ix_candidate_cat_cooldown", "cooldown_until"),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="candidate_categorizations",
    )
    category: Mapped["Category"] = relationship("Category")
    confirmed_grade: Mapped["Grade"] = relationship("Grade")
