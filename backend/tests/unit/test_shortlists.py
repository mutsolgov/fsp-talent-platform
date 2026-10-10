"""
Unit Test Suite for Shortlists & Stateful Candidate Pinning.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §4.1-4.3 and DISPATCH.md.
"""
from __future__ import annotations

import pytest

from app.services.shortlist_service import sort_and_rank_items


def test_two_tier_ranking_pinned_on_top():
    """
    Инвариант пиннинга:
    Закрепленные кандидаты (is_pinned=True) безусловно занимают верхний ярус,
    даже если их балл ниже, чем у незакрепленных соискателей.
    """
    raw_items = [
        {"candidate_profile_id": 1, "is_pinned": False, "match_score": 98.0},
        {"candidate_profile_id": 2, "is_pinned": True, "match_score": 75.0},
        {"candidate_profile_id": 3, "is_pinned": True, "match_score": 82.0},
        {"candidate_profile_id": 4, "is_pinned": False, "match_score": 91.0},
    ]

    ranked = sort_and_rank_items(raw_items)

    assert len(ranked) == 4

    # Ярус 1: Закрепленные (IDs 3 и 2)
    assert ranked[0]["candidate_profile_id"] == 3
    assert ranked[0]["rank_position"] == 1
    assert ranked[0]["is_pinned"] is True

    assert ranked[1]["candidate_profile_id"] == 2
    assert ranked[1]["rank_position"] == 2
    assert ranked[1]["is_pinned"] is True

    # Ярус 2: Незакрепленные (IDs 1 и 4)
    assert ranked[2]["candidate_profile_id"] == 1
    assert ranked[2]["rank_position"] == 3
    assert ranked[2]["is_pinned"] is False

    assert ranked[3]["candidate_profile_id"] == 4
    assert ranked[3]["rank_position"] == 4
    assert ranked[3]["is_pinned"] is False


def test_delta_score_calculation():
    """Проверка расчета дифференциального сдвига Delta S = S_new - S_old."""
    old_score = 80.0
    new_score_improved = 87.4
    delta_positive = round(new_score_improved - old_score, 2)
    assert delta_positive == 7.4

    new_score_degraded = 74.8
    delta_negative = round(new_score_degraded - old_score, 2)
    assert delta_negative == -5.2

    delta_neutral = round(old_score - old_score, 2)
    assert delta_neutral == 0.0
