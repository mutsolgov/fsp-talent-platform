"""
FSP IT-Talent Platform — 152-ФЗ Privacy Anonymizer & Multi-Tenant Access Controller.
Defined in docs/02 §5.3-5.4, docs/04 §3, and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.applications import Application
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.invitations import Invitation
from app.models.users import User
from app.models.vacancies import Vacancy


def format_masked_name(first_name: str, last_name: str, candidate_id: int) -> str:
    """
    Formats pseudonymized candidate name per 152-ФЗ: 'Имя Ф. (#C-1042)'.
    """
    initial = f"{last_name[:1]}." if last_name else ""
    name_part = f"{first_name} {initial}".strip()
    return f"{name_part} (#C-{candidate_id})".strip()


def format_full_name(first_name: str, last_name: str, middle_name: Optional[str] = None) -> str:
    """Formats full unmasked name for authorized viewers."""
    parts = [first_name, last_name]
    if middle_name:
        parts.append(middle_name)
    return " ".join(parts).strip()


async def check_contact_access(
    db: AsyncSession,
    candidate_id: int,
    requesting_user: User,
    employer_profile_id: Optional[int] = None,
) -> bool:
    """
    Evaluates whether requesting_user has legitimate access to unmasked contacts:
    1. Admins have system-wide access.
    2. Candidates have access to their own profile.
    3. Employers have access IF AND ONLY IF:
       - Candidate accepted an invitation from this employer (status == 'accepted')
       - Candidate submitted an active application to a vacancy of this employer
    4. Multi-tenant isolation: Unmasking to Employer A never unmasks to Employer B.
    """
    if requesting_user.role == "admin":
        return True

    # Check if candidate viewing their own profile
    if requesting_user.role == "candidate":
        stmt = select(CandidateProfile.id).where(
            CandidateProfile.id == candidate_id,
            CandidateProfile.user_id == requesting_user.id,
        )
        res = await db.execute(stmt)
        if res.scalar_one_or_none() is not None:
            return True
        return False

    # For employers, identify employer_profile_id
    emp_id = employer_profile_id
    if emp_id is None and requesting_user.role == "employer":
        e_stmt = select(EmployerProfile.id).where(EmployerProfile.user_id == requesting_user.id)
        emp_id = (await db.execute(e_stmt)).scalar_one_or_none()

    if not emp_id:
        return False

    # Check 1: Accepted invitation from THIS employer (Multi-tenant check)
    inv_stmt = select(Invitation.id).where(
        Invitation.candidate_profile_id == candidate_id,
        Invitation.employer_profile_id == emp_id,
        Invitation.status == "accepted",
    )
    inv_res = (await db.execute(inv_stmt)).scalar_one_or_none()
    if inv_res is not None:
        return True

    # Check 2: Direct application to a vacancy belonging to THIS employer
    app_stmt = (
        select(Application.id)
        .join(Vacancy, Application.vacancy_id == Vacancy.id)
        .where(
            Application.candidate_profile_id == candidate_id,
            Vacancy.employer_profile_id == emp_id,
            Application.status.in_(["applied", "viewed", "accepted"]),
        )
    )
    app_res = (await db.execute(app_stmt)).scalar_one_or_none()
    if app_res is not None:
        return True

    return False


def mask_candidate_profile(
    candidate: CandidateProfile,
    is_unmasked: bool,
    user_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transforms candidate profile into either masked (152-ФЗ compliant)
    or unmasked view based on verified access permissions.
    """
    if is_unmasked:
        email = user_email
        if email is None and hasattr(candidate, "user") and candidate.user:
            email = candidate.user.email

        return {
            "full_name": format_full_name(candidate.first_name, candidate.last_name, candidate.middle_name),
            "email": email,
            "phone": candidate.phone,
            "telegram": candidate.telegram,
            "github_url": candidate.github_url,
            "raw_resume_pdf_path": candidate.raw_resume_pdf_path,
            "is_contacts_masked": False,
        }
    else:
        return {
            "full_name": format_masked_name(candidate.first_name, candidate.last_name, candidate.id),
            "email": None,
            "phone": None,
            "telegram": None,
            "github_url": None,
            "raw_resume_pdf_path": None,
            "is_contacts_masked": True,
        }
