"""CAIO Agent — Chief AI Officer.

Akış: Observe -> Analyze -> Propose -> Create Patch -> Test -> Show Diff
      -> User Approval -> Apply

CAIO üretim koduna KENDİ BAŞINA değişiklik yapamaz. Yalnızca gözlem yapar,
bulgu üretir ve öneri sunar. Yama üretimi ve uygulama, AI Developer Console'un
onay akışından geçer.
"""

from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.enums import AITaskKind, AITaskStatus, LessonStatus
from app.models.lesson import Lesson
from app.models.performance import PerformanceRecord
from app.models.system import AITask, BackupRecord, CAIOFinding, SystemEvent
from app.models.user import User
from app.services.ai.base import AIProviderError, ChatMessage
from app.services.ai.prompts import SYSTEM_CAIO
from app.services.ai.registry import finish_task, start_task
from app.services.hsp import gateway as hsp_gateway
from app.services.scheduling import detect_all_conflicts

logger = get_logger("ai")

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


# ===========================================================================
# OBSERVE — ölçülebilir gerçekler
# ===========================================================================
def _observe_logs() -> dict[str, Any]:
    """Log dosyalarını tarayarak hata sınıflandırması yapar."""
    observations: dict[str, Any] = {
        "log_files": [],
        "error_count": 0,
        "warning_count": 0,
        "top_errors": [],
    }
    if not settings.log_path.exists():
        return observations

    error_signatures: dict[str, int] = {}
    for log_file in settings.log_path.glob("*.log"):
        try:
            size = log_file.stat().st_size
            # Yalnızca son 400 KB'ı oku (büyük log dosyalarında bellek koruması)
            with log_file.open("r", encoding="utf-8", errors="replace") as handle:
                if size > 400_000:
                    handle.seek(size - 400_000)
                    handle.readline()
                lines = handle.readlines()
        except OSError:
            continue

        errors = sum(1 for line in lines if "ERROR" in line or "CRITICAL" in line)
        warnings = sum(1 for line in lines if "WARNING" in line)
        observations["error_count"] += errors
        observations["warning_count"] += warnings
        observations["log_files"].append(
            {
                "name": log_file.name,
                "size_kb": round(size / 1024, 1),
                "errors": errors,
                "warnings": warnings,
            }
        )

        for line in lines:
            if "ERROR" not in line and "CRITICAL" not in line:
                continue
            # İmza: hata tipini normalize et (sayıları ve yolları çıkar)
            signature = re.sub(r"\d+", "N", line.split("|")[-1].strip())[:140]
            error_signatures[signature] = error_signatures.get(signature, 0) + 1

    observations["top_errors"] = [
        {"signature": signature, "count": count}
        for signature, count in sorted(error_signatures.items(), key=lambda kv: -kv[1])[
            :10
        ]
    ]
    return observations


def _observe_ai_usage(db: Session) -> dict[str, Any]:
    """AI kullanımı, maliyeti ve yerel/bulut dağılımı."""
    tasks = db.scalars(select(AITask)).all()
    if not tasks:
        return {
            "total_tasks": 0,
            "success_rate": None,
            "local_ratio": None,
            "total_tokens": 0,
            "avg_duration_ms": None,
            "failed_24h": 0,
        }

    successful = [t for t in tasks if t.status == AITaskStatus.SUCCESS]
    local_tasks = [t for t in successful if t.provider == "local"]
    cloud_tasks = [t for t in successful if t.provider and t.provider != "local"]
    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)

    return {
        "total_tasks": len(tasks),
        "successful": len(successful),
        "failed": sum(1 for t in tasks if t.status == AITaskStatus.FAILED),
        "failed_24h": sum(
            1
            for t in tasks
            if t.status == AITaskStatus.FAILED
            and t.started_at.replace(tzinfo=timezone.utc) >= day_ago
        ),
        "success_rate": round(len(successful) / len(tasks) * 100, 1),
        "local_ratio": (
            round(len(local_tasks) / len(successful) * 100, 1) if successful else None
        ),
        "cloud_task_count": len(cloud_tasks),
        "cloud_tokens": sum(t.total_tokens for t in cloud_tasks),
        "total_tokens": sum(t.total_tokens for t in tasks),
        "avg_duration_ms": (
            round(sum(t.duration_ms for t in successful) / len(successful))
            if successful
            else None
        ),
        "fallback_count": sum(1 for t in tasks if t.fallback_used),
        "by_kind": {
            kind: sum(1 for t in tasks if t.kind == kind)
            for kind in {t.kind for t in tasks}
        },
    }


