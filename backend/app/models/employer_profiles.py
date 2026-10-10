"""
FSP IT-Talent Platform — Employer Profile Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §6.1.
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.users import User
    from app.models.employer_needs import EmployerNeed
    from app.models.saved_shortlists import SavedShortlist
    from app.models.vacancies import Vacancy
    from app.models.invitations import Invitation
    from app.models.ats_integrations import AtsIntegration


class EmployerProfile(Base):
    __tablename__ = "employer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    inn: Mapped[str] = mapped_column(String(12), unique=True, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    is_inn_verified: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("false"),
        default=False,
        nullable=False,
    )
    trust_score: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("50"),
        default=50,
        nullable=False,
    )
    invite_daily_limit: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("20"),
        default=20,
        nullable=False,
    )
    invites_sent_today: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("0"),
        default=0,
        nullable=False,
    )
    last_invite_reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        default=datetime.now,
        nullable=False,
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[str] = mapped_column(
        String(100),
        server_default=sa.text("'Москва'"),
        default="Москва",
        nullable=False,
    )
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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
        UniqueConstraint("user_id", name="uq_employer_profiles_user"),
        UniqueConstraint("inn", name="uq_employer_profiles_inn"),
        CheckConstraint("length(inn) IN (10, 12)", name="chk_employer_inn_length"),
        CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="chk_employer_trust_score"),
        CheckConstraint("invite_daily_limit >= 0", name="chk_employer_daily_limit"),
        CheckConstraint("invites_sent_today >= 0", name="chk_employer_sent_today"),
    )

    user: Mapped["User"] = relationship("User", back_populates="employer_profile")
    employer_needs: Mapped[List["EmployerNeed"]] = relationship(
        "EmployerNeed",
        back_populates="employer_profile",
        cascade="all, delete-orphan",
    )
    saved_shortlists: Mapped[List["SavedShortlist"]] = relationship(
        "SavedShortlist",
        back_populates="employer_profile",
        cascade="all, delete-orphan",
    )
    vacancies: Mapped[List["Vacancy"]] = relationship(
        "Vacancy",
        back_populates="employer_profile",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="employer_profile",
        cascade="all, delete-orphan",
    )
    ats_integrations: Mapped[List["AtsIntegration"]] = relationship(
        "AtsIntegration",
        back_populates="employer_profile",
        cascade="all, delete-orphan",
    )
