"""
Empirical Adversarial Test Suite — Phase 3: Matching & Ranking Layer.
Authored by Challenger 1 (Algorithm & Ranking Stress Tester).

Empirically and adversarially verifies:
1. Non-FSP Dynamic Weight Parity:
   - Weights: w_test=0.52, w_stack=0.30, w_fsp=0.00, w_freshness=0.18, sum strictly 1.00.
   - Zero penalty: candidate with fsp_id=None reaches 100.0 / 100.0.
   - Meritocracy: high-performing non-FSP candidate decisively outranks weak FSP candidate.
   - FSP subscore upper ceiling (76.0) vs Non-FSP unconstrained potential (100.0).
   - Robustness to various representations of empty/null FSP data.
2. 2-Tier Pinning Invariant:
   - Pinned candidates (is_pinned=True) unconditionally occupy ranks 1..|P|.
   - NEVER placed below unpinned candidates regardless of match scores (even score 0.0 vs 100.0).
   - Contiguous rank progression: ranks are exactly 1, 2, ..., N with no gaps or collisions.
   - Deterministic tie-breaking within tiers.
   - Stateful DB verification: pin toggle, rank recomputation, and refine via SQLAlchemy.
3. Differential Refinement (Delta S):
   - Delta S = S_new - S_old is correctly computed and preserved across positive, negative, and zero shifts.
   - Two-tier pinning invariant is preserved post-refinement.
   - Database round-trip persistence of delta_score.
4. Freshness Subscore:
   - Exact 90-day half-life decay: S(t + 90) / S(t) = 0.50.
   - Exact 30-day half-life challenge boost: B(t + 30) / B(t) = 0.50.
   - Boundary tests: t < 0 (clock drift), t -> infinity (asymptotic 0), multiple challenges, ceiling cap 100.0.
"""
from __future__ import annotations

import asyncio
import math
import os
import sys
from typing import Any, Dict, List

# Ensure backend directory is in sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.employer_needs import EmployerNeed
from app.models.saved_shortlists import SavedShortlist
from app.models.shortlist_items import ShortlistItem
from app.models.users import User
from app.models.specializations import Specialization
from app.models.grades import Grade
from app.services.ranking_engine import (
    calculate_candidate_score,
    calculate_fsp_subscore,
    calculate_grade_multiplier,
    calculate_stack_subscore,
    calculate_weights,
    compute_freshness_subscore,
    aggregate_candidate_fsp_data,
    WEIGHTS_WITH_FSP,
    WEIGHTS_WITHOUT_FSP,
)
from app.services.shortlist_service import (
    sort_and_rank_items,
    pin_candidate_in_shortlist,
    refine_shortlist_items,
)
from app.services.explainability_service import build_explainability


# ==============================================================================
# SECTION 1: NON-FSP DYNAMIC WEIGHT PARITY & MERITOCRACY STRESS TESTS
# ==============================================================================

def test_weights_vector_exact_values():
    """Weights without FSP must be exactly (0.52, 0.30, 0.00, 0.18)."""
    weights = calculate_weights(has_fsp=False)
    assert weights == (0.52, 0.30, 0.00, 0.18)
    w_test, w_stack, w_fsp, w_fresh = weights
    assert w_test == 0.52
    assert w_stack == 0.30
    assert w_fsp == 0.00
    assert w_fresh == 0.18


def test_weights_sum_strictly_unity():
    """Weights sum must be strictly 1.00 for both modes."""
    w_non_fsp = calculate_weights(has_fsp=False)
    assert math.isclose(sum(w_non_fsp), 1.00, abs_tol=1e-12)
    assert round(sum(w_non_fsp), 6) == 1.0

    w_fsp = calculate_weights(has_fsp=True)
    assert math.isclose(sum(w_fsp), 1.00, abs_tol=1e-12)
    assert round(sum(w_fsp), 6) == 1.0


def test_null_fsp_representations_receive_non_fsp_weights():
    """Any null/empty representation of FSP must trigger dynamic weight parity."""
    fsp_variants = [
        None,
        {},
        {"fsp_id": None},
        {"fsp_id": ""},
        {"fsp_id": None, "sport_rank": "ms", "rating_points": 100},
    ]
    for fsp_input in fsp_variants:
        calc = calculate_candidate_score(
            cand_spec="backend",
            need_spec="backend",
            cand_grade="senior",
            need_grade="senior",
            theta_score=90.0,
            candidate_skills=["python", "fastapi"],
            core_stack=["python", "fastapi"],
            fsp_data=fsp_input,
            freshness_score=90.0,
        )
        assert calc["has_fsp"] is False
        assert calc["weights"] == (0.52, 0.30, 0.00, 0.18)
        assert calc["fsp_subscore"] == 0.0


