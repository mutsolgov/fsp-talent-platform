"""ReportLab platypus module."""
from __future__ import annotations
import io
import re
from typing import Any, Callable, List, Optional, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen.canvas import Canvas


class Flowable:
    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        return availWidth, 0.0

    def draw(self, canvas: Canvas, x: float, y: float) -> None:
        pass


class Spacer(Flowable):
    def __init__(self, width: float, height: float):
        self.width = width
        self.height = height

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        return self.width, self.height


class Paragraph(Flowable):
    def __init__(self, text: str, style: ParagraphStyle):
        self.text = text
        self.style = style

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        lines = self.text.replace("<br/>", "\n").replace("<br>", "\n").split("\n")
        line_count = max(1, len(lines))
        return availWidth, line_count * self.style.leading

    def draw(self, canvas: Canvas, x: float, y: float) -> None:
        lines = self.text.replace("<br/>", "\n").replace("<br>", "\n").split("\n")
        curr_y = y
        canvas.setFont(self.style.fontName, self.style.fontSize)
        canvas.setFillColor(self.style.textColor)

        for line in lines:
            clean = re.sub(r"<[^>]+>", "", line)
            canvas.drawString(x, curr_y, clean)
            curr_y -= self.style.leading


class Image(Flowable):
    def __init__(self, filename: str, width: Optional[float] = None, height: Optional[float] = None):
        self.filename = filename
        self.width = width or 100
        self.height = height or 40

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        return self.width, self.height

    def draw(self, canvas: Canvas, x: float, y: float) -> None:
        canvas.drawImage(self.filename, x, y, self.width, self.height)


class Table(Flowable):
    def __init__(self, data: List[List[Any]], colWidths: Optional[List[float]] = None, rowHeights: Optional[List[float]] = None, style: Any = None):
        self.data = data
        self.colWidths = colWidths or [100.0] * (len(data[0]) if data else 1)
        self.rowHeights = rowHeights or [20.0] * len(data)
        self.style = style

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        h = sum(self.rowHeights)
        w = sum(self.colWidths)
        return w, h

    def draw(self, canvas: Canvas, x: float, y: float) -> None:
        curr_y = y
        for row, rh in zip(self.data, self.rowHeights):
            curr_x = x
            for cell, cw in zip(row, self.colWidths):
                if isinstance(cell, Flowable):
                    cell.draw(canvas, curr_x, curr_y)
                else:
                    canvas.drawString(curr_x, curr_y, str(cell))
                curr_x += cw
            curr_y -= rh


class TableStyle:
    def __init__(self, commands: Optional[List[Any]] = None):
        self.commands = commands or []


class SimpleDocTemplate:
    def __init__(
        self,
        filename_or_buffer: Any,
        pagesize: Tuple[float, float] = A4,
        leftMargin: float = 36.0,
        rightMargin: float = 36.0,
        topMargin: float = 36.0,
        bottomMargin: float = 36.0,
    ):
        self.target = filename_or_buffer
        self.pagesize = pagesize
        self.leftMargin = leftMargin
        self.rightMargin = rightMargin
        self.topMargin = topMargin
        self.bottomMargin = bottomMargin
        self.width = pagesize[0] - leftMargin - rightMargin
        self.height = pagesize[1] - topMargin - bottomMargin

    def build(
        self,
        story: List[Flowable],
        onFirstPage: Optional[Callable[[Canvas, Any], None]] = None,
        onLaterPages: Optional[Callable[[Canvas, Any], None]] = None,
    ) -> None:
        canvas = Canvas(self.target, pagesize=self.pagesize)

        # Flow elements down the page
        curr_x = self.leftMargin
        curr_y = self.pagesize[1] - self.topMargin

        for flowable in story:
            w, h = flowable.wrap(self.width, curr_y - self.bottomMargin)
            if isinstance(flowable, Spacer):
                curr_y -= h
            else:
                flowable.draw(canvas, curr_x, curr_y)
                curr_y -= (h + getattr(flowable.style, "spaceAfter", 0.0) if hasattr(flowable, "style") else h)

        if onFirstPage:
            onFirstPage(canvas, self)

        # Generate standard PDF 1.4 stream
        stream_ops = "\n".join(canvas.operations)
        stream_bytes = stream_ops.encode("utf-8")
        stream_len = len(stream_bytes)

        page_obj = f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.pagesize[0]:.2f} {self.pagesize[1]:.2f}] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n".encode("ascii")
        contents_hdr = f"4 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("ascii")

        pdf_body = (
            b"%PDF-1.4\n"
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            + page_obj
            + contents_hdr
            + stream_bytes
            + b"\nendstream\nendobj\n"
            b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000010 00000 n \n"
            b"0000000060 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000260 00000 n \n"
            b"0000000350 00000 n \n"
            b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
            b"startxref\n420\n"
            b"%%EOF\n"
        )

        if hasattr(self.target, "write"):
            self.target.write(pdf_body)
        elif isinstance(self.target, str):
            with open(self.target, "wb") as f:
                f.write(pdf_body)
