"""
FSP IT-Talent Platform — Anti-Fraud & Employer Trust Verification Service.
Defined in docs/03 §5.3-5.6 and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
import socket
from typing import Optional, Set, Tuple

from app.models.employer_profiles import EmployerProfile

# List of prohibited free/consumer webmail domains
FREE_MAIL_PROVIDERS: Set[str] = {
    "gmail.com",
    "googlemail.com",
    "mail.ru",
    "inbox.ru",
    "bk.ru",
    "list.ru",
    "internet.ru",
    "yandex.ru",
    "ya.ru",
    "yandex.com",
    "rambler.ru",
    "lenta.ru",
    "autorambler.ru",
    "myrambler.ru",
    "ro.ru",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "me.com",
    "mac.com",
    "proton.me",
    "protonmail.com",
    "tutanota.com",
    "gmx.com",
    "zoho.com",
    "tempmail.com",
    "10minutemail.com",
}


def verify_inn(inn: str) -> bool:
    """
    Validates Russian Tax ID (ИНН) checksum using official FNS algorithm:
    - 10 digits for legal entities (Юрлица)
    - 12 digits for individual entrepreneurs (ИП / Физлица)
    """
    if not isinstance(inn, str):
        return False
    inn = inn.strip()

    if len(inn) == 10:
        if not inn.isdigit():
            return False
        digits = [int(d) for d in inn]
        weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        c10 = (sum(d * w for d, w in zip(digits[:9], weights)) % 11) % 10
        return c10 == digits[9]

    elif len(inn) == 12:
        if not inn.isdigit():
            return False
        digits = [int(d) for d in inn]
        weights_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        c11 = (sum(d * w for d, w in zip(digits[:10], weights_11)) % 11) % 10
        if c11 != digits[10]:
            return False
        weights_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
        c12 = (sum(d * w for d, w in zip(digits[:11], weights_12)) % 11) % 10
        return c12 == digits[11]

    return False


def verify_corporate_domain(email_or_domain: str, check_dns: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validates that employer email or domain belongs to a bona fide corporate domain:
    1. Rejects public free consumer mail providers (gmail, mail.ru, yandex, etc.)
    2. Validates domain structure
    3. Optionally verifies MX records via DNS
    """
    if not email_or_domain:
        return False, "Домен или адрес электронной почты не может быть пустым"

    domain = email_or_domain.lower().strip()
    if "@" in domain:
        domain = domain.split("@")[-1]

    # Clean domain
    domain = domain.lstrip("http://").lstrip("https://").split("/")[0]

    if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
        return False, "Некорректный формат доменного имени"

    if domain in FREE_MAIL_PROVIDERS:
        return False, f"Использование бесплатных почтовых сервисов ({domain}) для аккаунтов работодателей запрещено. Укажите корпоративную почту."

    if check_dns:
        try:
            # Check host resolution
            socket.gethostbyname(domain)
        except (socket.gaierror, socket.herror):
            return False, f"Домен {domain} не зарегистрирован или недоступен в DNS"

    return True, None


def validate_salary_range(salary_min: int, salary_max: int) -> Tuple[bool, Optional[str]]:
    """
    Enforces mandatory salary transparency and spread invariants (EC-01, EC-02, EC-16):
    - salary_min > 0 (RUB)
    - salary_max >= salary_min (RUB)
    - salary_max / salary_min <= 3.5 (Anti-Fraud Spread Ratio)
    """
    if salary_min <= 0:
        return False, "Минимальная заработная плата должна быть строго больше 0 рублей (скрытые зарплаты запрещены)."

    if salary_max < salary_min:
        return False, "Максимальная заработная плата не может быть меньше минимальной."

    ratio = float(salary_max) / float(salary_min)
    if ratio > 3.5:
        return False, f"Разброс зарплатной вилки ({ratio:.2f}) превышает допустимый антифрод-лимит 3.5."

    return True, None


def can_send_invitation(employer: EmployerProfile) -> Tuple[bool, int]:
    """
    Checks token-bucket daily quota (EC-17): max 20 invitations/day per employer.
    Resets counter if 24 hours have elapsed since last reset.
    Returns (is_allowed, remaining_quota).
    """
    now = datetime.now(timezone.utc)
    last_reset = employer.last_invite_reset_at
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    # Check if a new calendar day has started
    if now.date() > last_reset.date():
        employer.invites_sent_today = 0
        employer.last_invite_reset_at = now

    limit = employer.invite_daily_limit or 20
    remaining = max(0, limit - employer.invites_sent_today)

    if employer.invites_sent_today >= limit:
        return False, 0

    return True, remaining


def record_invitation_sent(employer: EmployerProfile) -> None:
    """Increments the invite counter for the employer."""
    now = datetime.now(timezone.utc)
    last_reset = employer.last_invite_reset_at
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=timezone.utc)

    if now.date() > last_reset.date():
        employer.invites_sent_today = 1
        employer.last_invite_reset_at = now
    else:
        employer.invites_sent_today += 1
