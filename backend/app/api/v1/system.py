"""Sistem uçları: sağlık, hakkında, ayarlar, denetim, bildirimler."""

from __future__ import annotations

import platform
import sys
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.deps import (
    client_ip,
    db_session,
    get_current_user,
    get_language,
    pagination,
    require_permissions,
)
from app.core.config import settings
from app.core.i18n import MESSAGES, missing_translations, t
from app.core.permissions import Perm
from app.db.session import engine, is_sqlite
from app.models.system import AppSetting, AuditLog, Notification
from app.models.user import User
from app.schemas.common import (
    HealthComponent,
    HealthReport,
    Message,
    Page,
    PaginationParams,
)
from app.schemas.system import (
    AboutInfo,
    AuditLogOut,
    NotificationCounts,
    NotificationCreate,
    NotificationOut,
    SettingOut,
    SettingUpdate,
)
from app.services import audit
from app.services.crud import get_or_404, paginate

router = APIRouter(tags=["Sistem"])


# ---------------------------------------------------------------------------
# Sağlık kontrolü
# ---------------------------------------------------------------------------
@router.get("/health", response_model=HealthReport, summary="Sistem sağlık kontrolü")
def health_check(db: Session = Depends(db_session)) -> HealthReport:
    """Backend, veritabanı ve AI sağlayıcılarının durumunu döndürür.

    AI çalışmasa bile ana sistem `ok` raporlar; AI ayrı bir bileşendir.
    """
    components: list[HealthComponent] = [
        HealthComponent(name="backend", status="ok", detail=f"v{settings.app_version}")
    ]

    # Veritabanı
    started = datetime.now(timezone.utc)
    try:
        db.execute(text("SELECT 1"))
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        components.append(
            HealthComponent(
                name="database",
                status="ok",
                detail="SQLite" if is_sqlite() else engine.dialect.name,
                latency_ms=latency,
            )
        )
    except Exception as exc:  # noqa: BLE001
        components.append(
            HealthComponent(name="database", status="down", detail=type(exc).__name__)
        )

    # AI sağlayıcıları (hata sistemin sağlığını düşürmez)
    try:
        from app.services.ai.registry import provider_health_snapshot

        for entry in provider_health_snapshot():
            components.append(
                HealthComponent(
                    name=f"ai:{entry['provider']}",
                    status=entry["status"],
                    detail=entry.get("detail"),
                    latency_ms=entry.get("latency_ms"),
                )
            )
    except Exception as exc:  # noqa: BLE001
        components.append(
            HealthComponent(name="ai", status="down", detail=f"{type(exc).__name__}")
        )

    # Frontend derlemesi
    dist = settings.project_root / "frontend" / "dist" / "index.html"
    components.append(
        HealthComponent(
            name="frontend",
            status="ok" if dist.exists() else "degraded",
            detail="derlenmiş" if dist.exists() else "geliştirme sunucusu gerekli",
        )
    )

    core_ok = all(
        c.status == "ok" for c in components if c.name in ("backend", "database")
    )
    return HealthReport(
        status="ok" if core_ok else "degraded",
        checked_at=datetime.now(timezone.utc),
        app_version=settings.app_version,
        components=components,
    )


@router.get("/about", response_model=AboutInfo, summary="Program bilgisi")
def about(
    db: Session = Depends(db_session),
    _: User = Depends(get_current_user),
) -> AboutInfo:
    """Sürüm, şema revizyonu ve derleme bilgisi.

    Kimlik doğrulaması ister: bu alanlar bir saldırgana kurulu sürümü ve
    şema durumunu bildirir (parmak izi çıkarma).
    """
    revision = None
    try:
        revision = db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    except Exception:  # noqa: BLE001
        pass

    git_commit = None
    git_head = settings.project_root / ".git" / "HEAD"
    try:
        if git_head.exists():
            head = git_head.read_text(encoding="utf-8").strip()
            if head.startswith("ref:"):
                ref_path = (
                    settings.project_root / ".git" / head.split(" ", 1)[1].strip()
                )
                if ref_path.exists():
                    git_commit = ref_path.read_text(encoding="utf-8").strip()[:12]
            else:
                git_commit = head[:12]
    except Exception:  # noqa: BLE001
        pass

    return AboutInfo(
        app_name=settings.app_name,
        version=settings.app_version,
        build=f"{settings.app_env}-{settings.app_version}",
        git_commit=git_commit,
        database_revision=revision,
        database_engine="SQLite" if is_sqlite() else engine.dialect.name,
        python_version=sys.version.split()[0],
        platform=f"{platform.system()} {platform.release()}",
        last_updated=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
@router.get("/settings", response_model=list[SettingOut], summary="Ayarları listele")
def list_settings(
    category: str | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.SETTINGS_READ)),
) -> list[SettingOut]:
    stmt = select(AppSetting).where(AppSetting.is_secret.is_(False))
    if category:
        stmt = stmt.where(AppSetting.category == category)
    return [
        SettingOut.model_validate(s)
        for s in db.scalars(stmt.order_by(AppSetting.category, AppSetting.key)).all()
    ]


@router.get("/settings/{key}", response_model=SettingOut, summary="Tek ayar")
def get_setting(
    key: str,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.SETTINGS_READ)),
) -> SettingOut:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == key))
    if setting is None or setting.is_secret:
        from app.core.exceptions import NotFoundError

        raise NotFoundError()
    return SettingOut.model_validate(setting)


