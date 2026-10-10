"""
FSP IT-Talent Platform — Pydantic v2 Models for Module 13: validation-benchmark.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.13.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field

from app.schemas.base import BaseSchema


class RunBenchmarkRequest(BaseSchema):
    force_recompute: bool = Field(default=False)
    include_leak_test: bool = Field(default=True)
    dataset_version: str = Field(default="golden_v1_60x15")


class BenchmarkExecutionResponse(BaseSchema):
    run_id: str
    status: Literal["completed", "running", "failed"]
    elapsed_seconds: float
    total_candidates_evaluated: int = 60
    total_needs_evaluated: int = 15
    thresholds_passed: bool
    summary_ndcg_at_5: float
    summary_ndcg_at_10: float
    summary_precision_at_5: float


class BenchmarkStatusResponse(BaseSchema):
    run_id: str
    status: Literal["idle", "running", "completed", "failed"]
    progress_percent: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class NeedMetricReport(BaseSchema):
    need_id: int
    need_title: str
    specialization: str
    grade: str
    ndcg_at_5: float
    ndcg_at_10: float
    precision_at_5: float
    ground_truth_top1_candidate_id: int
    actual_top1_candidate_id: int
    top1_match: bool


class BenchmarkReportResponse(BaseSchema):
    run_id: str
    dataset_version: str
    executed_at: datetime
    all_thresholds_passed: bool
    metrics: Dict[str, float] = Field(
        ...,
        description="Ключевые метрики: mean_ndcg_5, mean_ndcg_10, mean_p_5, test_retest_r, kelley_d, leak_index"
    )
    thresholds_comparison: List[Dict[str, Any]]
    needs_breakdown: List[NeedMetricReport]


class BenchmarkChartDataResponse(BaseSchema):
    radar_chart_series: List[Dict[str, Any]]
    ndcg_by_need_bars: List[Dict[str, Any]]
    scatter_test_retest: List[Dict[str, Any]]
