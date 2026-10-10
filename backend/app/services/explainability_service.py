"""
FSP IT-Talent Platform — Explainability Service.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §3.5 and SPEC.md.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


def get_recommendation_badge(score: float) -> str:
    """Returns fit badge based on overall match percentage score."""
    if score >= 90.0:
        return "Top Match"
    elif score >= 80.0:
        return "Strong Fit"
    elif score >= 70.0:
        return "Verified Fit"
    else:
        return "Potential Fit"


def build_radar_chart_data(
    test_score: float,
    stack_score: float,
    grade_multiplier: float,
    freshness_score: float,
    fsp_score: float,
    has_fsp: bool,
) -> List[Dict[str, Any]]:
    """
    Builds 5-axis radar chart series:
    1. Test Score (Балл тестирования KITE)
    2. Stack Overlap (Совпадение стека)
    3. Grade/Experience (Соответствие грейду)
    4. Freshness (Актуальность профиля)
    5. FSP Achievement (Достижения ФСП)
    """
    grade_fit = min(100.0, max(0.0, round(grade_multiplier * 100.0, 1)))
    fsp_val = fsp_score if has_fsp else 0.0

    return [
        {"axis": "Тестирование KITE", "value": round(test_score, 1), "full_mark": 100.0},
        {"axis": "Совпадение стека", "value": round(stack_score, 1), "full_mark": 100.0},
        {"axis": "Грейд и опыт", "value": grade_fit, "full_mark": 100.0},
        {"axis": "Свежесть профиля", "value": round(freshness_score, 1), "full_mark": 100.0},
        {"axis": "Достижения ФСП", "value": round(fsp_val, 1), "full_mark": 100.0},
    ]


def build_explainability(
    cand_spec: str,
    cand_grade: str,
    overall_score: float,
    test_subscore: float,
    stack_subscore: float,
    fsp_subscore: float,
    freshness_subscore: float,
    grade_multiplier: float,
    weights: Tuple[float, float, float, float],
    candidate_skills: Iterable[str],
    core_stack: Iterable[str],
    nice_to_have: Optional[Iterable[str]] = None,
    fsp_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synthesizes complete ExplainabilityObject dictionary matching docs/03 and docs/04 schema.
    """
    c_skills: Set[str] = {s.lower().strip() for s in candidate_skills if s}
    req_core = [s.strip() for s in core_stack if s]
    req_nice = [s.strip() for s in (nice_to_have or []) if s]
    all_req = req_core + req_nice

    matched_core = [s for s in req_core if s.lower() in c_skills]
    missing_core = [s for s in req_core if s.lower() not in c_skills]
    matched_nice = [s for s in req_nice if s.lower() in c_skills]
    missing_nice = [s for s in req_nice if s.lower() not in c_skills]

    matched_all = matched_core + matched_nice
    missing_all = missing_core + missing_nice

    has_fsp = bool(fsp_data and fsp_data.get("fsp_id"))

    if has_fsp:
        fsp_id = fsp_data.get("fsp_id")
        sport_rank = fsp_data.get("sport_rank", "1-й разряд")
        rating_pts = fsp_data.get("rating_points", 0)
        fsp_expl = (
            f"Верифицированный участник ФСП (ID: {fsp_id}). "
            f"Спортивный разряд: {sport_rank}, рейтинг: {rating_pts} п."
        )
    else:
        fsp_expl = (
            "Без соревновательной истории ФСП — квалификация подтверждена независимой "
            "сертификацией платформы. Применен весовой паритет (0.52/0.30/0.00/0.18)."
        )

    badge = get_recommendation_badge(overall_score)

    matched_sample = ", ".join(matched_all[:5]) if matched_all else "базовые навыки"
    spec_title = str(cand_spec).capitalize()
    grade_title = str(cand_grade).capitalize()

    narrative = (
        f"Кандидат подтвердил категорию {spec_title} · {grade_title} с баллом тестирования {test_subscore:.1f}/100. "
        f"Совпадение по стеку: {len(matched_all)}/{len(all_req) if all_req else 1} ключевых навыков ({matched_sample}). "
        f"{fsp_expl} Индекс актуальности знаний: {freshness_subscore:.1f}/100."
    )

    radar_chart = build_radar_chart_data(
        test_score=test_subscore,
        stack_score=stack_subscore,
        grade_multiplier=grade_multiplier,
        freshness_score=freshness_subscore,
        fsp_score=fsp_subscore,
        has_fsp=has_fsp,
    )

    w_test, w_stack, w_fsp, w_fresh = weights

    return {
        "match_percentage": overall_score,
        "overall_score": overall_score,
        "component_scores": {
            "test_score": test_subscore,
            "stack_score": stack_subscore,
            "fsp_score": fsp_subscore,
            "freshness_score": freshness_subscore,
            "weights_applied": {
                "is_fsp_profile": has_fsp,
                "w_test": w_test,
                "w_stack": w_stack,
                "w_fsp": w_fsp,
                "w_freshness": w_fresh,
                "sum_weights": round(sum(weights), 2),
            },
        },
        "matched_skills": matched_all,
        "missing_skills": missing_all,
        "matched_core_skills": matched_core,
        "missing_core_skills": missing_core,
        "matched_nice_skills": matched_nice,
        "missing_nice_skills": missing_nice,
        "radar_series": radar_chart,
        "fsp_bonus_explanation": fsp_expl,
        "freshness_activity": f"Актуальность {freshness_subscore:.1f}%",
        "recommendation_badge": badge,
        "human_summary_ru": narrative,
    }
