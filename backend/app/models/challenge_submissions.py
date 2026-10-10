"""
FSP IT-Talent Platform — Challenge Submission Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §5.2.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.micro_challenges import MicroChallenge
    from app.models.candidate_profiles import CandidateProfile


class ChallengeSubmission(Base):
    __tablename__ = "challenge_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(
        ForeignKey("micro_challenges.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    solution_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("0"),
        default=0,
        nullable=False,
    )
    memory_kb: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("0"),
        default=0,
        nullable=False,
    )
    test_results_json: Mapped[dict] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'{}'"),
        default=dict,
        nullable=False,
    )
    freshness_points_awarded: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("0.0"),
        default=0.0,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('passed', 'failed', 'timeout', 'error')",
            name="chk_challenge_submission_status",
        ),
        CheckConstraint("execution_time_ms >= 0", name="chk_challenge_submission_time"),
        CheckConstraint("memory_kb >= 0", name="chk_challenge_submission_memory"),
        CheckConstraint("freshness_points_awarded >= 0.0", name="chk_challenge_submission_freshness"),
    )

    challenge: Mapped["MicroChallenge"] = relationship(
        "MicroChallenge",
        back_populates="submissions",
    )
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="challenge_submissions",
    )
