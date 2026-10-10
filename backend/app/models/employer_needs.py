"""
FSP IT-Talent Platform — Employer Need Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §6.2.
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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSON_TYPE

if TYPE_CHECKING:
    from app.models.employer_profiles import EmployerProfile
    from app.models.specializations import Specialization
    from app.models.grades import Grade
    from app.models.saved_shortlists import SavedShortlist
    from app.models.invitations import Invitation


class EmployerNeed(Base):
    __tablename__ = "employer_needs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employer_profile_id: Mapped[int] = mapped_column(
        ForeignKey("employer_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    specialization_id: Mapped[int] = mapped_column(
        ForeignKey("specializations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    core_stack_json: Mapped[list] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'[]'"),
        default=list,
        nullable=False,
    )
    nice_to_have_stack_json: Mapped[list] = mapped_column(
        JSON_TYPE,
        server_default=sa.text("'[]'"),
        default=list,
        nullable=False,
    )
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    work_format: Mapped[str] = mapped_column(
        String(64),
        server_default=sa.text("'remote'"),
        default="remote",
        nullable=False,
    )
    team_tasks_text: Mapped[str] = mapped_column(Text, nullable=False)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_employer_needs_salary"),
        CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_employer_needs_work_format"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="employer_needs")
    specialization: Mapped["Specialization"] = relationship("Specialization")
    target_grade: Mapped["Grade"] = relationship("Grade")
    saved_shortlists: Mapped[List["SavedShortlist"]] = relationship("SavedShortlist", back_populates="employer_need")
    invitations: Mapped[List["Invitation"]] = relationship("Invitation", back_populates="employer_need")
