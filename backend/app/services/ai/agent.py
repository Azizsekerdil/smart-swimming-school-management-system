"""AI geliştirici ajanı / AI developer agent.

Akış:
    READ -> SEARCH -> ANALYZE -> PLAN -> GENERATE PATCH -> RUN TEST
         -> SHOW DIFF -> [KULLANICI ONAYI] -> APPLY PATCH -> ROLLBACK

Güvenlik:
  * Tüm dosya erişimi `CommandPolicy` üzerinden geçer (proje dışına çıkılamaz).
  * Yama uygulanmadan önce otomatik checkpoint (yedek) alınır.
  * `AI_DEVELOPER_ALLOW_APPLY=false` iken yalnızca öneri üretilir, yazma yapılmaz.
"""

from __future__ import annotations

import difflib
import json
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import SecurityPolicyError, ValidationError
from app.core.logging_config import get_logger
from app.models.enums import AITaskKind
from app.schemas.ai import AgentStep, DeveloperPlanResponse, FileChange
from app.services.ai.base import AIProviderError, ChatMessage
from app.services.ai.policy import policy
from app.services.ai.prompts import SYSTEM_DEVELOPER
from app.services.ai.registry import finish_task, start_task
from app.services.hsp import gateway as hsp_gateway

logger = get_logger("developer-agent")

CHECKPOINT_DIR = settings.project_root / ".ai_checkpoints"
PATCH_DIR = settings.project_root / "tools" / "ai_developer" / "patches"

# Kimlikler yalnızca üretildikleri biçimde kabul edilir. Serbest metin kabul
# edilseydi `../../` ya da mutlak yol ile dizin dışına çıkılabilirdi (traversal).
_CHECKPOINT_ID_RE = re.compile(r"^ckpt_\d{8}_\d{6}_[0-9a-f]{6}$")
_PATCH_ID_RE = re.compile(r"^patch_\d{8}_\d{6}_[0-9a-f]{6}$")


def _validate_id(value: str, pattern: re.Pattern[str], kind: str) -> str:
    """Kimliği doğrular; geçersizse dosya sistemine hiç dokunulmaz."""
    if not isinstance(value, str) or not pattern.match(value):
        raise ValidationError(details={"reason": f"invalid_{kind}_id"})
    return value


MAX_FILE_BYTES = 200_000
MAX_CONTEXT_CHARS = 60_000

# Ajanın arama yapacağı dizinler
SEARCHABLE_DIRS = ("backend/app", "frontend/src", "scripts", "docs", "backend/tests")


# ===========================================================================
# Dosya işlemleri (politika korumalı)
# ===========================================================================
def read_file(relative_path: str) -> str:
    decision = policy.can_read(relative_path)
    if not decision.allowed:
        raise SecurityPolicyError(
            "ai.path_outside_project", details={"reason": decision.reason}
        )
    path = policy.resolve_path(relative_path)
    if not path.exists() or not path.is_file():
        raise ValidationError(
            details={"reason": "file_not_found", "path": relative_path}
        )
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValidationError(
            details={"reason": "file_too_large", "path": relative_path}
        )
    return path.read_text(encoding="utf-8", errors="replace")


def list_project_files(pattern: str = "*.py", limit: int = 400) -> list[str]:
    """Proje içindeki kaynak dosyalarını listeler."""
    results: list[str] = []
    for directory in SEARCHABLE_DIRS:
        base = policy.project_root / directory
        if not base.exists():
            continue
        for path in base.rglob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(policy.project_root).as_posix()
            if policy.can_read(relative).allowed:
                results.append(relative)
            if len(results) >= limit:
                return sorted(results)
    return sorted(results)


def search_in_files(
    query: str, pattern: str = "*.py", limit: int = 60
) -> list[dict[str, Any]]:
    """Kaynak kodda metin arar (grep benzeri)."""
    hits: list[dict[str, Any]] = []
    needle = query.lower()
    for relative in list_project_files(pattern, limit=600):
        try:
            content = read_file(relative)
        except Exception:  # noqa: BLE001
            continue
        for number, line in enumerate(content.splitlines(), start=1):
            if needle in line.lower():
                hits.append(
                    {"path": relative, "line": number, "text": line.strip()[:200]}
                )
                if len(hits) >= limit:
                    return hits
    return hits


