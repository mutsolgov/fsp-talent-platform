"""ReportLab Canvas module."""
from __future__ import annotations
import io
import math
from typing import Any, List, Optional, Tuple
from reportlab.lib import colors


class Canvas:
    def __init__(self, filename_or_buffer: Any, pagesize: Tuple[float, float] = (595.27, 841.89)):
        self.target = filename_or_buffer
        self.pagesize = pagesize
        self.width, self.height = pagesize
        self._states: List[dict] = []
        self._font_name = "Helvetica"
        self._font_size = 10.0
        self._fill_color = colors.black
        self._alpha = 1.0
        self._rotation = 0.0
        self.operations: List[str] = []

    def saveState(self) -> None:
        self._states.append({
            "font_name": self._font_name,
            "font_size": self._font_size,
            "fill_color": self._fill_color,
            "alpha": self._alpha,
            "rotation": self._rotation,
        })
        self.operations.append("q")

    def restoreState(self) -> None:
        if self._states:
            s = self._states.pop()
            self._font_name = s["font_name"]
            self._font_size = s["font_size"]
            self._fill_color = s["fill_color"]
            self._alpha = s["alpha"]
            self._rotation = s["rotation"]
        self.operations.append("Q")

    def setFont(self, fontname: str, fontsize: float) -> None:
        self._font_name = fontname
        self._font_size = fontsize

    def setFillColor(self, color: Any, alpha: float = 1.0) -> None:
        self._fill_color = color
        self._alpha = alpha

    def rotate(self, theta: float) -> None:
        self._rotation += theta
        rad = math.radians(theta)
        c, s = math.cos(rad), math.sin(rad)
        self.operations.append(f"{c:.4f} {s:.4f} {-s:.4f} {c:.4f} 0 0 cm")

    def drawString(self, x: float, y: float, text: str) -> None:
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        r, g, b = getattr(self._fill_color, "red", 0.0), getattr(self._fill_color, "green", 0.0), getattr(self._fill_color, "blue", 0.0)
        self.operations.append(f"{r:.3f} {g:.3f} {b:.3f} rg")
        self.operations.append(f"BT /F1 {self._font_size:.1f} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self.operations.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def drawImage(self, image: Any, x: float, y: float, width: Optional[float] = None, height: Optional[float] = None) -> None:
        w = width or 100
        h = height or 100
        self.operations.append(f"% Image {image} at ({x}, {y}, {w}, {h})")
