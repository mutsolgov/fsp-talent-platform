"""
FSP IT-Talent Platform — FastAPI Main Application Entry Point.
"""
from __future__ import annotations

import sys
import os

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Union
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.v1.admin import router as admin_router
from app.api.v1.applications import router as applications_router
from app.api.v1.assessment import router as assessment_router
from app.api.v1.ats_integration import router as ats_integration_router
from app.api.v1.auth import router as auth_router
from app.api.v1.candidate_bank import router as candidate_bank_router
from app.api.v1.candidate_profile import router as candidate_profile_router
from app.api.v1.demo import router as demo_router
from app.api.v1.employer_needs import router as employer_needs_router
from app.api.v1.employer_profiles import router as employer_profiles_router
from app.api.v1.fsp_integration import router as fsp_integration_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.micro_challenges import router as micro_challenges_router
from app.api.v1.resume_pdf import router as resume_pdf_router
from app.api.v1.vacancies import router as vacancies_router
from app.api.v1.validation_benchmark import router as validation_benchmark_router
from app.core.config import settings
from app.database import ensure_keycloak_schema
from app.schemas.base import ErrorDetail, ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for application startup and shutdown."""
    await ensure_keycloak_schema()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Цифровая платформа-агрегатор ИТ-вакансий с верифицированным профилем достижений участника Федерации спортивного программирования (ФСП)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """RFC 7807 compliant Problem Details error response."""
    error_resp = ErrorResponse(
        error_code=f"ERR_HTTP_{exc.status_code}",
        message=str(exc.detail),
        detail=str(exc.detail),
        status_code=exc.status_code,
        path=str(request.url) if hasattr(request, "url") else None,
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(
        content=error_resp.model_dump(mode="json"),
        status_code=exc.status_code,
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """RFC 7807 compliant schema validation error handler."""
    details = [
        ErrorDetail(
            loc=list(err.get("loc", [])),
            msg=str(err.get("msg", "")),
            type=str(err.get("type", "value_error")),
        )
        for err in exc.errors()
    ]
    error_resp = ErrorResponse(
        error_code="ERR_VALIDATION_ERROR",
        message="Ошибка валидации параметров запроса",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
        path=str(request.url) if hasattr(request, "url") else None,
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(
        content=error_resp.model_dump(mode="json"),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


# Mount API v1 Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(fsp_integration_router, prefix=settings.API_V1_STR)
app.include_router(candidate_profile_router, prefix=settings.API_V1_STR)
app.include_router(resume_pdf_router, prefix=settings.API_V1_STR)
app.include_router(assessment_router, prefix=settings.API_V1_STR)
app.include_router(micro_challenges_router, prefix=settings.API_V1_STR)
app.include_router(employer_needs_router, prefix=settings.API_V1_STR)
app.include_router(employer_profiles_router, prefix=settings.API_V1_STR)
app.include_router(candidate_bank_router, prefix=settings.API_V1_STR)
app.include_router(invitations_router, prefix=settings.API_V1_STR)
app.include_router(vacancies_router, prefix=settings.API_V1_STR)
app.include_router(applications_router, prefix=settings.API_V1_STR)
app.include_router(ats_integration_router, prefix=settings.API_V1_STR)
app.include_router(validation_benchmark_router, prefix=settings.API_V1_STR)
app.include_router(demo_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)


@app.get("/api/health", tags=["system"], summary="Проверка работоспособности сервиса")
async def health_check():
    return {
        "status": "ok",
        "service": "fsp-talent-backend",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
