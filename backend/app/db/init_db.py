"""Başlangıç verisi / Database bootstrap: roller, yönetici, varsayılan ayarlar."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import bootstrap
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.permissions import ROLE_PERMISSIONS, RoleCode, default_role_seed
from app.core.security import hash_password
from app.models.enums import PackageType
from app.models.membership import Package
from app.models.system import AppSetting, KpiTarget
from app.models.user import Role, User

logger = get_logger("application")
security_logger = get_logger("security")


def sync_roles(db: Session) -> int:
    """Rolleri kod tanımıyla senkronize eder (yeni izinler otomatik yayılır)."""
    created = 0
    for spec in default_role_seed():
        role = db.scalar(select(Role).where(Role.code == spec["code"]))
        if role is None:
            role = Role(**spec)
            db.add(role)
            created += 1
        else:
            # Sistem rollerinin izinleri kod tanımının otoritesindedir
            if role.is_system:
                role.permissions = spec["permissions"]
                role.name_tr = spec["name_tr"]
                role.name_en = spec["name_en"]
    db.commit()
    return created


def ensure_admin(db: Session) -> User | None:
    """İlk sistem yöneticisini oluşturur (varsa dokunmaz).

    Kurulum kapısı yalnızca **bir kez** açılır. Parola değiştirildikten sonra
    hesap silinse bile varsayılan kimlik geri gelmez; kapı ancak hiç etkin
    süper kullanıcı kalmadığında (yerel kurtarma) yeniden açılır.
    """
    admin = db.scalar(select(User).where(User.email == settings.first_admin_email))
    if admin:
        return admin

    if bootstrap.is_completed(db):
        if bootstrap.has_active_superuser(db):
            # Kurulum tamamlanmış ve yönetim erişimi mevcut: varsayılan
            # kimlik KESİNLİKLE yeniden oluşturulmaz.
            return None
        # Hiç etkin süper kullanıcı yok - yerel kurtarma kapısı açılır.
        security_logger.warning(
            "Etkin süper kullanıcı bulunamadı; kurulum kapısı yerel kurtarma "
            "için yeniden açıldı. İlk girişten sonra parolayı hemen değiştirin."
        )
        bootstrap.reopen_for_recovery(db)

    admin_role = db.scalar(select(Role).where(Role.code == RoleCode.SYSTEM_ADMIN))
    admin = User(
        email=settings.first_admin_email,
        hashed_password=hash_password(settings.first_admin_password),
        full_name="Sistem Yöneticisi",
        language=settings.app_default_language,
        is_active=True,
        is_superuser=True,
        must_change_password=True,
    )
    if admin_role:
        admin.roles.append(admin_role)
    db.add(admin)
    db.commit()
    # Parola DEĞERİ hiçbir zaman loglanmaz - yalnızca kapının açık olduğu
    # ve değiştirilmesi gerektiği bilgisi yazılır.
    security_logger.warning(
        "İlk kurulum yöneticisi oluşturuldu (%s). Kurulum parolası ilk "
        "girişte DEĞİŞTİRİLMELİDİR; değişene kadar giriş yalnızca yerel "
        "cihazdan kabul edilir ve hiçbir korumalı uca erişilemez.",
        settings.first_admin_email,
    )
    return admin


DEFAULT_SETTINGS: list[dict] = [
    {
        "key": "organization",
        "category": "general",
        "description": "Kurum bilgileri",
        "value": {
            "name": "Akıllı Yüzme Okulu",
            "logo_url": None,
            "phone": "",
            "email": "",
            "address": "",
            "website": "",
            "tax_office": "",
            "tax_number": "",
            "currency": settings.app_currency,
            "language": settings.app_default_language,
            "timezone": settings.app_timezone,
            "date_format": "DD.MM.YYYY",
        },
    },
    {
        "key": "attendance",
        "category": "operations",
        "description": "Yoklama davranış ayarları",
        "value": {
            "late_threshold_minutes": 10,
            "auto_consume_credit": True,
            "allow_makeup": True,
            "makeup_window_days": 30,
        },
    },
    {
        "key": "membership",
        "category": "operations",
        "description": "Üyelik uyarı eşikleri",
        "value": {"expiry_warning_days": 14, "low_credit_warning": 2},
    },
    {
        "key": "finance",
        "category": "finance",
        "description": "Finans ayarları",
        "value": {"overdue_grace_days": 3, "tax_rate": 0, "invoice_prefix": "FT"},
    },
    {
        "key": "developer",
        "category": "developer",
        "description": "AI geliştirici konsolu politikası",
        "value": {
            "ai_developer_enabled": settings.ai_developer_enabled,
            "allow_apply": settings.ai_developer_allow_apply,
            "allow_shell": settings.ai_developer_allow_shell,
            "auto_test": settings.ai_developer_auto_test,
            "patch_policy": "review_required",
        },
    },
    {
        "key": "backup",
        "category": "backup",
        "description": "Yedekleme politikası",
        "value": {
            "schedule_enabled": settings.backup_schedule_enabled,
            "schedule_cron": settings.backup_schedule_cron,
            "retention_daily": settings.backup_retention_daily,
            "retention_weekly": settings.backup_retention_weekly,
            "retention_monthly": settings.backup_retention_monthly,
        },
    },
    {
        "key": "ai_runtime",
        "category": "ai",
        "description": "Çalışma zamanı AI tercihleri (sır içermez)",
        "value": {
            "mode": settings.ai_default_mode,
            "fallback_chain": settings.fallback_chain_list,
            "response_language": settings.ai_response_language,
            "local_model": settings.local_ai_model,
            "nvidia_model": settings.nvidia_model,
        },
    },
]

DEFAULT_KPI_TARGETS: list[dict] = [
    {"kpi_key": "attendance_rate", "target_value": 90, "unit": "percent"},
    {"kpi_key": "pool_occupancy", "target_value": 80, "unit": "percent"},
    {"kpi_key": "collection_rate", "target_value": 95, "unit": "percent"},
    {"kpi_key": "student_retention", "target_value": 85, "unit": "percent"},
    {"kpi_key": "lane_occupancy", "target_value": 75, "unit": "percent"},
]

DEFAULT_PACKAGES: list[dict] = [
    {
        "name": "4 Ders",
        "name_en": "4 Lessons",
        "package_type": PackageType.LESSON_PACK,
        "lesson_count": 4,
        "duration_days": 60,
        "price": 1600,
        "color": "#38bdf8",
    },
    {
        "name": "8 Ders",
        "name_en": "8 Lessons",
        "package_type": PackageType.LESSON_PACK,
        "lesson_count": 8,
        "duration_days": 90,
        "price": 3000,
        "color": "#0ea5e9",
    },
    {
        "name": "12 Ders",
        "name_en": "12 Lessons",
        "package_type": PackageType.LESSON_PACK,
        "lesson_count": 12,
        "duration_days": 120,
        "price": 4200,
        "color": "#0284c7",
    },
    {
        "name": "Aylık Sınırsız",
        "name_en": "Monthly Unlimited",
        "package_type": PackageType.MONTHLY,
        "lesson_count": None,
        "duration_days": 30,
        "price": 3500,
        "color": "#6366f1",
    },
    {
        "name": "3 Aylık",
        "name_en": "Quarterly",
        "package_type": PackageType.QUARTERLY,
        "lesson_count": 36,
        "duration_days": 90,
        "price": 9500,
        "color": "#8b5cf6",
    },
    {
        "name": "6 Aylık",
        "name_en": "6 Months",
        "package_type": PackageType.BIANNUAL,
        "lesson_count": 72,
        "duration_days": 180,
        "price": 18000,
        "color": "#a855f7",
    },
    {
        "name": "Yıllık",
        "name_en": "Annual",
        "package_type": PackageType.ANNUAL,
        "lesson_count": 144,
        "duration_days": 365,
        "price": 33000,
        "color": "#d946ef",
    },
    {
        "name": "Özel Ders 10'lu",
        "name_en": "Private Lesson x10",
        "package_type": PackageType.PRIVATE_PACK,
        "lesson_count": 10,
        "duration_days": 120,
        "price": 9000,
        "color": "#f59e0b",
    },
    {
        "name": "Deneme Dersi",
        "name_en": "Trial Lesson",
        "package_type": PackageType.TRIAL,
        "lesson_count": 1,
        "duration_days": 14,
        "price": 0,
        "color": "#94a3b8",
    },
]


def seed_defaults(db: Session) -> None:
    """Ayarlar, KPI hedefleri ve paket tanımlarını oluşturur."""
    for spec in DEFAULT_SETTINGS:
        if not db.scalar(select(AppSetting).where(AppSetting.key == spec["key"])):
            db.add(AppSetting(**spec))

    for spec in DEFAULT_KPI_TARGETS:
        if not db.scalar(select(KpiTarget).where(KpiTarget.kpi_key == spec["kpi_key"])):
            db.add(KpiTarget(**spec))

    for spec in DEFAULT_PACKAGES:
        if not db.scalar(select(Package).where(Package.name == spec["name"])):
            db.add(Package(**spec, currency=settings.app_currency))

    db.commit()


def init_db(db: Session) -> dict:
    """Tüm başlangıç adımlarını çalıştırır. Idempotent."""
    created_roles = sync_roles(db)
    admin = ensure_admin(db)
    seed_defaults(db)
    return {
        "roles_created": created_roles,
        "total_roles": len(ROLE_PERMISSIONS),
        "admin_email": admin.email if admin else None,
        "initialized_at": date.today().isoformat(),
    }
