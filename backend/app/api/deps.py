"""
Common FastAPI dependency providers across API modules.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.v1.auth import get_current_user
from app.models.users import User
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.core.security import generate_valid_inn


async def get_or_create_candidate_profile(
    user_id: int,
    db: AsyncSession,
) -> CandidateProfile:
    """
    Retrieves or creates candidate profile for user.
    Centralized helper function eliminating duplication across assessment, micro-challenges, and candidate profile.
    """
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    profile = res.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(
            user_id=user_id,
            first_name="Соискатель",
            last_name="ФСП",
            city="Москва",
            work_format="remote",
            freshness_score=50.0,
            is_published=True,
        )
        db.add(profile)
        await db.flush()
    return profile


async def get_current_employer(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EmployerProfile:
    """
    Resolves or lazily initializes employer profile for employer/admin user.
    Guarantees unique, checksum-valid INN and distinct company name on auto-creation.
    """
    if current_user.role not in ("employer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ разрешен только работодателям (ERR_EMPLOYER_ROLE_REQUIRED)",
        )
    stmt = select(EmployerProfile).where(EmployerProfile.user_id == current_user.id)
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        profile = EmployerProfile(
            user_id=current_user.id,
            company_name=f"ООО Компания #{current_user.id}",
            inn=generate_valid_inn(current_user.id),
            domain=f"company{current_user.id}.ru",
            is_inn_verified=True,
            trust_score=80,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


__all__ = [
    "get_current_employer",
    "get_current_user",
    "get_db",
    "get_or_create_candidate_profile",
]
