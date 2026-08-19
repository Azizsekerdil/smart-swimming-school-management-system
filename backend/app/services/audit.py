"""Denetim kaydı servisi / Audit logging service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.system import AuditLog, SystemEvent
from app.models.user import User

logger = get_logger("audit")

# Denetim kaydına asla düz metin yazılmayacak alanlar
_SENSITIVE_FIELDS = {
    "password",
    "hashed_password",
    "new_password",
    "current_password",
    "api_key",
    "nvidia_api_key",
    "local_ai_api_key",
    "secret_key",
    "token",
    "refresh_token",
    "access_token",
}


def _sanitize(data: dict[str, Any] | None) -> dict[str, Any]:
    """Hassas alanları maskeler."""
    if not data:
        return {}
    clean: dict[str, Any] = {}
    for key, value in data.items():
        if (
            key.lower() in _SENSITIVE_FIELDS
            or "password" in key.lower()
            or "secret" in key.lower()
        ):
            clean[key] = "***"
        elif isinstance(value, dict):
            clean[key] = _sanitize(value)
        elif isinstance(value, str) and len(value) > 500:
            clean[key] = value[:500] + "…"
        else:
            clean[key] = value
    return clean


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    user: User | None = None,
    summary: str | None = None,
    changes: dict[str, Any] | None = None,
    ip_address: str | None = None,
    commit: bool = False,
) -> AuditLog:
    """Denetim kaydı ekler.

    Not: `commit=False` varsayılandır; çağıran işlem kendi commit'ini yapar,
    böylece denetim kaydı iş verisiyle aynı işlemde atomik olur.
    """
    entry = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
        changes=_sanitize(changes),
        ip_address=ip_address,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    if commit:
        db.commit()
    logger.info(
        "%s %s#%s by %s | %s",
        action,
        entity_type,
        entity_id,
        user.email if user else "system",
        summary or "",
    )
    return entry


def diff_changes(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """İki sözlük arasındaki farkı {alan: {"from": x, "to": y}} biçiminde üretir."""
    changes: dict[str, Any] = {}
    for key, new_value in after.items():
        old_value = before.get(key)
        if old_value != new_value:
            changes[key] = {"from": old_value, "to": new_value}
    return _sanitize(changes)


def model_snapshot(obj: Any, fields: list[str]) -> dict[str, Any]:
    """Bir ORM nesnesinden seçili alanların anlık görüntüsünü alır."""
    snapshot: dict[str, Any] = {}
    for field in fields:
        value = getattr(obj, field, None)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif value is not None and not isinstance(
            value, (str, int, float, bool, list, dict)
        ):
            value = str(value)
        snapshot[field] = value
    return snapshot


def system_event(
    db: Session,
    *,
    event_type: str,
    message: str,
    severity: str = "info",
    details: dict[str, Any] | None = None,
    commit: bool = True,
) -> SystemEvent:
    """Sistem seviyesi olay kaydı (başlangıç, migration, yedek vb.)."""
    event = SystemEvent(
        event_type=event_type,
        severity=severity,
        message=message[:600],
        details=_sanitize(details),
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    if commit:
        db.commit()
    return event
