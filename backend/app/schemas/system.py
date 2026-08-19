"""Sistem şemaları: bildirim, denetim, ayar, yedek, KPI, eğitim, arama."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import (
    BackupStatus,
    BackupType,
    NotificationSeverity,
    NotificationType,
    TrainingStatus,
)
from app.schemas.common import ORMModel


# ---------------------------------------------------------------------------
# Bildirim
# ---------------------------------------------------------------------------
class NotificationOut(ORMModel):
    id: int
    notification_type: NotificationType
    severity: NotificationSeverity
    title: str
    body: str | None = None
    link: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool = False
    created_at: datetime


class NotificationCreate(BaseModel):
    user_ids: list[int] = Field(default_factory=list)
    role_codes: list[str] = Field(default_factory=list)
    notification_type: NotificationType = NotificationType.SYSTEM
    severity: NotificationSeverity = NotificationSeverity.INFO
    title_tr: str = Field(min_length=1, max_length=200)
    title_en: str | None = None
    body_tr: str | None = None
    body_en: str | None = None
    link: str | None = None


class NotificationCounts(BaseModel):
    total: int = 0
    unread: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Denetim kaydı
# ---------------------------------------------------------------------------
class AuditLogOut(ORMModel):
    id: int
    user_id: int | None = None
    user_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    summary: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    occurred_at: datetime


class AuditFilter(BaseModel):
    user_id: int | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None


# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------
class OrganizationSettings(BaseModel):
    name: str = "Yüzme Okulu"
    logo_url: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    website: str | None = None
    tax_office: str | None = None
    tax_number: str | None = None
    currency: str = "TRY"
    language: str = "tr"
    timezone: str = "Europe/Istanbul"
    date_format: str = "DD.MM.YYYY"


class DeveloperSettings(BaseModel):
    ai_developer_enabled: bool = True
    allow_apply: bool = False
    allow_shell: bool = False
    auto_test: bool = True
    patch_policy: str = "review_required"  # review_required | auto_apply_safe


class BackupSettings(BaseModel):
    schedule_enabled: bool = False
    schedule_cron: str = "0 23 * * *"
    retention_daily: int = 7
    retention_weekly: int = 4
    retention_monthly: int = 12
    backup_dir: str = "./backups"


class SettingUpdate(BaseModel):
    key: str
    value: Any
    category: str = "general"


class SettingOut(ORMModel):
    id: int
    key: str
    value: Any = None
    category: str
    description: str | None = None
    updated_at: datetime | None = None


class AboutInfo(BaseModel):
    """Ayarlar > Hakkında ekranı."""

    app_name: str
    version: str
    build: str
    git_commit: str | None = None
    database_revision: str | None = None
    database_engine: str
    python_version: str
    platform: str
    last_updated: datetime | None = None
    license: str = "MIT"


# ---------------------------------------------------------------------------
# Yedekleme
# ---------------------------------------------------------------------------
class BackupCreateRequest(BaseModel):
    backup_type: BackupType = BackupType.MANUAL
    note: str | None = None
    include_uploads: bool = True
    include_logs: bool = False
    protect: bool = False


class BackupOut(ORMModel):
    id: int
    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    file_name: str
    size_bytes: int
    size_mb: float = 0.0
    checksum_sha256: str | None = None
    app_version: str | None = None
    db_revision: str | None = None
    record_counts: dict[str, int] = Field(default_factory=dict)
    is_protected: bool = False
    verified_at: datetime | None = None
    verification_message: str | None = None
    error_message: str | None = None
    created_at: datetime


class BackupVerifyResult(BaseModel):
    backup_id: str
    is_valid: bool
    checks: list[dict[str, Any]]
    message: str


class RestorePreview(BaseModel):
    """Geri yükleme öncesi kullanıcıya gösterilen değişiklik özeti."""

    backup_id: str
    backup_created_at: datetime
    backup_app_version: str | None = None
    backup_db_revision: str | None = None
    current_db_revision: str | None = None
    revision_compatible: bool = True
    current_counts: dict[str, int] = Field(default_factory=dict)
    backup_counts: dict[str, int] = Field(default_factory=dict)
    differences: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    integrity_ok: bool = False


class RestoreRequest(BaseModel):
    backup_id: str
    confirm: bool = Field(
        description="Kullanıcı onayı - true olmadan geri yükleme yapılmaz"
    )
    create_safety_backup: bool = True


class RestoreResult(BaseModel):
    success: bool
    backup_id: str
    safety_backup_id: str | None = None
    message: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    rolled_back: bool = False


class BackupStatusInfo(BaseModel):
    """Yedekleme ekranı üst bilgi kartı."""

    last_backup_at: datetime | None = None
    last_successful_backup_at: datetime | None = None
    last_backup_size_mb: float | None = None
    backup_location: str
    total_backup_count: int = 0
    total_size_mb: float = 0.0
    protected_count: int = 0
    schedule_enabled: bool = False
    schedule_cron: str | None = None
    next_backup_at: datetime | None = None
    status: str = "unknown"


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------
class KpiTargetIn(BaseModel):
    kpi_key: str = Field(min_length=1, max_length=80)
    target_value: float
    unit: str = "percent"
    period: str = "monthly"
    notes: str | None = None


class KpiTargetOut(ORMModel, KpiTargetIn):
    id: int
    is_active: bool = True


class KpiValue(BaseModel):
    key: str
    label_tr: str
    label_en: str
    value: float
    unit: str
    target: float | None = None
    achievement_percent: float | None = None
    status: str = "neutral"  # good | warning | bad | neutral
    previous_value: float | None = None
    change_percent: float | None = None
    description_tr: str | None = None
    description_en: str | None = None


class KpiDashboard(BaseModel):
    period_start: date
    period_end: date
    kpis: list[KpiValue]


# ---------------------------------------------------------------------------
# Eğitim merkezi
# ---------------------------------------------------------------------------
class TutorialStep(BaseModel):
    order: int
    title_tr: str
    title_en: str
    body_tr: str
    body_en: str
    target_route: str | None = None
    action_hint_tr: str | None = None
    action_hint_en: str | None = None


class TutorialOut(BaseModel):
    id: str
    title_tr: str
    title_en: str
    description_tr: str
    description_en: str
    category: str
    roles: list[str] = Field(default_factory=list)
    estimated_minutes: int = 5
    steps: list[TutorialStep] = Field(default_factory=list)
    status: TrainingStatus = TrainingStatus.NOT_STARTED
    current_step: int = 0
    total_steps: int = 0
    progress_percent: float = 0.0


class TutorialProgressUpdate(BaseModel):
    tutorial_id: str
    current_step: int = Field(ge=0)
    status: TrainingStatus | None = None


class TrainingOverview(BaseModel):
    tracks: list[dict[str, Any]]
    total_tutorials: int
    completed: int
    in_progress: int
    overall_percent: float


class OnboardingState(BaseModel):
    completed: bool = False
    current_step: int = 0
    steps_done: list[str] = Field(default_factory=list)
    organization_configured: bool = False
    has_pool: bool = False
    has_instructor: bool = False
    has_student: bool = False
    ai_configured: bool = False
    backup_configured: bool = False


# ---------------------------------------------------------------------------
# Global arama & komut paleti
# ---------------------------------------------------------------------------
class SearchHit(BaseModel):
    entity_type: str
    id: int
    title: str
    subtitle: str | None = None
    route: str
    badge: str | None = None
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    total: int
    groups: dict[str, list[SearchHit]]
    took_ms: int = 0
