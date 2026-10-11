"""
FSP IT-Talent Platform — Assessment Pydantic v2 Schemas (KITE IRT 3PL).
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.5.
"""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import Field

from app.schemas.base import BaseSchema


class SessionTypeEnum(StrEnum):
    INITIAL = "initial"
    BOOST = "boost"
    RETEST_LOWER = "retest_lower"


class SessionStatusEnum(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SUBMITTED = "submitted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    ABANDONED = "abandoned"


class TaskTypeEnum(StrEnum):
    ALGORITHMIC = "algorithmic"
    SYSTEM_DESIGN = "system_design"
    CODE_TRIAGE = "code_triage"
    CODE_SANDBOX = "code_sandbox"
    MCQ = "mcq"


class AssessmentVerdictEnum(StrEnum):
    CONFIRMED = "confirmed"
    BOOST_OFFERED = "boost_offered"
    RETEST_LOWER_OFFERED = "retest_lower_offered"
    LOWER_GRADE_OFFERED = "lower_grade_offered"
    FAILED = "failed"


class StartAssessmentSessionRequest(BaseSchema):
    category_id: Optional[int] = Field(None, description="ID целевой категории (Specialization + Grade)")
    specialization_id: Optional[int] = Field(None, description="ID специализации")
    claimed_grade_id: Optional[int] = Field(None, description="ID заявляемого грейда")
    session_type: SessionTypeEnum = Field(default=SessionTypeEnum.INITIAL)


class AssessmentSessionStartResponse(BaseSchema):
    session_id: int
    category_id: int
    session_type: SessionTypeEnum
    tasks_count: int = 12
    total_tasks: int = 12
    time_limit_minutes: int = 90
    seed_hash: str = Field(..., description="Anti-leak seed hash сессии")
    variant_seed: Optional[str] = None
    status: str = "in_progress"
    started_at: datetime
    expires_at: datetime


class AssessmentTaskItemResponse(BaseSchema):
    session_id: int
    task_index: int = Field(..., ge=0, le=12)
    task_type: TaskTypeEnum
    title: str
    description: str
    prompt: Optional[str] = None
    code_template: Optional[str] = None
    public_tests: List[Dict[str, Any]] = Field(default_factory=list)
    time_limit_seconds: int = 300


class SubmitTaskAnswerRequest(BaseSchema):
    task_index: int = Field(..., ge=0, le=12)
    answer_payload: Union[str, Dict[str, Any]] = Field(..., description="Исходный код решения или ключ ответа")
    time_spent_seconds: Optional[int] = Field(default=0)
    tab_switch_count: Optional[int] = Field(default=0)


class SubmitTaskAnswerResponse(BaseSchema):
    session_id: int
    task_index: int
    passed_public_tests: int
    total_public_tests: int
    verdict: Literal["accepted", "wrong_answer", "timeout", "runtime_error"]
    execution_time_ms: float


class AssessmentSessionProgressResponse(BaseSchema):
    session_id: int
    status: SessionStatusEnum
    tasks_answered: int
    tasks_total: int = 12
    seconds_remaining: int


class AssessmentSessionResultResponse(BaseSchema):
    session_id: int
    candidate_id: int
    theta_score: float = Field(..., description="Оценка IRT theta [0.0, 100.0]")
    scaled_score: float = Field(..., description="Масштабированный балл (0..100)")
    raw_score: Optional[int] = 0
    grade_confirmed: Optional[str] = None
    claimed_grade: Optional[str] = None
    suggested_grade: Optional[str] = None
    specialization: Optional[str] = None
    verdict: AssessmentVerdictEnum
    boost_available: bool = False
    retest_lower_available: bool = False
    cooldown_until: Optional[datetime] = None
    completed_at: datetime
    status: str = "completed"
    explainability: Optional[Union[str, Dict[str, Any]]] = None


class RetestLowerGradeRequest(BaseSchema):
    failed_session_id: int


class CooldownStatusResponse(BaseSchema):
    candidate_id: int
    is_cooldown_active: bool
    cooldown_until: Optional[datetime] = None
    days_left: int = 0
    days_remaining: int = 0
    can_retest_lower: bool = True