def _observe_code_quality() -> dict[str, Any]:
    """Kod tabanı ve test kapsamı göstergeleri."""
    root = settings.project_root
    backend_files = (
        list((root / "backend" / "app").rglob("*.py"))
        if (root / "backend" / "app").exists()
        else []
    )
    test_files = (
        list((root / "backend" / "tests").rglob("test_*.py"))
        if (root / "backend" / "tests").exists()
        else []
    )
    frontend_files = (
        list((root / "frontend" / "src").rglob("*.ts"))
        + list((root / "frontend" / "src").rglob("*.tsx"))
        if (root / "frontend" / "src").exists()
        else []
    )

    total_lines = 0
    todo_count = 0
    long_files: list[dict[str, Any]] = []
    for path in backend_files:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        total_lines += len(lines)
        todo_count += sum(
            1 for line in lines if "TODO" in line or "FIXME" in line or "XXX" in line
        )
        if len(lines) > 700:
            long_files.append(
                {"path": path.relative_to(root).as_posix(), "lines": len(lines)}
            )

    # Test edilen modülleri kabaca eşle
    tested_modules = set()
    for path in test_files:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tested_modules.update(re.findall(r"from app\.([\w.]+) import", content))

    service_modules = {
        f"services.{p.stem}"
        for p in (root / "backend" / "app" / "services").glob("*.py")
        if p.stem != "__init__"
    }
    untested = sorted(service_modules - {m for m in tested_modules})

    return {
        "backend_file_count": len(backend_files),
        "backend_line_count": total_lines,
        "frontend_file_count": len(frontend_files),
        "test_file_count": len(test_files),
        "test_to_source_ratio": (
            round(len(test_files) / len(backend_files) * 100, 1) if backend_files else 0
        ),
        "todo_count": todo_count,
        "long_files": sorted(long_files, key=lambda f: -f["lines"])[:10],
        "untested_services": untested[:15],
    }


def _observe_database(db: Session) -> dict[str, Any]:
    """Veri hacmi ve veri kalitesi göstergeleri."""
    from app.models import Attendance, Invoice, Payment, Student

    from app.models.enums import StudentStatus

    student_count = db.scalar(select(func.count(Student.id))) or 0
    lesson_count = db.scalar(select(func.count(Lesson.id))) or 0

    # Veri kalitesi: eksik alanlar
    missing_birth_date = (
        db.scalar(select(func.count(Student.id)).where(Student.birth_date.is_(None)))
        or 0
    )
    missing_contact = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.phone.is_(None), Student.email.is_(None)
            )
        )
        or 0
    )
    no_consent = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.consent_given.is_(False), Student.status == StudentStatus.ACTIVE
            )
        )
        or 0
    )

    # Yoklaması alınmamış geçmiş dersler
    lessons_without_attendance = (
        db.scalar(
            select(func.count(Lesson.id)).where(
                Lesson.end_at < datetime.now(),
                Lesson.status != LessonStatus.CANCELLED,
                ~Lesson.id.in_(select(Attendance.lesson_id).distinct()),
            )
        )
        or 0
    )

    # Yaklaşan/geçmiş çakışmalar
    conflicts = detect_all_conflicts(
        db,
        date_from=date.today() - timedelta(days=7),
        date_to=date.today() + timedelta(days=30),
    )

    db_size_mb = None
    from app.db.session import database_file_path

    if (path := database_file_path()) and Path(path).exists():
        db_size_mb = round(Path(path).stat().st_size / 1048576, 2)

    return {
        "student_count": student_count,
        "lesson_count": lesson_count,
        "attendance_count": db.scalar(select(func.count(Attendance.id))) or 0,
        "payment_count": db.scalar(select(func.count(Payment.id))) or 0,
        "invoice_count": db.scalar(select(func.count(Invoice.id))) or 0,
        "performance_record_count": db.scalar(select(func.count(PerformanceRecord.id)))
        or 0,
        "database_size_mb": db_size_mb,
        "data_quality": {
            "missing_birth_date": missing_birth_date,
            "missing_contact": missing_contact,
            "active_without_consent": no_consent,
            "lessons_without_attendance": lessons_without_attendance,
        },
        "schedule_conflicts": len(conflicts),
        "conflict_samples": conflicts[:5],
    }


