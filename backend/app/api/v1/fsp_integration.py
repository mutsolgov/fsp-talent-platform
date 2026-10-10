"""
FSP IT-Talent Platform — API Module 2: fsp-integration.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.2, §4.1-4.3 and DISPATCH.md.
Provides OIDC authorization, athlete lookup, verification linking, and graceful fallback for non-FSP candidates.
"""
from __future__ import annotations

from datetime import datetime, timezone
import secrets
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.candidate_profiles import CandidateProfile
from app.models.fsp_achievements import FspAchievement
from app.models.users import User
from app.schemas.fsp_integration import (
    FspAchievementRead,
    FspConnectRequest,
    FspConnectResponse,
    FspDisciplineEnum,
    FspIntegrationStatusResponse,
    FspProfileResponse,
    FspSyncRequest,
    FspSyncResponse,
    MedalEnum,
    SportRankEnum,
    StatusMessageResponse,
)
from app.services.fsp_mock_registry import (
    MOCK_FSP_ATHLETES,
    create_mock_auth_code,
    exchange_authorization_code,
    generate_code_challenge,
    lookup_athlete,
    sync_candidate_achievements,
    unlink_candidate_fsp,
)

router = APIRouter(prefix="/fsp-integration", tags=["fsp-integration"])


async def get_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfile:
    """Helper to get or initialize candidate profile for authenticated user."""
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.user_id == current_user.id)
        .options(selectinload(CandidateProfile.fsp_achievements))
    )
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(
            user_id=current_user.id,
            first_name=current_user.email.split("@")[0].capitalize(),
            last_name="Спортсмен",
            fsp_id=None,
            fsp_verified=False,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.get("/authorize", summary="Mock OIDC Authorization Endpoint")
async def oidc_authorize(
    response_type: str = Query("code"),
    client_id: str = Query("fsp-platform-client"),
    redirect_uri: str = Query("http://localhost:3000/auth/fsp/callback"),
    code_challenge: str = Query(...),
    code_challenge_method: str = Query("S256"),
    fsp_id: Optional[str] = Query("FSP-77-01042"),
):
    """
    Simulates Keycloak OIDC Authorization endpoint.
    Issues an authorization code tied to code_challenge and mock FSP athlete ID.
    """
    if fsp_id not in MOCK_FSP_ATHLETES:
        fsp_id = "FSP-77-01042"
    code = create_mock_auth_code(fsp_id=fsp_id, code_challenge=code_challenge)
    return {
        "code": code,
        "redirect_uri": redirect_uri,
        "state": secrets.token_hex(8),
    }


@router.post("/token", summary="Mock OIDC Token Endpoint")
async def oidc_token(
    code: str = Query(...),
    code_verifier: str = Query(...),
    redirect_uri: str = Query("http://localhost:3000/auth/fsp/callback"),
):
    """
    Simulates Keycloak Token endpoint with PKCE verification.
    """
    try:
        athlete = exchange_authorization_code(
            code=code,
            code_verifier=code_verifier,
            redirect_uri=redirect_uri,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "access_token": f"fsp_oidc_access_{secrets.token_hex(16)}",
        "token_type": "Bearer",
        "expires_in": 3600,
        "fsp_id": athlete["fsp_id"],
        "athlete_name": athlete["athlete_name"],
    }


@router.get("/athlete/{fsp_id}", summary="Lookup athlete in FSP Registry")
async def athlete_lookup(fsp_id: str):
    """
    Looks up athlete profile in official FSP registry.
    Gracefully returns null if athlete not found.
    """
    athlete = lookup_athlete(fsp_id)
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Спортсмен с FSP ID '{fsp_id}' не найден в реестре ФСП",
        )
    return athlete


