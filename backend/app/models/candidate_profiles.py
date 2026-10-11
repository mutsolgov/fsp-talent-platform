"""
FSP IT-Talent Platform — Candidate Profile Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §3.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.candidate_skills import CandidateSkill
    from app.models.cooldown_resets import CooldownReset
    from app.models.assessment_sessions import AssessmentSession
    from app.models.challenge_submissions import ChallengeSubmission
    from app.models.candidate_categorizations import CandidateCategorization
    from app.models.shortlist_items import ShortlistItem
    from app.models.fsp_achievements import FspAchievement
    from app.models.invitations import Invitation
    from app.models.applications import Application


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    telegram: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default=None)
    relocation_ready: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), default=False, nullable=False)
    work_format: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default=None)
    expected_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_resume_pdf_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    survey_data_json: Mapped[dict] = mapped_column(JSON_TYPE, server_default=sa.text("'{}'"), default=dict, nullable=False)
    fsp_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, default=None, index=True)
    fsp_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), default=False, nullable=False)
    freshness_score: Mapped[float] = mapped_column(Float, server_default=sa.text("50.0"), default=50.0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_candidate_profiles_user"),
        CheckConstraint("work_format IS NULL OR work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_candidate_work_format"),
        CheckConstraint("expected_salary IS NULL OR expected_salary > 0", name="chk_candidate_salary"),
        CheckConstraint("freshness_score >= 0.0 AND freshness_score <= 100.0", name="chk_candidate_freshness"),
    )

    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")
    candidate_skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    cooldown_resets: Mapped[List["CooldownReset"]] = relationship(
        "CooldownReset",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    assessment_sessions: Mapped[List["AssessmentSession"]] = relationship(
        "AssessmentSession",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    challenge_submissions: Mapped[List["ChallengeSubmission"]] = relationship(
        "ChallengeSubmission",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    candidate_categorizations: Mapped[List["CandidateCategorization"]] = relationship(
        "CandidateCategorization",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    shortlist_items: Mapped[List["ShortlistItem"]] = relationship(
        "ShortlistItem",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    fsp_achievements: Mapped[List["FspAchievement"]] = relationship(
        "FspAchievement",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )
