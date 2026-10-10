"""
Unit Test Suite for KITE IRT 3PL & Bayesian EAP Estimator.
Verifies Birnbaum 3PL probability, Fisher Information, 61-point EAP integration,
log-sum-exp numerical stability, scale clamping [0.0, 100.0], and monotonicity.
"""
from __future__ import annotations

import math
import pytest

from app.services.kite_irt import (
    BayesianEAPEstimator,
    IRT3PLItem,
    compute_sem,
    compute_test_information,
)


def test_irt_item_validation():
    """Проверка валидации параметров трехпараметрической модели Бирнбаума."""
    # a <= 0 должно вызывать ValueError
    with pytest.raises(ValueError, match="Параметр дискриминативности a должен быть > 0.0"):
        IRT3PLItem(item_id=1, a=0.0, b=0.0, c=0.2)

    with pytest.raises(ValueError, match="Параметр дискриминативности a должен быть > 0.0"):
        IRT3PLItem(item_id=1, a=-1.5, b=0.0, c=0.2)

    # c вне [0.0, 1.0] должно вызывать ValueError
    with pytest.raises(ValueError, match="Параметр угадывания c должен лежать в"):
        IRT3PLItem(item_id=2, a=1.0, b=0.0, c=-0.1)

    with pytest.raises(ValueError, match="Параметр угадывания c должен лежать в"):
        IRT3PLItem(item_id=3, a=1.0, b=0.0, c=1.2)


def test_item_response_probability_bounds():
    """Проверка границ и аналитических свойств кривой отклика (Item Characteristic Curve)."""
    item = IRT3PLItem(item_id=10, a=1.2, b=0.0, c=0.25)

    # При theta* = b: P = c + (1 - c) / 2 = 0.25 + 0.375 = 0.625
    p_center = item.response_probability(0.0)
    assert math.isclose(p_center, 0.625, rel_tol=1e-5), f"P(b) ожидалось 0.625, получено {p_center}"

    # При экстремально низкой способности P стремится к c
    p_low = item.response_probability(-10.0)
    assert math.isclose(p_low, 0.25, abs_tol=1e-4)

    # При экстремально высокой способности P стремится к 1.0
    p_high = item.response_probability(10.0)
    assert math.isclose(p_high, 1.0, abs_tol=1e-4)

    # Монотонность: P(theta1) < P(theta2) при theta1 < theta2
    assert item.response_probability(-1.0) < item.response_probability(0.0) < item.response_probability(1.0)


def test_fisher_information_properties():
    """Проверка неотрицательности и свойств информационной функции Фишера."""
    item = IRT3PLItem(item_id=11, a=1.5, b=0.5, c=0.2)

    # Информация строго неотрицательна
    for theta in [-3.0, -1.0, 0.0, 0.5, 1.5, 3.0]:
        info = item.item_information(theta)
        assert info >= 0.0, f"Информация Фишера должна быть >= 0, получено {info} при theta={theta}"

    # Накопленная информация тестовой батареи аддитивна
    items = [
        IRT3PLItem(item_id=1, a=1.0, b=-1.0, c=0.2),
        IRT3PLItem(item_id=2, a=1.5, b=0.0, c=0.2),
        IRT3PLItem(item_id=3, a=1.2, b=1.0, c=0.2),
    ]
    total_info = compute_test_information(items, 0.0)
    expected_sum = sum(i.item_information(0.0) for i in items)
    assert math.isclose(total_info, expected_sum, rel_tol=1e-9)

    # SEM = 1 / sqrt(I)
    sem = compute_sem(items, 0.0)
    assert math.isclose(sem, 1.0 / math.sqrt(total_info), rel_tol=1e-9)


def test_bayesian_eap_estimation_empty_fallback():
    """При отсутствии ответов EAP возвращает параметры априорного распределения."""
    estimator = BayesianEAPEstimator(num_nodes=61, theta_min=-4.0, theta_max=4.0, prior_mean=0.0, prior_sd=1.0)
    theta_star, sem_star = estimator.estimate_theta_star([], [])
    assert theta_star == 0.0
    assert sem_star == 1.0


def test_bayesian_eap_dimension_mismatch_raises():
    """При несоответствии размерности заданий и ответов вызывается ValueError."""
    estimator = BayesianEAPEstimator()
    items = [IRT3PLItem(item_id=1), IRT3PLItem(item_id=2)]
    with pytest.raises(ValueError, match="Несоответствие размерностей"):
        estimator.estimate_theta_star(items, [1])


def test_bayesian_eap_monotonicity_and_ordering():
    """
    Проверка монотонности байесовской оценки EAP:
    Идеальный кандидат (все верно) > Средний кандидат > Слабый кандидат (все неверно).
    """
    estimator = BayesianEAPEstimator()
    # Тестовая батарея из 12 заданий разной сложности
    items = [
        IRT3PLItem(item_id=i, a=1.0 + (i % 3) * 0.3, b=-2.0 + i * 0.35, c=0.2)
        for i in range(12)
    ]

    # Кандидат A: 12 из 12 решено верно
    theta_a, sem_a = estimator.estimate_theta_star(items, [1] * 12)
    # Кандидат B: первые 6 решено верно, остальные неверно
    theta_b, sem_b = estimator.estimate_theta_star(items, [1] * 6 + [0] * 6)
    # Кандидат C: 0 из 12 решено верно
    theta_c, sem_c = estimator.estimate_theta_star(items, [0] * 12)

    assert theta_a > theta_b > theta_c, f"Нарушение упорядочивания: {theta_a} > {theta_b} > {theta_c}"
    assert sem_a > 0.0
    assert sem_b > 0.0
    assert sem_c > 0.0


def test_theta_scale_transformations_and_clamping():
    """Проверка аффинных преобразований в 100-балльную платформенную шкалу и жесткого клампинга."""
    # scale_theta_linear_8: theta = clamp((theta* + 4.0) * 12.5, 0.0, 100.0)
    assert BayesianEAPEstimator.scale_theta_linear_8(-4.0) == 0.0
    assert BayesianEAPEstimator.scale_theta_linear_8(0.0) == 50.0
    assert BayesianEAPEstimator.scale_theta_linear_8(4.0) == 100.0

    # Защитный клампинг за пределами [-4.0, +4.0]
    assert BayesianEAPEstimator.scale_theta_linear_8(-10.0) == 0.0
    assert BayesianEAPEstimator.scale_theta_linear_8(10.0) == 100.0

    # scale_sem: SEM = SEM* * 12.5
    assert BayesianEAPEstimator.scale_sem(0.5) == 6.25
    assert BayesianEAPEstimator.scale_sem(1.0) == 12.5
