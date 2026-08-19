"""Bildirim motoru / Notification engine.

Sistem olaylarını (üyelik bitişi, geciken ödeme, performans düşüşü, yaklaşan
yarışma vb.) tarar ve ilgili rollere bildirim üretir. Tekrarlayan bildirim
oluşmaması için aynı gün + aynı varlık için yinelenen kayıt eklenmez.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.enums import (
    LessonStatus,
    MembershipStatus,
    NotificationSeverity,
    NotificationType,
)
from app.models.competition import Competition
from app.models.facility import PoolMaintenance
from app.models.finance import Invoice
from app.models.lesson import Lesson
from app.models.membership import Membership
from app.models.system import Notification
from app.models.user import Role, User

logger = get_logger("application")


def _recipients(
    db: Session, user_ids: list[int] | None = None, role_codes: list[str] | None = None
) -> list[int]:
    """Alıcı kullanıcı kimliklerini çözer. Hiçbiri verilmezse boş liste (global bildirim)."""
    ids: set[int] = set(user_ids or [])
    if role_codes:
        rows = db.scalars(
            select(User.id)
            .join(User.roles)
            .where(Role.code.in_(role_codes), User.is_active.is_(True))
        ).all()
        ids.update(rows)
    return sorted(ids)


def _already_exists(
    db: Session, notification_type: str, entity_type: str | None, entity_id: str | None
) -> bool:
    """Aynı gün aynı varlık için bildirim üretilmiş mi?"""
    if not entity_id:
        return False
    today_start = datetime.combine(date.today(), time.min)
    return bool(
        db.scalar(
            select(func.count(Notification.id)).where(
                Notification.notification_type == notification_type,
                Notification.entity_type == entity_type,
                Notification.entity_id == str(entity_id),
                Notification.created_at >= today_start,
            )
        )
    )


def create(
    db: Session,
    *,
    notification_type: str,
    title_tr: str,
    title_en: str | None = None,
    body_tr: str | None = None,
    body_en: str | None = None,
    severity: str = NotificationSeverity.INFO,
    link: str | None = None,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
) -> Notification:
    """Tek bir bildirim oluşturur (commit çağıranın sorumluluğunda)."""
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        severity=severity,
        title_tr=title_tr,
        title_en=title_en or title_tr,
        body_tr=body_tr,
        body_en=body_en or body_tr,
        link=link,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(notification)
    return notification


def broadcast(
    db: Session,
    *,
    notification_type: str,
    title_tr: str,
    title_en: str | None = None,
    body_tr: str | None = None,
    body_en: str | None = None,
    severity: str = NotificationSeverity.INFO,
    link: str | None = None,
    user_ids: list[int] | None = None,
    role_codes: list[str] | None = None,
    entity_type: str | None = None,
    entity_id: str | int | None = None,
) -> int:
    """Birden çok kullanıcıya bildirim gönderir. Alıcı yoksa global bildirim üretir."""
    targets = _recipients(db, user_ids, role_codes)
    if not targets:
        create(
            db,
            notification_type=notification_type,
            title_tr=title_tr,
            title_en=title_en,
            body_tr=body_tr,
            body_en=body_en,
            severity=severity,
            link=link,
            user_id=None,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return 1

    for user_id in targets:
        create(
            db,
            notification_type=notification_type,
            title_tr=title_tr,
            title_en=title_en,
            body_tr=body_tr,
            body_en=body_en,
            severity=severity,
            link=link,
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    return len(targets)


# ---------------------------------------------------------------------------
# Otomatik sistem bildirimleri
# ---------------------------------------------------------------------------
MANAGEMENT_ROLES = ["system_admin", "school_director", "operations_manager"]
FINANCE_ROLES = ["system_admin", "school_director", "finance", "reception"]
COACH_ROLES = ["system_admin", "head_coach", "school_director"]


def generate_system_notifications(db: Session, expiry_days: int = 14) -> dict[str, int]:
    """Tüm otomatik uyarıları tarar ve üretir. Idempotent (gün bazında)."""
    created: dict[str, int] = {}
    today = date.today()

    # 1) Süresi dolmak üzere olan üyelikler
    count = 0
    limit_date = today + timedelta(days=expiry_days)
    memberships = db.scalars(
        select(Membership).where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date.is_not(None),
            Membership.end_date >= today,
            Membership.end_date <= limit_date,
        )
    ).all()
    for m in memberships:
        if _already_exists(
            db, NotificationType.MEMBERSHIP_EXPIRING, "membership", m.id
        ):
            continue
        name = m.student.full_name if m.student else f"#{m.student_id}"
        broadcast(
            db,
            notification_type=NotificationType.MEMBERSHIP_EXPIRING,
            severity=NotificationSeverity.WARNING,
            title_tr=f"Üyelik bitiyor: {name}",
            title_en=f"Membership expiring: {name}",
            body_tr=f"{m.end_date:%d.%m.%Y} tarihinde sona eriyor ({m.days_remaining} gün kaldı).",
            body_en=f"Expires on {m.end_date:%Y-%m-%d} ({m.days_remaining} days left).",
            link=f"/memberships/{m.id}",
            role_codes=FINANCE_ROLES,
            entity_type="membership",
            entity_id=m.id,
        )
        count += 1
    created["membership_expiring"] = count

    # 2) Geciken ödemeler
    count = 0
    overdue = db.scalars(
        select(Invoice).where(
            Invoice.due_date < today,
            Invoice.total_amount > Invoice.paid_amount,
        )
    ).all()
    for inv in overdue:
        if _already_exists(db, NotificationType.PAYMENT_OVERDUE, "invoice", inv.id):
            continue
        name = inv.student.full_name if inv.student else f"#{inv.student_id}"
        broadcast(
            db,
            notification_type=NotificationType.PAYMENT_OVERDUE,
            severity=NotificationSeverity.ERROR,
            title_tr=f"Geciken ödeme: {name}",
            title_en=f"Overdue payment: {name}",
            body_tr=f"{inv.balance:,.2f} {inv.currency} · {inv.days_overdue} gün gecikmiş.",
            body_en=f"{inv.balance:,.2f} {inv.currency} · {inv.days_overdue} days overdue.",
            link=f"/finance/invoices/{inv.id}",
            role_codes=FINANCE_ROLES,
            entity_type="invoice",
            entity_id=inv.id,
        )
        count += 1
    created["payment_overdue"] = count

    # 3) Yaklaşan yarışmalar (14 gün)
    count = 0
    competitions = db.scalars(
        select(Competition).where(
            Competition.start_date >= today,
            Competition.start_date <= today + timedelta(days=14),
            Competition.is_completed.is_(False),
        )
    ).all()
    for comp in competitions:
        if _already_exists(
            db, NotificationType.COMPETITION_UPCOMING, "competition", comp.id
        ):
            continue
        days = (comp.start_date - today).days
        broadcast(
            db,
            notification_type=NotificationType.COMPETITION_UPCOMING,
            severity=NotificationSeverity.INFO,
            title_tr=f"Yaklaşan yarışma: {comp.name}",
            title_en=f"Upcoming competition: {comp.name}",
            body_tr=f"{comp.start_date:%d.%m.%Y} · {days} gün kaldı · {comp.location or ''}",
            body_en=f"{comp.start_date:%Y-%m-%d} · in {days} days · {comp.location or ''}",
            link=f"/competitions/{comp.id}",
            role_codes=COACH_ROLES,
            entity_type="competition",
            entity_id=comp.id,
        )
        count += 1
    created["competition_upcoming"] = count

    # 4) Havuz bakımı
    count = 0
    maintenances = db.scalars(
        select(PoolMaintenance).where(
            PoolMaintenance.is_completed.is_(False),
            PoolMaintenance.start_at >= datetime.combine(today, time.min),
            PoolMaintenance.start_at
            <= datetime.combine(today + timedelta(days=7), time.max),
        )
    ).all()
    for m in maintenances:
        if _already_exists(
            db, NotificationType.POOL_MAINTENANCE, "pool_maintenance", m.id
        ):
            continue
        pool_name = m.pool.name if m.pool else f"#{m.pool_id}"
        broadcast(
            db,
            notification_type=NotificationType.POOL_MAINTENANCE,
            severity=NotificationSeverity.WARNING,
            title_tr=f"Havuz bakımı: {pool_name}",
            title_en=f"Pool maintenance: {pool_name}",
            body_tr=f"{m.start_at:%d.%m %H:%M} - {m.end_at:%d.%m %H:%M} · {m.maintenance_type}",
            body_en=f"{m.start_at:%Y-%m-%d %H:%M} - {m.end_at:%Y-%m-%d %H:%M} · {m.maintenance_type}",
            link=f"/pools/{m.pool_id}",
            role_codes=MANAGEMENT_ROLES + ["pool_technician", "lifeguard"],
            entity_type="pool_maintenance",
            entity_id=m.id,
        )
        count += 1
    created["pool_maintenance"] = count

    # 5) İptal edilen dersler (bugün)
    count = 0
    cancelled = db.scalars(
        select(Lesson).where(
            Lesson.status == LessonStatus.CANCELLED,
            Lesson.start_at >= datetime.combine(today, time.min),
            Lesson.start_at <= datetime.combine(today + timedelta(days=2), time.max),
        )
    ).all()
    for lesson in cancelled:
        if _already_exists(db, NotificationType.LESSON_CANCELLED, "lesson", lesson.id):
            continue
        broadcast(
            db,
            notification_type=NotificationType.LESSON_CANCELLED,
            severity=NotificationSeverity.WARNING,
            title_tr=f"Ders iptal edildi: {lesson.title}",
            title_en=f"Lesson cancelled: {lesson.title}",
            body_tr=f"{lesson.start_at:%d.%m.%Y %H:%M} · {lesson.cancellation_reason or ''}",
            body_en=f"{lesson.start_at:%Y-%m-%d %H:%M} · {lesson.cancellation_reason or ''}",
            link=f"/calendar?lesson={lesson.id}",
            role_codes=MANAGEMENT_ROLES + ["reception"],
            entity_type="lesson",
            entity_id=lesson.id,
        )
        count += 1
    created["lesson_cancelled"] = count

    # 6) Performansı düşen sporcular (istatistik motorundan)
    count = 0
    try:
        from app.services.statistics_engine import find_declining_athletes

        for row in find_declining_athletes(db, lookback_days=90, min_records=4)[:10]:
            if _already_exists(
                db, NotificationType.PERFORMANCE_DROP, "student", row.student_id
            ):
                continue
            broadcast(
                db,
                notification_type=NotificationType.PERFORMANCE_DROP,
                severity=NotificationSeverity.WARNING,
                title_tr=f"Performans düşüşü: {row.student_name}",
                title_en=f"Performance decline: {row.student_name}",
                body_tr=(
                    f"{row.distance_m} m {row.stroke}: son dönem ortalaması "
                    f"%{row.decline_percent:.1f} geriledi."
                ),
                body_en=(
                    f"{row.distance_m} m {row.stroke}: recent average declined by "
                    f"{row.decline_percent:.1f}%."
                ),
                link=f"/students/{row.student_id}?tab=performance",
                role_codes=COACH_ROLES,
                entity_type="student",
                entity_id=row.student_id,
            )
            count += 1
    except Exception:  # noqa: BLE001 - istatistik hatası bildirim üretimini durdurmasın
        logger.warning("Performans düşüşü taraması başarısız", exc_info=True)
    created["performance_drop"] = count

    db.commit()
    total = sum(created.values())
    logger.info("Otomatik bildirim taraması tamamlandı: %s yeni kayıt", total)
    created["total"] = total
    return created