def _observe_security(db: Session) -> dict[str, Any]:
    """Güvenlik göstergeleri."""
    from app.models.user import LoginAttempt

    day_ago = datetime.now() - timedelta(hours=24)
    failed_logins = (
        db.scalar(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.successful.is_(False), LoginAttempt.attempted_at >= day_ago
            )
        )
        or 0
    )
    locked_users = (
        db.scalar(select(func.count(User.id)).where(User.locked_until.is_not(None)))
        or 0
    )
    default_password_users = (
        db.scalar(
            select(func.count(User.id)).where(User.must_change_password.is_(True))
        )
        or 0
    )
    superusers = (
        db.scalar(select(func.count(User.id)).where(User.is_superuser.is_(True))) or 0
    )

    env_file = settings.project_root / ".env"
    gitignore = settings.project_root / ".gitignore"
    env_ignored = False
    if gitignore.exists():
        env_ignored = ".env" in gitignore.read_text(encoding="utf-8", errors="replace")

    return {
        "failed_logins_24h": failed_logins,
        "locked_accounts": locked_users,
        "users_must_change_password": default_password_users,
        "superuser_count": superusers,
        "env_file_exists": env_file.exists(),
        "env_git_ignored": env_ignored,
        "debug_mode": settings.app_debug,
        "is_production": settings.is_production,
        "shell_access_enabled": settings.ai_developer_allow_shell,
        "patch_apply_enabled": settings.ai_developer_allow_apply,
        "prompt_logging_enabled": settings.ai_log_prompts,
    }


def _observe_backups(db: Session) -> dict[str, Any]:
    from app.models.enums import BackupStatus

    records = db.scalars(
        select(BackupRecord).order_by(BackupRecord.created_at.desc())
    ).all()
    verified = [r for r in records if r.status == BackupStatus.VERIFIED]
    last = verified[0] if verified else None
    days_since = (
        (datetime.now(timezone.utc) - last.created_at.replace(tzinfo=timezone.utc)).days
        if last
        else None
    )
    return {
        "total_backups": len(records),
        "verified_backups": len(verified),
        "corrupted_backups": sum(
            1 for r in records if r.status == BackupStatus.CORRUPTED
        ),
        "days_since_last_backup": days_since,
        "schedule_enabled": settings.backup_schedule_enabled,
        "total_size_mb": round(sum(r.size_bytes for r in records) / 1048576, 2),
    }


def observe(db: Session) -> dict[str, Any]:
    """Tüm gözlemleri toplar."""
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "logs": _observe_logs(),
        "ai_usage": _observe_ai_usage(db),
        "code_quality": _observe_code_quality(),
        "database": _observe_database(db),
        "security": _observe_security(db),
        "backups": _observe_backups(db),
    }


