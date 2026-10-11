"""
FSP IT-Talent Platform — Local Offline Keycloak OIDC & FSP Registry Mock Service.
Defined in docs/04 §4.1-4.3 and DISPATCH.md.
Provides Keycloak-compatible OIDC authorization code exchange with PKCE,
athlete registry lookup, achievement synchronization, and graceful fallback for non-FSP candidates.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import secrets
from typing import Any, Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_profiles import CandidateProfile
from app.models.fsp_achievements import FspAchievement

# Mock athlete database in official FSP registry
MOCK_FSP_ATHLETES: Dict[str, Dict[str, Any]] = {
    "FSP-77-01042": {
        "fsp_id": "FSP-77-01042",
        "athlete_name": "Алексей Кузнецов",
        "sport_rank": "kms",
        "rating_points": 1420,
        "achievements": [
            {
                "championship_name": "Чемпионат России по спортивному программированию 2025",
                "discipline": "algorithmic",
                "stage": "всероссийский",
                "year": 2025,
                "place": 2,
                "medal": "silver",
                "sport_rank": "kms",
                "rating_points": 600,
                "certificate_url": "https://fsp-russia.ru/certs/2025-alg-silver-1042.pdf",
            },
            {
                "championship_name": "Кубок Федерации 2024",
                "discipline": "algorithmic",
                "stage": "всероссийский",
                "year": 2024,
                "place": 1,
                "medal": "gold",
                "sport_rank": "kms",
                "rating_points": 820,
                "certificate_url": "https://fsp-russia.ru/certs/2024-alg-gold-1042.pdf",
            },
        ],
    },
    "FSP-78-02091": {
        "fsp_id": "FSP-78-02091",
        "athlete_name": "Мария Соколова",
        "sport_rank": "ms",
        "rating_points": 2150,
        "achievements": [
            {
                "championship_name": "Всероссийский турнир по продуктовому программированию 2025",
                "discipline": "product",
                "stage": "всероссийский",
                "year": 2025,
                "place": 1,
                "medal": "gold",
                "sport_rank": "ms",
                "rating_points": 1100,
                "certificate_url": "https://fsp-russia.ru/certs/2025-prod-gold-2091.pdf",
            },
            {
                "championship_name": "Кубок России по спортивному программированию 2024",
                "discipline": "product",
                "stage": "всероссийский",
                "year": 2024,
                "place": 3,
                "medal": "bronze",
                "sport_rank": "ms",
                "rating_points": 1050,
                "certificate_url": "https://fsp-russia.ru/certs/2024-prod-bronze-2091.pdf",
            },
        ],
    },
    "FSP-16-00315": {
        "fsp_id": "FSP-16-00315",
        "athlete_name": "Тимур Ганиев",
        "sport_rank": "first_class",
        "rating_points": 890,
        "achievements": [
            {
                "championship_name": "Первенство ПФО по информационной безопасности 2025",
                "discipline": "infosec",
                "stage": "всероссийский",
                "year": 2025,
                "place": 3,
                "medal": "bronze",
                "sport_rank": "first_class",
                "rating_points": 450,
                "certificate_url": "https://fsp-russia.ru/certs/2025-sec-bronze-0315.pdf",
            },
            {
                "championship_name": "Открытый кубок по алгоритмическому программированию 2024",
                "discipline": "algorithmic",
                "stage": "региональный",
                "year": 2024,
                "place": 4,
                "medal": "participant",
                "sport_rank": "first_class",
                "rating_points": 440,
                "certificate_url": "https://fsp-russia.ru/certs/2024-alg-part-0315.pdf",
            },
        ],
    },
}

# In-memory auth codes for OIDC flow
_AUTH_CODES: Dict[str, Dict[str, Any]] = {}


def generate_code_challenge(verifier: str) -> str:
    """Generates S256 code challenge from PKCE verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verifies PKCE challenge against code_verifier."""
    expected = generate_code_challenge(code_verifier)
    return secrets.compare_digest(expected, code_challenge)


def create_mock_auth_code(fsp_id: str, code_challenge: str) -> str:
    """Simulates Keycloak authorization endpoint issuing an authorization code."""
    code = f"auth_code_{secrets.token_hex(16)}"
    _AUTH_CODES[code] = {
        "fsp_id": fsp_id,
        "code_challenge": code_challenge,
        "created_at": datetime.now(timezone.utc),
    }
    return code


def exchange_authorization_code(
    code: str,
    code_verifier: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """
    Exchanges authorization code with PKCE verification.
    Returns athlete profile payload from registry.
    """
    auth_data = _AUTH_CODES.get(code)
    if not auth_data:
        raise ValueError("ERR_INVALID_AUTH_CODE: Авторизационный код не найден или истек")

    # Verify PKCE
    if not verify_pkce(code_verifier, auth_data["code_challenge"]):
        raise ValueError("ERR_INVALID_PKCE_VERIFIER: Code verifier does not match challenge")
    fsp_id = auth_data["fsp_id"]

    athlete = MOCK_FSP_ATHLETES.get(fsp_id)
    if not athlete:
        raise ValueError(f"ERR_FSP_ATHLETE_NOT_FOUND: FSP ID '{fsp_id}' not found in registry")

    return athlete


def lookup_athlete(fsp_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Queries official FSP Athlete Registry.
    Returns None if fsp_id is None or unknown (Graceful Fallback).
    """
    if not fsp_id:
        return None
    return MOCK_FSP_ATHLETES.get(fsp_id)


async def sync_candidate_achievements(
    db: AsyncSession,
    candidate: CandidateProfile,
    fsp_id: str,
) -> int:
    """
    Synchronizes achievements from official registry into fsp_achievements table.
    Updates candidate profile verification status.
    """
    athlete = MOCK_FSP_ATHLETES.get(fsp_id)
    if not athlete:
        raise ValueError(f"ERR_ATHLETE_NOT_FOUND: {fsp_id}")

    # Remove previous achievements
    del_stmt = delete(FspAchievement).where(FspAchievement.candidate_profile_id == candidate.id)
    await db.execute(del_stmt)

    # Insert verified achievements
    count = 0
    now = datetime.now(timezone.utc)
    for ach in athlete.get("achievements", []):
        row = FspAchievement(
            candidate_profile_id=candidate.id,
            fsp_id=fsp_id,
            championship_name=ach["championship_name"],
            discipline=ach["discipline"],
            stage=ach.get("stage", "всероссийский"),
            year=ach["year"],
            place=ach.get("place"),
            medal=ach.get("medal"),
            sport_rank=ach.get("sport_rank"),
            rating_points=ach.get("rating_points", 0),
            certificate_url=ach.get("certificate_url"),
            verified_at=now,
            created_at=now,
        )
        db.add(row)
        count += 1

    candidate.fsp_id = fsp_id
    candidate.fsp_verified = True
    await db.commit()
    await db.refresh(candidate)

    return count


async def unlink_candidate_fsp(
    db: AsyncSession,
    candidate: CandidateProfile,
) -> None:
    """
    Unlinks FSP ID and resets candidate to non-FSP general track (Platform verification).
    """
    del_stmt = delete(FspAchievement).where(FspAchievement.candidate_profile_id == candidate.id)
    await db.execute(del_stmt)

    candidate.fsp_id = None
    candidate.fsp_verified = False
    await db.commit()
    await db.refresh(candidate)
