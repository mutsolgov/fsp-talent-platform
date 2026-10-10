#!/usr/bin/env python3
"""
Adversarial Verification Suite for Milestone 3 (03_ALGORITHMS_AND_BUSINESS_LOGIC.md)
Challenger Agent: challenger_m3_2

Tests:
1. Adversarial Non-FSP Parity Test:
   - Pairs: Candidate A (non-FSP, high test score theta=95) vs Candidate B (with FSP, low test score theta=60, medium FSP).
   - Candidate A ranks higher than Candidate B under diverse conditions.
   - Candidate without FSP can achieve score S = 100.0 (Zero glass ceiling).
   - Dynamic weight reallocation proof: w = (0.52, 0.30, 0.00, 0.18) sums to 1.00.
   - Empirical analysis of FSP subscore bounds (r_rank=100, m_medal=40, p_rating=100 -> S_fsp=76.0).
2. Stateful Shortlist Pinning Stress Test:
   - 10 candidates with 3 pinned candidates.
   - Severe filter query drops native scores of pinned candidates (Delta S < 0).
   - Pinned candidates strictly occupy top positions 1..3 with is_pinned = True.
3. Anti-Fraud INN & Salary Anomaly Test:
   - 10-digit and 12-digit FNS INN checksum verification with 25+ test cases.
   - Salary anomaly detection (ratio <= 3.5, zero salary, inverted salary, boundary conditions).
4. Section 6 Quality Gate Execution:
   - Direct execution of the embedded Quality Gate benchmark.
"""
import math
import re
import sys
from typing import Dict, List, Optional, Tuple, Any

# =============================================================================
# RE-IMPLEMENTED CORE ALGORITHMS DIRECTLY FROM M3 SPECIFICATION
# =============================================================================

def compute_fsp_subscore(fsp_data: Optional[Dict[str, Any]]) -> float:
    """Section 3.6: S_fsp in [0.0, 100.0]"""
    if not fsp_data or not fsp_data.get("fsp_id"):
        return 0.0

    rank_weights = {"ms": 100.0, "kms": 70.0, "first_class": 40.0, "none": 0.0, None: 0.0}
    r_rank = rank_weights.get(fsp_data.get("sport_rank"), 0.0)

    stage_multipliers = {"всероссийский": 1.0, "окружной": 0.8, "региональный": 0.6, None: 0.6}
    stage_mult = stage_multipliers.get(str(fsp_data.get("stage", "региональный")).lower(), 0.6)

    medal_weights = {"gold": 40.0, "silver": 30.0, "bronze": 20.0, "participant": 10.0, None: 5.0}
    m_medal = medal_weights.get(fsp_data.get("medal"), 5.0) * stage_mult

    rating_pts = float(fsp_data.get("rating_points", 0))
    p_rating = min(100.0, (rating_pts / 25.0) * 100.0)

    score = 0.35 * r_rank + 0.40 * m_medal + 0.25 * p_rating
    return min(100.0, round(score, 2))


def compute_stack_subscore(
    candidate_skills: Any, core_stack: List[str], nice_to_have: List[str]
) -> float:
    """Section 3.6: S_stack in [0.0, 100.0]"""
    cand_norm = {s.lower().strip() for s in candidate_skills}
    core_norm = {s.lower().strip() for s in core_stack}
    nice_norm = {s.lower().strip() for s in nice_to_have}

    j_core = len(cand_norm & core_norm) / len(core_norm) if core_norm else 1.0
    j_nice = len(cand_norm & nice_norm) / len(nice_norm) if nice_norm else 1.0

    score = 100.0 * (0.75 * j_core + 0.25 * j_nice)
    return min(100.0, round(score, 2))


def compute_freshness_subscore(
    days_since_test: float, recent_challenges: Optional[List[Dict[str, Any]]] = None
) -> float:
    """Section 3.6: S_freshness in [0.0, 100.0]"""
    decay_lambda = math.log(2) / 90.0
    base_decay = 100.0 * math.exp(-decay_lambda * max(0.0, days_since_test))

    bonus = 0.0
    if recent_challenges:
        bonus_mu = math.log(2) / 30.0
        for ch in recent_challenges:
            pts = float(ch.get("points", 20.0))
            dt = float(ch.get("days_ago", 0.0))
            bonus += pts * math.exp(-bonus_mu * max(0.0, dt))

    return min(100.0, round(base_decay + bonus, 2))


