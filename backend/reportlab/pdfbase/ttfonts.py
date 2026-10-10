"""ReportLab TTFont module."""
from __future__ import annotations


class TTFont:
    def __init__(self, name: str, filename: str):
        self.name = name
        self.filename = filename

    def __repr__(self) -> str:
        return f"TTFont({self.name}, {self.filename})"
