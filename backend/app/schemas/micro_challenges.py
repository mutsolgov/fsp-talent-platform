"""
FSP IT-Talent Platform — Micro Challenges Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.6.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field, model_validator

from app.schemas.base import BaseSchema, PaginationMeta


class SubmissionStatusEnum(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"


class TestCaseItem(BaseSchema):
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    input: Optional[Any] = None
    expected: Optional[Any] = None
    is_public: bool = True


class MicroChallengeListItem(BaseSchema):
    id: int
    title: str
    specialization: str
    grade: str
    points: int
    freshness_boost: float
    time_limit_ms: int
    author_company_name: str
    is_solved_by_me: bool = False


class MicroChallengeListResponse(BaseSchema):
    items: List[MicroChallengeListItem]
    meta: PaginationMeta


class MicroChallengeDetailResponse(BaseSchema):
    id: int
    title: str
    description_markdown: str
    specialization: str
    grade: str
    starter_code: str
    public_tests: List[Any]
    time_limit_ms: int
    memory_limit_mb: int
    points: int
    author_company_name: str
    created_at: datetime


class RunChallengeTestsRequest(BaseSchema):
    solution_code: Optional[str] = None
    code: Optional[str] = None


class ChallengeDryRunResponse(BaseSchema):
    all_passed: bool
    passed_count: int
    total_count: int
    logs: str
    execution_time_ms: float
    memory_used_mb: float
    status: str = "passed"
    memory_kb: Optional[int] = None
    public_results: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def populate_compat_fields(self) -> ChallengeDryRunResponse:
        if not self.status or (self.status == "passed" and not self.all_passed):
            self.status = "passed" if self.all_passed else "failed"
        if self.memory_kb is None and self.memory_used_mb is not None:
            self.memory_kb = int(self.memory_used_mb * 1024)
        return self


class SubmitChallengeRequest(BaseSchema):
    solution_code: Optional[str] = None
    code: Optional[str] = None


class ChallengeSubmissionResponse(BaseSchema):
    submission_id: int
    status: SubmissionStatusEnum
    points_awarded: int
    freshness_score_delta: float
    new_freshness_score: float
    submitted_at: datetime


class ChallengeSubmissionHistoryResponse(BaseSchema):
    challenge_id: int
    submissions: List[ChallengeSubmissionResponse]


class CreateMicroChallengeRequest(BaseSchema):
    specialization_id: int
    grade_id: int
    title: str = Field(..., min_length=5, max_length=200)
    description_markdown: Optional[str] = None
    description: Optional[str] = None
    starter_code: Optional[str] = None
    template_code: Optional[str] = None
    reference_solution: Optional[str] = None
    test_cases: List[Any] = Field(..., min_length=1)
    time_limit_ms: int = Field(default=2000, ge=100, le=10000)
    memory_limit_mb: int = Field(default=128, ge=32, le=512)
    points: int = Field(default=25, ge=1, le=100)


class UpdateMicroChallengeRequest(BaseSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description_markdown: Optional[str] = Field(None, min_length=20)
    starter_code: Optional[str] = None
    test_cases: Optional[List[TestCaseItem]] = None
    time_limit_ms: Optional[int] = Field(None, ge=100, le=10000)
