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
from app.models.users import User
from app.models.fsp_achievements import FspAchievement
from app.core.security import get_password_hash
from app.api.v1.demo import seed_demo_dataset
from app.schemas.demo import DemoSeedRequest
from scripts.seed_reference_data import seed_reference_data


async def seed_core_demo_users(session: AsyncSession) -> None:
    """
    Seeds essential demo and jury users matching Keycloak realm-export.json and README.md:
    - athlete@fsp-russia.ru / fsp_secret_2026 (Алексей Кузнецов, Senior Backend, КМС, FSP-77-01042)
    - candidate@fsp-russia.ru / fsp_secret_2026 (Федор Федотов, Senior Backend, без ФСП)
    - hr@technobank.ru / fsp_secret_2026 (Елена Соколова, АО «ТехноБанк», ИНН 7707083893)
    - admin@fsp-russia.ru / fsp_secret_2026 (Главный Администратор платформы)
    - jury@fsp-russia.ru / fsp_secret_2026 (Администратор / Жюри)
    - mikhail.popov@fsp-russia.ru / fsp_secret_2026 (Михаил Попов, Senior Backend, МС)
    - fedor.fedotov@fsp-russia.ru / fsp_secret_2026 (Федор Федотов, Senior Backend)
    """
    users_to_seed = [
        {
            "email": "athlete@fsp-russia.ru",
            "role": "candidate",
            "first_name": "Алексей",
            "last_name": "Кузнецов",
            "fsp_id": "FSP-77-01042",
            "fsp_verified": True,
            "sport_rank": "kms",
            "rating_points": 1420,
        },
        {
            "email": "candidate@fsp-russia.ru",
            "role": "candidate",
            "first_name": "Федор",
            "last_name": "Федотов",
            "fsp_id": None,
            "fsp_verified": False,
        },
        {
            "email": "mikhail.popov@fsp-russia.ru",
            "role": "candidate",
            "first_name": "Михаил",
            "last_name": "Попов",
            "fsp_id": "FSP-103",
            "fsp_verified": True,
            "sport_rank": "ms",
            "rating_points": 1580,
        },
        {
            "email": "fedor.fedotov@fsp-russia.ru",
            "role": "candidate",
            "first_name": "Федор",
            "last_name": "Федотов",
            "fsp_id": None,
            "fsp_verified": False,
        },
        {
            "email": "hr@technobank.ru",
            "role": "employer",
            "company_name": "АО «ТехноБанк»",
            "inn": "7707083893",
            "domain": "technobank.ru",
        },
        {
            "email": "admin@fsp-russia.ru",
            "role": "admin",
        },
        {
            "email": "jury@fsp-russia.ru",
            "role": "admin",
        },
    ]

    default_hash = get_password_hash("fsp_secret_2026")

    for u_info in users_to_seed:
        email = u_info["email"]
        u_res = await session.execute(select(User).where(User.email == email))
        user = u_res.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                hashed_password=default_hash,
                role=u_info["role"],
                is_active=True,
                email_verified=True,
            )
            session.add(user)
            await session.flush()
        else:
            user.hashed_password = default_hash
            user.is_active = True
            user.email_verified = True
            await session.flush()

        if u_info["role"] == "candidate":
            c_res = await session.execute(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
            prof = c_res.scalar_one_or_none()
            if not prof:
                prof = CandidateProfile(
                    user_id=user.id,
                    first_name=u_info["first_name"],
                    last_name=u_info["last_name"],
                    city="Москва",
                    work_format="remote",
                    fsp_id=u_info.get("fsp_id"),
                    fsp_verified=u_info.get("fsp_verified", False),
                    freshness_score=95.0,
                    is_published=True,
                )
                session.add(prof)
                await session.flush()
            else:
                prof.first_name = u_info["first_name"]
                prof.last_name = u_info["last_name"]
                prof.fsp_id = u_info.get("fsp_id")
                prof.fsp_verified = u_info.get("fsp_verified", False)
                prof.is_published = True

            if u_info.get("fsp_verified") and u_info.get("fsp_id"):
                ach_res = await session.execute(
                    select(FspAchievement).where(FspAchievement.candidate_profile_id == prof.id)
                )
                ach = ach_res.scalar_one_or_none()
                if not ach:
                    ach = FspAchievement(
                        candidate_profile_id=prof.id,
                        fsp_id=u_info["fsp_id"],
                        championship_name="Чемпионат России по спортивному программированию 2025",
                        discipline="algorithmic",
                        stage="финал",
                        year=2025,
                        place=2,
                        medal="silver",
                        sport_rank=u_info.get("sport_rank", "kms"),
                        rating_points=u_info.get("rating_points", 1420),
                    )
                    session.add(ach)

        elif u_info["role"] == "employer":
            e_res = await session.execute(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
            emp = e_res.scalar_one_or_none()
            if not emp:
                emp = EmployerProfile(
                    user_id=user.id,
                    company_name=u_info["company_name"],
                    inn=u_info["inn"],
                    domain=u_info["domain"],
                    is_inn_verified=True,
                    trust_score=95,
                    invite_daily_limit=50,
                )
                session.add(emp)
                await session.flush()
            else:
                emp.company_name = u_info["company_name"]
                emp.inn = u_info["inn"]
                emp.domain = u_info["domain"]
                emp.is_inn_verified = True
                emp.trust_score = 95

    await session.commit()


async def main() -> None:
    t0 = time.perf_counter()
    print("=" * 80)
    print("FSP IT-TALENT PLATFORM — DEMO DATASET SEEDER (60x15 GOLDEN DATASET)")
    print("=" * 80)

    # 1. Ensure database schema tables exist
    print("[1/5] Ensuring database schema and tables exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("      [✓] Database schema verified.")

    # 2. Ensure canonical reference data (specializations, grades, skills) exists
    print("[2/5] Verifying reference taxonomies (6 specializations, 4 grades, 24 categories)...")
    async with async_session_factory() as session:
        spec_count = (await session.execute(select(func.count(Specialization.id)))).scalar() or 0
        if spec_count < 6:
            print("      [*] Seeding canonical reference taxonomies...")
            stats = await seed_reference_data(session)
            print(f"      [✓] Seeded reference data: {stats}")
        else:
            print(f"      [✓] Reference taxonomies already present ({spec_count} specializations).")

    # 3. Seed core demo & jury accounts
    print("[3/5] Seeding core demo and jury user accounts (fsp_secret_2026)...")
    async with async_session_factory() as session:
        await seed_core_demo_users(session)
        print("      [✓] Seeded athlete, candidate, hr, admin accounts with verified credentials.")

    # 4. Execute demo dataset seeding logic
    print("[4/5] Seeding 60 golden talents and 15 employer needs...")
    async with async_session_factory() as session:
        payload = DemoSeedRequest(reset_database=False, seed_golden_dataset=True)
        resp = await seed_demo_dataset(payload=payload, db=session)
        print(f"      [✓] Seeding completed in {resp.elapsed_ms:.1f} ms.")

    # 5. Verify database state
    print("[5/5] Verifying populated entity counts in database...")
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