# ===========================================================================
# ANALYZE — kural tabanlı bulgular (AI'sız da çalışır)
# ===========================================================================
def analyze(observations: dict[str, Any]) -> list[dict[str, Any]]:
    """Gözlemlerden deterministik bulgular üretir."""
    findings: list[dict[str, Any]] = []

    def add(
        category: str,
        severity: str,
        title: str,
        description: str,
        recommendation: str,
        evidence: dict[str, Any],
    ) -> None:
        findings.append(
            {
                "category": category,
                "severity": severity,
                "title": title,
                "description": description,
                "recommendation": recommendation,
                "evidence": evidence,
                "source": "rule_engine",
            }
        )

    security = observations["security"]
    backups = observations["backups"]
    quality = observations["code_quality"]
    database = observations["database"]
    ai_usage = observations["ai_usage"]
    logs = observations["logs"]

    # --- Güvenlik ---
    if security["env_file_exists"] and not security["env_git_ignored"]:
        add(
            "security",
            "critical",
            ".env dosyası Git tarafından yok sayılmıyor",
            "Ortam dosyası sürüm kontrolüne girebilir; API anahtarları ve gizli anahtar sızabilir.",
            ".gitignore dosyasına `.env` satırını ekleyin ve `git rm --cached .env` çalıştırın.",
            {"env_git_ignored": False},
        )
    if security["is_production"] and security["debug_mode"]:
        add(
            "security",
            "high",
            "Üretim ortamında hata ayıklama modu açık",
            "APP_DEBUG=true üretimde ayrıntılı hata mesajları sızdırabilir.",
            ".env dosyasında APP_DEBUG=false yapın.",
            {"debug_mode": True},
        )
    if security["users_must_change_password"] > 0:
        add(
            "security",
            "medium",
            f"{security['users_must_change_password']} kullanıcı varsayılan parolayı değiştirmemiş",
            "Varsayılan parolalar yetkisiz erişim riski oluşturur.",
            "İlgili kullanıcılara parola değiştirmelerini hatırlatın.",
            {"count": security["users_must_change_password"]},
        )
    if security["failed_logins_24h"] > 20:
        add(
            "security",
            "high",
            f"Son 24 saatte {security['failed_logins_24h']} başarısız giriş denemesi",
            "Kaba kuvvet saldırısı işareti olabilir.",
            "security.log dosyasını inceleyin; gerekirse IP kısıtlaması ekleyin.",
            {"failed_logins_24h": security["failed_logins_24h"]},
        )
    if security["shell_access_enabled"]:
        add(
            "security",
            "medium",
            "AI geliştirici kabuk erişimi açık",
            "Yapay zekâ ajanının komut çalıştırma yetkisi etkin. Politika beyaz listesi devrede olsa da risk artar.",
            "Aktif geliştirme yapmıyorsanız AI_DEVELOPER_ALLOW_SHELL=false yapın.",
            {"shell_access_enabled": True},
        )
    if security["superuser_count"] > 3:
        add(
            "security",
            "low",
            f"{security['superuser_count']} süper kullanıcı tanımlı",
            "Tam yetkili hesap sayısının fazla olması saldırı yüzeyini büyütür.",
            "Süper kullanıcı sayısını en aza indirin; rol bazlı yetkilendirme kullanın.",
            {"superuser_count": security["superuser_count"]},
        )

    # --- Yedekleme ---
    if backups["total_backups"] == 0:
        add(
            "backup",
            "high",
            "Hiç yedek alınmamış",
            "Veri kaybı durumunda geri dönüş noktası yok.",
            "Ayarlar > Yedekleme bölümünden hemen yedek alın ve otomatik yedeklemeyi açın.",
            {"total_backups": 0},
        )
    elif (
        backups["days_since_last_backup"] is not None
        and backups["days_since_last_backup"] > 7
    ):
        add(
            "backup",
            "medium",
            f"Son doğrulanmış yedek {backups['days_since_last_backup']} gün önce",
            "Yedekler güncel değil.",
            "Otomatik yedeklemeyi etkinleştirin (BACKUP_SCHEDULE_ENABLED=true).",
            {"days_since_last_backup": backups["days_since_last_backup"]},
        )
    if backups["corrupted_backups"] > 0:
        add(
            "backup",
            "high",
            f"{backups['corrupted_backups']} bozuk yedek tespit edildi",
            "Bozuk yedekler geri yükleme sırasında kullanılamaz.",
            "Bozuk yedekleri silin ve yeni bir yedek oluşturup doğrulayın.",
            {"corrupted": backups["corrupted_backups"]},
        )

    # --- Test kapsamı ---
    if quality["test_to_source_ratio"] < 10:
        add(
            "testing",
            "medium",
            f"Test/kaynak oranı düşük (%{quality['test_to_source_ratio']})",
            "Düşük test kapsamı regresyon riskini artırır.",
            "Öncelikle iş kuralı içeren servisler için test yazın.",
            {
                "ratio": quality["test_to_source_ratio"],
                "test_files": quality["test_file_count"],
            },
        )
    if quality["untested_services"]:
        add(
            "testing",
            "medium",
            f"{len(quality['untested_services'])} servis modülü test edilmemiş görünüyor",
            "Bu modüllerde hata tespit edilmeden üretime çıkabilir.",
            "Öncelik sırası: " + ", ".join(quality["untested_services"][:5]),
            {"untested": quality["untested_services"]},
        )

    # --- Teknik borç ---
    if quality["todo_count"] > 20:
        add(
            "technical_debt",
            "low",
            f"Kodda {quality['todo_count']} adet TODO/FIXME notu",
            "Biriken teknik borç bakım maliyetini artırır.",
            "TODO'ları görev listesine dönüştürüp önceliklendirin.",
            {"todo_count": quality["todo_count"]},
        )
    if quality["long_files"]:
        add(
            "technical_debt",
            "low",
            f"{len(quality['long_files'])} dosya 700 satırı aşıyor",
            "Uzun dosyalar okunabilirliği ve test edilebilirliği düşürür.",
            "En uzun dosyaları modüllere bölmeyi değerlendirin: "
            + ", ".join(f["path"] for f in quality["long_files"][:3]),
            {"long_files": quality["long_files"][:5]},
        )

    # --- Hatalar ---
    if logs["error_count"] > 50:
        add(
            "reliability",
            "high",
            f"Loglarda {logs['error_count']} hata kaydı",
            "Yüksek hata sayısı kararlılık sorununa işaret eder.",
            "En sık hatayı önceliklendirin: "
            + (logs["top_errors"][0]["signature"][:100] if logs["top_errors"] else "-"),
            {"error_count": logs["error_count"], "top_errors": logs["top_errors"][:3]},
        )
    elif logs["error_count"] > 10:
        add(
            "reliability",
            "medium",
            f"Loglarda {logs['error_count']} hata kaydı",
            "Tekrarlayan hatalar var.",
            "application.log ve database.log dosyalarını inceleyin.",
            {"error_count": logs["error_count"]},
        )

    # --- Veri kalitesi ---
    quality_data = database["data_quality"]
    if quality_data["lessons_without_attendance"] > 5:
        add(
            "data_quality",
            "medium",
            f"{quality_data['lessons_without_attendance']} geçmiş derste yoklama alınmamış",
            "Eksik yoklama, devam istatistiklerini ve ders hakkı düşümünü bozar.",
            "Yoklama ekranından eksik dersleri tamamlayın.",
            {"count": quality_data["lessons_without_attendance"]},
        )
    if quality_data["active_without_consent"] > 0:
        add(
            "compliance",
            "medium",
            f"{quality_data['active_without_consent']} aktif öğrencide KVKK onayı yok",
            "Kişisel veri işleme için açık rıza kaydı bulunmuyor.",
            "Öğrenci kayıtlarında aydınlatma onayını tamamlayın.",
            {"count": quality_data["active_without_consent"]},
        )
    if database["schedule_conflicts"] > 0:
        add(
            "operations",
            "high",
            f"Takvimde {database['schedule_conflicts']} çakışma tespit edildi",
            "Aynı eğitmen veya kulvar birden fazla derse atanmış.",
            "Takvim ekranından çakışan dersleri düzeltin.",
            {"conflicts": database["conflict_samples"]},
        )

    # --- AI kullanımı ---
    if ai_usage["total_tasks"] > 0:
        if ai_usage["success_rate"] is not None and ai_usage["success_rate"] < 70:
            add(
                "ai_quality",
                "medium",
                f"AI görev başarı oranı düşük (%{ai_usage['success_rate']})",
                "Sağlayıcı erişilebilirliği veya model uyumu sorunlu olabilir.",
                "AI Merkezi > Bağlantı Testi çalıştırın; gerekirse fallback zincirini düzenleyin.",
                {
                    "success_rate": ai_usage["success_rate"],
                    "failed": ai_usage["failed"],
                },
            )
        if (
            ai_usage["local_ratio"] is not None
            and ai_usage["local_ratio"] < 50
            and ai_usage["cloud_tokens"] > 50_000
        ):
            add(
                "cost",
                "low",
                f"Bulut AI kullanımı yüksek (yerel oran %{ai_usage['local_ratio']})",
                f"Bulut sağlayıcıya {ai_usage['cloud_tokens']:,} token gönderilmiş. "
                "Maliyet ve gizlilik açısından yerel model tercih edilebilir.",
                "Rutin analizler için AI modunu 'local' yapın; yalnızca karmaşık görevlerde buluta düşün.",
                {
                    "local_ratio": ai_usage["local_ratio"],
                    "cloud_tokens": ai_usage["cloud_tokens"],
                },
            )
        if ai_usage["failed_24h"] > 5:
            add(
                "ai_quality",
                "medium",
                f"Son 24 saatte {ai_usage['failed_24h']} AI görevi başarısız",
                "Sağlayıcı bağlantısı kesik olabilir (ör. LM Studio kapalı).",
                "LM Studio sunucusunun çalıştığını doğrulayın veya bulut sağlayıcıyı etkinleştirin.",
                {"failed_24h": ai_usage["failed_24h"]},
            )

    findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 9))
    return findings


