#!/usr/bin/env python3
"""
FSP IT-Talent Platform — Standalone Golden Validation Benchmark Suite
Milestone 6 / Phase 6 Delivery Script (docs/06 §4 and docs/03 §6).

Python 3.12 Standard Library Only:
math, json, hashlib, hmac, re, pathlib, typing, sys, random.

Evaluates:
- 60 Golden Candidates (30 FSP, 30 non-FSP across 6 specializations and 4 grades)
- 15 Employer Needs (900 Candidate-Need Evaluation Pairs)
- Ground Truth Relevance y in {0, 1, 2, 3}
- Multi-Factor Ranking Engine with Non-FSP Dynamic Weight Reallocation (0.52 / 0.30 / 0.00 / 0.18)
- 6 Threshold Metrics:
  1. Mean NDCG@5 >= 0.8500
  2. Mean NDCG@10 >= 0.8800
  3. Mean Precision@5 >= 0.8000
  4. Test-Retest Pearson r_xx >= 0.8500
  5. Item Discrimination Kelley D >= 0.3000
  6. Leak Resistance Index >= 0.8500
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path to resolve canonical app.services.benchmark_service
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.services.benchmark_service import (
    SPECIALIZATIONS,
    GRADES,
    get_golden_candidates,
    get_employer_needs,
    get_ground_truth_relevance,
    calculate_fsp_subscore,
    calculate_stack_subscore,
    calculate_grade_multiplier,
    rank_candidates,
    calculate_dcg_at_k,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_test_retest_reliability,
    calculate_item_discrimination,
    calculate_leak_resistance,
    run_benchmark,
)

if __name__ == "__main__":
    run_benchmark()
    sys.exit(0)
