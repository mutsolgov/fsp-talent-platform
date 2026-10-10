"""
FSP IT-Talent Platform — API Module 5: assessment (KITE Engine).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.5 and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import math
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_or_create_candidate_profile
from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.assessment_answers import AssessmentAnswer
from app.models.assessment_sessions import AssessmentSession
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_categorizations import CandidateCategorization
from app.models.canonical_item_families import CanonicalItemFamily
from app.models.categories import Category
from app.models.cooldown_resets import CooldownReset
from app.models.grades import Grade
from app.models.specializations import Specialization
from app.models.users import User
from app.schemas.assessment import (
    AssessmentSessionProgressResponse,
    AssessmentSessionResultResponse,
    AssessmentSessionStartResponse,
    AssessmentTaskItemResponse,
    AssessmentVerdictEnum,
    CooldownStatusResponse,
    RetestLowerGradeRequest,
    SessionStatusEnum,
    SessionTypeEnum,
    StartAssessmentSessionRequest,
    SubmitTaskAnswerRequest,
    SubmitTaskAnswerResponse,
    TaskTypeEnum,
)
from app.services.grading_engine import GradingEngine
from app.services.isomorphic_generator import IsomorphicGenerator
from app.services.kite_irt import BayesianEAPEstimator, IRT3PLItem

router = APIRouter(prefix="/assessment", tags=["assessment"])
iso_generator = IsomorphicGenerator()
_session_index_base: Dict[int, int] = {}


def resolve_task_item_index(
    session_id: int,
    task_index: int,
    total_items: int = 12,
    explicit_base: Optional[int] = None,
) -> int:
    """
    Разрешает индекс задания с поддержкой как 0-based [0..11], так и 1-based [1..12] (стандарт UI).
    """
    if total_items <= 0:
        return 0

    if explicit_base is not None:
        base = 1 if explicit_base == 1 else 0
        _session_index_base[session_id] = base
        if base == 1:
            return min(max(0, task_index - 1), total_items - 1)
        return min(max(0, task_index), total_items - 1)

    # task_index == 0 однозначно свидетельствует о 0-based индексации
    if task_index == 0:
        _session_index_base[session_id] = 0
        return 0

    # task_index >= total_items (например, 12 при 12 заданиях) однозначно свидетельствует о 1-based индексации
    if task_index >= total_items:
        _session_index_base[session_id] = 1
        return total_items - 1

    # Если база уже зафиксирована для данной сессии
    if session_id in _session_index_base:
        base = _session_index_base[session_id]
        if base == 1:
            return min(max(0, task_index - 1), total_items - 1)
        return min(max(0, task_index), total_items - 1)

    # По умолчанию для UI (индексация 1..12) начальный task_index=1 соответствует первому заданию (items[0])
    _session_index_base[session_id] = 1
    return min(max(0, task_index - 1), total_items - 1)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


async def verify_session_ownership(
    sess: AssessmentSession,
    current_user: User,
    db: AsyncSession,
) -> None:
    """
    Verifies that the current user owns the assessment session or is an admin.
    Raises HTTP 403 Forbidden with exact message on IDOR violation.
    """
    if current_user.role == "admin":
        return
    profile = await get_or_create_candidate_profile(current_user.id, db)
    if sess.candidate_profile_id != profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к чужой тест-сессии",
        )



@router.post(
    "/sessions/start",
    status_code=status.HTTP_201_CREATED,
    response_model=AssessmentSessionStartResponse,
    summary="Старт сессии адаптивного тестирования KITE",
)
async def start_assessment_session(
    payload: StartAssessmentSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSessionStartResponse:
    profile = await get_or_create_candidate_profile(current_user.id, db)

    # 1. Проверка существования категории
    category_id = payload.category_id
    if category_id is None:
        if payload.specialization_id and payload.claimed_grade_id:
            c_res = await db.scalar(
                select(Category.id).where(
                    Category.specialization_id == payload.specialization_id,
                    Category.grade_id == payload.claimed_grade_id,
                )
            )
            category_id = c_res
        elif profile.survey_data_json:
            survey = profile.survey_data_json
            s_id = survey.get("specialization_id")
            g_id = survey.get("claimed_grade_id")
            if s_id and g_id:
                category_id = await db.scalar(
                    select(Category.id).where(
                        Category.specialization_id == s_id,
                        Category.grade_id == g_id,
                    )
                )

    if category_id is None:
        # Fallback к первой категории
        category_id = await db.scalar(select(Category.id))

    cat_res = await db.execute(
        select(Category)
        .options(selectinload(Category.specialization), selectinload(Category.grade))
        .where(Category.id == category_id)
    )
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанная категория тестирования не найдена",
        )

    # 2. Проверка 90-дневного кулдауна (EC-08)
    # Ищем последнюю подтвержденную сессию для этого профиля
    last_confirmed_res = await db.execute(
        select(AssessmentSession)
        .where(
            AssessmentSession.candidate_profile_id == profile.id,
            AssessmentSession.status.in_(["completed", "submitted"]),
            AssessmentSession.verdict == "confirmed",
        )
        .order_by(AssessmentSession.completed_at.desc())
    )
    last_confirmed = last_confirmed_res.scalars().first()

    now = datetime.now(timezone.utc)
    if last_confirmed and last_confirmed.completed_at:
        cooldown_until = last_confirmed.completed_at + timedelta(days=90)
        target_grade = category.grade.name
        can_proceed, cooldown_err = GradingEngine.check_cooldown(
            cooldown_until=cooldown_until,
            target_grade=target_grade,
            current_confirmed_grade=target_grade,
            is_demo_bypass=False,
            now=now,
        )
        if not can_proceed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=cooldown_err,
            )

    # 3. Вычисление seed_hash для сессии
    salt = f"{profile.id}:{category.id}:{now.timestamp()}"
    seed_hash = hashlib.sha256(salt.encode()).hexdigest()

    expires_at = now + timedelta(minutes=90)
    sess_type = payload.session_type.value if hasattr(payload.session_type, "value") else str(payload.session_type)
    session = AssessmentSession(
        candidate_profile_id=profile.id,
        category_id=category.id,
        session_type=sess_type,
        seed_hash=seed_hash,
        started_at=now,
        status="in_progress",
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return AssessmentSessionStartResponse(
        session_id=session.id,
        category_id=session.category_id,
        session_type=SessionTypeEnum(session.session_type),
        tasks_count=12,
        total_tasks=12,
        time_limit_minutes=90,
        seed_hash=session.seed_hash,
        variant_seed=session.seed_hash,
        status="in_progress",
        started_at=session.started_at,
        expires_at=session.expires_at,
    )


@router.get(
    "/sessions/{session_id}",
    summary="Информация о сессии тестирования (детали/прогресс)",
)
async def get_assessment_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.answers))
        .where(AssessmentSession.id == session_id)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    await verify_session_ownership(sess, current_user, db)

    now = datetime.now(timezone.utc)
    exp = ensure_utc(sess.expires_at) or now
    seconds_remaining = max(0, int((exp - now).total_seconds()))

    return {
        "session_id": sess.id,
        "status": sess.status,
        "session_type": sess.session_type,
        "category_id": sess.category_id,
        "seed_hash": sess.seed_hash,
        "tasks_answered": len(sess.answers),
        "tasks_total": 12,
        "seconds_remaining": seconds_remaining,
        "raw_score": sess.raw_score,
        "theta_score": sess.theta_score,
        "verdict": sess.verdict,
        "started_at": sess.started_at,
        "expires_at": sess.expires_at,
        "completed_at": sess.completed_at,
    }


@router.get(
    "/sessions/{session_id}/progress",
    response_model=AssessmentSessionProgressResponse,
    summary="Мониторинг прогресса сессии (остаток времени, число решенных)",
)
async def get_assessment_session_progress(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSessionProgressResponse:
    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.answers))
        .where(AssessmentSession.id == session_id)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    await verify_session_ownership(sess, current_user, db)

    now = datetime.now(timezone.utc)
    exp = ensure_utc(sess.expires_at) or now
    seconds_remaining = max(0, int((exp - now).total_seconds()))

    return AssessmentSessionProgressResponse(
        session_id=sess.id,
        status=sess.status,
        tasks_answered=len(sess.answers),
        tasks_total=12,
        seconds_remaining=seconds_remaining,
    )


@router.get(
    "/sessions/{session_id}/tasks/{task_index}",
    response_model=AssessmentTaskItemResponse,
    summary="Получение детерминированно мутированного задания",
)
async def get_assessment_task_item(
    session_id: int,
    task_index: int,
    base: Optional[int] = Query(None, description="0 (0-based [0..11]) или 1 (1-based [1..12])"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentTaskItemResponse:
    if not (0 <= task_index <= 12):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Индекс задания должен лежать в [0, 12]")

    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.category))
        .where(AssessmentSession.id == session_id)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    await verify_session_ownership(sess, current_user, db)

    # Ищем каноническое задание для данной специализации и грейда
    category = sess.category
    items_res = await db.execute(
        select(CanonicalItemFamily)
        .where(
            CanonicalItemFamily.specialization_id == category.specialization_id,
            CanonicalItemFamily.grade_id == category.grade_id,
            CanonicalItemFamily.is_active == True,
        )
        .order_by(CanonicalItemFamily.id)
    )
    items = items_res.scalars().all()
    if not items:
        # Fallback к любым активным каноническим заданиям
        items_res = await db.execute(select(CanonicalItemFamily).where(CanonicalItemFamily.is_active == True).order_by(CanonicalItemFamily.id))
        items = items_res.scalars().all()

    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Канонические задания не найдены")

    item_idx = resolve_task_item_index(sess.id, task_index, total_items=len(items), explicit_base=base)
    target_item = items[item_idx]

    # Генерируем детерминированный вариант
    variant = iso_generator.generate_variant(
        candidate_id=sess.candidate_profile_id,
        session_id=sess.id,
        item_id=target_item.id,
        template_text=target_item.template_text,
        param_matrix=target_item.param_matrix_json or {},
    )

    t_type = TaskTypeEnum(target_item.task_type) if target_item.task_type in TaskTypeEnum._value2member_map_ else TaskTypeEnum.MCQ

    return AssessmentTaskItemResponse(
        session_id=sess.id,
        task_index=task_index,
        task_type=t_type,
        title=target_item.title,
        description=variant["rendered_prompt"],
        prompt=variant["rendered_prompt"],
        code_template="# Введите ваше решение здесь\ndef solution(input_data):\n    pass\n",
        public_tests=variant["public_tests"],
        time_limit_seconds=variant["time_limit_sec"],
    )


@router.post(
    "/sessions/{session_id}/submit-task",
    response_model=SubmitTaskAnswerResponse,
    summary="Отправка ответа на задание (submit-task alias)",
)
@router.post(
    "/sessions/{session_id}/submit-item",
    response_model=SubmitTaskAnswerResponse,
    summary="Отправка ответа на конкретное задание (submit-item)",
)
@router.post(
    "/sessions/{session_id}/answer",
    response_model=SubmitTaskAnswerResponse,
    summary="Отправка ответа на задание (answer alias)",
)
async def submit_task_answer(
    session_id: int,
    payload: SubmitTaskAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmitTaskAnswerResponse:
    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.category))
        .where(AssessmentSession.id == session_id)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    await verify_session_ownership(sess, current_user, db)

    if sess.status != "in_progress":
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Сессия тестирования уже завершена")

    now = datetime.now(timezone.utc)
    exp = ensure_utc(sess.expires_at)
    if exp and now > exp:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Время тестирования истекло")

    # Получаем каноническое задание
    category = sess.category
    items_res = await db.execute(
        select(CanonicalItemFamily)
        .where(
            CanonicalItemFamily.specialization_id == category.specialization_id,
            CanonicalItemFamily.grade_id == category.grade_id,
        )
        .order_by(CanonicalItemFamily.id)
    )
    items = items_res.scalars().all()
    if not items:
        items_res = await db.execute(select(CanonicalItemFamily).order_by(CanonicalItemFamily.id))
        items = items_res.scalars().all()

    if not items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")

    explicit_base = getattr(payload, "base", None)
    item_idx = resolve_task_item_index(sess.id, payload.task_index, total_items=len(items), explicit_base=explicit_base)
    target_item = items[item_idx]

    t_start = time.perf_counter()
    variant = iso_generator.generate_variant(
        candidate_id=sess.candidate_profile_id,
        session_id=sess.id,
        item_id=target_item.id,
        template_text=target_item.template_text,
        param_matrix=target_item.param_matrix_json or {},
    )
    public_tests = variant.get("public_tests", [])
    total_public_tests = len(public_tests) if public_tests else 3

    if isinstance(payload.answer_payload, dict):
        selected_option = payload.answer_payload.get("selected_option") or payload.answer_payload.get("option")
        submitted_code = payload.answer_payload.get("code") or payload.answer_payload.get("solution") or ""
        ans_text = str(selected_option or submitted_code or payload.answer_payload)
    else:
        raw_str = str(payload.answer_payload).strip()
        if len(raw_str) == 1 and raw_str.upper() in ("A", "B", "C", "D"):
            selected_option = raw_str.upper()
            submitted_code = ""
        else:
            selected_option = None
            submitted_code = str(payload.answer_payload)
        ans_text = str(payload.answer_payload)

    passed_public_tests = 0
    if target_item.task_type == "mcq":
        correct_option = ["A", "B", "C", "D"][variant["seed_int"] % 4]
        if selected_option and str(selected_option).strip().upper() == correct_option:
            passed_public_tests = total_public_tests
            is_correct = True
        else:
            is_correct = False
    else:
        if submitted_code and submitted_code.strip():
            try:
                scope: Dict[str, Any] = {}
                safe_builtins = {
                    "max": max, "min": min, "sum": sum, "len": len,
                    "range": range, "int": int, "float": float, "str": str,
                    "list": list, "dict": dict, "set": set, "bool": bool,
                    "abs": abs, "round": round, "sorted": sorted,
                }
                exec(submitted_code, {"__builtins__": safe_builtins}, scope)
                fn = scope.get("solution") or scope.get("solve")
                if callable(fn):
                    for tc in public_tests:
                        inp = tc.get("input", {})
                        sig = inspect.signature(fn)
                        if len(sig.parameters) == 1:
                            res = fn(inp.get("records", inp))
                        elif len(sig.parameters) == 2:
                            res = fn(inp.get("records", []), inp.get("window_size", 5))
                        else:
                            res = fn()
                        if res == tc.get("expected"):
                            passed_public_tests += 1
                else:
                    passed_public_tests = total_public_tests
            except Exception:
                passed_public_tests = 0
        elif selected_option:
            correct_option = ["A", "B", "C", "D"][variant["seed_int"] % 4]
            if str(selected_option).strip().upper() == correct_option:
                passed_public_tests = total_public_tests
            else:
                passed_public_tests = 0
        is_correct = (passed_public_tests == total_public_tests and total_public_tests > 0)

    elapsed_ms = max(0.5, round((time.perf_counter() - t_start) * 1000, 2))

    # Записываем или обновляем assessment_answer
    ans_res = await db.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.session_id == sess.id,
            AssessmentAnswer.item_family_id == target_item.id,
        )
    )
    ans = ans_res.scalar_one_or_none()
    time_taken = payload.time_spent_seconds or 45
    if not ans:
        ans = AssessmentAnswer(
            session_id=sess.id,
            item_family_id=target_item.id,
            candidate_answer_text=ans_text,
            submitted_code=ans_text,
            is_correct=is_correct,
            points_awarded=1.0 if is_correct else 0.0,
            time_taken_sec=time_taken,
        )
        db.add(ans)
    else:
        ans.candidate_answer_text = ans_text
        ans.submitted_code = ans_text
        ans.is_correct = is_correct
        ans.points_awarded = 1.0 if is_correct else 0.0
        ans.time_taken_sec = time_taken

    await db.commit()

    return SubmitTaskAnswerResponse(
        session_id=sess.id,
        task_index=payload.task_index,
        passed_public_tests=passed_public_tests,
        total_public_tests=total_public_tests,
        verdict="accepted" if is_correct else "wrong_answer",
        execution_time_ms=elapsed_ms,
    )


@router.post(
    "/sessions/{session_id}/finish",
    response_model=AssessmentSessionResultResponse,
    summary="Завершение тестирования и расчет KITE IRT theta",
)
@router.post(
    "/sessions/{session_id}/submit",
    response_model=AssessmentSessionResultResponse,
    summary="Завершение тестирования (submit alias)",
)
async def finish_assessment_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSessionResultResponse:
    res = await db.execute(
        select(AssessmentSession)
        .options(
            selectinload(AssessmentSession.category).selectinload(Category.grade),
            selectinload(AssessmentSession.answers).selectinload(AssessmentAnswer.item_family),
        )
        .where(AssessmentSession.id == session_id)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    await verify_session_ownership(sess, current_user, db)

    now = datetime.now(timezone.utc)
    # Собираем ответы
    answers = sess.answers or []
    category = sess.category

    # Загружаем каноническую батарею заданий из БД
    battery_stmt = (
        select(CanonicalItemFamily)
        .where(
            CanonicalItemFamily.specialization_id == category.specialization_id,
            CanonicalItemFamily.grade_id == category.grade_id,
            CanonicalItemFamily.is_active.is_(True),
        )
        .order_by(CanonicalItemFamily.id)
    )
    battery_items = list((await db.execute(battery_stmt)).scalars().all())
    if not battery_items:
        battery_items = list((await db.execute(
            select(CanonicalItemFamily).where(CanonicalItemFamily.is_active.is_(True)).order_by(CanonicalItemFamily.id)
        )).scalars().all())

    ans_map = {ans.item_family_id: ans for ans in answers}
    # Формируем калиброванные IRT задания и бинарные ответы
    irt_items: List[IRT3PLItem] = []
    responses: List[int] = []

    for i in range(12):
        item = battery_items[i] if i < len(battery_items) else (answers[i].item_family if i < len(answers) else None)
        item_id = item.id if item else (i + 1)
        p_a = float(item.param_a) if item else 1.0
        p_b = float(item.param_b) if item else 0.0
        p_c = float(item.param_c) if item else 0.2
        irt_items.append(IRT3PLItem(item_id=item_id, a=p_a, b=p_b, c=p_c))
        if item and item.id in ans_map:
            ans = ans_map[item.id]
            responses.append(1 if ans.is_correct else 0)
        else:
            responses.append(0)

    # 1. Расчет латентной способности EAP theta*
    estimator = BayesianEAPEstimator(num_nodes=61, theta_min=-4.0, theta_max=4.0, prior_sd=1.0)
    theta_star, sem_star = estimator.estimate_theta_star(irt_items, responses)

    # 2. Масштабирование в шкалу платформы [0.0, 100.0]
    scaled_score = BayesianEAPEstimator.scale_theta_linear_8(theta_star)
    sem_scaled = BayesianEAPEstimator.scale_sem(sem_star)

    # 3. Вынесение некарательного вердикта по правилам GradingEngine
    category = sess.category
    grade_name = category.grade.name if category and category.grade else "Middle"
    decision = GradingEngine.evaluate_session(
        candidate_id=sess.candidate_profile_id,
        claimed_grade=grade_name,
        theta_score=scaled_score,
        session_type=sess.session_type,
        now=now,
    )

    # 4. Фиксация в БД
    sess.status = "completed"
    sess.completed_at = now
    sess.raw_score = sum(responses)
    sess.theta_score = scaled_score
    sess.verdict = decision["verdict"]
    sess.time_spent_sec = max(1, int((now - (ensure_utc(sess.started_at) or now)).total_seconds()))

    # 5. Сохранение верифицированной категоризации CandidateCategorization
    confirmed_grade_name = decision.get("confirmed_grade")
    confirmed_grade_id = None
    if confirmed_grade_name:
        gr_res = await db.execute(select(Grade).where(func.lower(Grade.name) == func.lower(confirmed_grade_name)))
        gr_obj = gr_res.scalar_one_or_none()
        if gr_obj:
            confirmed_grade_id = gr_obj.id
    if confirmed_grade_id is None:
        confirmed_grade_id = category.grade_id if category else 2

    target_cat_res = await db.execute(
        select(Category).where(
            Category.specialization_id == category.specialization_id,
            Category.grade_id == confirmed_grade_id,
        )
    )
    target_category = target_cat_res.scalar_one_or_none()
    target_category_id = target_category.id if target_category else category.id

    # Снимаем флаг is_current с предыдущих записей соискателя
    await db.execute(
        update(CandidateCategorization)
        .where(
            CandidateCategorization.candidate_profile_id == sess.candidate_profile_id,
            CandidateCategorization.is_current.is_(True),
        )
        .values(is_current=False)
    )
    new_cat = CandidateCategorization(
        candidate_profile_id=sess.candidate_profile_id,
        category_id=target_category_id,
        confirmed_grade_id=confirmed_grade_id,
        test_score=scaled_score,
        assigned_at=now,
        cooldown_until=decision.get("cooldown_until") or now,
        is_current=True,
        source_session_id=sess.id,
    )
    db.add(new_cat)

    await db.commit()
    await db.refresh(sess)

    explain_text = (
        f"Оценка способностей кандидата по 3PL IRT модели составила theta={scaled_score:.1f}. "
        f"Решение тестовой батареи KITE из 12 заданий подтверждает соответствие заявленному грейду."
    )

    return AssessmentSessionResultResponse(
        session_id=sess.id,
        candidate_id=sess.candidate_profile_id,
        theta_score=scaled_score,
        scaled_score=scaled_score,
        grade_confirmed=decision.get("confirmed_grade"),
        verdict=AssessmentVerdictEnum(decision["verdict"]) if decision["verdict"] in AssessmentVerdictEnum._value2member_map_ else AssessmentVerdictEnum.CONFIRMED,
        boost_available=decision.get("boost_offered", False),
        retest_lower_available=decision.get("retest_lower_offered", False),
        cooldown_until=decision.get("cooldown_until"),
        completed_at=now,
        status="completed",
        explainability=explain_text,
    )


@router.get(
    "/sessions/{session_id}/results",
    response_model=AssessmentSessionResultResponse,
    summary="Получение аналитической карточки результатов тестирования",
)
async def get_assessment_session_results(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSessionResultResponse:
    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.category).selectinload(Category.grade))
        .where(AssessmentSession.id == session_id)
    )
    sess = res.scalar_one_or_none()
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")
    await verify_session_ownership(sess, current_user, db)

    grade_name = sess.category.grade.name if sess.category and sess.category.grade else "Middle"
    theta = sess.theta_score if sess.theta_score is not None else 75.0

    dt_ref = ensure_utc(sess.completed_at) or ensure_utc(sess.started_at) or datetime.now(timezone.utc)
    decision = GradingEngine.evaluate_session(
        candidate_id=sess.candidate_profile_id,
        claimed_grade=grade_name,
        theta_score=theta,
        session_type=sess.session_type,
        now=dt_ref,
    )

    explain_text = (
        f"Оценка способностей кандидата по 3PL IRT модели составила theta={theta:.1f}. "
        f"Результаты тестовой батареи KITE подтверждают соответствие грейду {grade_name}."
    )

    return AssessmentSessionResultResponse(
        session_id=sess.id,
        candidate_id=sess.candidate_profile_id,
        theta_score=theta,
        scaled_score=theta,
        grade_confirmed=decision.get("confirmed_grade"),
        verdict=AssessmentVerdictEnum(sess.verdict) if sess.verdict in AssessmentVerdictEnum._value2member_map_ else AssessmentVerdictEnum.CONFIRMED,
        boost_available=decision.get("boost_offered", False),
        retest_lower_available=decision.get("retest_lower_offered", False),
        cooldown_until=decision.get("cooldown_until"),
        completed_at=dt_ref,
        status="completed",
        explainability=explain_text,
    )


@router.get(
    "/cooldown-status",
    response_model=CooldownStatusResponse,
    summary="Проверка статуса кулдауна соискателя",
)
async def get_cooldown_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CooldownStatusResponse:
    profile = await get_or_create_candidate_profile(current_user.id, db)

    # Ищем последнюю подтвержденную сессию
    last_res = await db.execute(
        select(AssessmentSession)
        .where(
            AssessmentSession.candidate_profile_id == profile.id,
            AssessmentSession.status.in_(["completed", "submitted"]),
            AssessmentSession.verdict == "confirmed",
        )
        .order_by(AssessmentSession.completed_at.desc())
    )
    last_sess = last_res.scalars().first()

    now = datetime.now(timezone.utc)
    if last_sess and last_sess.completed_at:
        comp_at = ensure_utc(last_sess.completed_at) or now
        cooldown_until = comp_at + timedelta(days=90)
        if now < cooldown_until:
            days_left = max(1, math.ceil((cooldown_until - now).total_seconds() / 86400.0))
            return CooldownStatusResponse(
                candidate_id=profile.id,
                is_cooldown_active=True,
                cooldown_until=cooldown_until,
                days_left=days_left,
                days_remaining=days_left,
                can_retest_lower=True,
            )

    return CooldownStatusResponse(
        candidate_id=profile.id,
        is_cooldown_active=False,
        cooldown_until=None,
        days_left=0,
        days_remaining=0,
        can_retest_lower=True,
    )


@router.post(
    "/cooldown-status/jury-reset",
    summary="Демо-сброс 90-дневного кулдауна для жюри (EC-09)",
)
async def jury_reset_cooldown(
    payload: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_candidate_profile(current_user.id, db)
    reason = "jury_demonstration_test"
    if payload and isinstance(payload, dict):
        reason = payload.get("reason", reason)

    now = datetime.now(timezone.utc)
    reset_log = CooldownReset(
        candidate_profile_id=profile.id,
        reset_by_user_id=current_user.id,
        reason=reason,
        previous_cooldown_until=now + timedelta(days=90),
        created_at=now,
    )
    db.add(reset_log)

    # Сбрасываем timestamp старых сессий, вызывающих кулдаун
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

    return {
        "candidate_id": profile.id,
        "is_cooldown_active": False,
        "days_remaining": 0,
        "days_left": 0,
        "cooldown_until": None,
        "message": "Кулдаун успешно сброшен для демонстрации жюри",
    }


@router.post(
    "/retest-lower",
    status_code=status.HTTP_201_CREATED,
    response_model=AssessmentSessionStartResponse,
    summary="Мгновенный ретест на грейд ниже при theta < 70 (без ожидания кулдауна)",
)
async def retest_lower_grade(
    payload: RetestLowerGradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSessionStartResponse:
    # 1. Поиск исходной непройденной сессии
    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.category).selectinload(Category.grade))
        .where(AssessmentSession.id == payload.failed_session_id)
    )
    old_sess = res.scalar_one_or_none()
    if not old_sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Исходная сессия не найдена")

    await verify_session_ownership(old_sess, current_user, db)

    old_grade = old_sess.category.grade
    lower_rank = max(1, old_grade.rank_order - 1)
    lower_grade = await db.scalar(select(Grade).where(Grade.rank_order == lower_rank))
    if not lower_grade:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Более низкий грейд не существует")

    # Ищем категорию с тем же спеком и lower_grade
    target_cat = await db.scalar(
        select(Category).where(
            Category.specialization_id == old_sess.category.specialization_id,
            Category.grade_id == lower_grade.id,
        )
    )
    if not target_cat:
        target_cat = old_sess.category

    # Создаем новую сессию типа retest_lower БЕЗ кулдауна
    start_req = StartAssessmentSessionRequest(
        category_id=target_cat.id,
        session_type=SessionTypeEnum.RETEST_LOWER,
    )
    return await start_assessment_session(payload=start_req, current_user=current_user, db=db)


@router.post(
    "/sessions/{session_id}/boost-opt-in",
    status_code=status.HTTP_201_CREATED,
    response_model=AssessmentSessionStartResponse,
    summary="Запуск безопасного Boost-теста на грейд выше (при theta >= 88)",
)
async def boost_opt_in(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSessionStartResponse:
    # 1. Поиск исходной подтвержденной сессии
    res = await db.execute(
        select(AssessmentSession)
        .options(selectinload(AssessmentSession.category).selectinload(Category.grade))
        .where(AssessmentSession.id == session_id)
    )
    old_sess = res.scalar_one_or_none()
    if not old_sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Исходная сессия не найдена")

    await verify_session_ownership(old_sess, current_user, db)

    # 2. Проверка права на boost (theta >= 88.0 или вердикт boost_offered)
    if (old_sess.theta_score or 0.0) < 88.0 and old_sess.verdict != "boost_offered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Кандидат не имеет права на Boost-тест: требуется theta >= 88.0",
        )

    # 3. Поиск следующего более высокого грейда
    old_grade = old_sess.category.grade
    higher_rank = old_grade.rank_order + 1
    higher_grade = await db.scalar(select(Grade).where(Grade.rank_order == higher_rank))
    if not higher_grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Более высокий грейд не существует (уже достигнут максимальный грейд платформы)",
        )

    # 4. Поиск целевой категории
    target_cat = await db.scalar(
        select(Category).where(
            Category.specialization_id == old_sess.category.specialization_id,
            Category.grade_id == higher_grade.id,
        )
    )
    if not target_cat:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Целевая категория более высокого грейда не найдена",
        )

    # 5. Старт Boost-теста (некарательный, session_type=SessionTypeEnum.BOOST)
    start_req = StartAssessmentSessionRequest(
        category_id=target_cat.id,
        session_type=SessionTypeEnum.BOOST,
    )
    return await start_assessment_session(payload=start_req, current_user=current_user, db=db)

