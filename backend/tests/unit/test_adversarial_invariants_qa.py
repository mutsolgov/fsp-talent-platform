"""
Adversarial QA & Invariants Verification Test Suite.
Verifies all 3 core invariant domains mandated by ТЗ ФСП:
1. Financial and Domain Invariants:
   - Salary range bounds: salary_min > 0, salary_max >= salary_min, salary_max / salary_min <= 3.5, currency strictly RUB
     across employer_needs, vacancies, candidate_profile, resume_parser.
   - Ranking Engine Multi-Factor formula for FSP (0.40 / 0.25 / 0.20 / 0.15) and Non-FSP (0.52 / 0.30 / 0.00 / 0.18).
2. Resume Parser Stress Testing:
   - Corrupted PDF magic bytes, empty files, files without contacts, files without experience.
   - Non-standard salary formats: «350k», «350к», «от 150 до 300 тыс. руб.», «180 - 250 тыс», «280 000 ₽».
   - Exotic Russian cities (Норильск, Магадан, Сургут, Якутск, Анадырь) and foreign locations (Тбилиси, Ереван, Дубай, Алматы, Минск).
3. Psychometrics KITE IRT 3PL:
   - Birnbaum 3PL model calibration across Junior, Middle, Senior, Lead.
   - Fisher Information and Standard Error SE <= 0.32 at grade thresholds.
   - Bayesian EAP ability estimation on 61 quadrature nodes with log-sum-exp stability.
   - Non-coercive evaluation and complete downgrade protection.
"""
from __future__ import annotations

import math
import os
import sys
import pytest
from pydantic import ValidationError

# Ensure backend directory in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.schemas.employer_needs import CreateEmployerNeedRequest, UpdateEmployerNeedRequest
from app.schemas.vacancies import CreateVacancyRequest, UpdateVacancyRequest
from app.schemas.candidate_profile import OnboardingSurveyRequest, CandidateProfileUpdateRequest
from app.schemas.resume_pdf import ResumeParsedResponse
from app.services.ranking_engine import (
    calculate_candidate_score,
    calculate_weights,
    calculate_grade_multiplier,
    calculate_stack_subscore,
    calculate_fsp_subscore,
    compute_freshness_subscore,
    WEIGHTS_WITH_FSP,
    WEIGHTS_WITHOUT_FSP,
)
from app.services.resume_parser import (
    ResumeParser,
    InvalidPdfFormatError,
    TAXONOMY_350_PLUS,
)
from app.services.kite_irt import (
    IRT3PLItem,
    BayesianEAPEstimator,
    compute_test_information,
    compute_sem,
)
from app.services.grading_engine import GradingEngine
from scripts.seed_canonical_items import BATTERY_SPECS, GRADE_BASE_DIFFICULTY


# ==============================================================================
# SECTION 1: FINANCIAL & DOMAIN INVARIANTS (ТЗ ФСП)
# ==============================================================================

