"""
FSP IT-Talent Platform — ATS Integration Schemas (Module 12).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.12.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginationMeta
from app.schemas.candidate_profile import WorkFormatEnum
from app.schemas.vacancies import VacancyDetailResponse


class AtsProviderEnum(StrEnum):
    HUNTFLOW = "huntflow"
    HEADHUNTER = "headhunter"
    HH = "hh"
    CUSTOM_WEBHOOK = "custom_webhook"
    GENERIC_WEBHOOK = "generic_webhook"
    E_STAFF = "e_staff"
    POTOK = "potok"
    CUSTOM = "custom"


class AtsIntegrationConfigResponse(BaseSchema):
    id: int
    employer_profile_id: int
    ats_type: AtsProviderEnum
    webhook_url: Optional[str] = None
    has_webhook_secret: bool
    is_active: bool
    total_deliveries_count: int = 0
    successful_deliveries_count: int = 0
    dead_letter_count: int = 0
    last_delivery_at: Optional[datetime] = None


class UpdateAtsConfigRequest(BaseSchema):
    ats_type: AtsProviderEnum
    api_token: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = Field(None, min_length=16, max_length=128)
    is_active: bool = True


class AtsVacancyImportRequest(BaseSchema):
    external_ats_id: str
    title: str = Field(..., min_length=5, max_length=200)
    specialization_code: str
    grade_code: str
    description: str = Field(..., min_length=20)
    required_skills: List[str] = Field(..., min_length=1)
    salary_min: int = Field(..., gt=0, description="Минимальная зарплата в рублях (> 0)")
    salary_max: int = Field(..., gt=0, description="Максимальная зарплата в рублях (>= salary_min)")
    salary_currency: Literal["RUB"] = "RUB"
    work_format: WorkFormatEnum = WorkFormatEnum.ANY
    city: Optional[str] = None

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("salary_min должен быть строго больше нуля (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @model_validator(mode="after")
    def validate_salary_bounds(self) -> "AtsVacancyImportRequest":
        if self.salary_max < self.salary_min:
            raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        return self


class WebhookTestDispatchResponse(BaseSchema):
    delivered: bool
    http_status: Optional[int] = None
    latency_ms: float
    signature_header: str
    timestamp_header: int
    response_body_preview: Optional[str] = None


class WebhookDeliveryLogItem(BaseSchema):
    delivery_id: str
    event: str
    timestamp: int
    http_status: Optional[int] = None
    status: Literal["delivered", "retry_pending", "dead_letter", "rejected_by_receiver"]
    attempts_count: int
    last_attempt_at: datetime
    error_message: Optional[str] = None


class PaginatedWebhookLogsResponse(BaseSchema):
    items: List[WebhookDeliveryLogItem]
    meta: PaginationMeta


class WebhookRetryResponse(BaseSchema):
    delivery_id: str
    requeued: bool
    next_attempt_at: datetime


class HuntflowApplicantExportResponse(BaseSchema):
    applicant: Dict[str, Any]
    metadata: Dict[str, Any]


class HeadHunterResumeExportResponse(BaseSchema):
    resume: Dict[str, Any]


class ExportApplicantRequest(BaseSchema):
    candidate_id: int
    ats_type: AtsProviderEnum = AtsProviderEnum.HUNTFLOW


# Backward-compatible aliases
AtsSettingsResponse = AtsIntegrationConfigResponse
AtsSettingsUpdate = UpdateAtsConfigRequest
