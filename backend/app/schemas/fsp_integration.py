"""
Pydantic v2 schemas for API Module 2: fsp-integration.
Defined in docs/04 §2.2.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Optional
from pydantic import Field

from app.schemas.base import BaseSchema


class SportRankEnum(StrEnum):
    KMS = "kms"
    MS = "ms"
    FIRST_CLASS = "first_class"
    NONE = "none"


class FspDisciplineEnum(StrEnum):
    ALGORITHMIC = "algorithmic"
    PRODUCT = "product"
    INFOSEC = "infosec"
    ROBOTICS = "robotics"


class MedalEnum(StrEnum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"
    PARTICIPANT = "participant"


class FspAchievementRead(BaseSchema):
    id: int
    championship_name: str
    discipline: FspDisciplineEnum
    stage: str
    year: int
    place: Optional[int] = None
    medal: Optional[MedalEnum] = None
    sport_rank_awarded: Optional[SportRankEnum] = None
    rating_points_earned: int = 0
    certificate_url: Optional[str] = None
    verified_at: datetime


class FspConnectRequest(BaseSchema):
    code: str = Field(..., description="Authorization code from Keycloak")
    redirect_uri: str = Field(..., description="Redirect URI registered in OIDC client")
    code_verifier: str = Field(..., min_length=10, max_length=128, description="PKCE code verifier")


class FspConnectResponse(BaseSchema):
    fsp_id: str
    fsp_verified: bool
    athlete_name: str
    sport_rank: SportRankEnum
    rating_points: int
    achievements_synced: int
    linked_at: datetime
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = "Bearer"
    role: Optional[str] = "candidate"
    user_id: Optional[int] = None
    email: Optional[str] = None



class FspProfileResponse(BaseSchema):
    is_fsp_candidate: bool = Field(..., description="False for candidates without FSP history")
    fsp_id: Optional[str] = Field(None, description="NULL for candidates without FSP profile")
    fsp_verified: bool = Field(False, description="Registry verified status")
    athlete_name: Optional[str] = None
    sport_rank: SportRankEnum = SportRankEnum.NONE
    sport_rank_title: str = Field(..., description="Readable rank title in Russian")
    rating_points: int = 0
    contests_count: int = 0
    badge_title: str = Field(..., description="Badge: 'Верифицирован ФСП' or 'Платформенная верификация'")
    achievements: List[FspAchievementRead] = Field(default_factory=list)
    last_synced_at: Optional[datetime] = None


class FspSyncRequest(BaseSchema):
    force_refresh: bool = Field(default=False, description="Force registry query")


class FspSyncResponse(BaseSchema):
    fsp_id: str
    achievements_total: int
    rating_points: int
    sport_rank: SportRankEnum
    synced_at: datetime


class FspIntegrationStatusResponse(BaseSchema):
    keycloak_reachable: bool
    registry_reachable: bool
    latency_ms: float
    checked_at: datetime


class StatusMessageResponse(BaseSchema):
    status: str
    message: str
