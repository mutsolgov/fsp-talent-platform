"""
FSP IT-Talent Platform — Multi-Factor Ranking Engine.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §3.2-3.4 and SPEC.md.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Canonical grade code to rank order (1..4)
GRADE_RANK_MAP: Dict[str, int] = {
    "junior": 1,
    "middle": 2,
    "senior": 3,
    "lead": 4,
}

# Dynamic weights
WEIGHTS_WITH_FSP = (0.35, 0.25, 0.25, 0.15)       # w_test, w_stack, w_fsp, w_freshness
WEIGHTS_WITHOUT_FSP = (0.52, 0.30, 0.00, 0.18)    # Sum = 1.00 (Zero non-FSP penalty)


def calculate_grade_multiplier(
    candidate_grade: int | str,
    target_grade: int | str,
) -> float:
    """
    Computes grade multiplier based on difference Delta Grade = Cand.rank - Need.rank.
    mult(0) = 1.00, mult(1) = 0.93, mult(-1) = 0.85, mult(2) = 0.60, mult(-2) = 0.45, else = 0.25
    """
    cand_rank = (
        GRADE_RANK_MAP.get(candidate_grade.lower().strip(), 2)
        if isinstance(candidate_grade, str)
        else int(candidate_grade)
    )
    target_rank = (
        GRADE_RANK_MAP.get(target_grade.lower().strip(), 2)
        if isinstance(target_grade, str)
        else int(target_grade)
    )
    diff = cand_rank - target_rank

    if diff == 0:
        return 1.00
    elif diff == 1:
        return 0.93
    elif diff == -1:
        return 0.85
    elif diff == 2:
        return 0.60
    elif diff == -2:
        return 0.45
    else:
        return 0.25


def calculate_stack_subscore(
    candidate_skills: Iterable[str],
    core_stack: Iterable[str],
    nice_to_have: Optional[Iterable[str]] = None,
) -> float:
    """
    Computes S_stack in [0.0, 100.0] as weighted Jaccard overlap:
    S_stack = 100.0 * (0.75 * J_core + 0.25 * J_nice)
    where J = |C & R| / |R| if |R| > 0 else 1.0.
    """
    c_set: Set[str] = {s.lower().strip() for s in candidate_skills if s}
    core_set: Set[str] = {s.lower().strip() for s in core_stack if s}
    nice_set: Set[str] = {s.lower().strip() for s in (nice_to_have or []) if s}

    if not core_set and not nice_set:
        return 100.0

    if not nice_set:
        j_core = len(c_set & core_set) / len(core_set) if core_set else 0.0
        score = 100.0 * j_core
    elif not core_set:
        j_nice = len(c_set & nice_set) / len(nice_set) if nice_set else 0.0
        score = 100.0 * j_nice
    else:
        j_core = len(c_set & core_set) / len(core_set)
        j_nice = len(c_set & nice_set) / len(nice_set)
        score = 100.0 * (0.75 * j_core + 0.25 * j_nice)

    return min(100.0, max(0.0, round(score, 2)))


def calculate_fsp_subscore(fsp_data: Optional[Dict[str, Any]] = None) -> float:
    """
    Computes S_fsp in [0.0, 100.0] for candidates with verified fsp_id:
    S_fsp = min(100.0, 0.35 * R_rank + 0.40 * M_medal + 0.25 * P_rating)
    Returns 0.0 if candidate has no FSP history.
    """
    if not fsp_data or not fsp_data.get("fsp_id"):
        return 0.0

    rank_weights = {
        "ms": 100.0,
        "kms": 70.0,
        "first_class": 40.0,
        "none": 0.0,
        None: 0.0,
    }
    r_rank = rank_weights.get(fsp_data.get("sport_rank"), 0.0)

    stage_mult = {
        "всероссийский": 1.0,
        "окружной": 0.8,
        "региональный": 0.6,
        None: 0.6,
    }
    stage_key = fsp_data.get("stage")
    stage_multiplier = stage_mult.get(
        str(stage_key).lower().strip() if stage_key else None,
        0.6,
    )

    medal_map = {
        "gold": 40.0,
        "silver": 30.0,
        "bronze": 20.0,
        "participant": 10.0,
        None: 5.0 if fsp_data.get("medal") is not None else 0.0,
    }
    medal_key = fsp_data.get("medal")
    m_medal = medal_map.get(
        str(medal_key).lower().strip() if medal_key else None,
        0.0,
    ) * stage_multiplier

    rating_pts = float(fsp_data.get("rating_points", 0) or 0)
    p_rating = min(100.0, (rating_pts / 25.0) * 100.0)

    score = 0.35 * r_rank + 0.40 * m_medal + 0.25 * p_rating
    return min(100.0, max(0.0, round(score, 2)))


def calculate_weights(has_fsp: bool) -> Tuple[float, float, float, float]:
    """Returns (w_test, w_stack, w_fsp, w_freshness)."""
    return WEIGHTS_WITH_FSP if has_fsp else WEIGHTS_WITHOUT_FSP


def calculate_candidate_score(
    cand_spec: str,
    need_spec: str,
    cand_grade: int | str,
    need_grade: int | str,
    theta_score: float,
    candidate_skills: Iterable[str],
    core_stack: Iterable[str],
    nice_to_have: Optional[Iterable[str]] = None,
    fsp_data: Optional[Dict[str, Any]] = None,
    freshness_score: float = 50.0,
) -> Dict[str, Any]:
    """
    Computes overall score S and subscores for candidate matching against an employer need.
    If specialization does not match, overall score S = 0.0.
    """
    cand_spec_norm = str(cand_spec).lower().strip()
    need_spec_norm = str(need_spec).lower().strip()

    if cand_spec_norm != need_spec_norm:
        return {
            "overall_score": 0.0,
            "test_subscore": 0.0,
            "stack_subscore": 0.0,
            "fsp_subscore": 0.0,
            "freshness_subscore": 0.0,
            "grade_multiplier": 0.0,
            "has_fsp": False,
            "weights": WEIGHTS_WITHOUT_FSP,
            "specialization_match": False,
        }

    mult = calculate_grade_multiplier(cand_grade, need_grade)
    test_sub = min(100.0, max(0.0, round(float(theta_score) * mult, 2)))
    stack_sub = calculate_stack_subscore(candidate_skills, core_stack, nice_to_have)
    fsp_sub = calculate_fsp_subscore(fsp_data)
    fresh_sub = min(100.0, max(0.0, round(float(freshness_score), 2)))

    has_fsp = bool(fsp_data and fsp_data.get("fsp_id"))
    weights = calculate_weights(has_fsp)
    w_test, w_stack, w_fsp, w_fresh = weights

    overall = w_test * test_sub + w_stack * stack_sub + w_fsp * fsp_sub + w_fresh * fresh_sub
    overall = min(100.0, max(0.0, round(overall, 2)))

    return {
        "overall_score": overall,
        "test_subscore": test_sub,
        "stack_subscore": stack_sub,
        "fsp_subscore": fsp_sub,
        "freshness_subscore": fresh_sub,
        "grade_multiplier": mult,
        "has_fsp": has_fsp,
        "weights": weights,
        "specialization_match": True,
    }


def compute_freshness_subscore(
    days_since_test: float,
    recent_challenges: Optional[List[Dict[str, Any]]] = None,
) -> float:
    """
    Computes S_freshness in [0.0, 100.0] with 90-day half-life decay and 30-day challenge boost.
    Formula per docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §3.4.4:
    S_freshness = min(100.0, S_decay + B_challenges)
    where S_decay = 100.0 * exp(-lambda * dt_test), lambda = ln(2)/90
    and B_challenges = sum(points_k * exp(-mu * dt_k)), mu = ln(2)/30.
    """
    decay_lambda = math.log(2) / 90.0
    base_decay = 100.0 * math.exp(-decay_lambda * max(0.0, float(days_since_test)))

    bonus = 0.0
    if recent_challenges:
        bonus_mu = math.log(2) / 30.0
        for ch in recent_challenges:
            pts = float(ch.get("points", 20.0))
            dt = float(ch.get("days_ago", 0.0))
            bonus += pts * math.exp(-bonus_mu * max(0.0, dt))

    return min(100.0, max(0.0, round(base_decay + bonus, 2)))


calculate_freshness_subscore = compute_freshness_subscore


def aggregate_candidate_fsp_data(
    fsp_id: Optional[str],
    achievements: Optional[Iterable[Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Aggregates candidate's real FSP achievements into a single representative profile dict:
    - Highest sport rank (ms > kms > first_class > none)
    - Best medal with tournament stage (medal_weight * stage_multiplier)
    - Total rating points across all tournaments
    Returns None if candidate has no fsp_id.
    """
    if not fsp_id:
        return None

    ach_list = list(achievements or [])
    if not ach_list:
        return {
            "fsp_id": fsp_id,
            "sport_rank": None,
            "stage": "региональный",
            "medal": None,
            "rating_points": 0,
        }

    # Rank priority: ms (100) > kms (70) > first_class (40) > none (0)
    rank_order = {"ms": 3, "kms": 2, "first_class": 1, "none": 0, None: 0}
    best_rank = None
    best_rank_priority = -1
    for a in ach_list:
        r = getattr(a, "sport_rank", None) or (a.get("sport_rank") if isinstance(a, dict) else None)
        r_norm = str(r).lower().strip() if r else None
        prio = rank_order.get(r_norm, 0)
        if prio > best_rank_priority:
            best_rank_priority = prio
            best_rank = r_norm

    # Medal with stage multiplier
    stage_mult = {"всероссийский": 1.0, "окружной": 0.8, "региональный": 0.6}
    medal_map = {"gold": 40.0, "silver": 30.0, "bronze": 20.0, "participant": 10.0}

    best_medal = None
    best_stage = "региональный"
    best_medal_effective = -1.0
    for a in ach_list:
        m = getattr(a, "medal", None) or (a.get("medal") if isinstance(a, dict) else None)
        st = getattr(a, "stage", None) or (a.get("stage") if isinstance(a, dict) else None)
        m_norm = str(m).lower().strip() if m else None
        st_norm = str(st).lower().strip() if st else "региональный"
        m_pts = medal_map.get(m_norm, 0.0)
        st_m = stage_mult.get(st_norm, 0.6)
        eff = m_pts * st_m
        if eff > best_medal_effective:
            best_medal_effective = eff
            best_medal = m_norm
            best_stage = st_norm

    total_rating = sum(
        int(getattr(a, "rating_points", 0) or 0) if not isinstance(a, dict) else int(a.get("rating_points", 0) or 0)
        for a in ach_list
    )

    return {
        "fsp_id": fsp_id,
        "sport_rank": best_rank,
        "stage": best_stage,
        "medal": best_medal,
        "rating_points": total_rating,
    }
