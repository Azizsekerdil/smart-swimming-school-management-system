"""Yedekleme ve geri yükleme uçları / Backup and restore endpoints."""

from __future__ import annotations


from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, db_session, get_language, require_permissions
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.system import BackupRecord, RestoreRecord
from app.models.user import User
from app.schemas.common import Message
from app.schemas.system import (
    BackupCreateRequest,
    BackupOut,
    BackupSettings,
    BackupStatusInfo,
    BackupVerifyResult,
    RestorePreview,
    RestoreRequest,
    RestoreResult,
)
from app.services import audit
from app.services.backup import (
    apply_retention,
    backup_status,
    create_backup,
    get_provider,
    restore_backup,
    restore_preview,
    verify_backup,
)

router = APIRouter(prefix="/backup", tags=["Yedekleme"])


def _to_out(record: BackupRecord) -> BackupOut:
    out = BackupOut.model_validate(record)
    out.size_mb = record.size_mb
    return out


@router.get("/status", response_model=BackupStatusInfo, summary="Yedekleme durumu")
def status(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.BACKUP_READ)),
) -> BackupStatusInfo:
    return BackupStatusInfo(**backup_status(db))


@router.get("", response_model=list[BackupOut], summary="Yedekleri listele")
def list_backups(
    limit: int = 100,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.BACKUP_READ)),
) -> list[BackupOut]:
    rows = db.scalars(
        select(BackupRecord).order_by(BackupRecord.created_at.desc()).limit(limit)
    ).all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=BackupOut, status_code=201, summary="Şimdi yedekle")
def create(
    payload: BackupCreateRequest,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.BACKUP_CREATE)),
) -> BackupOut:
    record = create_backup(
        db,
        backup_type=payload.backup_type,
        user_id=current.id,
        note=payload.note,
        include_uploads=payload.include_uploads,
        include_logs=payload.include_logs,
        protect=payload.protect,
    )
    audit.record(
        db,
        action="create",
        entity_type="backup",
        entity_id=record.backup_id,
        user=current,
        summary=f"Yedek oluşturuldu: {record.backup_id} ({record.size_mb} MB, {record.status})",
        ip_address=client_ip(request),
        commit=True,
    )
    return _to_out(record)


@router.post(
    "/{backup_id}/verify", response_model=BackupVerifyResult, summary="Yedeği doğrula"
)
def verify(
    backup_id: str,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.BACKUP_READ)),
) -> BackupVerifyResult:
    result = verify_backup(db, backup_id)
    if not result["checks"] and "bulunamadı" in result["message"]:
        raise NotFoundError("backup.not_found")
    return BackupVerifyResult(**result)


@router.get(
    "/{backup_id}/restore-preview",
    response_model=RestorePreview,
    summary="Geri yükleme önizleme",
)
def preview(
    backup_id: str,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.BACKUP_RESTORE)),
) -> RestorePreview:
    """Geri yüklemenin neyi değiştireceğini gösterir. Hiçbir değişiklik yapmaz."""
    return RestorePreview(**restore_preview(db, backup_id))


@router.post("/restore", response_model=RestoreResult, summary="Geri yükle")
def restore(
    payload: RestoreRequest,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.BACKUP_RESTORE)),
) -> RestoreResult:
    """Geri yükleme - `confirm=true` olmadan çalışmaz.

    Akış: doğrula -> güvenlik yedeği -> geri yükle -> bütünlük -> gerekirse rollback
    """
    if not payload.confirm:
        raise ValidationError(
            details={
                "reason": "confirmation_required",
                "hint": "Geri yükleme veri kaybına yol açabilir; confirm=true gönderin.",
            }
        )

    audit.record(
        db,
        action="restore_started",
        entity_type="backup",
        entity_id=payload.backup_id,
        user=current,
        summary=f"Geri yükleme başlatıldı: {payload.backup_id}",
        ip_address=client_ip(request),
        commit=True,
    )

    result = restore_backup(
        db,
        payload.backup_id,
        user_id=current.id,
        create_safety=payload.create_safety_backup,
    )

    from app.db.session import SessionLocal

    with SessionLocal() as fresh:
        audit.record(
            fresh,
            action="restore_finished",
            entity_type="backup",
            entity_id=payload.backup_id,
            user=None,
            summary=(
                f"Geri yükleme {'başarılı' if result['success'] else 'başarısız'}: "
                f"{result['message']}"
            ),
            commit=True,
        )

    return RestoreResult(**result)


