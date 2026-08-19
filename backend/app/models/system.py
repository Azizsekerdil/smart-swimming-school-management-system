"""Sistem modelleri / System models: denetim, bildirim, ayar, yedek, AI görev."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import (
    AITaskKind,
    AITaskStatus,
    BackupStatus,
    BackupType,
    NotificationSeverity,
    NotificationType,
    TrainingStatus,
)

if TYPE_CHECKING:
    pass


class AuditLog(Base, IntPKMixin):
    """Denetim kaydı: kim, ne yaptı, ne zaman, hangi kayıt değişti."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_user_time", "user_id", "occurred_at"),
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    user_email: Mapped[str | None] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(
        String(60), nullable=False, index=True
    )  # create/update/delete/login...
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(40))
    summary: Mapped[str | None] = mapped_column(String(400))
    changes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class Notification(Base, IntPKMixin):
    """Kullanıcı bildirimi."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_user_read", "user_id", "is_read"),)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    notification_type: Mapped[str] = mapped_column(
        String(40), default=NotificationType.SYSTEM, nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(20), default=NotificationSeverity.INFO, nullable=False
    )
    title_tr: Mapped[str] = mapped_column(String(200), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(200))
    body_tr: Mapped[str | None] = mapped_column(Text)
    body_en: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(300))
    entity_type: Mapped[str | None] = mapped_column(String(60))
    entity_id: Mapped[str | None] = mapped_column(String(40))

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def title(self, lang: str = "tr") -> str:
        return (self.title_en or self.title_tr) if lang == "en" else self.title_tr

    def body(self, lang: str = "tr") -> str | None:
        return (self.body_en or self.body_tr) if lang == "en" else self.body_tr


class AppSetting(Base, IntPKMixin, TimestampMixin):
    """Anahtar-değer uygulama ayarı (kurum bilgisi, KPI hedefleri, tercihler)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    category: Mapped[str] = mapped_column(
        String(60), default="general", nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(400))
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class BackupRecord(Base, IntPKMixin):
    """Oluşturulmuş yedeğin kaydı ve bütünlük bilgisi."""

    __tablename__ = "backup_records"

    backup_id: Mapped[str] = mapped_column(
        String(60), unique=True, index=True, nullable=False
    )
    backup_type: Mapped[str] = mapped_column(
        String(20), default=BackupType.MANUAL, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=BackupStatus.CREATING, nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(600), nullable=False)
    file_name: Mapped[str] = mapped_column(String(300), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    manifest: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    app_version: Mapped[str | None] = mapped_column(String(30))
    db_revision: Mapped[str | None] = mapped_column(String(60))
    record_counts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    is_protected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_message: Mapped[str | None] = mapped_column(String(400))
    error_message: Mapped[str | None] = mapped_column(Text)

    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024 * 1024), 2)


class RestoreRecord(Base, IntPKMixin):
    """Geri yükleme işlemi kaydı (izlenebilirlik için)."""

    __tablename__ = "restore_records"

    backup_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    safety_backup_id: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    performed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AITask(Base, IntPKMixin):
    """AI görev kaydı: sağlayıcı, model, token, süre, sonuç."""

    __tablename__ = "ai_tasks"
    __table_args__ = (Index("ix_ai_task_kind_status", "kind", "status"),)

    kind: Mapped[str] = mapped_column(
        String(30), default=AITaskKind.CHAT, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=AITaskStatus.PENDING, nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    provider: Mapped[str | None] = mapped_column(String(40), index=True)
    model: Mapped[str | None] = mapped_column(String(160))
    # Gizlilik: prompt yalnızca AI_LOG_PROMPTS=true iken saklanır
    prompt_preview: Mapped[str | None] = mapped_column(Text)
    result_preview: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempted_providers: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    file_changes: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    test_result: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIProviderHealth(Base, IntPKMixin):
    """AI sağlayıcı sağlık kontrolü geçmişi (AI Control Center için)."""

    __tablename__ = "ai_provider_health"

    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    model_count: Mapped[int | None] = mapped_column(Integer)
    endpoint: Mapped[str | None] = mapped_column(String(300))
    error_message: Mapped[str | None] = mapped_column(String(600))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class CAIOFinding(Base, IntPKMixin):
    """CAIO ajanının tespit ve önerileri (Observe -> Analyze -> Propose)."""

    __tablename__ = "caio_findings"

    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(
        String(20), default="info", nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(40), default="analysis", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="open", nullable=False, index=True
    )
    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    ai_provider: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KpiTarget(Base, IntPKMixin, TimestampMixin):
    """Yönetici tarafından belirlenen KPI hedefi."""

    __tablename__ = "kpi_targets"

    kpi_key: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="percent", nullable=False)
    period: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(400))


class TrainingProgress(Base, IntPKMixin, TimestampMixin):
    """Eğitim Merkezi ilerleme kaydı."""

    __tablename__ = "training_progress"
    __table_args__ = (
        Index("ix_training_user_tutorial", "user_id", "tutorial_id", unique=True),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tutorial_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=TrainingStatus.NOT_STARTED, nullable=False
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def progress_percent(self) -> float:
        if not self.total_steps:
            return 0.0
        return round(self.current_step / self.total_steps * 100, 1)


class ReportTemplate(Base, IntPKMixin, TimestampMixin):
    """Kayıtlı rapor şablonu (Report Builder filtreleri)."""

    __tablename__ = "report_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    report_key: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    filters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(String(400))
    is_shared: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class SystemEvent(Base, IntPKMixin):
    """Uygulama seviyesinde önemli olaylar (başlangıç, migration, hata sayacı)."""

    __tablename__ = "system_events"

    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    message: Mapped[str] = mapped_column(String(600), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
