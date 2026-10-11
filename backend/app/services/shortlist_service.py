"""
FSP IT-Talent Platform — Shortlist Service.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §4.1-4.3 and SPEC.md.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.saved_shortlists import SavedShortlist
from app.models.shortlist_items import ShortlistItem
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_skills import CandidateSkill
from app.models.candidate_categorizations import CandidateCategorization
from app.models.categories import Category
from app.models.employer_needs import EmployerNeed
from app.services.ranking_engine import (
    calculate_candidate_score,
    aggregate_candidate_fsp_data,
    GRADE_RANK_MAP,
)
from app.services.explainability_service import build_explainability


def sort_and_rank_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Two-tier sorting algorithm:
    1. Pinned items (is_pinned = True) sorted by match_score DESC, ranks 1..|P|
    2. Unpinned items (is_pinned = False) sorted by match_score DESC, ranks |P|+1..
    """
    pinned = [item for item in items if item.get("is_pinned")]
    unpinned = [item for item in items if not item.get("is_pinned")]

    pinned.sort(key=lambda x: (x.get("match_score", 0.0), x.get("candidate_profile_id", 0)), reverse=True)
    unpinned.sort(key=lambda x: (x.get("match_score", 0.0), x.get("candidate_profile_id", 0)), reverse=True)

    result: List[Dict[str, Any]] = []
    current_rank = 1

    for item in pinned:
        item_copy = dict(item)
        item_copy["rank_position"] = current_rank
        result.append(item_copy)
        current_rank += 1

    for item in unpinned:
        item_copy = dict(item)
        item_copy["rank_position"] = current_rank
        result.append(item_copy)
        current_rank += 1

    return result


async def pin_candidate_in_shortlist(
    db: AsyncSession,
    shortlist_id: int,
    candidate_profile_id: int,
    is_pinned: bool = True,
) -> Optional[ShortlistItem]:
    """
    Toggles candidate pinning status in a shortlist and recalibrates ranks.
    """
    stmt = (
        select(ShortlistItem)
        .where(
            ShortlistItem.shortlist_id == shortlist_id,
            ShortlistItem.candidate_profile_id == candidate_profile_id,
        )
    )
    res = await db.execute(stmt)
    item = res.scalar_one_or_none()
    if not item:
        return None

    item.is_pinned = is_pinned
    await db.flush()

    # Re-rank all items in this shortlist
    all_items_stmt = (
        select(ShortlistItem)
        .where(ShortlistItem.shortlist_id == shortlist_id)
    )
    items_res = await db.execute(all_items_stmt)
    all_items = list(items_res.scalars().all())

    pinned_items = [i for i in all_items if i.is_pinned]
    unpinned_items = [i for i in all_items if not i.is_pinned]

    pinned_items.sort(key=lambda x: (x.match_score, x.candidate_profile_id), reverse=True)
    unpinned_items.sort(key=lambda x: (x.match_score, x.candidate_profile_id), reverse=True)

    rank = 1
    for i in pinned_items:
        i.rank_position = rank
        rank += 1
    for i in unpinned_items:
        i.rank_position = rank
        rank += 1

    await db.commit()
    await db.refresh(item)
    return item


