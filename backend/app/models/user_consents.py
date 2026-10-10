"""
FSP IT-Talent Platform — 152-ФЗ User Consent Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §1.2.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.users import User


class UserConsent(Base):
    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    consent_pdn_processing: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_profile_publication: Mapped[bool] = mapped_column(Boolean, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(32), server_default=sa.text("'v1.0-2026'"), default="v1.0-2026", nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("consent_pdn_processing IS TRUE OR revoked_at IS NOT NULL", name="chk_user_consents_active"),
    )

    user: Mapped["User"] = relationship("User", back_populates="consent")
