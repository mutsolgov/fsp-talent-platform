"""
FSP IT-Talent Platform — Candidate Bank & Shortlist Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.8.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import ConfigDict, EmailStr, Field

from app.schemas.base import BaseSchema, PaginationMeta


class WeightBreakdown(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    is_fsp_profile: bool = Field(..., description="Флаг верифицированного профиля ФСП")
    w_test: float = Field(ge=0.0, le=1.0)
    w_stack: float = Field(ge=0.0, le=1.0)
    w_fsp: float = Field(ge=0.0, le=1.0)
    w_freshness: float = Field(ge=0.0, le=1.0)
    sum_weights: float = Field(ge=0.99, le=1.01)


class ComponentScores(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    test_score: float = Field(ge=0.0, le=100.0)
    stack_score: float = Field(ge=0.0, le=100.0)
    fsp_score: float = Field(ge=0.0, le=100.0)
    freshness_score: float = Field(ge=0.0, le=100.0)
    weights_applied: WeightBreakdown


class ExplainabilityObject(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    match_percentage: float = Field(ge=0.0, le=100.0, description="Итоговый скор соответствия S")
    overall_score: float = Field(ge=0.0, le=100.0)
    component_scores: ComponentScores
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    radar_series: List[Dict[str, Any]] = Field(default_factory=list)
    fsp_bonus_explanation: str = ""
    freshness_activity: str = ""
    recommendation_badge: str = "Potential Fit"
    human_summary_ru: str = Field(..., description="Естественно-языковое текстовое обоснование на русском")


class CandidateBankCard(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    user_id: int
    masked_full_name: str = Field(..., description="Псевдонимизированное ФИО: 'Алексей К. (#C-1042)'")
    specialization: str
    grade: str
    category_code: str
    category_badge: str
    test_score: float
    freshness_score: float
    city: Optional[str] = None
    work_format: Optional[str] = None
    relocation_ready: bool
    expected_salary: Optional[int] = None
    fsp_id: Optional[str] = None
    fsp_verified: bool
    fsp_badge: str
    skills: List[str] = Field(default_factory=list)
    match_score: Optional[float] = None
    explainability: Optional[Dict[str, Any]] = None
    invitation_status: Optional[str] = None
    is_contacts_unmasked: bool = False
    created_at: datetime


class CandidateBankSearchResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    items: List[CandidateBankCard]
    meta: PaginationMeta
    filter_echo: Dict[str, Any] = Field(default_factory=dict)


class CandidateAnonymizedDetailResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    user_id: int
    masked_full_name: str
    specialization: str
    grade: str
    category_title: str
    bio: Optional[str] = None
    city: Optional[str] = None
    work_format: Optional[str] = None
    relocation_ready: bool
    expected_salary: Optional[int] = None
    skills: List[str] = Field(default_factory=list)
    test_score: float
    freshness_score: float
    fsp_id: Optional[str] = None
    fsp_verified: bool
    fsp_badge: str
    fsp_achievements: List[Dict[str, Any]] = Field(default_factory=list)
    anonymized_pdf_url: Optional[str] = None
    is_contacts_masked: bool = True
    # Поля контактов (152-ФЗ) — передаются только при наличии согласия/акцепта
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    github_url: Optional[str] = None
    raw_resume_pdf_url: Optional[str] = None
    explainability: Optional[Dict[str, Any]] = None
    created_at: datetime


class CandidateUnmaskedContactsResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    candidate_id: int
    full_name: str = Field(..., description="Полное ФИО соискателя")
    email: EmailStr
    phone: Optional[str] = None
    telegram: Optional[str] = None
    github_url: Optional[str] = None
    raw_resume_pdf_url: Optional[str] = None
    full_pdf_url: Optional[str] = None
    unmasked_reason: str = "invitation_accepted"
    unmasked_at: datetime


class CategoryCatalogItem(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    specialization_code: str
    specialization_title: str
    grade_code: str
    grade_title: str
    category_code: str
    category_title: str
    verified_candidates_count: int = 0


class CreateShortlistRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    title: str = Field(..., min_length=2, max_length=200)
    need_id: Optional[int] = None
    filter_criteria_json: Dict[str, Any] = Field(default_factory=dict)
    candidate_ids: List[int] = Field(default_factory=list)


class ShortlistItemResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    shortlist_id: int
    candidate_profile_id: int
    is_pinned: bool
    match_score: float
    delta_score: float = 0.0
    rank_position: int
    explainability: Optional[Dict[str, Any]] = None
    candidate_card: Optional[CandidateBankCard] = None


class SavedShortlistDetailResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    employer_profile_id: int
    need_id: Optional[int] = None
    title: str
    filter_criteria_json: Dict[str, Any] = Field(default_factory=dict)
    pinned_count: int = 0
    items: List[ShortlistItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SavedShortlistSummaryResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    title: str
    need_id: Optional[int] = None
    candidates_count: int = 0
    pinned_count: int = 0
    created_at: datetime


class PinCandidateRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    candidate_profile_id: Optional[int] = None
    is_pinned: bool = True


class RefineShortlistRequest(BaseSchema):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    new_filter_criteria_json: Dict[str, Any] = Field(default_factory=dict)
    refined_need_id: Optional[int] = None
