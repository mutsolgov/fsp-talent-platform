"""
FSP IT-Talent Platform — Assessment Answer Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §4.3.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional
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
    from app.models.assessment_sessions import AssessmentSession
    from app.models.canonical_item_families import CanonicalItemFamily


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_family_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_item_families.id", ondelete="RESTRICT"),
        nullable=False,
    )
    variant_params_json: Mapped[dict] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'{}'"),
        default=dict,
        nullable=False,
    )
    variant_seed: Mapped[str] = mapped_column(
        String(64),
        server_default=sa.text("''"),
        default="",
        nullable=False,
    )
    candidate_answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_results_json: Mapped[dict] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'{}'"),
        default=dict,
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        server_default=sa.text("false"),
        default=False,
        nullable=False,
    )
    points_awarded: Mapped[float] = mapped_column(
        Float,
        server_default=sa.text("0.0"),
        default=0.0,
        nullable=False,
    )
    time_taken_sec: Mapped[int] = mapped_column(
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

    __table_args__ = (
        UniqueConstraint("session_id", "item_family_id", name="uq_session_item"),
        CheckConstraint("points_awarded >= 0.0", name="chk_assessment_answers_points"),
        CheckConstraint("time_taken_sec >= 0", name="chk_assessment_answers_time"),
    )

    session: Mapped["AssessmentSession"] = relationship(
        "AssessmentSession",
        back_populates="answers",
    )
    item_family: Mapped["CanonicalItemFamily"] = relationship(
        "CanonicalItemFamily",
        back_populates="assessment_answers",
    )
