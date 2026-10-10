"""
FSP IT-Talent Platform — Employer Profile Management API Router.
Defined in REQ-28 and docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_employer, get_db
from app.models.ats_integrations import AtsIntegration
from app.models.employer_needs import EmployerNeed
from app.models.employer_profiles import EmployerProfile
from app.schemas.employer_profiles import (
    EmployerProfileResponse,
    EmployerProfileUpdateRequest,
    EmployerTrustStatusResponse,
)
from app.services.antifraud_service import (
    can_send_invitation,
    verify_corporate_domain,
    verify_inn,
)

router = APIRouter(prefix="/employer-profiles", tags=["employer-profiles"])


async def _build_profile_response(
    employer: EmployerProfile,
    db: AsyncSession,
) -> EmployerProfileResponse:
    """Helper to assemble EmployerProfileResponse with computed active needs and ATS flags."""
    active_needs_count = (
        await db.execute(
            select(func.count(EmployerNeed.id)).where(
                EmployerNeed.employer_profile_id == employer.id,
                EmployerNeed.is_active.is_(True),
            )
        )
    ).scalar() or 0

    ats_count = (
        await db.execute(
            select(func.count(AtsIntegration.id)).where(
                AtsIntegration.employer_profile_id == employer.id,
                AtsIntegration.is_active.is_(True),
            )
        )
    ).scalar() or 0

    return EmployerProfileResponse(
        id=employer.id,
        user_id=employer.user_id,
        company_name=employer.company_name,
        inn=employer.inn,
        domain=employer.domain,
        is_inn_verified=employer.is_inn_verified,
        trust_score=employer.trust_score,
        invite_daily_limit=employer.invite_daily_limit,
        invites_sent_today=employer.invites_sent_today,
        last_invite_reset_at=employer.last_invite_reset_at,
        logo_url=employer.logo_url,
        description=employer.description,
        city=employer.city,
        website=employer.website,
        active_needs_count=active_needs_count,
        ats_connected=ats_count > 0,
        created_at=employer.created_at,
        updated_at=employer.updated_at,
    )


@router.get(
    "/me",
    response_model=EmployerProfileResponse,
    summary="Получение профиля текущего работодателя",
)
async def get_my_employer_profile(
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerProfileResponse:
    return await _build_profile_response(employer, db)


@router.put(
    "/me",
    response_model=EmployerProfileResponse,
    summary="Обновление профиля компании работодателя",
)
async def update_my_employer_profile(
    data: EmployerProfileUpdateRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerProfileResponse:
    if data.inn is not None:
        if not verify_inn(data.inn):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Некорректный контрольный разряд ИНН (ERR_INVALID_INN)",
            )
        stmt = select(EmployerProfile).where(
            EmployerProfile.inn == data.inn,
            EmployerProfile.id != employer.id,
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Организация с данным ИНН уже зарегистрирована (ERR_INN_ALREADY_REGISTERED)",
            )
        employer.inn = data.inn

    if data.domain is not None:
        is_valid, err_msg = verify_corporate_domain(data.domain)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=err_msg or "Некорректный корпоративный домен",
            )
        employer.domain = data.domain

    if data.company_name is not None:
        employer.company_name = data.company_name
    if data.description is not None:
        employer.description = data.description
    if data.city is not None:
        employer.city = data.city
    if data.website is not None:
        employer.website = data.website
    if data.logo_url is not None:
        employer.logo_url = data.logo_url

    employer.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(employer)

    return await _build_profile_response(employer, db)


@router.get(
    "/me/trust-status",
    response_model=EmployerTrustStatusResponse,
    summary="Проверка статуса доверия и суточной квоты приглашений",
)
async def get_my_employer_trust_status(
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerTrustStatusResponse:
    is_allowed, remaining = can_send_invitation(employer)
    await db.commit()

    return EmployerTrustStatusResponse(
        trust_score=employer.trust_score,
        is_inn_verified=employer.is_inn_verified,
        invite_daily_limit=employer.invite_daily_limit,
        invites_sent_today=employer.invites_sent_today,
        remaining_invites_today=remaining,
        can_send_invites=is_allowed,
    )
