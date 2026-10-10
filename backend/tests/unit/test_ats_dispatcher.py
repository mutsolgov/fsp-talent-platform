"""
Unit tests for ATS Webhook Dispatcher & Export Gateway.
Defined in app/services/ats_dispatcher.py.
"""
from __future__ import annotations

import time
import pytest

from app.services.ats_dispatcher import (
    AtsDispatcher,
    FAST_RETRY_DELAYS_SECONDS,
    RETRY_DELAYS_SECONDS,
    sign_payload,
    verify_signature,
    verify_timestamp,
)


def test_sign_and_verify_payload():
    secret = "secret_webhook_key_xyz_12345678"
    payload = b'{"event":"invitation.accepted","candidate_id":1042}'

    signature = sign_payload(secret, payload)
    assert signature.startswith("sha256=")

    # Verification success
    assert verify_signature(secret, payload, signature) is True

    # Tampered payload fails
    tampered_payload = b'{"event":"invitation.accepted","candidate_id":9999}'
    assert verify_signature(secret, tampered_payload, signature) is False

    # Wrong secret fails
    assert verify_signature("wrong_secret_key_87654321", payload, signature) is False


def test_verify_timestamp_replay_window():
    now = int(time.time())

    # Current time is valid
    assert verify_timestamp(now) is True

    # 100 seconds ago is valid (within 300s window)
    assert verify_timestamp(now - 100) is True

    # 500 seconds ago is expired (anti-replay violation)
    assert verify_timestamp(now - 500) is False

    # 400 seconds in the future is invalid
    assert verify_timestamp(now + 400) is False


def test_build_headers():
    dispatcher = AtsDispatcher()
    secret = "fsp_test_secret_abc"
    payload = b'{"test":true}'

    headers = dispatcher.build_headers(secret, payload, event_type="invitation.accepted")

    assert headers["Content-Type"] == "application/json"
    assert "X-FSP-Signature" in headers
    assert headers["X-FSP-Signature"].startswith("sha256=")
    assert "X-FSP-Timestamp" in headers
    assert headers["X-FSP-Event"] == "invitation.accepted"
    assert "FSP-Platform-ATS-Dispatcher" in headers["User-Agent"]


def test_format_huntflow_candidate():
    dispatcher = AtsDispatcher()
    cand = {
        "first_name": "Иван",
        "last_name": "Иванов",
        "middle_name": "Иванович",
        "email": "ivan@example.com",
        "phone": "+79991234567",
        "telegram": "@ivanov",
        "specialization": "Backend",
        "grade": "Senior",
        "expected_salary": 300000,
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "fsp_id": "FSP-77-01042",
        "fsp_verified": True,
        "test_score": 95.0,
    }

    huntflow_data = dispatcher.format_huntflow_candidate(cand)

    assert huntflow_data["first_name"] == "Иван"
    assert huntflow_data["last_name"] == "Иванов"
    assert huntflow_data["email"] == "ivan@example.com"
    assert huntflow_data["money"] == 300000
    assert len(huntflow_data["skills"]) == 3
    assert huntflow_data["fsp_verification"]["fsp_id"] == "FSP-77-01042"
    assert huntflow_data["fsp_verification"]["fsp_verified"] is True


def test_format_hh_candidate():
    dispatcher = AtsDispatcher()
    cand = {
        "first_name": "Анна",
        "last_name": "Смирнова",
        "middle_name": None,
        "email": "anna@example.com",
        "phone": "+79997654321",
        "specialization": "Frontend",
        "grade": "Middle",
        "expected_salary": 180000,
        "skills": ["React", "TypeScript"],
    }

    hh_data = dispatcher.format_hh_candidate(cand)

    assert hh_data["first_name"] == "Анна"
    assert hh_data["last_name"] == "Смирнова"
    assert hh_data["salary"]["amount"] == 180000
    assert hh_data["salary"]["currency"] == "RUR"
    assert "React" in hh_data["skill_set"]


