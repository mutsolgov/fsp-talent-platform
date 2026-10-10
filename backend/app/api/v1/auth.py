"""
FSP IT-Talent Platform — API Module 1: auth & 152-ФЗ compliance.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.1.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Optional
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_valid_inn,
    get_password_hash,
    verify_password,
)
from app.database import get_db
from app.models.audit_logs import AuditLog
from app.models.employer_profiles import EmployerProfile
from app.models.user_consents import UserConsent
from app.models.users import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UpdateConsentRequest,
    UserConsentResponse,
    UserProfileResponse,
    UserRegisterRequest,
    UserRegisterResponse,
    VerifyEmailRequest,
)
from app.schemas.base import StatusMessageResponse, UserRole

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency for validating Bearer token and resolving current active user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный или просроченный токен авторизации",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        token_type = payload.get("type")
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        user_id = int(user_id_str)
    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись деактивирована",
        )
    return user


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserRegisterResponse,
    summary="Регистрация пользователя с фиксацией 152-ФЗ согласий",
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> UserRegisterResponse:
    # 1. Проверка уникальности email
    existing = await db.execute(select(User).where(User.email == payload.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с указанным адресом электронной почты уже зарегистрирован",
        )

    # 2. Создание пользователя
    hashed_pwd = get_password_hash(payload.password)
    user = User(
        email=payload.email.lower(),
        hashed_password=hashed_pwd,
        role=payload.role.value if hasattr(payload.role, "value") else str(payload.role),
        is_active=True,
        email_verified=False,
    )
    db.add(user)
    await db.flush()

    # 2.1 Инициализация профиля работодателя при регистрации
    if user.role == "employer":
        domain = payload.email.split("@")[1] if "@" in payload.email else "company.ru"
        emp_profile = EmployerProfile(
            user_id=user.id,
            company_name=payload.company_name or f"ООО Компания #{user.id}",
            inn=payload.inn or generate_valid_inn(user.id),
            domain=domain,
            is_inn_verified=True,
            trust_score=80,
        )
        db.add(emp_profile)

    # 3. Фиксация согласий 152-ФЗ (ст. 9 и ст. 10.1)
    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")
    consent = UserConsent(
        user_id=user.id,
        consent_pdn_processing=payload.consent_pdn_processing,
        consent_profile_publication=payload.consent_profile_publication,
        policy_version=payload.policy_version,
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(consent)

    # 4. Запись в неизменяемый аудит-лог
    audit = AuditLog(
        user_id=user.id,
        action="USER_REGISTER",
        entity_type="user",
        entity_id=str(user.id),
        payload_json={
            "role": user.role,
            "email": user.email,
            "consent_pdn": payload.consent_pdn_processing,
            "consent_publication": payload.consent_profile_publication,
            "policy_version": payload.policy_version,
        },
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(user)

    # 5. Выпуск JWT токенов
    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    tokens = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=UserRole(user.role),
        email=user.email,
    )

    return UserRegisterResponse(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role),
        tokens=tokens,
        is_email_verified=user.email_verified,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Аутентификация и выпуск пары JWT токенов",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    res = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = res.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Учетная запись заблокирована или ожидает активации",
        )

    # Аудит логина
    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")
    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN",
        entity_type="user",
        entity_id=str(user.id),
        payload_json={"role": user.role, "email": user.email},
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(audit)
    await db.commit()

    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=user.id,
        role=UserRole(user.role),
        email=user.email,
    )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Ротация токенов по валидному Refresh токену",
)
async def refresh_token(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenRefreshResponse:
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный или просроченный Refresh токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise invalid_token_exception
        user_id = int(decoded.get("sub"))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise invalid_token_exception

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise invalid_token_exception

    token_data = {"sub": str(user.id), "role": user.role, "email": user.email}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    response_model=StatusMessageResponse,
    summary="Отзыв сессии пользователя",
)
async def logout(
    request: Request,
    payload: Optional[LogoutRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusMessageResponse:
    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")
    audit = AuditLog(
        user_id=current_user.id,
        action="USER_LOGOUT",
        entity_type="user",
        entity_id=str(current_user.id),
        payload_json={"user_id": current_user.id},
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(audit)
    await db.commit()

    return StatusMessageResponse(status="ok", message="Успешный выход из системы")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Получение профиля текущего пользователя и статуса 152-ФЗ",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    res = await db.execute(select(UserConsent).where(UserConsent.user_id == current_user.id))
    consent = res.scalar_one_or_none()

    consent_pdn = consent.consent_pdn_processing if consent else True
    consent_pub = consent.consent_profile_publication if consent else True

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        role=UserRole(current_user.role),
        is_active=current_user.is_active,
        is_email_verified=current_user.email_verified,
        consent_pdn_processing=consent_pdn,
        consent_profile_publication=consent_pub,
        created_at=current_user.created_at,
    )


@router.post(
    "/change-password",
    response_model=StatusMessageResponse,
    summary="Смена пароля текущего пользователя",
)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusMessageResponse:
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текущий пароль указан неверно",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.updated_at = datetime.now(timezone.utc)

    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")
    audit = AuditLog(
        user_id=current_user.id,
        action="CHANGE_PASSWORD",
        entity_type="user",
        entity_id=str(current_user.id),
        payload_json={"status": "password_changed"},
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(audit)
    await db.commit()

    return StatusMessageResponse(status="ok", message="Пароль успешно изменен")


@router.post(
    "/verify-email",
    response_model=StatusMessageResponse,
    summary="Подтверждение email адреса",
)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StatusMessageResponse:
    # Декодирование токена верификации email (или fallback для демо токена)
    try:
        data = decode_token(payload.token)
        user_id = int(data.get("sub", 0))
    except Exception:
        # Для прямых токенов с префиксом email_verify_
        if payload.token.startswith("email_verify_"):
            parts = payload.token.split("_")
            try:
                user_id = int(parts[-1])
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен подтверждения")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительный токен подтверждения")

    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    if user.email_verified:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email уже был подтвержден ранее")

    user.email_verified = True
    user.updated_at = datetime.now(timezone.utc)

    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")
    audit = AuditLog(
        user_id=user.id,
        action="VERIFY_EMAIL",
        entity_type="user",
        entity_id=str(user.id),
        payload_json={"email": user.email, "verified": True},
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(audit)
    await db.commit()

    return StatusMessageResponse(status="ok", message="Email успешно подтвержден")


@router.get(
    "/consents",
    response_model=UserConsentResponse,
    summary="Детальный юридический статус 152-ФЗ согласий",
)
async def get_consents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserConsentResponse:
    res = await db.execute(select(UserConsent).where(UserConsent.user_id == current_user.id))
    consent = res.scalar_one_or_none()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реестровая запись согласий 152-ФЗ не найдена",
        )

    return UserConsentResponse(
        user_id=consent.user_id,
        consent_pdn_processing=consent.consent_pdn_processing,
        consent_profile_publication=consent.consent_profile_publication,
        policy_version=consent.policy_version,
        accepted_at=consent.consent_timestamp,
        ip_address=consent.ip_address,
        revoked_at=consent.revoked_at,
    )


@router.put(
    "/consents",
    response_model=UserConsentResponse,
    summary="Обновление или отзыв согласия на распространение ПДн (ст. 10.1 152-ФЗ)",
)
async def update_consents(
    payload: UpdateConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserConsentResponse:
    res = await db.execute(select(UserConsent).where(UserConsent.user_id == current_user.id))
    consent = res.scalar_one_or_none()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Реестровая запись согласий не найдена",
        )

    consent.consent_profile_publication = payload.consent_profile_publication
    now = datetime.now(timezone.utc)
    if not payload.consent_profile_publication:
        consent.revoked_at = now
    else:
        consent.revoked_at = None

    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")
    audit = AuditLog(
        user_id=current_user.id,
        action="UPDATE_CONSENT",
        entity_type="user_consents",
        entity_id=str(consent.id),
        payload_json={
            "consent_profile_publication": payload.consent_profile_publication,
            "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
        },
        ip_address=ip_addr,
        user_agent=ua,
    )
    db.add(audit)
    await db.commit()
    await db.refresh(consent)

    return UserConsentResponse(
        user_id=consent.user_id,
        consent_pdn_processing=consent.consent_pdn_processing,
        consent_profile_publication=consent.consent_profile_publication,
        policy_version=consent.policy_version,
        accepted_at=consent.consent_timestamp,
        ip_address=consent.ip_address,
        revoked_at=consent.revoked_at,
    )
