"""
fastapi.exceptions — Compliant exceptions for lightweight FastAPI runner.
"""
from __future__ import annotations
from typing import Any, List, Optional

from fastapi import HTTPException


class RequestValidationError(Exception):
    """RFC 7807 compliant validation error."""

    def __init__(self, errors: Optional[List[Any]] = None):
        self._errors = errors or []
        super().__init__(str(self._errors))

    def errors(self) -> List[Any]:
        return self._errors


class WebSocketRequestValidationError(Exception):
    """RFC 7807 compliant websocket validation error."""

    def __init__(self, errors: Optional[List[Any]] = None):
        self._errors = errors or []
        super().__init__(str(self._errors))

    def errors(self) -> List[Any]:
        return self._errors


__all__ = [
    "HTTPException",
    "RequestValidationError",
    "WebSocketRequestValidationError",
]
