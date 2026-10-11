"""
Unit Test Suite for Multi-Factor Ranking Engine.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §3.2-3.4 and DISPATCH.md.
"""
from __future__ import annotations

from app.services.ranking_engine import (
    calculate_candidate_score,
    calculate_fsp_subscore,
    calculate_grade_multiplier,
    calculate_stack_subscore,
    calculate_weights,
    compute_freshness_subscore,
    aggregate_candidate_fsp_data,
)


def test_grade_multipliers():
    """Проверка всех ступеней мультипликатора грейдов."""
    assert calculate_grade_multiplier("middle", "middle") == 1.00
    assert calculate_grade_multiplier(2, 2) == 1.00

    # Разница +1 (кандидат старше на 1 грейд)
    assert calculate_grade_multiplier("senior", "middle") == 0.93
    assert calculate_grade_multiplier(3, 2) == 0.93

    # Разница -1 (кандидат младше на 1 грейд)
    assert calculate_grade_multiplier("junior", "middle") == 0.85
    assert calculate_grade_multiplier(1, 2) == 0.85

    # Разница +2
    assert calculate_grade_multiplier("lead", "middle") == 0.60
    assert calculate_grade_multiplier(4, 2) == 0.60

    # Разница -2
    assert calculate_grade_multiplier("junior", "senior") == 0.45
    assert calculate_grade_multiplier(1, 3) == 0.45

    # Разница > 2
    assert calculate_grade_multiplier("lead", "junior") == 0.25
    assert calculate_grade_multiplier(4, 1) == 0.25
    assert calculate_grade_multiplier("junior", "lead") == 0.25


def test_dynamic_weights_allocation():
    """Проверка динамической перенормировки весов с сохранением суммы 1.00."""
    w_fsp = calculate_weights(has_fsp=True)
    assert w_fsp == (0.40, 0.25, 0.20, 0.15)
    assert abs(sum(w_fsp) - 1.00) < 1e-5

    w_non_fsp = calculate_weights(has_fsp=False)
    assert w_non_fsp == (0.52, 0.30, 0.00, 0.18)
    assert abs(sum(w_non_fsp) - 1.00) < 1e-5


def test_non_fsp_zero_glass_ceiling_can_reach_100():
    """Доказательство паритета: кандидат БЕЗ ФСП может получить максимальный балл 100.0."""
    res = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="senior",
        need_grade="senior",
        theta_score=100.0,
        candidate_skills=["python", "fastapi", "postgresql", "docker", "redis"],
        core_stack=["python", "fastapi", "postgresql"],
        nice_to_have=["docker", "redis"],
        fsp_data=None,  # No FSP!
        freshness_score=100.0,
    )

    assert res["has_fsp"] is False
    assert res["weights"] == (0.52, 0.30, 0.00, 0.18)
    assert res["overall_score"] == 100.0
    assert res["test_subscore"] == 100.0
    assert res["stack_subscore"] == 100.0
    assert res["freshness_subscore"] == 100.0
    assert res["fsp_subscore"] == 0.0


def test_meritocracy_strong_non_fsp_beats_weak_fsp():
    """Сильный практик без ФСП (95.52) уверенно обходит слабого олимпиадника с КМС (77.30)."""
    # 1. Выдающийся разработчик без ФСП
    strong_non_fsp = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="senior",
        need_grade="senior",
        theta_score=96.0,
        candidate_skills=["python", "postgresql", "fastapi"],
        core_stack=["python", "postgresql"],
        nice_to_have=["fastapi"],
        fsp_data=None,
        freshness_score=95.0,
    )

    # 2. Посредственный программист с удостоверением КМС
    weak_fsp = calculate_candidate_score(
        cand_spec="backend",
        need_spec="backend",
        cand_grade="senior",
        need_grade="senior",
        theta_score=78.0,
        candidate_skills=["python"],
        core_stack=["python", "postgresql"],
        nice_to_have=["fastapi"],
        fsp_data={
            "fsp_id": "FSP-RUS-7701",
            "sport_rank": "kms",
            "stage": "всероссийский",
            "medal": "silver",
            "rating_points": 18,
        },
        freshness_score=75.0,
    )

    assert strong_non_fsp["overall_score"] > weak_fsp["overall_score"]
    assert strong_non_fsp["overall_score"] >= 90.0


def test_jaccard_stack_subscore():
    """Проверка формулы Жаккара: 75% core + 25% nice-to-have."""
    # Полное совпадение
    assert calculate_stack_subscore(
        candidate_skills=["python", "django", "redis"],
        core_stack=["python", "django"],
        nice_to_have=["redis"],
    ) == 100.0

    # Core 100%, nice-to-have 0% -> 75.0
    assert calculate_stack_subscore(
        candidate_skills=["python", "django"],
        core_stack=["python", "django"],
        nice_to_have=["redis", "clickhouse"],
    ) == 75.0

    # Core 50% (1/2), nice 100% -> 0.75*50 + 0.25*100 = 37.5 + 25.0 = 62.5
    assert calculate_stack_subscore(
        candidate_skills=["python", "redis"],
        core_stack=["python", "django"],
        nice_to_have=["redis"],
    ) == 62.5

    # Пустые требования -> 100.0
    assert calculate_stack_subscore(
        candidate_skills=["python"],
        core_stack=[],
        nice_to_have=[],
    ) == 100.0