def make_diff(path: str, original: str, updated: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )


def diff_stats(diff_text: str) -> tuple[int, int]:
    added = sum(
        1
        for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1
        for line in diff_text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    return added, removed


# ===========================================================================
# Checkpoint (geri alma)
# ===========================================================================
def create_checkpoint(paths: list[str], label: str = "") -> str:
    """Değiştirilecek dosyaların yedeğini alır ve checkpoint kimliği döndürür."""
    checkpoint_id = (
        f"ckpt_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    )
    target = CHECKPOINT_DIR / checkpoint_id
    target.mkdir(parents=True, exist_ok=True)

    manifest = {
        "checkpoint_id": checkpoint_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "files": [],
    }
    for relative in paths:
        source = policy.resolve_path(relative)
        if source.exists():
            destination = target / relative.replace("/", "__").replace("\\", "__")
            shutil.copy2(source, destination)
            manifest["files"].append(
                {"path": relative, "stored_as": destination.name, "existed": True}
            )
        else:
            manifest["files"].append(
                {"path": relative, "stored_as": None, "existed": False}
            )

    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Checkpoint oluşturuldu: %s (%s dosya)", checkpoint_id, len(paths))
    return checkpoint_id


def rollback_checkpoint(checkpoint_id: str) -> dict[str, Any]:
    """Checkpoint'e geri döner."""
    checkpoint_id = _validate_id(checkpoint_id, _CHECKPOINT_ID_RE, "checkpoint")
    target = CHECKPOINT_DIR / checkpoint_id
    manifest_path = target / "manifest.json"
    if not manifest_path.exists():
        raise ValidationError(
            details={"reason": "checkpoint_not_found", "id": checkpoint_id}
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored: list[str] = []
    removed: list[str] = []

    for entry in manifest["files"]:
        destination = policy.resolve_path(entry["path"])
        if entry["existed"] and entry["stored_as"]:
            shutil.copy2(target / entry["stored_as"], destination)
            restored.append(entry["path"])
        elif not entry["existed"] and destination.exists():
            # Ajan tarafından oluşturulan dosyayı kaldır
            destination.unlink()
            removed.append(entry["path"])

    logger.info(
        "Rollback: %s (%s geri yüklendi, %s silindi)",
        checkpoint_id,
        len(restored),
        len(removed),
    )
    return {
        "checkpoint_id": checkpoint_id,
        "restored": restored,
        "removed": removed,
        "label": manifest.get("label"),
    }


def list_checkpoints(limit: int = 30) -> list[dict[str, Any]]:
    if not CHECKPOINT_DIR.exists():
        return []
    entries: list[dict[str, Any]] = []
    for directory in sorted(CHECKPOINT_DIR.iterdir(), reverse=True)[:limit]:
        manifest_path = directory / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                entries.append(
                    {
                        "checkpoint_id": manifest["checkpoint_id"],
                        "created_at": manifest["created_at"],
                        "label": manifest.get("label", ""),
                        "file_count": len(manifest.get("files", [])),
                    }
                )
            except (ValueError, KeyError):
                continue
    return entries


# ===========================================================================
# Test çalıştırma
# ===========================================================================
def run_tests(target: str = "backend/tests", timeout: int = 300) -> dict[str, Any]:
    """Testleri çalıştırır. Kabuk politikası kapalıysa da testler çalıştırılabilir
    (sabit, güvenli komut; kullanıcı girdisi komuta enjekte edilmez)."""
    python_executable = settings.project_root / ".venv" / "Scripts" / "python.exe"
    if not python_executable.exists():
        python_executable = Path("python")

    command = [
        str(python_executable),
        "-m",
        "pytest",
        target,
        "-q",
        "--tb=short",
        "--no-header",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(  # noqa: S603 - sabit komut listesi, shell=False
            command,
            cwd=str(settings.project_root / "backend"),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        output = (completed.stdout or "") + (completed.stderr or "")

        passed = failed = 0
        if match := re.search(r"(\d+)\s+passed", output):
            passed = int(match.group(1))
        if match := re.search(r"(\d+)\s+failed", output):
            failed = int(match.group(1))

        return {
            "success": completed.returncode == 0,
            "return_code": completed.returncode,
            "passed": passed,
            "failed": failed,
            "duration_ms": duration_ms,
            "output": output[-4000:],
            "command": " ".join(command[1:]),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "return_code": -1,
            "passed": 0,
            "failed": 0,
            "duration_ms": timeout * 1000,
            "output": f"Test zaman aşımına uğradı ({timeout}s)",
            "command": " ".join(command[1:]),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "success": False,
            "return_code": -1,
            "passed": 0,
            "failed": 0,
            "duration_ms": 0,
            "output": f"{type(exc).__name__}: {exc}",
            "command": " ".join(command[1:]),
        }


def run_shell(command: str, timeout: int = 120) -> dict[str, Any]:
    """Politika denetiminden geçen kabuk komutunu çalıştırır."""
    decision = policy.check_command(command)
    if not decision.allowed:
        raise SecurityPolicyError(
            "ai.command_blocked", details={"reason": decision.reason}
        )

    import shlex

    parts = shlex.split(command, posix=False)
    started = time.perf_counter()
    try:
        completed = subprocess.run(  # noqa: S603 - politika beyaz listesinden geçti, shell=False
            parts,
            cwd=str(policy.project_root),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "success": completed.returncode == 0,
            "return_code": completed.returncode,
            "output": ((completed.stdout or "") + (completed.stderr or ""))[-4000:],
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "command": command,
            "policy_reason": decision.reason,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "return_code": -1,
            "output": f"Komut zaman aşımına uğradı ({timeout}s)",
            "duration_ms": timeout * 1000,
            "command": command,
        }


# ===========================================================================
# Yama üretimi
# ===========================================================================
PATCH_SCHEMA_HINT = """
Yanıtını YALNIZCA aşağıdaki JSON şemasında döndür (başka metin ekleme):

{
  "analysis": "Mevcut durumun kısa analizi",
  "plan": ["adım 1", "adım 2"],
  "changes": [
    {
      "path": "backend/app/api/v1/students.py",
      "action": "modify",
      "new_content": "DOSYANIN TAM YENİ İÇERİĞİ"
    }
  ],
  "warnings": ["dikkat edilmesi gereken nokta"],
  "test_command": "backend/tests/test_students.py"
}

KURALLAR:
- "action" yalnızca "create" veya "modify" olabilir. Dosya SİLME önerme.
- "new_content" dosyanın TAMAMINI içermelidir (parça değil).
- En fazla {max_files} dosya değiştir.
- Yalnızca sana gösterilen dosyaları veya yeni dosya oluştur.
"""


def _extract_json(text: str) -> dict[str, Any]:
    """AI yanıtından JSON nesnesini çıkarır."""
    cleaned = text.strip()
    if "```" in cleaned:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
        if blocks:
            cleaned = blocks[0].strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("JSON bulunamadı")
    return json.loads(cleaned[start : end + 1])


def _gather_context(instruction: str, max_files: int) -> tuple[str, list[str]]:
    """İstemle ilgili dosyaları bulur ve bağlam metni oluşturur."""
    # İstemden anahtar kelimeleri çıkar
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-zçğıöşüÇĞİÖŞÜ_]{4,}", instruction)
        if word.lower()
        not in {
            "için",
            "ekle",
            "yeni",
            "sonra",
            "olsun",
            "yapmak",
            "bunu",
            "şunu",
            "modül",
            "modülü",
            "dosya",
            "kodu",
            "kod",
            "ekran",
            "ekrana",
            "add",
            "create",
            "update",
            "make",
            "this",
            "that",
            "file",
            "code",
        }
    ][:8]

    scored: dict[str, int] = {}
    all_files = list_project_files("*.py", limit=600) + list_project_files(
        "*.ts*", limit=400
    )
    for relative in all_files:
        score = sum(3 for word in words if word in relative.lower())
        if score:
            scored[relative] = score

    # Dosya adında eşleşme yoksa içerikte ara
    if len(scored) < 3 and words:
        for hit in search_in_files(words[0], "*.py", limit=40):
            scored[hit["path"]] = scored.get(hit["path"], 0) + 1

    ranked = sorted(scored.items(), key=lambda kv: -kv[1])[:max_files]
    selected = [path for path, _ in ranked]

    parts: list[str] = []
    total = 0
    for relative in selected:
        try:
            content = read_file(relative)
        except Exception:  # noqa: BLE001
            continue
        block = f"\n===== DOSYA: {relative} =====\n{content}\n"
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        parts.append(block)
        total += len(block)

    return "".join(parts), selected


def plan_changes(
    db: Session,
    instruction: str,
    *,
    provider: str = "auto",
    model: str | None = None,
    user_id: int | None = None,
    max_files: int = 8,
    auto_test: bool | None = None,
) -> DeveloperPlanResponse:
    """READ -> SEARCH -> ANALYZE -> PLAN -> GENERATE PATCH -> RUN TEST -> SHOW DIFF"""
    if not settings.ai_developer_enabled:
        raise ValidationError("ai.developer_disabled")

    steps: list[AgentStep] = []
    warnings: list[str] = []

    def add_step(
        name: str,
        status: str,
        detail: str = "",
        duration: int | None = None,
        output: str | None = None,
    ) -> None:
        steps.append(
            AgentStep(
                step=name,
                status=status,
                detail=detail,
                duration_ms=duration,
                output=output,
            )
        )

    task = start_task(
        db,
        kind=AITaskKind.DEVELOPER,
        # Gizlilik: istem metni `AI_LOG_PROMPTS` kapalıyken hiçbir alanda
        # saklanmaz - başlık dahil (bkz. registry.start_task).
        title=(instruction[:280] if settings.ai_log_prompts else "Geliştirici görevi"),
        user_id=user_id,
        prompt=instruction,
    )

    # --- READ / SEARCH ---
    started = time.perf_counter()
    context, files_read = _gather_context(instruction, max_files)
    add_step(
        "READ",
        "success" if files_read else "failed",
        f"{len(files_read)} dosya okundu: " + ", ".join(files_read[:6]),
        int((time.perf_counter() - started) * 1000),
    )
    if not files_read:
        add_step("SEARCH", "failed", "İstemle eşleşen dosya bulunamadı")
        warnings.append(
            "İstemle eşleşen dosya bulunamadı. Daha açık bir istem yazın "
            "(ör. dosya adı veya modül adı belirtin)."
        )
        finish_task(db, task, error="no_matching_files")
        return DeveloperPlanResponse(
            task_id=task.id,
            instruction=instruction,
            steps=steps,
            warnings=warnings,
            requires_approval=True,
            apply_allowed=False,
        )
    add_step("SEARCH", "success", f"{len(files_read)} aday dosya")

    # --- ANALYZE / PLAN / GENERATE PATCH ---
    add_step("ANALYZE", "running")
    prompt = (
        f"GÖREV:\n{instruction}\n\n"
        f"PROJE DOSYALARI (yalnızca bunlar üzerinde çalış):\n{context}\n\n"
        f"PROJEDEKİ DİĞER DOSYALAR (referans):\n"
        f"{', '.join(list_project_files('*.py', limit=80))}\n\n"
        + PATCH_SCHEMA_HINT.replace("{max_files}", str(max_files))
    )

    try:
        # Geliştirici ajanı da HSP geçidinden geçer. Yük proje kaynak kodudur
        # (kişisel veri değil), ama politika değerlendirmesi ve hak makbuzu
        # yine de üretilir: "bütün AI çağrıları geçitten geçer" sözleşmesi
        # istisnasızdır ve yerel-öncelik politikası burada da uygulanır.
        outcome = hsp_gateway.chat(
            db,
            [
                ChatMessage(role="system", content=SYSTEM_DEVELOPER),
                ChatMessage(role="user", content=prompt),
            ],
            operation="ai.developer.plan",
            field_paths=[],
            preferred=provider,
            model=model,
            temperature=0.15,
            max_tokens=8192,
            json_mode=True,
            task="code",
            actor_user_id=user_id,
        )
        if outcome.blocked or outcome.result is None:
            raise AIProviderError(outcome.refusal_message())
        result = outcome.result
        attempted = outcome.attempted
        fallback_used = outcome.fallback_used
        steps[-1] = AgentStep(
            step="ANALYZE", status="success", detail=f"{result.provider}/{result.model}"
        )
    except AIProviderError as exc:
        steps[-1] = AgentStep(step="ANALYZE", status="failed", detail=str(exc))
        finish_task(db, task, error=str(exc))
        return DeveloperPlanResponse(
            task_id=task.id,
            instruction=instruction,
            steps=steps,
            warnings=[f"Yapay zekâ sağlayıcısına ulaşılamadı: {exc}"],
            requires_approval=True,
            apply_allowed=False,
        )

    try:
        payload = _extract_json(result.content)
        add_step("PLAN", "success", f"{len(payload.get('plan', []))} adım")
    except (ValueError, json.JSONDecodeError) as exc:
        add_step("PLAN", "failed", f"AI yanıtı ayrıştırılamadı: {exc}")
        finish_task(
            db, task, result=result, attempted=attempted, fallback_used=fallback_used
        )
        return DeveloperPlanResponse(
            task_id=task.id,
            instruction=instruction,
            analysis=result.content[:2000],
            steps=steps,
            warnings=[
                "AI yanıtı beklenen JSON şemasında değildi. Ham yanıt analiz alanındadır."
            ],
            requires_approval=True,
            apply_allowed=False,
            provider=result.provider,
            model=result.model,
        )

    # --- Değişiklikleri doğrula ve diff üret ---
    changes: list[FileChange] = []
    patch_payload: list[dict[str, Any]] = []

    for change in payload.get("changes", [])[:max_files]:
        relative = str(change.get("path", "")).replace("\\", "/").lstrip("./")
        action = change.get("action", "modify")
        new_content = change.get("new_content", "")

        if action == "delete":
            warnings.append(f"Dosya silme önerisi reddedildi: {relative}")
            continue
        if not relative or not new_content:
            continue

        decision = policy.can_write(relative)
        if not decision.allowed:
            warnings.append(f"Politika reddetti ({relative}): {decision.reason}")
            continue
        if decision.requires_confirmation:
            warnings.append(f"Dikkatli inceleyin ({relative}): {decision.reason}")

        path = policy.resolve_path(relative)
        original = (
            path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        )
        if original == new_content:
            continue

        diff_text = make_diff(relative, original, new_content)
        added, removed = diff_stats(diff_text)
        changes.append(
            FileChange(
                path=relative,
                action="create" if not path.exists() else "modify",
                diff=diff_text[:20000],
                original_size=len(original),
                new_size=len(new_content),
                lines_added=added,
                lines_removed=removed,
            )
        )
        patch_payload.append(
            {"path": relative, "action": action, "new_content": new_content}
        )

    add_step(
        "GENERATE_PATCH",
        "success" if changes else "failed",
        f"{len(changes)} dosya değişikliği",
    )
    add_step(
        "SHOW_DIFF",
        "success" if changes else "skipped",
        f"{sum(c.lines_added for c in changes)} satır eklendi",
    )

    # --- Yamayı diske yaz (henüz uygulanmadı) ---
    patch_id = None
    if changes:
        PATCH_DIR.mkdir(parents=True, exist_ok=True)
        patch_id = (
            f"patch_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
        )
        (PATCH_DIR / f"{patch_id}.json").write_text(
            json.dumps(
                {
                    "patch_id": patch_id,
                    "task_id": task.id,
                    "instruction": instruction,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "changes": patch_payload,
                    "analysis": payload.get("analysis"),
                    "plan": payload.get("plan", []),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    # --- Testleri çalıştır (mevcut kod üzerinde temel doğrulama) ---
    test_result = None
    should_test = settings.ai_developer_auto_test if auto_test is None else auto_test
    if should_test and changes:
        add_step(
            "RUN_TEST",
            "running",
            "Mevcut testler çalıştırılıyor (değişiklik öncesi temel)",
        )
        test_result = run_tests()
        steps[-1] = AgentStep(
            step="RUN_TEST",
            status="success" if test_result["success"] else "failed",
            detail=f"{test_result['passed']} geçti, {test_result['failed']} başarısız",
            duration_ms=test_result["duration_ms"],
            output=test_result["output"][-1500:],
        )

    if not settings.ai_developer_allow_apply:
        warnings.append(
            "Yama uygulama izni KAPALI. Değişiklikleri uygulamak için "
            "Ayarlar > Geliştirici bölümünden 'Yama Uygulama' seçeneğini açın."
        )
    add_step("APPLY_PATCH", "pending", "Kullanıcı onayı bekleniyor")

    finish_task(
        db,
        task,
        result=result,
        attempted=attempted,
        fallback_used=fallback_used,
        file_changes=[c.model_dump(mode="json", exclude={"diff"}) for c in changes],
        test_result=test_result or {},
    )

    return DeveloperPlanResponse(
        task_id=task.id,
        instruction=instruction,
        plan=payload.get("plan", []),
        analysis=payload.get("analysis"),
        steps=steps,
        changes=changes,
        patch_id=patch_id,
        test_result=test_result,
        requires_approval=True,
        apply_allowed=settings.ai_developer_allow_apply,
        warnings=warnings + payload.get("warnings", []),
        provider=result.provider,
        model=result.model,
    )


def apply_patch(
    db: Session,
    patch_id: str,
    *,
    run_tests_after: bool = True,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Yamayı uygular. Önce checkpoint alır; testler başarısızsa geri alır."""
    if not settings.ai_developer_allow_apply:
        raise ValidationError("ai.apply_not_allowed")

    patch_id = _validate_id(patch_id, _PATCH_ID_RE, "patch")
    patch_file = PATCH_DIR / f"{patch_id}.json"
    if not patch_file.exists():
        raise ValidationError(
            details={"reason": "patch_not_found", "patch_id": patch_id}
        )

    patch = json.loads(patch_file.read_text(encoding="utf-8"))
    paths = [change["path"] for change in patch["changes"]]

    # Politika yeniden denetlenir (yama üretiminden sonra ayar değişmiş olabilir)
    for relative in paths:
        decision = policy.can_write(relative)
        if not decision.allowed:
            raise SecurityPolicyError(
                "ai.command_blocked",
                details={"path": relative, "reason": decision.reason},
            )

    checkpoint_id = create_checkpoint(
        paths, label=f"{patch_id}: {patch['instruction'][:80]}"
    )
    applied: list[str] = []

    try:
        for change in patch["changes"]:
            path = policy.resolve_path(change["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(change["new_content"], encoding="utf-8")
            applied.append(change["path"])
        logger.info("Yama uygulandı: %s (%s dosya)", patch_id, len(applied))
    except Exception as exc:  # noqa: BLE001
        rollback_checkpoint(checkpoint_id)
        logger.exception("Yama uygulanamadı, geri alındı: %s", patch_id)
        return {
            "success": False,
            "patch_id": patch_id,
            "checkpoint_id": checkpoint_id,
            "applied_files": [],
            "test_result": None,
            "rolled_back": True,
            "message": f"Yama uygulanamadı ve geri alındı: {type(exc).__name__}",
        }

    test_result = None
    rolled_back = False
    message = f"{len(applied)} dosya güncellendi."

    if run_tests_after:
        test_result = run_tests()
        if not test_result["success"]:
            rollback_checkpoint(checkpoint_id)
            rolled_back = True
            message = (
                f"Testler başarısız oldu ({test_result['failed']} hata). "
                f"Değişiklikler otomatik olarak geri alındı."
            )
        else:
            message = (
                f"{len(applied)} dosya güncellendi. Testler geçti "
                f"({test_result['passed']} test)."
            )

    return {
        "success": not rolled_back,
        "patch_id": patch_id,
        "checkpoint_id": checkpoint_id,
        "applied_files": applied if not rolled_back else [],
        "test_result": test_result,
        "rolled_back": rolled_back,
        "message": message,
    }


def get_patch(patch_id: str) -> dict[str, Any]:
    patch_id = _validate_id(patch_id, _PATCH_ID_RE, "patch")
    patch_file = PATCH_DIR / f"{patch_id}.json"
    if not patch_file.exists():
        raise ValidationError(details={"reason": "patch_not_found"})
    patch = json.loads(patch_file.read_text(encoding="utf-8"))
    for change in patch["changes"]:
        change.pop("new_content", None)  # yanıtı hafif tut
    return patch


def list_patches(limit: int = 30) -> list[dict[str, Any]]:
    if not PATCH_DIR.exists():
        return []
    entries: list[dict[str, Any]] = []
    for file_path in sorted(PATCH_DIR.glob("patch_*.json"), reverse=True)[:limit]:
        try:
            patch = json.loads(file_path.read_text(encoding="utf-8"))
            entries.append(
                {
                    "patch_id": patch["patch_id"],
                    "instruction": patch["instruction"][:160],
                    "created_at": patch["created_at"],
                    "file_count": len(patch.get("changes", [])),
                    "files": [c["path"] for c in patch.get("changes", [])],
                }
            )
        except (ValueError, KeyError):
            continue
    return entries
