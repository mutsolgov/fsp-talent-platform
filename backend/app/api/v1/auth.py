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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
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
from app.models.candidate_profiles import CandidateProfile
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


async def get_current_user_flexible(
    request: Request,
    token: Optional[str] = Query(None, description="Access token via query param for direct browser download"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Flexible authentication dependency for file download and preview endpoints.

    Supports:
    1. Authorization: Bearer <token> header
    2. Query parameter ?token=<token>
    3. Fallback to active demo candidate user when DEMO_BYPASS_ENABLED=True and no token is passed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный или просроченный токен авторизации",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Step 1: Check Authorization header (Authorization: Bearer <token>)
    raw_token: Optional[str] = None
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header:
        parts = auth_header.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            raw_token = parts[1].strip()
        elif len(parts) == 1 and not parts[0].lower().startswith("bearer"):
            raw_token = parts[0].strip()

    # Step 2: If no header, check token query param
    if not raw_token:
        if token:
            raw_token = token.strip()
        elif hasattr(request, "query_params") and request.query_params:
            q_token = request.query_params.get("token")
            if q_token:
                raw_token = q_token.strip()

    # Step 3: If token is provided, decode via decode_token(token).
    # If invalid/expired/not access type, raise HTTPException 401.
    # If valid, fetch active user from DB. If user inactive, raise 403. Return user.
    # IMPORTANT: If a token was supplied but is invalid, NEVER fall back to demo mode — raise 401 immediately!
    if raw_token:
        try:
            payload = decode_token(raw_token)
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

    # Step 4: If NO token was provided at all (both header and query param are None):
    # Check getattr(settings, "DEMO_BYPASS_ENABLED", True).
    # If True, resolve demo candidate user (query User.role == "candidate" and User.is_active == True, fallback to email mikhail.popov@fsp-russia.ru).
    demo_bypass = getattr(settings, "DEMO_BYPASS_ENABLED", True)
    if isinstance(demo_bypass, str):
        demo_bypass = demo_bypass.lower() in ("true", "1", "yes")

    if demo_bypass:
        stmt = select(User).where(User.role == "candidate", User.is_active == True)
        res = await db.execute(stmt)
        candidates = res.scalars().all()
        # Prefer canonical demo candidate Mikhail Popov if present among active candidates
        demo_user = next((u for u in candidates if u.email == "mikhail.popov@fsp-russia.ru"), None)
        if not demo_user and candidates:
            demo_user = candidates[0]

        # Fallback to email mikhail.popov@fsp-russia.ru
        if not demo_user:
            res_email = await db.execute(
                select(User).where(User.email == "mikhail.popov@fsp-russia.ru")
            )
            demo_user = res_email.scalar_one_or_none()

        # If user does not exist at all in DB, provision Mikhail Popov + CandidateProfile
        if not demo_user:
            demo_user = User(
                email="mikhail.popov@fsp-russia.ru",
                hashed_password=get_password_hash("fsp_demo_secret_2026"),
                role="candidate",
                is_active=True,
                email_verified=True,
            )
            db.add(demo_user)
            await db.flush()

            c_prof = CandidateProfile(
                user_id=demo_user.id,
                first_name="Михаил",
                last_name="Попов",
                city="Москва",
                work_format="remote",
                fsp_id="FSP-103",
                fsp_verified=True,
                freshness_score=95.0,
                is_published=True,
            )
            db.add(c_prof)
            await db.commit()
            await db.refresh(demo_user)

        return demo_user

    # Step 5: If no token and DEMO_BYPASS_ENABLED is False, raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"}).
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


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
    # Строгое криптографическое декодирование токена верификации email
    try:
        data = decode_token(payload.token)
        user_id_str = data.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недействительный токен подтверждения",
            )
        user_id = int(user_id_str)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недействительный токен подтверждения",
        )

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
    summary="Обновление или отзыв согласия на распространение ПДн (ст. 10.1 152-ФЗ) с поддержкой UPSERT",
)
async def update_consents(
    payload: UpdateConsentRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserConsentResponse:
    res = await db.execute(select(UserConsent).where(UserConsent.user_id == current_user.id))
    consent = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")

    if not consent:
        consent_pdn = payload.consent_pdn_processing if payload.consent_pdn_processing is not None else True
        consent_pub = payload.consent_profile_publication if payload.consent_profile_publication is not None else True
        revoked = now if (not consent_pdn or not consent_pub) else None
        consent = UserConsent(
            user_id=current_user.id,
            consent_pdn_processing=consent_pdn,
            consent_profile_publication=consent_pub,
            policy_version="1.0-FSP",
            ip_address=ip_addr,
            user_agent=ua,
            consent_timestamp=now,
            revoked_at=revoked,
        )
        db.add(consent)
        await db.flush()
    else:
        if payload.consent_profile_publication is not None:
            consent.consent_profile_publication = payload.consent_profile_publication
        if payload.consent_pdn_processing is not None:
            consent.consent_pdn_processing = payload.consent_pdn_processing

        if not consent.consent_pdn_processing or not consent.consent_profile_publication:
            if not consent.revoked_at:
                consent.revoked_at = now
        else:
            consent.revoked_at = None

    # Если публикация профиля или обработка ПДн отозвана, скрываем профиль соискателя из поиска
    res_prof = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res_prof.scalar_one_or_none()
    if profile:
        if not consent.consent_profile_publication or not consent.consent_pdn_processing:
            profile.is_published = False
        else:
            profile.is_published = True

    audit = AuditLog(
        user_id=current_user.id,
        action="UPDATE_CONSENT",
        entity_type="user_consents",
        entity_id=str(consent.id),
        payload_json={
            "consent_profile_publication": consent.consent_profile_publication,
            "consent_pdn_processing": consent.consent_pdn_processing,
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


@router.get(
    "/export-archive",
    summary="Выгрузка архива персональных данных (ст. 14 152-ФЗ РФ)",
)
async def export_archive(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    # 1. User & Consents
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at.isoformat() if hasattr(current_user, "created_at") and current_user.created_at else None,
    }

    res_consent = await db.execute(select(UserConsent).where(UserConsent.user_id == current_user.id))
    consent = res_consent.scalar_one_or_none()
    consents_data = {
        "consent_pdn_processing": consent.consent_pdn_processing if consent else True,
        "consent_profile_publication": consent.consent_profile_publication if consent else True,
        "policy_version": consent.policy_version if consent else "1.0-FSP",
        "accepted_at": consent.consent_timestamp.isoformat() if consent and consent.consent_timestamp else None,
        "revoked_at": consent.revoked_at.isoformat() if consent and consent.revoked_at else None,
    }

    # 2. Candidate Profile
    res_prof = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res_prof.scalar_one_or_none()
    profile_data = None
    skills_data = []
    tests_data = []
    applications_data = []
    invitations_data = []

    if profile:
        profile_data = {
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "middle_name": profile.middle_name,
            "phone": profile.phone,
            "telegram": profile.telegram,
            "github_url": profile.github_url,
            "city": profile.city,
            "work_format": profile.work_format,
            "expected_salary": profile.expected_salary,
            "bio": profile.bio,
            "fsp_id": profile.fsp_id,
            "fsp_verified": profile.fsp_verified,
            "is_published": profile.is_published,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
        }

        # Skills
        from app.models.candidate_skills import CandidateSkill
        from app.models.skills import Skill
        res_skills = await db.execute(
            select(CandidateSkill, Skill.name)
            .join(Skill, CandidateSkill.skill_id == Skill.id, isouter=True)
            .where(CandidateSkill.candidate_profile_id == profile.id)
        )
        skills_data = [
            {
                "skill_id": cs.skill_id,
                "skill_name": sk_name or "",
                "proficiency_level": cs.proficiency_level,
                "years_experience": cs.years_experience,
                "is_verified": cs.is_verified,
            }
            for cs, sk_name in res_skills.all()
        ]

        # Assessment Sessions
        from app.models.assessment_sessions import AssessmentSession
        res_sess = await db.execute(select(AssessmentSession).where(AssessmentSession.candidate_profile_id == profile.id))
        tests_data = [
            {
                "session_id": sess.id,
                "session_type": sess.session_type,
                "status": sess.status,
                "final_theta": sess.theta_score,
                "theta_score": sess.theta_score,
                "raw_score": sess.raw_score,
                "verdict": sess.verdict,
                "completed_at": sess.completed_at.isoformat() if sess.completed_at else None,
            }
            for sess in res_sess.scalars().all()
        ]

        # Applications
        from app.models.applications import Application
        res_apps = await db.execute(select(Application).where(Application.candidate_profile_id == profile.id))
        applications_data = [
            {"vacancy_id": app.vacancy_id, "status": app.status, "applied_at": app.applied_at.isoformat() if app.applied_at else None}
            for app in res_apps.scalars().all()
        ]

        # Invitations
        from app.models.invitations import Invitation
        res_inv = await db.execute(select(Invitation).where(Invitation.candidate_profile_id == profile.id))
        invitations_data = [
            {"id": inv.id, "status": inv.status, "salary_min": inv.salary_min, "salary_max": inv.salary_max, "created_at": inv.created_at.isoformat() if inv.created_at else None}
            for inv in res_inv.scalars().all()
        ]

    # Audit Logs
    res_audit = await db.execute(
        select(AuditLog).where(AuditLog.user_id == current_user.id).order_by(AuditLog.created_at.desc()).limit(100)
    )
    audit_data = [
        {
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "payload": a.payload_json,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
        }
        for a in res_audit.scalars().all()
    ]

    archive = {
        "metadata": {
            "legal_basis": "Статья 14 Федерального закона от 27.07.2006 № 152-ФЗ «О персональных данных»",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "platform": "Цифровая платформа ИТ-талантов ФСП России",
        },
        "user": user_data,
        "consents": consents_data,
        "profile": profile_data,
        "skills": skills_data,
        "assessment_sessions": tests_data,
        "applications": applications_data,
        "invitations": invitations_data,
        "audit_logs": audit_data,
        "audit_trail": audit_data,
    }

    return JSONResponse(
        content=archive,
        headers={
            "Content-Disposition": 'attachment; filename="fsp_user_archive_152fz.json"',
            "Content-Type": "application/json; charset=utf-8",
        },
    )


@router.post(
    "/consents/revoke",
    response_model=UserConsentResponse,
    summary="Отзыв согласий на обработку и распространение ПДн (ст. 21 152-ФЗ)",
)
async def revoke_consents(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserConsentResponse:
    res = await db.execute(select(UserConsent).where(UserConsent.user_id == current_user.id))
    consent = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    ip_addr = request.client.host if request.client else "127.0.0.1"
    ua = request.headers.get("user-agent", "Unknown")

    if not consent:
        consent = UserConsent(
            user_id=current_user.id,
            consent_pdn_processing=False,
            consent_profile_publication=False,
            policy_version="1.0-FSP",
            ip_address=ip_addr,
            user_agent=ua,
            consent_timestamp=now,
            revoked_at=now,
        )
        db.add(consent)
        await db.flush()
    else:
        consent.consent_profile_publication = False
        consent.consent_pdn_processing = False
        consent.revoked_at = now

    # Hide candidate profile from search and public listings
    res_prof = await db.execute(select(CandidateProfile).where(CandidateProfile.user_id == current_user.id))
    profile = res_prof.scalar_one_or_none()
    if profile:
        profile.is_published = False

    audit = AuditLog(
        user_id=current_user.id,
        action="REVOKE_CONSENT",
        entity_type="user_consents",
        entity_id=str(consent.id),
        payload_json={
            "revoked_at": now.isoformat(),
            "reason": "Заявление субъекта ПДн по ст. 21 152-ФЗ РФ",
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
