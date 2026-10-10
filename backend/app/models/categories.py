"""
FSP IT-Talent Platform — Composite Category Model (Specialization × Grade = 24).
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §2.3.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.specializations import Specialization
    from app.models.grades import Grade
    from app.models.assessment_sessions import AssessmentSession


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    grade_id: Mapped[int] = mapped_column(ForeignKey("grades.id", ondelete="RESTRICT"), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("specialization_id", "grade_id", name="uq_categories_spec_grade"),
    )

    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="categories")
    grade: Mapped["Grade"] = relationship("Grade", back_populates="categories")
    assessment_sessions: Mapped[List["AssessmentSession"]] = relationship(
        "AssessmentSession",
        back_populates="category",
    )