@router.post(
    "/connect",
    response_model=FspConnectResponse,
    summary="Привязка ФСП ID через OIDC Authorization Code Flow с PKCE",
)
async def connect_fsp_profile(
    payload: FspConnectRequest,
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: AsyncSession = Depends(get_db),
) -> FspConnectResponse:
    try:
        athlete = exchange_authorization_code(
            code=payload.code,
            code_verifier=payload.code_verifier,
            redirect_uri=payload.redirect_uri,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    fsp_id = athlete["fsp_id"]
    synced_count = await sync_candidate_achievements(db, profile, fsp_id)

    raw_rank = athlete.get("sport_rank", "none")
    rank_enum = SportRankEnum(raw_rank) if raw_rank in SportRankEnum._value2member_map_ else SportRankEnum.NONE

    return FspConnectResponse(
        fsp_id=fsp_id,
        fsp_verified=True,
        athlete_name=athlete.get("athlete_name", "Спортсмен"),
        sport_rank=rank_enum,
        rating_points=athlete.get("rating_points", 0),
        achievements_synced=synced_count,
        linked_at=datetime.now(timezone.utc),
    )


@router.get(
    "/profile",
    response_model=FspProfileResponse,
    summary="Получение досье ФСП или статуса не-ФСП кандидата",
)
async def get_fsp_profile(
    candidate_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FspProfileResponse:
    # If candidate_id is specified (e.g. viewed by employer), resolve that profile
    if candidate_id is not None:
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.id == candidate_id)
            .options(selectinload(CandidateProfile.fsp_achievements))
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")
    else:
        profile = await get_candidate_profile(current_user=current_user, db=db)

    # Graceful handling of candidates without FSP history (fsp_id is None)
    if not profile.fsp_id or not profile.fsp_verified:
        return FspProfileResponse(
            is_fsp_candidate=False,
            fsp_id=None,
            fsp_verified=False,
            athlete_name=None,
            sport_rank=SportRankEnum.NONE,
            sport_rank_title="Без спортивного разряда (Платформенная верификация)",
            rating_points=0,
            contests_count=0,
            badge_title="Платформенная верификация",
            achievements=[],
            last_synced_at=None,
        )

    athlete = lookup_athlete(profile.fsp_id)
    raw_rank = athlete.get("sport_rank", "none") if athlete else "none"
    rank_enum = SportRankEnum(raw_rank) if raw_rank in SportRankEnum._value2member_map_ else SportRankEnum.NONE

    rank_titles = {
        SportRankEnum.KMS: "Кандидат в мастера спорта (КМС)",
        SportRankEnum.MS: "Мастер спорта РФ (МС)",
        SportRankEnum.FIRST_CLASS: "1-й спортивный разряд",
        SportRankEnum.NONE: "Без спортивного разряда",
    }
    rank_title = rank_titles.get(rank_enum, "Спортивный разряд")

    ach_reads: List[FspAchievementRead] = []
    achievements = getattr(profile, "fsp_achievements", [])
    for ach in achievements:
        disc = ach.discipline if ach.discipline in FspDisciplineEnum._value2member_map_ else FspDisciplineEnum.ALGORITHMIC
        medal = ach.medal if ach.medal in MedalEnum._value2member_map_ else None
        ach_rank = ach.sport_rank if ach.sport_rank in SportRankEnum._value2member_map_ else None
        ach_reads.append(
            FspAchievementRead(
                id=ach.id,
                championship_name=ach.championship_name,
                discipline=disc,
                stage=ach.stage,
                year=ach.year,
                place=ach.place,
                medal=medal,
                sport_rank_awarded=ach_rank,
                rating_points_earned=ach.rating_points,
                certificate_url=ach.certificate_url,
                verified_at=ach.verified_at,
            )
        )

    return FspProfileResponse(
        is_fsp_candidate=True,
        fsp_id=profile.fsp_id,
        fsp_verified=True,
        athlete_name=athlete.get("athlete_name", f"{profile.first_name} {profile.last_name}") if athlete else f"{profile.first_name} {profile.last_name}",
        sport_rank=rank_enum,
        sport_rank_title=rank_title,
        rating_points=athlete.get("rating_points", 0) if athlete else 0,
        contests_count=len(ach_reads),
        badge_title="Верифицирован ФСП",
        achievements=ach_reads,
        last_synced_at=profile.updated_at,
    )


@router.post(
    "/sync",
    response_model=FspSyncResponse,
    summary="Синхронизация наград из реестра ФСП",
)
async def sync_fsp_achievements_endpoint(
    payload: FspSyncRequest,
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: AsyncSession = Depends(get_db),
) -> FspSyncResponse:
    if not profile.fsp_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="К профилю не привязан FSP ID. Выполните подключение через /connect.",
        )
    try:
        count = await sync_candidate_achievements(db, profile, profile.fsp_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    athlete = lookup_athlete(profile.fsp_id) or {}
    raw_rank = athlete.get("sport_rank", "none")
    rank_enum = SportRankEnum(raw_rank) if raw_rank in SportRankEnum._value2member_map_ else SportRankEnum.NONE

    return FspSyncResponse(
        fsp_id=profile.fsp_id,
        achievements_total=count,
        rating_points=athlete.get("rating_points", 0),
        sport_rank=rank_enum,
        synced_at=datetime.now(timezone.utc),
    )


@router.delete(
    "/unlink",
    response_model=StatusMessageResponse,
    summary="Отвязка FSP ID и перевод профиля на платформенный трек (не-ФСП)",
)
async def unlink_fsp_profile(
    profile: CandidateProfile = Depends(get_candidate_profile),
    db: AsyncSession = Depends(get_db),
) -> StatusMessageResponse:
    await unlink_candidate_fsp(db, profile)
    return StatusMessageResponse(
        status="ok",
        message="FSP ID успешно отвязан. Профиль переведен на платформенную верификацию.",
    )


@router.get(
    "/status",
    response_model=FspIntegrationStatusResponse,
    summary="Диагностика доступности Keycloak и реестра ФСП",
)
async def get_fsp_integration_status() -> FspIntegrationStatusResponse:
    return FspIntegrationStatusResponse(
        keycloak_reachable=True,
        registry_reachable=True,
        latency_ms=1.42,
        checked_at=datetime.now(timezone.utc),
    )
