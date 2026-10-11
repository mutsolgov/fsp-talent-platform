"""
Adversarial Stress Test Suite — Challenger R17_2
Empirical verification of ReportLab Standardized Candidate PDF Profile Generator (app/services/pdf_generator.py)
and PDF data builder (app/api/v1/resume_pdf.py).

Tests:
1. Extreme empty dictionary ({}) in both Mode A (Masked) and Mode B (Full).
2. All fields None payload in both modes.
3. Theta variations: 0, 0.0, negative, string markers, NaN, None, vs calibrated.
4. Skills variations: [], None, non-empty.
5. Sport rank & FSP variations: fsp_id=None, fsp_id with sport_rank=None/"none"/"" vs real rank.
6. Conditions: city/work_format=None/""/"none", expected_salary=None/0/250000/invalid string.
7. Specialization & Grade markers: "Не выбрана", "Не определен", None, empty.
8. FSP achievements edge cases: None, [], [{}], [{championship_name: None}].
9. Contact privacy Mode A watermark & masked badge vs Mode B dossier.
10. XML/Markup injection resistance.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from app.services.pdf_generator import generate_fsp_profile_pdf
from app.api.v1.resume_pdf import _build_candidate_pdf_data
from app.models.candidate_profiles import CandidateProfile


def _extract_pdf_strings(pdf_bytes: bytes) -> List[str]:
    """Helper to extract drawn text strings from generated PDF bytes using PyMuPDF or fallback."""
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = [page.get_text() for page in doc]
        return texts
    except Exception:
        pass
    s_idx = pdf_bytes.find(b"stream\n") + len(b"stream\n")
    e_idx = pdf_bytes.find(b"\nendstream")
    if s_idx < 0 or e_idx < 0:
        return []
    raw = pdf_bytes[s_idx:e_idx]
    matches = re.findall(rb"\((.*?)\) Tj", raw)
    results = []
    for m in matches:
        try:
            decoded = m.decode("utf-8")
        except Exception:
            decoded = m.decode("latin-1", errors="ignore")
        decoded = decoded.replace(r"\(", "(").replace(r"\)", ")")
        results.append(decoded)
    return results


def test_pdf_extreme_empty_dict_mode_a():
    """Stress test: candidate_data = {} in Mode A (Masked)."""
    pdf = generate_fsp_profile_pdf({}, is_full_mode=False)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 2000
    assert pdf.startswith(b"%PDF-")

    strings = _extract_pdf_strings(pdf)
    text_corpus = " ".join(strings)

    # 1. Honest uncalibrated qualification
    assert "Квалификация: Ожидает верификации" in text_corpus
    # 2. Honest KITE score
    assert "Балл адаптивного тестирования KITE IRT: Тестирование не пройдено" in text_corpus
    # 3. Honest non-FSP / platform verification
    assert "Статус: Платформенная верификация" in text_corpus
    assert "История соревнований ФСП отсутствует" in text_corpus
    # 4. Honest unconfirmed skills warning
    assert "Навыки не подтверждены. Требуется прохождение онбординга и тестирования KITE." in text_corpus
    # 5. Honest conditions
    assert "Город: Не указан" in text_corpus
    assert "Формат работы: Не указан" in text_corpus
    assert "Ожидаемая ЗП: Не указана" in text_corpus
    # 6. Mode A watermark & masked notice
    assert "ПРЕДВАРИТЕЛЬНЫЙ ПРОФИЛЬ — 152-ФЗ" in text_corpus
    assert "[КОНТАКТЫ ЗАЩИЩЕНЫ 152-ФЗ РФ]" in text_corpus


def test_pdf_extreme_empty_dict_mode_b():
    """Stress test: candidate_data = {} in Mode B (Full dossier)."""
    pdf = generate_fsp_profile_pdf({}, is_full_mode=True)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 2000
    assert pdf.startswith(b"%PDF-")

    strings = _extract_pdf_strings(pdf)
    text_corpus = " ".join(strings)

    # Full mode must NOT contain the 152-ФЗ watermark or masked notice
    assert "ПРЕДВАРИТЕЛЬНЫЙ ПРОФИЛЬ — 152-ФЗ" not in text_corpus
    assert "[КОНТАКТЫ ЗАЩИЩЕНЫ 152-ФЗ РФ]" not in text_corpus

    # Missing contacts rendered as honest dashes
    assert "Email: —" in text_corpus
    assert "Телефон: —" in text_corpus

    # Honest uncalibrated fallbacks remain intact
    assert "Квалификация: Ожидает верификации" in text_corpus
    assert "Тестирование не пройдено" in text_corpus
    assert "Навыки не подтверждены" in text_corpus


def test_pdf_all_fields_none_payload():
    """Stress test: Every single known key explicitly mapped to None."""
    all_none_payload = {
        "id": None,
        "first_name": None,
        "last_name": None,
        "middle_name": None,
        "full_name": None,
        "masked_name": None,
        "email": None,
        "phone": None,
        "telegram": None,
        "github_url": None,
        "specialization": None,
        "grade": None,
        "theta": None,
        "test_score": None,
        "fsp_id": None,
        "fsp_verified": None,
        "sport_rank": None,
        "skills": None,
        "city": None,
        "work_format": None,
        "expected_salary": None,
        "fsp_achievements": None,
    }

    # Test Mode A
    pdf_a = generate_fsp_profile_pdf(all_none_payload, is_full_mode=False)
    assert pdf_a.startswith(b"%PDF-")
    corpus_a = " ".join(_extract_pdf_strings(pdf_a))
    assert "Квалификация: Ожидает верификации" in corpus_a
    assert "Тестирование не пройдено" in corpus_a
    assert "Навыки не подтверждены" in corpus_a
    assert "Город: Не указан" in corpus_a

    # Test Mode B
    pdf_b = generate_fsp_profile_pdf(all_none_payload, is_full_mode=True)
    assert pdf_b.startswith(b"%PDF-")
    corpus_b = " ".join(_extract_pdf_strings(pdf_b))
    assert "Email: —" in corpus_b
    assert "Телефон: —" in corpus_b


def test_pdf_theta_edge_cases():
    """Stress test: theta variations (0, 0.0, negative, string, NaN, calibrated)."""
    uncalibrated_thetas = [0, 0.0, -10.0, "invalid", None, float("nan"), "не определен", "0"]
    for th in uncalibrated_thetas:
        pdf = generate_fsp_profile_pdf({"theta": th}, is_full_mode=False)
        assert pdf.startswith(b"%PDF-")
        corpus = " ".join(_extract_pdf_strings(pdf))
        assert "Балл адаптивного тестирования KITE IRT: Тестирование не пройдено" in corpus

    # Calibrated positive theta
    pdf_calibrated = generate_fsp_profile_pdf({"theta": 88.5}, is_full_mode=False)
    corpus_calibrated = " ".join(_extract_pdf_strings(pdf_calibrated))
    assert "Балл адаптивного тестирования KITE IRT: 88.5 / 100" in corpus_calibrated


def test_pdf_skills_variations():
    """Stress test: skills variations ([], None, vs populated)."""
    # Empty list
    pdf_empty = generate_fsp_profile_pdf({"skills": []}, is_full_mode=False)
    corpus_empty = " ".join(_extract_pdf_strings(pdf_empty))
    assert "Навыки не подтверждены. Требуется прохождение онбординга и тестирования KITE." in corpus_empty

    # None
    pdf_none = generate_fsp_profile_pdf({"skills": None}, is_full_mode=False)
    corpus_none = " ".join(_extract_pdf_strings(pdf_none))
    assert "Навыки не подтверждены. Требуется прохождение онбординга и тестирования KITE." in corpus_none

    # Populated
    pdf_pop = generate_fsp_profile_pdf({"skills": ["Rust", "Go", "PostgreSQL"]}, is_full_mode=False)
    corpus_pop = " ".join(_extract_pdf_strings(pdf_pop))
    assert "Технологии: Rust, Go, PostgreSQL" in corpus_pop


def test_pdf_sport_rank_and_fsp_variations():
    """Stress test: Sport rank and FSP id combinations."""
    # 1. No FSP ID -> Non-FSP platform verification
    pdf_non_fsp = generate_fsp_profile_pdf({"fsp_id": None, "sport_rank": None}, is_full_mode=False)
    corpus_non_fsp = " ".join(_extract_pdf_strings(pdf_non_fsp))
    assert "Статус: Платформенная верификация" in corpus_non_fsp
    assert "История соревнований ФСП отсутствует" in corpus_non_fsp

    # 2. FSP ID present, but sport_rank is None -> "Без спортивного разряда"
    pdf_fsp_no_rank = generate_fsp_profile_pdf({"fsp_id": "FSP-77-01042", "sport_rank": None}, is_full_mode=False)
    corpus_fsp_no_rank = " ".join(_extract_pdf_strings(pdf_fsp_no_rank))
    assert "Спортивный разряд: Без спортивного разряда" in corpus_fsp_no_rank

    # 3. FSP ID present, sport_rank is empty string -> "Без спортивного разряда"
    pdf_fsp_empty_rank = generate_fsp_profile_pdf({"fsp_id": "FSP-77-01042", "sport_rank": ""}, is_full_mode=False)
    corpus_fsp_empty_rank = " ".join(_extract_pdf_strings(pdf_fsp_empty_rank))
    assert "Спортивный разряд: Без спортивного разряда" in corpus_fsp_empty_rank

    # 4. FSP ID present, sport_rank is "none" string -> "Без спортивного разряда"
    pdf_fsp_none_str = generate_fsp_profile_pdf({"fsp_id": "FSP-77-01042", "sport_rank": "none"}, is_full_mode=False)
    corpus_fsp_none_str = " ".join(_extract_pdf_strings(pdf_fsp_none_str))
    assert "Спортивный разряд: Без спортивного разряда" in corpus_fsp_none_str

    # 5. FSP ID present with real rank -> renders exact rank
    pdf_fsp_rank = generate_fsp_profile_pdf({"fsp_id": "FSP-77-01042", "sport_rank": "1-й спортивный разряд"}, is_full_mode=False)
    corpus_fsp_rank = " ".join(_extract_pdf_strings(pdf_fsp_rank))
    assert "Спортивный разряд: 1-й спортивный разряд" in corpus_fsp_rank


def test_pdf_conditions_and_preferences():
    """Stress test: city, work_format, and expected_salary variations."""
    # All None
    pdf_none = generate_fsp_profile_pdf({"city": None, "work_format": None, "expected_salary": None}, is_full_mode=False)
    corpus_none = " ".join(_extract_pdf_strings(pdf_none))
    assert "Город: Не указан" in corpus_none
    assert "Формат работы: Не указан" in corpus_none
    assert "Ожидаемая ЗП: Не указана (по договоренности)" in corpus_none

    # Empty string & 'none' string markers
    pdf_str = generate_fsp_profile_pdf({"city": "none", "work_format": "", "expected_salary": None}, is_full_mode=False)
    corpus_str = " ".join(_extract_pdf_strings(pdf_str))
    assert "Город: Не указан" in corpus_str
    assert "Формат работы: Не указан" in corpus_str

    # Valid values
    pdf_val = generate_fsp_profile_pdf({"city": "Екатеринбург", "work_format": "office", "expected_salary": 280000}, is_full_mode=False)
    corpus_val = " ".join(_extract_pdf_strings(pdf_val))
    assert "Город: Екатеринбург" in corpus_val
    assert "Формат работы: office" in corpus_val
    assert "Ожидаемая ЗП: 280 000 ₽" in corpus_val

    # String salary
    pdf_str_sal = generate_fsp_profile_pdf({"expected_salary": "по договоренности"}, is_full_mode=False)
    corpus_str_sal = " ".join(_extract_pdf_strings(pdf_str_sal))
    assert "Ожидаемая ЗП: по договоренности" in corpus_str_sal


def test_pdf_specialization_and_grade_markers():
    """Stress test: qualification markers ('Не выбрана', 'Не определен', 'none', empty)."""
    markers = [
        ("Не выбрана", "Не определен"),
        ("none", "none"),
        ("", ""),
        (None, None),
        ("не определена", "ожидает тестирования"),
    ]
    for spec, gr in markers:
        pdf = generate_fsp_profile_pdf({"specialization": spec, "grade": gr}, is_full_mode=False)
        corpus = " ".join(_extract_pdf_strings(pdf))
        assert "Квалификация: Ожидает верификации" in corpus

    # Real specialization & grade
    pdf_real = generate_fsp_profile_pdf({"specialization": "Backend", "grade": "Middle"}, is_full_mode=False)
    corpus_real = " ".join(_extract_pdf_strings(pdf_real))
    assert "Квалификация: Backend · Middle" in corpus_real


def test_pdf_fsp_achievements_robustness():
    """Stress test: Partial and empty achievement dictionaries."""
    adversarial_achievements = [
        None,
        [],
        [{}],
        [{"championship_name": None, "discipline": None, "place": None, "medal": None}],
        [{"championship_name": "Финал 2026", "place": 1, "medal": "Gold"}],
    ]
    for ach in adversarial_achievements:
        pdf = generate_fsp_profile_pdf(
            {"fsp_id": "FSP-101", "fsp_achievements": ach},
            is_full_mode=False,
        )
        assert isinstance(pdf, bytes)
        assert pdf.startswith(b"%PDF-")


def test_pdf_xml_markup_injection_resistance():
    """Stress test: XML-like characters in candidate fields must not break ReportLab Paragraph."""
    injection_payload = {
        "first_name": "<script>alert(1)</script>",
        "last_name": "O'Connor & Sons <tag>",
        "specialization": "Backend & Cloud <AI>",
        "grade": "Senior > Middle",
        "skills": ["C++ & C#", "<XML>", "HTML/CSS"],
        "city": "Town & Country",
        "bio": "Text with <b>valid</b> and <unclosed> tags & ampersands",
    }
    pdf = generate_fsp_profile_pdf(injection_payload, is_full_mode=False)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 2000
    assert pdf.startswith(b"%PDF-")


def test_build_candidate_pdf_data_zero_synthetic_defaults():
    """Verify that _build_candidate_pdf_data returns empty/None values for uncalibrated CandidateProfile."""
    # Construct an uncalibrated candidate model instance directly
    cand = CandidateProfile(
        id=777,
        user_id=888,
        first_name="Федор",
        last_name="Федотов",
        middle_name=None,
        city=None,
        work_format=None,
        expected_salary=None,
        fsp_id=None,
        fsp_verified=False,
        candidate_categorizations=[],
        candidate_skills=[],
        fsp_achievements=[],
        survey_data_json={},
    )

    data = _build_candidate_pdf_data(cand)

    assert data["specialization"] is None
    assert data["grade"] is None
    assert data["theta"] is None
    assert data["skills"] == []
    assert data["sport_rank"] is None
    assert data["city"] is None
    assert data["work_format"] is None
    assert data["expected_salary"] is None
    assert data["fsp_achievements"] == []
