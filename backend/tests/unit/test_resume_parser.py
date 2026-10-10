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
