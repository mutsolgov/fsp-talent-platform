"""
FSP IT-Talent Platform — Candidate Profile Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.3.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import EmailStr, Field, model_validator

from app.schemas.base import BaseSchema


class WorkFormatEnum(StrEnum):
    REMOTE = "remote"
    OFFICE = "office"
    HYBRID = "hybrid"
    ANY = "any"


class CandidateSkillItem(BaseSchema):
    skill_name: str = Field(..., min_length=1, max_length=100)
    years_of_experience: float = Field(default=1.0, ge=0.0, le=50.0)
    proficiency_level: str = Field(default="intermediate")
    is_core: bool = False
    verified_by_test: bool = False


class OnboardingSurveyRequest(BaseSchema):
    specialization_id: int = Field(..., description="ID канонической специализации (1..6)")
    claimed_grade_id: int = Field(..., description="Заявляемый начальный грейд (1..4)")
    skills: Any = Field(..., description="Ключевые технологии стека (список строк или объектов)")
    city: str = Field(default="Москва", min_length=2, max_length=100, description="Город проживания")
    work_format: WorkFormatEnum = Field(default=WorkFormatEnum.ANY)
    relocation_ready: bool = Field(default=False)
    expected_salary: Optional[int] = Field(None, gt=0, description="Ожидаемая заработная плата в рублях")
    salary_min: Optional[int] = Field(None, gt=0, description="Минимальная зарплата")
    salary_max: Optional[int] = Field(None, gt=0, description="Максимальная зарплата")
    salary_currency: Optional[Literal["RUB"]] = Field(default="RUB", description="Валюта заработной платы (строго RUB)")
    consent_personal_data: Optional[bool] = Field(default=True)
    consent_profile_publish: Optional[bool] = Field(default=True)
    bio: Optional[str] = Field(None, max_length=2000)
    about: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def validate_salary_bounds(self) -> "OnboardingSurveyRequest":
        if self.salary_min is not None and self.salary_min <= 0:
            raise ValueError("salary_min должен быть строго больше нуля (ERR_SALARY_MIN_NOT_POSITIVE)")
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
            ratio = self.salary_max / self.salary_min
            if ratio > 3.5:
                raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        return self


class OnboardingSurveyResponse(BaseSchema):
    profile_id: int
    category_assigned_preliminary: str = ""
    assessment_ready: bool = True
    next_action_url: str = "/api/v1/assessment/sessions/start"
    created_at: datetime
    status: str = "onboarding_completed"
    specialization: Optional[Dict[str, Any]] = None
    claimed_grade: Optional[Dict[str, Any]] = None


class CandidateFullProfileResponse(BaseSchema):
    id: int
    user_id: int
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    telegram: Optional[str] = None
    github_url: Optional[str] = None
    city: Optional[str] = None
    work_format: Optional[WorkFormatEnum] = None
    relocation_ready: bool = False
    expected_salary: Optional[int] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    bio: Optional[str] = None
    about: Optional[str] = None
    specialization: Optional[str] = None
    grade: Optional[str] = None
    category_title: Optional[str] = None
    skills: List[CandidateSkillItem] = []
    kite_score_scaled: float = 0.0
    theta: Optional[float] = None
    fsp_id: Optional[str] = None
    fsp_verified: bool
    fsp_badge: str
    freshness_score: float
    is_published: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def populate_compat_fields(self) -> CandidateFullProfileResponse:
        if self.theta is None and self.kite_score_scaled is not None:
            self.theta = self.kite_score_scaled
        return self


class CandidateProfileUpdateRequest(BaseSchema):
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=32)
    telegram: Optional[str] = Field(None, max_length=64)
    github_url: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    work_format: Optional[WorkFormatEnum] = None
    relocation_ready: Optional[bool] = None
    expected_salary: Optional[int] = Field(None, gt=0)
    salary_min: Optional[int] = Field(None, gt=0)
    salary_max: Optional[int] = Field(None, gt=0)
    salary_currency: Optional[Literal["RUB"]] = "RUB"
    bio: Optional[str] = Field(None, max_length=2000)
    about: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def validate_update_salary(self) -> "CandidateProfileUpdateRequest":
        if self.salary_currency is not None and self.salary_currency != "RUB":
            raise ValueError("Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)")
        if self.salary_min is not None and self.salary_min <= 0:
            raise ValueError("salary_min должен быть строго больше нуля (ERR_SALARY_MIN_NOT_POSITIVE)")
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
            ratio = self.salary_max / self.salary_min
            if ratio > 3.5:
                raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        return self


class CandidateCategoryStatusResponse(BaseSchema):
    candidate_id: int
    specialization_code: str
    grade_code: str
    category_badge: str
    is_grade_confirmed: bool
    cooldown_until: Optional[datetime] = None
    is_cooldown_active: bool
    days_left_cooldown: int
    status: str = "unverified"
    claimed_grade: Optional[str] = None
    verified_grade: Optional[str] = None


class FreshnessScoreResponse(BaseSchema):
    candidate_id: int
    freshness_score: float = Field(ge=0.0, le=100.0)
    half_life_days: int = 45
    last_activity_at: datetime
    activity_count_last_30d: int
    decay_status: Literal["active", "declining", "stale"]


class PrivacySettingsUpdateRequest(BaseSchema):
    is_published: bool = Field(..., description="Видимость профиля в Банке талантов")


class PrivacySettingsResponse(BaseSchema):
    candidate_id: int
    is_published: bool
    updated_at: datetime
