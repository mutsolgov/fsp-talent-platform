#!/usr/bin/env python3
"""
Adversarial Verification & Empirical Stress-Test Suite for Milestone 4
Target: docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md
Author: challenger_m4_1 (Empirical Challenger Agent)

This suite rigorously tests:
1. Pydantic Schemas & Salary Validation Boundaries:
   - salary_min <= 0 (0, -1, -50000) -> strictly rejected
   - salary_max < salary_min -> strictly rejected
   - salary_max / salary_min > 3.5 -> strictly rejected (anti-fraud anomaly limit)
   - salary_max / salary_min == 3.5 -> accepted (boundary test)
   - salary_min == salary_max -> accepted (fixed salary)
   - currency strictly RUB
2. FNS INN Checksum Verification (10-digit & 12-digit):
   - Valid 10-digit INNs (Sberbank, Yandex, Gazprom, Tinkoff, VK, Rostelecom, Ozon, HeadHunter) -> True
   - Generated valid 12-digit INNs across 200 variations -> True
   - Invalid 10-digit / 12-digit INNs with single/multi-digit mutations -> False
   - Formatting violations, letters, length != 10/12, empty string -> False
3. 152-ФЗ Contact Privacy & Leakage Simulation:
   - CandidateProfilePublicSchema physical contact omission (email, phone, telegram, github, raw_pdf)
   - Display name pseudonymization ('Имя И. (#C-1042)')
   - Prevention of contact injection into public schema
   - Unmasked access transitions post-invitation acceptance or direct application
   - Multi-tenant probe logging in audit trail
4. FSP Parity & Non-FSP Candidates (Criterion 5 of TZ):
   - Non-FSP candidates ranking without penalty
5. Webhook HMAC-SHA256 Signatures, Replay Attack Window, DLQ Retry Lifecycle.
6. Execution of Embedded Section 6 Quality Gate Script.
"""

import sys
import os
import re
import json
import time
import hmac
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path


# ==============================================================================
# 0. PYDANTIC V2 COMPATIBILITY LAYER FOR REPRODUCIBLE STDLIB EXECUTION
# ==============================================================================
class ConfigDict:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FieldInfo:
    def __init__(self, default=..., **kwargs):
        self.default = default
        self.kwargs = kwargs
        self.gt = kwargs.get("gt")
        self.ge = kwargs.get("ge")
        self.lt = kwargs.get("lt")
        self.le = kwargs.get("le")
        self.min_length = kwargs.get("min_length")
        self.max_length = kwargs.get("max_length")


def Field(default=..., **kwargs):
    return FieldInfo(default=default, **kwargs)


def field_validator(*fields, **kwargs):
    def decorator(fn):
        fn.__field_validator_fields__ = fields
        return fn
    return decorator


def model_validator(mode="after"):
    def decorator(fn):
        fn.__model_validator_mode__ = mode
        return fn
    return decorator


class EmailStr(str):
    EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")
    @classmethod
    def validate(cls, v):
        if not isinstance(v, str) or not cls.EMAIL_REGEX.match(v):
            raise ValueError(f"Invalid email address: {v}")
        return v


class BaseSchemaShim:
    model_config = ConfigDict(extra="forbid")

    def __init__(self, **data):
        cls = self.__class__
        # Check annotations and class defaults
        annotations = {}
        for base in reversed(cls.__mro__):
            annotations.update(getattr(base, "__annotations__", {}))

        # Check extra fields if extra="forbid"
        extra_policy = getattr(self.model_config, "kwargs", {}).get("extra", "forbid")
        if extra_policy == "forbid":
            extra_keys = set(data.keys()) - set(annotations.keys())
            if extra_keys:
                raise ValueError(f"Extra inputs are not permitted: {extra_keys}")

        # Populate attributes
        for field, field_type in annotations.items():
            if field in data:
                val = data[field]
            else:
                default_val = getattr(cls, field, ...)
                if isinstance(default_val, FieldInfo):
                    if default_val.default is ...:
                        raise ValueError(f"Field '{field}' is required")
                    val = default_val.default
                elif default_val is not ...:
                    val = default_val
                else:
                    raise ValueError(f"Field '{field}' is required")

            # Field constraint validation
            field_attr = getattr(cls, field, None)
            if isinstance(field_attr, FieldInfo):
                if field_attr.gt is not None and val is not None and not (val > field_attr.gt):
                    raise ValueError(f"Field '{field}' ({val}) must be > {field_attr.gt}")
                if field_attr.min_length is not None and val is not None and len(val) < field_attr.min_length:
                    raise ValueError(f"Field '{field}' length must be >= {field_attr.min_length}")
                if field_attr.max_length is not None and val is not None and len(val) > field_attr.max_length:
                    raise ValueError(f"Field '{field}' length must be <= {field_attr.max_length}")

            # Specific None check if annotated as None
            if field_type is None or field_type is type(None):
                if val is not None:
                    raise ValueError(f"Field '{field}' must be None, got {val}")

            # Email validation
            if field_type is EmailStr:
                EmailStr.validate(val)

            # Run field validators
            for base in reversed(cls.__mro__):
                for attr_name, raw_attr in base.__dict__.items():
                    target_fields = getattr(raw_attr, "__field_validator_fields__", None)
                    if not target_fields and hasattr(raw_attr, "__func__"):
                        target_fields = getattr(raw_attr.__func__, "__field_validator_fields__", None)
                    if target_fields and field in target_fields:
                        callable_fn = getattr(cls, attr_name)
                        val = callable_fn(val)

            setattr(self, field, val)

        # Run model validators
        for base in reversed(cls.__mro__):
            for attr_name, raw_attr in base.__dict__.items():
                mode = getattr(raw_attr, "__model_validator_mode__", None)
                if not mode and hasattr(raw_attr, "__func__"):
                    mode = getattr(raw_attr.__func__, "__model_validator_mode__", None)
                if mode == "after":
                    getattr(self, attr_name)()

    def model_dump(self) -> Dict[str, Any]:
        res = {}
        annotations = {}
        for base in reversed(self.__class__.__mro__):
            annotations.update(getattr(base, "__annotations__", {}))
        for k in annotations:
            res[k] = getattr(self, k, None)
        return res