def test_fsp_subscore_breakdown():
    """Проверка расчета соревновательного балла ФСП."""
    assert calculate_fsp_subscore(None) == 0.0
    assert calculate_fsp_subscore({}) == 0.0
    assert calculate_fsp_subscore({"fsp_id": None}) == 0.0

    # Мастер спорта, золото, всероссийский, рейтинг 25+
    res_max = calculate_fsp_subscore({
        "fsp_id": "FSP-101",
        "sport_rank": "ms",
        "stage": "всероссийский",
        "medal": "gold",
        "rating_points": 25,
    })
    # 0.35*100 + 0.40*40*1.0 + 0.25*100 = 35 + 16 + 25 = 76.0
    assert res_max > 70.0


def test_specialization_mismatch_zero_score():
    """При несовпадении специализации итоговый балл S строго равен 0.0."""
    res = calculate_candidate_score(
        cand_spec="frontend",
        need_spec="backend",
        cand_grade="senior",
        need_grade="senior",
        theta_score=95.0,
        candidate_skills=["react", "typescript"],
        core_stack=["python", "fastapi"],
        fsp_data={"fsp_id": "FSP-999"},
        freshness_score=90.0,
    )
    assert res["overall_score"] == 0.0
    assert res["specialization_match"] is False


def test_empty_nice_to_have_zero_unearned_points():
    """Кандидат с 0 совпадений по core_stack при пустом nice_to_have получает 0.0, а не 25.0 unearned points."""
    zero_score = calculate_stack_subscore(
        candidate_skills=["ruby", "rails"],
        core_stack=["python", "django"],
        nice_to_have=[],
    )
    assert zero_score == 0.0

    full_score = calculate_stack_subscore(
        candidate_skills=["python", "django"],
        core_stack=["python", "django"],
        nice_to_have=None,
    )
    assert full_score == 100.0


def test_compute_freshness_subscore_decay():
    """
    Проверка экспоненциального затухания свежести (t_1/2 = 90 дней):
    - 0 дней: 100.0
    - 90 дней: 50.0
    - 180 дней: 25.0
    """
    assert compute_freshness_subscore(0.0) == 100.0
    assert abs(compute_freshness_subscore(90.0) - 50.0) < 0.1
    assert abs(compute_freshness_subscore(180.0) - 25.0) < 0.1


def test_compute_freshness_subscore_with_challenge_boost():
    """
    Проверка буста за микро-челленджи (t_1/2 = 30 дней) и ограничения [0.0, 100.0]:
    """
    # 90 дней давности теста (базовый 50.0) + свежий челлендж 0 дней назад (20 очков) -> ~70.0
    res = compute_freshness_subscore(
        days_since_test=90.0,
        recent_challenges=[{"points": 20.0, "days_ago": 0.0}],
    )
    assert abs(res - 70.0) < 0.2

    # Челлендж 30 дней назад -> половинный буст (10 очков) -> ~60.0
    res_half = compute_freshness_subscore(
        days_since_test=90.0,
        recent_challenges=[{"points": 20.0, "days_ago": 30.0}],
    )
    assert abs(res_half - 60.0) < 0.2

    # Превышение 100 ограничивается потолком 100.0
    res_capped = compute_freshness_subscore(
        days_since_test=0.0,
        recent_challenges=[{"points": 50.0, "days_ago": 0.0}],
    )
    assert res_capped == 100.0


def test_aggregate_candidate_fsp_data():
    """Проверка корректной агрегации спортивных достижений ФСП."""
    class MockAchievement:
        def __init__(self, sport_rank, medal, stage, rating_points):
            self.sport_rank = sport_rank
            self.medal = medal
            self.stage = stage
            self.rating_points = rating_points

    achievements = [
        # Региональное золото: 40 * 0.6 = 24.0
        MockAchievement(sport_rank="first_class", medal="gold", stage="региональный", rating_points=10),
        # Всероссийское серебро: 30 * 1.0 = 30.0 (лучшая эффективная медаль)
        MockAchievement(sport_rank="kms", medal="silver", stage="всероссийский", rating_points=15),
    ]

    agg = aggregate_candidate_fsp_data("FSP-101", achievements)
    assert agg is not None
    assert agg["fsp_id"] == "FSP-101"
    assert agg["sport_rank"] == "kms"  # Высший разряд (kms > first_class)
    assert agg["medal"] == "silver"
    assert agg["stage"] == "всероссийский"
    assert agg["rating_points"] == 25  # 10 + 15 = 25


def test_aggregate_candidate_fsp_data_none_and_empty():
    """Проверка граничных условий агрегатора: fsp_id=None или пустой список достижений."""
    assert aggregate_candidate_fsp_data(None) is None
    assert aggregate_candidate_fsp_data(None, []) is None

    empty_agg = aggregate_candidate_fsp_data("FSP-200", [])
    assert empty_agg is not None
    assert empty_agg["fsp_id"] == "FSP-200"
    assert empty_agg["sport_rank"] is None
    assert empty_agg["rating_points"] == 0


def test_grade_multiplier_none_and_invalid_types():
    """Дефект N10: безопасная обработка None и невалидных типов грейда."""
    assert calculate_grade_multiplier(None, "middle") == 1.00
    assert calculate_grade_multiplier("senior", None) == 0.93
    assert calculate_grade_multiplier(None, None) == 1.00
    assert calculate_grade_multiplier("invalid_grade", "middle") == 1.00
    assert calculate_grade_multiplier(object(), 2) == 1.00
