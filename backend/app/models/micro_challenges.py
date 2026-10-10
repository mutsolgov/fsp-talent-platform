"""
FSP IT-Talent Platform — Micro Challenge Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §5.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.specializations import Specialization
    from app.models.grades import Grade
    from app.models.challenge_submissions import ChallengeSubmission


class MicroChallenge(Base):
    __tablename__ = "micro_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    specialization_id: Mapped[int] = mapped_column(
        ForeignKey("specializations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code_stub: Mapped[str] = mapped_column(Text, nullable=False)
    test_cases_json: Mapped[list] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'[]'"),
        default=list,
        nullable=False,
    )
    points: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("20"),
        default=20,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("true"),
        default=True,
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
        CheckConstraint("points > 0 AND points <= 100", name="chk_micro_challenges_points"),
    )

    specialization: Mapped["Specialization"] = relationship(
        "Specialization",
        back_populates="micro_challenges",
    )
    grade: Mapped["Grade"] = relationship(
        "Grade",
        back_populates="micro_challenges",
    )
    submissions: Mapped[List["ChallengeSubmission"]] = relationship(
        "ChallengeSubmission",
        back_populates="challenge",
        cascade="all, delete-orphan",
    )
