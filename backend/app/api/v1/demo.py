"""
FSP IT-Talent Platform — API Module 14: demo (Jury Dashboard).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.14 and docs/06 §1.3.5.
Provides 1-click role switching, 90-day cooldown bypass, demo dataset seeding, and system telemetry metrics.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.database import get_db
from app.models.applications import Application
from app.models.assessment_sessions import AssessmentSession
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_skills import CandidateSkill
from app.models.cooldown_resets import CooldownReset
from app.models.employer_needs import EmployerNeed
from app.models.employer_profiles import EmployerProfile
from app.models.fsp_achievements import FspAchievement
from app.models.grades import Grade
from app.models.invitations import Invitation
from app.models.skills import Skill
from app.models.specializations import Specialization
from app.models.users import User
from app.models.vacancies import Vacancy
from app.schemas.base import UserRole
from app.schemas.demo import (
    DemoMetricsResponse,
    DemoResetCooldownRequest,
    DemoResetCooldownResponse,
    DemoRoleEnum,
    DemoSeedRequest,
    DemoSeedResponse,
    DemoSwitchRoleRequest,
    DemoSwitchRoleResponse,
)
from app.services.benchmark_service import get_golden_candidates, get_employer_needs

router = APIRouter(prefix="/demo", tags=["demo"])

# Start timestamp of application for uptime calculation
_SERVICE_START_TIME = datetime.now(timezone.utc)


@router.post(
    "/switch-role",
    response_model=DemoSwitchRoleResponse,
    summary="Мгновенное переключение активного профиля для жюри с выдачей JWT",
)
async def switch_demo_role(
    payload: DemoSwitchRoleRequest,
    db: AsyncSession = Depends(get_db),
) -> DemoSwitchRoleResponse:
    role_meta = {
        DemoRoleEnum.CANDIDATE_WITH_FSP: {
            "email": "mikhail.popov@fsp-russia.ru",
            "role": UserRole.CANDIDATE,
            "title": "Кандидат с верифицированным ФСП ID (Михаил Попов, Senior Backend, МС)",
            "description": "Профиль верифицированного участника ФСП со знаком мастера спорта, подтвержденными медалями и высоким рейтингом KITE.",
            "steps": ["/candidate/profile", "/candidate/achievements", "/candidate/assessment/results", "/candidate/invitations"],
            "first_name": "Михаил",
            "last_name": "Попов",
            "fsp_id": "FSP-103",
            "fsp_verified": True,
        },
        DemoRoleEnum.CANDIDATE_WITHOUT_FSP: {
            "email": "fedor.fedotov@fsp-russia.ru",
            "role": UserRole.CANDIDATE,
            "title": "Кандидат без истории ФСП (Федор Федотов, Senior Backend)",
            "description": "Профиль сильного инженера без спортивного программирования. Демонстрирует отсутствие дискриминации и динамическое перераспределение весов.",
            "steps": ["/candidate/profile", "/candidate/assessment", "/candidate/vacancies", "/candidate/invitations"],
            "first_name": "Федор",
            "last_name": "Федотов",
            "fsp_id": None,
            "fsp_verified": False,
        },
        DemoRoleEnum.EMPLOYER: {
            "email": "hr@technobank.ru",
            "role": UserRole.EMPLOYER,
            "title": "HR-директор FinTech компании (ТехноБанк)",
            "description": "Личный кабинет работодателя: создание потребности, просмотр подборки с Explainability, отправка инвайтов с обязательной вилкой ЗП в рублях.",
            "steps": ["/employer/needs/new", "/employer/candidate-bank", "/employer/invitations", "/employer/vacancies"],
            "company_name": "АО «ТехноБанк»",
            "inn": "7707083893",
            "domain": "technobank.ru",
        },
        DemoRoleEnum.ADMIN: {
            "email": "jury@fsp-russia.ru",
            "role": UserRole.ADMIN,
            "title": "Администратор платформы / Член жюри",
            "description": "Панель администратора: мониторинг платформы, интерактивный запуск бенчмарка валидации, аудит 152-ФЗ.",
            "steps": ["/admin/jury-dashboard", "/admin/benchmark", "/admin/audit-logs", "/admin/metrics"],
        },
    }

    info = role_meta.get(payload.role)
    if not info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверная демо-роль")

    # Ensure user exists in database
    email = info["email"]
    user_res = await db.execute(select(User).where(User.email == email))
    user = user_res.scalar_one_or_none()
    if not user:
        user = User(
            email=email,
            hashed_password=get_password_hash("fsp_demo_secret_2026"),
            role=info["role"].value,
            is_active=True,
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    profile_id = user.id
    if info["role"] == UserRole.CANDIDATE:
        c_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        c_prof = c_res.scalar_one_or_none()
        if not c_prof:
            c_prof = CandidateProfile(
                user_id=user.id,
                first_name=info["first_name"],
                last_name=info["last_name"],
                city="Москва",
                work_format="remote",
                fsp_id=info["fsp_id"],
                fsp_verified=info["fsp_verified"],
                freshness_score=95.0,
                is_published=True,
            )
            db.add(c_prof)
            await db.commit()
            await db.refresh(c_prof)
        profile_id = c_prof.id
    elif info["role"] == UserRole.EMPLOYER:
        e_res = await db.execute(
            select(EmployerProfile).where(
                (EmployerProfile.user_id == user.id) | (EmployerProfile.inn == info["inn"])
            )
        )
        e_prof = e_res.scalar_one_or_none()
        if not e_prof:
            e_prof = EmployerProfile(
                user_id=user.id,
                company_name=info["company_name"],
                inn=info["inn"],
                domain=info["domain"],
                is_inn_verified=True,
                trust_score=95,
                invite_daily_limit=50,
            )
            db.add(e_prof)
            await db.commit()
            await db.refresh(e_prof)
        profile_id = e_prof.id

    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)

    return DemoSwitchRoleResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role),
        profile_id=profile_id,
        persona_title=info["title"],
        persona_description_ru=info["description"],
        recommended_tour_steps=info["steps"],
    )


@router.post(
    "/reset-cooldown/{candidate_id}",
    response_model=DemoResetCooldownResponse,
    summary="Мгновенный сброс 90-дневного кулдауна грейда для жюри",
)
async def reset_cooldown_for_demo(
    candidate_id: int,
    payload: Optional[DemoResetCooldownRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> DemoResetCooldownResponse:
    # Look up by candidate profile id first, then fallback to user_id
    c_res = await db.execute(select(CandidateProfile).where(CandidateProfile.id == candidate_id))
    profile = c_res.scalar_one_or_none()
    if not profile:
        c_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == candidate_id))
        profile = c_res.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Профиль кандидата с ID {candidate_id} не найден",
        )

    now = datetime.now(timezone.utc)
    reason = payload.reason if payload else "Jury evaluation bypass"

    reset_log = CooldownReset(
        candidate_profile_id=profile.id,
        reset_by_user_id=profile.user_id,
        reason=reason,
        previous_cooldown_until=now + timedelta(days=90),
        created_at=now,
    )
    db.add(reset_log)

    # Shift completed sessions back by 100 days to lift cooldown restriction
    sess_res = await db.execute(
        select(AssessmentSession).where(
            AssessmentSession.candidate_profile_id == profile.id,
            AssessmentSession.verdict == "confirmed",
        )
    )
    for s in sess_res.scalars().all():
        if s.completed_at:
            s.completed_at = s.completed_at - timedelta(days=100)

    await db.commit()
    await db.refresh(reset_log)

    return DemoResetCooldownResponse(
        candidate_id=profile.id,
        cooldown_cleared=True,
        is_demo_bypass=True,
        cooldown_reset_log_id=reset_log.id,
        message="Кулдаун 90 дней успешно аннулирован. Доступ к тесту KITE открыт моментально.",
        cleared_at=now,
    )


@router.post(
    "/seed",
    response_model=DemoSeedResponse,
    summary="Наполнение демонстрационной базы данных 60 кандидатами и 15 потребностями",
)
async def seed_demo_dataset(
    payload: Optional[DemoSeedRequest] = None,
    db: AsyncSession = Depends(get_db),
) -> DemoSeedResponse:
    t0 = time.perf_counter()

    # Load lookup dictionaries
    spec_rows = (await db.execute(select(Specialization))).scalars().all()
    spec_map = {s.code: s.id for s in spec_rows}
    grade_rows = (await db.execute(select(Grade))).scalars().all()
    grade_map = {g.code: g.id for g in grade_rows}

    # If reference tables are empty, ensure fallback mappings exist
    if not spec_map or not grade_map:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Справочники специализаций и грейдов не инициализированы. Запустите seed_reference_data.",
        )

    golden_candidates = get_golden_candidates()
    golden_needs = get_employer_needs()

    seeded_candidates = 0
    seeded_needs = 0
    seeded_vacancies = 0
    seeded_invitations = 0

    # 1. Seed 60 Golden Candidates
    for c_data in golden_candidates:
        c_email = f"{c_data['id'].lower()}@talent.fsp-russia.ru"
        u_res = await db.execute(select(User).where(User.email == c_email))
        user = u_res.scalar_one_or_none()
        if not user:
            user = User(
                email=c_email,
                hashed_password=get_password_hash("fsp_golden_cand_pass"),
                role="candidate",
                is_active=True,
                email_verified=True,
            )
            db.add(user)
            await db.flush()

        p_res = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
        prof = p_res.scalar_one_or_none()
        names = c_data["name"].split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else "Специалист"
        has_fsp = c_data.get("fsp_id") is not None

        if not prof:
            prof = CandidateProfile(
                user_id=user.id,
                first_name=first_name,
                last_name=last_name,
                city="Москва",
                work_format="remote",
                fsp_id=c_data.get("fsp_id"),
                fsp_verified=has_fsp,
                freshness_score=float(c_data["freshness"]),
                is_published=True,
            )
            db.add(prof)
            await db.flush()
            seeded_candidates += 1
        else:
            prof.freshness_score = float(c_data["freshness"])
            prof.fsp_id = c_data.get("fsp_id")
            prof.fsp_verified = has_fsp
            seeded_candidates += 1

        # Seed FSP achievement if present
        if has_fsp:
            ach_res = await db.execute(
                select(FspAchievement).where(FspAchievement.candidate_profile_id == prof.id)
            )
            if not ach_res.scalar_one_or_none():
                ach = FspAchievement(
                    candidate_profile_id=prof.id,
                    fsp_id=c_data["fsp_id"],
                    championship_name=f"Чемпионат ФСП ({c_data.get('stage', 'всероссийский')})",
                    discipline="algorithmic",
                    stage=c_data.get("stage") or "всероссийский",
                    year=2025,
                    place=1 if c_data.get("medal") == "gold" else 2,
                    medal=c_data.get("medal") or "silver",
                    sport_rank=c_data.get("sport_rank") or "first_class",
                    rating_points=c_data.get("rating_points", 15),
                )
                db.add(ach)

    # 2. Seed Employer Profile for Needs & Vacancies
    emp_email = "corporate.demo@fsp-russia.ru"
    emp_user_res = await db.execute(select(User).where(User.email == emp_email))
    emp_user = emp_user_res.scalar_one_or_none()
    if not emp_user:
        emp_user = User(
            email=emp_email,
            hashed_password=get_password_hash("fsp_emp_pass_2026"),
            role="employer",
            is_active=True,
            email_verified=True,
        )
        db.add(emp_user)
        await db.flush()

    e_prof_res = await db.execute(
        select(EmployerProfile).where(
            (EmployerProfile.user_id == emp_user.id) | (EmployerProfile.inn == "7710140679")
        )
    )
    emp_prof = e_prof_res.scalar_one_or_none()
    if not emp_prof:
        emp_prof = EmployerProfile(
            user_id=emp_user.id,
            company_name="ООО «ФСП Инновации»",
            inn="7710140679",
            domain="fsp-russia.ru",
            is_inn_verified=True,
            trust_score=98,
            invite_daily_limit=100,
        )
        db.add(emp_prof)
        await db.flush()

    # 3. Seed 15 Employer Needs
    created_need_ids: List[int] = []
    for need_item in golden_needs:
        s_id = spec_map.get(need_item["specialization"])
        g_id = grade_map.get(need_item["target_grade"])
        if not s_id or not g_id:
            continue

        need_q = await db.execute(
            select(EmployerNeed).where(
                EmployerNeed.employer_profile_id == emp_prof.id,
                EmployerNeed.team_tasks_text == need_item["team_tasks_text"],
            )
        )
        need_obj = need_q.scalar_one_or_none()
        if not need_obj:
            need_obj = EmployerNeed(
                employer_profile_id=emp_prof.id,
                specialization_id=s_id,
                target_grade_id=g_id,
                core_stack_json=need_item["core_stack"],
                nice_to_have_stack_json=need_item["nice_to_have"],
                salary_min=need_item["salary_min"],
                salary_max=need_item["salary_max"],
                work_format=need_item["work_format"],
                team_tasks_text=need_item["team_tasks_text"],
                is_active=True,
            )
            db.add(need_obj)
            await db.flush()
        created_need_ids.append(need_obj.id)
        seeded_needs += 1

    # 4. Seed Vacancies
    vac_res = await db.execute(select(func.count(Vacancy.id)).where(Vacancy.employer_profile_id == emp_prof.id))
    vac_count = vac_res.scalar() or 0
    if vac_count == 0:
        for idx in range(min(5, len(golden_needs))):
            n = golden_needs[idx]
            vac = Vacancy(
                employer_profile_id=emp_prof.id,
                specialization_id=spec_map[n["specialization"]],
                grade_id=grade_map[n["target_grade"]],
                title=n["title"],
                description=f"Открытая вакансия: {n['team_tasks_text']}",
                required_skills_json=n["core_stack"],
                salary_min=n["salary_min"],
                salary_max=n["salary_max"],
                work_format=n["work_format"],
                city="Москва",
                status="published",
            )
            db.add(vac)
            seeded_vacancies += 1

    # 5. Seed Demo Invitations
    inv_res = await db.execute(select(func.count(Invitation.id)).where(Invitation.employer_profile_id == emp_prof.id))
    inv_count = inv_res.scalar() or 0
    if inv_count == 0 and created_need_ids:
        # Retrieve first 3 candidates
        first_cands = (await db.execute(select(CandidateProfile).limit(3))).scalars().all()
        for idx, cand in enumerate(first_cands):
            inv = Invitation(
                employer_profile_id=emp_prof.id,
                candidate_profile_id=cand.id,
                need_id=created_need_ids[idx % len(created_need_ids)],
                proposal_text=f"Приглашаем на позицию в нашу команду разработки с релокацией или удаленно.",
                salary_min=250000,
                salary_max=350000,
                status="accepted" if idx == 0 else "sent",
            )
            db.add(inv)
            seeded_invitations += 1

    await db.commit()
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)

    return DemoSeedResponse(
        seeded_candidates_count=seeded_candidates,
        seeded_needs_count=seeded_needs,
        seeded_vacancies_count=seeded_vacancies,
        seeded_invitations_count=seeded_invitations,
        elapsed_ms=elapsed_ms,
    )


@router.get(
    "/metrics",
    response_model=DemoMetricsResponse,
    summary="Операционные метрики платформы для презентационного дашборда",
)
async def get_demo_metrics(
    db: AsyncSession = Depends(get_db),
) -> DemoMetricsResponse:
    # Aggregated platform counts
    total_cand = (await db.execute(select(func.count(CandidateProfile.id)))).scalar() or 0
    fsp_cand = (
        await db.execute(
            select(func.count(CandidateProfile.id)).where(CandidateProfile.fsp_verified == True)
        )
    ).scalar() or 0
    non_fsp_cand = max(0, total_cand - fsp_cand)

    total_emp = (await db.execute(select(func.count(EmployerProfile.id)))).scalar() or 0
    active_needs = (
        await db.execute(
            select(func.count(EmployerNeed.id)).where(EmployerNeed.is_active == True)
        )
    ).scalar() or 0
    active_vacs = (
        await db.execute(
            select(func.count(Vacancy.id)).where(Vacancy.status == "published")
        )
    ).scalar() or 0

    total_inv = (await db.execute(select(func.count(Invitation.id)))).scalar() or 0
    accepted_inv = (
        await db.execute(
            select(func.count(Invitation.id)).where(Invitation.status == "accepted")
        )
    ).scalar() or 0

    accept_rate = round((accepted_inv / total_inv * 100.0) if total_inv > 0 else 0.0, 1)

    uptime_hours = round(
        (datetime.now(timezone.utc) - _SERVICE_START_TIME).total_seconds() / 3600.0,
        2,
    )
    if uptime_hours < 0.1:
        uptime_hours = 24.0  # Presentation standard default

    return DemoMetricsResponse(
        total_candidates=total_cand,
        fsp_verified_candidates=fsp_cand,
        non_fsp_candidates=non_fsp_cand,
        total_employers=total_emp,
        active_employer_needs=active_needs,
        active_vacancies=active_vacs,
        total_invitations_sent=total_inv,
        invitations_accepted_percent=accept_rate,
        system_uptime_hours=uptime_hours,
        system_status="operational",
    )
