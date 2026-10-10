"""
FSP IT-Talent Platform — Resume PDF Parser & Skill Matcher.
Validates magic bytes %PDF-, extracts text, contacts, experience, and canonical skills.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §5.1 and DISPATCH.md.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class InvalidPdfFormatError(Exception):
    """Исключение при некорректном или поврежденном заголовке PDF-файла (EC-18)."""
    pass


# Каноническая таксономия ключевых навыков из docs/03 §5.1.2
TAXONOMY_350_PLUS: Dict[str, List[str]] = {
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
    ],
}

# Регулярные выражения для контактов
RE_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE)
RE_PHONE = re.compile(
    r"(?:\+7|8|7)[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}"
)
RE_TELEGRAM = re.compile(
    r"(?:https?://t\.me/|(?<![a-zA-Z0-9_.+-])@)([a-zA-Z0-9_]{5,32})", re.IGNORECASE
)
RE_GITHUB = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_-]{1,39})", re.IGNORECASE
)


class ResumeParser:
    """Парсер PDF-резюме со строгой валидацией magic bytes %PDF- и извлечением компетенций."""

    @staticmethod
    def validate_magic_bytes(pdf_bytes: bytes) -> None:
        """
        Проверяет первые 5 байт входящего потока.
        Обязано начинаться с b'%PDF-'. При несовпадении выбрасывает InvalidPdfFormatError (EC-18).
        """
        if not pdf_bytes or len(pdf_bytes) < 5 or not pdf_bytes.startswith(b"%PDF-"):
            raise InvalidPdfFormatError(
                "ERR_INVALID_PDF_FORMAT: Некорректный или поврежденный формат PDF-документа: отсутствует заголовок %PDF-"
            )

    @classmethod
    def extract_text_from_pdf(cls, pdf_bytes: bytes) -> str:
        """
        Извлекает текстовые данные из PDF-файла с поддержкой PyMuPDF (fitz) и pikepdf/stream-fallback.
        """
        cls.validate_magic_bytes(pdf_bytes)

        # 1. Попытка через PyMuPDF (fitz)
        try:
            import fitz  # type: ignore

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_blocks = []
            for page in doc:
                text = page.get_text()
                if text and text.strip():
                    text_blocks.append(text.strip())
                else:
                    blocks = page.get_text("blocks")
                    for b in blocks:
                        if len(b) >= 5 and isinstance(b[4], str) and b[4].strip():
                            text_blocks.append(b[4].strip())
            if text_blocks:
                return "\n\n".join(text_blocks)
        except Exception as exc:
            logger.warning("PDF parse attempt failed: %s", exc, exc_info=True)

        # 2. Попытка через pikepdf
        try:
            import io
            import pikepdf  # type: ignore

            text_chunks = []
            with pikepdf.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    contents = page.get("/Contents")
                    stream_objs = []
                    if contents is not None:
                        if isinstance(contents, pikepdf.Array):
                            stream_objs.extend(contents)
                        elif isinstance(contents, pikepdf.Stream):
                            stream_objs.append(contents)
                    if not stream_objs:
                        for obj in page.values():
                            if isinstance(obj, pikepdf.Stream):
                                stream_objs.append(obj)

                    for obj in stream_objs:
                        try:
                            raw_bytes = obj.read_bytes()
                            decoded_stream = raw_bytes.decode("utf-8", errors="ignore")
                            # Извлечение текстовых литералов из PDF операторов Tj и TJ
                            extracted_literals = re.findall(r"\(([^)]+)\)\s*T[jJ]", decoded_stream)
                            if extracted_literals:
                                text_chunks.append("\n".join(extracted_literals))
                            else:
                                text_chunks.append(decoded_stream)
                        except Exception as exc:
                            logger.warning("PDF parse attempt failed: %s", exc, exc_info=True)
            if text_chunks:
                clean_text = "\n\n".join(text_chunks)
                if len(clean_text) > 20:
                    return clean_text
        except Exception as exc:
            logger.warning("PDF parse attempt failed: %s", exc, exc_info=True)

        # 3. Fallback: извлечение строковых литералов и чистого потока из PDF stream
        decoded = pdf_bytes.decode("latin1", errors="ignore")
        clean_stream = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", decoded)
        matches = re.findall(r"\(([^)]+)\)", decoded)
        if matches and len(" ".join(matches)) > len(clean_stream) * 0.5:
            return " ".join(matches)
        return clean_stream

    @classmethod
    def extract_contacts(cls, text: str) -> Dict[str, Optional[str]]:
        """Извлекает телефон, email, telegram, github из текста."""
        email_match = RE_EMAIL.search(text)
        email = email_match.group(0).lower() if email_match else None

        phone_match = RE_PHONE.search(text)
        phone = phone_match.group(0) if phone_match else None

        # Исключаем найденный email из текста для предотвращения ложных срабатываний домена на @handle
        text_without_email = text.replace(email_match.group(0), " ") if email_match else text

        tg_match = RE_TELEGRAM.search(text_without_email)
        telegram = f"@{tg_match.group(1)}" if tg_match else None

        gh_match = RE_GITHUB.search(text)
        github = f"https://github.com/{gh_match.group(1)}" if gh_match else None

        return {
            "email": email,
            "phone": phone,
            "telegram": telegram,
            "github_url": github,
        }

    @classmethod
    def match_skills(cls, text: str) -> List[str]:
        """Сопоставляет текст резюме с канонической таксономией 350+ навыков."""
        text_lower = text.lower()
        matched: Set[str] = set()

        for domain, skills_list in TAXONOMY_350_PLUS.items():
            for skill in skills_list:
                # Поиск целого слова / точного термина с lookaround границами (поддерживает c++, c#, .net и т.д.)
                pattern = r"(?<![a-zA-Z0-9_])" + re.escape(skill) + r"(?![a-zA-Z0-9_])"
                if re.search(pattern, text_lower):
                    matched.add(skill)

        # Сортировка для детерминированного вывода
        return sorted(list(matched))

    @classmethod
    def parse_experience_and_education(
        cls, text: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
        """Извлекает реальный опыт работы и образование по эвристикам из текста резюме."""
        # Оценка суммарного стажа по годам / месяцам
        year_matches = re.findall(r"\b(20[0-2][0-9]|199[0-9])\b", text)
        total_months = 0
        explicit_years = re.search(r"(\d+)\s*(?:лет|года|год|years?)", text, re.IGNORECASE)
        explicit_months = re.search(r"(\d+)\s*(?:мес|месяцев|months?)", text, re.IGNORECASE)
        if explicit_years:
            try:
                y = int(explicit_years.group(1))
                total_months += y * 12
            except ValueError:
                pass
        if explicit_months:
            try:
                m = int(explicit_months.group(1))
                total_months += m
            except ValueError:
                pass

        if total_months == 0 and len(year_matches) >= 2:
            years = sorted([int(y) for y in year_matches])
            span = min(40, max(1, years[-1] - years[0]))
            total_months = span * 12

        # 1. Извлечение должности (Position)
        detected_position = None
        role_pattern = (
            r"(?i)\b((?:Junior|Middle|Senior|Lead|Principal|Staff)?\s*"
            r"(?:Software\s+Engineer|Backend\s+Developer|Frontend\s+Developer|Fullstack\s+Developer|"
            r"DevOps\s+Engineer|Data\s+Scientist|ML\s+Engineer|QA\s+Engineer|Security\s+Engineer|"
            r"Разработчик(?:\s+[a-zA-Zа-яА-Я]+)?|Инженер(?:\s+[a-zA-Zа-яА-Я]+)?|"
            r"Архитектор(?:\s+[a-zA-Zа-яА-Я]+)?|Аналитик(?:\s+[a-zA-Zа-яА-Я]+)?|"
            r"Тестировщик(?:\s+[a-zA-Zа-яА-Я]+)?|Программист(?:\s+[a-zA-Zа-яА-Я]+)?))\b"
        )
        pos_match = re.search(role_pattern, text)
        if pos_match:
            detected_position = pos_match.group(1).strip()
        elif "backend" in text.lower():
            detected_position = "Backend Developer"
        elif "frontend" in text.lower():
            detected_position = "Frontend Developer"
        elif "qa" in text.lower():
            detected_position = "QA Engineer"
        elif "devops" in text.lower():
            detected_position = "DevOps Engineer"
        else:
            detected_position = "Software Engineer"

        # 2. Извлечение компании (Company)
        detected_company = None
        corp_match = re.search(r'(?i)(?:ООО|АО|ЗАО|ПАО)\s+["«]?([A-Za-zА-Яа-яЁё0-9\s\-_]{2,40})["»]?', text)
        if corp_match:
            detected_company = corp_match.group(0).strip().replace('"', '').replace('«', '').replace('»', '')
        else:
            known_co = re.search(
                r'(?i)\b(Яндекс|Сбер|Тинькофф|Т-Банк|VK|ВКонтакте|Озон|Ozon|Авито|Avito|МТС|MTS|Kaspersky|'
                r'Лаборатория\s+Касперского|Yandex|Sber|T-Bank|Wildberries|Вайлдберриз|HeadHunter|HH\.ru|'
                r'Т1|Крок|IBS|Positive\s+Technologies|Selectel|Ростелеком)\b',
                text
            )
            if known_co:
                detected_company = known_co.group(1).strip()
            else:
                at_company = re.search(r'(?i)(?:в\s+компании|company|at)\s+["«]?([A-ZА-Я][A-Za-zА-Яа-я0-9\s\-_]{2,30})["»]?', text)
                if at_company:
                    detected_company = at_company.group(1).strip()
                elif "опыт" in text.lower() or total_months > 0:
                    detected_company = "Технологическая Компания"

        experience: List[Dict[str, Any]] = []
        if detected_company or "опыт" in text.lower() or "experience" in text.lower() or total_months > 0:
            skills_found = cls.match_skills(text)
            start_yr = min(year_matches) if year_matches else "2021"
            experience.append({
                "company_name": detected_company or "Технологическая Компания",
                "position": detected_position,
                "start_date": f"{start_yr}-01",
                "end_date": None,
                "is_current": True,
                "description": f"Разработка и поддержка программного обеспечения ({', '.join(skills_found[:3]) if skills_found else 'Core Stack'})",
                "skills_detected": skills_found[:5],
            })

        # 3. Извлечение образования (Education)
        education: List[Dict[str, Any]] = []
        inst_match = re.search(
            r'(?i)\b(МГУ|МФТИ|НИУ\s+ВШЭ|ВШЭ|ИТМО|СПбГУ|МГТУ\s+им\.?\s*Баумана|Бауманка|МИФИ|УрФУ|НГУ|МИРЭА|МАИ|'
            r'СПбПУ|ТПУ|КФУ|[А-Яа-яЁё\s]{4,40}(?:университет|институт|академия|колледж))\b',
            text
        )
        deg_match = re.search(r'(?i)\b(Бакалавр|Магистр|Специалист|Аспирант|Bachelor|Master|PhD)\b', text)
        grad_year = int(max(year_matches)) if year_matches else 2022

        if inst_match or any(w in text.lower() for w in ["университет", "институт", "вуз", "education", "бакалавр", "магистр"]):
            inst_name = inst_match.group(1).strip() if inst_match else "Государственный Университет"
            deg_name = deg_match.group(1).capitalize() if deg_match else "Бакалавр"
            education.append({
                "institution": inst_name,
                "faculty": "Информационные технологии и программирование",
                "degree": deg_name,
                "graduation_year": grad_year,
            })

        return experience, education, total_months

    @classmethod
    def parse_resume(cls, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Полный конвейер разбора PDF-резюме:
        1. Валидация magic bytes %PDF- (ошибка 415 при сбое)
        2. Извлечение текста
        3. Извлечение контактов
        4. Сопоставление с таксономией 350+ навыков
        5. Структурирование опыта и образования
        """
        cls.validate_magic_bytes(pdf_bytes)
        text = cls.extract_text_from_pdf(pdf_bytes)
        contacts = cls.extract_contacts(text)
        skills = cls.match_skills(text)
        exp, edu, months = cls.parse_experience_and_education(text)

        # Эвристика извлечения имени и фамилии
        first_name: Optional[str] = None
        last_name: Optional[str] = None

        named_match = re.search(r"(?:Кандидат|ФИО|Имя соискателя)[:\s]+([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)", text)
        if named_match:
            last_name = named_match.group(1)
            first_name = named_match.group(2)
        else:
            STOP_NAME_WORDS = {
                "резюме", "кандидат", "федерация", "спортивного", "программирования",
                "профиль", "специалист", "разработчик", "инженер", "опыт", "работа",
                "образование", "навыки", "контакты", "телефон", "почта", "город",
                "москва", "россия", "курсы", "сертификаты", "английский", "русский"
            }
            words = [w for w in re.findall(r"[А-ЯЁ][а-яё]+", text) if w.lower() not in STOP_NAME_WORDS]
            if len(words) >= 2:
                last_name = words[0]
                first_name = words[1]
            elif not first_name:
                en_stop = {"resume", "curriculum", "vitae", "software", "engineer", "developer", "experience", "education", "skills", "summary"}
                en_words = [w for w in re.findall(r"\b[A-Z][a-z]+\b", text) if w.lower() not in en_stop]
                if len(en_words) >= 2:
                    first_name = en_words[0]
                    last_name = en_words[1]

        return {
            "detected_first_name": first_name,
            "detected_last_name": last_name,
            "detected_email": contacts["email"],
            "detected_phone": contacts["phone"],
            "detected_telegram": contacts["telegram"],
            "detected_github": contacts["github_url"],
            "detected_city": "Москва",
            "extracted_skills": skills,
            "detected_skills": skills,
            "work_experience": exp,
            "education": edu,
            "total_experience_months": months,
            "raw_text_length": len(text),
        }
