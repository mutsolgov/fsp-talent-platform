"""
FSP IT-Talent Platform — Canonical Reference Data Seeder.
Seeds:
- 6 Specializations (Backend, Frontend, ML/Data, DevOps, QA, InfoSec)
- 4 Grades (Junior, Middle, Senior, Lead)
- 24 Composite Categories (6 × 4)
- 350+ Verified Canonical IT Skills from TAXONOMY_350_PLUS (docs/03 §5.1.2)
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, engine, ensure_keycloak_schema
from app.models.base import Base
from app.models.specializations import Specialization
from app.models.grades import Grade
from app.models.categories import Category
from app.models.skills import Skill

SPECIALIZATIONS_DATA = [
    {
        "code": "backend",
        "name": "Backend разработка",
        "description": "Серверная логика, базы данных, распределенные системы",
    },
    {
        "code": "frontend",
        "name": "Frontend разработка",
        "description": "Пользовательские интерфейсы, веб-клиенты, SPA",
    },
    {
        "code": "ml_data",
        "name": "Machine Learning и Data Science",
        "description": "Машинное обучение, инженерия данных, нейросети",
    },
    {
        "code": "devops",
        "name": "DevOps и Cloud инфраструктура",
        "description": "CI/CD, контейнеризация, оркестрация, облачные платформы",
    },
    {
        "code": "qa",
        "name": "Quality Assurance и тестирование",
        "description": "Ручное и автоматизированное тестирование, нагрузка",
    },
    {
        "code": "infosec",
        "name": "Информационная безопасность",
        "description": "Безопасность приложений, аудит, криптография, DevSecOps",
    },
]

GRADES_DATA = [
    {
        "code": "junior",
        "name": "Junior",
        "rank_order": 1,
        "description": "Базовые практические навыки под руководством наставника",
    },
    {
        "code": "middle",
        "name": "Middle",
        "rank_order": 2,
        "description": "Самостоятельное решение типовых инженерных задач",
    },
    {
        "code": "senior",
        "name": "Senior",
        "rank_order": 3,
        "description": "Проектирование архитектуры, решение нестандартных проблем",
    },
    {
        "code": "lead",
        "name": "Lead",
        "rank_order": 4,
        "description": "Техническое лидерство, кросс-системная координация",
    },
]

TAXONOMY_350_PLUS = {
    "backend": [
        "python", "go", "golang", "java", "kotlin", "c++", "c#", "rust", "php", "node.js",
        "ruby", "scala", "elixir", "clojure", "django", "fastapi", "flask", "aiohttp",
        "tornado", "spring", "spring boot", "quarkus", "micronaut", "asp.net", "asp.net core",
        "gin", "echo", "fiber", "chi", "actix", "tokio", "laravel", "symfony", "ruby on rails",
        "express", "nestjs", "fastify", "koa", "postgresql", "postgres", "mysql", "mariadb",
        "sqlite", "oracle", "ms sql", "sql server", "redis", "memcached", "valkey", "mongodb",
        "cassandra", "scylladb", "couchbase", "dynamodb", "clickhouse", "elasticsearch",
        "opensearch", "kafka", "rabbitmq", "nats", "celery", "pulsar", "activemq", "zeromq",
        "grpc", "protobuf", "rest", "graphql", "websocket", "thrift", "sqlalchemy", "alembic",
        "hibernate", "jpa", "ef core", "dapper", "gorm", "prisma", "typeorm", "docker",
        "linux", "system design", "microservices", "event-driven architecture", "cqrs",
        "event sourcing", "domain-driven design", "clean architecture", "hexagonal architecture"
    ],
    "frontend": [
        "javascript", "typescript", "react", "next.js", "vue", "vue.js", "nuxt", "nuxt.js",
        "angular", "svelte", "sveltekit", "solid.js", "redux", "redux toolkit", "mobx",
        "zustand", "pinia", "recoil", "rxjs", "html", "html5", "css", "css3", "sass", "scss",
        "less", "tailwind", "tailwind css", "material ui", "mui", "ant design", "chakra ui",
        "shadcn", "radix ui", "bootstrap", "webpack", "vite", "rollup", "parcel", "turbopack",
        "babel", "esbuild", "swc", "jest", "vitest", "cypress", "playwright", "storybook",
        "websockets", "webrtc", "pwa", "webassembly", "wasm", "accessibility", "a11y",
        "wcag", "responsive design", "css modules", "styled components", "emotion", "three.js", "d3.js"
    ],
    "ml_data": [
        "python", "r", "julia", "c++", "pytorch", "tensorflow", "keras", "jax", "scikit-learn",
        "sklearn", "xgboost", "lightgbm", "catboost", "pandas", "numpy", "scipy", "polars",
        "dask", "spark", "pyspark", "ray", "hadoop", "hive", "airflow", "prefect", "dagster",
        "dbt", "kafka", "flink", "mlflow", "dvc", "weights & biases", "wandb", "triton",
        "onnx", "tensorrt", "openvino", "hugging face", "transformers", "langchain",
        "llamaindex", "vllm", "deepspeed", "fastai", "opencv", "spacy", "nltk", "gensim",
        "llm", "fine-tuning", "lora", "qlora", "rag", "embeddings", "faiss", "milvus",
        "qdrant", "chroma", "weaviate", "sql", "clickhouse", "snowflake", "bigquery",
        "computer vision", "nlp", "reinforcement learning", "feature store"
    ],
    "devops": [
        "linux", "bash", "shell", "python", "go", "docker", "podman", "containerd",
        "kubernetes", "k8s", "helm", "kustomize", "terraform", "terragrunt", "opentofu",
        "ansible", "puppet", "chef", "saltstack", "gitlab ci", "github actions", "jenkins",
        "argocd", "flux", "tekton", "teamcity", "prometheus", "grafana", "victoriametrics",
        "alertmanager", "loki", "elk", "elasticsearch", "logstash", "kibana", "jaeger",
        "opentelemetry", "datadog", "zabbix", "aws", "gcp", "azure", "yandex cloud", "vk cloud",
        "nginx", "haproxy", "envoy", "traefik", "cilium", "istio", "linkerd", "vault",
        "sops", "ceph", "minio", "zfs", "tcp/ip", "dns", "bgp", "wireguard", "openvpn"
    ],
    "qa": [
        "manual testing", "testrail", "jira", "confluence", "allure", "zephyr", "qase",
        "postman", "soapui", "swagger", "insomnia", "charles", "charles proxy", "fiddler",
        "mitmproxy", "wireshark", "python", "java", "javascript", "typescript", "c#",
        "selenium", "selenium webdriver", "playwright", "cypress", "appium", "puppeteer",
        "pytest", "junit", "testng", "jest", "allure framework", "k6", "jmeter", "gatling",
        "locust", "sql", "docker", "git", "api testing", "ui testing", "load testing",
        "stress testing", "security testing", "penetration testing", "cross-browser testing",
        "mobile testing", "test plan", "test cases", "bug reporting", "regression testing"
    ],
    "infosec": [
        "owasp", "owasp top 10", "web security", "penetration testing", "pentest", "burp suite",
        "owasp zap", "nmap", "wireshark", "metasploit", "kali linux", "nessus", "sqlmap",
        "ghidra", "ida pro", "x64dbg", "reverse engineering", "binary exploitation",
        "cryptography", "tls", "ssl", "pki", "oauth 2.0", "openid connect", "saml", "jwt",
        "siem", "soc", "splunk", "elastic siem", "wazuh", "suricata", "snort", "ossec",
        "yara", "threat modeling", "stride", "mitre att&ck", "linux hardening",
        "windows hardening", "active directory security", "appsec", "devsecops", "sast",
        "dast", "sonarqube", "trivy", "snyk", "semgrep", "gitleaks", "cis benchmarks",
        "iso 27001", "152-фз", "pci dss", "incident response"
    ]
}


def make_slug(name: str) -> str:
    """Generate safe, deterministic unique slug for skill."""
    s = name.lower()
    s = s.replace("c++", "cpp").replace("c#", "csharp").replace(".net", "dotnet").replace("152-фз", "152-fz")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "skill"


async def seed_reference_data(session: AsyncSession) -> dict[str, int]:
    """Execute complete reference data seeding."""
    await ensure_keycloak_schema()
    stats = {"specializations": 0, "grades": 0, "categories": 0, "skills": 0}

    # 1. Specializations
    spec_map: dict[str, int] = {}
    for spec_info in SPECIALIZATIONS_DATA:
        res = await session.execute(select(Specialization).where(Specialization.code == spec_info["code"]))
        existing = res.scalar_one_or_none()
        if not existing:
            spec_obj = Specialization(
                code=spec_info["code"],
                name=spec_info["name"],
                description=spec_info["description"],
                is_active=True,
            )
            session.add(spec_obj)
            await session.flush()
            spec_map[spec_info["code"]] = spec_obj.id
            stats["specializations"] += 1
        else:
            spec_map[spec_info["code"]] = existing.id

    # 2. Grades
    grade_map: dict[str, int] = {}
    grade_objs: dict[str, Grade] = {}
    for grade_info in GRADES_DATA:
        res = await session.execute(select(Grade).where(Grade.code == grade_info["code"]))
        existing = res.scalar_one_or_none()
        if not existing:
            grade_obj = Grade(
                code=grade_info["code"],
                name=grade_info["name"],
                rank_order=grade_info["rank_order"],
                description=grade_info["description"],
            )
            session.add(grade_obj)
            await session.flush()
            grade_map[grade_info["code"]] = grade_obj.id
            grade_objs[grade_info["code"]] = grade_obj
            stats["grades"] += 1
        else:
            grade_map[grade_info["code"]] = existing.id
            grade_objs[grade_info["code"]] = existing

    # 3. Composite Categories (6 × 4 = 24)
    for spec_code, spec_id in spec_map.items():
        spec_name = next(s["name"] for s in SPECIALIZATIONS_DATA if s["code"] == spec_code)
        for grade_code, grade_id in grade_map.items():
            slug = f"{spec_code}_{grade_code}"
            grade_name = grade_objs[grade_code].name
            title = f"{spec_name} · {grade_name}"

            res = await session.execute(select(Category).where(Category.slug == slug))
            existing = res.scalar_one_or_none()
            if not existing:
                cat_obj = Category(
                    specialization_id=spec_id,
                    grade_id=grade_id,
                    slug=slug,
                    title=title,
                    description=f"Верифицированная категория пула талантов: {title}",
                )
                session.add(cat_obj)
                stats["categories"] += 1

    await session.flush()

    # 4. Canonical Skills (350+ skills)
    inserted_skill_names: set[str] = set()
    res = await session.execute(select(Skill.name))
    for r in res.scalars():
        inserted_skill_names.add(r.lower())

    for spec_code, skill_list in TAXONOMY_350_PLUS.items():
        spec_id = spec_map[spec_code]
        for skill_name in skill_list:
            clean_name = skill_name.strip()
            if clean_name.lower() in inserted_skill_names:
                continue

            slug = make_slug(clean_name)
            # Ensure unique slug
            base_slug = slug
            counter = 1
            while True:
                slug_check = await session.execute(select(Skill).where(Skill.slug == slug))
                if not slug_check.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1

            skill_obj = Skill(
                name=clean_name,
                slug=slug,
                specialization_id=spec_id,
                category_tag=spec_code,
                is_core=clean_name.lower() in ("python", "go", "java", "typescript", "c++", "c#", "rust", "react", "docker", "kubernetes", "sql", "postgresql"),
                is_verified=True,
            )
            session.add(skill_obj)
            inserted_skill_names.add(clean_name.lower())
            stats["skills"] += 1

    await session.commit()
    return stats


async def main() -> None:
    print("=" * 70)
    print("FSP IT-Talent Platform — Seeding Reference Data")
    print("=" * 70)

    # Ensure keycloak schema exists if running on PostgreSQL
    await ensure_keycloak_schema()

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        stats = await seed_reference_data(session)

    # Print verification
    async with async_session_factory() as session:
        specs_count = (await session.execute(select(Specialization))).scalars().all()
        grades_count = (await session.execute(select(Grade))).scalars().all()
        cats_count = (await session.execute(select(Category))).scalars().all()
        skills_count = (await session.execute(select(Skill))).scalars().all()

    print(f"[✓] Specializations: {len(specs_count)} (added {stats['specializations']})")
    print(f"[✓] Grades:          {len(grades_count)} (added {stats['grades']})")
    print(f"[✓] Categories:      {len(cats_count)} (added {stats['categories']})")
    print(f"[✓] Verified Skills: {len(skills_count)} (added {stats['skills']})")
    print("=" * 70)
    assert len(specs_count) == 6, f"Expected 6 specializations, got {len(specs_count)}"
    assert len(grades_count) == 4, f"Expected 4 grades, got {len(grades_count)}"
    assert len(cats_count) == 24, f"Expected 24 categories, got {len(cats_count)}"
    assert len(skills_count) >= 350, f"Expected >= 350 skills, got {len(skills_count)}"
    print("Reference Data Seeding Completed Successfully! All Invariants Verified.")


if __name__ == "__main__":
    asyncio.run(main())
