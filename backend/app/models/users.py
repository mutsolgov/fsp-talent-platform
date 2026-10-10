"""
FSP IT-Talent Platform — User Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §1.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user_consents import UserConsent
    from app.models.audit_logs import AuditLog
    from app.models.candidate_profiles import CandidateProfile
    from app.models.cooldown_resets import CooldownReset
    from app.models.employer_profiles import EmployerProfile


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("false"), default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("role IN ('candidate', 'employer', 'admin')", name="chk_users_role"),
    )

    consent: Mapped[Optional["UserConsent"]] = relationship("UserConsent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user")
    candidate_profile: Mapped[Optional["CandidateProfile"]] = relationship("CandidateProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    cooldown_resets: Mapped[List["CooldownReset"]] = relationship("CooldownReset", back_populates="reset_by_user")
    employer_profile: Mapped[Optional["EmployerProfile"]] = relationship("EmployerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
