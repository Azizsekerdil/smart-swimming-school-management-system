"""Uygulama istisnaları ve güvenli hata yanıtları / Application exceptions.

Kural: İç hata detayları (stack trace, SQL, dosya yolu) istemciye ASLA
sızdırılmaz. İstemciye yerelleştirilmiş, anlaşılır bir mesaj ve bir hata kodu
döner; ayrıntı sunucu tarafında loglanır.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.i18n import normalize_language, t
from app.core.logging_config import get_logger

logger = get_logger("application")

# starlette 1.x bu sabiti HTTP_422_UNPROCESSABLE_CONTENT olarak yeniden adlandırdı;
# eski ad hâlâ çalışıyor ancak kullanımdan kaldırma uyarısı üretiyor.
# Not: `getattr(..., default)` varsayılanı hemen değerlendirdiği için eski ada
# yine dokunur ve uyarıyı tetikler; bu yüzden koşullu erişim kullanılır.
# (HTTP kodu her iki sürümde de 422'dir.)
HTTP_422 = (
    status.HTTP_422_UNPROCESSABLE_CONTENT
    if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT")
    else status.HTTP_422_UNPROCESSABLE_ENTITY
)


class AppError(Exception):
    """Tüm uygulama hatalarının atası."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    message_key: str = "common.internal_error"

    def __init__(
        self,
        message_key: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message_key = message_key or self.message_key
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message_key)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    message_key = "common.not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    message_key = "common.already_exists"


class ValidationError(AppError):
    status_code = HTTP_422
    message_key = "common.validation_error"


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    message_key = "auth.not_authenticated"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    message_key = "auth.forbidden"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    message_key = "auth.rate_limited"


class PasswordChangeRequiredError(AppError):
    """İlk kurulum parolası değiştirilmeden korumalı uca erişilemez."""

    status_code = status.HTTP_403_FORBIDDEN
    message_key = "auth.password_change_required"


class BootstrapRemoteLoginError(AppError):
    """Kurulum parolası ağ üzerinden kullanılamaz (yalnızca yerel cihaz)."""

    status_code = status.HTTP_403_FORBIDDEN
    message_key = "auth.bootstrap_local_only"


class SchedulingConflictError(ConflictError):
    """Ders planlama çakışması - ayrıntılı çakışma listesi taşır."""

    message_key = "lesson.conflict_lane"


class AIProviderError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message_key = "ai.provider_unavailable"


class SecurityPolicyError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    message_key = "ai.command_blocked"


def _lang_from_request(request: Request) -> str:
    q = request.query_params.get("lang")
    if q:
        return normalize_language(q)
    return normalize_language(request.headers.get("accept-language"))


def _error_payload(
    code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        payload["error"]["details"] = jsonable_encoder(details)
    return payload


def register_exception_handlers(app) -> None:  # noqa: ANN001
    """FastAPI uygulamasına güvenli hata işleyicilerini bağlar."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):  # noqa: ANN202
        lang = _lang_from_request(request)
        if exc.status_code >= 500:
            logger.error("AppError: %s | details=%s", exc.message_key, exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                exc.message_key, t(exc.message_key, lang), exc.details
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ):  # noqa: ANN202
        lang = _lang_from_request(request)
        fields = [
            {
                "field": ".".join(str(p) for p in err.get("loc", [])[1:]),
                "type": err.get("type"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=HTTP_422,
            content=_error_payload(
                "common.validation_error",
                t("common.validation_error", lang),
                {"fields": fields},
            ),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(request: Request, exc: IntegrityError):  # noqa: ANN202
        lang = _lang_from_request(request)
        logger.warning("IntegrityError: %s", str(exc.orig)[:400])
        key = (
            "common.already_exists"
            if "UNIQUE" in str(exc.orig).upper()
            else "common.in_use"
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_payload(key, t(key, lang)),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(request: Request, exc: SQLAlchemyError):  # noqa: ANN202
        lang = _lang_from_request(request)
        # Ayrıntı yalnızca sunucu log'unda
        get_logger("database").exception("Veritabanı hatası: %s", type(exc).__name__)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "common.internal_error", t("common.internal_error", lang)
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):  # noqa: ANN202
        lang = _lang_from_request(request)
        logger.exception("İşlenmemiş hata: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                "common.internal_error", t("common.internal_error", lang)
            ),
        )
