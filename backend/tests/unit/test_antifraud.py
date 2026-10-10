"""
Unit tests for Anti-Fraud & Employer Trust Verification Service.
Defined in app/services/antifraud_service.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.models.employer_profiles import EmployerProfile
from app.services.antifraud_service import (
    can_send_invitation,
    record_invitation_sent,
    validate_salary_range,
    verify_corporate_domain,
    verify_inn,
)


def test_verify_inn_10_digits():
    # Valid 10-digit Russian INN (Sber: 7707083893, Yandex: 7736207543)
    assert verify_inn("7707083893") is True
    assert verify_inn("7736207543") is True

    # Invalid checksum
    assert verify_inn("7707083894") is False
    assert verify_inn("1234567890") is False

    # Invalid lengths and formats
    assert verify_inn("770708389") is False
    assert verify_inn("77070838931") is False
    assert verify_inn("abcdefghij") is False
    assert verify_inn("") is False


def test_verify_inn_12_digits():
    # Valid 12-digit Russian INN (e.g. 500100732259)
    assert verify_inn("500100732259") is True

    # Invalid 12-digit checksum
    assert verify_inn("500100732250") is False
    assert verify_inn("123456789012") is False


def test_verify_corporate_domain():
    # Corporate domains allowed
    valid, err = verify_corporate_domain("recruiter@sberbank.ru")
    assert valid is True
    assert err is None

    valid, err = verify_corporate_domain("hr@tech-corp.com")
    assert valid is True
    assert err is None

    # Free public mail providers forbidden
    valid, err = verify_corporate_domain("hr_lead@gmail.com")
    assert valid is False
    assert "бесплатных почтовых сервисов" in err

    valid, err = verify_corporate_domain("vasya@mail.ru")
    assert valid is False
    assert "бесплатных почтовых сервисов" in err

    valid, err = verify_corporate_domain("job@yandex.ru")
    assert valid is False
    assert "бесплатных почтовых сервисов" in err

    # Invalid domain formats
    valid, err = verify_corporate_domain("invalid-format")
    assert valid is False

    valid, err = verify_corporate_domain("")
    assert valid is False


def test_validate_salary_range_bounds_and_spread():
    # Valid transparent salary range
    valid, err = validate_salary_range(150000, 250000)
    assert valid is True
    assert err is None

    # Hidden / non-positive salary_min
    valid, err = validate_salary_range(0, 100000)
    assert valid is False
    assert "строго больше 0" in err

    valid, err = validate_salary_range(-50000, 100000)
    assert valid is False
    assert "строго больше 0" in err

    # salary_max < salary_min
    valid, err = validate_salary_range(200000, 150000)
    assert valid is False
    assert "не может быть меньше минимальной" in err

    # Spread ratio > 3.5 (Anti-Fraud protection)
    # Ratio = 400000 / 100000 = 4.0 (> 3.5)
    valid, err = validate_salary_range(100000, 400000)
    assert valid is False
    assert "превышает допустимый антифрод-лимит 3.5" in err

    # Edge case: Exactly 3.5 ratio
    valid, err = validate_salary_range(100000, 350000)
    assert valid is True
    assert err is None


def test_can_send_invitation_daily_quota():
    class DummyEmployer:
        invite_daily_limit = 20
        invites_sent_today = 0
        last_invite_reset_at = datetime.now(timezone.utc)

    emp = DummyEmployer()

    # Initial state
    allowed, rem = can_send_invitation(emp)
    assert allowed is True
    assert rem == 20

    # Send 19 invites
    for _ in range(19):
        record_invitation_sent(emp)

    allowed, rem = can_send_invitation(emp)
    assert allowed is True
    assert rem == 1

    # Send 20th invite
    record_invitation_sent(emp)
    assert emp.invites_sent_today == 20

    # Quota reached
    allowed, rem = can_send_invitation(emp)
    assert allowed is False
    assert rem == 0

    # Next day reset
    emp.last_invite_reset_at = datetime.now(timezone.utc) - timedelta(days=1, hours=1)
    allowed, rem = can_send_invitation(emp)
    assert allowed is True
    assert rem == 20
    assert emp.invites_sent_today == 0
