"""
FSP IT-Talent Platform — Security, Cryptography & 152-ФЗ Compliance Utilities.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import re
from typing import Any, Dict, Optional
import jwt
from passlib.context import CryptContext

from app.core.config import settings

# Passlib CryptContext with bcrypt scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_inn_checksum(inn: str) -> bool:
    """
    Алгоритмическая проверка контрольных разрядов ИНН по весам ФНС РФ (docs/03 §5.3, docs/04 §2.1).
    10-значный ИНН: юридические лица.
    12-значный ИНН: индивидуальные предприниматели и физические лица.
    """
    if not isinstance(inn, str) or not re.match(r"^\d{10}$|^\d{12}$", inn):
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


def generate_valid_inn(seq: int = 1) -> str:
    """
    Генерация детерминированного валидного 10-значного ИНН с корректным контрольным разрядом
    по алгоритму весов ФНС РФ (docs/03 §5.3).
    """
    base = f"77{(seq % 10_000_000):07d}"
    digits = [int(d) for d in base]
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    c10 = (sum(d * w for d, w in zip(digits, weights)) % 11) % 10
    return f"{base}{c10}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля по хешу bcrypt."""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback to sha256 with salt if legacy format
        if hashed_password.startswith("sha256$"):
            _, salt, h = hashed_password.split("$")
            calc = hashlib.sha256((salt + plain_password).encode()).hexdigest()
            return hmac.compare_digest(calc, h)
        return False


def get_password_hash(password: str) -> str:
    """Генерация криптографического хеша пароля bcrypt."""
    try:
        return pwd_context.hash(password)
    except Exception:
        salt = os.urandom(16).hex()
        h = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"sha256${salt}${h}"


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Выпуск короткоживущего JWT Access токена (по умолчанию 15 минут)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "access",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Выпуск долгоживущего JWT Refresh токена (по умолчанию 7 дней)."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Декодирование и верификация подписи JWT токена."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
