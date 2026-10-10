"""
FSP IT-Talent Platform — Resume PDF Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.4.
"""
from __future__ import annotations

from enum import StrEnum
from typing import List, Optional
from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class ExportModeEnum(StrEnum):
    AUTO = "auto"
    MODE_A_ANONYMIZED = "mode_a_anonymized"
    MODE_B_FULL = "mode_b_full"


class ParsedWorkExperience(BaseSchema):
    company_name: str
    position: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    skills_detected: List[str] = Field(default_factory=list)


class ParsedEducation(BaseSchema):
    institution: str
    faculty: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None


class ResumeParsedResponse(BaseSchema):
    detected_first_name: Optional[str] = None
    detected_last_name: Optional[str] = None
    detected_email: Optional[EmailStr] = None
    detected_phone: Optional[str] = None
    detected_telegram: Optional[str] = None
    detected_github: Optional[str] = None
    detected_city: Optional[str] = None
    extracted_skills: List[str] = Field(default_factory=list)
    detected_skills: List[str] = Field(default_factory=list)
    work_experience: List[ParsedWorkExperience] = Field(default_factory=list)
    education: List[ParsedEducation] = Field(default_factory=list)
    total_experience_months: int = 0
    raw_text_length: int
