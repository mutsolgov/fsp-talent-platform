"""
FSP IT-Talent Platform — API Module 15: admin.
Provides audit logs review, user management, and platform analytics for administrator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.audit_logs import AuditLog
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.user_consents import UserConsent
from app.models.users import User
from app.schemas.base import BaseSchema, PaginationMeta

router = APIRouter(prefix="/admin", tags=["admin"])


def _verify_admin(user: User) -> None:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен: требуются права администратора платформы",
        )


@router.get(
    "/audit-logs",
    summary="Журнал аудита безопасности и доступа 152-ФЗ",
)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    action: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    _verify_admin(current_user)

    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)

    # Count total
    count_stmt = select(func.count(AuditLog.id))
    if action:
        count_stmt = count_stmt.where(AuditLog.action == action)
    total = (await db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    records = (await db.execute(stmt)).scalars().all()

    items = []
    for r in records:
        # Determine if action is suspicious
        is_suspicious = False
        if "FAILED" in r.action or "SUSPICIOUS" in r.action or "SCRAP" in r.action:
            is_suspicious = True

        items.append({
            "id": r.id,
            "user_id": r.user_id,
            "action": r.action,
            "resource": f"/{r.entity_type}/{r.entity_id}" if r.entity_id else f"/{r.entity_type}",
            "ip_address": r.ip_address,
            "user_agent": r.user_agent or "",
            "timestamp": r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
            "created_at": r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
            "is_suspicious": is_suspicious,
            "metadata": r.payload_json or {},
        })

    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        },
    }


@router.get(
    "/users",
    summary="Реестр пользователей платформы",
)
async def list_admin_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    _verify_admin(current_user)

    stmt = (
        select(User)
        .options(
            selectinload(User.candidate_profile),
            selectinload(User.employer_profile),
        )
        .order_by(User.id.asc())
    )

    offset = (page - 1) * page_size
    users = list((await db.execute(stmt.offset(offset).limit(page_size))).scalars().all())

    # Map user consents
    user_ids = [u.id for u in users]
    consents_map: Dict[int, UserConsent] = {}
    if user_ids:
        res_cons = await db.execute(select(UserConsent).where(UserConsent.user_id.in_(user_ids)))
        for c in res_cons.scalars().all():
            consents_map[c.user_id] = c

    items = []
    for u in users:
        full_name = u.email.split("@")[0]
        if u.candidate_profile and (u.candidate_profile.first_name or u.candidate_profile.last_name):
            full_name = f"{u.candidate_profile.first_name or ''} {u.candidate_profile.last_name or ''}".strip()
        elif u.employer_profile and u.employer_profile.company_name:
            full_name = u.employer_profile.company_name

        c = consents_map.get(u.id)
        has_pdn = c.consent_pdn_processing if c else True
        has_pub = c.consent_profile_publication if c else True

        items.append({
            "id": u.id,
            "email": u.email,
            "full_name": full_name,
            "role": u.role,
            "is_pdn_consent_given": has_pdn,
            "is_profile_publication_consent_given": has_pub,
            "is_verified": u.email_verified,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {"items": items}
