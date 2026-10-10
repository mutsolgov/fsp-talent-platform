"""
FSP IT-Talent Platform — Employer Profile Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md and REQ-28.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import Field

from app.schemas.base import BaseSchema


class EmployerProfileResponse(BaseSchema):
    id: int
    user_id: int
    company_name: str
    inn: str
    domain: str
    is_inn_verified: bool
    trust_score: int
    invite_daily_limit: int
    invites_sent_today: int
    last_invite_reset_at: datetime
    logo_url: Optional[str] = None
    description: Optional[str] = None
    city: str
    website: Optional[str] = None
    active_needs_count: int = 0
    ats_connected: bool = False
    created_at: datetime
    updated_at: datetime


class EmployerProfileUpdateRequest(BaseSchema):
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    inn: Optional[str] = Field(None, min_length=10, max_length=12)
    domain: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    city: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    logo_url: Optional[str] = Field(None, max_length=500)


class EmployerTrustStatusResponse(BaseSchema):
    trust_score: int
    is_inn_verified: bool
    invite_daily_limit: int
    invites_sent_today: int
    remaining_invites_today: int
    can_send_invites: bool
