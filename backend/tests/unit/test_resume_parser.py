"""
Unit Test Suite for Resume PDF Parser & Skill Matcher.
Verifies magic bytes %PDF- validation (EC-18 raises InvalidPdfFormatError),
regex contact extraction, and canonical skill matching against 350+ skills taxonomy.
"""
from __future__ import annotations

import pytest

from app.services.resume_parser import (
    InvalidPdfFormatError,
    ResumeParser,
    TAXONOMY_350_PLUS,
)


def test_magic_bytes_valid_pdf():
    """Файл, начинающийся с b'%PDF-', проходит валидацию успешно."""
    valid_pdf_sample = b"%PDF-1.4\n1 0 obj\n<< /Title (Resume) >>\nendobj\ntrailer\n%%EOF"
    ResumeParser.validate_magic_bytes(valid_pdf_sample)


def test_magic_bytes_invalid_rejects_ec18():
    """EC-18: Не-PDF файлы (DOCX, ZIP, HTML, текстовые строки) отклоняются с InvalidPdfFormatError."""
    # ZIP / DOCX magic bytes
    with pytest.raises(InvalidPdfFormatError, match=r"%PDF-"):
        ResumeParser.validate_magic_bytes(b"PK\x03\x04\x14\x00\x06\x00")

    # HTML
    with pytest.raises(InvalidPdfFormatError, match=r"%PDF-"):
        ResumeParser.validate_magic_bytes(b"<!DOCTYPE html><html><body>Resume</body></html>")

    # Пустой файл
    with pytest.raises(InvalidPdfFormatError, match=r"%PDF-"):
        ResumeParser.validate_magic_bytes(b"")

    # Обычный текст
    with pytest.raises(InvalidPdfFormatError, match=r"%PDF-"):
        ResumeParser.validate_magic_bytes(b"Ivan Ivanov, Python developer")


def test_contact_extraction_regex():
    """Проверка извлечения email, телефона и telegram-аккаунта из текстового блока."""
    sample_text = """
    Иванов Иван Иванович
    Email: ivan.senior@techcorp.ru
    Телефон: +7 (999) 123-45-67
    Telegram: @ivan_code_master
    GitHub: https://github.com/ivan-dev
    """
    contacts = ResumeParser.extract_contacts(sample_text)

    assert contacts["email"] == "ivan.senior@techcorp.ru"
    assert "+7 (999) 123-45-67" in contacts["phone"]
    assert contacts["telegram"] == "@ivan_code_master"
    assert contacts["github_url"] == "https://github.com/ivan-dev"


def test_skill_matching_against_canonical_taxonomy():
    """Проверка сопоставления навыков из резюме с 350+ таксономией."""
    sample_text = """
    Опыт работы: 5 лет в роли Senior Backend Developer.
    Стек: Python, FastAPI, PostgreSQL, Docker, Redis, Kafka, SQLAlchemy, Linux.
    Знаком с архитектурными паттернами: Microservices, System Design, CQRS.
    """
    detected_skills = ResumeParser.match_skills(sample_text)

    assert isinstance(detected_skills, list)
    assert "python" in detected_skills
    assert "fastapi" in detected_skills
    assert "postgresql" in detected_skills
    assert "docker" in detected_skills
    assert "redis" in detected_skills
    assert "kafka" in detected_skills
    assert "microservices" in detected_skills


def test_taxonomy_350_plus_completeness():
    """Проверка полноты таксономии навыков (суммарно >= 350 навыков по всем специализациям)."""
    total_skills = sum(len(skills) for skills in TAXONOMY_350_PLUS.values())
    assert total_skills >= 350, f"Таксономия должна содержать >= 350 навыков, содержит {total_skills}"
    assert "backend" in TAXONOMY_350_PLUS
    assert "frontend" in TAXONOMY_350_PLUS
    assert "ml_data" in TAXONOMY_350_PLUS
    assert "devops" in TAXONOMY_350_PLUS
    assert "qa" in TAXONOMY_350_PLUS
    assert "infosec" in TAXONOMY_350_PLUS


def test_city_extraction_known_and_none():
    """Проверка определения городов РФ и возврат None при отсутствии (устранение хардкода Москвы)."""
    assert ResumeParser.extract_city("Проживание: г. Санкт-Петербург, готов к релокации") == "Санкт-Петербург"
    assert ResumeParser.extract_city("Локация: Казань") == "Казань"
    assert ResumeParser.extract_city("Живу в Екатеринбурге, удаленка") == "Екатеринбург"
    assert ResumeParser.extract_city("Иванов Иван, Python разработчик, удаленная работа") is None


