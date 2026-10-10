"""
FSP IT-Talent Platform — FSP Achievements Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §3.2.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.candidate_profiles import CandidateProfile


class FspAchievement(Base):
    __tablename__ = "fsp_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    fsp_id: Mapped[str] = mapped_column(String(64), nullable=False)
    championship_name: Mapped[str] = mapped_column(String(255), nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    stage: Mapped[str] = mapped_column(
        String(50),
        server_default=sa.text("'всероссийский'"),
        default="всероссийский",
        nullable=False,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    place: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    medal: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sport_rank: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    rating_points: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("0"),
        default=0,
        nullable=False,
    )
    certificate_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("discipline IN ('algorithmic', 'product', 'infosec', 'robotics')", name="chk_fsp_achievements_discipline"),
        CheckConstraint("year BETWEEN 2018 AND 2030", name="chk_fsp_achievements_year"),
        CheckConstraint("place IS NULL OR place > 0", name="chk_fsp_achievements_place"),
        CheckConstraint("medal IS NULL OR medal IN ('gold', 'silver', 'bronze', 'participant')", name="chk_fsp_achievements_medal"),
        CheckConstraint("sport_rank IS NULL OR sport_rank IN ('kms', 'ms', 'none', 'first_class')", name="chk_fsp_achievements_sport_rank"),
        CheckConstraint("rating_points >= 0", name="chk_fsp_achievements_rating"),
        Index("ix_fsp_achievements_candidate", "candidate_profile_id"),
        Index("ix_fsp_achievements_discipline", "discipline"),
        Index("ix_fsp_achievements_fsp_id", "fsp_id"),
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="fsp_achievements")