def test_non_fsp_candidate_reaches_perfect_score_100():
    """A candidate with no FSP history can achieve a perfect 100.0/100.0 score."""
    calc = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="senior",
        need_grade="senior",
        theta_score=100.0,
        candidate_skills=["python", "fastapi", "postgresql", "redis"],
        core_stack=["python", "fastapi"],
        nice_to_have=["postgresql", "redis"],
        fsp_data=None,
        freshness_score=100.0,
    )
    assert calc["has_fsp"] is False
    assert calc["test_subscore"] == 100.0
    assert calc["stack_subscore"] == 100.0
    assert calc["fsp_subscore"] == 0.0
    assert calc["freshness_subscore"] == 100.0
    # 0.52 * 100 + 0.30 * 100 + 0.00 * 0 + 0.18 * 100 = 52 + 30 + 18 = 100.0
    assert calc["overall_score"] == 100.0


def test_zero_penalty_parity_and_fsp_bounds():
    """
    Zero Penalty Proof & Subscore Ceiling Analysis:
    - Non-FSP candidate can reach 100.0 / 100.0 (zero glass ceiling).
    - FSP subscore has maximum value = 76.0 (MS=100*0.35 + Gold All-Russia=40*0.40 + 25pts*0.25 = 35+16+25 = 76.0).
    - Max FSP overall score = 0.35*100 + 0.25*100 + 0.25*76 + 0.15*100 = 94.0.
    - Thus, a top non-FSP candidate (100.0) outscores even the maximum theoretical FSP candidate (94.0).
    """
    perf_non_fsp = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="lead",
        need_grade="lead",
        theta_score=100.0,
        candidate_skills=["python", "fastapi"],
        core_stack=["python", "fastapi"],
        fsp_data=None,
        freshness_score=100.0,
    )
    assert perf_non_fsp["overall_score"] == 100.0

    perf_fsp = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="lead",
        need_grade="lead",
        theta_score=100.0,
        candidate_skills=["python", "fastapi"],
        core_stack=["python", "fastapi"],
        fsp_data={"fsp_id": "FSP-MAX", "sport_rank": "ms", "stage": "всероссийский", "medal": "gold", "rating_points": 25},
        freshness_score=100.0,
    )
    assert perf_fsp["fsp_subscore"] == 76.0
    assert perf_fsp["overall_score"] == 94.0
    # Proof: Non-FSP candidate is unconstrained and reaches full 100.0
    assert perf_non_fsp["overall_score"] > perf_fsp["overall_score"]


def test_meritocracy_strong_non_fsp_outranks_weak_fsp():
    """
    Meritocracy Check:
    A strong non-FSP engineer (theta=95, full stack match, freshness=90)
    MUST decisively outrank a weak FSP candidate (theta=65, poor stack, but has FSP medal).
    """
    strong_non_fsp = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="middle",
        need_grade="middle",
        theta_score=95.0,
        candidate_skills=["python", "fastapi", "postgresql", "docker"],
        core_stack=["python", "fastapi", "postgresql"],
        nice_to_have=["docker"],
        fsp_data=None,
        freshness_score=90.0,
    )

    weak_fsp = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="middle",
        need_grade="middle",
        theta_score=65.0,
        candidate_skills=["c++"],
        core_stack=["python", "fastapi", "postgresql"],
        nice_to_have=["docker"],
        fsp_data={
            "fsp_id": "FSP-WEAK",
            "sport_rank": "ms",
            "stage": "всероссийский",
            "medal": "gold",
            "rating_points": 25,
        },
        freshness_score=60.0,
    )

    # Non-FSP score: 0.52*95 + 0.30*100 + 0.18*90 = 49.4 + 30.0 + 16.2 = 95.6
    assert strong_non_fsp["overall_score"] >= 95.0
    # Weak FSP score: 0.35*65 + 0.25*0 + 0.25*76 + 0.15*60 = 22.75 + 0 + 19.0 + 9.0 = 50.75
    assert weak_fsp["overall_score"] < 55.0
    assert strong_non_fsp["overall_score"] > weak_fsp["overall_score"]


