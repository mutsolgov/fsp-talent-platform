"""
FSP IT-Talent Platform — Vacancies Schemas (Module 10).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.10.
Mandatory Invariant: salary_min > 0 AND salary_max >= salary_min in RUB (spread <= 3.5).
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginationMeta
from app.schemas.candidate_profile import WorkFormatEnum


class VacancyStatusEnum(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"


class CreateVacancyRequest(BaseSchema):
    specialization_id: int = Field(..., description="ID специализации")
    grade_id: int = Field(..., description="ID грейда")
    title: str = Field(..., min_length=5, max_length=200, description="Название вакансии")
    description: str = Field(..., min_length=20, max_length=10000, description="Подробное описание вакансии")
    required_skills: List[str] = Field(..., min_length=1, description="Обязательный стек технологий")
    optional_skills: List[str] = Field(default_factory=list, description="Желательные навыки")
    salary_min: int = Field(..., gt=0, description="Минимальная зарплата в рублях (> 0)")
    salary_max: int = Field(..., gt=0, description="Максимальная зарплата в рублях (>= salary_min)")
    salary_currency: Literal["RUB"] = Field(default="RUB", description="Валюта оклада (строго RUB)")
    work_format: WorkFormatEnum = Field(default=WorkFormatEnum.ANY, description="Формат работы")
    city: Optional[str] = Field(default="Москва", max_length=100, description="Город локации")

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("salary_min должен быть строго больше нуля (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @model_validator(mode="after")
    def validate_salary_bounds(self) -> "CreateVacancyRequest":
        if self.salary_max < self.salary_min:
            raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        return self


class UpdateVacancyRequest(BaseSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=20, max_length=10000)
    specialization_id: Optional[int] = None
    grade_id: Optional[int] = None
    required_skills: Optional[List[str]] = None
    optional_skills: Optional[List[str]] = None
    salary_min: Optional[int] = Field(None, gt=0)
    salary_max: Optional[int] = Field(None, gt=0)
    salary_currency: Optional[Literal["RUB"]] = "RUB"
    work_format: Optional[WorkFormatEnum] = None
    city: Optional[str] = None
    status: Optional[VacancyStatusEnum] = None

    @model_validator(mode="after")
    def validate_update_salary(self) -> "UpdateVacancyRequest":
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
            ratio = self.salary_max / self.salary_min
            if ratio > 3.5:
                raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        return self


class UpdateVacancyStatusRequest(BaseSchema):
    status: VacancyStatusEnum = Field(..., description="Новый статус вакансии")


class VacancyDetailResponse(BaseSchema):
    id: int
    employer_profile_id: int
    employer_company_name: str
    specialization: str
    specialization_id: Optional[int] = None
    grade: str
    grade_id: Optional[int] = None
    title: str
    description: str
    required_skills: List[str]
    optional_skills: List[str] = Field(default_factory=list)
    salary_min: int
    salary_max: int
    salary_currency: Literal["RUB"] = "RUB"
    work_format: WorkFormatEnum
    city: Optional[str] = "Москва"
    status: VacancyStatusEnum
    applications_count: int = 0
    created_at: datetime
    updated_at: datetime


class PaginatedVacanciesResponse(BaseSchema):
    items: List[VacancyDetailResponse]
    meta: PaginationMeta


# Backward-compatible aliases
VacancyCreate = CreateVacancyRequest
VacancyUpdate = UpdateVacancyRequest
VacancyResponse = VacancyDetailResponse
