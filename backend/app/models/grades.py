"""
FSP IT-Talent Platform — Grade Qualification Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §2.2.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.categories import Category
    from app.models.canonical_item_families import CanonicalItemFamily
    from app.models.micro_challenges import MicroChallenge


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    rank_order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("code IN ('junior', 'middle', 'senior', 'lead')", name="chk_grades_code"),
        CheckConstraint("rank_order BETWEEN 1 AND 4", name="chk_grades_rank_order"),
    )

    categories: Mapped[List["Category"]] = relationship("Category", back_populates="grade")
    canonical_item_families: Mapped[List["CanonicalItemFamily"]] = relationship(
        "CanonicalItemFamily",
        back_populates="grade",
    )
    micro_challenges: Mapped[List["MicroChallenge"]] = relationship(
        "MicroChallenge",
        back_populates="grade",
    )