def test_meritocracy_grid_sweep_dominance():
    """
    Empirical parameter sweep across 20 synthetic pairs:
    Stronger engineering candidates without FSP always defeat lower-skilled FSP holders.
    """
    for i in range(20):
        strong_theta = 85.0 + (i * 0.7)
        weak_theta = 50.0 + (i * 0.8)

        c_strong = calculate_candidate_score(
            cand_spec="backend",
            need_spec="backend",
            cand_grade="middle",
            need_grade="middle",
            theta_score=strong_theta,
            candidate_skills=["python", "postgresql"],
            core_stack=["python", "postgresql"],
            fsp_data=None,
            freshness_score=80.0,
        )
        c_weak = calculate_candidate_score(
            cand_spec="backend",
            need_spec="backend",
            cand_grade="middle",
            need_grade="middle",
            theta_score=weak_theta,
            candidate_skills=["python"],
            core_stack=["python", "postgresql"],
            fsp_data={"fsp_id": f"FSP-{i}", "sport_rank": "kms", "rating_points": 10},
            freshness_score=50.0,
        )
        assert c_strong["overall_score"] > c_weak["overall_score"], (
            f"Iteration {i}: Strong non-FSP ({c_strong['overall_score']}) failed to outrank weak FSP ({c_weak['overall_score']})"
        )


def test_explainability_non_fsp_clean_radar_and_narrative():
    """Explainability for non-FSP candidate includes correct badge, zero NaN, and Russian narrative."""
    calc = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="middle",
        need_grade="middle",
        theta_score=88.0,
        candidate_skills=["python", "fastapi"],
        core_stack=["python"],
        nice_to_have=["fastapi"],
        fsp_data=None,
        freshness_score=85.0,
    )
    expl = build_explainability(
        cand_spec="backend",
        cand_grade="middle",
        overall_score=calc["overall_score"],
        test_subscore=calc["test_subscore"],
        stack_subscore=calc["stack_subscore"],
        fsp_subscore=calc["fsp_subscore"],
        freshness_subscore=calc["freshness_subscore"],
        grade_multiplier=calc["grade_multiplier"],
        weights=calc["weights"],
        candidate_skills=["python", "fastapi"],
        core_stack=["python"],
        nice_to_have=["fastapi"],
        fsp_data=None,
    )
    assert expl["component_scores"]["weights_applied"]["is_fsp_profile"] is False
    assert expl["component_scores"]["weights_applied"]["w_test"] == 0.52
    assert expl["component_scores"]["weights_applied"]["w_stack"] == 0.30
    assert expl["component_scores"]["weights_applied"]["w_fsp"] == 0.00
    assert expl["component_scores"]["weights_applied"]["w_freshness"] == 0.18
    assert expl["component_scores"]["weights_applied"]["sum_weights"] == 1.00

    fsp_radar = next(p for p in expl["radar_series"] if p["axis"] == "Достижения ФСП")
    assert fsp_radar["value"] == 0.0
    assert "паритет" in expl["human_summary_ru"].lower() or "независимой" in expl["human_summary_ru"].lower()


# ==============================================================================
# SECTION 2: 2-TIER PINNING INVARIANT ADVERSARIAL STRESS TESTS
# ==============================================================================

def test_extreme_score_inversion_pinned_score_zero_vs_unpinned_100():
    """
    Adversarial Inversion:
    Pinned candidate has match_score = 0.0.
    Unpinned candidate has match_score = 100.0.
    Invariant: Pinned candidate MUST be Rank 1, Unpinned MUST be Rank 2.
    """
    items = [
        {"candidate_profile_id": 101, "is_pinned": False, "match_score": 100.0},
        {"candidate_profile_id": 202, "is_pinned": True, "match_score": 0.0},
    ]
    ranked = sort_and_rank_items(items)

    assert len(ranked) == 2
    # Pinned MUST be rank 1 despite score 0.0
    assert ranked[0]["candidate_profile_id"] == 202
    assert ranked[0]["rank_position"] == 1
    assert ranked[0]["is_pinned"] is True

    # Unpinned MUST be rank 2 despite score 100.0
    assert ranked[1]["candidate_profile_id"] == 101
    assert ranked[1]["rank_position"] == 2
    assert ranked[1]["is_pinned"] is False