class TestFinancialAndDomainInvariants:
    """Verifies salary invariants and ranking weights across all endpoints."""

    def test_employer_needs_salary_invariants(self):
        """employer_needs: min > 0, max >= min, max / min <= 3.5, currency RUB."""
        base_valid = {
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Lead",
            "team_tasks_text": "High load architecture",
            "salary_min": 100000,
            "salary_max": 250000,
            "salary_currency": "RUB",
        }
        # 1. Valid boundary: ratio exactly 3.5
        req_35 = CreateEmployerNeedRequest(**{**base_valid, "salary_min": 100000, "salary_max": 350000})
        assert req_35.salary_max / req_35.salary_min == 3.5

        # 2. Valid equality: min == max
        req_eq = CreateEmployerNeedRequest(**{**base_valid, "salary_min": 150000, "salary_max": 150000})
        assert req_eq.salary_min == req_eq.salary_max

        # 3. Invalid: min <= 0
        with pytest.raises(ValidationError):
            CreateEmployerNeedRequest(**{**base_valid, "salary_min": 0, "salary_max": 150000})
        with pytest.raises(ValidationError):
            CreateEmployerNeedRequest(**{**base_valid, "salary_min": -50000, "salary_max": 150000})

        # 4. Invalid: max < min
        with pytest.raises(ValidationError):
            CreateEmployerNeedRequest(**{**base_valid, "salary_min": 200000, "salary_max": 150000})

        # 5. Invalid: max / min > 3.5 (spread too wide)
        with pytest.raises(ValidationError):
            CreateEmployerNeedRequest(**{**base_valid, "salary_min": 100000, "salary_max": 350001})

        # 6. Invalid: non-RUB currency
        with pytest.raises(ValidationError):
            CreateEmployerNeedRequest(**{**base_valid, "salary_currency": "USD"})

        # 7. UpdateEmployerNeedRequest validations
        with pytest.raises(ValidationError):
            UpdateEmployerNeedRequest(salary_min=100000, salary_max=400000)
        with pytest.raises(ValidationError):
            UpdateEmployerNeedRequest(salary_min=-1)
        with pytest.raises(ValidationError):
            UpdateEmployerNeedRequest(salary_currency="EUR")

    def test_vacancies_salary_invariants(self):
        """vacancies: min > 0, max >= min, max / min <= 3.5, currency RUB."""
        base_vac = {
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Middle Python Developer",
            "description": "Разработка распределенных микросервисов в финтех-проекте",
            "required_skills": ["python", "fastapi", "postgresql"],
            "salary_min": 150000,
            "salary_max": 300000,
            "salary_currency": "RUB",
        }
        # 1. Valid creation
        vac = CreateVacancyRequest(**base_vac)
        assert vac.salary_currency == "RUB"

        # 2. Invalid min <= 0
        with pytest.raises(ValidationError):
            CreateVacancyRequest(**{**base_vac, "salary_min": 0})

        # 3. Invalid max < min
        with pytest.raises(ValidationError):
            CreateVacancyRequest(**{**base_vac, "salary_min": 250000, "salary_max": 200000})

        # 4. Invalid spread > 3.5
        with pytest.raises(ValidationError):
            CreateVacancyRequest(**{**base_vac, "salary_min": 100000, "salary_max": 360000})

        # 5. Invalid non-RUB
        with pytest.raises(ValidationError):
            CreateVacancyRequest(**{**base_vac, "salary_currency": "USD"})

        # 6. UpdateVacancyRequest checks
        with pytest.raises(ValidationError):
            UpdateVacancyRequest(salary_min=100000, salary_max=500000)
        with pytest.raises(ValidationError):
            UpdateVacancyRequest(salary_min=200000, salary_max=100000)

    def test_candidate_profile_salary_invariants(self):
        """candidate_profile: Onboarding & ProfileUpdate salary bounds validation."""
        base_onb = {
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "skills": ["python", "docker"],
            "city": "Москва",
            "salary_min": 150000,
            "salary_max": 300000,
            "salary_currency": "RUB",
        }
        # 1. Valid onboarding
        onb = OnboardingSurveyRequest(**base_onb)
        assert onb.salary_currency == "RUB"

        # 2. Invalid min <= 0
        with pytest.raises(ValidationError):
            OnboardingSurveyRequest(**{**base_onb, "salary_min": 0})

        # 3. Invalid max < min
        with pytest.raises(ValidationError):
            OnboardingSurveyRequest(**{**base_onb, "salary_min": 250000, "salary_max": 180000})

        # 4. Invalid ratio > 3.5
        with pytest.raises(ValidationError):
            OnboardingSurveyRequest(**{**base_onb, "salary_min": 100000, "salary_max": 360000})

        # 5. Invalid non-RUB currency
        with pytest.raises(ValidationError):
            OnboardingSurveyRequest(**{**base_onb, "salary_currency": "USD"})

        # 6. CandidateProfileUpdateRequest invalid checks
        with pytest.raises(ValidationError):
            CandidateProfileUpdateRequest(salary_min=200000, salary_max=150000)
        with pytest.raises(ValidationError):
            CandidateProfileUpdateRequest(salary_min=100000, salary_max=400000)
        with pytest.raises(ValidationError):
            CandidateProfileUpdateRequest(salary_currency="EUR")

    def test_ranking_engine_weights_and_recalibration(self):
        """Formula verification: FSP (0.40/0.25/0.20/0.15) and Non-FSP (0.52/0.30/0.00/0.18)."""
        w_fsp = calculate_weights(has_fsp=True)
        assert w_fsp == (0.40, 0.25, 0.20, 0.15), f"FSP weights mismatch: got {w_fsp}"
        assert abs(sum(w_fsp) - 1.00) < 1e-6, "FSP weights must sum to exactly 1.00"

        w_non_fsp = calculate_weights(has_fsp=False)
        assert w_non_fsp == (0.52, 0.30, 0.00, 0.18), f"Non-FSP weights mismatch: got {w_non_fsp}"
        assert abs(sum(w_non_fsp) - 1.00) < 1e-6, "Non-FSP weights must sum to exactly 1.00"

    def test_ranking_engine_zero_glass_ceiling_and_meritocracy(self):
        """Non-FSP candidate can achieve 100.0 and outrank weaker FSP candidates."""
        # Perfect Non-FSP candidate
        res_non_fsp = calculate_candidate_score(
            cand_spec="backend",
            need_spec="backend",
            cand_grade="senior",
            need_grade="senior",
            theta_score=100.0,
            candidate_skills=["python", "fastapi", "postgresql", "redis"],
            core_stack=["python", "fastapi", "postgresql"],
            nice_to_have=["redis"],
            fsp_data=None,
            freshness_score=100.0,
        )
        assert res_non_fsp["overall_score"] == 100.0
        assert res_non_fsp["weights"] == (0.52, 0.30, 0.00, 0.18)

        # Strong Non-FSP practitioner vs weak FSP candidate
        strong_practitioner = calculate_candidate_score(
            cand_spec="backend",
            need_spec="backend",
            cand_grade="senior",
            need_grade="senior",
            theta_score=95.0,
            candidate_skills=["python", "fastapi", "postgresql"],
            core_stack=["python", "fastapi"],
            nice_to_have=["postgresql"],
            fsp_data=None,
            freshness_score=95.0,
        )
        weak_fsp = calculate_candidate_score(
            cand_spec="backend",
            need_spec="backend",
            cand_grade="senior",
            need_grade="senior",
            theta_score=75.0,
            candidate_skills=["python"],
            core_stack=["python", "fastapi"],
            nice_to_have=["postgresql"],
            fsp_data={"fsp_id": "FSP-101", "sport_rank": "kms", "rating_points": 10},
            freshness_score=70.0,
        )
        assert strong_practitioner["overall_score"] > weak_fsp["overall_score"], (
            f"Meritocracy violated: Non-FSP ({strong_practitioner['overall_score']}) <= FSP ({weak_fsp['overall_score']})"
        )


