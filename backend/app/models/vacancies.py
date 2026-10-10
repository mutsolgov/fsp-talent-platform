"""
FSP IT-Talent Platform — Vacancies Model.
Defined in docs/02_DOMAIN_MODEL_AND_DB_SCHEMA.md §7.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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
    from app.models.applications import Application
    from app.models.invitations import Invitation


class Vacancy(Base):
    __tablename__ = "vacancies"

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
    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills_json: Mapped[list] = mapped_column(
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
    city: Mapped[str] = mapped_column(
        String(100),
        server_default=sa.text("'Москва'"),
        default="Москва",
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        server_default=sa.text("'published'"),
        default="published",
        nullable=False,
        index=True,
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
        CheckConstraint("salary_min > 0 AND salary_max >= salary_min", name="chk_vacancies_salary"),
        CheckConstraint("status IN ('published', 'closed', 'draft', 'archived')", name="chk_vacancies_status"),
        CheckConstraint("work_format IN ('remote', 'office', 'hybrid', 'any')", name="chk_vacancies_work_format"),
        Index("ix_vacancies_spec_grade", "specialization_id", "grade_id"),
    )

    employer_profile: Mapped["EmployerProfile"] = relationship("EmployerProfile", back_populates="vacancies")
    specialization: Mapped["Specialization"] = relationship("Specialization")
    grade: Mapped["Grade"] = relationship("Grade")
    applications: Mapped[List["Application"]] = relationship(
        "Application",
        back_populates="vacancy",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[List["Invitation"]] = relationship(
        "Invitation",
        back_populates="vacancy",
    )
