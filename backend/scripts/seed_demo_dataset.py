#!/usr/bin/env python3
"""
FSP IT-Talent Platform — Standalone Synthetic Dataset Seeder CLI.
Seeds:
- 60 Golden Candidates (30 FSP, 30 non-FSP balanced across 6 specializations and 4 grades)
- 1 Employer Profile (ООО «ФСП Инновации», ИНН 7710140679)
- 15 Employer Needs with verified RUB salary ranges
- 5 Published Vacancies
- Demo Invitations (including status='accepted' for 152-FZ contact unmasking)

Usage:
    python3 scripts/seed_demo_dataset.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Add both host backend and container app directories to sys.path
_SCRIPTS_DIR = Path(__file__).resolve().parent
_CONTAINER_APP = _SCRIPTS_DIR.parent
_HOST_BACKEND = _SCRIPTS_DIR.parent / "backend"

for p in (_CONTAINER_APP, _HOST_BACKEND, _SCRIPTS_DIR):
    if str(p) not in sys.path and p.exists():
        sys.path.insert(0, str(p))

from sqlalchemy import func, select
from app.database import async_session_factory, engine
from app.models.base import Base
import app.models as _models  # noqa: F401
from app.models.specializations import Specialization
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.employer_needs import EmployerNeed
from app.models.vacancies import Vacancy
from app.models.invitations import Invitation
from app.api.v1.demo import seed_demo_dataset
from app.schemas.demo import DemoSeedRequest
from scripts.seed_reference_data import seed_reference_data


async def main() -> None:
    t0 = time.perf_counter()
    print("=" * 80)
    print("FSP IT-TALENT PLATFORM — DEMO DATASET SEEDER (60x15 GOLDEN DATASET)")
    print("=" * 80)

    # 1. Ensure database schema tables exist
    print("[1/4] Ensuring database schema and tables exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("      [✓] Database schema verified.")

    # 2. Ensure canonical reference data (specializations, grades, skills) exists
    print("[2/4] Verifying reference taxonomies (6 specializations, 4 grades, 24 categories)...")
    async with async_session_factory() as session:
        spec_count = (await session.execute(select(func.count(Specialization.id)))).scalar() or 0
        if spec_count < 6:
            print("      [*] Seeding canonical reference taxonomies...")
            stats = await seed_reference_data(session)
            print(f"      [✓] Seeded reference data: {stats}")
        else:
            print(f"      [✓] Reference taxonomies already present ({spec_count} specializations).")

    # 3. Execute demo dataset seeding logic
    print("[3/4] Seeding 60 golden talents and 15 employer needs...")
    async with async_session_factory() as session:
        payload = DemoSeedRequest(reset_database=False, seed_golden_dataset=True)
        resp = await seed_demo_dataset(payload=payload, db=session)
        print(f"      [✓] Seeding completed in {resp.elapsed_ms:.1f} ms.")

    # 4. Verify database state
    print("[4/4] Verifying populated entity counts in database...")
    async with async_session_factory() as session:
        cand_total = (await session.execute(select(func.count(CandidateProfile.id)))).scalar() or 0
        cand_fsp = (
            await session.execute(
                select(func.count(CandidateProfile.id)).where(CandidateProfile.fsp_verified.is_(True))
            )
        ).scalar() or 0
        cand_non_fsp = (
            await session.execute(
                select(func.count(CandidateProfile.id)).where(
                    (CandidateProfile.fsp_verified.is_(False)) | (CandidateProfile.fsp_id.is_(None))
                )
            )
        ).scalar() or 0
        emp_total = (await session.execute(select(func.count(EmployerProfile.id)))).scalar() or 0
        needs_total = (await session.execute(select(func.count(EmployerNeed.id)))).scalar() or 0
        vac_total = (await session.execute(select(func.count(Vacancy.id)))).scalar() or 0
        inv_total = (await session.execute(select(func.count(Invitation.id)))).scalar() or 0

    print("-" * 80)
    print(f"  • Total Candidates:        {cand_total:>3}  (Target: >= 60)")
    print(f"    - With Verified FSP ID:  {cand_fsp:>3}  (Target: >= 30)")
    print(f"    - Without FSP (Parity):  {cand_non_fsp:>3}  (Target: >= 30)")
    print(f"  • Employer Profiles:       {emp_total:>3}  (Target: >= 1)")
    print(f"  • Active Employer Needs:   {needs_total:>3}  (Target: >= 15)")
    print(f"  • Published Vacancies:     {vac_total:>3}  (Target: >= 5)")
    print(f"  • Test Invitations:        {inv_total:>3}  (Target: >= 1)")
    print("-" * 80)

    assert cand_total >= 60, f"Expected >= 60 candidates, got {cand_total}"
    assert cand_fsp >= 30, f"Expected >= 30 FSP candidates, got {cand_fsp}"
    assert cand_non_fsp >= 30, f"Expected >= 30 non-FSP candidates, got {cand_non_fsp}"
    assert emp_total >= 1, f"Expected >= 1 employer profile, got {emp_total}"
    assert needs_total >= 15, f"Expected >= 15 employer needs, got {needs_total}"
    assert vac_total >= 1, f"Expected >= 1 vacancies, got {vac_total}"
    assert inv_total >= 1, f"Expected >= 1 invitations, got {inv_total}"

    total_time = round(time.perf_counter() - t0, 3)
    print(f"[SUCCESS] Demo dataset successfully seeded & verified in {total_time}s.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
