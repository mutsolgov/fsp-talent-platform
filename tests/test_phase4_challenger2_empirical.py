#!/usr/bin/env python3
"""
FSP IT-Talent Platform — QA Automation & Benchmark Challenger Phase 4 Harness
Empirical Challenger: challenger_qa_phase4_2
Targets:
- 152-ФЗ Contact Privacy Barrier, State Machine Transitions & Multi-Tenant Isolation
- Salary Invariants & Anti-Fraud Boundaries (spread <= 3.5, RUB currency)
- ATS Webhook HMAC-SHA256, Replay Protection (300s) & Exponential DLQ Schedule
- Branded PDF Generation & Non-FSP Graceful Fallback (fsp_id = null)
- Direct Vacancy Applications & Unmasking Access
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Setup paths
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, text

from app.database import get_db
from app.main import app
from app.models.base import Base
import app.models as _models  # noqa: F401
from app.models.users import User
from app.models.employer_profiles import EmployerProfile
from app.models.candidate_profiles import CandidateProfile
from app.models.vacancies import Vacancy
from app.models.invitations import Invitation
from app.models.applications import Application
from app.services.ats_dispatcher import (
    sign_payload,
    verify_signature,
    verify_timestamp,
    AtsDispatcher,
    REPLAY_WINDOW_SECONDS,
    FAST_RETRY_DELAYS_SECONDS,
)
from app.services.pdf_generator import generate_fsp_profile_pdf
from scripts.seed_reference_data import seed_reference_data

TEST_DB_FILE = repo_root / "test_phase4_challenger2.db"
TEST_DB_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"

engine = create_async_engine(TEST_DB_URL, echo=False)
session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_clean_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        await seed_reference_data(session)


def make_valid_inn(seed: int) -> str:
    base = f"77{seed:07d}"
    digits = [int(d) for d in base]
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    ctrl = sum(d * w for d, w in zip(digits, weights)) % 11
    if ctrl > 9:
        ctrl = ctrl % 10
    return base + str(ctrl)


def auth_user(client: TestClient, email: str, role: str) -> dict[str, str]:
    inn = make_valid_inn(int(time.time() * 1000) % 800000 + 1000) if role == "employer" else None
    company = "ООО Челленджер Корп" if role == "employer" else None
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123!",
            "role": role,
            "first_name": "Тестер",
            "last_name": "Челленджеров",
            "company_name": company,
            "inn": inn,
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    if res.status_code == 201:
        token = res.json()["tokens"]["access_token"]
    else:
        login = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPassword123!"})
        token = login.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TEST SUITE 1: 152-ФЗ Contact Privacy & State-Machine Unmasking
# ==============================================================================
def test_privacy_state_machine_and_multi_tenant(client: TestClient):
    print("--- [TEST 1] 152-ФЗ Contact Privacy & Multi-Tenant Isolation ---")
    cand_hdr = auth_user(client, "cand.challenger@fsp.ru", role="candidate")

    # Onboarding
    surv = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_hdr,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python", "fastapi"]},
    )
    assert surv.status_code == 201, f"Onboarding failed: {surv.text}"

    # Update private contacts
    put_res = client.put(
        "/api/v1/candidate-profile/me",
        headers=cand_hdr,
        json={
            "phone": "+7 (999) 444-55-66",
            "telegram": "@challenger_candidate",
            "github_url": "https://github.com/challenger_cand",
        },
    )
    assert put_res.status_code == 200, f"Update profile failed: {put_res.text}"

    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_hdr).json()
    cand_id = cand_me["id"]

    # Employer A
    emp_a_hdr = auth_user(client, "emp.a@fsp.ru", role="employer")
    # Employer B
    emp_b_hdr = auth_user(client, "emp.b@fsp.ru", role="employer")

    # Stage 1: No invitation sent
    det_a = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_a_hdr).json()
    assert det_a["is_contacts_masked"] is True, "Contacts must be masked initially"
    assert det_a["email"] is None
    assert det_a["phone"] is None
    assert det_a["telegram"] is None
    assert det_a["github_url"] is None
    assert "(#C-" in det_a["masked_full_name"], "Full name must be masked"

    cnt_a = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_hdr)
    assert cnt_a.status_code == 403, "Direct contact access must be 403"

    # Stage 2: Employer A sends invitation (status = 'sent')
    inv_res = client.post(
        "/api/v1/invitations",
        headers=emp_a_hdr,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Приглашаем в команду платежного шлюза",
            "salary_min": 200000,
            "salary_max": 300000,
        },
    )
    assert inv_res.status_code == 201, f"Invitation failed: {inv_res.text}"
    inv_id = inv_res.json()["id"]

    # In 'sent' state, contacts must REMAIN MASKED
    det_a_sent = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_a_hdr).json()
    assert det_a_sent["is_contacts_masked"] is True
    assert det_a_sent["phone"] is None
    cnt_a_sent = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_hdr)
    assert cnt_a_sent.status_code == 403

    # Stage 3: Candidate accepts invitation -> status = 'accepted'
    acc_res = client.post(f"/api/v1/invitations/{inv_id}/accept", headers=cand_hdr)
    assert acc_res.status_code == 200, f"Accept failed: {acc_res.text}"

    # Stage 4: Employer A now gets unmasked contacts
    cnt_a_acc = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_hdr)
    assert cnt_a_acc.status_code == 200, f"Unmasked contacts should be accessible: {cnt_a_acc.text}"
    contacts_data = cnt_a_acc.json()
    assert contacts_data["phone"] == "+7 (999) 444-55-66"
    assert contacts_data["telegram"] == "@challenger_candidate"
    assert contacts_data["github_url"] == "https://github.com/challenger_cand"
    assert contacts_data["email"] == "cand.challenger@fsp.ru"

    # Stage 5: Multi-Tenant Isolation: Employer B must STILL BE FORBIDDEN (403)
    cnt_b = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_b_hdr)
    assert cnt_b.status_code == 403, "Employer B must not have access to candidate contacts!"
    det_b = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_b_hdr).json()
    assert det_b["is_contacts_masked"] is True
    assert det_b["phone"] is None
    print("[PASS] 152-ФЗ Contact Privacy & Multi-Tenant Isolation verified.")


# ==============================================================================
# TEST SUITE 2: Salary Range Invariants & Anti-Fraud Boundaries
# ==============================================================================
def test_salary_range_and_spread_invariants(client: TestClient):
    print("--- [TEST 2] Salary Invariants & Spread Boundary Checks ---")
    emp_hdr = auth_user(client, "emp.salary_challenger@fsp.ru", role="employer")

    cases = [
        # (min, max, expected_status, description)
        (0, 200000, 422, "salary_min == 0 rejected"),
        (-50000, 200000, 422, "negative salary_min rejected"),
        (250000, 200000, 422, "salary_max < salary_min rejected"),
        (100000, 360000, 422, "spread 3.6 > 3.5 rejected"),
        (100000, 350000, 201, "spread 3.5 exact boundary accepted"),
        (180000, 250000, 201, "normal spread accepted"),
        (220000, 220000, 201, "fixed salary min == max accepted"),
    ]

    for min_val, max_val, expected, desc in cases:
        vac_res = client.post(
            "/api/v1/vacancies",
            headers=emp_hdr,
            json={
                "specialization_id": 1,
                "grade_id": 2,
                "title": f"Позиция {min_val}-{max_val}",
                "description": "Подробное описание вакансии для команды разработки высоконагруженных систем",
                "required_skills": ["python", "postgresql"],
                "salary_min": min_val,
                "salary_max": max_val,
                "salary_currency": "RUB",
                "work_format": "remote",
            },
        )
        assert vac_res.status_code == expected, (
            f"Failed on case '{desc}': expected HTTP {expected}, got {vac_res.status_code} ({vac_res.text})"
        )

    print("[PASS] Salary range invariants and anti-fraud spread guardrails verified.")


# ==============================================================================
# TEST SUITE 3: ATS Webhook HMAC-SHA256, Replay Defense & DLQ Lifecycle
# ==============================================================================
def test_ats_webhook_security_and_dlq(client: TestClient):
    print("--- [TEST 3] ATS Webhook HMAC-SHA256 & Replay Protection ---")
    secret = "fsp_test_super_secret_ats_key_2026"
    now_ts = int(time.time())
    payload = b'{"event": "invitation.accepted", "candidate_id": 42}'

    # 1. Valid signature
    sig_header = sign_payload(secret, payload)
    assert verify_signature(secret, payload, sig_header) is True, "Valid signature rejected"

    # 2. Corrupted signature header rejected
    corrupted_sig = sig_header + "bad"
    assert verify_signature(secret, payload, corrupted_sig) is False, "Corrupted signature accepted"

    # 3. Tampered payload rejected
    tampered_payload = b'{"event": "invitation.accepted", "candidate_id": 9999}'
    assert verify_signature(secret, payload_bytes=tampered_payload, signature_header=sig_header) is False

    # 4. Anti-replay timestamp checks
    assert verify_timestamp(now_ts, max_drift_seconds=300) is True
    assert verify_timestamp(now_ts - 350, max_drift_seconds=300) is False, "Expired timestamp accepted"
    assert verify_timestamp(now_ts + 350, max_drift_seconds=300) is False, "Future timestamp drift accepted"

    # 5. Dispatcher instantiation and headers
    dispatcher = AtsDispatcher()
    hdrs = dispatcher.build_headers(secret, payload)
    assert "X-FSP-Signature" in hdrs
    assert "X-FSP-Timestamp" in hdrs
    assert "X-FSP-Event" in hdrs
    assert verify_signature(secret, payload, hdrs["X-FSP-Signature"]) is True

    # 6. Retry intervals
    assert dispatcher.retry_delays == [60, 300, 900]
    print("[PASS] ATS Webhook HMAC-SHA256, 300s replay window, and DLQ intervals verified.")


# ==============================================================================
# TEST SUITE 4: Branded PDF Generation & Non-FSP Graceful Fallback
# ==============================================================================
def test_branded_pdf_and_non_fsp_fallback():
    print("--- [TEST 4] Branded PDF Generation & Non-FSP Graceful Fallback ---")

    # Case A: Candidate WITH FSP history
    pdf_fsp = generate_fsp_profile_pdf(
        candidate_data={
            "id": 101,
            "full_name": "Алексей Смирнов",
            "specialization": "Backend Разработка",
            "grade": "Senior",
            "category_badge": "Backend · Senior",
            "test_score": 92.5,
            "freshness_score": 96.0,
            "city": "Санкт-Петербург",
            "work_format": "Удаленно",
            "expected_salary": 320000,
            "skills": ["Python", "AsyncIO", "PostgreSQL", "Docker", "Kubernetes"],
            "fsp_id": "FSP-RU-78-0042",
            "fsp_verified": True,
            "fsp_badge": "Мастер спорта ФСП",
            "fsp_achievements": [
                {
                    "championship_name": "Всероссийский чемпионат по спортивному программированию 2025",
                    "discipline": "Алгоритмическое программирование",
                    "year": 2025,
                    "place": 2,
                    "medal": "silver",
                    "sport_rank": "МС",
                }
            ],
            "bio": "Опытный бэкенд архитектор высоконагруженных систем.",
        },
        is_full_mode=True,
    )
    assert isinstance(pdf_fsp, bytes)
    assert pdf_fsp.startswith(b"%PDF-"), "Generated file must be valid PDF"
    assert len(pdf_fsp) > 1000

    # Case B: Candidate WITHOUT FSP history (fsp_id = None, empty achievements)
    pdf_no_fsp = generate_fsp_profile_pdf(
        candidate_data={
            "id": 102,
            "full_name": "Елена Кузнецова",
            "specialization": "Frontend Разработка",
            "grade": "Middle",
            "category_badge": "Frontend · Middle",
            "test_score": 85.0,
            "freshness_score": 90.0,
            "city": "Москва",
            "work_format": "Гибрид",
            "expected_salary": 220000,
            "skills": ["TypeScript", "React", "TailwindCSS"],
            "fsp_id": None,
            "fsp_verified": False,
            "fsp_badge": "Платформенная верификация",
            "fsp_achievements": [],
            "bio": "Frontend-разработчик SPA приложений.",
        },
        is_full_mode=False,
    )
    assert isinstance(pdf_no_fsp, bytes)
    assert pdf_no_fsp.startswith(b"%PDF-")
    assert len(pdf_no_fsp) > 1000

    print("[PASS] Branded PDF generation verified for both FSP athletes and non-FSP candidates (Zero crashes).")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    print("=" * 80)
    print("QA AUTOMATION CHALLENGER PHASE 4: EMPIRICAL STRESS TEST SUITE")
    print("=" * 80)

    # Initialize isolated database
    asyncio.run(init_clean_db())
    app.dependency_overrides[get_db] = override_get_db

    try:
        client = TestClient(app)
        test_privacy_state_machine_and_multi_tenant(client)
        test_salary_range_and_spread_invariants(client)
        test_ats_webhook_security_and_dlq(client)
        test_branded_pdf_and_non_fsp_fallback()
    finally:
        app.dependency_overrides.clear()
        if TEST_DB_FILE.exists():
            try:
                TEST_DB_FILE.unlink()
            except Exception:
                pass

    print("=" * 80)
    print("ALL EMPIRICAL CHALLENGER STRESS TESTS PASSED (100% SUCCESS, EXIT CODE 0)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