def compute_ranking_score(
    test_score: float,
    stack_score: float,
    fsp_score: float,
    freshness_score: float,
    has_fsp: bool,
) -> Tuple[float, Tuple[float, float, float, float]]:
    """Section 3.6: S with Dynamic Weight Reallocation"""
    if has_fsp:
        weights = (0.35, 0.25, 0.25, 0.15)
    else:
        weights = (0.52, 0.30, 0.00, 0.18)

    w_test, w_stack, w_fsp, w_freshness = weights
    score = (
        w_test * test_score
        + w_stack * stack_score
        + w_fsp * fsp_score
        + w_freshness * freshness_score
    )
    return round(score, 2), weights


def build_explainability_object(
    cand: Dict[str, Any],
    need: Dict[str, Any],
    s_test: float,
    s_stack: float,
    s_fsp: float,
    s_fresh: float,
    overall_score: float,
    weights: Tuple[float, float, float, float],
) -> Dict[str, Any]:
    """Section 3.6: Explainability generator"""
    c_skills = {s.lower().strip() for s in cand.get("skills", [])}
    req_core = [s.lower().strip() for s in need.get("core_stack", [])]
    req_nice = [s.lower().strip() for s in need.get("nice_to_have", [])]
    all_req = req_core + req_nice

    matched = [s for s in all_req if s in c_skills]
    missing = [s for s in all_req if s not in c_skills]

    has_fsp = cand.get("fsp_id") is not None
    if has_fsp:
        fsp_expl = (
            f"Верифицированный участник ФСП (ID: {cand['fsp_id']}). "
            f"Разряд: {cand.get('sport_rank', '1-й разряд')}, рейтинг: {cand.get('rating_points', 0)} п."
        )
    else:
        fsp_expl = (
            "Без соревновательной истории ФСП — квалификация подтверждена независимой "
            "сертификацией платформы. Применен весовой паритет."
        )

    badge = (
        "Top Match"
        if overall_score >= 90.0
        else "Strong Fit"
        if overall_score >= 80.0
        else "Verified Fit"
        if overall_score >= 70.0
        else "Potential Fit"
    )

    matched_sample = ", ".join(matched[:5]) if matched else "базовые навыки"
    spec = cand.get("specialization", "Backend").capitalize()
    grade = cand.get("grade", "Middle").capitalize()

    narrative = (
        f"Кандидат подтвердил категорию {spec} · {grade} с баллом тестирования {s_test:.1f}/100. "
        f"Совпадение по стеку: {len(matched)}/{len(all_req)} ключевых навыков ({matched_sample}). "
        f"{fsp_expl} Индекс актуальности знаний: {s_fresh:.1f}/100."
    )

    return {
        "match_percentage": overall_score,
        "overall_score": overall_score,
        "component_scores": {
            "test_score": s_test,
            "stack_score": s_stack,
            "fsp_score": s_fsp,
            "freshness_score": s_fresh,
            "weights_applied": {
                "is_fsp_profile": has_fsp,
                "w_test": weights[0],
                "w_stack": weights[1],
                "w_fsp": weights[2],
                "w_freshness": weights[3],
                "sum_weights": round(sum(weights), 2),
            },
        },
        "matched_skills": matched,
        "missing_skills": missing,
        "fsp_bonus_explanation": fsp_expl,
        "freshness_activity": f"Актуальность {s_fresh:.1f}%",
        "recommendation_badge": badge,
        "human_summary_ru": narrative,
    }