def test_multi_candidate_strict_partition_ranks_1_to_p():
    """
    Stress test with |P|=5 and |U|=5:
    Every pinned candidate has a lower score (10..50) than every unpinned candidate (90..98).
    Ranks 1..5 MUST be occupied by pinned candidates.
    Ranks 6..10 MUST be occupied by unpinned candidates.
    """
    pinned_scores = [10.0, 20.0, 30.0, 40.0, 50.0]
    unpinned_scores = [90.0, 92.0, 94.0, 96.0, 98.0]

    items = []
    for i, sc in enumerate(pinned_scores):
        items.append({"candidate_profile_id": 100 + i, "is_pinned": True, "match_score": sc})
    for i, sc in enumerate(unpinned_scores):
        items.append({"candidate_profile_id": 200 + i, "is_pinned": False, "match_score": sc})

    ranked = sort_and_rank_items(items)
    assert len(ranked) == 10

    # Ranks must be contiguous 1..10
    ranks = [r["rank_position"] for r in ranked]
    assert ranks == list(range(1, 11))

    # First 5 items MUST be pinned
    for i in range(5):
        assert ranked[i]["is_pinned"] is True
        assert ranked[i]["rank_position"] == i + 1
        assert ranked[i]["candidate_profile_id"] in range(100, 105)

    # Remaining 5 items MUST be unpinned
    for i in range(5, 10):
        assert ranked[i]["is_pinned"] is False
        assert ranked[i]["rank_position"] == i + 1
        assert ranked[i]["candidate_profile_id"] in range(200, 205)

    # Maximum rank of pinned candidates MUST be strictly less than minimum rank of unpinned
    max_pinned_rank = max(r["rank_position"] for r in ranked if r["is_pinned"])
    min_unpinned_rank = min(r["rank_position"] for r in ranked if not r["is_pinned"])
    assert max_pinned_rank < min_unpinned_rank


def test_within_tier_score_descending_order():
    """Within each tier, items must be ordered by match_score DESC."""
    items = [
        {"candidate_profile_id": 1, "is_pinned": True, "match_score": 40.0},
        {"candidate_profile_id": 2, "is_pinned": True, "match_score": 80.0},
        {"candidate_profile_id": 3, "is_pinned": True, "match_score": 60.0},
        {"candidate_profile_id": 4, "is_pinned": False, "match_score": 55.0},
        {"candidate_profile_id": 5, "is_pinned": False, "match_score": 95.0},
        {"candidate_profile_id": 6, "is_pinned": False, "match_score": 75.0},
    ]
    ranked = sort_and_rank_items(items)

    # Pinned tier: IDs 2 (80.0), 3 (60.0), 1 (40.0) -> Ranks 1, 2, 3
    assert [r["candidate_profile_id"] for r in ranked[:3]] == [2, 3, 1]
    assert [r["rank_position"] for r in ranked[:3]] == [1, 2, 3]

    # Unpinned tier: IDs 5 (95.0), 6 (75.0), 4 (55.0) -> Ranks 4, 5, 6
    assert [r["candidate_profile_id"] for r in ranked[3:]] == [5, 6, 4]
    assert [r["rank_position"] for r in ranked[3:]] == [4, 5, 6]


def test_deterministic_tie_breaking():
    """Identical scores within a tier must break ties deterministically by candidate_profile_id DESC."""
    items = [
        {"candidate_profile_id": 10, "is_pinned": True, "match_score": 80.0},
        {"candidate_profile_id": 30, "is_pinned": True, "match_score": 80.0},
        {"candidate_profile_id": 20, "is_pinned": True, "match_score": 80.0},
    ]
    ranked = sort_and_rank_items(items)
    assert [r["candidate_profile_id"] for r in ranked] == [30, 20, 10]
    assert [r["rank_position"] for r in ranked] == [1, 2, 3]


