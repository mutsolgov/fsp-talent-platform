"""
FSP IT-Talent Platform — Global Base Pydantic v2 Schemas.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §1.4.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class UserRole(StrEnum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"
    ADMIN = "admin"
    PUBLIC = "public"


class BaseSchema(BaseModel):
    """Базовый класс для всех Pydantic-схем платформы."""
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


class ErrorDetail(BaseSchema):
    """Детализация ошибки валидации конкретного поля запроса."""
    loc: List[Union[str, int]] = Field(..., description="Путь к полю в теле/параметрах запроса")
    msg: str = Field(..., description="Текстовое описание нарушения")
    type: str = Field(..., description="Машиночитаемый идентификатор типа ошибки")


class ErrorResponse(BaseSchema):
    """Единый формат возврата ошибок по спецификации RFC 7807."""
    error_code: str = Field(..., description="Канонический машиночитаемый код ошибки")
    message: str = Field(..., description="Понятное человеку описание ошибки на русском языке")
    detail: Optional[str] = Field(default=None, description="Совместимость со стандартным форматом FastAPI")
    status_code: int = Field(..., description="HTTP статус-код ответа")
    details: Optional[List[ErrorDetail]] = Field(default=None, description="Список детальных ошибок валидации полей")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Метка времени фиксации ошибки в UTC")
    path: Optional[str] = Field(default=None, description="Относительный URL запроса")


class PaginationMeta(BaseSchema):
    """Метаданные пагинации для коллекций сущностей."""
    total: int = Field(ge=0, description="Общее число элементов под фильтром")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, le=100, description="Количество элементов на странице")
    total_pages: int = Field(ge=0, description="Всего страниц")


class StatusMessageResponse(BaseSchema):
    """Универсальный успешный ответ с информационным сообщением."""
    status: Literal["ok"] = "ok"
    message: str = Field(..., description="Информационное сообщение о результате операции")


class AuditLogEntry(BaseSchema):
    """Схема записи неизменяемого журнала аудита безопасности."""
    id: int
    user_id: Optional[int]
    action: str
    target_entity: str
    target_id: Optional[int]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata_json: Dict[str, Any]
    created_at: datetime