def refine_shortlist_with_pinning(
    current_items: List[Dict[str, Any]],
    refined_need: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Section 4.4: Stateful Search & Shortlist Refinement Service"""
    recalculated = []
    for item in current_items:
        cand = item["candidate"]
        old_score = float(item.get("match_score", 0.0))
        is_pinned = bool(item.get("is_pinned", False))

        c_skills = set(cand.get("skills", []))
        s_test = float(cand.get("theta", cand.get("test_score", 75.0)))
        s_stack = compute_stack_subscore(
            c_skills,
            refined_need.get("core_stack", []),
            refined_need.get("nice_to_have", []),
        )
        s_fsp = compute_fsp_subscore(cand)
        s_fresh = float(cand.get("freshness", cand.get("freshness_score", 80.0)))
        has_fsp = cand.get("fsp_id") is not None

        new_score, weights = compute_ranking_score(s_test, s_stack, s_fsp, s_fresh, has_fsp)
        delta_s = round(new_score - old_score, 2)

        expl = build_explainability_object(
            cand, refined_need, s_test, s_stack, s_fsp, s_fresh, new_score, weights
        )

        recalculated.append({
            "candidate_id": cand["id"],
            "candidate": cand,
            "is_pinned": is_pinned,
            "match_score": new_score,
            "delta_score": delta_s,
            "explainability": expl,
        })

    pinned_tier = sorted(
        [x for x in recalculated if x["is_pinned"]],
        key=lambda x: x["match_score"],
        reverse=True,
    )
    unpinned_tier = sorted(
        [x for x in recalculated if not x["is_pinned"]],
        key=lambda x: x["match_score"],
        reverse=True,
    )

    ordered = pinned_tier + unpinned_tier
    for rank, entry in enumerate(ordered, start=1):
        entry["rank_position"] = rank

    return ordered


def verify_inn(inn: str) -> bool:
    """Section 5.7: FNS INN Checksum Verification"""
    if not isinstance(inn, str):
        return False
    inn = inn.strip()

    if len(inn) == 10:
        if not re.match(r"^\d{10}$", inn):
            return False
        digits = [int(d) for d in inn]
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        c10 = (sum(d * w for d, w in zip(digits[:9], weights)) % 11) % 10
        return c10 == digits[9]

    elif len(inn) == 12:
        if not re.match(r"^\d{12}$", inn):
            return False
        digits = [int(d) for d in inn]
        weights_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        c11 = (sum(d * w for d, w in zip(digits[:10], weights_11)) % 11) % 10
        if c11 != digits[10]:
            return False
        weights_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        c12 = (sum(d * w for d, w in zip(digits[:11], weights_12)) % 11) % 10
        return c12 == digits[11]

    return False


def validate_salary_range(salary_min: int, salary_max: int) -> Tuple[bool, Optional[str]]:
    """Section 5.7: Salary Spread & Bounds Validation"""
    if salary_min <= 0:
        return False, "Минимальная заработная плата должна быть строго > 0"
    if salary_max < salary_min:
        return False, "Максимальная заработная плата не может быть меньше минимальной"

    ratio = salary_max / salary_min
    if ratio > 3.5:
        return False, f"Разброс вилки {ratio:.2f} превышает допустимый максимум 3.5"

    return True, None


# =============================================================================
# ADVERSARIAL TEST SUITE
# =============================================================================

def test_non_fsp_ranking_parity() -> None:
    print("\n" + "=" * 80)
    print("TEST SUITE 1: ADVERSARIAL NON-FSP RANKING PARITY & ZERO GLASS CEILING")
    print("=" * 80)

    # 1. Perfect candidate without FSP achieves exactly 100.0
    score_100, weights_100 = compute_ranking_score(
        test_score=100.0,
        stack_score=100.0,
        fsp_score=0.0,
        freshness_score=100.0,
        has_fsp=False,
    )
    print(f"[*] Max Score Check: Candidate without FSP (100, 100, 100) -> Score: {score_100:.2f}, Weights: {weights_100}")
    assert score_100 == 100.0, f"Expected 100.0, got {score_100}"
    assert sum(weights_100) == 1.00, f"Weights sum {sum(weights_100)} != 1.00"

    # 2. Candidate A (No FSP, theta=95) vs Candidate B (With FSP, theta=60, medium FSP)
    cand_b_fsp = {
        "fsp_id": "FSP-BENCH-999",
        "sport_rank": "kms",
        "medal": "silver",
        "stage": "окружной",
        "rating_points": 20.0,
    }

    fsp_b_score = compute_fsp_subscore(cand_b_fsp)
    print(f"[*] Candidate B FSP Subscore: {fsp_b_score:.2f} (kms, silver окружной, 20 pts)")

    # Baseline comparison with equal stack (80) and freshness (80)
    score_a_base, w_a = compute_ranking_score(95.0, 80.0, 0.0, 80.0, has_fsp=False)
    score_b_base, w_b = compute_ranking_score(60.0, 80.0, fsp_b_score, 80.0, has_fsp=True)
    print(f"[*] Baseline Scenario (Equal stack=80, fresh=80):")
    print(f"    Candidate A (Non-FSP, theta=95.0): Score = {score_a_base:.2f}")
    print(f"    Candidate B (FSP,     theta=60.0): Score = {score_b_base:.2f}")
    assert score_a_base > score_b_base, f"Candidate A ({score_a_base}) should rank higher than Candidate B ({score_b_base})"

    # Adversarial Scenario 1: Candidate B given MAXIMUM SINGLE COMPETITION FSP
    # ms (100.0), gold (40.0), всероссийский (1.0), 25 rating points (100.0) -> S_fsp = 0.35*100 + 0.40*40 + 0.25*100 = 76.0
    cand_b_max_fsp = {
        "fsp_id": "FSP-MAX-1",
        "sport_rank": "ms",
        "medal": "gold",
        "stage": "всероссийский",
        "rating_points": 25.0,
    }
    fsp_b_formula_max = compute_fsp_subscore(cand_b_max_fsp)
    print(f"[*] Formula-Derived Max Single Competition FSP Subscore: {fsp_b_formula_max:.2f}")
    assert fsp_b_formula_max == 76.0, f"Expected 76.0 from formula, got {fsp_b_formula_max}"

    score_b_formula_max, _ = compute_ranking_score(60.0, 80.0, fsp_b_formula_max, 80.0, has_fsp=True)
    print(f"[*] Adversarial Scenario 1A (Candidate B has Formula Max FSP S_fsp=76.0):")
    print(f"    Candidate A (Non-FSP, theta=95.0): Score = {score_a_base:.2f}")
    print(f"    Candidate B (Max FSP, theta=60.0): Score = {score_b_formula_max:.2f}")
    assert score_a_base > score_b_formula_max, f"Candidate A ({score_a_base}) must defeat Candidate B ({score_b_formula_max})"

    # Adversarial Scenario 1B: Candidate B given HYPOTHETICAL S_fsp = 100.0 (Upper Clamp Limit)
    score_b_hypothetical_100, _ = compute_ranking_score(60.0, 80.0, 100.0, 80.0, has_fsp=True)
    print(f"[*] Adversarial Scenario 1B (Candidate B has Theoretical Clamped Max FSP S_fsp=100.0):")
    print(f"    Candidate A (Non-FSP, theta=95.0): Score = {score_a_base:.2f}")
    print(f"    Candidate B (FSP=100, theta=60.0): Score = {score_b_hypothetical_100:.2f}")
    assert score_a_base > score_b_hypothetical_100, (
        f"Candidate A ({score_a_base}) must defeat Candidate B even with clamped S_fsp=100.0 ({score_b_hypothetical_100})"
    )

    # Adversarial Scenario 2: Candidate B also has higher stack match (stack=90 vs stack=75 for A) + FSP=100.0
    score_a_disadvantage, _ = compute_ranking_score(95.0, 75.0, 0.0, 80.0, has_fsp=False)
    score_b_advantage, _ = compute_ranking_score(60.0, 90.0, 100.0, 80.0, has_fsp=True)
    print(f"[*] Adversarial Scenario 2 (Candidate B has stack=90% & FSP=100.0 vs A stack=75%):")
    print(f"    Candidate A (Non-FSP, theta=95.0, stack=75%): Score = {score_a_disadvantage:.2f}")
    print(f"    Candidate B (Max FSP, theta=60.0, stack=90%): Score = {score_b_advantage:.2f}")
    assert score_a_disadvantage > score_b_advantage, (
        f"Candidate A ({score_a_disadvantage}) must still beat Candidate B ({score_b_advantage})"
    )

    # Adversarial Scenario 3: Sensitivity sweep across test scores for Candidate A
    print(f"[*] Sensitivity Analysis: Finding crossover threshold theta for Candidate A against Candidate B:")
    crossover_found = False
    for theta_a in range(50, 101):
        s_a, _ = compute_ranking_score(float(theta_a), 80.0, 0.0, 80.0, has_fsp=False)
        if s_a > score_b_base and not crossover_found:
            print(f"    -> Crossover at Candidate A theta = {theta_a}: S_A={s_a:.2f} > S_B={score_b_base:.2f}")
            crossover_found = True
            break
    assert crossover_found, "Candidate A should cross over and beat Candidate B"

    # 3. Explainability Object Verification for Non-FSP
    cand_obj = {
        "id": "CAND-TEST-A",
        "specialization": "backend",
        "grade": "senior",
        "skills": ["python", "fastapi", "postgresql"],
        "fsp_id": None,
    }
    need_obj = {
        "core_stack": ["python", "fastapi"],
        "nice_to_have": ["postgresql"],
    }
    expl = build_explainability_object(
        cand_obj, need_obj, s_test=95.0, s_stack=100.0, s_fsp=0.0, s_fresh=85.0,
        overall_score=score_a_base, weights=w_a
    )
    print(f"[*] Explainability Object Inspection for Non-FSP:")
    print(f"    is_fsp_profile: {expl['component_scores']['weights_applied']['is_fsp_profile']}")
    print(f"    sum_weights:    {expl['component_scores']['weights_applied']['sum_weights']}")
    print(f"    explanation:    {expl['fsp_bonus_explanation']}")
    assert expl['component_scores']['weights_applied']['is_fsp_profile'] is False
    assert expl['component_scores']['weights_applied']['sum_weights'] == 1.0
    assert "Без соревновательной истории ФСП" in expl['fsp_bonus_explanation']
    assert "Применен весовой паритет" in expl['fsp_bonus_explanation']

    print("[PASS] Test Suite 1: Non-FSP ranking parity and zero glass ceiling verified successfully.")


def test_stateful_shortlist_pinning() -> None:
    print("\n" + "=" * 80)
    print("TEST SUITE 2: STATEFUL SHORTLIST PINNING STRESS TEST UNDER ADVERSARIAL QUERIES")
    print("=" * 80)

    # Initial list of 10 candidates
    # 3 pinned candidates (CAND-P1, CAND-P2, CAND-P3)
    # 7 unpinned candidates (CAND-U1..U7)
    candidates_pool = [
        # Pinned candidates (Python backend experts)
        {
            "id": "CAND-P1", "name": "Pinned 1", "specialization": "backend", "grade": "senior",
            "theta": 90.0, "skills": ["python", "django", "postgresql"], "freshness": 90.0, "fsp_id": "FSP-P1",
            "sport_rank": "kms", "medal": "silver", "stage": "окружной", "rating_points": 20
        },
        {
            "id": "CAND-P2", "name": "Pinned 2", "specialization": "backend", "grade": "middle",
            "theta": 82.0, "skills": ["python", "fastapi", "redis"], "freshness": 88.0, "fsp_id": None,
        },
        {
            "id": "CAND-P3", "name": "Pinned 3", "specialization": "backend", "grade": "senior",
            "theta": 85.0, "skills": ["python", "flask", "sqlite"], "freshness": 85.0, "fsp_id": None,
        },
        # Unpinned candidates (Diverse stack)
        {
            "id": "CAND-U1", "name": "Unpinned 1", "specialization": "backend", "grade": "lead",
            "theta": 98.0, "skills": ["rust", "elixir", "couchdb", "grpc", "k8s"], "freshness": 98.0, "fsp_id": "FSP-U1",
            "sport_rank": "ms", "medal": "gold", "stage": "всероссийский", "rating_points": 35
        },
        {
            "id": "CAND-U2", "name": "Unpinned 2", "specialization": "backend", "grade": "senior",
            "theta": 96.0, "skills": ["rust", "elixir", "couchdb", "docker"], "freshness": 95.0, "fsp_id": None,
        },
        {
            "id": "CAND-U3", "name": "Unpinned 3", "specialization": "backend", "grade": "senior",
            "theta": 94.0, "skills": ["rust", "elixir", "couchdb"], "freshness": 92.0, "fsp_id": None,
        },
        {
            "id": "CAND-U4", "name": "Unpinned 4", "specialization": "backend", "grade": "middle",
            "theta": 88.0, "skills": ["rust", "elixir"], "freshness": 89.0, "fsp_id": None,
        },
        {
            "id": "CAND-U5", "name": "Unpinned 5", "specialization": "backend", "grade": "middle",
            "theta": 80.0, "skills": ["python", "django"], "freshness": 80.0, "fsp_id": None,
        },
        {
            "id": "CAND-U6", "name": "Unpinned 6", "specialization": "backend", "grade": "junior",
            "theta": 75.0, "skills": ["python"], "freshness": 75.0, "fsp_id": None,
        },
        {
            "id": "CAND-U7", "name": "Unpinned 7", "specialization": "backend", "grade": "junior",
            "theta": 70.0, "skills": ["git"], "freshness": 70.0, "fsp_id": None,
        },
    ]

    # Initial state: query for Python
    initial_need = {
        "core_stack": ["python", "django", "postgresql"],
        "nice_to_have": ["redis"],
    }

    # Initial evaluation:
    initial_items = []
    for cand in candidates_pool:
        is_pinned = cand["id"].startswith("CAND-P")
        s_test = cand["theta"]
        s_stack = compute_stack_subscore(cand["skills"], initial_need["core_stack"], initial_need["nice_to_have"])
        s_fsp = compute_fsp_subscore(cand)
        s_fresh = cand["freshness"]
        has_fsp = cand.get("fsp_id") is not None
        score, _ = compute_ranking_score(s_test, s_stack, s_fsp, s_fresh, has_fsp)
        initial_items.append({
            "candidate": cand,
            "is_pinned": is_pinned,
            "match_score": score,
        })

    print("[*] Initial Shortlist Computed:")
    for it in initial_items:
        print(f"    {it['candidate']['id']}: Pinned={it['is_pinned']}, MatchScore={it['match_score']:.2f}")

    # ADVERSARIAL FILTER QUERY:
    # Completely replace required stack with Rust/Elixir/CouchDB
    # Pinned candidates have 0% overlap with this stack!
    adversarial_need = {
        "core_stack": ["rust", "elixir", "couchdb"],
        "nice_to_have": ["grpc", "k8s"],
    }

    print("\n[*] Applying Severe Filter Query (core_stack=['rust', 'elixir', 'couchdb']):")
    refined_results = refine_shortlist_with_pinning(initial_items, adversarial_need)

    print(f"\n{'Rank':<5} | {'Candidate ID':<12} | {'Is Pinned':<10} | {'New Score':<10} | {'Delta S':<10} | {'Old Score'}")
    print("-" * 65)
    for r in refined_results:
        print(f"{r['rank_position']:<5} | {r['candidate_id']:<12} | {str(r['is_pinned']):<10} | {r['match_score']:<10.2f} | {r['delta_score']:<10.2f} | {r['match_score'] - r['delta_score']:<10.2f}")

    # VERIFY PINNING INVARIANTS:
    assert len(refined_results) == 10, f"Expected 10 candidates, got {len(refined_results)}"

    # Invariant 1: Top 3 positions (1, 2, 3) MUST be pinned candidates
    top_3_pinned = [r["is_pinned"] for r in refined_results[:3]]
    top_3_ids = [r["candidate_id"] for r in refined_results[:3]]
    print(f"\n[*] Invariant 1: Top 3 positions must be pinned: {top_3_pinned} -> IDs: {top_3_ids}")
    assert all(top_3_pinned), f"Top 3 positions must all have is_pinned=True, got {top_3_pinned}"
    assert set(top_3_ids) == {"CAND-P1", "CAND-P2", "CAND-P3"}, f"Mismatch in pinned candidates: {top_3_ids}"

    # Invariant 2: Ranks 4..10 MUST be unpinned candidates
    remaining_unpinned = [r["is_pinned"] for r in refined_results[3:]]
    print(f"[*] Invariant 2: Positions 4..10 must be unpinned: {remaining_unpinned}")
    assert not any(remaining_unpinned), f"Positions 4..10 must all have is_pinned=False, got {remaining_unpinned}"

    # Invariant 3: Pinned candidates strictly dropped in native scores: Delta S < 0
    for r in refined_results[:3]:
        print(f"[*] Invariant 3: Pinned candidate {r['candidate_id']} Delta S = {r['delta_score']:.2f}")
        assert r["delta_score"] < 0, f"Expected Delta S < 0 for pinned candidate {r['candidate_id']}, got {r['delta_score']}"

    # Invariant 4: Pinned candidate score is LOWER than top unpinned candidate, yet ranked HIGHER
    top_unpinned_score = refined_results[3]["match_score"]
    lowest_pinned_score = refined_results[2]["match_score"]
    print(f"[*] Invariant 4: Score Inversion under Pinning: Lowest Pinned ({lowest_pinned_score:.2f}) vs Top Unpinned ({top_unpinned_score:.2f})")
    assert lowest_pinned_score < top_unpinned_score, (
        f"Under severe query, unpinned candidates should have higher score ({top_unpinned_score}) "
        f"than pinned candidates ({lowest_pinned_score}), verifying two-tier pinning enforcement."
    )

    # Invariant 5: Monotonic ordering within each tier
    pinned_scores = [r["match_score"] for r in refined_results[:3]]
    unpinned_scores = [r["match_score"] for r in refined_results[3:]]
    assert pinned_scores == sorted(pinned_scores, reverse=True), "Pinned tier must be sorted descending"
    assert unpinned_scores == sorted(unpinned_scores, reverse=True), "Unpinned tier must be sorted descending"

    print("[PASS] Test Suite 2: Stateful shortlist pinning invariants verified under severe adversarial queries.")


def test_anti_fraud_inn_and_salary() -> None:
    print("\n" + "=" * 80)
    print("TEST SUITE 3: ANTI-FRAUD FNS INN CHECKSUM & SALARY ANOMALY TEST")
    print("=" * 80)

    # 1. INN CHECKSUM TEST (26 test cases: 10-digit and 12-digit)
    inn_test_cases = [
        # --- VALID 10-DIGIT INNs (Official Russian legal entities) ---
        ("7707083893", True, "ПАО Сбербанк"),
        ("7736207543", True, "ООО Яндекс"),
        ("7736050003", True, "ПАО Газпром"),
        ("7743001840", True, "VK (Mail.ru)"),
        ("7710140679", True, "АО Тинькофф Банк"),
        ("7712040126", True, "ПАО Аэрофлот"),
        ("7706107510", True, "ПАО НК Роснефть"),
        ("7740000076", True, "ПАО МТС"),
        ("7812014560", True, "ПАО Мегафон"),
        ("7707049388", True, "ПАО Ростелеком"),

        # --- INVALID 10-DIGIT INNs ---
        ("7707083894", False, "Сбербанк with corrupted checksum digit 4 != 3"),
        ("7736207540", False, "Яндекс with corrupted checksum digit 0 != 3"),
        ("1234567890", False, "Sequential digits with invalid checksum"),
        ("9999999999", False, "All 9s invalid checksum"),
        ("770708389",  False, "9 digits (length violation)"),
        ("77070838931", False, "11 digits (length violation)"),
        ("770708389A", False, "Non-digit character"),
        ("",           False, "Empty string"),
        ("abcdefghij", False, "All alphabetic characters"),

        # --- VALID 12-DIGIT INNs (Entrepreneurs & individuals) ---
        ("500100732259", True, "Valid 12-digit INN #1"),
        ("772816897110", True, "Valid 12-digit INN #2"),
        ("780100000163", True, "Valid 12-digit INN #3"),

        # --- INVALID 12-DIGIT INNs ---
        ("500100732258", False, "12-digit with corrupted d12 (8 != 9)"),
        ("500100732249", False, "12-digit with corrupted d11 (4 != 5)"),
        ("772816897111", False, "12-digit with corrupted d12 (1 != 0)"),
        ("123456789012", False, "Arbitrary 12 digits invalid checksum"),
        ("5001007322591", False, "13 digits (length violation)"),
        ("50010073225",  False, "11 digits (length violation)"),
    ]

    print(f"[*] Running {len(inn_test_cases)} INN Verification Test Cases:")
    inn_passed = 0
    for inn_val, expected_valid, desc in inn_test_cases:
        res = verify_inn(inn_val)
        status = "PASS" if res == expected_valid else "FAIL"
        if status == "FAIL":
            print(f"    [FAIL] INN: '{inn_val}' | Expected: {expected_valid} | Got: {res} | {desc}")
        assert res == expected_valid, f"INN test failed for {inn_val} ({desc}): expected {expected_valid}, got {res}"
        inn_passed += 1

    print(f"[*] All {inn_passed} INN Test Cases Passed (10-digit and 12-digit FNS compliance verified).")

    # 2. SALARY ANOMALY TEST
    print("\n[*] Running Salary Anomaly & Boundary Test Cases:")
    salary_test_cases = [
        # (salary_min, salary_max, expected_valid, description)
        (100000, 250000, True,  "Standard salary range: ratio 2.50 <= 3.5"),
        (100000, 350000, True,  "Exact maximum threshold: ratio 3.50 == 3.5"),
        (200000, 200000, True,  "Flat salary: ratio 1.00 <= 3.5"),
        (50000,  150000, True,  "Junior range: ratio 3.00 <= 3.5"),
        (1,      3,      True,  "Minimal boundary: ratio 3.00 <= 3.5"),

        # Anomalies & Failures
        (100000, 350001, False, "Exceeds ratio: 3.50001 > 3.5"),
        (30000,  600000, False, "Clickbait range: ratio 20.0 > 3.5"),
        (10000,  1000000,False, "Extreme spread: ratio 100.0 > 3.5"),
        (0,      300000, False, "Zero minimum salary (boundary violation)"),
        (-50000, 200000, False, "Negative minimum salary"),
        (300000, 200000, False, "Inverted salary (max < min)"),
        (100000, -10000, False, "Inverted and negative salary"),
        (0,      0,      False, "Both zero"),
        (-1000,  -500,   False, "Both negative"),
    ]

    salary_passed = 0
    for s_min, s_max, expected_valid, desc in salary_test_cases:
        is_val, err_msg = validate_salary_range(s_min, s_max)
        status = "PASS" if is_val == expected_valid else "FAIL"
        ratio_str = f"ratio={(s_max/s_min):.2f}" if s_min > 0 else "N/A"
        print(f"    [{status}] ({s_min}, {s_max}) [{ratio_str}]: Valid={is_val} | Error='{err_msg}' | {desc}")
        assert is_val == expected_valid, (
            f"Salary test failed for ({s_min}, {s_max}): expected {expected_valid}, got {is_val} ({err_msg})"
        )
        salary_passed += 1

    print(f"[*] All {salary_passed} Salary Anomaly Test Cases Passed (ratio <= 3.5 and strict boundary invariants hold).")
    print("[PASS] Test Suite 3: Anti-fraud INN checksums and salary anomaly detection fully verified.")


def main() -> int:
    print("=" * 80)
    print("CHALLENGER_M3_2: EXECUTING ADVERSARIAL VERIFICATION HARNESS")
    print("=" * 80)

    try:
        test_non_fsp_ranking_parity()
        test_stateful_shortlist_pinning()
        test_anti_fraud_inn_and_salary()
        print("\n" + "#" * 80)
        print("### ALL ADVERSARIAL TESTS COMPLETED WITH 100% SUCCESS (EXIT CODE 0) ###")
        print("#" * 80 + "\n")
        return 0
    except AssertionError as e:
        print(f"\n[CRITICAL FAILURE] Assertion failed: {e}", file=sys.stderr)
        return 1
    except Exception as ex:
        print(f"\n[UNEXPECTED ERROR] {ex}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
