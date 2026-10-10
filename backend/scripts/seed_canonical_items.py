"""
FSP IT-Talent Platform — Canonical Item Families Seeder.
Populates calibrated test item families for all 6 specializations and 4 grades (288 items total).
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §1.5 and DISPATCH.md.
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Optional

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.canonical_item_families import CanonicalItemFamily
from app.models.grades import Grade
from app.models.specializations import Specialization

# Калибровочные параметры 12 заданий батареи KITE из docs/03 §1.5.2
BATTERY_SPECS = [
    {
        "index": 1,
        "task_type": "mcq",
        "title": "Computer Science: Memory Models & Complexity",
        "a": 1.30,
        "b_rel": -0.80,
        "c": 0.20,
        "time_limit": 180,
        "template": "В распределенном сервисе {{service_name}} оценивается асимптотическая сложность выборки из кэша размера {{window_size}}. Какова наихудшая сложность?",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["OrderRouter", "AuthGateway", "PaymentDispatcher", "InventoryBroker"]},
            "window_size": {"type": "range_int", "min": 100, "max": 1000, "step": 100},
        },
    },
    {
        "index": 2,
        "task_type": "mcq",
        "title": "Concurrency & Runtime Architecture",
        "a": 1.40,
        "b_rel": -0.40,
        "c": 0.20,
        "time_limit": 180,
        "template": "Компонент {{service_name}} обрабатывает параллельные задачи в пуле потоков. При каком условии возникает деградация производительности?",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["TaskWorker", "EventLoopDispatcher", "QueueConsumer", "SyncBridge"]},
            "threshold": {"type": "range_int", "min": 50, "max": 500, "step": 50},
        },
    },
    {
        "index": 3,
        "task_type": "mcq",
        "title": "Persistence & Transaction Isolation",
        "a": 1.50,
        "b_rel": -0.10,
        "c": 0.20,
        "time_limit": 180,
        "template": "База данных сервиса {{service_name}} настроена с уровнем изоляции Repeatable Read. Защищает ли это от фантомных вставок?",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["BillingLedger", "AccountRegistry", "AuditStore", "BalanceManager"]},
        },
    },
    {
        "index": 4,
        "task_type": "mcq",
        "title": "Networking Protocols & RPC",
        "a": 1.60,
        "b_rel": 0.10,
        "c": 0.20,
        "time_limit": 180,
        "template": "При передаче потоковых данных между сервисами {{service_name}} и клиентом с лимитом {{threshold}} RPS, какой протокол обеспечивает минимальный оверхед?",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["TelemetryCollector", "StreamingGateway", "NotificationHub", "MetricsAggregator"]},
            "threshold": {"type": "range_int", "min": 1000, "max": 50000, "step": 5000},
        },
    },
    {
        "index": 5,
        "task_type": "code_triage",
        "title": "Bug Triage: Race Condition Diagnostics",
        "a": 1.70,
        "b_rel": -0.20,
        "c": 0.05,
        "time_limit": 300,
        "template": "В модуле {{service_name}} обнаружено состояние гонки при обновлении счетчика с порогом {{threshold}}. Найдите уязвимый блок кода.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["RateLimiterState", "SessionStore", "AtomicCounter", "SlotAllocator"]},
            "threshold": {"type": "range_int", "min": 10, "max": 200, "step": 10},
        },
    },
    {
        "index": 6,
        "task_type": "system_design",
        "title": "Architecture: Caching & Consistency Trade-offs",
        "a": 1.80,
        "b_rel": 0.20,
        "c": 0.05,
        "time_limit": 300,
        "template": "Спроектируйте стратегию инвалидации кэша в {{service_name}} при объеме {{threshold}} записей для предотвращения Cache Stampede.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["CatalogService", "UserProfileCache", "PriceEngine", "SearchIndexer"]},
            "threshold": {"type": "range_int", "min": 10000, "max": 1000000, "step": 50000},
        },
    },
    {
        "index": 7,
        "task_type": "code_triage",
        "title": "Security Audit & Vulnerability Mitigation",
        "a": 1.90,
        "b_rel": 0.40,
        "c": 0.05,
        "time_limit": 300,
        "template": "В эндпоинте аутентификации {{service_name}} обнаружен потенциальный дефект валидации токенов с окном действия {{window_size}} сек.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["JwtValidator", "OAuthVerifier", "SsoFilter", "TokenIntrospect"]},
            "window_size": {"type": "range_int", "min": 30, "max": 300, "step": 30},
        },
    },
    {
        "index": 8,
        "task_type": "system_design",
        "title": "Distributed Systems: Partitioning & Idempotency",
        "a": 2.00,
        "b_rel": 0.60,
        "c": 0.05,
        "time_limit": 300,
        "template": "Разработайте механизм дедупликации сообщений в брокере {{service_name}} с гарантией точно один раз при падении узлов.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["KafkaConsumerGroup", "RabbitMqExchange", "NatsCluster", "PulsarRouter"]},
        },
    },
    {
        "index": 9,
        "task_type": "algorithmic",
        "title": "Algorithmic Core: Sliding Window Maximum",
        "a": 2.00,
        "b_rel": 0.00,
        "c": 0.00,
        "time_limit": 450,
        "template": "Реализуйте функцию поиска максимума в скользящем окне размера {{window_size}} для логов микросервиса {{service_name}} за O(N).",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["LogAnalyzer", "AnomalyDetector", "MetricFilter", "StreamAverager"]},
            "window_size": {"type": "range_int", "min": 3, "max": 15, "step": 2},
        },
    },
    {
        "index": 10,
        "task_type": "code_sandbox",
        "title": "Practical Component: Thread-Safe Rate Limiter",
        "a": 2.10,
        "b_rel": 0.30,
        "c": 0.00,
        "time_limit": 450,
        "template": "Напишите потокобезопасный Token Bucket ограничитель запросов для сервиса {{service_name}} с емкостью {{threshold}} токенов.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["ApiGatewayLimiter", "IngressThrottler", "ClientQuotaManager", "DdosGuard"]},
            "threshold": {"type": "range_int", "min": 50, "max": 500, "step": 50},
        },
    },
    {
        "index": 11,
        "task_type": "algorithmic",
        "title": "Fault Tolerance: Exponential Backoff with Jitter",
        "a": 2.20,
        "b_rel": 0.70,
        "c": 0.00,
        "time_limit": 450,
        "template": "Реализуйте алгоритм Full Jitter Retry для клиентов {{service_name}} с базовой задержкой {{window_size}} мс и коэффициентом 2.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["RpcClient", "DbConnector", "PaymentGatewayClient", "WebhookPoster"]},
            "window_size": {"type": "range_int", "min": 50, "max": 500, "step": 50},
        },
    },
    {
        "index": 12,
        "task_type": "code_sandbox",
        "title": "High-Load Pipeline: Backpressure Batch Buffer",
        "a": 2.30,
        "b_rel": 1.10,
        "c": 0.00,
        "time_limit": 450,
        "template": "Разработайте потокобезопасный буфер с обратным давлением (Backpressure) для пайплайна {{service_name}} с максимальным размером {{threshold}}.",
        "param_matrix": {
            "service_name": {"type": "synonym", "synonyms": ["EventBatcher", "TelemetryBuffer", "IngestPipeline", "AsyncWriter"]},
            "threshold": {"type": "range_int", "min": 500, "max": 5000, "step": 500},
        },
    },
]

# Базовая сложность по грейдам
GRADE_BASE_DIFFICULTY = {
    "junior": -0.40,
    "middle": 1.00,
    "senior": 1.80,
    "lead": 2.30,
}


async def seed_canonical_items(session: Optional[AsyncSession] = None) -> int:
    """Сидирует 288 откалиброванных канонических семейств заданий KITE."""
    if session is not None:
        return await _seed_with_session(session)
    async with async_session_factory() as sess:
        return await _seed_with_session(sess)


async def _seed_with_session(session: AsyncSession) -> int:
    # Получаем все специализации и грейды
    specs_res = await session.execute(select(Specialization))
    specs = {s.code: s for s in specs_res.scalars().all()}

    grades_res = await session.execute(select(Grade))
    grades = {g.code: g for g in grades_res.scalars().all()}

    if not specs or not grades:
        print("[-] Ошибка: Справочники специализаций или грейдов пусты. Сначала запустите seed_reference_data.py")
        return 0

    created_count = 0
    for spec_code, spec in specs.items():
        for grade_code, grade in grades.items():
            b_base = GRADE_BASE_DIFFICULTY.get(grade_code, 0.0)

            for item_spec in BATTERY_SPECS:
                family_code = f"{spec_code.upper()}-{grade_code.upper()}-TASK-{item_spec['index']:02d}"

                # Проверяем наличие
                existing = await session.execute(
                    select(CanonicalItemFamily).where(CanonicalItemFamily.family_code == family_code)
                )
                if existing.scalar_one_or_none():
                    continue

                param_b = round(b_base + item_spec["b_rel"], 2)

                item = CanonicalItemFamily(
                    specialization_id=spec.id,
                    grade_id=grade.id,
                    family_code=family_code,
                    task_type=item_spec["task_type"],
                    title=f"[{spec.name}] {item_spec['title']}",
                    template_text=item_spec["template"],
                    param_matrix_json=item_spec["param_matrix"],
                    test_generator_code="# Deterministic KITE Python generator code",
                    param_a=item_spec["a"],
                    param_b=param_b,
                    param_c=item_spec["c"],
                    time_limit_sec=item_spec["time_limit"],
                    is_active=True,
                )
                session.add(item)
                created_count += 1

    await session.commit()
    print(f"[+] Успешно сидировано {created_count} канонических семейств заданий KITE.")
    return created_count


if __name__ == "__main__":
    count = asyncio.run(seed_canonical_items())
    print(f"[*] Готово: {count} заданий сохранено в базу данных.")
