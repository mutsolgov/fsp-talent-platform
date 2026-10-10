"""
Integration Tests for Phase 6 Worker 1 additions:
- DemoResetCooldownRequest with is_demo_bypass flag
- Candidate profile lookup fallback (id first, then user_id)
- Benchmark status by job_id (/validation-benchmark/status/{job_id} and /benchmark/status/{job_id})
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
from sqlalchemy import event, text
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.base import Base
import app.models as _models  # noqa: F401
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_phase6_worker1.db"
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


def test_demo_reset_cooldown_with_is_demo_bypass_payload(client: TestClient):
    """Test POST /api/v1/demo/reset-cooldown/{candidate_id} accepts { 'is_demo_bypass': true }."""
    # Switch to candidate role
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200, c_resp.text
    cand_profile_id = c_resp.json()["profile_id"]

    # Call reset cooldown with only is_demo_bypass
    resp = client.post(
        f"/api/v1/demo/reset-cooldown/{cand_profile_id}",
        json={"is_demo_bypass": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["candidate_id"] == cand_profile_id
    assert data["cooldown_cleared"] is True
    assert data["is_demo_bypass"] is True


def test_demo_reset_cooldown_with_both_reason_and_bypass(client: TestClient):
    """Test POST /api/v1/demo/reset-cooldown/{candidate_id} accepts both reason and is_demo_bypass."""
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_without_fsp"})
    assert c_resp.status_code == 200, c_resp.text
    cand_profile_id = c_resp.json()["profile_id"]

    resp = client.post(
        f"/api/v1/demo/reset-cooldown/{cand_profile_id}",
        json={"reason": "Jury evaluation live test", "is_demo_bypass": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["candidate_id"] == cand_profile_id
    assert data["cooldown_cleared"] is True
    assert data["is_demo_bypass"] is True


def test_demo_reset_cooldown_user_id_fallback(client: TestClient):
    """Test POST /api/v1/demo/reset-cooldown works when querying by user_id."""
    c_resp = client.post("/api/v1/demo/switch-role", json={"role": "candidate_with_fsp"})
    assert c_resp.status_code == 200, c_resp.text
    user_id = c_resp.json()["user_id"]

    resp = client.post(
        f"/api/v1/demo/reset-cooldown/{user_id}",
        json={"is_demo_bypass": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["cooldown_cleared"] is True
    assert data["is_demo_bypass"] is True


def test_validation_benchmark_status_by_job_id(client: TestClient):
    """Test GET /api/v1/validation-benchmark/status/{job_id} and /api/v1/benchmark/status/{job_id}."""
    resp = client.get("/api/v1/validation-benchmark/status/job_alpha_99")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["run_id"] == "job_alpha_99"
    assert data["status"] == "completed"
    assert data["progress_percent"] == 100

    resp_alias = client.get("/api/v1/benchmark/status/job_beta_100")
    assert resp_alias.status_code == 200, resp_alias.text
    data_alias = resp_alias.json()
    assert data_alias["run_id"] == "job_beta_100"
    assert data_alias["status"] == "completed"