# ==============================================================================
# SECTION 2: RESUME PARSER STRESS TESTING
# ==============================================================================

class TestResumeParserStress:
    """Stress tests PDF parsing: corrupted files, empty inputs, exotic cities, varied salary formats."""

    def test_damaged_and_invalid_magic_bytes_rejection(self):
        """Corrupted and invalid PDF streams must raise InvalidPdfFormatError."""
        invalid_payloads = [
            b"",
            b"%",
            b"%PD",
            b"%PDF",  # Exactly 4 bytes, lacks '-'
            b"PK\x03\x04\x14\x00\x00\x00",  # ZIP archive
            b"<!DOCTYPE html><html><body>Resume</body></html>",
            b"\x7fELF\x02\x01\x01\x00",  # ELF binary
            b"Random unstructured text bytes without pdf header",
        ]
        for payload in invalid_payloads:
            with pytest.raises(InvalidPdfFormatError):
                ResumeParser.validate_magic_bytes(payload)
            with pytest.raises(InvalidPdfFormatError):
                ResumeParser.parse_resume(payload)

    def test_empty_syntactically_valid_pdf_safe_parsing(self):
        """Empty PDF with valid %PDF- magic bytes must return honest defaults without crashing."""
        minimal_pdf = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
            b"xref\n0 3\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n"
            b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n116\n%%EOF"
        )
        parsed = ResumeParser.parse_resume(minimal_pdf)
        assert isinstance(parsed, dict)
        assert parsed["detected_email"] is None
        assert parsed["detected_phone"] is None
        assert parsed["detected_telegram"] is None
        assert parsed["detected_city"] is None
        assert parsed["detected_specialization"] in ("backend", "frontend", "qa", "devops", "ml_data", "infosec")
        assert parsed["detected_grade"] == "junior"
        assert parsed["work_experience"] == []
        assert parsed["education"] == []

        # Pydantic schema validation check
        response_model = ResumeParsedResponse(**parsed)
        assert response_model.raw_text_length >= 0

    def test_resume_text_without_contacts_or_experience(self):
        """Text without contacts or experience yields None and empty lists safely."""
        text_no_contacts = (
            "Изучаю программирование на Python и алгоритмы. Знаю Docker, Git, Linux. "
            "Интересуюсь разработкой распределенных сервисов."
        )
        contacts = ResumeParser.extract_contacts(text_no_contacts)
        assert contacts["email"] is None
        assert contacts["phone"] is None
        assert contacts["telegram"] is None
        assert contacts["github_url"] is None

        exp, edu, months = ResumeParser.parse_experience_and_education("Просто текст без дат и компаний.")
        assert exp == []
        assert edu == []
        assert months == 0

    def test_unconventional_salary_formats_and_bounds(self):
        """Parses «350k», «от 150 до 300 тыс. руб.», «180 - 250 тыс», «280 000 ₽» strictly obeying ratio <= 3.5."""
        test_cases = [
            ("Желаемая зарплата: 350k", (295000, 435000)),
            ("Зарплатные ожидания: 350к", (295000, 435000)),
            ("350k rub", (295000, 435000)),
            ("от 150 до 300 тыс. руб.", (150000, 300000)),
            ("Зарплата: 180 - 250 тыс", (180000, 250000)),
            ("от 200k", (200000, 270000)),
            ("до 350 тыс руб", (260000, 350000)),
            ("Ожидания по компенсации: 280 000 ₽", (235000, 350000)),
            ("Зарплата: от 100 000 до 350 000 руб", (100000, 350000)),
        ]
        for snippet, (exp_min, exp_max) in test_cases:
            s_min, s_max = ResumeParser.parse_salary_expectations(snippet)
            assert s_min is not None and s_max is not None, f"Failed to parse salary from: {snippet}"
            assert s_min == exp_min, f"Min mismatch for {snippet}: got {s_min}, expected {exp_min}"
            assert s_max == exp_max, f"Max mismatch for {snippet}: got {s_max}, expected {exp_max}"
            # Verify universal invariants
            assert s_min > 0, f"s_min must be positive: {s_min}"
            assert s_max >= s_min, f"s_max must be >= s_min: {s_max} vs {s_min}"
            assert s_max / s_min <= 3.5, f"Spread must be <= 3.5: {s_max / s_min:.2f}"

    def test_exotic_russian_cities_and_foreign_locations(self):
        """Extracts exotic Russian cities and foreign relocation hubs."""
        loc_cases = [
            ("Проживание: Норильск. Готов к удаленной работе.", "Норильск"),
            ("Локация: Сургут (ХМАО)", "Сургут"),
            ("Город: Магадан, часовой пояс UTC+11", "Магадан"),
            ("Место жительства: Якутск", "Якутск"),
            ("Город: Петропавловск-Камчатский", "Петропавловск-Камчатский"),
            ("Локация: Анадырь (Чукотка)", "Анадырь"),
            ("Проживание: Грозный, Чеченская Республика", "Грозный"),
            ("Город: Дербент", "Дербент"),
            ("Проживаю в Южно-Сахалинске", "Южно-Сахалинск"),
            # Зарубежные локации
            ("Релокация в Тбилиси, ищу удаленку", "Тбилиси"),
            ("Живу в Ереване, оформлен как ИП", "Ереван"),
            ("Проживание: Алматы, Казахстан", "Алматы"),
            ("Location: Dubai, UAE", "Дубай"),
            ("Локация: Белград, Сербия", "Белград"),
            ("Город: Минск, готов к гибриду", "Минск"),
        ]
        for snippet, expected_city in loc_cases:
            detected = ResumeParser.extract_city(snippet)
            assert detected == expected_city, f"City detection mismatch for '{snippet}': got {detected}, expected {expected_city}"


