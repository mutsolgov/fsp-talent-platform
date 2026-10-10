"""
KITE (Kalibrated Isomorphic Task Engine) — IRT 3PL & Bayesian EAP Estimator.
Implements Birnbaum 3PL model, Fisher Information, and Bayesian EAP ability estimation.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §1.2–1.4 and DISPATCH.md.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


class IRT3PLItem:
    """Откалиброванное тестовое задание в трехпараметрической логистической модели Бирнбаума."""

    def __init__(
        self,
        item_id: int,
        a: float = 1.0,
        b: float = 0.0,
        c: float = 0.2,
        task_type: str = "mcq",
    ):
        if a <= 0.0:
            raise ValueError(f"Параметр дискриминативности a должен быть > 0.0, получено {a}")
        if not (0.0 <= c <= 1.0):
            raise ValueError(f"Параметр угадывания c должен лежать в [0.0, 1.0], получено {c}")

        self.item_id = item_id
        self.a = float(a)
        self.b = float(b)
        self.c = float(c)
        self.task_type = task_type
        self.D = 1.702  # Константа Бирнбаума

    def response_probability(self, theta_star: float) -> float:
        """
        Вычисляет вероятность правильного ответа P_i(theta*) в модели IRT 3PL:
        P_i(theta*) = c_i + (1 - c_i) / (1 + exp(-1.702 * a_i * (theta* - b_i)))
        """
        exponent = -self.D * self.a * (theta_star - self.b)
        if exponent > 40.0:
            return self.c
        elif exponent < -40.0:
            return 1.0
        return self.c + (1.0 - self.c) / (1.0 + math.exp(exponent))

    def item_information(self, theta_star: float) -> float:
        """
        Вычисляет значение локальной информационной функции Фишера:
        I_i(theta*) = (1.702 * a_i)^2 * (P_i - c_i)^2 / ((1 - c_i)^2 * P_i * (1 - P_i))
        """
        p = self.response_probability(theta_star)
        q = 1.0 - p
        if q <= 1e-12 or p <= 1e-12:
            return 0.0
        if self.c >= 1.0:
            return 0.0

        numerator = ((self.D * self.a * (p - self.c)) ** 2) * q
        denominator = ((1.0 - self.c) ** 2) * p
        return numerator / denominator if denominator > 0.0 else 0.0


class BayesianEAPEstimator:
    """
    Байесовский EAP-оценщик латентного уровня способностей на 61 точке квадратуры
    с априорным Гауссом N(mu, sigma^2) и логарифмической log-sum-exp стабилизацией.
    """

    def __init__(
        self,
        num_nodes: int = 61,
        theta_min: float = -4.0,
        theta_max: float = 4.0,
        prior_mean: float = 0.0,
        prior_sd: float = 1.0,
    ):
        self.num_nodes = num_nodes
        self.theta_min = theta_min
        self.theta_max = theta_max
        self.step = (theta_max - theta_min) / (num_nodes - 1)
        self.prior_mean = prior_mean
        self.prior_sd = prior_sd

        # 61 узел квадратуры в [-4.0, +4.0]
        self.nodes = [theta_min + k * self.step for k in range(num_nodes)]

        # Веса априорного нормального распределения
        self.prior_weights = []
        for x in self.nodes:
            norm_pdf = (1.0 / (prior_sd * math.sqrt(2.0 * math.pi))) * math.exp(
                -0.5 * ((x - prior_mean) / prior_sd) ** 2
            )
            self.prior_weights.append(norm_pdf * self.step)

    def estimate_theta_star(
        self,
        items: List[IRT3PLItem],
        responses: List[int],
    ) -> Tuple[float, float]:
        """
        Оценивает математическое ожидание апостериорного распределения (EAP) theta* и PSD (SEM*).
        responses: бинарный вектор длины n (1 = решено, 0 = не решено).
        """
        if len(items) != len(responses):
            raise ValueError(f"Несоответствие размерностей: {len(items)} заданий vs {len(responses)} ответов")

        if not items:
            return self.prior_mean, self.prior_sd

        # 1. Расчет логарифма правдоподобия в каждом узле
        log_likelihoods = []
        for x in self.nodes:
            ll = 0.0
            for item, u in zip(items, responses):
                p = item.response_probability(x)
                p = max(1e-12, min(1.0 - 1e-12, p))
                ll += math.log(p) if u == 1 else math.log(1.0 - p)
            log_likelihoods.append(ll)

        # 2. Логарифм ненормированного апостериорного веса
        log_posteriors = [
            ll + math.log(max(1e-300, pw))
            for ll, pw in zip(log_likelihoods, self.prior_weights)
        ]

        # 3. Нормализация через log-sum-exp
        max_lp = max(log_posteriors)
        shifted_weights = [math.exp(lp - max_lp) for lp in log_posteriors]
        total_weight = sum(shifted_weights)
        norm_weights = [w / total_weight for w in shifted_weights]

        # 4. Точечная оценка EAP (математическое ожидание)
        theta_eap = sum(x * w for x, w in zip(self.nodes, norm_weights))

        # 5. Дисперсия и апостериорное стандартное отклонение (PSD / SEM*)
        variance = sum(((x - theta_eap) ** 2) * w for x, w in zip(self.nodes, norm_weights))
        sem_star = math.sqrt(max(0.0, variance))

        return theta_eap, sem_star

    @staticmethod
    def scale_theta_linear_8(theta_star: float) -> float:
        """
        Масштабирование по шкале [-4.0, +4.0] -> [0.0, 100.0]:
        theta = clamp((theta* + 4.0) * 12.5, 0.0, 100.0).
        """
        raw = (theta_star + 4.0) * 12.5
        return round(max(0.0, min(100.0, raw)), 2)

    @staticmethod
    def scale_sem(sem_star: float) -> float:
        """Масштабирование стандартной ошибки измерения: SEM = SEM* * 12.5."""
        return round(sem_star * 12.5, 2)

    @staticmethod
    def theta_star_to_platform_score(theta_star: float) -> float:
        """
        Аффинное преобразование латентного признака theta* in [-3, 3] в шкалу [0, 100].
        theta = clamp(50.0 + 16.6667 * theta*, 0.0, 100.0).
        """
        raw_score = 50.0 + (50.0 / 3.0) * theta_star
        return round(max(0.0, min(100.0, raw_score)), 2)


def compute_test_information(items: List[IRT3PLItem], theta_star: float) -> float:
    """Вычисляет общую накопленную информацию тестовой батареи."""
    return sum(item.item_information(theta_star) for item in items)


def compute_sem(items: List[IRT3PLItem], theta_star: float) -> float:
    """Стандартная ошибка измерения SEM(theta*) = 1 / sqrt(I(theta*))."""
    info = compute_test_information(items, theta_star)
    return 1.0 / math.sqrt(info) if info > 1e-9 else 999.0
