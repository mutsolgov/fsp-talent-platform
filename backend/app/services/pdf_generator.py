"""
FSP IT-Talent Platform — Standardized ReportLab PDF Profile Generator (FR-CAND-03).
Formatted per assets/brand/example.png with JetBrains Mono TTF, blue accent #402FFF, and lineline1.png.
Defined in docs/03 §5.2, docs/05 §5.6.10, and DISPATCH.md.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Image, Paragraph, SimpleDocTemplate, Spacer

# Brand colors
FSP_BLUE_ACCENT = colors.HexColor("#402FFF")
FSP_DARK_TEXT = colors.HexColor("#1B1C21")
FSP_LIGHT_NODE = colors.HexColor("#C8C9CA")
FSP_GRAY_BG = colors.HexColor("#F5F6F8")
FSP_WATERMARK_GRAY = colors.HexColor("#E5E7EB")

# Locate brand assets robustly across host and container environments
def _find_brand_dir() -> Path:
    current_file = Path(__file__).resolve()
    candidates = [
        current_file.parent.parent.parent.parent / "assets" / "brand",  # host repo root
        current_file.parent.parent.parent / "assets" / "brand",         # docker /app/assets/brand
        Path("/app/assets/brand"),                                       # container absolute
        Path("assets/brand"),                                            # current working directory
    ]
    for cand in candidates:
        if (cand / "fonts" / "JetBrainsMono-Regular.ttf").exists():
            return cand
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


BRAND_DIR = _find_brand_dir()
FONTS_DIR = BRAND_DIR / "fonts"
LINELINE_IMG = BRAND_DIR / "lineline1.png"
LOGO_IMG = BRAND_DIR / "logo_small_blue.png"

# Register local TTF fonts
FONT_REGULAR = "JetBrainsMono"
FONT_BOLD = "JetBrainsMono-Bold"
FONT_MEDIUM = "JetBrainsMono-Medium"

try:
    reg_path = FONTS_DIR / "JetBrainsMono-Regular.ttf"
    bold_path = FONTS_DIR / "JetBrainsMono-Bold.ttf"
    med_path = FONTS_DIR / "JetBrainsMono-Medium.ttf"

    if reg_path.exists():
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(reg_path)))
    else:
        FONT_REGULAR = "Helvetica"

    if bold_path.exists():
        pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold_path)))
    else:
        FONT_BOLD = "Helvetica-Bold"

    if med_path.exists():
        pdfmetrics.registerFont(TTFont(FONT_MEDIUM, str(med_path)))
    else:
        FONT_MEDIUM = FONT_BOLD

    if hasattr(pdfmetrics, "registerFontFamily") and FONT_REGULAR == "JetBrainsMono":
        pdfmetrics.registerFontFamily(
            FONT_REGULAR,
            normal=FONT_REGULAR,
            bold=FONT_BOLD,
            italic=FONT_REGULAR,
            boldItalic=FONT_BOLD,
        )
except Exception:
    FONT_REGULAR = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"
    FONT_MEDIUM = "Helvetica-Bold"


def generate_fsp_profile_pdf(
    candidate_data: Dict[str, Any],
    is_full_mode: bool = False,
) -> bytes:
    """
    Generates branded FSP IT-Talent standardized PDF profile:
    - is_full_mode == False (Mode A): Masked contacts, watermark 'ПРЕДВАРИТЕЛЬНЫЙ ПРОФИЛЬ — 152-ФЗ'
    - is_full_mode == True (Mode B): Unmasked full contacts dossier
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40.0,
        rightMargin=40.0,
        topMargin=40.0,
        bottomMargin=40.0,
    )
    styles = getSampleStyleSheet()

    # Custom styles matching FSP brandbook
    header_style = ParagraphStyle(
        "FSPHeader",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=20,
        textColor=FSP_BLUE_ACCENT,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "FSPSubtitle",
        parent=styles["Normal"],
        fontName=FONT_MEDIUM,
        fontSize=10,
        leading=14,
        textColor=FSP_DARK_TEXT,
        spaceAfter=10,
    )
    h2_style = ParagraphStyle(
        "FSPH2",
        parent=styles["Heading2"],
        fontName=FONT_BOLD,
        fontSize=12,
        leading=16,
        textColor=FSP_BLUE_ACCENT,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "FSPBody",
        parent=styles["Normal"],
        fontName=FONT_REGULAR,
        fontSize=9,
        leading=13,
        textColor=FSP_DARK_TEXT,
    )
    badge_style = ParagraphStyle(
        "FSPBadge",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=9,
        leading=12,
        textColor=FSP_BLUE_ACCENT,
    )
    masked_notice_style = ParagraphStyle(
        "FSPMaskedNotice",
        parent=styles["Normal"],
        fontName=FONT_MEDIUM,
        fontSize=8,
        leading=12,
        textColor=colors.HexColor("#6B7280"),
    )

    story: List[Flowable] = []

    # 1. Header with FSP branding
    story.append(Paragraph("ФЕДЕРАЦИЯ СПОРТИВНОГО ПРОГРАММИРОВАНИЯ", header_style))
    story.append(Paragraph("ЦИФРОВОЙ ВЕРИФИЦИРОВАННЫЙ ПРОФИЛЬ IT-СПЕЦИАЛИСТА", subtitle_style))

    # Connector line graphic if available
    if LINELINE_IMG.exists():
        story.append(Image(str(LINELINE_IMG), width=515, height=6))
        story.append(Spacer(1, 8))
    else:
        story.append(Spacer(1, 10))

    # 2. Candidate Identification
    cand_id = candidate_data.get("id", 1001)
    if is_full_mode:
        cand_name = candidate_data.get("full_name") or f"{candidate_data.get('first_name', 'Иван')} {candidate_data.get('last_name', 'Иванов')}"
        story.append(Paragraph(f"<b>Кандидат:</b> {cand_name}", h2_style))

        email = candidate_data.get("email") or "—"
        phone = candidate_data.get("phone") or "—"
        tg = candidate_data.get("telegram") or "—"
        github = candidate_data.get("github_url") or "—"
        contacts_html = f"Email: <b>{email}</b> | Телефон: <b>{phone}</b><br/>Telegram: <b>{tg}</b> | GitHub: <b>{github}</b>"
        story.append(Paragraph(contacts_html, body_style))
    else:
        first = candidate_data.get("first_name", "Алексей")
        last = candidate_data.get("last_name", "Кузнецов")
        initial = f"{last[:1]}." if last else ""
        masked_name = candidate_data.get("masked_name") or f"{first} {initial} (#C-{cand_id})"
        story.append(Paragraph(f"<b>Кандидат:</b> {masked_name}", h2_style))
        story.append(Paragraph("<b>[КОНТАКТЫ ЗАЩИЩЕНЫ 152-ФЗ РФ]</b>", badge_style))
        story.append(
            Paragraph(
                "Прямые контактные данные (Email, Телефон, Telegram, GitHub) будут раскрыты автоматически после принятия соискателем вашего персонального приглашения.",
                masked_notice_style,
            )
        )

    story.append(Spacer(1, 10))

    # 3. Verified Category & KITE IRT Score
    raw_spec = candidate_data.get("specialization")
    raw_grade = candidate_data.get("grade")

    invalid_specs = ("none", "не выбрана", "не определена", "не выбрано", "")
    invalid_grades = ("none", "не определен", "не определено", "ожидает тестирования", "")

    spec_valid = bool(raw_spec and str(raw_spec).strip().lower() not in invalid_specs)
    grade_valid = bool(raw_grade and str(raw_grade).strip().lower() not in invalid_grades)

    if spec_valid and grade_valid:
        spec_text = str(raw_spec).capitalize()
        grade_text = str(raw_grade).capitalize()
        qual_text = f"Квалификация: <b>{spec_text} · {grade_text}</b>"
    else:
        qual_text = "Квалификация: <b>Ожидает верификации</b>"

    raw_score = candidate_data.get("test_score")
    if raw_score is None:
        raw_score = candidate_data.get("theta")

    try:
        score_val = float(raw_score) if raw_score is not None else 0.0
    except (ValueError, TypeError):
        score_val = 0.0

    if score_val > 0.0:
        score_text = f"Балл адаптивного тестирования KITE IRT: <b>{score_val:.1f} / 100</b>"
    else:
        score_text = "Балл адаптивного тестирования KITE IRT: <b>Тестирование не пройдено</b>"

    story.append(Paragraph("ПОДТВЕРЖДЕННАЯ КАТЕГОРИЯ", h2_style))
    cat_text = f"{qual_text}<br/>{score_text}"
    story.append(Paragraph(cat_text, body_style))

    story.append(Spacer(1, 10))

    # 4. FSP Verification Status & History
    fsp_id = candidate_data.get("fsp_id")
    story.append(Paragraph("СПОРТИВНОЕ ПРОГРАММИРОВАНИЕ (ФСП)", h2_style))
    if fsp_id:
        fsp_verified = candidate_data.get("fsp_verified", True)
        badge = "Верифицирован в реестре ФСП" if fsp_verified else "В процессе верификации"
        raw_rank = candidate_data.get("sport_rank")
        rank = str(raw_rank) if raw_rank and str(raw_rank).strip().lower() not in ("none", "") else "Без спортивного разряда"
        fsp_text = (
            f"Статус: <b>{badge}</b> (ФСП ID: {fsp_id})<br/>"
            f"Спортивный разряд: <b>{rank}</b>"
        )
        story.append(Paragraph(fsp_text, body_style))

        achievements = candidate_data.get("fsp_achievements", [])
        if achievements:
            story.append(Spacer(1, 4))
            ach_lines = []
            for ach in achievements[:4]:
                champ = ach.get("championship_name", "Всероссийский чемпионат")
                disc = ach.get("discipline", "algorithmic")
                place = ach.get("place", "Финалист")
                medal = ach.get("medal", "")
                medal_str = f" ({medal})" if medal else ""
                ach_lines.append(f"• {champ} [{disc}]: {place}{medal_str}")
            story.append(Paragraph("<br/>".join(ach_lines), body_style))
    else:
        non_fsp_text = (
            "Статус: <b>Платформенная верификация</b><br/>"
            "История соревнований ФСП отсутствует. Профиль подтвержден калиброванным тестом KITE и практической оценкой стека технологий без штрафов к рейтингу."
        )
        story.append(Paragraph(non_fsp_text, body_style))

    story.append(Spacer(1, 10))

    # 5. Technology Stack
    story.append(Paragraph("ПОДТВЕРЖДЕННЫЙ ТЕХНОЛОГИЧЕСКИЙ СТЕК", h2_style))
    skills = candidate_data.get("skills", [])
    if skills:
        skills_str = ", ".join(skills)
        story.append(Paragraph(f"Технологии: {skills_str}", body_style))
    else:
        story.append(
            Paragraph(
                "Навыки не подтверждены. Требуется прохождение онбординга и тестирования KITE.",
                body_style,
            )
        )

    # 6. Conditions & Preferences
    story.append(Spacer(1, 10))
    story.append(Paragraph("УСЛОВИЯ И ПРЕДПОЧТЕНИЯ", h2_style))
    raw_city = candidate_data.get("city")
    city_str = str(raw_city) if raw_city and str(raw_city).strip().lower() not in ("none", "") else "Не указан"

    raw_fmt = candidate_data.get("work_format")
    fmt_str = str(raw_fmt) if raw_fmt and str(raw_fmt).strip().lower() not in ("none", "") else "Не указан"

    exp_sal = candidate_data.get("expected_salary")
    if exp_sal is not None:
        try:
            sal_num = int(exp_sal)
            sal_str = f"{sal_num:,} ₽".replace(",", " ")
        except (ValueError, TypeError):
            sal_str = str(exp_sal)
    else:
        sal_str = "Не указана (по договоренности)"

    cond_text = f"Город: <b>{city_str}</b> | Формат работы: <b>{fmt_str}</b> | Ожидаемая ЗП: <b>{sal_str}</b>"
    story.append(Paragraph(cond_text, body_style))

    # Watermark callback for Mode A
    def draw_watermark(canvas: Any, _doc_obj: Any) -> None:
        if not is_full_mode:
            canvas.saveState()
            canvas.setFont(FONT_BOLD, 30)
            canvas.setFillColor(FSP_WATERMARK_GRAY, alpha=0.35)
            canvas.rotate(45)
            canvas.drawString(160, 50, "ПРЕДВАРИТЕЛЬНЫЙ ПРОФИЛЬ — 152-ФЗ")
            canvas.restoreState()

    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    return buffer.getvalue()
