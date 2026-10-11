"""
FSP IT-Talent Platform — Non-Coercive Grading Engine & Cooldown Controller.
Implements non-punitive assessment evaluation, 30-day cooldown, and jury bypass.
Defined in docs/03_ALGORITHMS_AND_BUSINESS_LOGIC.md §2.4–2.5 and DISPATCH.md.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import os
from typing import Any, Dict, Optional, Tuple


class GradingEngine:
    """Некарательный движок принятия решений по грейдам и контроллер кулдауна."""

    GRADE_RANKS: Dict[str, int] = {
        "junior": 1,
        "middle": 2,
        "senior": 3,
        "lead": 4,
        "Junior": 1,
        "Middle": 2,
        "Senior": 3,
        "Lead": 4,
    }
    RANK_TO_GRADE: Dict[int, str] = {
        1: "Junior",
        2: "Middle",
        3: "Senior",
        4: "Lead",
    }
    COOLDOWN_DAYS: int = int(os.getenv("COOLDOWN_DAYS", "90"))

    @classmethod
    def evaluate_session(
        cls,
        candidate_id: int,
        claimed_grade: str,
        theta_score: float,
        session_type: str = "initial",
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Оценивает результат тестирования по некарательным правилам платформы:
        - theta < 70.0: без понижения, предлагается ретест на уровень ниже (без кулдауна).
        - 70.0 <= theta < 88.0: подтверждение грейда, кулдаун 90 дней.
        - theta >= 88.0: подтверждение грейда, добровольный риск-фри буст-тест.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        canonical_grade = claimed_grade.capitalize()
        current_rank = cls.GRADE_RANKS.get(canonical_grade, 2)

        # 1. Оценка буст-теста
        if session_type == "boost":
            if theta_score >= 70.0:
                cooldown_until = now + timedelta(days=cls.COOLDOWN_DAYS)
                return {
                    "verdict": "confirmed",
                    "confirmed_grade": canonical_grade,
                    "theta_score": theta_score,
                    "is_grade_confirmed": True,
                    "boost_passed": True,
                    "boost_offered": False,
                    "retest_lower_offered": False,
                    "cooldown_until": cooldown_until,
                    "message": f"Буст-тест успешно пройден ({theta_score:.1f}/100)! Подтвержден повышенный грейд {canonical_grade}.",
                }
            else:
                # Гарантия некарательного буста: сохранение базового грейда без штрафа и без кулдауна
                prev_grade = cls.RANK_TO_GRADE.get(max(1, current_rank - 1), canonical_grade)
                return {
                    "verdict": "confirmed",
                    "confirmed_grade": prev_grade,
                    "theta_score": theta_score,
                    "is_grade_confirmed": True,
                    "boost_passed": False,
                    "boost_offered": False,
                    "retest_lower_offered": False,
                    "cooldown_until": None,
                    "message": f"Буст-тест не сдан ({theta_score:.1f} < 70). Базовый грейд {prev_grade} сохранен в полном объеме.",
                }

        # 2. Оценка стандартного или ретест-сеанса
        if theta_score < 70.0:
            lower_grade = cls.RANK_TO_GRADE.get(current_rank - 1, None) if current_rank > 1 else None
            return {
                "verdict": "retest_lower_offered" if lower_grade else "failed",
                "confirmed_grade": None,
                "theta_score": theta_score,
                "is_grade_confirmed": False,
                "boost_offered": False,
                "retest_lower_offered": (lower_grade is not None),
                "suggested_grade": lower_grade,
                "cooldown_until": None,  # Мгновенный ретест на грейд ниже доступен без кулдауна
                "message": (
                    f"Грейд {canonical_grade} не подтвержден ({theta_score:.1f} < 70). Принудительного понижения нет. "
                    f"Вы можете прямо сейчас пройти тестирование на уровень {lower_grade} без кулдауна."
                    if lower_grade
                    else f"Грейд {canonical_grade} не подтвержден ({theta_score:.1f} < 70). Рекомендуем повторить теорию."
                ),
            }
        elif 70.0 <= theta_score < 88.0:
            cooldown_until = now + timedelta(days=cls.COOLDOWN_DAYS)
            return {
                "verdict": "confirmed",
                "confirmed_grade": canonical_grade,
                "theta_score": theta_score,
                "is_grade_confirmed": True,
                "boost_offered": False,
                "retest_lower_offered": False,
                "suggested_grade": None,
                "cooldown_until": cooldown_until,
                "message": f"Поздравляем! Заявленный грейд {canonical_grade} подтвержден ({theta_score:.1f}/100).",
            }
        else:  # theta >= 88.0
            higher_grade = cls.RANK_TO_GRADE.get(current_rank + 1, None) if current_rank < 4 else None
            cooldown_until = now + timedelta(days=cls.COOLDOWN_DAYS)
            return {
                "verdict": "boost_offered" if higher_grade else "confirmed",
                "confirmed_grade": canonical_grade,
                "theta_score": theta_score,
                "is_grade_confirmed": True,
                "boost_offered": (higher_grade is not None),
                "retest_lower_offered": False,
                "suggested_grade": higher_grade,
                "cooldown_until": cooldown_until,
                "message": (
                    f"Грейд {canonical_grade} подтвержден с отличием ({theta_score:.1f}/100)! "
                    f"Вам доступен риск-фри буст-тест на грейд {higher_grade} прямо сейчас."
                    if higher_grade
                    else f"Наивысший результат! Грейд {canonical_grade} подтвержден с отличием ({theta_score:.1f}/100)."
                ),
            }

    @classmethod
    def check_cooldown(
        cls,
        cooldown_until: Optional[datetime],
        target_grade: str,
        current_confirmed_grade: Optional[str] = None,
        is_demo_bypass: bool = False,
        now: Optional[datetime] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет активность 90-дневного кулдауна:
        - is_demo_bypass = True: моментальный обход для жюри
        - Сдача на более низкий грейд: разрешена без кулдауна
        - Сдача на равный или повышенный грейд: блокируется до истечения cooldown_until
        """
        if is_demo_bypass:
            return True, None

        if cooldown_until is None:
            return True, None

        if now is None:
            now = datetime.now(timezone.utc)

        # Обеспечиваем одинаковую осведомленность о таймзонах
        if cooldown_until.tzinfo is None:
            cooldown_until = cooldown_until.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        if now < cooldown_until:
            if current_confirmed_grade:
                current_rank = cls.GRADE_RANKS.get(current_confirmed_grade.capitalize(), 0)
                target_rank = cls.GRADE_RANKS.get(target_grade.capitalize(), 0)
                if target_rank < current_rank:
                    return True, None

            remaining_days = max(1, math.ceil((cooldown_until - now).total_seconds() / 86400.0))
            return (
                False,
                f"Действует {cls.COOLDOWN_DAYS}-дневный кулдаун смены грейда (осталось {remaining_days} дн.). Доступен демо-сброс для жюри.",
            )

        return True, None