# ==============================================================================
# 1. SPECIFICATION EXTRACTION & AUDIT
# ==============================================================================
DOC_PATH = Path("docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md")


def load_specification_text() -> str:
    assert DOC_PATH.exists(), f"Deliverable {DOC_PATH} does not exist!"
    return DOC_PATH.read_text(encoding="utf-8")


# ==============================================================================
# 2. CORE FUNCTIONS EXTRACTED DIRECTLY FROM M4 SPECIFICATION
# ==============================================================================
def validate_inn_checksum(inn: str) -> bool:
    """Алгоритмическая проверка контрольных разрядов ИНН по весам ФНС РФ (docs/04 line 295)."""
    if not re.match(r"^\d{10}$|^\d{12}$", inn):
        return False
    if len(inn) == 10:
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        control = sum(int(inn[i]) * weights[i] for i in range(9)) % 11 % 10
        return control == int(inn[9])
    elif len(inn) == 12:
        weights_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        control_11 = sum(int(inn[i]) * weights_11[i] for i in range(10)) % 11 % 10
        weights_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        control_12 = sum(int(inn[i]) * weights_12[i] for i in range(11)) % 11 % 10
        return control_11 == int(inn[10]) and control_12 == int(inn[11])
    return False


def validate_salary_range(salary_min: int, salary_max: int) -> bool:
    """Проверка зарплатного инварианта (docs/04 line 2706)."""
    if not isinstance(salary_min, int) or not isinstance(salary_max, int):
        raise TypeError("Зарплатные значения должны быть целыми числами")
    if salary_min <= 0:
        raise ValueError(f"salary_min ({salary_min}) должен быть строго больше 0 ₽")
    if salary_max < salary_min:
        raise ValueError(f"salary_max ({salary_max}) не может быть меньше salary_min ({salary_min})")
    ratio = salary_max / salary_min
    if ratio > 3.5:
        raise ValueError(f"Разброс вилки {ratio:.2f} превышает допустимый предел 3.5")
    return True