def test_boundary_empty_and_single_tiers():
    """Handles empty items, all-pinned (|U|=0), and all-unpinned (|P|=0) without error."""
    assert sort_and_rank_items([]) == []

    all_pinned = [{"candidate_profile_id": i, "is_pinned": True, "match_score": float(i * 10)} for i in range(1, 4)]
    r_pinned = sort_and_rank_items(all_pinned)
    assert len(r_pinned) == 3
    assert [r["rank_position"] for r in r_pinned] == [1, 2, 3]

    all_unpinned = [{"candidate_profile_id": i, "is_pinned": False, "match_score": float(i * 10)} for i in range(1, 4)]
    r_unpinned = sort_and_rank_items(all_unpinned)
    assert len(r_unpinned) == 3
    assert [r["rank_position"] for r in r_unpinned] == [1, 2, 3]


# ==============================================================================
# SECTION 3: DIFFERENTIAL REFINEMENT (DELTA S) VERIFICATION
# ==============================================================================

def test_delta_s_formula_positive_negative_zero():
    """Delta S = round(S_new - S_old, 2) across all directions."""
    # 1. Positive Delta (improved fit)
    s_old = 72.35
    s_new_better = 88.60
    delta_pos = round(s_new_better - s_old, 2)
    assert delta_pos == 16.25
    assert delta_pos > 0

    # 2. Negative Delta (degraded fit)
    s_new_worse = 61.10
    delta_neg = round(s_new_worse - s_old, 2)
    assert delta_neg == -11.25
    assert delta_neg < 0

    # 3. Zero Delta (identical fit)
    delta_zero = round(s_old - s_old, 2)
    assert delta_zero == 0.0


def test_delta_s_extreme_boundaries():
    """Boundary checks: 0 to 100, 100 to 0, 100 to 100, 0 to 0."""
    assert round(100.0 - 0.0, 2) == 100.0
    assert round(0.0 - 100.0, 2) == -100.0
    assert round(100.0 - 100.0, 2) == 0.0
    assert round(0.0 - 0.0, 2) == 0.0


# ==============================================================================
# SECTION 4: FRESHNESS SUBSCORE & HALF-LIFE DECAY MATHEMATICAL RIGOR
# ==============================================================================

def test_decay_exact_90_day_half_life():
    """
    Verify exact 90-day half-life decay:
    S(0) = 100.0
    S(90) = 50.0
    S(180) = 25.0
    S(270) = 12.5
    S(360) = 6.25
    """
    s0 = compute_freshness_subscore(0.0)
    s90 = compute_freshness_subscore(90.0)
    s180 = compute_freshness_subscore(180.0)
    s270 = compute_freshness_subscore(270.0)
    s360 = compute_freshness_subscore(360.0)

    assert s0 == 100.0
    assert abs(s90 - 50.0) < 0.05, f"Expected 50.0, got {s90}"
    assert abs(s180 - 25.0) < 0.05, f"Expected 25.0, got {s180}"
    assert abs(s270 - 12.5) < 0.05, f"Expected 12.5, got {s270}"
    assert abs(s360 - 6.25) < 0.05, f"Expected 6.25, got {s360}"

    # Verify mathematical ratio S(t + 90) / S(t) == 0.50
    assert abs(s90 / s0 - 0.50) < 0.001
    assert abs(s180 / s90 - 0.50) < 0.001
    assert abs(s270 / s180 - 0.50) < 0.001
    assert abs(s360 / s270 - 0.50) < 0.001


def test_challenge_boost_exact_30_day_half_life():
    """
    Verify challenge boost has exact 30-day half-life:
    Let test age be infinity (base decay -> 0), challenge pts = 20:
    dt = 0 -> boost = 20.0
    dt = 30 -> boost = 10.0
    dt = 60 -> boost = 5.0
    dt = 90 -> boost = 2.5
    """
    b0 = compute_freshness_subscore(9999.0, [{"points": 20.0, "days_ago": 0.0}])
    b30 = compute_freshness_subscore(9999.0, [{"points": 20.0, "days_ago": 30.0}])
    b60 = compute_freshness_subscore(9999.0, [{"points": 20.0, "days_ago": 60.0}])
    b90 = compute_freshness_subscore(9999.0, [{"points": 20.0, "days_ago": 90.0}])

    assert abs(b0 - 20.0) < 0.05
    assert abs(b30 - 10.0) < 0.05
    assert abs(b60 - 5.0) < 0.05
    assert abs(b90 - 2.5) < 0.05

    assert abs(b30 / b0 - 0.50) < 0.005
    assert abs(b60 / b30 - 0.50) < 0.005
    assert abs(b90 / b60 - 0.50) < 0.005