async def refine_shortlist_items(
    db: AsyncSession,
    shortlist: SavedShortlist,
    need: EmployerNeed,
) -> List[ShortlistItem]:
    """
    Refines shortlist matching:
    1. Recalculates new score S_new for each candidate.
    2. Computes delta S = S_new - S_old.
    3. Keeps pinned candidates at the top.
    """
    stmt = (
        select(ShortlistItem)
        .options(
            selectinload(ShortlistItem.candidate_profile)
                .selectinload(CandidateProfile.candidate_skills)
                .selectinload(CandidateSkill.skill),
            selectinload(ShortlistItem.candidate_profile)
                .selectinload(CandidateProfile.candidate_categorizations)
                .selectinload(CandidateCategorization.category)
                .selectinload(Category.specialization),
            selectinload(ShortlistItem.candidate_profile)
                .selectinload(CandidateProfile.candidate_categorizations)
                .selectinload(CandidateCategorization.category)
                .selectinload(Category.grade),
            selectinload(ShortlistItem.candidate_profile)
                .selectinload(CandidateProfile.candidate_categorizations)
                .selectinload(CandidateCategorization.confirmed_grade),
            selectinload(ShortlistItem.candidate_profile)
                .selectinload(CandidateProfile.fsp_achievements),
        )
        .where(ShortlistItem.shortlist_id == shortlist.id)
    )
    res = await db.execute(stmt)
    items = list(res.scalars().all())

    spec_code = need.specialization.code if hasattr(need, "specialization") and need.specialization else "backend"
    need_grade_rank = need.target_grade.rank_order if hasattr(need, "target_grade") and need.target_grade else 2

    for item in items:
        cand = item.candidate_profile
        # Extract candidate actual specialization and grade from latest categorization or profile survey
        cand_spec = "unknown"
        cand_grade_str = "middle"
        cand_grade_rank = 2
        theta = 50.0

        if cand.candidate_categorizations:
            curr_cat = next(
                (c for c in cand.candidate_categorizations if c.is_current),
                cand.candidate_categorizations[0],
            )
            theta = curr_cat.test_score
            if curr_cat.category:
                if curr_cat.category.specialization:
                    cand_spec = curr_cat.category.specialization.code
                elif getattr(curr_cat.category, "slug", None):
                    cand_spec = curr_cat.category.slug.split("-")[0]
                if curr_cat.category.grade:
                    cand_grade_str = curr_cat.category.grade.code
                    cand_grade_rank = curr_cat.category.grade.rank_order
            if hasattr(curr_cat, "confirmed_grade") and curr_cat.confirmed_grade:
                cand_grade_rank = curr_cat.confirmed_grade.rank_order
                cand_grade_str = curr_cat.confirmed_grade.code
        elif cand.survey_data_json and isinstance(cand.survey_data_json, dict):
            if cand.survey_data_json.get("specialization_code"):
                cand_spec = cand.survey_data_json["specialization_code"]
            if cand.survey_data_json.get("claimed_grade_code"):
                cand_grade_str = cand.survey_data_json["claimed_grade_code"]
                cand_grade_rank = GRADE_RANK_MAP.get(str(cand_grade_str).lower(), 2)

        if cand_spec == "unknown" and hasattr(cand, "specialization") and cand.specialization:
            cand_spec = cand.specialization.code if hasattr(cand.specialization, "code") else str(cand.specialization)

        cand_skills = [
            cs.skill.name if hasattr(cs, "skill") and cs.skill else "python"
            for cs in (cand.candidate_skills or [])
        ]

        fsp_data = aggregate_candidate_fsp_data(cand.fsp_id, getattr(cand, "fsp_achievements", []))

        calc = calculate_candidate_score(
            cand_spec=cand_spec,
            need_spec=spec_code,
            cand_grade=cand_grade_rank,
            need_grade=need_grade_rank,
            theta_score=theta,
            candidate_skills=cand_skills,
            core_stack=need.core_stack_json or [],
            nice_to_have=need.nice_to_have_stack_json or [],
            fsp_data=fsp_data,
            freshness_score=cand.freshness_score,
        )

        old_score = item.match_score
        new_score = calc["overall_score"]
        item.delta_score = round(new_score - old_score, 2)
        item.match_score = new_score

        expl = build_explainability(
            cand_spec=cand_spec,
            cand_grade=cand_grade_str,
            overall_score=new_score,
            test_subscore=calc["test_subscore"],
            stack_subscore=calc["stack_subscore"],
            fsp_subscore=calc["fsp_subscore"],
            freshness_subscore=calc["freshness_subscore"],
            grade_multiplier=calc["grade_multiplier"],
            weights=calc["weights"],
            candidate_skills=cand_skills,
            core_stack=need.core_stack_json or [],
            nice_to_have=need.nice_to_have_stack_json or [],
            fsp_data=fsp_data,
        )
        item.explainability_json = expl

    # Partition and assign rank positions
    pinned = [i for i in items if i.is_pinned]
    unpinned = [i for i in items if not i.is_pinned]

    pinned.sort(key=lambda x: (x.match_score, x.candidate_profile_id), reverse=True)
    unpinned.sort(key=lambda x: (x.match_score, x.candidate_profile_id), reverse=True)

    rank = 1
    for i in pinned:
        i.rank_position = rank
        rank += 1
    for i in unpinned:
        i.rank_position = rank
        rank += 1

    await db.commit()
    return items
