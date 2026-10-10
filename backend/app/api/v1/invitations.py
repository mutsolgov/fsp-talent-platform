"""
FSP IT-Talent Platform — API Module 9: invitations.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.9 and DISPATCH.md.
Mandatory Invariant: salary_min > 0 AND salary_max >= salary_min in RUB (spread <= 3.5).
Quota: max 20 invitations/day per employer.
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
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.invitations import Invitation
from app.models.users import User
from app.schemas.base import PaginationMeta
from app.schemas.invitations import (
    ContactMethodEnum,
    DeclineInvitationRequest,
    InvitationActionResponse,
    InvitationResponse,
    InvitationStatusEnum,
    PaginatedInvitationsResponse,
    SendInvitationRequest,
)
from app.services.anonymizer import format_full_name, format_masked_name
from app.services.antifraud_service import can_send_invitation, record_invitation_sent, validate_salary_range

router = APIRouter(prefix="/invitations", tags=["invitations"])

from app.api.deps import get_current_employer


async def get_current_candidate(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateProfile:
    """Resolves candidate profile for candidate user."""
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == current_user.id)
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


def _serialize_invitation(inv: Invitation) -> InvitationResponse:
    emp = inv.employer_profile
    cand = inv.candidate_profile

    # Determine display name based on 152-ФЗ unmasking rules
    if inv.status == "accepted":
        display_name = format_full_name(cand.first_name, cand.last_name, cand.middle_name) if cand else f"Кандидат #{inv.candidate_profile_id}"
    else:
        display_name = format_masked_name(cand.first_name, cand.last_name, cand.id) if cand else f"Кандидат #{inv.candidate_profile_id}"

    status_enum = InvitationStatusEnum(inv.status) if inv.status in InvitationStatusEnum._value2member_map_ else InvitationStatusEnum.SENT
    method_enum = ContactMethodEnum(inv.contact_method) if inv.contact_method in ContactMethodEnum._value2member_map_ else ContactMethodEnum.PLATFORM

    return InvitationResponse(
        id=inv.id,
        employer_profile_id=inv.employer_profile_id,
        employer_company_name=emp.company_name if emp else "Компания",
        employer_inn=emp.inn if emp else "7701234567",
        candidate_profile_id=inv.candidate_profile_id,
        candidate_display_name=display_name,
        proposal_text=inv.proposal_text,
        salary_min=inv.salary_min,
        salary_max=inv.salary_max,
        salary_currency="RUB",
        contact_method=method_enum,
        status=status_enum,
        need_id=inv.need_id,
        vacancy_id=inv.vacancy_id,
        sent_at=inv.sent_at,
        viewed_at=inv.viewed_at,
        resolved_at=inv.resolved_at,
        decline_reason=inv.decline_reason,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InvitationResponse,
    summary="Отправка прямого приглашения с обязательной вилкой зарплаты в рублях",
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=InvitationResponse,
    include_in_schema=False,
)
async def send_invitation(
    payload: SendInvitationRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    # 1. Quota check (EC-17: max 20/day)
    allowed, remaining = can_send_invitation(employer)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Дневной лимит отправки приглашений исчерпан (максимум 20 в день, ERR_INVITE_DAILY_LIMIT_EXCEEDED)",
        )

    # 2. Candidate existence check
    cand_stmt = select(CandidateProfile).where(CandidateProfile.id == payload.candidate_profile_id)
    candidate = (await db.execute(cand_stmt)).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Соискатель не найден")

    # 3. Mandatory salary transparency and spread check
    is_valid_salary, salary_err = validate_salary_range(payload.salary_min, payload.salary_max)
    if not is_valid_salary:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=salary_err)

    # 4. Check for existing active invitation
    dup_stmt = select(Invitation).where(
        Invitation.employer_profile_id == employer.id,
        Invitation.candidate_profile_id == payload.candidate_profile_id,
        Invitation.status.in_(["sent", "viewed"]),
    )
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этому кандидату уже отправлено активное приглашение (ERR_ACTIVE_INVITE_EXISTS)",
        )

    # 5. Persist invitation
    invitation = Invitation(
        employer_profile_id=employer.id,
        candidate_profile_id=payload.candidate_profile_id,
        need_id=payload.need_id,
        vacancy_id=payload.vacancy_id,
        proposal_text=payload.proposal_text,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        contact_method=payload.contact_method.value if hasattr(payload.contact_method, "value") else str(payload.contact_method),
        status="sent",
        sent_at=datetime.now(timezone.utc),
    )
    db.add(invitation)

    # 6. Record quota consumption
    record_invitation_sent(employer)

    await db.commit()
    await db.refresh(invitation)

    # Re-fetch with relationships
    fetch_stmt = (
        select(Invitation)
        .where(Invitation.id == invitation.id)
        .options(selectinload(Invitation.employer_profile), selectinload(Invitation.candidate_profile))
    )
    inv_loaded = (await db.execute(fetch_stmt)).scalar_one()
    return _serialize_invitation(inv_loaded)


@router.get(
    "/candidate",
    response_model=PaginatedInvitationsResponse,
    summary="Реестр входящих приглашений соискателя (alias)",
)
@router.get(
    "/incoming",
    response_model=PaginatedInvitationsResponse,
    summary="Реестр входящих приглашений соискателя",
)
async def list_candidate_invitations(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    candidate: CandidateProfile = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
) -> PaginatedInvitationsResponse:
    query = (
        select(Invitation)
        .where(Invitation.candidate_profile_id == candidate.id)
        .options(selectinload(Invitation.employer_profile), selectinload(Invitation.candidate_profile))
        .order_by(Invitation.created_at.desc())
    )
    count_query = select(func.count(Invitation.id)).where(Invitation.candidate_profile_id == candidate.id)

    if status_filter:
        query = query.where(Invitation.status == status_filter)
        count_query = count_query.where(Invitation.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    items_stmt = query.offset((page - 1) * page_size).limit(page_size)
    invitations = (await db.execute(items_stmt)).scalars().all()

    items = [_serialize_invitation(inv) for inv in invitations]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedInvitationsResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/employer",
    response_model=PaginatedInvitationsResponse,
    summary="Реестр исходящих приглашений работодателя (alias)",
)
@router.get(
    "/outgoing",
    response_model=PaginatedInvitationsResponse,
    summary="Реестр исходящих приглашений работодателя",
)
async def list_employer_invitations(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedInvitationsResponse:
    query = (
        select(Invitation)
        .where(Invitation.employer_profile_id == employer.id)
        .options(selectinload(Invitation.employer_profile), selectinload(Invitation.candidate_profile))
        .order_by(Invitation.created_at.desc())
    )
    count_query = select(func.count(Invitation.id)).where(Invitation.employer_profile_id == employer.id)

    if status_filter:
        query = query.where(Invitation.status == status_filter)
        count_query = count_query.where(Invitation.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    items_stmt = query.offset((page - 1) * page_size).limit(page_size)
    invitations = (await db.execute(items_stmt)).scalars().all()

    items = [_serialize_invitation(inv) for inv in invitations]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedInvitationsResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/{id}",
    response_model=InvitationResponse,
    summary="Просмотр карточки инвайта с фиксацией viewed_at",
)
async def get_invitation_detail(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvitationResponse:
    stmt = (
        select(Invitation)
        .where(Invitation.id == id)
        .options(selectinload(Invitation.employer_profile), selectinload(Invitation.candidate_profile))
    )
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")

    # Access check: candidate, employer, or admin
    is_cand = inv.candidate_profile and inv.candidate_profile.user_id == current_user.id
    is_emp = inv.employer_profile and inv.employer_profile.user_id == current_user.id
    if not (is_cand or is_emp or current_user.role == "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому приглашению")

    # Candidate view marks invitation as viewed
    if is_cand and inv.status == "sent":
        inv.status = "viewed"
        inv.viewed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(inv)

    return _serialize_invitation(inv)


@router.post(
    "/{id}/accept",
    response_model=InvitationActionResponse,
    summary="Принятие приглашения соискателем (демаскирование контактов 152-ФЗ)",
)
async def accept_invitation(
    id: int,
    candidate: CandidateProfile = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
) -> InvitationActionResponse:
    stmt = select(Invitation).where(Invitation.id == id, Invitation.candidate_profile_id == candidate.id)
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")

    if inv.status in ("accepted", "declined", "expired"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно принять приглашение со статусом '{inv.status}'",
        )

    now = datetime.now(timezone.utc)
    inv.status = "accepted"
    inv.resolved_at = now
    await db.commit()

    return InvitationActionResponse(
        invitation_id=inv.id,
        status=InvitationStatusEnum.ACCEPTED,
        unmasked_contacts_granted=True,
        resolved_at=now,
        message="Приглашение успешно принято. Ваши контактные данные открыты работодателю.",
    )


@router.post(
    "/{id}/decline",
    response_model=InvitationActionResponse,
    summary="Отклонение приглашения соискателем (контакты остаются закрытыми)",
)
async def decline_invitation(
    id: int,
    payload: Optional[DeclineInvitationRequest] = None,
    candidate: CandidateProfile = Depends(get_current_candidate),
    db: AsyncSession = Depends(get_db),
) -> InvitationActionResponse:
    stmt = select(Invitation).where(Invitation.id == id, Invitation.candidate_profile_id == candidate.id)
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")

    if inv.status in ("accepted", "declined", "expired"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно отклонить приглашение со статусом '{inv.status}'",
        )

    now = datetime.now(timezone.utc)
    inv.status = "declined"
    inv.resolved_at = now
    if payload and payload.decline_reason:
        inv.decline_reason = payload.decline_reason

    await db.commit()

    return InvitationActionResponse(
        invitation_id=inv.id,
        status=InvitationStatusEnum.DECLINED,
        unmasked_contacts_granted=False,
        resolved_at=now,
        message="Приглашение отклонено. Ваши контактные данные не раскрыты.",
    )


@router.post(
    "/{id}/cancel",
    response_model=InvitationActionResponse,
    summary="Отзыв приглашения работодателем",
)
async def cancel_invitation(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> InvitationActionResponse:
    stmt = select(Invitation).where(Invitation.id == id, Invitation.employer_profile_id == employer.id)
    inv = (await db.execute(stmt)).scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Приглашение не найдено")

    if inv.status in ("accepted", "declined", "expired"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Невозможно отозвать приглашение со статусом '{inv.status}'",
        )

    now = datetime.now(timezone.utc)
    inv.status = "expired"
    inv.resolved_at = now
    await db.commit()

    return InvitationActionResponse(
        invitation_id=inv.id,
        status=InvitationStatusEnum.EXPIRED,
        unmasked_contacts_granted=False,
        resolved_at=now,
        message="Приглашение отозвано.",
    )
