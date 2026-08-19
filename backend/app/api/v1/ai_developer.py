"""AI Developer Console uçları / AI Developer Console endpoints.

Güvenlik: Tüm yollar `CommandPolicy` denetiminden geçer. Yama uygulama ve
rollback açık kullanıcı onayı gerektirir.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_language, require_permissions
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.user import User
from app.schemas.ai import (
    CommandPolicyInfo,
    DeveloperCommand,
    DeveloperPlanResponse,
    PatchApplyRequest,
    PatchApplyResult,
    RollbackRequest,
)
from app.schemas.common import Message
from app.services import audit
from app.services.ai import agent
from app.services.ai.policy import policy

router = APIRouter(prefix="/ai/developer", tags=["AI Developer Console"])


@router.get("/policy", response_model=CommandPolicyInfo, summary="Güvenlik politikası")
def get_policy(
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> CommandPolicyInfo:
    """Ajanın neleri yapıp yapamayacağını şeffaf olarak gösterir."""
    return CommandPolicyInfo(**policy.public_info())


@router.get("/files", summary="Proje dosyalarını listele")
def list_files(
    pattern: str = "*.py",
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    files = agent.list_project_files(pattern)
    return {"pattern": pattern, "count": len(files), "files": files}


@router.get("/file", summary="Dosya oku")
def read_file(
    path: str,
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    """Politika denetiminden geçen dosyayı okur (.env gibi sır dosyaları engellenir)."""
    content = agent.read_file(path)
    return {
        "path": path,
        "size": len(content),
        "lines": content.count("\n") + 1,
        "content": content,
    }


@router.get("/search", summary="Kaynak kodda ara")
def search(
    q: str,
    pattern: str = "*.py",
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    if len(q) < 2:
        raise ValidationError(details={"reason": "query_too_short"})
    hits = agent.search_in_files(q, pattern)
    return {"query": q, "count": len(hits), "hits": hits}


@router.post(
    "/plan", response_model=DeveloperPlanResponse, summary="Görev planla ve yama üret"
)
def plan(
    payload: DeveloperCommand,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> DeveloperPlanResponse:
    """READ -> SEARCH -> ANALYZE -> PLAN -> GENERATE PATCH -> RUN TEST -> SHOW DIFF

    Bu uç HİÇBİR DOSYAYI DEĞİŞTİRMEZ. Yalnızca önizleme (diff) üretir.
    """
    result = agent.plan_changes(
        db,
        payload.instruction,
        provider=payload.provider,
        model=payload.model,
        user_id=current.id,
        max_files=payload.max_files,
        auto_test=payload.auto_test,
    )
    audit.record(
        db,
        action="ai_plan",
        entity_type="ai_developer",
        entity_id=result.patch_id,
        user=current,
        summary=(
            f"AI geliştirici planı: {payload.instruction[:120]} "
            f"({len(result.changes)} dosya önerildi)"
        ),
        commit=True,
    )
    return result


@router.get("/patches", summary="Üretilmiş yamalar")
def list_patches(
    limit: int = 30,
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> list[dict]:
    return agent.list_patches(limit)


@router.get("/patches/{patch_id}", summary="Yama detayı")
def get_patch(
    patch_id: str,
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    return agent.get_patch(patch_id)


@router.post("/apply", response_model=PatchApplyResult, summary="Yamayı uygula")
def apply_patch(
    payload: PatchApplyRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> PatchApplyResult:
    """Yamayı uygular. Önce otomatik checkpoint alınır.

    * `confirm=true` zorunludur.
    * `AI_DEVELOPER_ALLOW_APPLY=false` iken reddedilir.
    * Testler başarısız olursa değişiklikler OTOMATİK geri alınır.
    """
    if not payload.confirm:
        raise ValidationError(
            details={"reason": "confirmation_required", "hint": "confirm=true gönderin"}
        )
    if not settings.ai_developer_allow_apply:
        raise ValidationError("ai.apply_not_allowed")

    result = agent.apply_patch(
        db,
        payload.patch_id,
        run_tests_after=payload.run_tests_after,
        user_id=current.id,
    )
    audit.record(
        db,
        action="ai_apply_patch",
        entity_type="ai_developer",
        entity_id=payload.patch_id,
        user=current,
        summary=(
            f"Yama {'uygulandı' if result['success'] else 'uygulanamadı'}: "
            f"{payload.patch_id} · {result['message']}"
        ),
        changes={
            "files": result["applied_files"],
            "rolled_back": result["rolled_back"],
        },
        commit=True,
    )
    return PatchApplyResult(**result)


@router.get("/checkpoints", summary="Geri alma noktaları")
def list_checkpoints(
    limit: int = 30,
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> list[dict]:
    return agent.list_checkpoints(limit)


@router.post("/rollback", response_model=Message, summary="Değişiklikleri geri al")
def rollback(
    payload: RollbackRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
    lang: str = Depends(get_language),
) -> Message:
    if not payload.confirm:
        raise ValidationError(details={"reason": "confirmation_required"})

    result = agent.rollback_checkpoint(payload.checkpoint_id)
    audit.record(
        db,
        action="ai_rollback",
        entity_type="ai_developer",
        entity_id=payload.checkpoint_id,
        user=current,
        summary=(
            f"Geri alındı: {payload.checkpoint_id} "
            f"({len(result['restored'])} dosya geri yüklendi)"
        ),
        commit=True,
    )
    return Message(
        code="common.updated", message=t("common.updated", lang), data=result
    )


@router.post("/run-tests", summary="Testleri çalıştır")
def run_tests(
    target: str = "backend/tests",
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    """Proje testlerini çalıştırır (sabit ve güvenli komut)."""
    if ".." in target or target.startswith(("/", "\\")) or ":" in target:
        raise ValidationError(details={"reason": "invalid_target"})
    result = agent.run_tests(target)
    audit.record(
        db,
        action="ai_run_tests",
        entity_type="ai_developer",
        user=current,
        summary=f"Testler çalıştırıldı: {result['passed']} geçti, {result['failed']} başarısız",
        commit=True,
    )
    return result


@router.post("/shell", summary="Kabuk komutu çalıştır (politika denetimli)")
def run_shell(
    command: str,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    """Yalnızca beyaz listedeki komutlar çalışır.

    Varsayılan olarak KAPALIDIR (`AI_DEVELOPER_ALLOW_SHELL=false`).
    """
    result = agent.run_shell(command)
    audit.record(
        db,
        action="ai_shell",
        entity_type="ai_developer",
        user=current,
        summary=f"Kabuk komutu: {command[:120]} (çıkış kodu {result['return_code']})",
        commit=True,
    )
    return result


@router.post("/check-command", summary="Komut politika denetimi")
def check_command(
    command: str,
    _: User = Depends(require_permissions(Perm.AI_DEVELOPER)),
) -> dict:
    """Komutu çalıştırmadan yalnızca politika sonucunu döndürür."""
    decision = policy.check_command(command)
    return {
        "command": command,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "requires_confirmation": decision.requires_confirmation,
    }
