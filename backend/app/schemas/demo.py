"""
FSP IT-Talent Platform — Pydantic v2 Models for Module 14: demo (Jury Dashboard).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.14.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema, UserRole


class DemoRoleEnum(StrEnum):
    CANDIDATE_WITH_FSP = "candidate_with_fsp"
    CANDIDATE_WITHOUT_FSP = "candidate_without_fsp"
    EMPLOYER = "employer"
    ADMIN = "admin"


class DemoSwitchRoleRequest(BaseSchema):
    role: DemoRoleEnum = Field(..., description="Выбираемая демо-роль для проверки")


class DemoSwitchRoleResponse(BaseSchema):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user_id: int
    email: EmailStr
    role: UserRole
    profile_id: int
    persona_title: str
    persona_description_ru: str
    recommended_tour_steps: List[str]


class DemoResetCooldownRequest(BaseSchema):
    reason: str = Field(default="Jury evaluation bypass", max_length=200)
    is_demo_bypass: Optional[bool] = Field(default=True, description="Jury demo cooldown bypass flag")


class DemoResetCooldownResponse(BaseSchema):
    candidate_id: int
    cooldown_cleared: Literal[True] = True
    is_demo_bypass: Literal[True] = True
    cooldown_reset_log_id: int
    message: str = "Кулдаун 90 дней успешно аннулирован. Доступ к тесту KITE открыт моментально."
    cleared_at: datetime


class DemoSeedRequest(BaseSchema):
    reset_database: bool = Field(default=False)
    seed_golden_dataset: bool = Field(default=True)


class DemoSeedResponse(BaseSchema):
    seeded_candidates_count: int
    seeded_needs_count: int
    seeded_vacancies_count: int
    seeded_invitations_count: int
    elapsed_ms: float


class DemoMetricsResponse(BaseSchema):
    total_candidates: int
    fsp_verified_candidates: int
    non_fsp_candidates: int
    total_employers: int
    active_employer_needs: int
    active_vacancies: int
    total_invitations_sent: int
    invitations_accepted_percent: float
    system_uptime_hours: float
    system_status: Literal["operational", "degraded"]
