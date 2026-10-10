"""ReportLab colors module."""
from __future__ import annotations
from typing import Tuple


class Color:
    def __init__(self, red: float = 0.0, green: float = 0.0, blue: float = 0.0, alpha: float = 1.0):
        self.red = float(red)
        self.green = float(green)
        self.blue = float(blue)
        self.alpha = float(alpha)

    def __repr__(self) -> str:
        return f"Color({self.red:.2f}, {self.green:.2f}, {self.blue:.2f}, {self.alpha:.2f})"


class HexColor(Color):
    def __init__(self, val: str):
        val = val.lstrip("#")
        if len(val) == 6:
            r = int(val[0:2], 16) / 255.0
            g = int(val[2:4], 16) / 255.0
            b = int(val[4:6], 16) / 255.0
            alpha = 1.0
        elif len(val) == 8:
            r = int(val[0:2], 16) / 255.0
            g = int(val[2:4], 16) / 255.0
            b = int(val[4:6], 16) / 255.0
            alpha = int(val[6:8], 16) / 255.0
        elif len(val) == 3:
            r = int(val[0] * 2, 16) / 255.0
            g = int(val[1] * 2, 16) / 255.0
            b = int(val[2] * 2, 16) / 255.0
            alpha = 1.0
        else:
            r, g, b, alpha = 0.0, 0.0, 0.0, 1.0
        super().__init__(r, g, b, alpha)


white = Color(1.0, 1.0, 1.0)
black = Color(0.0, 0.0, 0.0)
red = Color(1.0, 0.0, 0.0)
green = Color(0.0, 1.0, 0.0)
blue = Color(0.0, 0.0, 1.0)
gray = Color(0.5, 0.5, 0.5)
lightgrey = HexColor("#E5E7EB")
transparent = Color(0.0, 0.0, 0.0, 0.0)