def test_handle_dispatch_failure_and_dlq():
    dispatcher = AtsDispatcher()
    event_id = "evt_101"
    url = "https://ats.example.com/webhook"
    payload = {"candidate_id": 42}

    # Attempt 0 -> Schedule retry (60s)
    res0 = dispatcher.handle_dispatch_failure(event_id, url, payload, 0, "HTTP 500")
    assert res0["status"] == "retry_scheduled"
    assert res0["next_retry_delay_seconds"] == 60
    assert res0["is_dlq"] is False

    # Attempt 1 -> Schedule retry (300s)
    res1 = dispatcher.handle_dispatch_failure(event_id, url, payload, 1, "HTTP 502")
    assert res1["status"] == "retry_scheduled"
    assert res1["next_retry_delay_seconds"] == 300
    assert res1["is_dlq"] is False

    # Attempt 2 -> Schedule retry (900s)
    res2 = dispatcher.handle_dispatch_failure(event_id, url, payload, 2, "HTTP 504")
    assert res2["status"] == "retry_scheduled"
    assert res2["next_retry_delay_seconds"] == 900
    assert res2["is_dlq"] is False

    # Attempt 3 -> Exhausted -> Route to Dead Letter Queue (DLQ)
    res3 = dispatcher.handle_dispatch_failure(event_id, url, payload, 3, "HTTP Connection Timeout")
    assert res3["status"] == "dlq_routed"
    assert res3["is_dlq"] is True
    assert res3["next_retry_delay_seconds"] is None
    assert len(dispatcher.dlq_log) == 1
    assert dispatcher.dlq_log[0]["event_id"] == "evt_101"
    assert dispatcher.dlq_log[0]["last_error"] == "HTTP Connection Timeout"


def test_handle_dispatch_failure_fast_retries_and_dlq():
    """Verifies configurable FAST_RETRY_DELAYS_SECONDS = [1, 2, 4, 8, 16] exponential backoff and DLQ routing."""
    assert FAST_RETRY_DELAYS_SECONDS == [1, 2, 4, 8, 16]
    assert RETRY_DELAYS_SECONDS == [60, 300, 900]

    dispatcher = AtsDispatcher(retry_delays=FAST_RETRY_DELAYS_SECONDS)
    assert dispatcher.retry_delays == [1, 2, 4, 8, 16]

    event_id = "evt_fast_42"
    url = "https://ats.mock.fsp.ru/webhook"
    payload = {"candidate_id": 1042, "status": "accepted"}

    # Attempt 0 -> 1s
    r0 = dispatcher.handle_dispatch_failure(event_id, url, payload, 0, "Network Glitch")
    assert r0["status"] == "retry_scheduled"
    assert r0["next_retry_delay_seconds"] == 1
    assert r0["is_dlq"] is False

    # Attempt 1 -> 2s
    r1 = dispatcher.handle_dispatch_failure(event_id, url, payload, 1, "Network Glitch")
    assert r1["next_retry_delay_seconds"] == 2

    # Attempt 2 -> 4s
    r2 = dispatcher.handle_dispatch_failure(event_id, url, payload, 2, "Network Glitch")
    assert r2["next_retry_delay_seconds"] == 4

    # Attempt 3 -> 8s
    r3 = dispatcher.handle_dispatch_failure(event_id, url, payload, 3, "Network Glitch")
    assert r3["next_retry_delay_seconds"] == 8

    # Attempt 4 -> 16s
    r4 = dispatcher.handle_dispatch_failure(event_id, url, payload, 4, "Network Glitch")
    assert r4["status"] == "retry_scheduled"
    assert r4["next_retry_delay_seconds"] == 16
    assert r4["is_dlq"] is False

    # Attempt 5 -> Exhausted (5 attempts: 1, 2, 4, 8, 16) -> DLQ
    r5 = dispatcher.handle_dispatch_failure(event_id, url, payload, 5, "Connection reset by peer")
    assert r5["status"] == "dlq_routed"
    assert r5["is_dlq"] is True
    assert r5["next_retry_delay_seconds"] is None
    assert len(dispatcher.dlq_log) == 1
    assert dispatcher.dlq_log[0]["event_id"] == "evt_fast_42"
    assert dispatcher.dlq_log[0]["attempts_exhausted"] == 6

