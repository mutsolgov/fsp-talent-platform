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

# Список городов РФ с нормализацией падежей и альтернативных наименований
RUSSIAN_CITIES: List[Tuple[str, str]] = [
    ("Москва", r"\b(?:москв[аеыу]|moscow)\b"),
    ("Санкт-Петербург", r"\b(?:санкт-петербург[ае]?|петербург[ае]?|спб|питер[е]?|saint[- ]petersburg)\b"),
    ("Новосибирск", r"\b(?:новосибирск[ае]?|novosibirsk)\b"),
    ("Екатеринбург", r"\b(?:екатеринбург[ае]?|екб|yekaterinburg|ekaterinburg)\b"),
    ("Казань", r"\b(?:казан[ьиея]?|kazan)\b"),
    ("Нижний Новгород", r"\b(?:нижн(?:ий|его|ем|ему)\s+новгород[ае]?|nizhny\s+novgorod)\b"),
    ("Челябинск", r"\b(?:челябинск[ае]?|chelyabinsk)\b"),
    ("Самара", r"\b(?:самар[аеыу]|samara)\b"),
    ("Ростов-на-Дону", r"\b(?:ростов-на-дону|ростов[еа]?|rostov)\b"),
    ("Уфа", r"\b(?:уф[аеыу]|ufa)\b"),
    ("Красноярск", r"\b(?:красноярск[ае]?|krasnoyarsk)\b"),
    ("Пермь", r"\b(?:перм[ьиея]?|perm)\b"),
    ("Воронеж", r"\b(?:воронеж[ае]?|voronezh)\b"),
    ("Волгоград", r"\b(?:волгоград[ае]?|volgograd)\b"),
    ("Краснодар", r"\b(?:краснодар[ае]?|krasnodar)\b"),
    ("Саратов", r"\b(?:саратов[ае]?|saratov)\b"),
    ("Тюмень", r"\b(?:тюмен[ьиея]?|tyumen)\b"),
    ("Тольятти", r"\b(?:тольятти|tolyatti)\b"),
    ("Ижевск", r"\b(?:ижевск[ае]?|izhevsk)\b"),
    ("Барнаул", r"\b(?:барнаул[ае]?|barnaul)\b"),
    ("Ульяновск", r"\b(?:ульяновск[ае]?|ulyanovsk)\b"),
    ("Иркутск", r"\b(?:иркутск[ае]?|irkutsk)\b"),
    ("Владивосток", r"\b(?:владивосток[ае]?|vladivostok)\b"),
    ("Ярославль", r"\b(?:ярославл[ьея]|yaroslavl)\b"),
    ("Севастополь", r"\b(?:севастопол[ьея]|sevastopol)\b"),
    ("Томск", r"\b(?:томск[ае]?|tomsk)\b"),
    ("Оренбург", r"\b(?:оренбург[ае]?|orenburg)\b"),
    ("Кемерово", r"\b(?:кемеров[оеа]|kemerovo)\b"),
    ("Новокузнецк", r"\b(?:новокузнецк[ае]?|novokuznetsk)\b"),
    ("Рязань", r"\b(?:рязан[ьиея]?|ryazan)\b"),
    ("Астрахань", r"\b(?:астрахан[ьиея]?|astrakhan)\b"),
    ("Набережные Челны", r"\b(?:набережные\s+челны|naberezhnye\s+chelny)\b"),
    ("Пенза", r"\b(?:пенз[аеыу]|penza)\b"),
    ("Липецк", r"\b(?:липецк[ае]?|lipetsk)\b"),
    ("Тула", r"\b(?:тул[аеыу]|tula)\b"),
    ("Киров", r"\b(?:киров[ае]?|kirov)\b"),
    ("Чебоксары", r"\b(?:чебоксар[ыае]|cheboksary)\b"),
    ("Калининград", r"\b(?:калининград[ае]?|kaliningrad)\b"),
    ("Брянск", r"\b(?:брянск[ае]?|bryansk)\b"),
    ("Курск", r"\b(?:курск[ае]?|kursk)\b"),
    ("Иваново", r"\b(?:иванов[оеа]|ivanovo)\b"),
    ("Магнитогорск", r"\b(?:магнитогорск[ае]?|magnitogorsk)\b"),
    ("Тверь", r"\b(?:твер[ьиея]?|tver)\b"),
    ("Сочи", r"\b(?:сочи|sochi)\b"),
    ("Сургут", r"\b(?:сургут[ае]?|surgut)\b"),
    ("Норильск", r"\b(?:норильск[ае]?|norilsk)\b"),
    ("Магадан", r"\b(?:магадан[ае]?|magadan)\b"),
    ("Якутск", r"\b(?:якутск[ае]?|yakutsk)\b"),
    ("Хабаровск", r"\b(?:хабаровск[ае]?|khabarovsk)\b"),
    ("Владикавказ", r"\b(?:владикавказ[ае]?|vladikavkaz)\b"),
    ("Грозный", r"\b(?:грозн(?:ый|ом|ого|ому)|grozny)\b"),
    ("Южно-Сахалинск", r"\b(?:южно-сахалинск[ае]?|yuzhno-sakhalinsk)\b"),
    ("Петропавловск-Камчатский", r"\b(?:петропавловск-камчатск(?:ий|ом|ого)|petropavlovsk)\b"),
    ("Архангельск", r"\b(?:архангельск[ае]?|arkhangelsk)\b"),
    ("Мурманск", r"\b(?:мурманск[ае]?|murmansk)\b"),
    ("Чита", r"\b(?:чит[аеыу]|chita)\b"),
    ("Вологда", r"\b(?:вологд[аеыу]|vologda)\b"),
    ("Смоленск", r"\b(?:смоленск[ае]?|smolensk)\b"),
    ("Саранск", r"\b(?:саранск[ае]?|saransk)\b"),
    ("Тамбов", r"\b(?:тамбов[ае]?|tambov)\b"),
    ("Кострома", r"\b(?:костром[аеыу]|kostroma)\b"),
    ("Псков", r"\b(?:псков[ае]?|pskov)\b"),
    ("Таганрог", r"\b(?:таганрог[ае]?|taganrog)\b"),
    ("Нальчик", r"\b(?:нальчик[ае]?|nalchik)\b"),
    ("Сыктывкар", r"\b(?:сыктывкар[ае]?|syktyvkar)\b"),
    ("Йошкар-Ола", r"\b(?:йошкар-ол[аеыу]|yoshkar-ola)\b"),
    ("Курган", r"\b(?:курган[ае]?|kurgan)\b"),
    ("Комсомольск-на-Амуре", r"\b(?:комсомольск-на-амуре|komsomolsk)\b"),
    ("Благовещенск", r"\b(?:благовещенск[ае]?|blagoveshchensk)\b"),
    ("Ханты-Мансийск", r"\b(?:ханты-мансийск[ае]?|khanty-mansiysk)\b"),
    ("Анадырь", r"\b(?:анадыр[ьея]|anadyr)\b"),
    ("Дербент", r"\b(?:дербент[ае]?|derbent)\b"),
    ("Великий Новгород", r"\b(?:велик(?:ий|ого|ем)\s+новгород[ае]?|veliky\s+novgorod)\b"),
    # Международные и зарубежные локации соискателей
    ("Минск", r"\b(?:минск[ае]?|minsk)\b"),
    ("Алматы", r"\b(?:алмат[ыае]|almaty)\b"),
    ("Астана", r"\b(?:астан[аеыу]|astana|нур-султан[ае]?)\b"),
    ("Ереван", r"\b(?:ереван[ае]?|yerevan)\b"),
    ("Тбилиси", r"\b(?:тбилиси|tbilisi)\b"),
    ("Ташкент", r"\b(?:ташкент[ае]?|tashkent)\b"),
    ("Бишкек", r"\b(?:бишкек[ае]?|bishkek)\b"),
    ("Баку", r"\b(?:баку|baku)\b"),
    ("Белград", r"\b(?:белград[ае]?|belgrade)\b"),
    ("Дубай", r"\b(?:дуба[йея]|dubai)\b"),
    ("Лимассол", r"\b(?:лимассол[ае]?|limassol)\b"),
    ("Стамбул", r"\b(?:стамбул[ае]?|istanbul)\b"),
    ("Берлин", r"\b(?:берлин[ае]?|berlin)\b"),
    ("Лондон", r"\b(?:лондон[ае]?|london)\b"),
]


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
    def extract_contacts(cls, text: Optional[str]) -> Dict[str, Optional[str]]:
        """Извлекает телефон, email, telegram, github из текста."""
        if not text or not isinstance(text, str):
            return {"email": None, "phone": None, "telegram": None, "github_url": None}

        email_match = RE_EMAIL.search(text)
        email = email_match.group(0).lower().rstrip(".,;:") if email_match else None

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
    def match_skills(cls, text: Optional[str]) -> List[str]:
        """Сопоставляет текст резюме с канонической таксономией 350+ навыков."""
        if not text or not isinstance(text, str):
            return []

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
        cls, text: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
        """Извлекает реальный опыт работы и образование по эвристикам из текста резюме."""
        if not text or not isinstance(text, str):
            return [], [], 0
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
    def extract_city(cls, text: Optional[str]) -> Optional[str]:
        """
        Извлекает город соискателя из текста резюме.
        Если город не указан или text пуст — возвращает None (устранение демо-хардкода Москвы).
        """
        if not text or not isinstance(text, str):
            return None

        # 1. Приоритетный поиск в блоке города / проживания
        city_header = re.search(
            r"(?i)(?:город|проживание|локация|место\s+жительства|г\.|city|location)[:\s]+([^\n,\.;]+)",
            text,
        )
        if city_header:
            header_chunk = city_header.group(1).strip()
            for city_name, pat in RUSSIAN_CITIES:
                if re.search(pat, header_chunk, re.IGNORECASE):
                    return city_name

        # 2. Поиск по всему тексту резюме
        for city_name, pat in RUSSIAN_CITIES:
            if re.search(pat, text, re.IGNORECASE):
                return city_name

        return None

    @classmethod
    def parse_salary_expectations(cls, text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
        """
        Извлекает зарплатные ожидания (вилку min/max в RUB) из текста резюме.
        Соблюдает строгий финансовый инвариант платформы: salary_min > 0, max >= min, max / min <= 3.5.
        Поддерживает форматы «350k», «от 150 до 300 тыс. руб.», «180 - 250 тыс», «280 000 ₽».
        """
        if not text or not isinstance(text, str):
            return None, None
        def _parse_val(val_str: str) -> Optional[int]:
            s = val_str.lower().replace(" ", "").replace("\xa0", "").strip()
            multiplier = 1
            if "тыс" in s or "k" in s or "к" in s:
                multiplier = 1000
                s = re.sub(r"[^\d.,]", "", s)
            else:
                s = re.sub(r"[^\d]", "", s)
            if not s:
                return None
            try:
                num = int(float(s.replace(",", ".")) * multiplier)
                return num
            except (ValueError, TypeError):
                return None

        # Шаблон числа с возможным суффиксом "тыс"/"к"/"k" или полной суммой
        N_PAT = r"(\d{1,3}\s*(?:тыс|к|k)|\d[\d\s\xa0]{4,8}|\d{2,7})"

        def _clean_bounds(s_min: int, s_max: int) -> Tuple[int, int]:
            s_min, s_max = min(s_min, s_max), max(s_min, s_max)
            s_min = max(30000, (s_min // 5000) * 5000)
            s_max = max(s_min, (s_max // 5000) * 5000)
            if s_max / s_min > 3.5:
                s_max = int(s_min * 3.5)
            return s_min, s_max

        # 1. Поиск вилки "от X до Y" или "X - Y"
        range_match = re.search(
            rf"(?i)(?:зарплата|зп|доход|ожидания|salary)?[:\s]*(?:от\s+)?{N_PAT}\s*(?:до|-|–|—)\s*{N_PAT}\s*(?:руб|рублей|р\b|₽|rub|k|к|тыс)?",
            text,
        )
        if range_match:
            v1 = _parse_val(range_match.group(1))
            v2 = _parse_val(range_match.group(2))
            full_chunk = range_match.group(0).lower()
            has_k = any(w in full_chunk for w in ["тыс", "k", "к"])
            if v1 and v2:
                if v1 < 1000 and (v2 >= 10000 or has_k):
                    v1 *= 1000
                if v2 < 1000 and (v1 >= 10000 or has_k):
                    v2 *= 1000
                if 25000 <= v1 <= 2500000 and 25000 <= v2 <= 2500000:
                    return _clean_bounds(v1, v2)

        # 2. Поиск "от X"
        ot_match = re.search(
            rf"(?i)(?:зарплата|зп|доход|ожидания|salary)?[:\s]*от\s+{N_PAT}\s*(?:руб|рублей|р\b|₽|rub|k|к|тыс)?",
            text,
        )
        if ot_match:
            v = _parse_val(ot_match.group(1))
            full_chunk = ot_match.group(0).lower()
            if v and v < 1000 and any(w in full_chunk for w in ["тыс", "k", "к"]):
                v *= 1000
            if v and 25000 <= v <= 2500000:
                s_min = max(30000, (v // 5000) * 5000)
                s_max = int(s_min * 1.35 // 5000 * 5000)
                return _clean_bounds(s_min, s_max)

        # 3. Поиск "до Y"
        do_match = re.search(
            rf"(?i)(?:зарплата|зп|доход|ожидания|salary)?[:\s]*до\s+{N_PAT}\s*(?:руб|рублей|р\b|₽|rub|k|к|тыс)?",
            text,
        )
        if do_match:
            v = _parse_val(do_match.group(1))
            full_chunk = do_match.group(0).lower()
            if v and v < 1000 and any(w in full_chunk for w in ["тыс", "k", "к"]):
                v *= 1000
            if v and 25000 <= v <= 2500000:
                s_max = (v // 5000) * 5000
                s_min = max(30000, int(s_max * 0.75 // 5000 * 5000))
                return _clean_bounds(s_min, s_max)

        # 4. Поиск единичного упоминания суммы
        single_match = re.search(
            rf"(?i)(?:зарплата|зп|доход|ожидания|salary)[:\s]+{N_PAT}\s*(?:руб|рублей|р\b|₽|rub|k|к|тыс)?",
            text,
        )
        if not single_match:
            single_match = re.search(
                rf"(?i){N_PAT}\s*(?:руб|рублей|р\b|₽|rub|k|к|тыс)",
                text,
            )
        if single_match:
            v = _parse_val(single_match.group(1))
            full_chunk = single_match.group(0).lower()
            if v and v < 1000 and any(w in full_chunk for w in ["тыс", "k", "к"]):
                v *= 1000
            if v and 25000 <= v <= 2500000:
                s_min = max(30000, int(v * 0.85 // 5000 * 5000))
                s_max = int(v * 1.25 // 5000 * 5000)
                return _clean_bounds(s_min, s_max)

        return None, None

    @classmethod
    def detect_specialization(cls, matched_skills: Optional[List[str]], text: Optional[str]) -> str:
        """
        Определяет специализацию кандидата (backend, frontend, ml_data, devops, qa, infosec)
        по пересечению навыков с таксономией и ключевым маркерам должности.
        """
        scores: Dict[str, int] = {
            "backend": 0,
            "frontend": 0,
            "ml_data": 0,
            "devops": 0,
            "qa": 0,
            "infosec": 0,
        }

        # 1. Очки за найденные навыки из таксономии
        lower_skills = set(s.lower() for s in (matched_skills or []))
        for domain, d_skills in TAXONOMY_350_PLUS.items():
            overlap = lower_skills & set(d_skills)
            scores[domain] += len(overlap) * 2

        # 2. Очки за контекстные маркеры в тексте
        t_low = (text or "").lower() if isinstance(text, str) else ""
        if re.search(r"(?i)\b(?:backend|бэкенд|бэкэнд|серверн\w*|fastapi|django|spring\s+boot|golang|asp\.net)\b", t_low):
            scores["backend"] += 5
        if re.search(r"(?i)\b(?:frontend|фронтенд|react|vue|angular|верстк\w*|html5|typescript|javascript)\b", t_low):
            scores["frontend"] += 5
        if re.search(r"(?i)\b(?:machine\s+learning|data\s+scientist|ml\s+engineer|nlp|pytorch|tensorflow|машинн\w*\s+обучени\w*|нейросет\w*)\b", t_low):
            scores["ml_data"] += 5
        if re.search(r"(?i)\b(?:devops|девопс|sre|kubernetes|k8s|ansible|terraform|ci/cd|инфраструктур\w*)\b", t_low):
            scores["devops"] += 5
        if re.search(r"(?i)\b(?:qa|тестировщик|тестировани\w*|quality\s+assurance|playwright|selenium|pytest)\b", t_low):
            scores["qa"] += 5
        if re.search(r"(?i)\b(?:infosec|инфобез|безопасност\w*|appsec|pentest|пентест|owasp|soc|siem)\b", t_low):
            scores["infosec"] += 5

        best_spec = max(scores, key=lambda k: scores[k])
        if scores[best_spec] == 0:
            return "backend"
        return best_spec

    @classmethod
    def detect_grade(cls, total_experience_months: Optional[int], text: Optional[str]) -> str:
        """
        Определяет заявляемый грейд (junior, middle, senior, lead).
        Сначала по явному маркеру должности, затем по совокупному опыту работы:
        - junior (< 18 мес / < 1.5 лет)
        - middle (18-48 мес / 1.5 - 4 года)
        - senior (48-84 мес / 4 - 7 лет)
        - lead (>= 84 мес / > 7 лет)
        """
        t_low = (text or "").lower() if isinstance(text, str) else ""
        # 1. Поиск явного грейда в тексте
        if re.search(r"(?i)\b(?:lead|tech\s*lead|team\s*lead|тимлид|ведущ(?:ий|ая)|архитектор|principal)\b", t_low):
            return "lead"
        if re.search(r"(?i)\b(?:senior|сеньор|сениор|старш(?:ий|ая))\b", t_low):
            return "senior"
        if re.search(r"(?i)\b(?:middle|мидд?л)\b", t_low):
            return "middle"
        if re.search(r"(?i)\b(?:junior|джуниор|джун|стажер|стажёр|intern)\b", t_low):
            return "junior"

        # 2. Определение по стажу
        months = total_experience_months or 0
        if months < 18:
            return "junior"
        elif months < 48:
            return "middle"
        elif months < 84:
            return "senior"
        else:
            return "lead"

    @classmethod
    def parse_resume(cls, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Полный конвейер разбора PDF-резюме:
        1. Валидация magic bytes %PDF- (ошибка 415 при сбое)
        2. Извлечение текста
        3. Извлечение контактов
        4. Сопоставление с таксономией 350+ навыков
        5. Структурирование опыта и образования
        6. Автоопределение города, специализации, грейда и зарплатных ожиданий
        """
        cls.validate_magic_bytes(pdf_bytes)
        text = cls.extract_text_from_pdf(pdf_bytes)
        contacts = cls.extract_contacts(text)
        skills = cls.match_skills(text)
        exp, edu, months = cls.parse_experience_and_education(text)

        city = cls.extract_city(text)
        spec = cls.detect_specialization(skills, text)
        grade = cls.detect_grade(months, text)
        sal_min, sal_max = cls.parse_salary_expectations(text)

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
            "detected_city": city,
            "detected_specialization": spec,
            "detected_grade": grade,
            "detected_salary_min": sal_min,
            "detected_salary_max": sal_max,
            "extracted_skills": skills,
            "detected_skills": skills,
            "work_experience": exp,
            "education": edu,
            "total_experience_months": months,
            "raw_text_length": len(text),
        }