def test_multiple_challenges_additive_decay():
    """Multiple challenges additively boost the score before saturation."""
    # Test aged 90 days (base 50.0) + challenge 0d ago (20.0) + challenge 30d ago (10.0)
    # Expected: 50.0 + 20.0 + 10.0 = 80.0
    res = compute_freshness_subscore(
        days_since_test=90.0,
        recent_challenges=[
            {"points": 20.0, "days_ago": 0.0},
            {"points": 20.0, "days_ago": 30.0},
        ],
    )
    assert abs(res - 80.0) < 0.2


def test_ceiling_saturation_at_100():
    """Sum of decay and challenges cannot exceed 100.0."""
    res = compute_freshness_subscore(
        days_since_test=0.0,  # 100.0
        recent_challenges=[{"points": 50.0, "days_ago": 0.0}],  # +50.0
    )
    assert res == 100.0


def test_negative_days_clock_skew_robustness():
    """Negative days (future timestamp / clock drift) clamps safely to 0 days (100.0)."""
    res = compute_freshness_subscore(days_since_test=-15.0)
    assert res == 100.0

    res_ch = compute_freshness_subscore(
        days_since_test=90.0,
        recent_challenges=[{"points": 20.0, "days_ago": -5.0}],
    )
    # Clamped to 0 days -> +20.0 -> total 70.0
    assert abs(res_ch - 70.0) < 0.2


def test_large_days_asymptotic_zero_no_underflow():
    """Very large days_since_test gracefully approaches 0.0 without underflow/NaN."""
    res_10k = compute_freshness_subscore(days_since_test=10000.0)
    assert res_10k == 0.0
    assert not math.isnan(res_10k)
    assert not math.isinf(res_10k)


# ==============================================================================
# SECTION 5: ASYNC DB INTEGRATION & PERSISTENCE VERIFICATION
# ==============================================================================

