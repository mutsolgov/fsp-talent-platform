"""
FSP IT-Talent Platform — ATS Integrations Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §7.4.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.employer_profiles import EmployerProfile


class AtsIntegration(Base):
    __tablename__ = "ats_integrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    ats_type: Mapped[str] = mapped_column(String(32), nullable=False)
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    webhook_signing_secret: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    webhook_delivery_logs_json: Mapped[list] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'[]'"),
        default=list,
        nullable=False,
    )
    events_subscribed_json: Mapped[list] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'[]'"),
        default=list,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("true"),
        default=True,
        nullable=False,
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_count: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("0"),
        default=0,
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
        UniqueConstraint("employer_profile_id", "ats_type", name="uq_employer_ats_type"),
        CheckConstraint(
            "ats_type IN ('huntflow', 'hh', 'headhunter', 'e_staff', 'potok', 'custom', 'custom_webhook')",
            name="chk_ats_type",
        ),
        Index("ix_ats_integrations_employer", "employer_profile_id"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="ats_integrations")
