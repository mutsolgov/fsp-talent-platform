"""
FSP IT-Talent Platform — Cooldown Reset Audit Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §3.4.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.candidate_profiles import CandidateProfile
    from app.models.users import User


class CooldownReset(Base):
    __tablename__ = "cooldown_resets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reset_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        String(255),
        server_default=sa.text("'Jury Demo Bypass'"),
        default="Jury Demo Bypass",
        nullable=False,
    )
    previous_cooldown_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )

    candidate_profile: Mapped["CandidateProfile"] = relationship(
        "CandidateProfile",
        back_populates="cooldown_resets",
    )
    reset_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="cooldown_resets",
    )
