"""
FSP IT-Talent Platform — Isomorphic Task Generator.
Deterministic task variant mutation using HMAC-SHA256 seeds.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §2.1–2.3 and DISPATCH.md.
"""
from __future__ import annotations

import hashlib
import hmac
import random
from typing import Any, Dict, List, Optional


class IsomorphicGenerator:
    """
    Детерминированный генератор изоморфных вариантов заданий KITE
    на базе криптографического HMAC-SHA256 сида.
    """

    def __init__(self, secret_key: str = "kite_master_secret_2026_lct"):
        self.secret_key = secret_key.encode("utf-8")

    def derive_seed_hash(self, candidate_id: int, session_id: int, item_id: int) -> str:
        """
        Вычисляет детерминированный HMAC-SHA256 хэш сида для тройки:
        candidate_id:session_id:item_id
        """
        message = f"{candidate_id}:{session_id}:{item_id}".encode("utf-8")
        return hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()

    def generate_variant(
        self,
        candidate_id: int,
        session_id: int,
        item_id: int,
        template_text: str,
        param_matrix: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Генерирует детерминированно мутированный текст задачи, 3 публичных примера
        и 10 скрытых стресс-тестов без коллизий.
        """
        seed_hash = self.derive_seed_hash(candidate_id, session_id, item_id)
        seed_int = int(seed_hash[:16], 16)
        rng = random.Random(seed_int)

        # 1. Мутация параметров по формальной матрице
        selected_params: Dict[str, Any] = {}
        for param_name, config in param_matrix.items():
            if not isinstance(config, dict):
                continue
            param_type = config.get("type", "choice")
            if param_type == "choice":
                choices = config.get("choices", [])
                if choices:
                    selected_params[param_name] = rng.choice(choices)
            elif param_type == "range_int":
                min_v = config.get("min", 1)
                max_v = config.get("max", 10)
                step = config.get("step", 1)
                selected_params[param_name] = rng.randrange(min_v, max_v + 1, step)
            elif param_type == "synonym":
                synonyms = config.get("synonyms", [])
                if synonyms:
                    selected_params[param_name] = rng.choice(synonyms)

        # 2. Подстановка мутированных параметров в условие задания
        rendered_prompt = template_text
        for k, v in selected_params.items():
            rendered_prompt = rendered_prompt.replace(f"{{{{{k}}}}}", str(v))

        # 3. Детерминированная генерация 3 публичных тестов
        window_size = int(selected_params.get("window_size", 5))
        threshold = int(selected_params.get("threshold", 100))
        service_name = str(selected_params.get("service_name", "OrderRouter"))

        public_tests: List[Dict[str, Any]] = []
        for i in range(3):
            sample_len = window_size + rng.randint(2, 6)
            sample_records = [rng.randint(10, 500) for _ in range(sample_len)]
            expected_val = max(sample_records[:window_size])
            public_tests.append({
                "test_id": f"pub_{i+1}",
                "input": {
                    "service": service_name,
                    "window_size": window_size,
                    "records": sample_records,
                },
                "expected": expected_val,
                "is_public": True,
            })

        # 4. Детерминированная генерация 10 скрытых тестов (включая стресс-тесты)
        hidden_tests: List[Dict[str, Any]] = []
        for i in range(10):
            # Первые 8 тестов — функциональные границы, последние 2 — стресс-тесты на O(N log N)
            if i < 8:
                n_elements = rng.randint(20, 250)
                is_stress = False
            elif i == 8:
                n_elements = 1000
                is_stress = True
            else:
                n_elements = 5000
                is_stress = True

            hidden_records = [rng.randint(-500, 10000) for _ in range(n_elements)]
            expected_val = max(hidden_records[:window_size]) if hidden_records else 0

            hidden_tests.append({
                "test_id": f"hid_{i+1}",
                "input": {
                    "service": service_name,
                    "window_size": window_size,
                    "records": hidden_records,
                },
                "expected": expected_val,
                "is_public": False,
                "is_stress": is_stress,
            })

        return {
            "variant_seed": seed_hash,
            "seed_int": seed_int,
            "selected_params": selected_params,
            "rendered_prompt": rendered_prompt,
            "public_tests": public_tests,
            "hidden_tests": hidden_tests,
            "time_limit_sec": int(param_matrix.get("time_limit_sec", 1200)),
        }
