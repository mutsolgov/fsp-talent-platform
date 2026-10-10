"""
FSP IT-Talent Platform — Applications Schemas (Module 11).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.11.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional
from pydantic import Field

from app.schemas.base import BaseSchema, PaginationMeta
from app.schemas.candidate_bank import CandidateUnmaskedContactsResponse


class ApplicationStatusEnum(StrEnum):
    APPLIED = "applied"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class CreateApplicationRequest(BaseSchema):
    vacancy_id: int = Field(..., description="ID открытой вакансии")
    cover_letter: Optional[str] = Field(None, max_length=2000, description="Сопроводительное письмо")


class ApplicationDetailResponse(BaseSchema):
    id: int
    vacancy_id: int
    vacancy_title: str
    employer_company_name: str
    candidate_profile_id: int
    cover_letter: Optional[str] = None
    status: ApplicationStatusEnum
    applied_at: datetime
    viewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class UpdateApplicationStatusRequest(BaseSchema):
    status: ApplicationStatusEnum = Field(..., description="Новый статус отклика")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Причина отклонения (при статусе rejected)")


class ApplicationEmployerItem(BaseSchema):
    application: ApplicationDetailResponse
    candidate_contacts: CandidateUnmaskedContactsResponse


class PaginatedApplicationsEmployerResponse(BaseSchema):
    items: List[ApplicationEmployerItem]
    meta: PaginationMeta


class PaginatedApplicationsCandidateResponse(BaseSchema):
    items: List[ApplicationDetailResponse]
    meta: PaginationMeta


# Backward-compatible aliases
ApplicationCreate = CreateApplicationRequest
ApplicationResponse = ApplicationDetailResponse
