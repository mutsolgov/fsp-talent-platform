"""
FSP IT-Talent Platform — Specialization Reference Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §2.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.categories import Category
    from app.models.skills import Skill
    from app.models.canonical_item_families import CanonicalItemFamily
    from app.models.micro_challenges import MicroChallenge


class Specialization(Base):
    __tablename__ = "specializations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sa.text("true"), default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "code IN ('backend', 'frontend', 'ml_data', 'devops', 'qa', 'infosec')",
            name="chk_specializations_code",
        ),
    )

    categories: Mapped[List["Category"]] = relationship("Category", back_populates="specialization")
    skills: Mapped[List["Skill"]] = relationship("Skill", back_populates="specialization")
    canonical_item_families: Mapped[List["CanonicalItemFamily"]] = relationship(
        "CanonicalItemFamily",
        back_populates="specialization",
    )
    micro_challenges: Mapped[List["MicroChallenge"]] = relationship(
        "MicroChallenge",
        back_populates="specialization",
    )
