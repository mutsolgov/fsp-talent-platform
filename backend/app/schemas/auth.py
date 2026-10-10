"""
FSP IT-Talent Platform — Pydantic v2 Models for Module 1: auth & 152-ФЗ compliance.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.security import validate_inn_checksum
from app.schemas.base import BaseSchema, UserRole, StatusMessageResponse


class UserRegisterRequest(BaseSchema):
    email: EmailStr = Field(..., description="Корпоративный или личный адрес электронной почты")
    password: str = Field(..., min_length=8, max_length=128, description="Пароль учетной записи")
    role: UserRole = Field(..., description="Роль при регистрации: candidate или employer")
    consent_pdn_processing: bool = Field(..., description="Согласие на обработку ПДн (ст. 9 152-ФЗ РФ)")
    consent_profile_publication: bool = Field(default=True, description="Согласие на публикацию (ст. 10.1 152-ФЗ)")
    policy_version: str = Field(default="v1.0-2026", description="Версия акцептованной политики конфиденциальности")
    first_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Имя (для соискателя)")
    last_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Фамилия (для соискателя)")
    company_name: Optional[str] = Field(None, min_length=2, max_length=255, description="Название компании")
    inn: Optional[str] = Field(None, description="ИНН организации (10 цифр) или ИП (12 цифр)")

    @field_validator("consent_pdn_processing")
    @classmethod
    def validate_mandatory_pdn(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Регистрация невозможна без согласия на обработку ПДн (152-ФЗ)")
        return v

    @model_validator(mode="after")
    def validate_role_fields(self) -> "UserRegisterRequest":
        if self.role == UserRole.EMPLOYER:
            if not self.company_name:
                raise ValueError("Для работодателя обязательно указание наименования организации")
            if not self.inn:
                raise ValueError("Для работодателя обязательно указание ИНН")
            if not validate_inn_checksum(self.inn):
                raise ValueError("Указан некорректный контрольный разряд ИНН организации (ERR_INVALID_INN_CHECKSUM)")
        elif self.role == UserRole.CANDIDATE:
            if not self.first_name or not self.last_name:
                raise ValueError("Для соискателя обязательно указание имени и фамилии")
        return self


class TokenResponse(BaseSchema):
    access_token: str = Field(..., description="JWT Access Token (срок действия 15 минут)")
    refresh_token: str = Field(..., description="JWT Refresh Token (срок действия 7 дней)")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(default=900, description="Время жизни Access токена в секундах")
    user_id: int
    role: UserRole
    email: EmailStr


class UserRegisterResponse(BaseSchema):
    user_id: int
    email: EmailStr
    role: UserRole
    tokens: TokenResponse
    is_email_verified: bool = False
    created_at: datetime


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class TokenRefreshRequest(BaseSchema):
    refresh_token: str = Field(..., description="Одноразовый Refresh токен")


class TokenRefreshResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = 900


class LogoutRequest(BaseSchema):
    refresh_token: Optional[str] = None


class UserProfileResponse(BaseSchema):
    id: int
    email: EmailStr
    role: UserRole
    is_active: bool
    is_email_verified: bool
    candidate_profile_id: Optional[int] = None
    employer_profile_id: Optional[int] = None
    consent_pdn_processing: bool
    consent_profile_publication: bool
    created_at: datetime


class ChangePasswordRequest(BaseSchema):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_passwords_differ(self) -> "ChangePasswordRequest":
        if self.old_password == self.new_password:
            raise ValueError("Новый пароль должен отличаться от старого")
        return self


class VerifyEmailRequest(BaseSchema):
    token: str = Field(..., min_length=32)


class UserConsentResponse(BaseSchema):
    user_id: int
    consent_pdn_processing: bool
    consent_profile_publication: bool
    policy_version: str
    accepted_at: datetime
    ip_address: Optional[str] = None
    revoked_at: Optional[datetime] = None


class UpdateConsentRequest(BaseSchema):
    consent_profile_publication: bool = Field(..., description="Флаг согласия на распространение ПДн (ст. 10.1)")
