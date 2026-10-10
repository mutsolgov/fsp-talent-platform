"""
Pydantic v2 schemas for API Module 9: invitations.
Defined in docs/04 §2.9.
Mandatory Invariant: salary_min > 0 AND salary_max >= salary_min in RUB (salary spread <= 3.5).
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema, PaginationMeta


class InvitationStatusEnum(StrEnum):
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class ContactMethodEnum(StrEnum):
    PLATFORM_CHAT = "platform_chat"
    PLATFORM = "platform"
    EMAIL = "email"
    TELEGRAM = "telegram"
    PHONE = "phone"


class SendInvitationRequest(BaseSchema):
    candidate_profile_id: int = Field(..., description="ID приглашаемого соискателя")
    proposal_text: str = Field(..., min_length=10, max_length=3000, description="Индивидуальное предложение")
    salary_min: int = Field(..., gt=0, description="Минимальный уровень оклада в рублях (строго > 0)")
    salary_max: int = Field(..., gt=0, description="Максимальный уровень оклада в рублях (>= salary_min)")
    salary_currency: Literal["RUB"] = Field(default="RUB", description="Только рубли РФ")
    contact_method: ContactMethodEnum = Field(default=ContactMethodEnum.PLATFORM)
    need_id: Optional[int] = None
    vacancy_id: Optional[int] = None

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Минимальная зарплата должна быть строго положительной (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @model_validator(mode="after")
    def validate_salary_range(self) -> "SendInvitationRequest":
        if self.salary_max < self.salary_min:
            raise ValueError(
                f"salary_max ({self.salary_max}) не может быть меньше salary_min ({self.salary_min}) "
                f"(ERR_SALARY_MAX_LT_MIN)"
            )
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(
                f"Разброс зарплатной вилки {ratio:.2f} превышает допустимый лимит 3.5 "
                f"(ERR_SUSPICIOUS_SALARY_SPREAD)"
            )
        return self


class InvitationResponse(BaseSchema):
    id: int
    employer_profile_id: int
    employer_company_name: str
    employer_inn: str
    candidate_profile_id: int
    candidate_display_name: str
    proposal_text: str
    salary_min: int
    salary_max: int
    salary_currency: Literal["RUB"] = "RUB"
    contact_method: ContactMethodEnum = ContactMethodEnum.PLATFORM
    status: InvitationStatusEnum
    need_id: Optional[int] = None
    vacancy_id: Optional[int] = None
    sent_at: datetime
    viewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    decline_reason: Optional[str] = None


class PaginatedInvitationsResponse(BaseSchema):
    items: List[InvitationResponse]
    meta: PaginationMeta


class InvitationActionResponse(BaseSchema):
    invitation_id: int
    status: InvitationStatusEnum
    unmasked_contacts_granted: bool
    resolved_at: datetime
    message: str


class DeclineInvitationRequest(BaseSchema):
    decline_reason: Optional[str] = Field(None, max_length=500)
