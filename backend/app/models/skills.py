"""
FSP IT-Talent Platform — Skill Model (350+ Skills Taxonomy).
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §2.4.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.specializations import Specialization
    from app.models.candidate_skills import CandidateSkill


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    specialization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("specializations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_tag: Mapped[str] = mapped_column(
        String(50),
        server_default=sa.text("'general'"),
        default="general",
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
        server_default=sa.text("true"),
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    specialization: Mapped[Optional["Specialization"]] = relationship("Specialization", back_populates="skills")
    candidate_skills: Mapped[List["CandidateSkill"]] = relationship(
        "CandidateSkill",
        back_populates="skill",
    )
