"""
FSP IT-Talent Platform — Candidate Skill Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §3.3.
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
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.candidate_profiles import CandidateProfile
    from app.models.skills import Skill


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    years_experience: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("1.0"),
        default=1.0,
        nullable=False,
    )
    proficiency_level: Mapped[str] = mapped_column(
        String(20),
        server_default=sa.text("'intermediate'"),
        default="intermediate",
        nullable=False,
    )
    is_core: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("false"),
        default=False,
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("false"),
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("candidate_profile_id", "skill_id", name="uq_candidate_skills"),
        CheckConstraint("years_experience >= 0.0", name="chk_candidate_skills_years"),
        CheckConstraint(
            "proficiency_level IN ('beginner', 'intermediate', 'advanced', 'expert')",
            name="chk_candidate_skills_level",
        ),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="candidate_skills",
    )
    skill: Mapped["Skill"] = relationship(
        "Skill",
        back_populates="candidate_skills",
    )