# ==============================================================================
# SECTION 3: PSYCHOMETRICS KITE IRT 3PL & DOWNGRADE PROTECTION
# ==============================================================================

class TestPsychometricsKiteIrt:
    """Verifies Birnbaum 3PL model, Fisher Information, SE <= 0.32, EAP, and downgrade protection."""

    def test_irt_3pl_probability_bounds_and_monotonicity(self):
        """Birnbaum 3PL probability bounds [c_i, 1.0] and strictly monotonic in theta*."""
        item = IRT3PLItem(item_id=1, a=1.5, b=0.5, c=0.2)
        assert item.response_probability(-100.0) == pytest.approx(0.2, abs=1e-4)
        assert item.response_probability(100.0) == pytest.approx(1.0, abs=1e-4)

        prev_p = 0.0
        for th in [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]:
            p = item.response_probability(th)
            assert 0.2 <= p <= 1.0
            assert p > prev_p
            prev_p = p

    def test_fisher_information_and_standard_error_bound_se_le_032(self):
        """
        Calculates accumulated Fisher test information across Junior, Middle, Senior, Lead batteries.
        Verifies that SEM(theta*) <= 0.32 at target qualification thresholds.
        """
        for grade_code, base_diff in GRADE_BASE_DIFFICULTY.items():
            battery = [
                IRT3PLItem(
                    item_id=spec["index"],
                    a=spec["a"],
                    b=base_diff + spec["b_rel"],
                    c=spec["c"],
                    task_type=spec["task_type"],
                )
                for spec in BATTERY_SPECS
            ]
            # Qualification threshold is centered near base_diff + 0.2
            th_target = base_diff + 0.2
            info = compute_test_information(battery, th_target)
            sem = compute_sem(battery, th_target)

            assert info >= 15.0, f"Grade {grade_code}: Fisher info {info:.2f} < 15.0"
            assert sem <= 0.32, f"Grade {grade_code}: SEM {sem:.4f} > 0.32 threshold (violated SE <= 0.32)"
            # Exact empirical SEM is ~ 0.235
            assert sem < 0.26, f"Grade {grade_code}: expected SEM < 0.26, got {sem:.4f}"

    def test_bayesian_eap_monotonicity_and_extreme_patterns(self):
        """Bayesian EAP estimation on 61 quadrature nodes is strictly monotonic and finite on extreme vectors."""
        estimator = BayesianEAPEstimator(num_nodes=61, theta_min=-4.0, theta_max=4.0)
        battery = [
            IRT3PLItem(item_id=spec["index"], a=spec["a"], b=1.0 + spec["b_rel"], c=spec["c"])
            for spec in BATTERY_SPECS
        ]

        # 1. Monotonicity: [0, 0, ...] < [1, 0, ...] < [1, 1, 0, ...] < ... < [1, 1, 1, ...]
        prev_theta = -999.0
        for num_correct in range(13):
            responses = [1] * num_correct + [0] * (12 - num_correct)
            theta_eap, sem_eap = estimator.estimate_theta_star(battery, responses)
            scaled = estimator.scale_theta_linear_8(theta_eap)

            assert 0.0 <= scaled <= 100.0
            assert theta_eap > prev_theta, f"EAP monotonicity violated at num_correct={num_correct}"
            prev_theta = theta_eap
            assert sem_eap > 0.0

        # 2. Extreme pattern: all zeros [0]*12
        th_zero, sem_zero = estimator.estimate_theta_star(battery, [0] * 12)
        assert not math.isnan(th_zero)
        assert not math.isinf(th_zero)
        assert -4.0 <= th_zero <= 0.0

        # 3. Extreme pattern: all ones [1]*12
        th_ones, sem_ones = estimator.estimate_theta_star(battery, [1] * 12)
        assert not math.isnan(th_ones)
        assert not math.isinf(th_ones)
        assert 1.0 <= th_ones <= 4.0

    def test_downgrade_protection_non_coercive_evaluation(self):
        """Guarantees complete downgrade protection across failed initial and boost sessions."""
        # 1. Failed initial session (theta < 70): No downgrade, immediate retest lower grade without cooldown
        eval_failed = GradingEngine.evaluate_session(
            candidate_id=1,
            claimed_grade="Senior",
            theta_score=62.5,
            session_type="initial",
        )
        assert eval_failed["is_grade_confirmed"] is False
        assert eval_failed["confirmed_grade"] is None  # NOT set to Middle forcibly
        assert eval_failed["retest_lower_offered"] is True
        assert eval_failed["suggested_grade"] == "Middle"
        assert eval_failed["cooldown_until"] is None  # Immediate retest allowed

        # 2. Failed boost session: Base grade preserved in full without penalty
        eval_boost_failed = GradingEngine.evaluate_session(
            candidate_id=1,
            claimed_grade="Lead",  # Boost attempt from Senior to Lead
            theta_score=65.0,      # Failed boost threshold (< 70)
            session_type="boost",
        )
        assert eval_boost_failed["is_grade_confirmed"] is True
        assert eval_boost_failed["confirmed_grade"] == "Senior"  # Retains Senior
        assert eval_boost_failed["boost_passed"] is False
        assert "Базовый грейд Senior сохранен в полном объеме" in eval_boost_failed["message"]

        # 3. Successful boost session: Higher grade confirmed
        eval_boost_success = GradingEngine.evaluate_session(
            candidate_id=1,
            claimed_grade="Lead",
            theta_score=82.0,
            session_type="boost",
        )
        assert eval_boost_success["is_grade_confirmed"] is True
        assert eval_boost_success["confirmed_grade"] == "Lead"
        assert eval_boost_success["boost_passed"] is True

        # 4. Standard confirmation (70 <= theta < 88)
        eval_confirmed = GradingEngine.evaluate_session(
            candidate_id=1,
            claimed_grade="Middle",
            theta_score=76.4,
            session_type="initial",
        )
        assert eval_confirmed["is_grade_confirmed"] is True
        assert eval_confirmed["confirmed_grade"] == "Middle"
        assert eval_confirmed["boost_offered"] is False

        # 5. Distinction (theta >= 88): Risk-free boost offered
        eval_distinction = GradingEngine.evaluate_session(
            candidate_id=1,
            claimed_grade="Middle",
            theta_score=91.0,
            session_type="initial",
        )
        assert eval_distinction["is_grade_confirmed"] is True
        assert eval_distinction["confirmed_grade"] == "Middle"
        assert eval_distinction["boost_offered"] is True
        assert eval_distinction["suggested_grade"] == "Senior"
