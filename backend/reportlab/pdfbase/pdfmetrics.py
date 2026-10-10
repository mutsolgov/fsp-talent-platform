"""ReportLab pdfmetrics module."""
from __future__ import annotations
from typing import Any, Dict

_FONTS: Dict[str, Any] = {}


def registerFont(font: Any) -> None:
    name = getattr(font, "name", str(font))
    _FONTS[name] = font


def getFont(name: str) -> Any:
    return _FONTS.get(name)