def test_salary_expectations_parsing():
    """Проверка парсинга зарплатной вилки и соблюдения инварианта max/min <= 3.5."""
    min_val, max_val = ResumeParser.parse_salary_expectations("Ожидания по ЗП: от 180 000 до 250 000 руб")
    assert min_val == 180000
    assert max_val == 250000
    assert max_val / min_val <= 3.5

    min_val2, max_val2 = ResumeParser.parse_salary_expectations("Желаемый доход: 200 000 ₽")
    assert min_val2 is not None and max_val2 is not None
    assert min_val2 <= 200000 <= max_val2
    assert max_val2 / min_val2 <= 3.5

    min_val3, max_val3 = ResumeParser.parse_salary_expectations("Зарплата: 250 тыс руб")
    assert min_val3 is not None and max_val3 is not None
    assert max_val3 / min_val3 <= 3.5

    # Если зарплата не указана
    no_min, no_max = ResumeParser.parse_salary_expectations("Условия: удаленная работа, гибкий график")
    assert no_min is None
    assert no_max is None


def test_specialization_detection():
    """Проверка автоопределения канонической специализации из 6 категорий."""
    fe_skills = ["react", "typescript", "tailwind", "next.js"]
    assert ResumeParser.detect_specialization(fe_skills, "Frontend Developer, React, Redux") == "frontend"

    ml_skills = ["pytorch", "pandas", "numpy", "transformers"]
    assert ResumeParser.detect_specialization(ml_skills, "ML Engineer, Data Science, LLM") == "ml_data"

    devops_skills = ["kubernetes", "docker", "terraform", "ansible"]
    assert ResumeParser.detect_specialization(devops_skills, "DevOps Engineer, SRE, CI/CD") == "devops"

    qa_skills = ["playwright", "pytest", "selenium", "allure"]
    assert ResumeParser.detect_specialization(qa_skills, "QA Automation Engineer") == "qa"

    sec_skills = ["burp suite", "owasp", "metasploit", "wireshark"]
    assert ResumeParser.detect_specialization(sec_skills, "Application Security Specialist") == "infosec"


def test_grade_detection_by_experience_and_marker():
    """Проверка автоопределения грейда по шкале стажа (<18, 18-48, 48-84, >=84 мес) и маркерам."""
    assert ResumeParser.detect_grade(12, "Разработчик") == "junior"
    assert ResumeParser.detect_grade(36, "Разработчик") == "middle"
    assert ResumeParser.detect_grade(60, "Разработчик") == "senior"
    assert ResumeParser.detect_grade(96, "Разработчик") == "lead"

    # Явные маркеры имеют приоритет
    assert ResumeParser.detect_grade(12, "Senior Python Developer") == "senior"
    assert ResumeParser.detect_grade(70, "Junior QA Engineer") == "junior"
    assert ResumeParser.detect_grade(24, "Team Lead Backend") == "lead"


def test_parser_none_and_empty_edge_cases():
    """Проверка устойчивости всех методов парсера к аргументам None и пустым строкам."""
    assert ResumeParser.extract_city(None) is None
    assert ResumeParser.extract_city("") is None
    assert ResumeParser.parse_salary_expectations(None) == (None, None)
    assert ResumeParser.parse_salary_expectations("") == (None, None)
    assert ResumeParser.detect_specialization(None, None) == "backend"
    assert ResumeParser.detect_specialization([], "") == "backend"
    assert ResumeParser.detect_grade(None, None) == "junior"
    assert ResumeParser.detect_grade(0, "") == "junior"
    assert ResumeParser.extract_contacts(None) == {
        "email": None, "phone": None, "telegram": None, "github_url": None
    }
    assert ResumeParser.match_skills(None) == []
    assert ResumeParser.parse_experience_and_education(None) == ([], [], 0)


def test_salary_expectations_advanced_formats():
    """Проверка продвинутых паттернов зарплатной вилки (k, тыс, от-до)."""
    # 150 - 200 тыс руб
    s_min, s_max = ResumeParser.parse_salary_expectations("Зарплата: 150 - 200 тыс руб")
    assert s_min == 150000 and s_max == 200000
    assert s_max / s_min <= 3.5

    # 150-200k
    s_min2, s_max2 = ResumeParser.parse_salary_expectations("150-200k")
    assert s_min2 == 150000 and s_max2 == 200000

    # 150к - 200к
    s_min3, s_max3 = ResumeParser.parse_salary_expectations("150к - 200к")
    assert s_min3 == 150000 and s_max3 == 200000

    # от 150 000 руб
    s_min4, s_max4 = ResumeParser.parse_salary_expectations("от 150 000 руб")
    assert s_min4 == 150000 and s_max4 == 200000


def test_contacts_email_clean_punctuation():
    """Проверка очистки email от замыкающей пунктуации предложения."""
    text = "Свяжитесь со мной по почте ivan.dev@corp.ru. Жду ответа!"
    contacts = ResumeParser.extract_contacts(text)
    assert contacts["email"] == "ivan.dev@corp.ru"


