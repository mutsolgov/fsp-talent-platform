"""
Unit Test Suite for Grading Engine & Cooldown Controller.
Verifies non-coercive evaluation (EC-05 theta < 70, EC-06 theta >= 88, EC-07 boost safety),
90-day cooldown enforcement (EC-08), and jury demo bypass (EC-09).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.services.grading_engine import GradingEngine


def test_eval_theta_below_70_no_forced_downgrade():
    """EC-05: theta < 70 не понижает грейд принудительно, предлагает ретест на грейд ниже без кулдауна."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    res = GradingEngine.evaluate_session(
        candidate_id=1,
        claimed_grade="Middle",
        theta_score=62.5,
        session_type="initial",
        now=now,
    )

    assert res["is_grade_confirmed"] is False
    assert res["verdict"] == "retest_lower_offered"
    assert res["retest_lower_offered"] is True
    assert res["suggested_grade"] == "Junior"
    assert res["cooldown_until"] is None, "Ретест на уровень ниже должен быть доступен без кулдауна"


def test_eval_theta_standard_confirmation_70_to_88():
    """70 <= theta < 88: подтверждение заявленного грейда и запуск 90-дневного кулдауна."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    res = GradingEngine.evaluate_session(
        candidate_id=2,
        claimed_grade="Middle",
        theta_score=75.0,
        session_type="initial",
        now=now,
    )

    assert res["is_grade_confirmed"] is True
    assert res["verdict"] == "confirmed"
    assert res["confirmed_grade"] == "Middle"
    assert res["boost_offered"] is False
    assert res["retest_lower_offered"] is False
    expected_cooldown = now + timedelta(days=90)
    assert res["cooldown_until"] == expected_cooldown


def test_eval_theta_high_performance_boost_offer():
    """EC-06: theta >= 88 подтверждает грейд и предлагает добровольный риск-фри буст-тест."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    res = GradingEngine.evaluate_session(
        candidate_id=3,
        claimed_grade="Middle",
        theta_score=91.4,
        session_type="initial",
        now=now,
    )

    assert res["is_grade_confirmed"] is True
    assert res["verdict"] == "boost_offered"
    assert res["confirmed_grade"] == "Middle"
    assert res["boost_offered"] is True
    assert res["suggested_grade"] == "Senior"


def test_eval_lead_highest_grade_no_higher_boost():
    """Для максимального грейда Lead (4) буст-тест выше недоступен."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    res = GradingEngine.evaluate_session(
        candidate_id=4,
        claimed_grade="Lead",
        theta_score=95.0,
        session_type="initial",
        now=now,
    )

    assert res["is_grade_confirmed"] is True
    assert res["verdict"] == "confirmed"
    assert res["confirmed_grade"] == "Lead"
    assert res["boost_offered"] is False
    assert res["suggested_grade"] is None


def test_eval_boost_success_promotes_grade():
    """Успешное прохождение буст-теста (theta >= 70) утверждает повышенный грейд."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    res = GradingEngine.evaluate_session(
        candidate_id=5,
        claimed_grade="Senior",
        theta_score=74.0,
        session_type="boost",
        now=now,
    )

    assert res["is_grade_confirmed"] is True
    assert res["boost_passed"] is True
    assert res["confirmed_grade"] == "Senior"


def test_eval_boost_failure_preserves_base_grade():
    """EC-07: Провал буст-теста (theta < 70) гарантированно сохраняет базовый грейд без штрафа."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    res = GradingEngine.evaluate_session(
        candidate_id=6,
        claimed_grade="Senior",
        theta_score=58.0,
        session_type="boost",
        now=now,
    )

    assert res["is_grade_confirmed"] is True
    assert res["boost_passed"] is False
    assert res["confirmed_grade"] == "Middle", "Базовый грейд Middle должен быть сохранен при неудаче буста на Senior"


def test_cooldown_blocks_same_or_higher_grade():
    """EC-08: Активный 90-дневный кулдаун блокирует пересдачу на тот же или более высокий грейд."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    cooldown_until = now + timedelta(days=60)

    # Попытка сдачи на Middle (тот же)
    allowed, msg = GradingEngine.check_cooldown(
        cooldown_until=cooldown_until,
        target_grade="Middle",
        current_confirmed_grade="Middle",
        is_demo_bypass=False,
        now=now,
    )
    assert allowed is False
    assert "90-дневный кулдаун" in msg

    # Попытка сдачи на Senior (выше)
    allowed, msg = GradingEngine.check_cooldown(
        cooldown_until=cooldown_until,
        target_grade="Senior",
        current_confirmed_grade="Middle",
        is_demo_bypass=False,
        now=now,
    )
    assert allowed is False


def test_cooldown_allows_lower_retest_and_expired():
    """Сдача на более низкий грейд разрешена даже при активном кулдауне."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    cooldown_until = now + timedelta(days=60)

    # Попытка сдачи на Junior (ниже)
    allowed, msg = GradingEngine.check_cooldown(
        cooldown_until=cooldown_until,
        target_grade="Junior",
        current_confirmed_grade="Middle",
        is_demo_bypass=False,
        now=now,
    )
    assert allowed is True
    assert msg is None

    # Истекший кулдаун
    past_cooldown = now - timedelta(days=1)
    allowed_expired, _ = GradingEngine.check_cooldown(
        cooldown_until=past_cooldown,
        target_grade="Middle",
        now=now,
    )
    assert allowed_expired is True


def test_cooldown_jury_demo_bypass():
    """EC-09: Демо-сброс для жюри мгновенно снимает блокировку кулдауна."""
    now = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    cooldown_until = now + timedelta(days=89)

    allowed, msg = GradingEngine.check_cooldown(
        cooldown_until=cooldown_until,
        target_grade="Senior",
        current_confirmed_grade="Middle",
        is_demo_bypass=True,
        now=now,
    )
    assert allowed is True
    assert msg is None
