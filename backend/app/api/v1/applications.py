"""
FSP IT-Talent Platform — API Module 11: applications.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.11 and DISPATCH.md.
Applying to a vacancy unmasks candidate contacts to that specific employer (152-ФЗ конклюдентное действие).
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.applications import Application
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.users import User
from app.models.vacancies import Vacancy
from app.schemas.applications import (
    ApplicationDetailResponse,
    ApplicationEmployerItem,
    ApplicationStatusEnum,
    CreateApplicationRequest,
    PaginatedApplicationsCandidateResponse,
    PaginatedApplicationsEmployerResponse,
    UpdateApplicationStatusRequest,
)
from app.schemas.base import PaginationMeta
from app.schemas.candidate_bank import CandidateUnmaskedContactsResponse
from app.services.anonymizer import format_full_name

router = APIRouter(prefix="/applications", tags=["applications"])


async def get_current_candidate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfile:
    """Resolves or initializes candidate profile for candidate user."""
    stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.user_id == current_user.id)
        .options(selectinload(CandidateProfile.user))
    )
    profile = (await db.execute(stmt)).scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(
            user_id=current_user.id,
            first_name=current_user.email.split("@")[0].capitalize(),
            last_name="Кандидат",
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile
from app.api.deps import get_current_employer


def _serialize_application_detail(app: Application) -> ApplicationDetailResponse:
    vac_title = app.vacancy.title if getattr(app, "vacancy", None) else "Вакансия"
    emp_company = (
        app.vacancy.employer_profile.company_name
        if getattr(app, "vacancy", None) and getattr(app.vacancy, "employer_profile", None)
        else "Работодатель"
    )
    status_enum = (
        ApplicationStatusEnum(app.status)
        if app.status in ApplicationStatusEnum._value2member_map_
        else ApplicationStatusEnum.APPLIED
    )

    return ApplicationDetailResponse(
        id=app.id,
        vacancy_id=app.vacancy_id,
        vacancy_title=vac_title,
        employer_company_name=emp_company,
        candidate_profile_id=app.candidate_profile_id,
        cover_letter=app.cover_letter,
        status=status_enum,
        applied_at=app.applied_at,
        viewed_at=app.viewed_at,
        resolved_at=app.resolved_at,
        rejection_reason=app.rejection_reason,
    )


def _serialize_candidate_contacts(cand: CandidateProfile) -> CandidateUnmaskedContactsResponse:
    user_email = cand.user.email if hasattr(cand, "user") and cand.user else f"candidate_{cand.id}@fsp.ru"
    full_name = format_full_name(cand.first_name, cand.last_name, cand.middle_name)
    now = datetime.now(timezone.utc)

    return CandidateUnmaskedContactsResponse(
        candidate_id=cand.id,
        full_name=full_name,
        email=user_email,
        phone=cand.phone or "+7 (999) 000-00-00",
        telegram=cand.telegram or "@fsp_candidate",
        github_url=cand.github_url or "https://github.com/fsp-candidate",
        raw_resume_pdf_url=cand.raw_resume_pdf_path,
        full_pdf_url=f"/api/v1/resume-pdf/{cand.id}/full",
        unmasked_reason="vacancy_applied",
        unmasked_at=now,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationDetailResponse,
    summary="Подача соискателем прямого отклика на вакансию",
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ApplicationDetailResponse,
    include_in_schema=False,
)
async def create_application(
    payload: CreateApplicationRequest,
    candidate: CandidateProfile = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailResponse:
    # 1. Check vacancy
    vac_stmt = (
        select(Vacancy)
        .where(Vacancy.id == payload.vacancy_id)
        .options(selectinload(Vacancy.employer_profile))
    )
    vacancy = (await db.execute(vac_stmt)).scalar_one_or_none()
    if not vacancy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")

    if vacancy.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Вакансия не активна (статус '{vacancy.status}')",
        )

    # 2. Check duplicate application
    dup_stmt = select(Application).where(
        Application.vacancy_id == payload.vacancy_id,
        Application.candidate_profile_id == candidate.id,
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже откликнулись на эту вакансию (ERR_APPLICATION_EXISTS)",
        )

    # 3. Create application
    now = datetime.now(timezone.utc)
    app = Application(
        vacancy_id=payload.vacancy_id,
        candidate_profile_id=candidate.id,
        cover_letter=payload.cover_letter,
        status="applied",
        applied_at=now,
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)

    # Re-fetch with relations
    load_stmt = (
        select(Application)
        .where(Application.id == app.id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
    )
    loaded = (await db.execute(load_stmt)).scalar_one()
    return _serialize_application_detail(loaded)


@router.get(
    "/candidate",
    response_model=PaginatedApplicationsCandidateResponse,
    summary="История отправленных откликов соискателя (alias)",
)
@router.get(
    "/sent",
    response_model=PaginatedApplicationsCandidateResponse,
    summary="История отправленных откликов соискателя",
)
async def list_candidate_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    candidate: CandidateProfile = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
) -> PaginatedApplicationsCandidateResponse:
    query = (
        select(Application)
        .where(Application.candidate_profile_id == candidate.id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
        .order_by(Application.created_at.desc())
    )
    count_query = select(func.count(Application.id)).where(Application.candidate_profile_id == candidate.id)

    if status_filter:
        query = query.where(Application.status == status_filter)
        count_query = count_query.where(Application.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    items_stmt = query.offset((page - 1) * page_size).limit(page_size)
    apps = (await db.execute(items_stmt)).scalars().all()

    items = [_serialize_application_detail(a) for a in apps]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedApplicationsCandidateResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/employer",
    response_model=PaginatedApplicationsEmployerResponse,
    summary="Входящие отклики работодателя с открытыми контактами соискателя (alias)",
)
@router.get(
    "/received",
    response_model=PaginatedApplicationsEmployerResponse,
    summary="Входящие отклики работодателя с открытыми контактами соискателя",
)
async def list_employer_applications(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedApplicationsEmployerResponse:
    query = (
        select(Application)
        .join(Vacancy, Application.vacancy_id == Vacancy.id)
        .where(Vacancy.employer_profile_id == employer.id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile).selectinload(CandidateProfile.user),
        )
        .order_by(Application.created_at.desc())
    )
    count_query = (
        select(func.count(Application.id))
        .join(Vacancy, Application.vacancy_id == Vacancy.id)
        .where(Vacancy.employer_profile_id == employer.id)
    )

    if status_filter:
        query = query.where(Application.status == status_filter)
        count_query = count_query.where(Application.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    items_stmt = query.offset((page - 1) * page_size).limit(page_size)
    apps = (await db.execute(items_stmt)).scalars().all()

    items: List[ApplicationEmployerItem] = []
    for a in apps:
        app_detail = _serialize_application_detail(a)
        contacts = _serialize_candidate_contacts(a.candidate_profile)
        items.append(ApplicationEmployerItem(application=app_detail, candidate_contacts=contacts))

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedApplicationsEmployerResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/{id}",
    response_model=ApplicationDetailResponse,
    summary="Детальный просмотр отклика",
)
async def get_application_detail(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailResponse:
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    # Access check: candidate, employer, or admin
    is_cand = app.candidate_profile and app.candidate_profile.user_id == current_user.id
    is_emp = (
        app.vacancy
        and app.vacancy.employer_profile
        and app.vacancy.employer_profile.user_id == current_user.id
    )
    if not (is_cand or is_emp or current_user.role == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому отклику")

    # Mark viewed by employer
    if is_emp and app.status == "applied":
        app.status = "viewed"
        app.viewed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(app)

    return _serialize_application_detail(app)


@router.post(
    "/{id}/accept",
    response_model=ApplicationDetailResponse,
    summary="Принятие отклика работодателем",
)
async def accept_application(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailResponse:
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    if not app.vacancy or app.vacancy.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к отклику на чужую вакансию")

    app.status = "accepted"
    app.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(app)

    return _serialize_application_detail(app)


@router.post(
    "/{id}/reject",
    response_model=ApplicationDetailResponse,
    summary="Отклонение отклика работодателем",
)
async def reject_application(
    id: int,
    payload: Optional[UpdateApplicationStatusRequest] = None,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailResponse:
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    if not app.vacancy or app.vacancy.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к отклику на чужую вакансию")

    app.status = "rejected"
    app.resolved_at = datetime.now(timezone.utc)
    if payload and payload.rejection_reason:
        app.rejection_reason = payload.rejection_reason

    await db.commit()
    await db.refresh(app)

    return _serialize_application_detail(app)


@router.patch(
    "/{id}/status",
    response_model=ApplicationDetailResponse,
    summary="Обновление статуса отклика работодателем",
)
async def update_application_status(
    id: int,
    payload: UpdateApplicationStatusRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailResponse:
    stmt = (
        select(Application)
        .where(Application.id == id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    if not app.vacancy or app.vacancy.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к отклику на чужую вакансию")

    app.status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    if payload.rejection_reason:
        app.rejection_reason = payload.rejection_reason
    if payload.status in (ApplicationStatusEnum.ACCEPTED, ApplicationStatusEnum.REJECTED):
        app.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(app)

    return _serialize_application_detail(app)


@router.post(
    "/{id}/withdraw",
    response_model=ApplicationDetailResponse,
    summary="Отзыв отклика соискателем",
)
async def withdraw_application(
    id: int,
    candidate: CandidateProfile = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
) -> ApplicationDetailResponse:
    stmt = (
        select(Application)
        .where(Application.id == id, Application.candidate_profile_id == candidate.id)
        .options(
            selectinload(Application.vacancy).selectinload(Vacancy.employer_profile),
            selectinload(Application.candidate_profile),
        )
    )
    app = (await db.execute(stmt)).scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отклик не найден")

    app.status = "withdrawn"
    app.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(app)

    return _serialize_application_detail(app)
