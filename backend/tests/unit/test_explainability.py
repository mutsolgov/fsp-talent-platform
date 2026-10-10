"""
Unit Test Suite for Explainability Service.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §3.5 and DISPATCH.md.
"""
from __future__ import annotations

import pytest

from app.services.explainability_service import (
    build_explainability,
    build_radar_chart_data,
    get_recommendation_badge,
)


def test_recommendation_badges():
    """Проверка пороговых бейджей рекомендаций."""
    assert get_recommendation_badge(95.0) == "Top Match"
    assert get_recommendation_badge(90.0) == "Top Match"
    assert get_recommendation_badge(85.5) == "Strong Fit"
    assert get_recommendation_badge(80.0) == "Strong Fit"
    assert get_recommendation_badge(75.0) == "Verified Fit"
    assert get_recommendation_badge(70.0) == "Verified Fit"
    assert get_recommendation_badge(69.9) == "Potential Fit"
    assert get_recommendation_badge(45.0) == "Potential Fit"


def test_radar_chart_data_5_axes():
    """Проверка структуры 5-осевого радара соответствия."""
    radar = build_radar_chart_data(
        test_score=85.0,
        stack_score=90.0,
        grade_multiplier=0.93,
        freshness_score=80.0,
        fsp_score=60.0,
        has_fsp=True,
    )

    assert len(radar) == 5
    axes = [item["axis"] for item in radar]
    assert "Тестирование KITE" in axes
    assert "Совпадение стека" in axes
    assert "Грейд и опыт" in axes
    assert "Свежесть профиля" in axes
    assert "Достижения ФСП" in axes

    for point in radar:
        assert 0.0 <= point["value"] <= 100.0
        assert point["full_mark"] == 100.0


def test_radar_chart_data_non_fsp():
    """Для кандидата без ФСП ось соревнований равна 0.0."""
    radar = build_radar_chart_data(
        test_score=92.0,
        stack_score=88.0,
        grade_multiplier=1.00,
        freshness_score=90.0,
        fsp_score=0.0,
        has_fsp=False,
    )
    fsp_point = next(p for p in radar if p["axis"] == "Достижения ФСП")
    assert fsp_point["value"] == 0.0


def test_matched_and_missing_skills_breakdown():
    """Проверка точной разбивки совпадающих и недостающих технологий."""
    expl = build_explainability(
        cand_spec="backend",
        cand_grade="middle",
        overall_score=84.5,
        test_subscore=82.0,
        stack_subscore=87.5,
        fsp_subscore=0.0,
        freshness_subscore=85.0,
        grade_multiplier=1.0,
        weights=(0.52, 0.30, 0.00, 0.18),
        candidate_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        core_stack=["Python", "PostgreSQL", "Kafka"],
        nice_to_have=["Docker", "Kubernetes"],
        fsp_data=None,
    )

    assert "Python" in expl["matched_core_skills"]
    assert "PostgreSQL" in expl["matched_core_skills"]
    assert "Kafka" in expl["missing_core_skills"]

    assert "Docker" in expl["matched_nice_skills"]
    assert "Kubernetes" in expl["missing_nice_skills"]


def test_narrative_generation_russian():
    """Проверка связного русскоязычного нарратива для менеджера."""
    expl = build_explainability(
        cand_spec="backend",
        cand_grade="middle",
        overall_score=92.0,
        test_subscore=90.0,
        stack_subscore=95.0,
        fsp_subscore=85.0,
        freshness_subscore=90.0,
        grade_multiplier=1.0,
        weights=(0.35, 0.25, 0.25, 0.15),
        candidate_skills=["python", "fastapi"],
        core_stack=["python"],
        nice_to_have=["fastapi"],
        fsp_data={
            "fsp_id": "FSP-101",
            "sport_rank": "Мастер спорта",
            "rating_points": 24,
        },
    )

    nar = expl["human_summary_ru"]
    assert "Backend" in nar
    assert "Middle" in nar
    assert "90.0/100" in nar
    assert "FSP-101" in nar
    assert expl["recommendation_badge"] == "Top Match"