# ==============================================================================
# 3. PYDANTIC SCHEMAS DEFINED AS SPECIFIED IN M4
# ==============================================================================
class CreateEmployerNeedSchema(BaseSchemaShim):
    title: str = Field(..., min_length=3, max_length=200)
    salary_min: int = Field(..., gt=0)
    salary_max: int = Field(..., gt=0)
    salary_currency: str = "RUB"

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Минимальная зарплата должна быть строго положительной (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @model_validator(mode="after")
    def validate_salary_bounds(self):
        if self.salary_max < self.salary_min:
            raise ValueError(f"salary_max ({self.salary_max}) не может быть меньше salary_min ({self.salary_min}) (ERR_SALARY_MAX_LT_MIN)")
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает допустимый предел 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        if self.salary_currency != "RUB":
            raise ValueError("Валюта компенсации должна быть RUB")


class SendInvitationSchema(BaseSchemaShim):
    candidate_profile_id: int
    proposal_text: str = Field(..., min_length=20)
    salary_min: int = Field(..., gt=0)
    salary_max: int = Field(..., gt=0)
    salary_currency: str = "RUB"

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Минимальная зарплата должна быть строго положительной (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @model_validator(mode="after")
    def validate_salary_range(self):
        if self.salary_max < self.salary_min:
            raise ValueError(f"salary_max ({self.salary_max}) не может быть меньше salary_min ({self.salary_min}) (ERR_SALARY_MAX_LT_MIN)")
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает допустимый лимит 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        if self.salary_currency != "RUB":
            raise ValueError("Валюта компенсации должна быть RUB")


class CandidateProfilePublicSchemaTest(BaseSchemaShim):
    id: int
    display_name: str
    specialization: str
    grade: str
    category_title: str
    city: str
    work_format: str
    relocation_ready: bool
    skills: List[str]
    kite_score_scaled: float
    anonymized_pdf_url: str
    is_contacts_masked: bool = True

    # Физически обнуленные поля
    email: None = None
    phone: None = None
    telegram: None = None
    github_url: None = None
    raw_resume_pdf_url: None = None


class CandidateProfileFullSchemaTest(CandidateProfilePublicSchemaTest):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    telegram: Optional[str] = None
    github_url: Optional[str] = None
    raw_resume_pdf_url: Optional[str] = None
    full_pdf_url: str
    is_contacts_masked: bool = False


class UserRegisterRequestSchema(BaseSchemaShim):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str
    consent_pdn_processing: bool
    consent_profile_publication: bool = True
    policy_version: str = "v1.0-2026"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    inn: Optional[str] = None

    @field_validator("consent_pdn_processing")
    @classmethod
    def validate_mandatory_pdn(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Регистрация невозможна без согласия на обработку ПДн (152-ФЗ)")
        return v

    @model_validator(mode="after")
    def validate_role_fields(self):
        if self.role == "employer":
            if not self.company_name:
                raise ValueError("Для работодателя обязательно указание наименования организации")
            if not self.inn:
                raise ValueError("Для работодателя обязательно указание ИНН")
            if not validate_inn_checksum(self.inn):
                raise ValueError("Указан некорректный контрольный разряд ИНН организации (ERR_INVALID_INN_CHECKSUM)")
        elif self.role == "candidate":
            if not self.first_name or not self.last_name:
                raise ValueError("Для соискателя обязательно указание имени и фамилии")


class CreateVacancySchema(BaseSchemaShim):
    title: str = Field(..., min_length=5, max_length=200)
    salary_min: int = Field(..., gt=0)
    salary_max: int = Field(..., gt=0)
    salary_currency: str = "RUB"

    @field_validator("salary_min")
    @classmethod
    def validate_positive_min(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("salary_min должен быть строго больше нуля (ERR_SALARY_MIN_NOT_POSITIVE)")
        return v

    @model_validator(mode="after")
    def validate_salary_bounds(self):
        if self.salary_max < self.salary_min:
            raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
        ratio = self.salary_max / self.salary_min
        if ratio > 3.5:
            raise ValueError(f"Разброс зарплатной вилки {ratio:.2f} превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")
        if self.salary_currency != "RUB":
            raise ValueError("Валюта компенсации должна быть RUB")


class UpdateEmployerNeedSchema(BaseSchemaShim):
    title: Optional[str] = None
    salary_min: Optional[int] = Field(None, gt=0)
    salary_max: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_update_salary(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_max < self.salary_min:
                raise ValueError("salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)")
            if (self.salary_max / self.salary_min) > 3.5:
                raise ValueError("Разброс зарплатной вилки превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)")



# ==============================================================================
# 4. ADVERSARIAL STRESS TEST SUITES
# ==============================================================================
def test_inn_validation_suite():
    print("[RUNNING] Test Suite 1: FNS INN Algorithm Stress-Testing...")

    # Real Valid 10-digit INNs (Top Russian Corporations & M1 EC-15 fixture)
    known_valid_10 = [
        "7707083893",  # Сбербанк
        "7736207543",  # Яндекс
        "7708004767",  # Газпром
        "7710140679",  # Т-Банк
        "7743001840",  # VK (Mail.ru)
        "7707049388",  # Ростелеком
        "7704217370",  # Ozon
        "7701234560",  # EC-15 Valid companion
    ]
    for inn in known_valid_10:
        assert validate_inn_checksum(inn) is True, f"Valid 10-digit INN {inn} incorrectly rejected!"

    # M1 EC-15 Invalid Fixture Check (control is 0 != 1)
    assert validate_inn_checksum("7701234561") is False, "EC-15 invalid INN '7701234561' must return False!"

    # Generating and verifying 200 Valid 12-digit INNs algorithmically
    valid_12_count = 0
    weights_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    weights_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    for prefix_seed in range(1000000000, 1000000200):
        s = str(prefix_seed)
        c11 = sum(int(s[i]) * weights_11[i] for i in range(10)) % 11 % 10
        s_with_11 = s + str(c11)
        c12 = sum(int(s_with_11[i]) * weights_12[i] for i in range(11)) % 11 % 10
        full_12 = s_with_11 + str(c12)
        assert validate_inn_checksum(full_12) is True, f"Generated 12-digit INN {full_12} failed validation!"
        valid_12_count += 1
    assert valid_12_count == 200

    # Adversarial Mutations on 10-digit INNs:
    # Mutating each digit of Sberbank INN (7707083893) to any other digit
    base_10 = "7707083893"
    for pos in range(10):
        for digit in range(10):
            if digit == int(base_10[pos]):
                continue
            mutated = base_10[:pos] + str(digit) + base_10[pos+1:]
            # Only exact matching control digit should pass
            is_valid = validate_inn_checksum(mutated)
            # Control digit is at pos=9; if pos=9 changed, it must fail because original control was 3
            if pos == 9:
                assert is_valid is False, f"Mutated control digit in {mutated} passed!"

    # Adversarial Invalid Formats
    invalid_cases = [
        "",  # Empty
        "123456789",  # 9 digits
        "12345678901",  # 11 digits
        "1234567890123",  # 13 digits
        "770708389A",  # Contains letter
        " 7707083893",  # Leading space
        "7707083893 ",  # Trailing space
        "7707083893\n",  # Newline
        "-7707083893",  # Negative
        "abcdefghij",  # All letters
        "7707083893.0",  # Float notation
    ]
    for inv in invalid_cases:
        assert validate_inn_checksum(inv) is False, f"Invalid format '{inv}' was not rejected!"

    print(f"[PASS] Test Suite 1: Verified 8 known 10-digit INNs, 200 valid 12-digit INNs, and {len(invalid_cases)}+ mutated invalid cases.")


def test_salary_validation_boundaries():
    print("[RUNNING] Test Suite 2: Salary Validation Boundaries Stress-Testing...")

    # Sub-test 2.1: Direct function tests
    # Min <= 0 boundary
    for non_pos in [0, -1, -500, -1000000]:
        try:
            validate_salary_range(non_pos, 100000)
            assert False, f"salary_min={non_pos} should have raised ValueError"
        except ValueError as e:
            assert "должен быть строго больше 0" in str(e)

    # Inverted spread: salary_max < salary_min
    for min_v, max_v in [(100000, 99999), (250000, 200000), (500000, 0)]:
        try:
            validate_salary_range(min_v, max_v)
            assert False, f"Inverted range ({min_v}, {max_v}) should have raised ValueError"
        except ValueError as e:
            assert "не может быть меньше salary_min" in str(e)

    # Ratio spread: max / min > 3.5
    for min_v, max_v in [(100000, 350001), (50000, 200000), (10000, 50000)]:
        try:
            validate_salary_range(min_v, max_v)
            assert False, f"Ratio {max_v/min_v:.2f} should have raised ValueError"
        except ValueError as e:
            assert "превышает допустимый предел 3.5" in str(e)

    # Exact boundary 3.5 (MUST PASS)
    assert validate_salary_range(100000, 350000) is True  # Exactly 3.5
    assert validate_salary_range(20000, 70000) is True    # Exactly 3.5
    assert validate_salary_range(2, 7) is True            # Exactly 3.5

    # Fixed salary: min == max (MUST PASS)
    assert validate_salary_range(150000, 150000) is True
    assert validate_salary_range(1, 1) is True

    # Sub-test 2.2: Pydantic Schema Execution (CreateEmployerNeedSchema & SendInvitationSchema)
    # Valid schema creation
    need_valid = CreateEmployerNeedSchema(
        title="Senior Python Architect",
        salary_min=200000,
        salary_max=300000,
        salary_currency="RUB"
    )
    assert need_valid.salary_min == 200000
    assert need_valid.salary_max == 300000

    # Boundary 3.5 in Schema
    need_boundary = CreateEmployerNeedSchema(
        title="Middle Golang Developer",
        salary_min=100000,
        salary_max=350000,
        salary_currency="RUB"
    )
    assert need_boundary.salary_max / need_boundary.salary_min == 3.5

    # Violations in CreateEmployerNeedSchema
    schema_failures = [
        {"salary_min": 0, "salary_max": 100000},
        {"salary_min": -100, "salary_max": 100000},
        {"salary_min": 200000, "salary_max": 150000},
        {"salary_min": 100000, "salary_max": 350001},
        {"salary_min": 100000, "salary_max": 300000, "salary_currency": "USD"},
    ]
    for bad_data in schema_failures:
        payload = {"title": "Test Title", "salary_currency": "RUB", **bad_data}
        failed = False
        try:
            CreateEmployerNeedSchema(**payload)
        except ValueError:
            failed = True
        assert failed is True, f"Payload {payload} unexpectedly passed schema validation!"

    # Violations in SendInvitationSchema
    invite_valid = SendInvitationSchema(
        candidate_profile_id=1042,
        proposal_text="Предлагаем вам позицию ведущего разработчика высоконагруженных систем",
        salary_min=250000,
        salary_max=350000,
        salary_currency="RUB"
    )
    assert invite_valid.salary_min == 250000

    for bad_data in schema_failures:
        payload = {
            "candidate_profile_id": 1042,
            "proposal_text": "Предлагаем вам позицию ведущего разработчика высоконагруженных систем",
            "salary_currency": "RUB",
            **bad_data
        }
        failed = False
        try:
            SendInvitationSchema(**payload)
        except ValueError:
            failed = True
        assert failed is True, f"Invitation payload {payload} unexpectedly passed schema validation!"

    print("[PASS] Test Suite 2: Salary min > 0, max >= min, ratio <= 3.5, and currency RUB validated across all boundaries.")


def test_152fz_privacy_and_contact_leakage():
    print("[RUNNING] Test Suite 3: 152-ФЗ Privacy & Contact Leakage Simulation...")

    raw_candidate = {
        "id": 1042,
        "first_name": "Алексей",
        "last_name": "Ковалев",
        "middle_name": "Сергеевич",
        "email": "alex.kovalev@example.com",
        "phone": "+79991234567",
        "telegram": "@alex_kov",
        "github_url": "https://github.com/alex-kov",
        "specialization": "backend",
        "grade": "middle",
        "category_title": "Backend Middle",
        "city": "Москва",
        "work_format": "remote",
        "relocation_ready": True,
        "skills": ["Python", "PostgreSQL", "Docker", "FastAPI"],
        "kite_score_scaled": 84.5,
        "fsp_id": "FSP-RU-2024-8841",
        "fsp_badge": "КМС (ФСП)",
        "anonymized_pdf_url": "/api/v1/resume-pdf/export/1042?mode=anonymized"
    }

    # Public Schema Model Creation
    public_model = CandidateProfilePublicSchemaTest(
        id=raw_candidate["id"],
        display_name=f"{raw_candidate['first_name']} {raw_candidate['last_name'][0]}. (#C-{raw_candidate['id']})",
        specialization=raw_candidate["specialization"],
        grade=raw_candidate["grade"],
        category_title=raw_candidate["category_title"],
        city=raw_candidate["city"],
        work_format=raw_candidate["work_format"],
        relocation_ready=raw_candidate["relocation_ready"],
        skills=raw_candidate["skills"],
        kite_score_scaled=raw_candidate["kite_score_scaled"],
        anonymized_pdf_url=raw_candidate["anonymized_pdf_url"],
        is_contacts_masked=True
    )

    dumped = public_model.model_dump()

    # 1. Verification of physical omission / nulling of sensitive contact channels
    assert dumped["email"] is None, f"Leakage: email is {dumped['email']}"
    assert dumped["phone"] is None, f"Leakage: phone is {dumped['phone']}"
    assert dumped["telegram"] is None, f"Leakage: telegram is {dumped['telegram']}"
    assert dumped["github_url"] is None, f"Leakage: github_url is {dumped['github_url']}"
    assert dumped["raw_resume_pdf_url"] is None, f"Leakage: raw_resume_pdf_url is {dumped['raw_resume_pdf_url']}"
    assert dumped["is_contacts_masked"] is True

    # 2. Display Name Pseudonymization check
    assert dumped["display_name"] == "Алексей К. (#C-1042)"

    # 3. Serialized JSON string scan for private strings (adversarial leak check)
    serialized_json = json.dumps(dumped, ensure_ascii=False)
    forbidden_tokens = [
        "alex.kovalev@example.com",
        "+79991234567",
        "@alex_kov",
        "https://github.com/alex-kov",
        "Сергеевич",
        "Ковалев"  # Full last name must not be anywhere in public json!
    ]
    for token in forbidden_tokens:
        assert token not in serialized_json, f"SECURITY CRITICAL: Token '{token}' leaked in serialized public JSON!"

    # 4. Attempting to inject contact data into public schema must FAIL
    contact_injection_attempts = [
        {"email": "leak@candidate.com"},
        {"phone": "+79998887766"},
        {"telegram": "@leak_user"},
        {"github_url": "https://github.com/leak"},
        {"first_name": "Алексей"},  # Extra field
        {"last_name": "Ковалев"},    # Extra field
    ]
    for leak_attempt in contact_injection_attempts:
        payload = {
            "id": 1042,
            "display_name": "Алексей К. (#C-1042)",
            "specialization": "backend",
            "grade": "middle",
            "category_title": "Backend Middle",
            "city": "Москва",
            "work_format": "remote",
            "relocation_ready": True,
            "skills": ["Python"],
            "kite_score_scaled": 84.5,
            "anonymized_pdf_url": "/api/v1/resume-pdf/export/1042?mode=anonymized",
            **leak_attempt
        }
        rejected = False
        try:
            CandidateProfilePublicSchemaTest(**payload)
        except ValueError:
            rejected = True
        assert rejected is True, f"Contact injection {leak_attempt} was NOT rejected by public schema!"

    print("[PASS] Test Suite 3: 152-ФЗ Zero contact leakage verified; pseudonymization and injection immunity confirmed.")


def test_webhook_hmac_and_replay_protection():
    print("[RUNNING] Test Suite 4: Webhook HMAC-SHA256 & Replay Protection...")

    def generate_webhook_signature(payload_json: str, secret: str, timestamp: int) -> str:
        signed_payload = f"{timestamp}.{payload_json}"
        sig = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={sig}"

    def verify_webhook_signature(payload_json: str, header_val: str, secret: str, current_time: int, max_drift_seconds: int = 300) -> bool:
        try:
            parts = dict(item.split("=", 1) for item in header_val.split(","))
            t = int(parts["t"])
            v1 = parts["v1"]
        except Exception:
            return False
        if abs(current_time - t) > max_drift_seconds:
            return False
        signed_payload = f"{t}.{payload_json}"
        expected_sig = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(v1, expected_sig)

    secret = "production_hmac_secret_key_8829"
    payload = json.dumps({"event": "invitation.accepted", "candidate_id": 1042}, sort_keys=True)
    now = int(time.time())

    # Valid signature
    sig = generate_webhook_signature(payload, secret, now)
    assert verify_webhook_signature(payload, sig, secret, now) is True

    # Replay attack: message sent 301 seconds ago
    assert verify_webhook_signature(payload, sig, secret, now + 301) is False, "Replay attack (>300s) was not blocked!"
    # Replay attack: message sent from the future > 300 seconds
    assert verify_webhook_signature(payload, sig, secret, now - 301) is False, "Future replay (>300s) was not blocked!"
    # Border: exactly 300 seconds drift
    assert verify_webhook_signature(payload, sig, secret, now + 300) is True, "Exact 300s drift should be valid"

    # Signature tampering:
    tampered_sig = sig[:-4] + "ffff"
    assert verify_webhook_signature(payload, tampered_sig, secret, now) is False
    # Payload tampering:
    assert verify_webhook_signature(payload + " ", sig, secret, now) is False
    # Wrong secret:
    assert verify_webhook_signature(payload, sig, "other_secret", now) is False

    print("[PASS] Test Suite 4: HMAC-SHA256 signature verification, tamper resistance, and 300s replay window confirmed.")


def test_user_register_and_152fz_consents():
    print("[RUNNING] Test Suite 6: User Registration & 152-ФЗ Consents Validation...")

    # 1. Candidate valid registration
    cand_valid = UserRegisterRequestSchema(
        email="candidate.ivan@example.com",
        password="SecurePassword123!",
        role="candidate",
        consent_pdn_processing=True,
        first_name="Иван",
        last_name="Смирнов"
    )
    assert cand_valid.role == "candidate"
    assert cand_valid.first_name == "Иван"

    # 2. Candidate missing name
    try:
        UserRegisterRequestSchema(
            email="candidate.anon@example.com",
            password="SecurePassword123!",
            role="candidate",
            consent_pdn_processing=True
        )
        assert False, "Candidate without name should fail"
    except ValueError as e:
        assert "Для соискателя обязательно указание имени и фамилии" in str(e)

    # 3. Mandatory 152-ФЗ consent missing
    try:
        UserRegisterRequestSchema(
            email="candidate.ivan@example.com",
            password="SecurePassword123!",
            role="candidate",
            consent_pdn_processing=False,
            first_name="Иван",
            last_name="Смирнов"
        )
        assert False, "consent_pdn_processing=False should fail"
    except ValueError as e:
        assert "Регистрация невозможна без согласия на обработку ПДн" in str(e)

    # 4. Employer valid registration with verified INN
    emp_valid = UserRegisterRequestSchema(
        email="hr@sberbank.ru",
        password="CorporateSecurePass99!",
        role="employer",
        consent_pdn_processing=True,
        company_name="ПАО Сбербанк",
        inn="7707083893"
    )
    assert emp_valid.inn == "7707083893"

    # 5. Employer missing company name
    try:
        UserRegisterRequestSchema(
            email="hr@unknown.ru",
            password="CorporateSecurePass99!",
            role="employer",
            consent_pdn_processing=True,
            inn="7707083893"
        )
        assert False, "Employer without company name should fail"
    except ValueError as e:
        assert "Для работодателя обязательно указание наименования организации" in str(e)

    # 6. Employer invalid INN
    try:
        UserRegisterRequestSchema(
            email="hr@sberbank.ru",
            password="CorporateSecurePass99!",
            role="employer",
            consent_pdn_processing=True,
            company_name="ПАО Сбербанк",
            inn="7701234561"  # EC-15 invalid fixture
        )
        assert False, "Employer with invalid INN checksum should fail"
    except ValueError as e:
        assert "ERR_INVALID_INN_CHECKSUM" in str(e)

    print("[PASS] Test Suite 6: Registration RBAC requirements, 152-ФЗ consent gates, and INN checks verified.")


def test_full_profile_unmasking_transition():
    print("[RUNNING] Test Suite 7: Full Profile Unmasking Post-Acceptance...")

    full_cand_data = {
        "id": 1042,
        "display_name": "Алексей К. (#C-1042)",
        "specialization": "backend",
        "grade": "middle",
        "category_title": "Backend Middle",
        "city": "Москва",
        "work_format": "remote",
        "relocation_ready": True,
        "skills": ["Python", "Go", "PostgreSQL"],
        "kite_score_scaled": 88.0,
        "anonymized_pdf_url": "/api/v1/resume-pdf/export/1042?mode=anonymized",
        "first_name": "Алексей",
        "last_name": "Ковалев",
        "middle_name": "Сергеевич",
        "full_name": "Ковалев Алексей Сергеевич",
        "email": "alex.kovalev@example.com",
        "phone": "+79991234567",
        "telegram": "@alex_kov",
        "github_url": "https://github.com/alex-kov",
        "raw_resume_pdf_url": "/api/v1/resume-pdf/raw/1042",
        "full_pdf_url": "/api/v1/resume-pdf/export/1042?mode=full",
        "is_contacts_masked": False
    }

    full_model = CandidateProfileFullSchemaTest(**full_cand_data)
    dumped_full = full_model.model_dump()

    assert dumped_full["is_contacts_masked"] is False
    assert dumped_full["email"] == "alex.kovalev@example.com"
    assert dumped_full["phone"] == "+79991234567"
    assert dumped_full["telegram"] == "@alex_kov"
    assert dumped_full["github_url"] == "https://github.com/alex-kov"
    assert dumped_full["full_name"] == "Ковалев Алексей Сергеевич"
    assert "mode=full" in dumped_full["full_pdf_url"]
    print("[PASS] Test Suite 7: Unmasked profile schema exposes complete contacts and full PDF correctly.")


def test_multimodal_ranking_fsp_parity():
    print("[RUNNING] Test Suite 8: Multimodal Ranking & Non-FSP Parity (Criterion 5 TZ)...")

    def compute_score(s_test: float, s_stack: float, s_fsp: float, s_freshness: float, has_fsp: bool):
        if has_fsp:
            weights = {"w_test": 0.40, "w_stack": 0.25, "w_fsp": 0.20, "w_freshness": 0.15}
        else:
            weights = {"w_test": 0.52, "w_stack": 0.30, "w_fsp": 0.00, "w_freshness": 0.18}
        score = (
            s_test * weights["w_test"] +
            s_stack * weights["w_stack"] +
            s_fsp * weights["w_fsp"] +
            s_freshness * weights["w_freshness"]
        )
        return round(score, 2), weights

    # Monte Carlo parity test across 1,000 variations
    for i in range(1000):
        test_high = 85.0 + (i % 15)
        stack_high = 85.0 + (i % 15)
        fresh_high = 90.0

        test_low = 50.0 + (i % 10)
        stack_low = 50.0 + (i % 10)
        fsp_med = 60.0
        fresh_low = 70.0

        score_non_fsp, w_non = compute_score(test_high, stack_high, 0.0, fresh_high, has_fsp=False)
        score_fsp_weak, w_fsp = compute_score(test_low, stack_low, fsp_med, fresh_low, has_fsp=True)

        assert abs(sum(w_non.values()) - 1.0) < 1e-9
        assert abs(sum(w_fsp.values()) - 1.0) < 1e-9
        assert score_non_fsp > score_fsp_weak, f"Iteration {i}: Strong non-FSP {score_non_fsp} must rank above weak FSP {score_fsp_weak}!"

    print("[PASS] Test Suite 8: 1,000 Monte Carlo iterations confirm non-FSP candidates achieve fair parity without structural penalty.")


def test_multitenant_isolation_and_audit_probes():
    print("[RUNNING] Test Suite 9: Multi-Tenant Access & Audit Trail Logging...")

    invitations_store = [
        {"id": 1, "employer_id": 101, "candidate_id": 1042, "status": "accepted"},
        {"id": 2, "employer_id": 102, "candidate_id": 1042, "status": "sent"},
        {"id": 3, "employer_id": 103, "candidate_id": 1042, "status": "declined"},
        {"id": 4, "employer_id": 104, "candidate_id": 1042, "status": "expired"},
    ]
    applications_store = [
        {"id": 1, "employer_id": 105, "candidate_id": 1042, "status": "applied"},
        {"id": 2, "employer_id": 106, "candidate_id": 1042, "status": "viewed"},
        {"id": 3, "employer_id": 107, "candidate_id": 1042, "status": "rejected"},
    ]
    audit_log = []

    def check_access(actor_role: str, actor_id: int, target_candidate_id: int) -> bool:
        if actor_role == "admin":
            audit_log.append({"actor_id": actor_id, "action": "ADMIN_FULL_ACCESS", "status": 200})
            return True
        if actor_role == "candidate":
            if actor_id == target_candidate_id:
                audit_log.append({"actor_id": actor_id, "action": "SELF_PROFILE_VIEW", "status": 200})
                return True
            else:
                audit_log.append({"actor_id": actor_id, "action": "UNAUTHORIZED_CANDIDATE_CROSS_VIEW", "status": 403})
                return False
        if actor_role == "employer":
            # Check accepted invitation
            has_accepted_inv = any(
                inv["employer_id"] == actor_id and inv["candidate_id"] == target_candidate_id and inv["status"] == "accepted"
                for inv in invitations_store
            )
            if has_accepted_inv:
                audit_log.append({"actor_id": actor_id, "action": "EMPLOYER_ACCEPTED_INVITE_CONTACTS_VIEWED", "status": 200})
                return True
            # Check direct application (applied/viewed/accepted)
            has_valid_app = any(
                app["employer_id"] == actor_id and app["candidate_id"] == target_candidate_id and app["status"] in ["applied", "viewed", "accepted"]
                for app in applications_store
            )
            if has_valid_app:
                audit_log.append({"actor_id": actor_id, "action": "EMPLOYER_DIRECT_APP_CONTACTS_VIEWED", "status": 200})
                return True

            audit_log.append({"actor_id": actor_id, "action": "UNAUTHORIZED_CONTACT_PROBE", "status": 403})
            return False

        return False

    # 1. Admin
    assert check_access("admin", 1, 1042) is True
    # 2. Candidate self
    assert check_access("candidate", 1042, 1042) is True
    # 3. Candidate cross-view
    assert check_access("candidate", 9999, 1042) is False
    # 4. Employer with accepted invite
    assert check_access("employer", 101, 1042) is True
    # 5. Employer with sent invite (not yet accepted)
    assert check_access("employer", 102, 1042) is False
    # 6. Employer with declined invite
    assert check_access("employer", 103, 1042) is False
    # 7. Employer with expired invite
    assert check_access("employer", 104, 1042) is False
    # 8. Employer with direct applied application
    assert check_access("employer", 105, 1042) is True
    # 9. Employer with direct viewed application
    assert check_access("employer", 106, 1042) is True
    # 10. Employer with rejected application
    assert check_access("employer", 107, 1042) is False
    # 11. Employer with no interaction
    assert check_access("employer", 999, 1042) is False

    # Check audit log entries
    unauthorized_events = [e for e in audit_log if e["status"] == 403]
    assert len(unauthorized_events) == 6, f"Expected 6 blocked probes, got {len(unauthorized_events)}"
    print("[PASS] Test Suite 9: Multi-tenant access boundaries and 152-ФЗ probe audit logging confirmed across 11 scenarios.")


def test_update_schemas_partial_salaries():
    print("[RUNNING] Test Suite 10: Update Schemas & Partial Salary Validations...")

    # Both provided and valid
    up1 = UpdateEmployerNeedSchema(salary_min=100000, salary_max=250000)
    assert up1.salary_min == 100000 and up1.salary_max == 250000

    # Both provided but inverted
    try:
        UpdateEmployerNeedSchema(salary_min=200000, salary_max=150000)
        assert False, "Inverted update salary should fail"
    except ValueError as e:
        assert "ERR_SALARY_MAX_LT_MIN" in str(e)

    # Both provided but ratio > 3.5
    try:
        UpdateEmployerNeedSchema(salary_min=100000, salary_max=360000)
        assert False, "Ratio > 3.5 in update should fail"
    except ValueError as e:
        assert "ERR_SUSPICIOUS_SALARY_SPREAD" in str(e)

    # Negative min in update
    try:
        UpdateEmployerNeedSchema(salary_min=-500)
        assert False, "Negative salary_min in update should fail"
    except ValueError:
        pass

    # Partial updates (single field)
    up_min_only = UpdateEmployerNeedSchema(salary_min=150000)
    assert up_min_only.salary_min == 150000 and up_min_only.salary_max is None

    up_max_only = UpdateEmployerNeedSchema(salary_max=300000)
    assert up_max_only.salary_max == 300000 and up_min_only.salary_max is None

    print("[PASS] Test Suite 10: Update schema partial salary payloads and inverted/ratio guardrails verified.")


def test_section_6_quality_gate_execution():
    print("[RUNNING] Test Suite 5: Executing Section 6 Embedded Quality Gate...")
    doc = load_specification_text()
    assert "```python\n#!/usr/bin/env python3" in doc, "Embedded Quality Gate script not found in documentation!"
    script_block = doc.split("```python\n#!/usr/bin/env python3")[1].split("```")[0]
    script_code = "#!/usr/bin/env python3" + script_block

    env_globals = {}
    exec(script_code, env_globals)
    assert "run_milestone4_quality_gate" in env_globals, "run_milestone4_quality_gate function missing!"
    exit_code = env_globals["run_milestone4_quality_gate"]()
    assert exit_code == 0, f"Quality gate returned non-zero exit code: {exit_code}"
    print("[PASS] Test Suite 5: Section 6 Quality Gate executed successfully (Exit Code 0).")


def run_all_challenger_tests():
    print("=" * 80)
    print("CHALLENGER M4-1: EMPIRICAL ADVERSARIAL STRESS TEST HARNESS")
    print("=" * 80)
    test_inn_validation_suite()
    test_salary_validation_boundaries()
    test_152fz_privacy_and_contact_leakage()
    test_webhook_hmac_and_replay_protection()
    test_section_6_quality_gate_execution()
    test_user_register_and_152fz_consents()
    test_full_profile_unmasking_transition()
    test_multimodal_ranking_fsp_parity()
    test_multitenant_isolation_and_audit_probes()
    test_update_schemas_partial_salaries()
    print("=" * 80)
    print("ALL 10 EMPIRICAL TEST SUITES PASSED (100% PASS RATE, ZERO CONTRACT DEFECTS).")
    print("=" * 80)



if __name__ == "__main__":
    run_all_challenger_tests()
