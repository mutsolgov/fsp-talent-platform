"""ReportLab styles module."""
from __future__ import annotations
from typing import Any, Dict, Optional
from reportlab.lib import colors


class ParagraphStyle:
    def __init__(
        self,
        name: str,
        parent: Optional[ParagraphStyle] = None,
        fontName: str = "Helvetica",
        fontSize: float = 10.0,
        leading: float = 12.0,
        alignment: int = 0,
        textColor: Any = colors.black,
        spaceAfter: float = 0.0,
        spaceBefore: float = 0.0,
        **kwargs: Any,
    ):
        self.name = name
        self.parent = parent
        self.fontName = fontName
        self.fontSize = fontSize
        self.leading = leading
        self.alignment = alignment
        self.textColor = textColor
        self.spaceAfter = spaceAfter
        self.spaceBefore = spaceBefore
        for k, v in kwargs.items():
            setattr(self, k, v)


class StyleSheet:
    def __init__(self):
        self._styles: Dict[str, ParagraphStyle] = {}

    def add(self, style: ParagraphStyle) -> None:
        self._styles[style.name] = style

    def __getitem__(self, key: str) -> ParagraphStyle:
        return self._styles[key]

    def __contains__(self, key: str) -> bool:
        return key in self._styles


def getSampleStyleSheet() -> StyleSheet:
    ss = StyleSheet()
    normal = ParagraphStyle("Normal", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.black)
    ss.add(normal)
    ss.add(ParagraphStyle("BodyText", parent=normal, spaceBefore=6))
    ss.add(ParagraphStyle("Heading1", parent=normal, fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=8))
    ss.add(ParagraphStyle("Heading2", parent=normal, fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=6))
    ss.add(ParagraphStyle("Heading3", parent=normal, fontName="Helvetica-Bold", fontSize=12, leading=15, spaceAfter=4))
    ss.add(ParagraphStyle("Title", parent=normal, fontName="Helvetica-Bold", fontSize=24, leading=28, spaceAfter=12, alignment=1))
    return ss