# ===========================================================================
# PROPOSE — AI yorumu (isteğe bağlı)
# ===========================================================================
def run_caio(
    db: Session,
    *,
    include_ai: bool = True,
    provider: str = "auto",
    user_id: int | None = None,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """CAIO döngüsünü çalıştırır: Observe -> Analyze -> Propose."""
    started = time.perf_counter()
    observations = observe(db)
    findings_data = analyze(observations)

    if categories:
        findings_data = [f for f in findings_data if f["category"] in categories]

    # Bulguları kaydet (aynı başlık açıksa yinelenmez)
    stored: list[CAIOFinding] = []
    now = datetime.now(timezone.utc)
    for data in findings_data:
        existing = db.scalar(
            select(CAIOFinding).where(
                CAIOFinding.title == data["title"], CAIOFinding.status == "open"
            )
        )
        if existing:
            existing.evidence = data["evidence"]
            existing.description = data["description"]
            stored.append(existing)
            continue
        finding = CAIOFinding(**data, is_ai_generated=False, created_at=now)
        db.add(finding)
        stored.append(finding)
    db.commit()

    severity_counts: dict[str, int] = {}
    for finding in stored:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

    report: dict[str, Any] = {
        "run_at": now,
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "observations": observations,
        "findings": stored,
        "findings_by_severity": severity_counts,
        "ai_available": False,
        "ai_summary": None,
        "ai_proposals": [],
        "provider": None,
    }

    if not include_ai:
        return report

    # --- AI yorumu ---
    task = start_task(
        db, kind=AITaskKind.CAIO, title="CAIO analiz döngüsü", user_id=user_id
    )
    summary_input = {
        "observations": {
            "logs": observations["logs"],
            "ai_usage": observations["ai_usage"],
            "code_quality": {
                key: value
                for key, value in observations["code_quality"].items()
                if key != "long_files"
            },
            "database": {
                key: value
                for key, value in observations["database"].items()
                if key != "conflict_samples"
            },
            "security": observations["security"],
            "backups": observations["backups"],
        },
        "rule_findings": [
            {"severity": f["severity"], "category": f["category"], "title": f["title"]}
            for f in findings_data
        ],
    }

    prompt = (
        "Aşağıda bir yüzme okulu yönetim yazılımının ÖLÇÜLMÜŞ sistem verileri ve "
        "kural motorunun ürettiği bulgular var.\n\n"
        f"{json.dumps(summary_input, ensure_ascii=False, default=str)[:8000]}\n\n"
        "GÖREV:\n"
        "1. Bu verilerden bir yönetici özeti yaz (en fazla 5 cümle).\n"
        "2. Kural motorunun KAÇIRDIĞI, verilerden çıkarılabilecek en fazla 5 ek öneri üret.\n"
        "3. Her öneriyi '- ' ile başlayan tek satırda, önceliğiyle birlikte yaz.\n\n"
        "BİÇİM:\n"
        "## Özet\n(metin)\n\n## Ek Öneriler\n- (öneri)\n"
    )

    try:
        # CAIO çağrısı da HSP geçidinden geçer: yalnızca toplulaştırılmış
        # ölçümler gönderilir, ama karar + hak makbuzu yine üretilir.
        outcome = hsp_gateway.chat(
            db,
            [
                ChatMessage(role="system", content=SYSTEM_CAIO),
                ChatMessage(role="user", content=prompt),
            ],
            operation="ai.caio.report",
            field_paths=[],
            preferred=provider,
            temperature=0.2,
            task="reasoning",
        )
        if outcome.blocked or outcome.result is None:
            raise AIProviderError(outcome.refusal_message())
        result = outcome.result
        attempted = outcome.attempted
        fallback_used = outcome.fallback_used
        content = result.content
        summary_part, proposals = content, []
        if "## Ek Öneriler" in content or "Ek Öneriler" in content:
            marker = "## Ek Öneriler" if "## Ek Öneriler" in content else "Ek Öneriler"
            summary_part, _, proposal_text = content.partition(marker)
            proposals = [
                line.lstrip("-•* ").strip()
                for line in proposal_text.splitlines()
                if line.strip().startswith(("-", "•", "*"))
            ][:5]

        report["ai_available"] = True
        report["ai_summary"] = summary_part.replace("## Özet", "").strip()[:2000]
        report["ai_proposals"] = proposals
        report["provider"] = result.provider

        # AI önerilerini de bulgu olarak kaydet (öneri statüsünde)
        for proposal in proposals:
            if db.scalar(
                select(CAIOFinding).where(
                    CAIOFinding.title == proposal[:280], CAIOFinding.status == "open"
                )
            ):
                continue
            db.add(
                CAIOFinding(
                    category="ai_suggestion",
                    severity="info",
                    title=proposal[:280],
                    description=proposal,
                    recommendation=proposal,
                    evidence={"source": "ai", "provider": result.provider},
                    source="ai",
                    status="open",
                    is_ai_generated=True,
                    ai_provider=result.provider,
                    created_at=now,
                )
            )
        db.commit()
        finish_task(
            db, task, result=result, attempted=attempted, fallback_used=fallback_used
        )

    except AIProviderError as exc:
        logger.info("CAIO AI yorumu atlandı (sağlayıcı yok): %s", exc)
        finish_task(db, task, error=str(exc))

    db.add(
        SystemEvent(
            event_type="caio_run",
            severity="info",
            message=f"CAIO analizi tamamlandı: {len(stored)} bulgu",
            details={"severity_counts": severity_counts, "ai": report["ai_available"]},
            occurred_at=now,
        )
    )
    db.commit()

    # Yeniden sorgula ki ilişkiler tazelensin
    report["findings"] = db.scalars(
        select(CAIOFinding)
        .where(CAIOFinding.status == "open")
        .order_by(CAIOFinding.created_at.desc())
    ).all()
    return report
