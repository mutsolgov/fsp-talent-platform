"""
FSP IT-Talent Platform — Database Models Registry (All 25 Models).
"""
from app.models.base import Base, TimestampMixin, JSON_TYPE
from app.models.users import User
from app.models.user_consents import UserConsent
from app.models.audit_logs import AuditLog
from app.models.specializations import Specialization
from app.models.grades import Grade
from app.models.categories import Category
from app.models.skills import Skill

# Phase 2 Models (Assessment Layer)
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_skills import CandidateSkill
from app.models.canonical_item_families import CanonicalItemFamily
from app.models.assessment_sessions import AssessmentSession
from app.models.assessment_answers import AssessmentAnswer
from app.models.cooldown_resets import CooldownReset
from app.models.micro_challenges import MicroChallenge
from app.models.challenge_submissions import ChallengeSubmission

# Phase 3 Models (Matching Layer)
from app.models.employer_profiles import EmployerProfile
from app.models.employer_needs import EmployerNeed
from app.models.candidate_categorizations import CandidateCategorization
from app.models.saved_shortlists import SavedShortlist
from app.models.shortlist_items import ShortlistItem

# Phase 4 Models (Security & Integration Layer)
from app.models.fsp_achievements import FspAchievement
from app.models.vacancies import Vacancy
from app.models.invitations import Invitation
from app.models.applications import Application
from app.models.ats_integrations import AtsIntegration

__all__ = [
    "Base",
    "TimestampMixin",
    "JSON_TYPE",
    "User",
    "UserConsent",
    "AuditLog",
    "Specialization",
    "Grade",
    "Category",
    "Skill",
    "CandidateProfile",
    "CandidateSkill",
    "CanonicalItemFamily",
    "AssessmentSession",
    "AssessmentAnswer",
    "CooldownReset",
    "MicroChallenge",
    "ChallengeSubmission",
    "EmployerProfile",
    "EmployerNeed",
    "CandidateCategorization",
    "SavedShortlist",
    "ShortlistItem",
    "FspAchievement",
    "Vacancy",
    "Invitation",
    "Application",
    "AtsIntegration",
]
