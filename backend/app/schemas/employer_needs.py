"""
FSP IT-Talent Platform — Employer Needs Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.7.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginationMeta


class CreateEmployerNeedRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    specialization_id: int = Field(..., description="ID канонической специализации")
    grade_id: Optional[int] = Field(None, description="ID требуемого грейда")
    target_grade_id: Optional[int] = Field(None, description="ID целевого грейда")
    title: Optional[str] = Field(None, description="Наименование потребности команды")
    description: Optional[str] = Field(None, description="Описание задач и проекта")
    team_tasks_text: Optional[str] = Field(None, description="Текст задач команды")
    required_skills: Optional[List[str]] = Field(default=None, description="Обязательный стек технологий")
    core_stack: Optional[List[str]] = Field(default=None, description="Критический стек технологий")
    optional_skills: Optional[List[str]] = Field(default=None, description="Желательный стек технологий")
    nice_to_have_stack: Optional[List[str]] = Field(default=None, description="Желательный стек")
    salary_min: int = Field(..., gt=0, description="Минимальная зарплата в рублях (строго > 0)")
    salary_max: int = Field(..., gt=0, description="Максимальная зарплата в рублях (>= salary_min)")
    salary_currency: Literal["RUB"] = Field(default="RUB", description="Валюта компенсации (только рубли)")
    work_format: str = Field(default="remote")
    city: Optional[str] = Field(default="Москва", max_length=100)

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Минимальная зарплата должна быть строго положительной (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @field_validator("salary_currency")
    @classmethod
    def validate_salary_currency(cls, v: str) -> str:
        if v != "RUB":
            raise ValueError("Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)")
        return v

    @model_validator(mode="after")
    def validate_need_fields(self) -> "CreateEmployerNeedRequest":
        if self.salary_currency != "RUB":
            raise ValueError("Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)")
        if self.salary_max < self.salary_min:
            raise ValueError(
                f"salary_max ({self.salary_max}) не может быть меньше salary_min ({self.salary_min}) "
                f"(ERR_SALARY_MAX_LT_MIN)"
            )
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(
                f"Разброс зарплатной вилки {ratio:.2f} превышает допустимый предел 3.5 "
                f"(ERR_SUSPICIOUS_SALARY_SPREAD)"
            )
        if not self.target_grade_id and not self.grade_id:
            self.target_grade_id = 2  # default Middle
        elif self.grade_id and not self.target_grade_id:
            self.target_grade_id = self.grade_id

        return self


class UpdateEmployerNeedRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    specialization_id: Optional[int] = None
    target_grade_id: Optional[int] = None
    grade_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    team_tasks_text: Optional[str] = None
    required_skills: Optional[List[str]] = None
    core_stack: Optional[List[str]] = None
    optional_skills: Optional[List[str]] = None
    nice_to_have_stack: Optional[List[str]] = None
    salary_min: Optional[int] = Field(None, gt=0)
    salary_max: Optional[int] = Field(None, gt=0)
    salary_currency: Optional[Literal["RUB"]] = "RUB"
    work_format: Optional[str] = None
    city: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("salary_currency")
    @classmethod
    def validate_update_salary_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "RUB":
            raise ValueError("Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)")
        return v

    @model_validator(mode="after")
    def validate_update_salary(self) -> "UpdateEmployerNeedRequest":
        if self.salary_currency is not None and self.salary_currency != "RUB":
            raise ValueError("Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)")
        if self.salary_min is not None and self.salary_min <= 0:
            raise ValueError("salary_min must be positive (ERR_SALARY_MIN_NOT_POSITIVE)")
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
            if (self.salary_max / self.salary_min) > 3.5:
                raise ValueError("Разброс зарплатной вилки превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        return self


class EmployerNeedResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    employer_profile_id: int
    specialization_id: int
    target_grade_id: int
    title: str = "Потребность в специалисте"
    specialization: str = "backend"
    grade: str = "middle"
    description: str = ""
    team_tasks_text: str = ""
    required_skills: List[str] = Field(default_factory=list)
    core_stack: List[str] = Field(default_factory=list)
    optional_skills: List[str] = Field(default_factory=list)
    nice_to_have_stack: List[str] = Field(default_factory=list)
    salary_min: int
    salary_max: int
    salary_currency: Literal["RUB"] = "RUB"
    work_format: str = "remote"
    city: Optional[str] = "Москва"
    is_active: bool = True
    matched_candidates_count: int = 0
    created_at: datetime
    updated_at: datetime


class EmployerNeedListResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    items: List[EmployerNeedResponse]
    meta: PaginationMeta