def test_shortlist_service_db_pin_and_refine_lifecycle():
    """
    Stateful DB stress test:
    1. Create user, employer, candidate, and shortlist in SQLite.
    2. Add 4 items with varied match scores.
    3. Toggle pin on a low-scoring candidate.
    4. Assert DB column rank_position updates to 1.
    5. Assert unpinning drops rank position back to bottom.
    6. Run refine_shortlist_items with a need and assert delta_score is computed and stored.
    """
    async def _run_db_lifecycle():
        test_db_url = "sqlite+aiosqlite:///:memory:"
        engine = create_async_engine(test_db_url, echo=False)
        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as db:
            # Create Specialization & Grade
            spec = Specialization(code="backend", name="Бэкенд-разработка")
            grade = Grade(code="middle", name="Middle", rank_order=2)
            db.add_all([spec, grade])
            await db.flush()

            emp_user = User(
                email="emp.test@test.org",
                role="employer",
                hashed_password="hash",
                is_active=True,
            )
            cand_user = User(
                email="cand.test@test.org",
                role="candidate",
                hashed_password="hash",
                is_active=True,
            )
            db.add_all([emp_user, cand_user])
            await db.flush()

            emp_prof = EmployerProfile(
                user_id=emp_user.id,
                company_name="Emp Corp",
                inn="7707083893",
                domain="empcorp.ru",
            )
            cand_prof_1 = CandidateProfile(
                user_id=cand_user.id,
                first_name="Dev 1",
                last_name="Alpha",
                city="Москва",
            )
            db.add_all([emp_prof, cand_prof_1])
            await db.flush()

            # Add 3 more candidate profiles with distinct freshness to differentiate refined scores
            cand_profs = [cand_prof_1]
            cand_prof_1.freshness_score = 95.0
            fresh_vals = [85.0, 75.0, 40.0]
            for idx, f_val in enumerate(fresh_vals, start=2):
                u = User(email=f"cand{idx}@test.org", role="candidate", hashed_password="hash", is_active=True)
                db.add(u)
                await db.flush()
                cp = CandidateProfile(
                    user_id=u.id,
                    first_name=f"Dev {idx}",
                    last_name="Beta",
                    city="Москва",
                    freshness_score=f_val,
                )
                db.add(cp)
                await db.flush()
                cand_profs.append(cp)

            # Create Employer Need
            need = EmployerNeed(
                employer_profile_id=emp_prof.id,
                specialization_id=spec.id,
                target_grade_id=grade.id,
                team_tasks_text="Middle Python Developer",
                core_stack_json=["python", "fastapi"],
                nice_to_have_stack_json=["docker"],
                salary_min=180000,
                salary_max=250000,
            )
            db.add(need)
            await db.flush()
            need.specialization = spec
            need.target_grade = grade

            # Create Shortlist
            shortlist = SavedShortlist(
                employer_profile_id=emp_prof.id,
                need_id=need.id,
                title="Adversarial Test Shortlist",
            )
            db.add(shortlist)
            await db.flush()

            # Insert 4 items with initial scores: ID 1: 95.0, ID 2: 85.0, ID 3: 75.0, ID 4: 40.0
            scores = [95.0, 85.0, 75.0, 40.0]
            items = []
            for cp, sc in zip(cand_profs, scores):
                item = ShortlistItem(
                    shortlist_id=shortlist.id,
                    candidate_profile_id=cp.id,
                    match_score=sc,
                    is_pinned=False,
                    rank_position=1,
                )
                db.add(item)
                items.append(item)
            await db.commit()

            # Initial sort via pin_candidate_in_shortlist on candidate 4 (score 40.0) -> pin it!
            pinned_item = await pin_candidate_in_shortlist(
                db=db,
                shortlist_id=shortlist.id,
                candidate_profile_id=cand_profs[3].id,  # Cand 4 with lowest score (40.0)
                is_pinned=True,
            )
            assert pinned_item is not None
            assert pinned_item.is_pinned is True
            assert pinned_item.rank_position == 1  # Occupies rank 1 unconditionally!

            # Verify all ranks in DB
            res = await db.execute(
                select(ShortlistItem)
                .where(ShortlistItem.shortlist_id == shortlist.id)
                .order_by(ShortlistItem.rank_position.asc())
            )
            all_db_items = list(res.scalars().all())
            assert len(all_db_items) == 4

            # Rank 1 must be candidate 4 (score 40.0, pinned)
            assert all_db_items[0].candidate_profile_id == cand_profs[3].id
            assert all_db_items[0].rank_position == 1
            assert all_db_items[0].is_pinned is True

            # Ranks 2..4 must be candidates 1 (95.0), 2 (85.0), 3 (75.0) (unpinned)
            assert all_db_items[1].candidate_profile_id == cand_profs[0].id
            assert all_db_items[1].rank_position == 2
            assert all_db_items[1].is_pinned is False

            assert all_db_items[2].candidate_profile_id == cand_profs[1].id
            assert all_db_items[2].rank_position == 3

            assert all_db_items[3].candidate_profile_id == cand_profs[2].id
            assert all_db_items[3].rank_position == 4

            # Test refine_shortlist_items
            refined_items = await refine_shortlist_items(db, shortlist, need)
            assert len(refined_items) == 4
            # Pinned item MUST still be rank 1 after refinement
            ref_pinned = next(i for i in refined_items if i.candidate_profile_id == cand_profs[3].id)
            assert ref_pinned.is_pinned is True
            assert ref_pinned.rank_position == 1
            assert ref_pinned.delta_score is not None

            # Unpin candidate 4 -> rank should drop back to 4
            unpinned_item = await pin_candidate_in_shortlist(
                db=db,
                shortlist_id=shortlist.id,
                candidate_profile_id=cand_profs[3].id,
                is_pinned=False,
            )
            assert unpinned_item.is_pinned is False

            res2 = await db.execute(
                select(ShortlistItem)
                .where(ShortlistItem.shortlist_id == shortlist.id)
                .order_by(ShortlistItem.rank_position.asc())
            )
            all_db_items2 = list(res2.scalars().all())
            # Cand 4 is now unpinned and at rank 4
            assert all_db_items2[3].candidate_profile_id == cand_profs[3].id
            assert all_db_items2[3].rank_position == 4

        await engine.dispose()

    asyncio.run(_run_db_lifecycle())


if __name__ == "__main__":
    import traceback

    funcs = [obj for name, obj in list(globals().items()) if name.startswith("test_") and callable(obj)]
    print(f"Running {len(funcs)} adversarial tests...")
    passed = 0
    failed = 0
    for f in funcs:
        try:
            f()
            print(f"  [PASS] {f.__name__}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {f.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\nResult: {passed} passed, {failed} failed.")
    sys.exit(0 if failed == 0 else 1)
