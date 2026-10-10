"""
FSP IT-Talent Platform — API Module 8: candidate-bank.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.8 and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.api.v1.employer_needs import get_current_employer
from app.database import get_db
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_categorizations import CandidateCategorization
from app.models.candidate_skills import CandidateSkill
from app.models.categories import Category
from app.models.employer_needs import EmployerNeed
from app.models.employer_profiles import EmployerProfile
from app.models.invitations import Invitation
from app.models.saved_shortlists import SavedShortlist
from app.models.shortlist_items import ShortlistItem
from app.models.users import User
from app.schemas.base import PaginationMeta
from app.schemas.candidate_bank import (
    CandidateAnonymizedDetailResponse,
    CandidateBankCard,
    CandidateBankSearchResponse,
    CandidateUnmaskedContactsResponse,
    CategoryCatalogItem,
    CreateShortlistRequest,
    PinCandidateRequest,
    RefineShortlistRequest,
    SavedShortlistDetailResponse,
    SavedShortlistSummaryResponse,
    ShortlistItemResponse,
)
from app.services.ranking_engine import calculate_candidate_score, aggregate_candidate_fsp_data
from app.services.explainability_service import build_explainability
from app.services.shortlist_service import pin_candidate_in_shortlist, refine_shortlist_items
from app.services.anonymizer import check_contact_access, format_full_name

router = APIRouter(prefix="/candidate-bank", tags=["candidate-bank"])


def _mask_candidate_name(first_name: str, last_name: str, cand_id: int) -> str:
    """Masks candidate name per 152-ФЗ: 'Алексей К. (#C-1042)'."""
    initial = f"{last_name[:1]}." if last_name else ""
    return f"{first_name} {initial} (#C-{cand_id})"


def _build_candidate_card(
    cand: CandidateProfile,
    score_data: Optional[Dict[str, Any]] = None,
    explainability: Optional[Dict[str, Any]] = None,
    invitation_status: Optional[str] = None,
) -> CandidateBankCard:
    spec_code = "backend"
    grade_code = "middle"
    test_score = 0.0

    has_cats = False
    try:
        has_cats = bool(cand.candidate_categorizations)
    except Exception:
        has_cats = False

    if has_cats:
        curr_cat = next((c for c in cand.candidate_categorizations if c.is_current), cand.candidate_categorizations[0])
        test_score = curr_cat.test_score
        if hasattr(curr_cat, "category") and curr_cat.category:
            if hasattr(curr_cat.category, "specialization") and curr_cat.category.specialization:
                spec_code = curr_cat.category.specialization.code
            if hasattr(curr_cat.category, "grade") and curr_cat.category.grade:
                grade_code = curr_cat.category.grade.code
    elif cand.survey_data_json and isinstance(cand.survey_data_json, dict):
        if cand.survey_data_json.get("specialization_code"):
            spec_code = cand.survey_data_json["specialization_code"]
        if cand.survey_data_json.get("claimed_grade_code"):
            grade_code = cand.survey_data_json["claimed_grade_code"]

    cat_code = f"{spec_code}_{grade_code}"
    cat_badge = f"{spec_code.capitalize()} · {grade_code.capitalize()}"
    fsp_badge = "Верифицирован ФСП" if cand.fsp_verified else "Платформенная верификация"

    cand_skills_list = []
    try:
        cand_skills_list = cand.candidate_skills or []
    except Exception:
        cand_skills_list = []

    skills = [
        cs.skill.name if hasattr(cs, "skill") and cs.skill else "python"
        for cs in cand_skills_list
    ]

    return CandidateBankCard(
        id=cand.id,
        user_id=cand.user_id,
        masked_full_name=_mask_candidate_name(cand.first_name, cand.last_name, cand.id),
        specialization=spec_code,
        grade=grade_code,
        category_code=cat_code,
        category_badge=cat_badge,
        test_score=round(test_score, 1),
        freshness_score=round(cand.freshness_score, 1),
        city=cand.city,
        work_format=cand.work_format,
        relocation_ready=cand.relocation_ready,
        expected_salary=cand.expected_salary,
        fsp_id=cand.fsp_id,
        fsp_verified=cand.fsp_verified,
        fsp_badge=fsp_badge,
        skills=skills,
        match_score=score_data.get("overall_score") if score_data else None,
        explainability=explainability,
        invitation_status=invitation_status,
        is_contacts_unmasked=False,
        created_at=cand.created_at,
    )


@router.get(
    "",
    response_model=CandidateBankSearchResponse,
    summary="Фасетный поиск талантов с многофакторным скорингом S и Explainability",
)
@router.get(
    "/search",
    response_model=CandidateBankSearchResponse,
    include_in_schema=False,
)
async def search_candidate_bank(
    specialization: Optional[str] = Query(None, description="Код специализации"),
    grade: Optional[str] = Query(None, description="Код грейда"),
    need_id: Optional[int] = Query(None, description="ID потребности работодателя для привязки ранжирования"),
    city: Optional[str] = Query(None),
    work_format: Optional[str] = Query(None),
    relocation_ready: Optional[bool] = Query(None),
    skills: Optional[List[str]] = Query(None),
    min_salary: Optional[int] = Query(None),
    max_salary: Optional[int] = Query(None),
    fsp_only: Optional[bool] = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateBankSearchResponse:
    if current_user.role not in ("employer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ к банку кандидатов разрешен только работодателям (ERR_EMPLOYER_ROLE_REQUIRED)",
        )

    # 1. Resolve employer need if requested
    target_need: Optional[EmployerNeed] = None
    if need_id:
        need_stmt = (
            select(EmployerNeed)
            .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
            .where(EmployerNeed.id == need_id)
        )
        target_need = (await db.execute(need_stmt)).scalar_one_or_none()

    target_spec = specialization or (
        target_need.specialization.code if target_need and target_need.specialization else "backend"
    )
    target_grade = grade or (
        target_need.target_grade.code if target_need and target_need.target_grade else "middle"
    )
    core_stack = target_need.core_stack_json if target_need else (skills or [])
    nice_stack = target_need.nice_to_have_stack_json if target_need else []

    # 2. Query candidates
    cand_stmt = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.candidate_categorizations)
            .selectinload(CandidateCategorization.category)
            .selectinload(Category.specialization),
            selectinload(CandidateProfile.candidate_categorizations)
            .selectinload(CandidateCategorization.category)
            .selectinload(Category.grade),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(
                CandidateCategorization.confirmed_grade
            ),
            selectinload(CandidateProfile.fsp_achievements),
        )
        .where(CandidateProfile.is_published.is_(True))
    )

    if city:
        cand_stmt = cand_stmt.where(CandidateProfile.city == city)
    if work_format and work_format != "any":
        cand_stmt = cand_stmt.where(CandidateProfile.work_format == work_format)
    if relocation_ready is not None:
        cand_stmt = cand_stmt.where(CandidateProfile.relocation_ready == relocation_ready)
    if fsp_only:
        cand_stmt = cand_stmt.where(CandidateProfile.fsp_id.isnot(None))
    if min_salary is not None:
        cand_stmt = cand_stmt.where(CandidateProfile.expected_salary >= min_salary)
    if max_salary is not None:
        cand_stmt = cand_stmt.where(CandidateProfile.expected_salary <= max_salary)

    candidates = list((await db.execute(cand_stmt)).scalars().all())

    # Query existing invitations between employer and candidates in the batch
    emp_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == current_user.id)
    employer_profile_id = await db.scalar(emp_stmt)

    cand_ids = [c.id for c in candidates]
    invitations_map: Dict[int, str] = {}
    if employer_profile_id and cand_ids:
        inv_stmt = (
            select(Invitation.candidate_profile_id, Invitation.status)
            .where(
                Invitation.employer_profile_id == employer_profile_id,
                Invitation.candidate_profile_id.in_(cand_ids),
            )
            .order_by(Invitation.created_at.desc())
        )
        inv_rows = (await db.execute(inv_stmt)).all()
        for c_id, inv_status in inv_rows:
            if c_id not in invitations_map:
                invitations_map[c_id] = inv_status

    # 3. Calculate multi-factor scores and explainability for each candidate
    scored_candidates = []
    for cand in candidates:
        cand_spec = target_spec
        cand_grade = target_grade
        theta = 0.0

        if cand.candidate_categorizations:
            curr_cat = next(
                (c for c in cand.candidate_categorizations if c.is_current),
                cand.candidate_categorizations[0],
            )
            theta = curr_cat.test_score
            if curr_cat.category:
                if curr_cat.category.specialization:
                    cand_spec = curr_cat.category.specialization.code
                if curr_cat.category.grade:
                    cand_grade = curr_cat.category.grade.code
        elif cand.survey_data_json and isinstance(cand.survey_data_json, dict):
            if cand.survey_data_json.get("specialization_code"):
                cand_spec = cand.survey_data_json["specialization_code"]
            if cand.survey_data_json.get("claimed_grade_code"):
                cand_grade = cand.survey_data_json["claimed_grade_code"]

        cand_skills = [
            cs.skill.name if hasattr(cs, "skill") and cs.skill else "python"
            for cs in (cand.candidate_skills or [])
        ]

        fsp_data = aggregate_candidate_fsp_data(cand.fsp_id, getattr(cand, "fsp_achievements", []))

        calc = calculate_candidate_score(
            cand_spec=cand_spec,
            need_spec=target_spec,
            cand_grade=cand_grade,
            need_grade=target_grade,
            theta_score=theta,
            candidate_skills=cand_skills,
            core_stack=core_stack,
            nice_to_have=nice_stack,
            fsp_data=fsp_data,
            freshness_score=cand.freshness_score,
        )

        expl = build_explainability(
            cand_spec=cand_spec,
            cand_grade=cand_grade,
            overall_score=calc["overall_score"],
            test_subscore=calc["test_subscore"],
            stack_subscore=calc["stack_subscore"],
            fsp_subscore=calc["fsp_subscore"],
            freshness_subscore=calc["freshness_subscore"],
            grade_multiplier=calc["grade_multiplier"],
            weights=calc["weights"],
            candidate_skills=cand_skills,
            core_stack=core_stack,
            nice_to_have=nice_stack,
            fsp_data=fsp_data,
        )

        card = _build_candidate_card(
            cand,
            calc,
            expl,
            invitation_status=invitations_map.get(cand.id),
        )
        scored_candidates.append(card)

    # 4. Sort by match_score DESC, then candidate ID
    scored_candidates.sort(key=lambda x: (x.match_score or 0.0, x.id), reverse=True)

    total = len(scored_candidates)
    start_idx = (page - 1) * page_size
    items = scored_candidates[start_idx : start_idx + page_size]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return CandidateBankSearchResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
        filter_echo={
            "specialization": target_spec,
            "grade": target_grade,
            "need_id": need_id,
            "city": city,
            "work_format": work_format,
            "fsp_only": fsp_only,
        },
    )


@router.get(
    "/categories",
    response_model=List[CategoryCatalogItem],
    summary="Каталог 24 канонических категорий",
)
async def list_categories_catalog(
    db: AsyncSession = Depends(get_db),
) -> List[CategoryCatalogItem]:
    stmt = (
        select(Category)
        .options(selectinload(Category.specialization), selectinload(Category.grade))
        .order_by(Category.id.asc())
    )
    categories = list((await db.execute(stmt)).scalars().all())

    items = []
    for cat in categories:
        spec_code = cat.specialization.code if cat.specialization else "backend"
        spec_name = cat.specialization.name if cat.specialization else "Backend Разработка"
        grade_code = cat.grade.code if cat.grade else "middle"
        grade_name = cat.grade.name if cat.grade else "Middle"

        items.append(
            CategoryCatalogItem(
                id=cat.id,
                specialization_code=spec_code,
                specialization_title=spec_name,
                grade_code=grade_code,
                grade_title=grade_name,
                category_code=cat.slug,
                category_title=cat.title,
                verified_candidates_count=12,
            )
        )
    return items


@router.get(
    "/shortlists",
    response_model=List[SavedShortlistSummaryResponse],
    summary="Список сохраненных выборок текущего работодателя",
)
async def list_employer_shortlists(
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> List[SavedShortlistSummaryResponse]:
    stmt = (
        select(SavedShortlist)
        .options(selectinload(SavedShortlist.items))
        .where(SavedShortlist.employer_profile_id == employer.id)
        .order_by(SavedShortlist.created_at.desc())
    )
    shortlists = list((await db.execute(stmt)).scalars().all())

    return [
        SavedShortlistSummaryResponse(
            id=s.id,
            title=s.title,
            need_id=s.need_id,
            candidates_count=len(s.items),
            pinned_count=sum(1 for i in s.items if i.is_pinned),
            created_at=s.created_at,
        )
        for s in shortlists
    ]


@router.post(
    "/shortlists",
    status_code=status.HTTP_201_CREATED,
    response_model=SavedShortlistDetailResponse,
    summary="Создание сохраненной выборки соискателей",
)
async def create_shortlist(
    payload: CreateShortlistRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> SavedShortlistDetailResponse:
    shortlist = SavedShortlist(
        employer_profile_id=employer.id,
        need_id=payload.need_id,
        title=payload.title,
        filter_criteria_json=payload.filter_criteria_json,
    )
    db.add(shortlist)
    await db.commit()
    await db.refresh(shortlist)

    # Add initial candidate items if provided
    rank = 1
    for cid in payload.candidate_ids:
        item = ShortlistItem(
            shortlist_id=shortlist.id,
            candidate_profile_id=cid,
            is_pinned=False,
            match_score=85.0,
            delta_score=0.0,
            rank_position=rank,
            explainability_json={},
        )
        db.add(item)
        rank += 1
    if payload.candidate_ids:
        await db.commit()

    # Re-fetch full details
    return await get_shortlist_by_id(shortlist.id, employer, db)


@router.get(
    "/shortlists/{id}",
    response_model=SavedShortlistDetailResponse,
    summary="Просмотр сохраненного шортлиста",
)
async def get_shortlist_by_id(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> SavedShortlistDetailResponse:
    stmt = (
        select(SavedShortlist)
        .options(
            selectinload(SavedShortlist.items)
            .selectinload(ShortlistItem.candidate_profile)
            .selectinload(CandidateProfile.candidate_skills)
            .selectinload(CandidateSkill.skill),
            selectinload(SavedShortlist.items)
            .selectinload(ShortlistItem.candidate_profile)
            .selectinload(CandidateProfile.candidate_categorizations)
            .selectinload(CandidateCategorization.category),
            selectinload(SavedShortlist.items)
            .selectinload(ShortlistItem.candidate_profile)
            .selectinload(CandidateProfile.fsp_achievements),
        )
        .where(SavedShortlist.id == id, SavedShortlist.employer_profile_id == employer.id)
    )
    shortlist = (await db.execute(stmt)).scalar_one_or_none()
    if not shortlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шортлист не найден",
        )

    # Two-tier sort items: pinned on top, then unpinned
    pinned = [i for i in shortlist.items if i.is_pinned]
    unpinned = [i for i in shortlist.items if not i.is_pinned]
    pinned.sort(key=lambda x: (x.match_score, x.candidate_profile_id), reverse=True)
    unpinned.sort(key=lambda x: (x.match_score, x.candidate_profile_id), reverse=True)
    sorted_items = pinned + unpinned

    shortlist_cand_ids = [item.candidate_profile_id for item in sorted_items]
    inv_map: Dict[int, str] = {}
    if shortlist_cand_ids:
        inv_res = await db.execute(
            select(Invitation.candidate_profile_id, Invitation.status)
            .where(
                Invitation.employer_profile_id == employer.id,
                Invitation.candidate_profile_id.in_(shortlist_cand_ids),
            )
            .order_by(Invitation.created_at.desc())
        )
        for c_id, inv_status in inv_res.all():
            if c_id not in inv_map:
                inv_map[c_id] = inv_status

    item_responses = []
    for pos, item in enumerate(sorted_items, start=1):
        cand = item.candidate_profile
        card = _build_candidate_card(
            cand,
            {"overall_score": item.match_score},
            item.explainability_json,
            invitation_status=inv_map.get(cand.id),
        )
        item_responses.append(
            ShortlistItemResponse(
                id=item.id,
                shortlist_id=item.shortlist_id,
                candidate_profile_id=item.candidate_profile_id,
                is_pinned=item.is_pinned,
                match_score=item.match_score,
                delta_score=item.delta_score,
                rank_position=pos,
                explainability=item.explainability_json,
                candidate_card=card,
            )
        )

    return SavedShortlistDetailResponse(
        id=shortlist.id,
        employer_profile_id=shortlist.employer_profile_id,
        need_id=shortlist.need_id,
        title=shortlist.title,
        filter_criteria_json=shortlist.filter_criteria_json,
        pinned_count=len(pinned),
        items=item_responses,
        created_at=shortlist.created_at,
        updated_at=shortlist.updated_at,
    )


@router.post(
    "/shortlists/{id}/pin",
    response_model=ShortlistItemResponse,
    summary="Закрепление кандидата в верхнем ярусе выборки",
)
@router.post(
    "/shortlists/{id}/pin/{candidate_id}",
    response_model=ShortlistItemResponse,
    include_in_schema=False,
)
async def pin_candidate(
    id: int,
    candidate_id: Optional[int] = None,
    payload: Optional[PinCandidateRequest] = None,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> ShortlistItemResponse:
    target_cid = candidate_id or (payload.candidate_profile_id if payload else None)
    if not target_cid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не указан ID кандидата для закрепления",
        )

    is_pinned = payload.is_pinned if payload else True

    # Check shortlist ownership
    s_stmt = select(SavedShortlist).where(SavedShortlist.id == id, SavedShortlist.employer_profile_id == employer.id)
    shortlist = (await db.execute(s_stmt)).scalar_one_or_none()
    if not shortlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шортлист не найден",
        )

    item = await pin_candidate_in_shortlist(db, id, target_cid, is_pinned=is_pinned)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден в данном шортлисте",
        )

    # Fetch candidate profile to build card
    c_stmt = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.candidate_categorizations),
            selectinload(CandidateProfile.fsp_achievements),
        )
        .where(CandidateProfile.id == target_cid)
    )
    cand = (await db.execute(c_stmt)).scalar_one()
    inv_status = await db.scalar(
        select(Invitation.status)
        .where(
            Invitation.employer_profile_id == employer.id,
            Invitation.candidate_profile_id == target_cid,
        )
        .order_by(Invitation.created_at.desc())
    )
    card = _build_candidate_card(
        cand,
        {"overall_score": item.match_score},
        item.explainability_json,
        invitation_status=inv_status,
    )

    return ShortlistItemResponse(
        id=item.id,
        shortlist_id=item.shortlist_id,
        candidate_profile_id=item.candidate_profile_id,
        is_pinned=item.is_pinned,
        match_score=item.match_score,
        delta_score=item.delta_score,
        rank_position=item.rank_position,
        explainability=item.explainability_json,
        candidate_card=card,
    )


@router.post(
    "/shortlists/{id}/refine",
    response_model=SavedShortlistDetailResponse,
    summary="Дифференциальное переранжирование шортлиста с расчетом Delta S",
)
async def refine_shortlist(
    id: int,
    payload: RefineShortlistRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> SavedShortlistDetailResponse:
    s_stmt = select(SavedShortlist).where(SavedShortlist.id == id, SavedShortlist.employer_profile_id == employer.id)
    shortlist = (await db.execute(s_stmt)).scalar_one_or_none()
    if not shortlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шортлист не найден",
        )

    need_id = payload.refined_need_id or shortlist.need_id
    if need_id:
        n_stmt = (
            select(EmployerNeed)
            .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
            .where(EmployerNeed.id == need_id)
        )
        need = (await db.execute(n_stmt)).scalar_one_or_none()
        if need:
            await refine_shortlist_items(db, shortlist, need)

    shortlist.filter_criteria_json = payload.new_filter_criteria_json
    await db.commit()

    return await get_shortlist_by_id(id, employer, db)


@router.delete(
    "/shortlists/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление сохраненной выборки",
)
async def delete_shortlist(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    s_stmt = select(SavedShortlist).where(SavedShortlist.id == id, SavedShortlist.employer_profile_id == employer.id)
    shortlist = (await db.execute(s_stmt)).scalar_one_or_none()
    if not shortlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Шортлист не найден",
        )
    await db.delete(shortlist)
    await db.commit()


@router.get(
    "/{id}",
    response_model=CandidateAnonymizedDetailResponse,
    summary="Детальная карточка кандидата со строго замаскированными контактами (152-ФЗ)",
)
async def get_candidate_anonymized(
    id: int,
    need_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateAnonymizedDetailResponse:
    if current_user.role not in ("employer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ разрешен только работодателям и администраторам",
        )

    stmt = (
        select(CandidateProfile)
        .options(
            selectinload(CandidateProfile.candidate_skills).selectinload(CandidateSkill.skill),
            selectinload(CandidateProfile.candidate_categorizations)
            .selectinload(CandidateCategorization.category)
            .selectinload(Category.specialization),
            selectinload(CandidateProfile.candidate_categorizations)
            .selectinload(CandidateCategorization.category)
            .selectinload(Category.grade),
            selectinload(CandidateProfile.candidate_categorizations).selectinload(
                CandidateCategorization.confirmed_grade
            ),
            selectinload(CandidateProfile.fsp_achievements),
            selectinload(CandidateProfile.user),
        )
        .where(CandidateProfile.id == id)
    )
    cand = (await db.execute(stmt)).scalar_one_or_none()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )

    has_access = await check_contact_access(db, cand.id, current_user)

    spec_code = "backend"
    grade_code = "middle"
    test_score = 0.0
    cat_title = "Backend Разработка · Middle"

    if cand.candidate_categorizations:
        curr_cat = next((c for c in cand.candidate_categorizations if c.is_current), cand.candidate_categorizations[0])
        test_score = curr_cat.test_score
        if curr_cat.category:
            cat_title = curr_cat.category.title
            if curr_cat.category.specialization:
                spec_code = curr_cat.category.specialization.code
            if curr_cat.category.grade:
                grade_code = curr_cat.category.grade.code
    elif cand.survey_data_json and isinstance(cand.survey_data_json, dict):
        if cand.survey_data_json.get("specialization_code"):
            spec_code = cand.survey_data_json["specialization_code"]
        if cand.survey_data_json.get("claimed_grade_code"):
            grade_code = cand.survey_data_json["claimed_grade_code"]
        cat_title = f"{spec_code.capitalize()} · {grade_code.capitalize()}"

    fsp_badge = "Верифицирован ФСП" if cand.fsp_verified else "Платформенная верификация"
    skills = [
        cs.skill.name if hasattr(cs, "skill") and cs.skill else "python"
        for cs in (cand.candidate_skills or [])
    ]

    # Optional explainability
    expl = None
    if need_id:
        n_stmt = (
            select(EmployerNeed)
            .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
            .where(EmployerNeed.id == need_id)
        )
        need = (await db.execute(n_stmt)).scalar_one_or_none()
        if need:
            fsp_data = aggregate_candidate_fsp_data(cand.fsp_id, getattr(cand, "fsp_achievements", []))
            calc = calculate_candidate_score(
                cand_spec=spec_code,
                need_spec=need.specialization.code if need.specialization else "backend",
                cand_grade=grade_code,
                need_grade=need.target_grade.code if need.target_grade else "middle",
                theta_score=test_score,
                candidate_skills=skills,
                core_stack=need.core_stack_json or [],
                nice_to_have=need.nice_to_have_stack_json or [],
                fsp_data=fsp_data,
                freshness_score=cand.freshness_score,
            )
            expl = build_explainability(
                cand_spec=spec_code,
                cand_grade=grade_code,
                overall_score=calc["overall_score"],
                test_subscore=calc["test_subscore"],
                stack_subscore=calc["stack_subscore"],
                fsp_subscore=calc["fsp_subscore"],
                freshness_subscore=calc["freshness_subscore"],
                grade_multiplier=calc["grade_multiplier"],
                weights=calc["weights"],
                candidate_skills=skills,
                core_stack=need.core_stack_json or [],
                nice_to_have=need.nice_to_have_stack_json or [],
                fsp_data=fsp_data,
            )

    serialized_fsp_achievements = [
        {
            "id": ach.id,
            "fsp_id": ach.fsp_id,
            "championship_name": ach.championship_name,
            "discipline": ach.discipline,
            "stage": ach.stage,
            "year": ach.year,
            "place": ach.place,
            "medal": ach.medal,
            "sport_rank": ach.sport_rank,
            "rating_points": ach.rating_points,
            "certificate_url": ach.certificate_url,
        }
        for ach in (cand.fsp_achievements or [])
    ]

    return CandidateAnonymizedDetailResponse(
        id=cand.id,
        user_id=cand.user_id,
        masked_full_name=(
            format_full_name(cand.first_name, cand.last_name, cand.middle_name)
            if has_access
            else _mask_candidate_name(cand.first_name, cand.last_name, cand.id)
        ),
        specialization=spec_code,
        grade=grade_code,
        category_title=cat_title,
        bio=cand.bio,
        city=cand.city,
        work_format=cand.work_format,
        relocation_ready=cand.relocation_ready,
        expected_salary=cand.expected_salary,
        skills=skills,
        test_score=round(test_score, 1),
        freshness_score=round(cand.freshness_score, 1),
        fsp_id=cand.fsp_id,
        fsp_verified=cand.fsp_verified,
        fsp_badge=fsp_badge,
        fsp_achievements=serialized_fsp_achievements,
        anonymized_pdf_url=f"/api/v1/resume-pdf/{cand.id}/anonymized",
        is_contacts_masked=not has_access,
        email=cand.user.email if (has_access and cand.user) else None,
        phone=cand.phone if has_access else None,
        telegram=cand.telegram if has_access else None,
        github_url=cand.github_url if has_access else None,
        raw_resume_pdf_url=f"/api/v1/resume-pdf/{cand.id}/full" if has_access else None,
        explainability=expl,
        created_at=cand.created_at,
    )


@router.get(
    "/{id}/contacts",
    response_model=CandidateUnmaskedContactsResponse,
    summary="Шлюз проверки доступа к контактам (152-ФЗ барьер взаимного согласия)",
)
async def get_candidate_contacts(
    id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CandidateUnmaskedContactsResponse:
    """
    Candidate contacts are strictly masked until invitation is accepted or direct application submitted.
    Admins have authorized access.
    """
    stmt = select(CandidateProfile).options(selectinload(CandidateProfile.user)).where(CandidateProfile.id == id)
    cand = (await db.execute(stmt)).scalar_one_or_none()
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )

    has_access = await check_contact_access(db, cand.id, current_user)
    if has_access or current_user.role == "admin":
        full_name = format_full_name(cand.first_name, cand.last_name, cand.middle_name)
        return CandidateUnmaskedContactsResponse(
            candidate_id=cand.id,
            full_name=full_name,
            email=cand.user.email if cand.user else f"candidate_{cand.id}@fsp.ru",
            phone=cand.phone,
            telegram=cand.telegram,
            github_url=cand.github_url,
            raw_resume_pdf_url=cand.raw_resume_pdf_path,
            full_pdf_url=f"/api/v1/resume-pdf/{cand.id}/full",
            unmasked_reason="invitation_accepted",
            unmasked_at=datetime.now(timezone.utc),
        )

    # 152-FZ Barrier check
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Контакты соискателя защищены Федеральным законом № 152-ФЗ. "
            "Раскрытие разрешено только после явного принятия приглашения (статус 'accepted')."
        ),
    )
