"""
FSP IT-Talent Platform — API Module 3: candidate-profile.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.3 and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import APIRouter, Depends, HTTPException, status

import app.models  # noqa: F401
from app.api.deps import get_or_create_candidate_profile
from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.assessment_sessions import AssessmentSession
from app.models.candidate_categorizations import CandidateCategorization
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_skills import CandidateSkill
from app.models.categories import Category
from app.models.grades import Grade
from app.models.skills import Skill
from app.models.specializations import Specialization
from app.models.users import User
from app.schemas.candidate_profile import (
    CandidateCategoryStatusResponse,
    CandidateFullProfileResponse,
    CandidateProfileUpdateRequest,
    CandidateSkillItem,
    FreshnessScoreResponse,
    OnboardingSurveyRequest,
    OnboardingSurveyResponse,
    PrivacySettingsResponse,
    PrivacySettingsUpdateRequest,
    WorkFormatEnum,
)

router = APIRouter(prefix="/candidate-profile", tags=["candidate-profile"])


@router.post(
    "/onboarding-survey",
    status_code=status.HTTP_201_CREATED,
    response_model=OnboardingSurveyResponse,
    summary="Завершение обязательного онбординга соискателя",
)
async def submit_onboarding_survey(
    payload: OnboardingSurveyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OnboardingSurveyResponse:
    if current_user.role != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только соискатели могут заполнять анкету онбординга",
        )

    if not payload.consent_personal_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Согласие на обработку персональных данных (152-ФЗ) обязательно",
        )

    # 1. Валидация специализации и заявляемого грейда
    spec = await db.scalar(select(Specialization).where(Specialization.id == payload.specialization_id))
    if not spec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Указанная специализация не найдена")

    grade = await db.scalar(select(Grade).where(Grade.id == payload.claimed_grade_id))
    if not grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Указанный грейд не найден")

    # 2. Поиск существующего профиля или создание нового
    profile = await get_or_create_candidate_profile(current_user.id, db)

    skills_data: List[Dict[str, Any]] = []
    if isinstance(payload.skills, list):
        for s in payload.skills:
            if isinstance(s, str):
                s_name = s.strip()
                if s_name:
                    skills_data.append({
                        "name": s_name,
                        "years_experience": 1.0,
                        "proficiency_level": "intermediate",
                        "is_core": True,
                    })
            elif isinstance(s, dict):
                s_name = s.get("skill_name") or s.get("name")
                skill_id = s.get("skill_id")
                if not s_name and skill_id:
                    sk_db = await db.scalar(select(Skill).where(Skill.id == skill_id))
                    if sk_db:
                        s_name = sk_db.name
                if s_name:
                    raw_years = s.get("years_experience", s.get("years_of_experience", 1.0))
                    try:
                        y_exp = max(0.0, float(raw_years))
                    except (ValueError, TypeError):
                        y_exp = 1.0
                    raw_prof = str(s.get("proficiency_level", "intermediate")).lower().strip()
                    valid_levels = ("beginner", "intermediate", "advanced", "expert")
                    prof_level = raw_prof if raw_prof in valid_levels else "intermediate"
                    is_core = bool(s.get("is_core", True))
                    skills_data.append({
                        "name": str(s_name).strip(),
                        "years_experience": y_exp,
                        "proficiency_level": prof_level,
                        "is_core": is_core,
                    })

    exp_salary = payload.expected_salary or payload.salary_min
    bio_text = payload.bio or payload.about

    survey_data = {
        "specialization_id": payload.specialization_id,
        "claimed_grade_id": payload.claimed_grade_id,
        "specialization_code": spec.code,
        "claimed_grade_code": grade.code,
        "skills": [sd["name"] for sd in skills_data],
        "salary_min": payload.salary_min,
        "salary_max": payload.salary_max,
        "consent_personal_data": payload.consent_personal_data,
        "consent_profile_publish": payload.consent_profile_publish,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    profile.city = payload.city
    profile.work_format = payload.work_format.value if hasattr(payload.work_format, "value") else str(payload.work_format)
    profile.relocation_ready = payload.relocation_ready
    if exp_salary is not None:
        profile.expected_salary = exp_salary
    if bio_text is not None:
        profile.bio = bio_text
    profile.survey_data_json = survey_data
    await db.flush()

    # 3. Синхронизация навыков (candidate_skills)
    for s_info in skills_data:
        skill_name = s_info["name"]
        skill_res = await db.execute(select(Skill).where(Skill.name.ilike(skill_name.strip())))
        skill_obj = skill_res.scalar_one_or_none()
        if not skill_obj:
            # Создаем динамический навык при отсутствии
            slug = skill_name.strip().lower().replace(" ", "-").replace(".", "-")
            skill_obj = Skill(
                name=skill_name.strip(),
                slug=slug,
                specialization_id=spec.id,
                category_tag="onboarding",
                is_core=s_info["is_core"],
                is_verified=False,
            )
            db.add(skill_obj)
            await db.flush()

        # Привязываем к профилю
        cand_skill_res = await db.execute(
            select(CandidateSkill).where(
                CandidateSkill.candidate_profile_id == profile.id,
                CandidateSkill.skill_id == skill_obj.id,
            )
        )
        cand_skill = cand_skill_res.scalar_one_or_none()
        if not cand_skill:
            cand_skill = CandidateSkill(
                candidate_profile_id=profile.id,
                skill_id=skill_obj.id,
                years_experience=s_info["years_experience"],
                proficiency_level=s_info["proficiency_level"],
                is_core=s_info["is_core"],
                is_verified=False,
            )
            db.add(cand_skill)
        else:
            cand_skill.years_experience = s_info["years_experience"]
            cand_skill.proficiency_level = s_info["proficiency_level"]
            cand_skill.is_core = s_info["is_core"]

    await db.commit()
    await db.refresh(profile)

    category_badge = f"{spec.name} · {grade.name} (Заявлено)"
    return OnboardingSurveyResponse(
        profile_id=profile.id,
        category_assigned_preliminary=category_badge,
        assessment_ready=True,
        next_action_url="/api/v1/assessment/sessions/start",
        created_at=profile.created_at,
        status="onboarding_completed",
        specialization={"id": spec.id, "name": spec.name, "code": spec.code},
        claimed_grade={"id": grade.id, "name": grade.name, "code": grade.code},
    )


@router.get(
    "/me",
    response_model=CandidateFullProfileResponse,
    summary="Получение полного собственного профиля соискателя (Self-view)",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateFullProfileResponse:
    res = await db.execute(
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.candidate_categorizations)
                .selectinload(CandidateCategorization.category)
                .selectinload(Category.specialization),
            selectinload(CandidateProfile.candidate_categorizations)
                .selectinload(CandidateCategorization.category)
                .selectinload(Category.grade),
            selectinload(CandidateProfile.candidate_categorizations)
                .selectinload(CandidateCategorization.confirmed_grade),
        )
        .where(CandidateProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        # Автоматически создаем начальный профиль, если еще не создан
        profile = CandidateProfile(
            user_id=current_user.id,
            first_name="Соискатель",
            last_name="ФСП",
            city=None,
            work_format=None,
            freshness_score=50.0,
            is_published=True,
        )
        db.add(profile)
        await db.commit()
        res = await db.execute(
            select(CandidateProfile)
            .options(
                selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
                selectinload(CandidateProfile.candidate_categorizations)
                    .selectinload(CandidateCategorization.category)
                    .selectinload(Category.specialization),
                selectinload(CandidateProfile.candidate_categorizations)
                    .selectinload(CandidateCategorization.category)
                    .selectinload(Category.grade),
                selectinload(CandidateProfile.candidate_categorizations)
                    .selectinload(CandidateCategorization.confirmed_grade),
            )
            .where(CandidateProfile.id == profile.id)
        )
        profile = res.scalar_one()

    skills_items: List[CandidateSkillItem] = []
    for cs in getattr(profile, "candidate_skills", []):
        s_name = cs.skill.name if cs.skill else f"Skill #{cs.skill_id}"
        skills_items.append(
            CandidateSkillItem(
                skill_name=s_name,
                years_of_experience=cs.years_experience,
                proficiency_level=cs.proficiency_level,
                is_core=cs.is_core,
                verified_by_test=cs.is_verified,
            )
        )

    survey = profile.survey_data_json or {}
    curr_cat = next((c for c in getattr(profile, "candidate_categorizations", []) if c.is_current), None)

    if curr_cat:
        score_scaled = curr_cat.test_score
        grade_name = (
            curr_cat.confirmed_grade.name
            if curr_cat.confirmed_grade
            else (curr_cat.category.grade.name if curr_cat.category and curr_cat.category.grade else "Не определен")
        )
        spec_name = (
            curr_cat.category.specialization.name
            if curr_cat.category and curr_cat.category.specialization
            else "Не выбрана"
        )
        cat_title = curr_cat.category.title if curr_cat.category else f"{spec_name} · {grade_name}"
    elif survey and (survey.get("specialization_code") or survey.get("claimed_grade_code")):
        score_scaled = 0.0
        raw_spec = survey.get("specialization_code")
        raw_grade = survey.get("claimed_grade_code")
        spec_name = raw_spec.capitalize() if raw_spec else "Не выбрана"
        grade_name = raw_grade.capitalize() if raw_grade else "Не определен"
        cat_title = f"{spec_name} · {grade_name}" if (raw_spec and raw_grade) else "Профиль не откалиброван"
    else:
        # Новый соискатель с пустой анкетой и без категорий
        score_scaled = 0.0
        spec_name = "Не выбрана"
        grade_name = "Не определен"
        cat_title = "Профиль не откалиброван"

    sal_min = survey.get("salary_min") if survey.get("salary_min") is not None else profile.expected_salary
    sal_max = survey.get("salary_max") if survey.get("salary_max") is not None else profile.expected_salary
    about_text = profile.bio

    work_fmt = (
        WorkFormatEnum(profile.work_format)
        if profile.work_format and profile.work_format in WorkFormatEnum._value2member_map_
        else None
    )

    return CandidateFullProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        middle_name=profile.middle_name,
        email=current_user.email,
        phone=profile.phone,
        telegram=profile.telegram,
        github_url=profile.github_url,
        city=profile.city,
        work_format=work_fmt,
        relocation_ready=profile.relocation_ready,
        expected_salary=profile.expected_salary,
        salary_min=sal_min,
        salary_max=sal_max,
        bio=profile.bio,
        about=about_text,
        specialization=spec_name,
        grade=grade_name,
        category_title=cat_title,
        skills=skills_items,
        kite_score_scaled=score_scaled,
        theta=score_scaled,
        fsp_id=profile.fsp_id,
        fsp_verified=profile.fsp_verified,
        fsp_badge="Участник ФСП" if profile.fsp_verified else "Платформенная верификация",
        freshness_score=profile.freshness_score,
        is_published=profile.is_published,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.put(
    "/me",
    response_model=CandidateFullProfileResponse,
    summary="Обновление данных профиля соискателя",
)
async def update_my_profile(
    payload: CandidateProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateFullProfileResponse:
    res = await db.execute(
        select(CandidateProfile)
        .options(selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill))
        .where(CandidateProfile.user_id == current_user.id)
    )
    profile = res.scalar_one_or_none()
    if not profile:
        profile = CandidateProfile(
            user_id=current_user.id,
            first_name=payload.first_name or "Соискатель",
            last_name=payload.last_name or "ФСП",
            city=payload.city,
            work_format=payload.work_format.value if payload.work_format else None,
            freshness_score=50.0,
            is_published=True,
        )
        db.add(profile)
        await db.flush()

    if payload.first_name is not None:
        profile.first_name = payload.first_name
    if payload.last_name is not None:
        profile.last_name = payload.last_name
    if payload.middle_name is not None:
        profile.middle_name = payload.middle_name
    if payload.phone is not None:
        profile.phone = payload.phone
    if payload.telegram is not None:
        profile.telegram = payload.telegram
    if payload.github_url is not None:
        profile.github_url = payload.github_url
    if payload.city is not None:
        profile.city = payload.city
    if payload.work_format is not None:
        profile.work_format = payload.work_format.value if hasattr(payload.work_format, "value") else str(payload.work_format)
    if payload.relocation_ready is not None:
        profile.relocation_ready = payload.relocation_ready
    if payload.expected_salary is not None:
        profile.expected_salary = payload.expected_salary
    if payload.bio is not None:
        profile.bio = payload.bio
    if payload.about is not None:
        profile.bio = payload.about

    curr_survey = dict(profile.survey_data_json or {})
    new_min = payload.salary_min if payload.salary_min is not None else curr_survey.get("salary_min")
    new_max = payload.salary_max if payload.salary_max is not None else curr_survey.get("salary_max")
    if new_min is not None and new_max is not None:
        if new_max < new_min:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"salary_max ({new_max}) не может быть меньше salary_min ({new_min}) (ERR_SALARY_MAX_LT_MIN)",
            )
        if new_min > 0 and (new_max / new_min) > 3.5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Разброс зарплатной вилки {new_max / new_min:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)",
            )

    if payload.salary_min is not None:
        curr_survey["salary_min"] = payload.salary_min
        profile.expected_salary = payload.salary_min
    if payload.salary_max is not None:
        curr_survey["salary_max"] = payload.salary_max
    profile.survey_data_json = curr_survey

    await db.commit()
    await db.refresh(profile)
    return await get_my_profile(current_user=current_user, db=db)


@router.get(
    "/category",
    response_model=CandidateCategoryStatusResponse,
    summary="Просмотр подтвержденной категории LHH и кулдауна",
)
async def get_candidate_category_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateCategoryStatusResponse:
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")

    survey = profile.survey_data_json or {}
    spec_code = survey.get("specialization_code", "backend")
    grade_code = survey.get("claimed_grade_code", "middle")

    # Проверяем наличие подтвержденной сессии тестирования
    sess_res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.category).selectinload(Category.grade))
        .where(
            AssessmentSession.candidate_profile_id == profile.id,
            AssessmentSession.status.in_(["completed", "submitted"]),
            AssessmentSession.verdict == "confirmed",
        )
        .order_by(AssessmentSession.completed_at.desc())
    )
    confirmed_sess = sess_res.scalars().first()
    is_confirmed = confirmed_sess is not None

    status_str = "confirmed" if is_confirmed else "unverified"
    verified_grade = confirmed_sess.category.grade.name if (is_confirmed and confirmed_sess.category and confirmed_sess.category.grade) else None
    claimed_grade = grade_code.capitalize()

    return CandidateCategoryStatusResponse(
        candidate_id=profile.id,
        specialization_code=spec_code,
        grade_code=grade_code,
        category_badge=f"{spec_code.capitalize()} · {grade_code.capitalize()}",
        is_grade_confirmed=is_confirmed,
        cooldown_until=None,
        is_cooldown_active=False,
        days_left_cooldown=0,
        status=status_str,
        claimed_grade=claimed_grade,
        verified_grade=verified_grade,
    )


@router.get(
    "/freshness",
    response_model=FreshnessScoreResponse,
    summary="Мониторинг индекса актуальности профиля соискателя",
)
async def get_freshness_score(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FreshnessScoreResponse:
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")

    decay_status = "active" if profile.freshness_score >= 50.0 else ("declining" if profile.freshness_score >= 25.0 else "stale")

    return FreshnessScoreResponse(
        candidate_id=profile.id,
        freshness_score=profile.freshness_score,
        half_life_days=45,
        last_activity_at=profile.updated_at,
        activity_count_last_30d=3,
        decay_status=decay_status,
    )


@router.post(
    "/freshness/ping",
    summary="Пинг активности соискателя (сброс к 100.0)",
)
async def ping_freshness(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")

    profile.freshness_score = 100.0
    await db.commit()
    await db.refresh(profile)

    return {
        "candidate_id": profile.id,
        "freshness_score": 100.0,
        "status": "ok",
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else datetime.now(timezone.utc).isoformat(),
    }


@router.put(
    "/privacy",
    response_model=PrivacySettingsResponse,
    summary="Настройки публичности профиля соискателя",
)
async def update_privacy_settings(
    payload: PrivacySettingsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrivacySettingsResponse:
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")

    profile.is_published = payload.is_published
    await db.commit()
    await db.refresh(profile)

    return PrivacySettingsResponse(
        candidate_id=profile.id,
        is_published=profile.is_published,
        updated_at=profile.updated_at or datetime.now(timezone.utc),
    )


@router.post(
    "/publish",
    response_model=PrivacySettingsResponse,
    summary="Публикация профиля соискателя в банке талантов (is_published = True)",
)
async def publish_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrivacySettingsResponse:
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")

    profile.is_published = True
    await db.commit()
    await db.refresh(profile)

    return PrivacySettingsResponse(
        candidate_id=profile.id,
        is_published=profile.is_published,
        updated_at=profile.updated_at or datetime.now(timezone.utc),
    )


@router.post(
    "/unpublish",
    response_model=PrivacySettingsResponse,
    summary="Скрытие профиля соискателя из банка талантов (is_published = False)",
)
async def unpublish_candidate_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrivacySettingsResponse:
    res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Профиль соискателя не найден")

    profile.is_published = False
    await db.commit()
    await db.refresh(profile)

    return PrivacySettingsResponse(
        candidate_id=profile.id,
        is_published=profile.is_published,
        updated_at=profile.updated_at or datetime.now(timezone.utc),
    )
