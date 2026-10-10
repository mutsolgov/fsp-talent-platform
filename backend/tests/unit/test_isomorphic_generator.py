"""
Unit Test Suite for Isomorphic Task Generator.
Verifies HMAC-SHA256 seed determinism, zero collisions across seeds,
parameter matrix mutations, template rendering, and 3 public / 10 hidden tests contract.
"""
from __future__ import annotations

import pytest

from app.services.isomorphic_generator import IsomorphicGenerator


def test_hmac_seed_determinism():
    """Одинаковые candidate_id, session_id, item_id дают идентичный сид и одинаковый вариант."""
    gen = IsomorphicGenerator(secret_key="test_secret_key_123")

    hash1 = gen.derive_seed_hash(candidate_id=42, session_id=101, item_id=7)
    hash2 = gen.derive_seed_hash(candidate_id=42, session_id=101, item_id=7)

    assert hash1 == hash2, "HMAC-SHA256 сид должен быть строго детерминирован"
    assert len(hash1) == 64, "SHA-256 хэш должен состоять из 64 hex-символов"


def test_seed_collision_resistance():
    """Разные параметры генерации дают уникальные сид-хэши."""
    gen = IsomorphicGenerator()

    hash_a = gen.derive_seed_hash(candidate_id=1, session_id=100, item_id=10)
    hash_b = gen.derive_seed_hash(candidate_id=2, session_id=100, item_id=10)
    hash_c = gen.derive_seed_hash(candidate_id=1, session_id=101, item_id=10)
    hash_d = gen.derive_seed_hash(candidate_id=1, session_id=100, item_id=11)

    unique_hashes = {hash_a, hash_b, hash_c, hash_d}
    assert len(unique_hashes) == 4, "Все сиды должны быть уникальными при изменении любого компонента тройки"


def test_variant_generation_and_template_rendering():
    """Проверка генерации варианта: подстановка плейсхолдеров и детерминированность."""
    gen = IsomorphicGenerator()

    template = "Сервис {{service_name}} с окном скольжения {{window_size}} и порогом {{threshold}}."
    param_matrix = {
        "service_name": {"type": "choice", "choices": ["BillingGateway", "OrderRouter", "AuthSentinel"]},
        "window_size": {"type": "range_int", "min": 3, "max": 10, "step": 1},
        "threshold": {"type": "choice", "choices": [100, 200, 500]},
        "time_limit_sec": 1200,
    }

    v1 = gen.generate_variant(
        candidate_id=15,
        session_id=88,
        item_id=20,
        template_text=template,
        param_matrix=param_matrix,
    )
    v2 = gen.generate_variant(
        candidate_id=15,
        session_id=88,
        item_id=20,
        template_text=template,
        param_matrix=param_matrix,
    )

    # Строгая повторяемость
    assert v1["variant_seed"] == v2["variant_seed"]
    assert v1["rendered_prompt"] == v2["rendered_prompt"]
    assert v1["selected_params"] == v2["selected_params"]

    # В результирующем промпте не должно остаться шаблонов {{...}}
    assert "{{" not in v1["rendered_prompt"]
    assert "}}" not in v1["rendered_prompt"]
    assert v1["selected_params"]["service_name"] in ["BillingGateway", "OrderRouter", "AuthSentinel"]
    assert 3 <= v1["selected_params"]["window_size"] <= 10


def test_testcases_contract_3_public_10_hidden():
    """
    Проверка контракта KITE:
    Ровно 3 публичных примера (is_public=True) и ровно 10 скрытых тестов (is_public=False).
    """
    gen = IsomorphicGenerator()
    matrix = {
        "service_name": {"type": "choice", "choices": ["MetricsCollector"]},
        "window_size": {"type": "range_int", "min": 4, "max": 8, "step": 2},
    }

    variant = gen.generate_variant(
        candidate_id=99,
        session_id=102,
        item_id=305,
        template_text="Task text",
        param_matrix=matrix,
    )

    public_tests = variant["public_tests"]
    hidden_tests = variant["hidden_tests"]

    assert len(public_tests) == 3, f"Ожидалось ровно 3 публичных теста, получено {len(public_tests)}"
    assert all(t["is_public"] is True for t in public_tests)

    assert len(hidden_tests) == 10, f"Ожидалось ровно 10 скрытых тестов, получено {len(hidden_tests)}"
    assert all(t["is_public"] is False for t in hidden_tests)

    # Проверка наличия стресс-тестов в скрытом наборе
    stress_tests = [t for t in hidden_tests if t.get("is_stress") is True]
    assert len(stress_tests) == 2, f"Ожидалось 2 стресс-теста, получено {len(stress_tests)}"
    assert len(stress_tests[0]["input"]["records"]) == 1000
    assert len(stress_tests[1]["input"]["records"]) == 5000
