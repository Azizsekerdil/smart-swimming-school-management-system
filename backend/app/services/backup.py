"""Yedekleme ve felaket kurtarma / Backup and disaster recovery.

Tasarım:
  * Yedek = ZIP arşivi + `backup_manifest.json` (SHA-256 özetleri dahil).
  * Sırlar (.env, API anahtarları) ASLA yedeğe dahil edilmez.
  * Her yedekten sonra otomatik bütünlük doğrulaması yapılır.
  * Geri yükleme öncesi mutlaka güvenlik yedeği alınır; hata olursa geri alınır.
  * `BackupProvider` soyutlaması ileride bulut hedeflerine izin verir; ancak
    kullanıcı izni olmadan hiçbir veri dışarı gönderilmez.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.security import file_sha256
from app.db.session import SessionLocal, database_file_path, engine, is_sqlite
from app.models import (
    Attendance,
    Competition,
    Guardian,
    Instructor,
    Invoice,
    Lesson,
    Membership,
    Payment,
    PerformanceRecord,
    Pool,
    Student,
    User,
)
from app.models.enums import BackupStatus, BackupType
from app.models.system import BackupRecord, RestoreRecord

logger = get_logger("application")

MANIFEST_NAME = "backup_manifest.json"
DB_ENTRY_NAME = "database/swimming_school.db"

# Yedeğe ASLA dahil edilmeyecek dosya desenleri (sır sızıntısı önlemi)
EXCLUDED_PATTERNS = (
    ".env",
    ".key",
    ".pem",
    "credentials",
    "secrets",
    "token",
    "id_rsa",
)

COUNT_MODELS = {
    "users": User,
    "students": Student,
    "guardians": Guardian,
    "instructors": Instructor,
    "pools": Pool,
    "lessons": Lesson,
    "attendances": Attendance,
    "memberships": Membership,
    "payments": Payment,
    "invoices": Invoice,
    "performance_records": PerformanceRecord,
    "competitions": Competition,
}


# ===========================================================================
# Sağlayıcı soyutlaması
# ===========================================================================
class BackupProvider(ABC):
    """Yedek hedefi soyutlaması (yerel disk, NAS, bulut ...)."""

    name: str = "base"

    @abstractmethod
    def store(self, source: Path, backup_id: str) -> str:
        """Yedeği hedefe yazar ve erişim yolunu döndürür."""

    @abstractmethod
    def retrieve(self, path: str) -> Path:
        """Yedeği yerel olarak erişilebilir hale getirir."""

    @abstractmethod
    def delete(self, path: str) -> bool: ...

    @abstractmethod
    def exists(self, path: str) -> bool: ...


class LocalDiskProvider(BackupProvider):
    """Yerel disk yedekleme - ilk sürümde varsayılan ve tek etkin sağlayıcı."""

    name = "local_disk"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.backup_path
        self.root.mkdir(parents=True, exist_ok=True)

    def store(self, source: Path, backup_id: str) -> str:
        target = self.root / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        return str(target)

    def retrieve(self, path: str) -> Path:
        return Path(path)

    def delete(self, path: str) -> bool:
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def exists(self, path: str) -> bool:
        return Path(path).exists()


_provider: BackupProvider = LocalDiskProvider()


def get_provider() -> BackupProvider:
    return _provider


# ===========================================================================
# Yardımcılar
# ===========================================================================
def _record_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, model in COUNT_MODELS.items():
        try:
            counts[label] = db.scalar(select(func.count()).select_from(model)) or 0
        except Exception:  # noqa: BLE001
            counts[label] = -1
    return counts


def _db_revision(db: Session) -> str | None:
    try:
        return db.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
    except Exception:  # noqa: BLE001
        return None


def _is_excluded(path: Path) -> bool:
    name = path.name.lower()
    return any(pattern in name for pattern in EXCLUDED_PATTERNS)


def _snapshot_sqlite(destination: Path) -> bool:
    """SQLite veritabanının tutarlı bir kopyasını alır.

    `sqlite3.Connection.backup()` çevrimiçi yedekleme API'sini kullanır; bu,
    WAL modunda açık bağlantılar varken bile bütünlüklü kopya üretir.
    """
    source_path = database_file_path()
    if not source_path or not Path(source_path).exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(source_path)
    target = sqlite3.connect(str(destination))
    try:
        with target:
            source.backup(target)
        return True
    finally:
        source.close()
        target.close()


def _sanitized_ai_config() -> dict[str, Any]:
    """AI yapılandırması - SIRLAR HARİÇ."""
    config = settings.public_ai_config()
    for section in config.values():
        if isinstance(section, dict):
            section.pop("api_key_masked", None)
    return config


# ===========================================================================
# Yedek oluşturma
# ===========================================================================
def create_backup(
    db: Session,
    *,
    backup_type: str = BackupType.MANUAL,
    user_id: int | None = None,
    note: str | None = None,
    include_uploads: bool = True,
    include_logs: bool = False,
    protect: bool = False,
) -> BackupRecord:
    """Tam yedek oluşturur, doğrular ve kaydeder."""
    now = datetime.now(timezone.utc)
    backup_id = f"bkp_{now:%Y%m%d_%H%M%S}_{backup_type}"
    provider = get_provider()
    archive_path = (
        provider.root / f"{backup_id}.zip"
        if isinstance(provider, LocalDiskProvider)
        else settings.backup_path / f"{backup_id}.zip"
    )

    record = BackupRecord(
        backup_id=backup_id,
        backup_type=backup_type,
        status=BackupStatus.CREATING,
        file_path=str(archive_path),
        file_name=archive_path.name,
        app_version=settings.app_version,
        db_revision=_db_revision(db),
        record_counts=_record_counts(db),
        is_protected=protect,
        created_by_user_id=user_id,
        created_at=now,
    )
    db.add(record)
    db.commit()

    temp_dir = settings.backup_path / f".tmp_{backup_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        files_in_archive: list[dict[str, Any]] = []

        # 1) Veritabanı
        db_copy = temp_dir / "swimming_school.db"
        if is_sqlite():
            if not _snapshot_sqlite(db_copy):
                raise RuntimeError("SQLite veritabanı dosyası bulunamadı")
        else:
            raise RuntimeError(
                "Bu sürümde otomatik yedekleme yalnızca SQLite için desteklenir. "
                "PostgreSQL için pg_dump kullanın."
            )
        files_in_archive.append(
            {
                "path": DB_ENTRY_NAME,
                "size": db_copy.stat().st_size,
                "sha256": file_sha256(str(db_copy)),
                "kind": "database",
            }
        )

        # 2) Ayarlar (sırlar hariç)
        settings_payload = {
            "app_version": settings.app_version,
            "app_env": settings.app_env,
            "currency": settings.app_currency,
            "language": settings.app_default_language,
            "timezone": settings.app_timezone,
            "ai_config": _sanitized_ai_config(),
            "note": "API anahtarları ve parolalar güvenlik gereği yedeğe dahil edilmez.",
        }
        settings_file = temp_dir / "settings.json"
        settings_file.write_text(
            json.dumps(settings_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        files_in_archive.append(
            {
                "path": "settings.json",
                "size": settings_file.stat().st_size,
                "sha256": file_sha256(str(settings_file)),
                "kind": "settings",
            }
        )

        # 3) Yüklenen belgeler
        upload_entries: list[tuple[Path, str]] = []
        uploads_dir = settings.data_path / "uploads"
        if include_uploads and uploads_dir.exists():
            for file_path in uploads_dir.rglob("*"):
                if file_path.is_file() and not _is_excluded(file_path):
                    relative = (
                        f"uploads/{file_path.relative_to(uploads_dir).as_posix()}"
                    )
                    upload_entries.append((file_path, relative))

        log_entries: list[tuple[Path, str]] = []
        if include_logs and settings.log_path.exists():
            for file_path in settings.log_path.glob("*.log"):
                if not _is_excluded(file_path):
                    log_entries.append((file_path, f"logs/{file_path.name}"))

        # 4) Manifest
        manifest = {
            "backup_id": backup_id,
            "created_at": now.isoformat(),
            "backup_type": backup_type,
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "database_engine": "sqlite",
            "database_revision": record.db_revision,
            "record_counts": record.record_counts,
            "note": note,
            "includes_uploads": bool(upload_entries),
            "includes_logs": bool(log_entries),
            "excludes_secrets": True,
            "files": files_in_archive
            + [
                {"path": relative, "size": path.stat().st_size, "kind": "upload"}
                for path, relative in upload_entries
            ]
            + [
                {"path": relative, "size": path.stat().st_size, "kind": "log"}
                for path, relative in log_entries
            ],
        }
        manifest_file = temp_dir / MANIFEST_NAME
        manifest_file.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 5) Arşivle
        with zipfile.ZipFile(
            archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            archive.write(manifest_file, MANIFEST_NAME)
            archive.write(db_copy, DB_ENTRY_NAME)
            archive.write(settings_file, "settings.json")
            for path, relative in upload_entries + log_entries:
                archive.write(path, relative)

        record.size_bytes = archive_path.stat().st_size
        record.checksum_sha256 = file_sha256(str(archive_path))
        record.manifest = manifest
        record.status = BackupStatus.COMPLETED
        db.commit()

        # 6) Otomatik doğrulama
        verification = verify_backup(db, backup_id)
        record.status = (
            BackupStatus.VERIFIED
            if verification["is_valid"]
            else BackupStatus.CORRUPTED
        )
        record.verified_at = datetime.now(timezone.utc)
        record.verification_message = verification["message"][:400]
        db.commit()

        logger.info(
            "Yedek oluşturuldu: %s (%.2f MB, durum: %s)",
            backup_id,
            record.size_mb,
            record.status,
        )

    except Exception as exc:  # noqa: BLE001
        record.status = BackupStatus.FAILED
        record.error_message = f"{type(exc).__name__}: {exc}"[:1000]
        db.commit()
        logger.exception("Yedek oluşturulamadı: %s", backup_id)
        if archive_path.exists():
            archive_path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return record


# ===========================================================================
# Doğrulama
# ===========================================================================
def verify_backup(db: Session, backup_id: str) -> dict[str, Any]:
    """Yedeğin bütünlüğünü çok adımlı olarak doğrular."""
    record = db.scalar(select(BackupRecord).where(BackupRecord.backup_id == backup_id))
    if record is None:
        return {
            "backup_id": backup_id,
            "is_valid": False,
            "checks": [],
            "message": "Yedek kaydı bulunamadı.",
        }

    checks: list[dict[str, Any]] = []
    archive_path = Path(record.file_path)

    def check(name: str, passed: bool, detail: str = "") -> bool:
        checks.append(
            {"check": name, "result": "PASS" if passed else "FAIL", "detail": detail}
        )
        return passed

    # 1) Dosya var mı?
    if not check("file_exists", archive_path.exists(), str(archive_path)):
        return {
            "backup_id": backup_id,
            "is_valid": False,
            "checks": checks,
            "message": "Yedek dosyası bulunamadı.",
        }

    # 2) Boyut mantıklı mı?
    size = archive_path.stat().st_size
    check("size_reasonable", size > 1024, f"{size} bayt")

    # 3) Checksum
    if record.checksum_sha256:
        actual = file_sha256(str(archive_path))
        check(
            "checksum_matches",
            actual == record.checksum_sha256,
            f"{actual[:16]}… / beklenen {record.checksum_sha256[:16]}…",
        )

    # 4) ZIP bütünlüğü + manifest + veritabanı
    temp_dir = settings.backup_path / f".verify_{backup_id}"
    try:
        with zipfile.ZipFile(archive_path) as archive:
            bad_file = archive.testzip()
            check("archive_intact", bad_file is None, bad_file or "OK")

            names = archive.namelist()
            check("manifest_present", MANIFEST_NAME in names)
            check("database_present", DB_ENTRY_NAME in names)

            if MANIFEST_NAME in names:
                manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
                check(
                    "manifest_valid",
                    manifest.get("backup_id") == backup_id,
                    f"id: {manifest.get('backup_id')}",
                )
                check(
                    "secrets_excluded",
                    manifest.get("excludes_secrets") is True,
                    "Sırlar yedeğe dahil edilmemiş",
                )

            if DB_ENTRY_NAME in names:
                temp_dir.mkdir(parents=True, exist_ok=True)
                archive.extract(DB_ENTRY_NAME, temp_dir)
                extracted = temp_dir / DB_ENTRY_NAME
                connection = sqlite3.connect(str(extracted))
                try:
                    integrity = connection.execute("PRAGMA integrity_check").fetchone()
                    check(
                        "database_integrity",
                        integrity and integrity[0] == "ok",
                        str(integrity),
                    )
                    tables = connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                    check("tables_readable", len(tables) > 10, f"{len(tables)} tablo")
                    student_count = connection.execute(
                        "SELECT COUNT(*) FROM students"
                    ).fetchone()[0]
                    expected = record.record_counts.get("students", 0)
                    check(
                        "record_counts_match",
                        student_count == expected,
                        f"öğrenci: {student_count} / beklenen {expected}",
                    )
                finally:
                    connection.close()
    except Exception as exc:  # noqa: BLE001
        check("archive_readable", False, f"{type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    is_valid = all(c["result"] == "PASS" for c in checks)
    passed = sum(1 for c in checks if c["result"] == "PASS")
    message = (
        f"Tüm kontroller başarılı ({passed}/{len(checks)})."
        if is_valid
        else f"Doğrulama başarısız: {passed}/{len(checks)} kontrol geçti."
    )

    record.verified_at = datetime.now(timezone.utc)
    record.verification_message = message[:400]
    if not is_valid and record.status == BackupStatus.VERIFIED:
        record.status = BackupStatus.CORRUPTED
    db.commit()

    return {
        "backup_id": backup_id,
        "is_valid": is_valid,
        "checks": checks,
        "message": message,
    }


# ===========================================================================
# Geri yükleme
# ===========================================================================
def restore_preview(db: Session, backup_id: str) -> dict[str, Any]:
    """Geri yükleme öncesi neyin değişeceğini gösterir."""
    record = db.scalar(select(BackupRecord).where(BackupRecord.backup_id == backup_id))
    if record is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("backup.not_found", details={"backup_id": backup_id})

    verification = verify_backup(db, backup_id)
    current_counts = _record_counts(db)
    backup_counts = record.record_counts or {}
    current_revision = _db_revision(db)

    differences = {
        key: backup_counts.get(key, 0) - current_counts.get(key, 0)
        for key in set(current_counts) | set(backup_counts)
    }

    warnings: list[str] = []
    if not verification["is_valid"]:
        warnings.append(
            "Yedek bütünlük doğrulamasından geçemedi. Geri yükleme önerilmez."
        )
    if (
        record.db_revision
        and current_revision
        and record.db_revision != current_revision
    ):
        warnings.append(
            f"Veritabanı şema sürümü farklı (yedek: {record.db_revision}, "
            f"mevcut: {current_revision}). Geri yükleme sonrası migration gerekebilir."
        )
    if record.app_version != settings.app_version:
        warnings.append(
            f"Program sürümü farklı (yedek: {record.app_version}, mevcut: {settings.app_version})."
        )
    losses = {k: v for k, v in differences.items() if v < 0}
    if losses:
        warnings.append(
            "Bu geri yükleme sonucunda bazı kayıtlar KAYBOLACAK: "
            + ", ".join(f"{k}: {abs(v)}" for k, v in losses.items())
        )

    return {
        "backup_id": backup_id,
        "backup_created_at": record.created_at,
        "backup_app_version": record.app_version,
        "backup_db_revision": record.db_revision,
        "current_db_revision": current_revision,
        "revision_compatible": record.db_revision == current_revision,
        "current_counts": current_counts,
        "backup_counts": backup_counts,
        "differences": differences,
        "warnings": warnings,
        "integrity_ok": verification["is_valid"],
    }


def restore_backup(
    db: Session,
    backup_id: str,
    *,
    user_id: int | None = None,
    create_safety: bool = True,
) -> dict[str, Any]:
    """Güvenli geri yükleme akışı.

    Doğrula -> güvenlik yedeği -> geri yükle -> bütünlük kontrolü -> hata varsa rollback
    """
    steps: list[dict[str, Any]] = []
    started = datetime.now(timezone.utc)

    def step(name: str, status: str, detail: str = "") -> None:
        steps.append({"step": name, "status": status, "detail": detail})

    record = db.scalar(select(BackupRecord).where(BackupRecord.backup_id == backup_id))
    if record is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("backup.not_found", details={"backup_id": backup_id})

    restore_log = RestoreRecord(
        backup_id=backup_id,
        status="running",
        performed_by_user_id=user_id,
        started_at=started,
    )
    db.add(restore_log)
    db.commit()

    # 1) Doğrula
    verification = verify_backup(db, backup_id)
    step(
        "verify_backup",
        "success" if verification["is_valid"] else "failed",
        verification["message"],
    )
    if not verification["is_valid"]:
        restore_log.status = "failed"
        restore_log.message = (
            "Bütünlük doğrulaması başarısız - geri yükleme iptal edildi."
        )
        restore_log.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "success": False,
            "backup_id": backup_id,
            "safety_backup_id": None,
            "message": restore_log.message,
            "steps": steps,
            "rolled_back": False,
        }

    # 2) Güvenlik yedeği
    safety_id: str | None = None
    if create_safety:
        try:
            safety = create_backup(
                db,
                backup_type=BackupType.SAFETY,
                user_id=user_id,
                note=f"{backup_id} geri yüklenmeden önce otomatik güvenlik yedeği",
                include_uploads=True,
                protect=True,
            )
            safety_id = safety.backup_id
            restore_log.safety_backup_id = safety_id
            db.commit()
            step("safety_backup", "success", safety_id)
        except Exception as exc:  # noqa: BLE001
            step("safety_backup", "failed", str(exc))
            restore_log.status = "failed"
            restore_log.message = (
                "Güvenlik yedeği alınamadı - geri yükleme iptal edildi."
            )
            restore_log.finished_at = datetime.now(timezone.utc)
            db.commit()
            return {
                "success": False,
                "backup_id": backup_id,
                "safety_backup_id": None,
                "message": restore_log.message,
                "steps": steps,
                "rolled_back": False,
            }

    target_db = database_file_path()
    if not target_db:
        step("restore_database", "failed", "SQLite olmayan veritabanı")
        return {
            "success": False,
            "backup_id": backup_id,
            "safety_backup_id": safety_id,
            "message": "Bu sürümde geri yükleme yalnızca SQLite için desteklenir.",
            "steps": steps,
            "rolled_back": False,
        }

    target_path = Path(target_db)
    temp_dir = settings.backup_path / f".restore_{backup_id}"
    rolled_back = False

    try:
        # 3) Çıkart
        temp_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(Path(record.file_path)) as archive:
            archive.extract(DB_ENTRY_NAME, temp_dir)
            upload_names = [n for n in archive.namelist() if n.startswith("uploads/")]
            for name in upload_names:
                archive.extract(name, temp_dir)
        extracted_db = temp_dir / DB_ENTRY_NAME
        step("extract_archive", "success", f"{len(upload_names)} belge")

        # 4) Bağlantıları kapat ve dosyayı değiştir
        db.close()
        engine.dispose()

        pre_restore_copy = target_path.with_suffix(".db.pre_restore")
        if target_path.exists():
            shutil.copy2(target_path, pre_restore_copy)
        # WAL/SHM artıklarını temizle
        for suffix in ("-wal", "-shm"):
            leftover = Path(str(target_path) + suffix)
            leftover.unlink(missing_ok=True)

        shutil.copy2(extracted_db, target_path)
        step("restore_database", "success", str(target_path))

        # 5) Belgeleri geri yükle
        uploads_source = temp_dir / "uploads"
        if uploads_source.exists():
            uploads_target = settings.data_path / "uploads"
            uploads_target.mkdir(parents=True, exist_ok=True)
            for file_path in uploads_source.rglob("*"):
                if file_path.is_file():
                    destination = uploads_target / file_path.relative_to(uploads_source)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, destination)
            step("restore_uploads", "success")

        # 6) Bütünlük kontrolü
        connection = sqlite3.connect(str(target_path))
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            healthy = bool(integrity and integrity[0] == "ok")
            student_count = connection.execute(
                "SELECT COUNT(*) FROM students"
            ).fetchone()[0]
        finally:
            connection.close()

        if not healthy:
            raise RuntimeError(
                "Geri yüklenen veritabanı bütünlük kontrolünden geçemedi"
            )
        step("integrity_check", "success", f"öğrenci sayısı: {student_count}")

        # 7) Uygulama sağlığı
        with SessionLocal() as fresh:
            fresh.execute(text("SELECT 1"))
            revision = _db_revision(fresh)
        step("health_check", "success", f"şema sürümü: {revision}")
        pre_restore_copy.unlink(missing_ok=True)

        message = (
            "Geri yükleme tamamlandı. Değişikliklerin tam olarak etkin olması için "
            "uygulamayı yeniden başlatın."
        )
        success = True

    except Exception as exc:  # noqa: BLE001
        logger.exception("Geri yükleme başarısız: %s", backup_id)
        step("restore", "failed", f"{type(exc).__name__}: {exc}")
        # Rollback
        try:
            pre_restore_copy = target_path.with_suffix(".db.pre_restore")
            if pre_restore_copy.exists():
                shutil.copy2(pre_restore_copy, target_path)
                pre_restore_copy.unlink(missing_ok=True)
                rolled_back = True
                step("rollback", "success", "Önceki veritabanı geri yüklendi")
        except Exception as rollback_exc:  # noqa: BLE001
            step("rollback", "failed", str(rollback_exc))
        message = f"Geri yükleme başarısız: {type(exc).__name__}. " + (
            "Sistem önceki durumuna döndürüldü."
            if rolled_back
            else f"Güvenlik yedeği: {safety_id or 'yok'}"
        )
        success = False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    with SessionLocal() as fresh:
        log = fresh.scalar(
            select(RestoreRecord).where(RestoreRecord.id == restore_log.id)
        )
        if log:
            log.status = "success" if success else "failed"
            log.message = message
            log.finished_at = datetime.now(timezone.utc)
            fresh.commit()

    return {
        "success": success,
        "backup_id": backup_id,
        "safety_backup_id": safety_id,
        "message": message,
        "steps": steps,
        "rolled_back": rolled_back,
    }


# ===========================================================================
# Saklama politikası
# ===========================================================================
def apply_retention(
    db: Session,
    *,
    daily: int | None = None,
    weekly: int | None = None,
    monthly: int | None = None,
) -> dict[str, Any]:
    """Saklama politikasını uygular. Korunan yedekler asla silinmez."""
    daily = daily if daily is not None else settings.backup_retention_daily
    weekly = weekly if weekly is not None else settings.backup_retention_weekly
    monthly = monthly if monthly is not None else settings.backup_retention_monthly

    today = date.today()
    records = db.scalars(
        select(BackupRecord)
        .where(BackupRecord.is_protected.is_(False))
        .order_by(BackupRecord.created_at.desc())
    ).all()

    keep: set[int] = set()
    seen_weeks: set[tuple[int, int]] = set()
    seen_months: set[tuple[int, int]] = set()

    for record in records:
        created = record.created_at.date()
        age = (today - created).days

        if age <= daily:
            keep.add(record.id)
            continue
        week_key = (created.isocalendar().year, created.isocalendar().week)
        if age <= weekly * 7 and week_key not in seen_weeks:
            seen_weeks.add(week_key)
            keep.add(record.id)
            continue
        month_key = (created.year, created.month)
        if age <= monthly * 31 and month_key not in seen_months:
            seen_months.add(month_key)
            keep.add(record.id)

    deleted: list[str] = []
    freed_bytes = 0
    provider = get_provider()
    for record in records:
        if record.id in keep:
            continue
        try:
            provider.delete(record.file_path)
            freed_bytes += record.size_bytes
            deleted.append(record.backup_id)
            db.delete(record)
        except Exception:  # noqa: BLE001
            logger.warning("Yedek silinemedi: %s", record.backup_id)

    db.commit()
    logger.info(
        "Saklama politikası: %s yedek silindi (%.2f MB)",
        len(deleted),
        freed_bytes / 1048576,
    )
    return {
        "deleted_count": len(deleted),
        "deleted_ids": deleted,
        "freed_mb": round(freed_bytes / 1048576, 2),
        "kept_count": len(keep),
    }


def backup_status(db: Session) -> dict[str, Any]:
    """Yedekleme ekranı üst bilgi kartı verisi."""
    records = db.scalars(
        select(BackupRecord).order_by(BackupRecord.created_at.desc())
    ).all()
    successful = [
        r
        for r in records
        if r.status in (BackupStatus.COMPLETED, BackupStatus.VERIFIED)
    ]
    last = records[0] if records else None
    last_ok = successful[0] if successful else None

    next_backup = None
    if settings.backup_schedule_enabled and _scheduler is not None:
        jobs = _scheduler.get_jobs()
        if jobs and jobs[0].next_run_time:
            next_backup = jobs[0].next_run_time

    return {
        "last_backup_at": last.created_at if last else None,
        "last_successful_backup_at": last_ok.created_at if last_ok else None,
        "last_backup_size_mb": last_ok.size_mb if last_ok else None,
        "backup_location": str(settings.backup_path),
        "total_backup_count": len(records),
        "total_size_mb": round(sum(r.size_bytes for r in records) / 1048576, 2),
        "protected_count": sum(1 for r in records if r.is_protected),
        "schedule_enabled": settings.backup_schedule_enabled,
        "schedule_cron": settings.backup_schedule_cron,
        "next_backup_at": next_backup,
        "status": (
            "ok"
            if last_ok
            and (
                datetime.now(timezone.utc)
                - last_ok.created_at.replace(tzinfo=timezone.utc)
            ).days
            <= 7
            else "warning" if last_ok else "never"
        ),
    }


# ===========================================================================
# Zamanlayıcı
# ===========================================================================
_scheduler = None


def _scheduled_backup_job() -> None:
    """Zamanlanmış yedekleme görevi."""
    try:
        with SessionLocal() as db:
            record = create_backup(
                db, backup_type=BackupType.SCHEDULED, note="Zamanlanmış otomatik yedek"
            )
            apply_retention(db)
            from app.services.notifications import broadcast

            broadcast(
                db,
                notification_type="backup_result",
                severity=(
                    "success" if record.status == BackupStatus.VERIFIED else "warning"
                ),
                title_tr=f"Otomatik yedek tamamlandı ({record.size_mb} MB)",
                title_en=f"Scheduled backup completed ({record.size_mb} MB)",
                body_tr=record.verification_message,
                role_codes=["system_admin"],
                entity_type="backup",
                entity_id=record.backup_id,
            )
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Zamanlanmış yedekleme başarısız")


def start_backup_scheduler() -> None:
    """APScheduler ile cron tabanlı yedekleme başlatır."""
    global _scheduler
    if not settings.backup_schedule_enabled or _scheduler is not None:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        _scheduler = BackgroundScheduler(timezone=settings.app_timezone)
        _scheduler.add_job(
            _scheduled_backup_job,
            CronTrigger.from_crontab(settings.backup_schedule_cron),
            id="scheduled_backup",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(
            "Yedekleme zamanlayıcısı başlatıldı: %s", settings.backup_schedule_cron
        )
    except Exception:  # noqa: BLE001
        logger.warning("Yedekleme zamanlayıcısı başlatılamadı", exc_info=True)
        _scheduler = None


def stop_backup_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
