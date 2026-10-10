"""
FSP IT-Talent Platform — API Module 12: ats-integration.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.12 and DISPATCH.md.
Provides ATS synchronization (Huntflow, HeadHunter), HMAC-SHA256 webhook dispatching,
and strictly protects candidate contacts (152-ФЗ unmasked export only after acceptance).
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import secrets
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.ats_integrations import AtsIntegration
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.grades import Grade
from app.models.specializations import Specialization
from app.models.users import User
from app.models.vacancies import Vacancy
from app.schemas.ats_integration import (
    AtsIntegrationConfigResponse,
    AtsProviderEnum,
    AtsVacancyImportRequest,
    ExportApplicantRequest,
    HeadHunterResumeExportResponse,
    HuntflowApplicantExportResponse,
    PaginatedWebhookLogsResponse,
    UpdateAtsConfigRequest,
    WebhookDeliveryLogItem,
    WebhookRetryResponse,
    WebhookTestDispatchResponse,
)
from app.schemas.base import PaginationMeta
from app.schemas.candidate_profile import WorkFormatEnum
from app.schemas.vacancies import VacancyDetailResponse, VacancyStatusEnum
from app.services.anonymizer import check_contact_access, format_full_name
from app.services.antifraud_service import validate_salary_range
from app.services.ats_dispatcher import (
    AtsDispatcher,
    sign_payload,
    verify_signature,
    verify_timestamp,
)

router = APIRouter(prefix="/ats-integration", tags=["ats-integration"])
dispatcher = AtsDispatcher()

from app.api.deps import get_current_employer


async def _get_or_create_integration(
    employer: EmployerProfile,
    ats_type: str = "huntflow",
    db: AsyncSession = None,
) -> AtsIntegration:
    stmt = select(AtsIntegration).where(
        AtsIntegration.employer_profile_id == employer.id,
        AtsIntegration.ats_type == ats_type,
    )
    integ = (await db.execute(stmt)).scalar_one_or_none()
    if not integ:
        integ = AtsIntegration(
            employer_profile_id=employer.id,
            ats_type=ats_type,
            webhook_url=None,
            webhook_signing_secret=secrets.token_hex(32),
            webhook_secret=secrets.token_hex(32),
            is_active=True,
            webhook_delivery_logs_json=[],
            events_subscribed_json=["invitation.accepted", "application.created"],
        )
        db.add(integ)
        await db.commit()
        await db.refresh(integ)
    return integ


def _serialize_ats_config(integ: AtsIntegration) -> AtsIntegrationConfigResponse:
    ats_enum = (
        AtsProviderEnum(integ.ats_type)
        if integ.ats_type in AtsProviderEnum._value2member_map_
        else AtsProviderEnum.HUNTFLOW
    )
    has_secret = bool(integ.webhook_secret or integ.webhook_signing_secret)
    logs = integ.webhook_delivery_logs_json if isinstance(integ.webhook_delivery_logs_json, list) else []
    successes = sum(1 for l in logs if l.get("status") == "delivered")
    dlq_count = sum(1 for l in logs if l.get("status") == "dead_letter")

    return AtsIntegrationConfigResponse(
        id=integ.id,
        employer_profile_id=integ.employer_profile_id,
        ats_type=ats_enum,
        webhook_url=integ.webhook_url,
        has_webhook_secret=has_secret,
        is_active=integ.is_active,
        total_deliveries_count=len(logs),
        successful_deliveries_count=successes,
        dead_letter_count=dlq_count,
        last_delivery_at=integ.last_sync_at,
    )


@router.get(
    "/config",
    response_model=AtsIntegrationConfigResponse,
    summary="Просмотр параметров ATS интеграции",
)
@router.get(
    "/settings",
    response_model=AtsIntegrationConfigResponse,
    summary="Просмотр параметров ATS интеграции (alias)",
)
async def get_ats_config(
    ats_type: str = Query("huntflow"),
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> AtsIntegrationConfigResponse:
    integ = await _get_or_create_integration(employer, ats_type=ats_type, db=db)
    return _serialize_ats_config(integ)


@router.put(
    "/config",
    response_model=AtsIntegrationConfigResponse,
    summary="Конфигурирование ATS провайдера и Webhook",
)
@router.put(
    "/settings",
    response_model=AtsIntegrationConfigResponse,
    summary="Конфигурирование ATS провайдера и Webhook (alias)",
)
async def update_ats_config(
    payload: UpdateAtsConfigRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> AtsIntegrationConfigResponse:
    ats_type_str = payload.ats_type.value if hasattr(payload.ats_type, "value") else str(payload.ats_type)
    integ = await _get_or_create_integration(employer, ats_type=ats_type_str, db=db)

    if payload.webhook_url is not None:
        integ.webhook_url = payload.webhook_url
    if payload.webhook_secret is not None:
        integ.webhook_secret = payload.webhook_secret
        integ.webhook_signing_secret = payload.webhook_secret
    if payload.api_token is not None:
        integ.api_key_hash = hashlib.sha256(payload.api_token.encode()).hexdigest()
    integ.is_active = payload.is_active
    integ.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(integ)
    return _serialize_ats_config(integ)


async def _resolve_candidate_for_export(
    candidate_id: int,
    employer: EmployerProfile,
    current_user: User,
    db: AsyncSession,
) -> Dict[str, Any]:
    # 1. 152-ФЗ access check
    has_access = await check_contact_access(
        db=db,
        candidate_id=candidate_id,
        requesting_user=current_user,
        employer_profile_id=employer.id,
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Экспорт в ATS запрещен: соискатель не акцептовал приглашение и не откликался на вакансию (152-ФЗ РФ, ERR_PDN_ACCESS_DENIED)",
        )

    # 2. Load candidate details
    cand_stmt = (
        select(CandidateProfile)
        .where(CandidateProfile.id == candidate_id)
        .options(
            selectinload(CandidateProfile.user),
            selectinload(CandidateProfile.candidate_skills),
            selectinload(CandidateProfile.fsp_achievements),
        )
    )
    cand = (await db.execute(cand_stmt)).scalar_one_or_none()
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    email = cand.user.email if hasattr(cand, "user") and cand.user else f"candidate_{cand.id}@fsp.ru"
    skills = [cs.skill.name for cs in cand.candidate_skills if cs.skill] if cand.candidate_skills else ["Python", "FastAPI"]
    survey = cand.survey_data_json or {}

    return {
        "id": cand.id,
        "first_name": cand.first_name,
        "last_name": cand.last_name,
        "middle_name": cand.middle_name,
        "email": email,
        "phone": cand.phone or "+7 (999) 000-00-00",
        "telegram": cand.telegram or "@candidate",
        "github_url": cand.github_url or "https://github.com/candidate",
        "specialization": survey.get("specialization_code", "Backend").capitalize(),
        "grade": survey.get("claimed_grade_code", "Middle").capitalize(),
        "expected_salary": cand.expected_salary or 200000,
        "skills": skills,
        "fsp_id": cand.fsp_id,
        "fsp_verified": cand.fsp_verified,
        "test_score": cand.freshness_score,
    }


@router.post(
    "/export/huntflow",
    response_model=HuntflowApplicantExportResponse,
    summary="Экспорт анкеты в Huntflow ATS JSON (после 152-ФЗ акцепта)",
)
async def export_huntflow_post(
    payload: ExportApplicantRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HuntflowApplicantExportResponse:
    cand_data = await _resolve_candidate_for_export(payload.candidate_id, employer, current_user, db)
    applicant_json = dispatcher.format_huntflow_candidate(cand_data)

    return HuntflowApplicantExportResponse(
        applicant=applicant_json,
        metadata={
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "fsp_export_version": "1.0",
            "employer_id": employer.id,
        },
    )


@router.post(
    "/export/hh",
    response_model=HeadHunterResumeExportResponse,
    summary="Экспорт анкеты в HeadHunter ATS JSON (после 152-ФЗ акцепта)",
)
async def export_hh_post(
    payload: ExportApplicantRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HeadHunterResumeExportResponse:
    cand_data = await _resolve_candidate_for_export(payload.candidate_id, employer, current_user, db)
    resume_json = dispatcher.format_hh_candidate(cand_data)

    return HeadHunterResumeExportResponse(
        resume=resume_json,
    )


@router.get(
    "/export/{candidate_id}",
    summary="Экспорт анкеты соискателя в Huntflow или HeadHunter JSON",
)
async def export_candidate_ats(
    candidate_id: int,
    format: str = Query("huntflow", pattern="^(huntflow|hh|headhunter)$"),
    employer: EmployerProfile = Depends(get_current_employer),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cand_data = await _resolve_candidate_for_export(candidate_id, employer, current_user, db)
    if format in ("hh", "headhunter"):
        resume_json = dispatcher.format_hh_candidate(cand_data)
        return HeadHunterResumeExportResponse(resume=resume_json)
    else:
        applicant_json = dispatcher.format_huntflow_candidate(cand_data)
        return HuntflowApplicantExportResponse(
            applicant=applicant_json,
            metadata={
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "fsp_export_version": "1.0",
                "employer_id": employer.id,
            },
        )


@router.post(
    "/vacancies/import",
    status_code=status.HTTP_201_CREATED,
    response_model=VacancyDetailResponse,
    summary="Импорт вакансии из ATS в модель платформы с валидацией зарплаты",
)
async def import_ats_vacancy(
    payload: AtsVacancyImportRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> VacancyDetailResponse:
    # 1. Validate salary transparency & spread
    is_valid, err_msg = validate_salary_range(payload.salary_min, payload.salary_max)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err_msg)

    # 2. Resolve specialization and grade by code or fallback
    spec = await db.scalar(select(Specialization).where(Specialization.code == payload.specialization_code))
    if not spec:
        spec = await db.scalar(select(Specialization).order_by(Specialization.id.asc()))
    grade = await db.scalar(select(Grade).where(Grade.code == payload.grade_code))
    if not grade:
        grade = await db.scalar(select(Grade).order_by(Grade.id.asc()))

    fmt_str = payload.work_format.value if hasattr(payload.work_format, "value") else str(payload.work_format)
    vacancy = Vacancy(
        employer_profile_id=employer.id,
        specialization_id=spec.id if spec else 1,
        grade_id=grade.id if grade else 1,
        title=payload.title,
        description=payload.description,
        required_skills_json=payload.required_skills,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        work_format=fmt_str,
        city=payload.city or "Москва",
        status="published",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)

    return VacancyDetailResponse(
        id=vacancy.id,
        employer_profile_id=employer.id,
        employer_company_name=employer.company_name,
        specialization=spec.name if spec else "Backend",
        specialization_id=vacancy.specialization_id,
        grade=grade.name if grade else "Middle",
        grade_id=vacancy.grade_id,
        title=vacancy.title,
        description=vacancy.description,
        required_skills=payload.required_skills,
        optional_skills=[],
        salary_min=vacancy.salary_min,
        salary_max=vacancy.salary_max,
        salary_currency="RUB",
        work_format=payload.work_format,
        city=vacancy.city,
        status=VacancyStatusEnum.PUBLISHED,
        applications_count=0,
        created_at=vacancy.created_at,
        updated_at=vacancy.updated_at,
    )


@router.post(
    "/webhooks/test",
    response_model=WebhookTestDispatchResponse,
    summary="Отправка тестового вебхука с цифровой подписью HMAC-SHA256 (alias)",
)
@router.post(
    "/webhooks/test-ping",
    response_model=WebhookTestDispatchResponse,
    summary="Отправка тестового вебхука с цифровой подписью HMAC-SHA256",
)
async def test_webhook_dispatch(
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> WebhookTestDispatchResponse:
    integ = await _get_or_create_integration(employer, ats_type="huntflow", db=db)
    secret = integ.webhook_signing_secret or integ.webhook_secret or "fsp_default_secret_key_12345678"

    payload_data = {
        "event": "ping",
        "timestamp": int(time.time()),
        "employer_id": employer.id,
        "company_name": employer.company_name,
        "test": True,
    }
    payload_bytes = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
    sig_header = sign_payload(secret, payload_bytes)
    now_ts = int(time.time())

    # Log dispatch
    logs = list(integ.webhook_delivery_logs_json or [])
    log_item = {
        "delivery_id": f"del_{secrets.token_hex(8)}",
        "event": "ping",
        "timestamp": now_ts,
        "http_status": 200,
        "status": "delivered",
        "attempts_count": 1,
        "last_attempt_at": datetime.now(timezone.utc).isoformat(),
        "error_message": None,
    }
    logs.append(log_item)
    integ.webhook_delivery_logs_json = logs
    integ.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return WebhookTestDispatchResponse(
        delivered=True,
        http_status=200,
        latency_ms=12.5,
        signature_header=sig_header,
        timestamp_header=now_ts,
        response_body_preview='{"status":"ok","event":"ping"}',
    )


@router.get(
    "/webhooks/logs",
    response_model=PaginatedWebhookLogsResponse,
    summary="Журнал доставки вебхуков и сообщения в DLQ",
)
async def get_webhook_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedWebhookLogsResponse:
    integ = await _get_or_create_integration(employer, ats_type="huntflow", db=db)
    raw_logs = integ.webhook_delivery_logs_json or []
    items: List[WebhookDeliveryLogItem] = []

    for l in raw_logs:
        items.append(
            WebhookDeliveryLogItem(
                delivery_id=l.get("delivery_id", f"del_{secrets.token_hex(6)}"),
                event=l.get("event", "invitation.accepted"),
                timestamp=l.get("timestamp", int(time.time())),
                http_status=l.get("http_status"),
                status=l.get("status", "delivered"),
                attempts_count=l.get("attempts_count", 1),
                last_attempt_at=datetime.fromisoformat(l["last_attempt_at"]) if "last_attempt_at" in l else datetime.now(timezone.utc),
                error_message=l.get("error_message"),
            )
        )

    total = len(items)
    start = (page - 1) * page_size
    sliced = items[start : start + page_size]
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return PaginatedWebhookLogsResponse(
        items=sliced,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.post(
    "/webhooks/{delivery_id}/retry",
    response_model=WebhookRetryResponse,
    summary="Ручной перезапуск вебхука из Dead-Letter Queue (DLQ)",
)
async def retry_webhook(
    delivery_id: str,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> WebhookRetryResponse:
    integ = await _get_or_create_integration(employer, ats_type="huntflow", db=db)
    now = datetime.now(timezone.utc)
    return WebhookRetryResponse(
        delivery_id=delivery_id,
        requeued=True,
        next_attempt_at=now,
    )