@router.post("/{backup_id}/protect", response_model=BackupOut, summary="Yedeği koru")
def protect(
    backup_id: str,
    protect: bool = True,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.BACKUP_CREATE)),
) -> BackupOut:
    """Korunan yedekler saklama politikası tarafından silinmez."""
    record = db.scalar(select(BackupRecord).where(BackupRecord.backup_id == backup_id))
    if record is None:
        raise NotFoundError("backup.not_found")
    record.is_protected = protect
    audit.record(
        db,
        action="protect" if protect else "unprotect",
        entity_type="backup",
        entity_id=backup_id,
        user=current,
        summary=f"Yedek koruma durumu: {protect}",
    )
    db.commit()
    return _to_out(record)


@router.delete("/{backup_id}", response_model=Message, summary="Yedeği sil")
def delete_backup(
    backup_id: str,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.BACKUP_CREATE)),
    lang: str = Depends(get_language),
) -> Message:
    record = db.scalar(select(BackupRecord).where(BackupRecord.backup_id == backup_id))
    if record is None:
        raise NotFoundError("backup.not_found")
    if record.is_protected:
        raise ValidationError("backup.protected")

    get_provider().delete(record.file_path)
    db.delete(record)
    audit.record(
        db,
        action="delete",
        entity_type="backup",
        entity_id=backup_id,
        user=current,
        summary=f"Yedek silindi: {backup_id}",
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


@router.post("/cleanup", response_model=Message, summary="Eski yedekleri temizle")
def cleanup(
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.BACKUP_CREATE)),
    lang: str = Depends(get_language),
) -> Message:
    """Saklama politikasını uygular (korunan yedeklere dokunmaz)."""
    result = apply_retention(db)
    audit.record(
        db,
        action="cleanup",
        entity_type="backup",
        user=current,
        summary=f"{result['deleted_count']} eski yedek silindi ({result['freed_mb']} MB)",
        commit=True,
    )
    return Message(
        code="common.deleted", message=t("common.deleted", lang), data=result
    )


@router.get(
    "/settings/current", response_model=BackupSettings, summary="Yedekleme ayarları"
)
def get_backup_settings(
    _: User = Depends(require_permissions(Perm.BACKUP_READ)),
) -> BackupSettings:
    return BackupSettings(
        schedule_enabled=settings.backup_schedule_enabled,
        schedule_cron=settings.backup_schedule_cron,
        retention_daily=settings.backup_retention_daily,
        retention_weekly=settings.backup_retention_weekly,
        retention_monthly=settings.backup_retention_monthly,
        backup_dir=str(settings.backup_path),
    )


@router.get("/location/open", summary="Yedek klasörü yolu")
def backup_location(
    _: User = Depends(require_permissions(Perm.BACKUP_READ)),
) -> dict:
    """Yedek klasörünün yolunu döndürür (arayüz bu yolu kullanıcıya gösterir)."""
    path = settings.backup_path
    files = sorted(path.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "path": str(path),
        "exists": path.exists(),
        "file_count": len(files),
        "total_size_mb": round(sum(f.stat().st_size for f in files) / 1048576, 2),
        "recent_files": [f.name for f in files[:10]],
    }


@router.get("/restores/history", summary="Geri yükleme geçmişi")
def restore_history(
    limit: int = 50,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.BACKUP_READ)),
) -> list[dict]:
    rows = db.scalars(
        select(RestoreRecord).order_by(RestoreRecord.started_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "backup_id": r.backup_id,
            "safety_backup_id": r.safety_backup_id,
            "status": r.status,
            "message": r.message,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in rows
    ]
