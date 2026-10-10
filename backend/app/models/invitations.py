"""
FSP IT-Talent Platform — Invitations Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §7.2.
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
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.employer_profiles import EmployerProfile
    from app.models.candidate_profiles import CandidateProfile
    from app.models.employer_needs import EmployerNeed
    from app.models.vacancies import Vacancy


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    need_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employer_needs.id", ondelete="SET NULL"),
        nullable=True,
    )
    vacancy_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("vacancies.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_text: Mapped[str] = mapped_column(Text, nullable=False)
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    contact_method: Mapped[str] = mapped_column(
        String(50),
        server_default=sa.text("'platform'"),
        default="platform",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        server_default=sa.text("'sent'"),
        default="sent",
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )
    viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decline_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
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
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_invitations_salary"),
        CheckConstraint("status IN ('sent', 'viewed', 'accepted', 'declined', 'expired')", name="chk_invitations_status"),
        Index("ix_invitations_candidate_status", "candidate_profile_id", "status"),
        Index("ix_invitations_employer_status", "employer_profile_id", "status"),
        Index("ix_invitations_created", "created_at"),
        Index("ix_invitations_emp_cand_status", "employer_profile_id", "candidate_profile_id", "status"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="invitations")
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="invitations")
    employer_need: Mapped[Optional["EmployerNeed"]] = relationship("EmployerNeed", back_populates="invitations")
    vacancy: Mapped[Optional["Vacancy"]] = relationship("Vacancy", back_populates="invitations")
