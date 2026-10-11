"""
FSP IT-Talent Platform — API Module 4: resume-pdf.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.4 and DISPATCH.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status

from app.api.v1.auth import get_current_user, get_current_user_flexible
from app.database import get_db
from app.models.audit_logs import AuditLog
from app.models.candidate_categorizations import CandidateCategorization
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_skills import CandidateSkill
from app.models.categories import Category
from app.models.users import User
from app.schemas.resume_pdf import (
    ResumeParsedResponse,
)
from app.services.anonymizer import check_contact_access, format_full_name, format_masked_name
from app.services.pdf_generator import generate_fsp_profile_pdf
from app.services.resume_parser import InvalidPdfFormatError, ResumeParser

router = APIRouter(prefix="/resume-pdf", tags=["resume-pdf"])


@router.post(
    "/parse",
    response_model=ResumeParsedResponse,
    summary="Автораспознавание структуры резюме из PDF (PyMuPDF / fallback)",
)
@router.post(
    "/upload",
    response_model=ResumeParsedResponse,
    summary="Загрузка и парсинг PDF-резюме соискателя",
)
async def upload_and_parse_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeParsedResponse:
    # 1. Чтение байтов загруженного файла
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пустой файл",
        )

    # 2. Валидация magic bytes %PDF- (EC-18)
    try:
        parsed_data = ResumeParser.parse_resume(content)
    except InvalidPdfFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка парсинга PDF-файла: {exc}",
        )

    # 3. Сохраняем в профиль кандидата, если найден
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if profile:
        if parsed_data.get("detected_first_name") and profile.first_name == "Соискатель":
            profile.first_name = parsed_data["detected_first_name"]
        if parsed_data.get("detected_last_name") and profile.last_name == "ФСП":
            profile.last_name = parsed_data["detected_last_name"]
        if parsed_data.get("detected_phone") and not profile.phone:
            profile.phone = parsed_data["detected_phone"]
        if parsed_data.get("detected_telegram") and not profile.telegram:
            profile.telegram = parsed_data["detected_telegram"]
        if parsed_data.get("detected_github") and not profile.github_url:
            profile.github_url = parsed_data["detected_github"]
        if parsed_data.get("detected_city") and not profile.city:
            profile.city = parsed_data["detected_city"]
        if parsed_data.get("detected_salary_min") and not profile.expected_salary:
            profile.expected_salary = parsed_data["detected_salary_min"]

        # Сохраняем разобранные данные
        curr_survey = profile.survey_data_json or {}
        curr_survey["parsed_resume"] = parsed_data
        profile.survey_data_json = curr_survey
        await db.commit()

    return ResumeParsedResponse(**parsed_data)


@router.get(
    "/parsed",
    response_model=ResumeParsedResponse,
    summary="Получение последних автораспознанных данных резюме соискателя",
)
async def get_parsed_resume(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeParsedResponse:
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile or not profile.survey_data_json or "parsed_resume" not in profile.survey_data_json:
        # Возвращаем типовую структуру по текущему профилю
        return ResumeParsedResponse(
            detected_first_name=profile.first_name if profile else None,
            detected_last_name=profile.last_name if profile else None,
            detected_email=current_user.email,
            detected_phone=profile.phone if profile else None,
            detected_telegram=profile.telegram if profile else None,
            detected_github=profile.github_url if profile else None,
            detected_city=profile.city if profile else None,
            extracted_skills=[],
            work_experience=[],
            education=[],
            total_experience_months=0,
            raw_text_length=0,
        )

    return ResumeParsedResponse(**profile.survey_data_json["parsed_resume"])


def _build_candidate_pdf_data(cand: CandidateProfile) -> Dict[str, Any]:
    spec: Optional[str] = None
    grade: Optional[str] = None
    theta: Optional[float] = None

    if cand.candidate_categorizations:
        curr_cat = next((c for c in cand.candidate_categorizations if c.is_current), cand.candidate_categorizations[0])
        if curr_cat.test_score is not None:
            theta = curr_cat.test_score
        if curr_cat.category:
            if curr_cat.category.specialization:
                spec = curr_cat.category.specialization.name or curr_cat.category.specialization.code
            if curr_cat.category.grade:
                grade = curr_cat.category.grade.name or curr_cat.category.grade.code

    skills = [cs.skill.name for cs in (cand.candidate_skills or []) if cs.skill]
    if not skills and cand.survey_data_json and isinstance(cand.survey_data_json, dict):
        skills = cand.survey_data_json.get("skills", [])
    if not skills:
        skills = []

    sport_rank: Optional[str] = None
    achievements = []
    if cand.fsp_achievements:
        for a in cand.fsp_achievements:
            if a.sport_rank and not sport_rank:
                sport_rank = a.sport_rank
            achievements.append({
                "discipline": a.discipline,
                "stage": a.stage,
                "standing": f"{a.place}-е место" if a.place else (a.medal or "Участник"),
                "event_name": a.championship_name,
                "event_year": a.year,
                "verified": True,
            })
    elif cand.survey_data_json and isinstance(cand.survey_data_json, dict) and "fsp_achievements" in cand.survey_data_json:
        achievements = cand.survey_data_json["fsp_achievements"]

    masked_name = format_masked_name(cand.first_name or "Соискатель", cand.last_name or "ФСП", cand.id)

    return {
        "id": cand.id,
        "first_name": cand.first_name or "Соискатель",
        "last_name": cand.last_name or "ФСП",
        "middle_name": cand.middle_name,
        "full_name": format_full_name(cand.first_name, cand.last_name, cand.middle_name),
        "masked_name": masked_name,
        "email": cand.user.email if cand.user else f"candidate_{cand.id}@fsp.ru",
        "phone": cand.phone,
        "telegram": cand.telegram,
        "github_url": cand.github_url,
        "specialization": spec,
        "grade": grade,
        "theta": theta,
        "fsp_id": cand.fsp_id,
        "fsp_verified": cand.fsp_verified,
        "sport_rank": sport_rank,
        "skills": skills,
        "city": cand.city,
        "work_format": cand.work_format,
        "expected_salary": cand.expected_salary,
        "fsp_achievements": achievements,
    }


async def _get_candidate_with_relations(candidate_id: int, db: AsyncSession) -> Optional[CandidateProfile]:
    stmt = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.user),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(CandidateCategorization.category).selectinload(Category.specialization),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(CandidateCategorization.category).selectinload(Category.grade),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(CandidateCategorization.confirmed_grade),
            selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.fsp_achievements),
        )
    )
    res = await db.execute(stmt.where(CandidateProfile.id == candidate_id))
    cand = res.scalar_one_or_none()
    if not cand:
        # Fallback to query by user_id
        res_user = await db.execute(stmt.where(CandidateProfile.user_id == candidate_id))
        cand = res_user.scalar_one_or_none()
    return cand


@router.get(
    "/{candidate_id}/anonymized",
    summary="Скачивание анонимизированного резюме соискателя (Mode A с водяным знаком 152-ФЗ)",
)
async def get_anonymized_resume_pdf(
    candidate_id: int,
    current_user: User = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> Response:
    cand = await _get_candidate_with_relations(candidate_id, db)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    data = _build_candidate_pdf_data(cand)
    pdf_bytes = generate_fsp_profile_pdf(data, is_full_mode=False)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="candidate_{candidate_id}_anonymized.pdf"'},
    )


@router.get(
    "/{candidate_id}/full",
    summary="Скачивание полного резюме соискателя (Mode B с проверкой 152-ФЗ)",
)
async def get_full_resume_pdf(
    candidate_id: int,
    current_user: User = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> Response:
    cand = await _get_candidate_with_relations(candidate_id, db)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    has_access = await check_contact_access(db, cand.id, current_user)
    if not has_access and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Контакты соискателя защищены Федеральным законом № 152-ФЗ. Раскрытие разрешено только после явного принятия приглашения (статус 'accepted').",
        )

    data = _build_candidate_pdf_data(cand)
    pdf_bytes = generate_fsp_profile_pdf(data, is_full_mode=True)

    audit = AuditLog(
        user_id=current_user.id,
        action="DOWNLOAD_FULL_PDF_152FZ",
        entity_type="candidate_profile",
        entity_id=str(cand.id),
        payload_json={
            "candidate_id": cand.id,
            "role": current_user.role,
            "mode": "full",
        },
        ip_address="127.0.0.1",
        user_agent="FSP Platform PDF Export",
    )
    db.add(audit)
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="candidate_{candidate_id}_full.pdf"'},
    )


@router.get(
    "/export-fsp/{candidate_id}",
    summary="Стандартизированный экспорт профиля ФСП в PDF (Mode A vs Mode B)",
)
async def export_fsp_profile_pdf(
    candidate_id: int,
    mode: str = Query("auto"),
    current_user: User = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> Response:
    cand = await _get_candidate_with_relations(candidate_id, db)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    has_access = (current_user.role == "admin") or (await check_contact_access(db, cand.id, current_user))

    if mode == "mode_b_full":
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Контакты соискателя защищены Федеральным законом № 152-ФЗ.",
            )
        is_full = True
    elif mode == "mode_a_anonymized":
        is_full = False
    else:  # auto
        is_full = has_access

    data = _build_candidate_pdf_data(cand)
    pdf_bytes = generate_fsp_profile_pdf(data, is_full_mode=is_full)
    suffix = "full" if is_full else "anonymized"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="fsp_profile_{candidate_id}_{suffix}.pdf"'},
    )


@router.get(
    "/preview-export",
    summary="Предпросмотр собственного полного PDF соискателем (Mode B)",
)
async def preview_own_resume_pdf(
    current_user: User = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> Response:
    stmt = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.user),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(CandidateCategorization.category).selectinload(Category.specialization),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(CandidateCategorization.category).selectinload(Category.grade),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(CandidateCategorization.confirmed_grade),
            selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.fsp_achievements),
        )
        .where(CandidateProfile.user_id == current_user.id)
    )
    cand = (await db.execute(stmt)).scalar_one_or_none()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль соискателя не найден",
        )

    data = _build_candidate_pdf_data(cand)
    pdf_bytes = generate_fsp_profile_pdf(data, is_full_mode=True)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="fsp_profile_preview.pdf"'},
    )

