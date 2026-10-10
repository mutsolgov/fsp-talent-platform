"""
FSP IT-Talent Platform — Assessment Session Model (KITE Engine).
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §4.2.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.candidate_profiles import CandidateProfile
    from app.models.categories import Category
    from app.models.assessment_answers import AssessmentAnswer


class AssessmentSession(Base):
    __tablename__ = "assessment_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_type: Mapped[str] = mapped_column(
        String(32),
        server_default=sa.text("'initial'"),
        default="initial",
        nullable=False,
    )
    seed_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        server_default=sa.text("'in_progress'"),
        default="in_progress",
        nullable=False,
    )
    raw_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    theta_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    time_spent_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "session_type IN ('initial', 'boost', 'retest_lower')",
            name="chk_assessment_session_type",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'submitted', 'expired', 'cancelled', 'abandoned')",
            name="chk_assessment_session_status",
        ),
        CheckConstraint(
            "theta_score IS NULL OR (theta_score >= 0.0 AND theta_score <= 100.0)",
            name="chk_assessment_session_theta",
        ),
        CheckConstraint(
            "verdict IS NULL OR verdict IN ('confirmed', 'boost_offered', 'retest_lower_offered', 'lower_grade_offered', 'failed')",
            name="chk_assessment_session_verdict",
        ),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="assessment_sessions",
    )
    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="assessment_sessions",
    )
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
    )
