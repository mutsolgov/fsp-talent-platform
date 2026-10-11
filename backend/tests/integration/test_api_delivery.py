"""
Integration Test Suite for API Modules 13 & 14: Packaging, Benchmark & Delivery.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.13-2.14 and docs/06 §1.3.5.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
import app.models as _models  # noqa: F401
from scripts.seed_reference_data import seed_reference_data

from sqlalchemy import event, text

TEST_DB_URL = "sqlite+aiosqlite:///./test_delivery_integration.db"
test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"timeout": 30},
    echo=False,
)
test_session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
    except Exception:
        pass


async def override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_db_initialized = False


@pytest.fixture
def client():
    global _db_initialized

    async def _setup():
        global _db_initialized
        if not _db_initialized:
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            async with test_session_factory() as session:
                await seed_reference_data(session)
            _db_initialized = True

    asyncio.run(_setup())
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(test_engine.dispose())



# =============================================================================
# MODULE 13: VALIDATION BENCHMARK TESTS
# =============================================================================

def test_validation_benchmark_run(client: TestClient):
    """Test POST /api/v1/validation-benchmark/run and /api/v1/benchmark/run."""
    resp = client.post("/api/v1/validation-benchmark/run", json={"force_recompute": True})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "completed"
    assert data["total_candidates_evaluated"] == 60
    assert data["total_needs_evaluated"] == 15
    assert data["thresholds_passed"] is True
    assert data["summary_ndcg_at_5"] >= 0.85
    assert data["summary_ndcg_at_10"] >= 0.88
    assert data["summary_precision_at_5"] >= 0.80

    # Alias path
    resp_alias = client.post("/api/v1/benchmark/run")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["thresholds_passed"] is True


def test_validation_benchmark_status(client: TestClient):
    """Test GET /api/v1/validation-benchmark/status and /api/v1/benchmark/status."""
    resp = client.get("/api/v1/validation-benchmark/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["progress_percent"] == 100
    assert data["run_id"] is not None

    resp_alias = client.get("/api/v1/benchmark/status")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["status"] == "completed"


def test_validation_benchmark_report(client: TestClient):
    """Test GET /api/v1/validation-benchmark/report and /api/v1/benchmark/report."""
    resp = client.get("/api/v1/validation-benchmark/report")
    assert resp.status_code == 200
    data = resp.json()
    assert data["all_thresholds_passed"] is True
    assert "mean_ndcg_5" in data["metrics"]
    assert "mean_ndcg_10" in data["metrics"]
    assert "mean_p_5" in data["metrics"]
    assert "test_retest_r" in data["metrics"]
    assert "kelley_d" in data["metrics"]
    assert "leak_index" in data["metrics"]
    assert len(data["thresholds_comparison"]) == 6
    assert len(data["needs_breakdown"]) == 15

    # Check each comparison
    for comp in data["thresholds_comparison"]:
        assert comp["passed"] is True

    # Alias path
    resp_alias = client.get("/api/v1/benchmark/report")
    assert resp_alias.status_code == 200
    assert resp_alias.json()["all_thresholds_passed"] is True


def test_validation_benchmark_chart_data(client: TestClient):
    """Test GET /api/v1/validation-benchmark/chart-data and /api/v1/benchmark/chart-data."""
    resp = client.get("/api/v1/validation-benchmark/chart-data")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["radar_chart_series"]) == 6
    assert len(data["ndcg_by_need_bars"]) == 15
    assert len(data["scatter_test_retest"]) == 30

    resp_alias = client.get("/api/v1/benchmark/chart-data")
    assert resp_alias.status_code == 200
    assert len(resp_alias.json()["radar_chart_series"]) == 6


# =============================================================================
# MODULE 14: DEMO DASHBOARD TESTS
# =============================================================================

def test_demo_switch_role_candidate_with_fsp(client: TestClient):
    """Test POST /api/v1/demo/switch-role for candidate_with_fsp."""
    resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "candidate"
    assert "ФСП ID" in data["persona_title"]
    assert len(data["recommended_tour_steps"]) > 0


def test_demo_switch_role_candidate_without_fsp(client: TestClient):
    """Test POST /api/v1/demo/switch-role for candidate_without_fsp."""
    resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_without_fsp"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "candidate"
    assert "без истории ФСП" in data["persona_title"]


def test_demo_switch_role_employer(client: TestClient):
    """Test POST /api/v1/demo/switch-role for employer."""
    resp = client.post("/api/v1/demo/switch-role", json={"role": "employer"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "employer"


def test_demo_switch_role_admin(client: TestClient):
    """Test POST /api/v1/demo/switch-role for admin."""
    resp = client.post("/api/v1/demo/switch-role", json={"role": "admin"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"


def test_demo_seed_dataset(client: TestClient):
    """Test POST /api/v1/demo/seed."""
    resp = client.post("/api/v1/demo/seed", json={"reset_database": False, "seed_golden_dataset": True})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["seeded_candidates_count"] == 60
    assert data["seeded_needs_count"] == 15
    assert data["elapsed_ms"] >= 0.0


def test_demo_reset_cooldown(client: TestClient):
    """Test POST /api/v1/demo/reset-cooldown/{candidate_id}."""
    # First switch role to create candidate
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    cand_profile_id = c_resp.json()["profile_id"]

    resp = client.post(
        f"/api/v1/demo/reset-cooldown/{cand_profile_id}",
        json={"reason": "Jury demonstration test bypass"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["candidate_id"] == cand_profile_id
    assert data["cooldown_cleared"] is True
    assert data["is_demo_bypass"] is True
    assert "cooldown_reset_log_id" in data


def test_demo_metrics(client: TestClient):
    """Test GET /api/v1/demo/metrics."""
    resp = client.get("/api/v1/demo/metrics")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["system_status"] == "operational"
    assert data["total_candidates"] >= 0
    assert data["active_employer_needs"] >= 0
    assert data["system_uptime_hours"] > 0


def test_resume_pdf_endpoints_and_privacy(client: TestClient):
    """Test PDF profile generation, export, and 152-ФЗ contact privacy barrier."""
    # 1. Switch to candidate and seed profile
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200
    cand_token = c_resp.json()["access_token"]
    cand_id = c_resp.json()["profile_id"]

    # 2. Candidate self-preview
    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    prev_resp = client.get("/api/v1/resume-pdf/preview-export", headers=cand_headers)
    assert prev_resp.status_code == 200
    assert prev_resp.headers["content-type"] == "application/pdf"
    assert prev_resp.content.startswith(b"%PDF-")

    # 3. Anonymized PDF (Mode A) download
    anon_resp = client.get(f"/api/v1/resume-pdf/{cand_id}/anonymized", headers=cand_headers)
    assert anon_resp.status_code == 200
    assert anon_resp.headers["content-type"] == "application/pdf"
    assert anon_resp.content.startswith(b"%PDF-")

    # 4. Standardized export-fsp endpoint (auto / mode_a)
    exp_resp = client.get(f"/api/v1/resume-pdf/export-fsp/{cand_id}?mode=mode_a_anonymized", headers=cand_headers)
    assert exp_resp.status_code == 200
    assert exp_resp.headers["content-type"] == "application/pdf"
    assert exp_resp.content.startswith(b"%PDF-")

    # 5. Switch to employer (who has NOT sent an accepted invitation yet)
    emp_resp = client.post("/api/v1/demo/switch-role", json={"role": "employer"})
    emp_token = emp_resp.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Employer gets 403 on full unmasked PDF due to 152-ФЗ barrier
    full_resp = client.get(f"/api/v1/resume-pdf/{cand_id}/full", headers=emp_headers)
    assert full_resp.status_code == 403
    assert "152-ФЗ" in full_resp.json()["detail"]

    # Employer CAN download Mode A anonymized PDF
    emp_anon_resp = client.get(f"/api/v1/resume-pdf/{cand_id}/anonymized", headers=emp_headers)
    assert emp_anon_resp.status_code == 200
    assert emp_anon_resp.content.startswith(b"%PDF-")

    # Admin has authorized access to full PDF
    admin_resp = client.post("/api/v1/demo/switch-role", json={"role": "admin"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_full_resp = client.get(f"/api/v1/resume-pdf/{cand_id}/full", headers=admin_headers)
    assert admin_full_resp.status_code == 200
    assert admin_full_resp.content.startswith(b"%PDF-")


def test_micro_challenges_put_and_delete(client: TestClient):
    """Test PUT and DELETE /api/v1/micro-challenges/{id}."""
    # Switch to employer
    emp_resp = client.post("/api/v1/demo/switch-role", json={"role": "employer"})
    emp_token = emp_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {emp_token}"}

    # Create challenge
    create_payload = {
        "specialization_id": 1,
        "grade_id": 2,
        "title": "High-Throughput Redis Token Bucket Rate Limiter",
        "description_markdown": "Реализуйте алгоритм rate limiting с использованием Redis Lua scripts.",
        "starter_code": "def rate_limit(user_id: str) -> bool:\n    pass",
        "test_cases": [{"input": "user1", "expected": True, "is_public": True}],
        "time_limit_ms": 1500,
        "points": 35,
    }
    c_resp = client.post("/api/v1/micro-challenges", json=create_payload, headers=headers)
    assert c_resp.status_code == 201
    ch_id = c_resp.json()["id"]

    # PUT update challenge
    update_payload = {
        "title": "Updated Redis Token Bucket Rate Limiter v2",
        "time_limit_ms": 2500,
    }
    put_resp = client.put(f"/api/v1/micro-challenges/{ch_id}", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["title"] == "Updated Redis Token Bucket Rate Limiter v2"
    assert put_resp.json()["time_limit_ms"] == 2500

    # DELETE challenge
    del_resp = client.delete(f"/api/v1/micro-challenges/{ch_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "ok"


# =============================================================================
# FLEXIBLE AUTH FOR PDF RESUME DELIVERY TESTS
# =============================================================================

def test_resume_pdf_flexible_auth_bearer(client: TestClient):
    """Test PDF export with valid Authorization Bearer header -> 200."""
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200
    cand_token = c_resp.json()["access_token"]
    cand_id = c_resp.json()["profile_id"]

    headers = {"Authorization": f"Bearer {cand_token}"}
    resp = client.get(f"/api/v1/resume-pdf/export-fsp/{cand_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF-")


def test_resume_pdf_flexible_auth_query_token(client: TestClient):
    """Test PDF export with valid ?token query param -> 200."""
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200
    cand_token = c_resp.json()["access_token"]
    cand_id = c_resp.json()["profile_id"]

    # 1. export-fsp with query param token
    resp_exp = client.get(f"/api/v1/resume-pdf/export-fsp/{cand_id}?token={cand_token}")
    assert resp_exp.status_code == 200
    assert resp_exp.headers["content-type"] == "application/pdf"
    assert resp_exp.content.startswith(b"%PDF-")

    # 2. anonymized with query param token
    resp_anon = client.get(f"/api/v1/resume-pdf/{cand_id}/anonymized?token={cand_token}")
    assert resp_anon.status_code == 200
    assert resp_anon.content.startswith(b"%PDF-")

    # 3. preview-export with query param token
    resp_prev = client.get(f"/api/v1/resume-pdf/preview-export?token={cand_token}")
    assert resp_prev.status_code == 200
    assert resp_prev.content.startswith(b"%PDF-")


def test_resume_pdf_flexible_auth_demo_bypass(client: TestClient):
    """Test PDF export without token when DEMO_BYPASS_ENABLED=True -> 200."""
    # Ensure profile exists
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200
    cand_id = c_resp.json()["profile_id"]

    orig = settings.DEMO_BYPASS_ENABLED
    try:
        settings.DEMO_BYPASS_ENABLED = True

        # Calling without any Authorization header or query token
        resp_exp = client.get(f"/api/v1/resume-pdf/export-fsp/{cand_id}")
        assert resp_exp.status_code == 200
        assert resp_exp.headers["content-type"] == "application/pdf"
        assert resp_exp.content.startswith(b"%PDF-")

        resp_anon = client.get(f"/api/v1/resume-pdf/{cand_id}/anonymized")
        assert resp_anon.status_code == 200
        assert resp_anon.content.startswith(b"%PDF-")
    finally:
        settings.DEMO_BYPASS_ENABLED = orig


def test_resume_pdf_flexible_auth_invalid_token_never_falls_back_to_demo(client: TestClient):
    """Test PDF export with invalid token -> 401 (must NEVER fall back to demo mode)."""
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200
    cand_id = c_resp.json()["profile_id"]

    orig = settings.DEMO_BYPASS_ENABLED
    try:
        # Even when DEMO_BYPASS_ENABLED is True, invalid token must return 401
        settings.DEMO_BYPASS_ENABLED = True

        # 1. Invalid Bearer header
        resp_bad_header = client.get(
            f"/api/v1/resume-pdf/export-fsp/{cand_id}",
            headers={"Authorization": "Bearer malformed.invalid.token"},
        )
        assert resp_bad_header.status_code == 401
        assert any(k.lower() == "www-authenticate" for k in resp_bad_header.headers)

        # 2. Invalid query parameter token
        resp_bad_query = client.get(
            f"/api/v1/resume-pdf/export-fsp/{cand_id}?token=malformed_token_12345"
        )
        assert resp_bad_query.status_code == 401
        assert any(k.lower() == "www-authenticate" for k in resp_bad_query.headers)

        # 3. When DEMO_BYPASS_ENABLED is False, no token at all also returns 401
        settings.DEMO_BYPASS_ENABLED = False
        resp_no_token = client.get(f"/api/v1/resume-pdf/export-fsp/{cand_id}")
        assert resp_no_token.status_code == 401
        assert any(k.lower() == "www-authenticate" for k in resp_no_token.headers)
    finally:
        settings.DEMO_BYPASS_ENABLED = orig


def test_resume_pdf_flexible_auth_mode_b_full_152_fz_privacy_barrier(client: TestClient):
    """Test Mode B /full without contact access -> 403 (verifying 152-ФЗ check remains active)."""
    # 1. Setup candidate
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200
    cand_id = c_resp.json()["profile_id"]

    # 2. Setup employer who has not sent accepted invitation
    emp_resp = client.post("/api/v1/demo/switch-role", json={"role": "employer"})
    assert emp_resp.status_code == 200
    emp_token = emp_resp.json()["access_token"]

    # 2a. Employer accesses full PDF via Bearer header -> 403
    resp_full_header = client.get(
        f"/api/v1/resume-pdf/{cand_id}/full",
        headers={"Authorization": f"Bearer {emp_token}"},
    )
    assert resp_full_header.status_code == 403
    assert "152-ФЗ" in resp_full_header.json()["detail"]

    # 2b. Employer accesses full PDF via query token -> 403
    resp_full_query = client.get(
        f"/api/v1/resume-pdf/{cand_id}/full?token={emp_token}"
    )
    assert resp_full_query.status_code == 403
    assert "152-ФЗ" in resp_full_query.json()["detail"]

    # 2c. Employer accesses export-fsp with mode_b_full via query token -> 403
    resp_exp_b = client.get(
        f"/api/v1/resume-pdf/export-fsp/{cand_id}?mode=mode_b_full&token={emp_token}"
    )
    assert resp_exp_b.status_code == 403
    assert "152-ФЗ" in resp_exp_b.json()["detail"]