@router.put("/settings", response_model=SettingOut, summary="Ayar güncelle")
def update_setting(
    payload: SettingUpdate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.SETTINGS_WRITE)),
) -> SettingOut:
    setting = db.scalar(select(AppSetting).where(AppSetting.key == payload.key))
    old_value = setting.value if setting else None
    if setting is None:
        setting = AppSetting(
            key=payload.key, category=payload.category, value=payload.value
        )
        db.add(setting)
    else:
        setting.value = payload.value
        setting.category = payload.category or setting.category
    setting.updated_by_user_id = current.id

    audit.record(
        db,
        action="update",
        entity_type="app_setting",
        entity_id=payload.key,
        user=current,
        summary=f"Ayar güncellendi: {payload.key}",
        changes={"value": {"from": old_value, "to": payload.value}},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(setting)
    return SettingOut.model_validate(setting)


@router.get("/i18n/validate", summary="Çeviri bütünlük denetimi")
def validate_translations(
    _: User = Depends(require_permissions(Perm.SETTINGS_READ)),
) -> dict:
    """Backend mesajlarında eksik çeviri anahtarlarını raporlar."""
    missing = missing_translations()
    return {
        "total_keys": len(MESSAGES),
        "missing": missing,
        "is_complete": all(not v for v in missing.values()),
    }


# ---------------------------------------------------------------------------
# Denetim kaydı
# ---------------------------------------------------------------------------
@router.get("/audit", response_model=Page[AuditLogOut], summary="Denetim kayıtları")
def list_audit(
    user_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    days: int = 30,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AUDIT_READ)),
) -> Page[AuditLogOut]:
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    stmt = select(AuditLog).where(AuditLog.occurred_at >= since)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    stmt = stmt.order_by(AuditLog.occurred_at.desc())
    rows, total = paginate(db, stmt, params)
    return Page[AuditLogOut](
        items=[AuditLogOut.model_validate(r) for r in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


# ---------------------------------------------------------------------------
# Bildirimler
# ---------------------------------------------------------------------------
@router.get(
    "/notifications", response_model=Page[NotificationOut], summary="Bildirimlerim"
)
def list_notifications(
    unread_only: bool = False,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Page[NotificationOut]:
    stmt = select(Notification).where(
        (Notification.user_id == user.id) | (Notification.user_id.is_(None))
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    stmt = stmt.order_by(Notification.created_at.desc())
    rows, total = paginate(db, stmt, params)

    items = []
    for n in rows:
        item = NotificationOut.model_validate(
            {
                "id": n.id,
                "notification_type": n.notification_type,
                "severity": n.severity,
                "title": n.title(lang),
                "body": n.body(lang),
                "link": n.link,
                "entity_type": n.entity_type,
                "entity_id": n.entity_id,
                "is_read": n.is_read,
                "created_at": n.created_at,
            }
        )
        items.append(item)
    return Page[NotificationOut](
        items=items, total=total, page=params.page, page_size=params.page_size
    )


@router.get(
    "/notifications/counts",
    response_model=NotificationCounts,
    summary="Bildirim sayıları",
)
def notification_counts(
    db: Session = Depends(db_session), user: User = Depends(get_current_user)
) -> NotificationCounts:
    base = (Notification.user_id == user.id) | (Notification.user_id.is_(None))
    total = db.scalar(select(func.count(Notification.id)).where(base)) or 0
    unread = (
        db.scalar(
            select(func.count(Notification.id)).where(
                base, Notification.is_read.is_(False)
            )
        )
        or 0
    )
    by_severity = dict(
        db.execute(
            select(Notification.severity, func.count(Notification.id))
            .where(base, Notification.is_read.is_(False))
            .group_by(Notification.severity)
        ).all()
    )
    return NotificationCounts(total=total, unread=unread, by_severity=by_severity)


@router.post(
    "/notifications/{notification_id}/read",
    response_model=Message,
    summary="Okundu işaretle",
)
def mark_read(
    notification_id: int,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    notification = get_or_404(db, Notification, notification_id)
    if notification.user_id in (user.id, None):
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.post(
    "/notifications/read-all", response_model=Message, summary="Tümünü okundu işaretle"
)
def mark_all_read(
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    now = datetime.now(timezone.utc)
    for n in db.scalars(
        select(Notification).where(
            ((Notification.user_id == user.id) | (Notification.user_id.is_(None))),
            Notification.is_read.is_(False),
        )
    ).all():
        n.is_read = True
        n.read_at = now
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.post(
    "/notifications", response_model=Message, status_code=201, summary="Bildirim gönder"
)
def send_notification(
    payload: NotificationCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.NOTIFICATION_SEND)),
    lang: str = Depends(get_language),
) -> Message:
    from app.services.notifications import broadcast

    count = broadcast(
        db,
        notification_type=payload.notification_type,
        severity=payload.severity,
        title_tr=payload.title_tr,
        title_en=payload.title_en,
        body_tr=payload.body_tr,
        body_en=payload.body_en,
        link=payload.link,
        user_ids=payload.user_ids,
        role_codes=payload.role_codes,
    )
    audit.record(
        db,
        action="notify",
        entity_type="notification",
        user=current,
        summary=f"{count} kullanıcıya bildirim gönderildi: {payload.title_tr}",
    )
    db.commit()
    return Message(
        code="common.created",
        message=t("common.created", lang),
        data={"recipients": count},
    )


@router.post(
    "/notifications/generate",
    response_model=Message,
    summary="Otomatik bildirimleri üret",
)
def generate_notifications(
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.NOTIFICATION_SEND)),
    lang: str = Depends(get_language),
) -> Message:
    """Üyelik bitişi, geciken ödeme, performans düşüşü gibi uyarıları tarar."""
    from app.services.notifications import generate_system_notifications

    created = generate_system_notifications(db)
    return Message(
        code="common.created",
        message=t("common.created", lang),
        data={"created": created},
    )
