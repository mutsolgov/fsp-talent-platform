"""
Unit tests for ReportLab Standardized Candidate PDF Profile Generator.
Defined in app/services/pdf_generator.py.
"""
from __future__ import annotations

import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from app.services.pdf_generator import generate_fsp_profile_pdf


def test_generate_pdf_masked_mode():
    candidate_data = {
        "id": 1042,
        "first_name": "Алексей",
        "last_name": "Кузнецов",
        "specialization": "Backend",
        "grade": "Senior",
        "theta": 92.4,
        "fsp_id": "FSP-77-01042",
        "fsp_verified": True,
        "sport_rank": "Кандидат в мастера спорта",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kafka"],
        "city": "Москва",
        "work_format": "remote",
        "expected_salary": 320000,
        "fsp_achievements": [
            {
                "championship_name": "Чемпионат России по спортивному программированию 2025",
                "discipline": "algorithmic",
                "place": 2,
                "medal": "silver",
            }
        ],
    }

    pdf_bytes = generate_fsp_profile_pdf(candidate_data, is_full_mode=False)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_full_unmasked_mode():
    candidate_data = {
        "id": 1042,
        "first_name": "Алексей",
        "last_name": "Кузнецов",
        "middle_name": "Игоревич",
        "email": "alex.kuznetsov@corp.ru",
        "phone": "+7 (999) 111-22-33",
        "telegram": "@alex_kuz",
        "github_url": "https://github.com/alex-kuz",
        "specialization": "Backend",
        "grade": "Senior",
        "theta": 92.4,
        "fsp_id": "FSP-77-01042",
        "fsp_verified": True,
        "sport_rank": "КМС",
        "skills": ["Python", "Go", "PostgreSQL", "Kubernetes"],
        "city": "Санкт-Петербург",
        "work_format": "hybrid",
        "expected_salary": 350000,
    }

    pdf_bytes = generate_fsp_profile_pdf(candidate_data, is_full_mode=True)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_pdf_non_fsp_candidate_fallback():
    candidate_data = {
        "id": 2045,
        "first_name": "Елена",
        "last_name": "Морозова",
        "specialization": "Frontend",
        "grade": "Middle",
        "theta": 84.0,
        "fsp_id": None,
        "fsp_verified": False,
        "skills": ["TypeScript", "React", "Next.js", "Tailwind CSS"],
        "city": "Казань",
        "work_format": "remote",
        "expected_salary": 200000,
        "fsp_achievements": [],
    }

    # Should generate cleanly without errors or crashes
    pdf_bytes = generate_fsp_profile_pdf(candidate_data, is_full_mode=False)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")
