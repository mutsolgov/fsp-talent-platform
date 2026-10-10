"""
FSP IT-Talent Platform — Canonical Item Family Model (KITE IRT 3PL).
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §4.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List
import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.specializations import Specialization
    from app.models.grades import Grade
    from app.models.assessment_answers import AssessmentAnswer


class CanonicalItemFamily(Base):
    __tablename__ = "canonical_item_families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    specialization_id: Mapped[int] = mapped_column(
        ForeignKey("specializations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    family_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    param_matrix_json: Mapped[dict] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'{}'"),
        default=dict,
        nullable=False,
    )
    test_generator_code: Mapped[str] = mapped_column(Text, nullable=False)
    param_a: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("1.0"),
        default=1.0,
        nullable=False,
    )
    param_b: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("0.0"),
        default=0.0,
        nullable=False,
    )
    param_c: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("0.2"),
        default=0.2,
        nullable=False,
    )
    time_limit_sec: Mapped[int] = mapped_column(
        Integer,
        server_default=sa.text("1200"),
        default=1200,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint("family_code", name="uq_canonical_items_family_code"),
        CheckConstraint(
            "task_type IN ('algorithmic', 'system_design', 'code_triage', 'code_sandbox', 'mcq')",
            name="chk_canonical_items_task_type",
        ),
        CheckConstraint("param_a > 0.0", name="chk_canonical_items_param_a"),
        CheckConstraint("param_c >= 0.0 AND param_c <= 1.0", name="chk_canonical_items_param_c"),
        CheckConstraint("time_limit_sec > 0", name="chk_canonical_items_time"),
    )

    specialization: Mapped["Specialization"] = relationship(
        "Specialization",
        back_populates="canonical_item_families",
    )
    grade: Mapped["Grade"] = relationship(
        "Grade",
        back_populates="canonical_item_families",
    )
    assessment_answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="item_family",
    )
