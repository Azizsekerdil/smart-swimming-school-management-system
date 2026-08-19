"""Yapılandırılmış loglama / Structured logging.

Kategoriler ayrı dosyalara yazılır: application, database, ai, security,
developer-agent, audit. Hassas veriler (API anahtarı, parola, token) otomatik
olarak maskelenir.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

LOG_CATEGORIES = (
    "application",
    "database",
    "ai",
    "security",
    "developer-agent",
    "audit",
)

# Hassas veri desenleri - log'a asla düz metin sızmamalı
_SENSITIVE_PATTERNS = [
    (re.compile(r"(nvapi-)[A-Za-z0-9_\-]{10,}", re.I), r"\1***REDACTED***"),
    (re.compile(r"(sk-)[A-Za-z0-9_\-]{16,}", re.I), r"\1***REDACTED***"),
    (re.compile(r"(gh[pousr]_)[A-Za-z0-9]{20,}", re.I), r"\1***REDACTED***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\._\-]{16,}", re.I), r"\1***REDACTED***"),
    (
        re.compile(
            r'("?(?:api[_-]?key|apikey|secret|password|passwd|token|authorization)"?\s*[:=]\s*"?)([^"\s,}]{4,})',
            re.I,
        ),
        r"\1***REDACTED***",
    ),
]


def redact(text: str) -> str:
    """Metindeki sırları maskeler."""
    if not text:
        return text
    for pattern, repl in _SENSITIVE_PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactingFilter(logging.Filter):
    """Her log kaydını maskeleme filtresinden geçirir."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        k: redact(v) if isinstance(v, str) else v
                        for k, v in record.args.items()
                    }
                elif isinstance(record.args, tuple):
                    record.args = tuple(
                        redact(a) if isinstance(a, str) else a for a in record.args
                    )
        except Exception:  # noqa: BLE001 - loglama asla uygulamayı düşürmemeli
            pass
        return True


class JsonFormatter(logging.Formatter):
    """JSON satır formatı (log toplama sistemleri için)."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
        }
        for key in ("user_id", "request_id", "category", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


_TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def _build_handler(category: str) -> logging.Handler:
    log_file = settings.log_path / f"{category}.log"
    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(
        JsonFormatter() if settings.log_json else logging.Formatter(_TEXT_FORMAT)
    )
    handler.addFilter(RedactingFilter())
    return handler


_configured = False


def setup_logging() -> None:
    """Uygulama başlangıcında bir kez çağrılır."""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(settings.log_level)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_TEXT_FORMAT))
    console.addFilter(RedactingFilter())
    root.handlers = [console, _build_handler("application")]

    # Kategori bazlı ayrı dosyalar
    for category in LOG_CATEGORIES:
        if category == "application":
            continue
        cat_logger = logging.getLogger(f"sws.{category}")
        cat_logger.handlers = [_build_handler(category)]
        cat_logger.propagate = False
        cat_logger.setLevel(logging.INFO)

    # Gürültülü kütüphaneleri kıs
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )
    _configured = True


def get_logger(category: str = "application") -> logging.Logger:
    """Kategori logger'ı döndürür."""
    if category == "application":
        return logging.getLogger("sws.app")
    return logging.getLogger(f"sws.{category}")


# Kısayollar
app_log = lambda: get_logger("application")  # noqa: E731
ai_log = lambda: get_logger("ai")  # noqa: E731
security_log = lambda: get_logger("security")  # noqa: E731
audit_log = lambda: get_logger("audit")  # noqa: E731
agent_log = lambda: get_logger("developer-agent")  # noqa: E731
db_log = lambda: get_logger("database")  # noqa: E731
