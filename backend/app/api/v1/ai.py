"""AI Merkezi uçları / AI Control Center endpoints."""

from __future__ import annotations

import re


from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    db_session,
    get_language,
    pagination,
    require_permissions,
)
from app.core.config import settings
from app.core.exceptions import AIProviderError as AppAIError
from app.core.exceptions import ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.enums import AITaskKind
from app.models.system import AITask
from app.models.user import User
from app.schemas.ai import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    AIConfigUpdate,
    AIControlCenter,
    AITaskOut,
    ChatRequest,
    ChatResponse,
    ConnectionTestReport,
    ModelInfo,
    PromptTemplate,
    ProviderStatus,
    TokenUsage,
)
from app.schemas.common import Message, Page, PaginationParams
from app.services import audit
from app.core.logging_config import get_logger
from app.services.ai.analysis import generate_training_plan, run_analysis
from app.services.ai.base import AIProviderError, ChatMessage
from app.services.ai.prompts import get_prompts
from app.services.ai.providers import (
    TASK_LABELS,
    TASK_MODEL_HINTS,
    suggest_model_for_task,
)
from app.services.ai.registry import (
    AIRouter,
    control_center_data,
    finish_task,
    get_provider,
    get_providers,
    record_health,
    reload_providers,
    run_connection_tests,
    start_task,
)
from app.services.crud import paginate
from app.services.hsp import freetext
from app.services.hsp import gateway as hsp_gateway
from app.services.hsp.redaction import replace_names

router = APIRouter(prefix="/ai", tags=["Yapay Zekâ"])

# `.env` satırına yazılacak değerlerde yasak karakterler (enjeksiyon koruması)
_ENV_LINE_UNSAFE = re.compile(r"[\r\n\x00-\x1f\x7f]")
_ENV_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,60}$")

logger = get_logger("ai")


def chat_task_title(content: str) -> str:
    """Görev başlığı.

    Gizlilik: kullanıcı istemi (prompt) `AI_LOG_PROMPTS` kapalıyken
    hiçbir alanda saklanmaz - başlık dahil. Aksi hâlde her sohbetin ilk
    200 karakteri bayrağa rağmen veritabanına yazılırdı.
    """
    if settings.ai_log_prompts:
        return content[:200]
    return "Sohbet"


@router.get(
    "/control-center", response_model=AIControlCenter, summary="AI Kontrol Merkezi"
)
def control_center(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AI_USE)),
) -> AIControlCenter:
    """Sağlayıcı durumu, gecikme, model, token kullanımı ve hata sayıları."""
    data = control_center_data(db)
    return AIControlCenter(
        mode=data["mode"],
        fallback_chain=data["fallback_chain"],
        response_language=data["response_language"],
        providers=[ProviderStatus(**p) for p in data["providers"]],
        usage_today=TokenUsage(**data["usage_today"]),
        usage_total=TokenUsage(**data["usage_total"]),
        task_counts=data["task_counts"],
        error_count_24h=data["error_count_24h"],
        local_only_mode=data["local_only_mode"],
    )


@router.get(
    "/providers/{provider}/models",
    response_model=list[ModelInfo],
    summary="Model listesi",
)
def list_models(
    provider: str,
    _: User = Depends(require_permissions(Perm.AI_USE)),
) -> list[ModelInfo]:
    instance = get_provider(provider)
    if instance is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(details={"provider": provider})
    return [
        ModelInfo(
            id=model.id,
            provider=model.provider,
            owned_by=model.owned_by,
            capabilities=model.capabilities,
            capability_source=model.capability_source,
            context_length=model.context_length,
        )
        for model in instance.list_models(use_cache=False)
    ]


@router.post("/providers/{provider}/health", summary="Sağlık kontrolü")
def provider_health(
    provider: str,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AI_USE)),
) -> dict:
    entry = record_health(db, provider)
    return {
        "provider": entry.provider,
        "available": entry.is_available,
        "latency_ms": entry.latency_ms,
        "model_count": entry.model_count,
        "endpoint": entry.endpoint,
        "error": entry.error_message,
        "checked_at": entry.checked_at.isoformat(),
    }


@router.post(
    "/providers/{provider}/test",
    response_model=ConnectionTestReport,
    summary="Bağlantı testi",
)
def test_provider(
    provider: str,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_CONFIGURE)),
) -> ConnectionTestReport:
    """Connection · Model · Simple prompt · JSON output · Timeout · Streaming testleri.

    API anahtarları hiçbir test çıktısında görünmez.
    """
    report = run_connection_tests(provider)
    audit.record(
        db,
        action="ai_test",
        entity_type="ai_provider",
        entity_id=provider,
        user=current,
        summary=f"AI bağlantı testi: {provider} -> {report['overall']}",
        commit=True,
    )
    return ConnectionTestReport(**report)


@router.get("/routing/tasks", summary="Model yönlendirme tablosu")
def routing_table(
    lang: str = Depends(get_language),
    _: User = Depends(require_permissions(Perm.AI_USE)),
) -> dict:
    """Görev türlerine göre model önerileri.

    Yetenekler yalnızca sağlayıcı API'si açıkça bildirdiğinde `api` kaynaklıdır;
    aksi halde ad eşleşmesine dayanan `heuristic` olarak işaretlenir ve
    doğrulanmamış sayılmalıdır.
    """
    rows = []
    for task, keywords in TASK_MODEL_HINTS.items():
        entry: dict = {
            "task": task,
            "label": TASK_LABELS.get(task, {}).get(lang, task),
            "keywords": keywords,
            "providers": {},
        }
        for name, provider in get_providers().items():
            if not provider.enabled:
                continue
            models = provider.list_models()
            model_id, source = suggest_model_for_task(task, models)
            entry["providers"][name] = {
                "suggested_model": model_id,
                "capability_source": source,
                "verified": source == "api",
            }
        rows.append(entry)

    return {
        "tasks": rows,
        "note_tr": (
            "Yetenek bilgisi yalnızca sağlayıcı API'si bildirdiğinde doğrulanmış "
            "sayılır. 'heuristic' kaynağı model adına dayanan tahmindir."
        ),
        "note_en": (
            "Capability is considered verified only when reported by the provider API. "
            "A 'heuristic' source is a guess based on the model name."
        ),
    }


def _chat_messages(payload: ChatRequest) -> list[ChatMessage]:
    return [ChatMessage(role=m.role, content=m.content) for m in payload.messages]


def _scan_chat(db: Session, payload: ChatRequest) -> tuple[list[str], dict[str, str]]:
    """Serbest sohbet metnini HSP kayıt defterine karşı tarar.

    Sohbet yapılandırılmış alan listesi taşımaz; taranmadan gönderilirse
    kişisel veri geçitsiz çıkar. Bu yüzden gönderilecek bütün metin taranır.
    """
    combined = "\n".join(m.content for m in payload.messages)
    return freetext.scan(db, combined)


@router.post("/chat", response_model=ChatResponse, summary="Sohbet")
def chat(
    payload: ChatRequest,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.AI_USE)),
    lang: str = Depends(get_language),
) -> ChatResponse:
    field_paths, subject_names = _scan_chat(db, payload)
    task = start_task(
        db,
        kind=AITaskKind.CHAT,
        title=chat_task_title(payload.messages[-1].content),
        user_id=user.id,
        prompt=payload.messages[-1].content,
    )
    try:
        # Bütün AI çağrıları HSP geçidinden geçer: sınıflandırma, sağlayıcı
        # kanıtı, politika kararı, takma adlaştırma ve hak makbuzu.
        outcome = hsp_gateway.chat(
            db,
            _chat_messages(payload),
            operation="ai.chat",
            field_paths=field_paths,
            subject_names=subject_names,
            preferred=payload.provider,
            model=payload.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            json_mode=payload.json_mode,
            actor_user_id=user.id,
            actor_role=(user.role_codes[0] if user.role_codes else None),
        )
    except AIProviderError as exc:
        finish_task(db, task, error=str(exc))
        raise AppAIError(
            "ai.all_providers_failed", details={"detail": str(exc)}
        ) from exc

    if outcome.blocked or outcome.result is None:
        message = outcome.refusal_message(lang)
        finish_task(db, task, error=message)
        raise AppAIError(
            "ai.blocked_by_policy",
            details={
                "detail": message,
                "receipt_id": outcome.receipt_id,
                "excluded_providers": outcome.excluded_providers,
            },
        )

    result = outcome.result
    finish_task(
        db,
        task,
        result=result,
        attempted=outcome.attempted,
        fallback_used=outcome.fallback_used,
    )
    return ChatResponse(
        content=result.content,
        provider=result.provider,
        model=result.model,
        usage=TokenUsage(**result.usage.to_dict()),
        duration_ms=result.duration_ms,
        fallback_used=outcome.fallback_used,
        attempted_providers=outcome.attempted,
        finish_reason=result.finish_reason,
    )


@router.post("/chat/stream", summary="Sohbet (akış)")
def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.AI_USE)),
    lang: str = Depends(get_language),
) -> StreamingResponse:
    """Akışlı sohbet — istek/yanıt ucuyla AYNI HSP politikasından geçer.

    Akış parça parça geldiği için geçidin karar aşaması (`preflight`) çağrıdan
    önce çalışır: karar BLOCK ise sağlayıcıya hiçbir şey gönderilmez.
    """
    field_paths, subject_names = _scan_chat(db, payload)
    plan = hsp_gateway.preflight(
        db,
        _chat_messages(payload),
        operation="ai.chat.stream",
        field_paths=field_paths,
        subject_names=subject_names,
        preferred=payload.provider,
        actor_role=(user.role_codes[0] if user.role_codes else None),
    )
    actor_role = user.role_codes[0] if user.role_codes else None

    if plan.blocked:
        hsp_gateway.issue_receipt(
            db,
            plan,
            outcome="blocked",
            provider=None,
            actor_user_id=user.id,
            actor_role=actor_role,
        )
        refusal = plan.refusal_message(lang)

        def refuse():  # noqa: ANN202
            yield refusal

        return StreamingResponse(
            refuse(), media_type="text/plain; charset=utf-8", status_code=200
        )

    reverse = {alias: real for real, alias in plan.name_map.items()}
    chosen = plan.allowed[0]

    def generate():  # noqa: ANN202
        outcome = "completed"
        try:
            router_instance = AIRouter(db)
            for chunk in router_instance.stream(
                plan.outgoing,
                preferred=chosen,
                model=payload.model,
            ):
                # Takma adlar yalnızca uygulama içinde geri eşlenir.
                yield replace_names(chunk, reverse) if reverse else chunk
        except AIProviderError as exc:
            outcome = "provider_error"
            yield f"\n\n[HATA] {exc}"
        finally:
            try:
                hsp_gateway.issue_receipt(
                    db,
                    plan,
                    outcome=outcome,
                    provider=chosen,
                    actor_user_id=user.id,
                    actor_role=actor_role,
                )
            except Exception:  # noqa: BLE001 - makbuz hatası akışı bozmamalı
                logger.warning("Akış makbuzu yazılamadı", exc_info=True)

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@router.post(
    "/analyze",
    response_model=AIAnalysisResponse,
    summary="Veri analizi (İstatistik + AI)",
)
def analyze(
    payload: AIAnalysisRequest,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.AI_USE)),
) -> AIAnalysisResponse:
    """Önce Statistics Engine gerçek metrikleri hesaplar, sonra AI yorumlar.

    Yanıtta `metrics` gerçek veridir; `ai_interpretation` bir model yorumudur.
    AI kullanılamıyorsa yalnızca metrikler döner - istek yine de başarılıdır.
    """
    return run_analysis(db, payload, user_id=user.id, user_language=user.language)


@router.post("/training-plan/{student_id}", summary="AI antrenman planı taslağı")
def training_plan(
    student_id: int,
    weeks: int = 4,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.AI_USE, Perm.PERFORMANCE_READ)),
) -> dict:
    """Plan taslak olarak kaydedilir; eğitmen onayı olmadan yürürlüğe girmez."""
    return generate_training_plan(
        db,
        student_id,
        weeks=min(12, max(1, weeks)),
        user_id=user.id,
        lang=user.language,
    )


@router.get(
    "/prompts", response_model=list[PromptTemplate], summary="Prompt kütüphanesi"
)
def prompts(
    category: str | None = None,
    _: User = Depends(require_permissions(Perm.AI_USE)),
) -> list[PromptTemplate]:
    return get_prompts(category)


@router.get("/tasks", response_model=Page[AITaskOut], summary="AI görev geçmişi")
def list_tasks(
    kind: AITaskKind | None = None,
    status: str | None = None,
    provider: str | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AI_USE)),
) -> Page[AITaskOut]:
    stmt = select(AITask)
    if kind:
        stmt = stmt.where(AITask.kind == kind)
    if status:
        stmt = stmt.where(AITask.status == status)
    if provider:
        stmt = stmt.where(AITask.provider == provider)
    stmt = stmt.order_by(AITask.started_at.desc())
    rows, total = paginate(db, stmt, params)
    return Page[AITaskOut](
        items=[AITaskOut.model_validate(r) for r in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/config", summary="AI yapılandırması (maskeli)")
def get_config(
    _: User = Depends(require_permissions(Perm.AI_CONFIGURE)),
) -> dict:
    """API anahtarları ASLA tam olarak döndürülmez, yalnızca maskelenmiş gösterilir."""
    return settings.public_ai_config()


@router.put("/config", response_model=Message, summary="AI yapılandırmasını güncelle")
def update_config(
    payload: AIConfigUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_CONFIGURE)),
    lang: str = Depends(get_language),
) -> Message:
    """Ayarları `.env` dosyasına yazar ve sağlayıcıları yeniden yükler.

    API anahtarları yalnızca `.env` dosyasına yazılır; veritabanına veya loglara
    düz metin olarak kaydedilmez.
    """
    env_path = settings.project_root / ".env"
    if not env_path.exists():
        example = settings.project_root / ".env.example"
        env_path.write_text(
            example.read_text(encoding="utf-8") if example.exists() else "",
            encoding="utf-8",
        )

    field_map = {
        "mode": "AI_DEFAULT_MODE",
        "response_language": "AI_RESPONSE_LANGUAGE",
        "local_enabled": "LOCAL_AI_ENABLED",
        "local_base_url": "LOCAL_AI_BASE_URL",
        "local_model": "LOCAL_AI_MODEL",
        "local_timeout": "LOCAL_AI_TIMEOUT",
        "local_max_tokens": "LOCAL_AI_MAX_TOKENS",
        "local_temperature": "LOCAL_AI_TEMPERATURE",
        "nvidia_enabled": "NVIDIA_ENABLED",
        "nvidia_base_url": "NVIDIA_BASE_URL",
        "nvidia_model": "NVIDIA_MODEL",
        "nvidia_api_key": "NVIDIA_API_KEY",
        "nvidia_timeout": "NVIDIA_TIMEOUT",
        "nvidia_max_tokens": "NVIDIA_MAX_TOKENS",
        "nvidia_temperature": "NVIDIA_TEMPERATURE",
    }

    updates: dict[str, str] = {}
    data = payload.model_dump(exclude_unset=True)
    if "fallback_chain" in data and data["fallback_chain"]:
        updates["AI_FALLBACK_CHAIN"] = ",".join(data.pop("fallback_chain"))

    changed_fields: list[str] = []
    for field, env_key in field_map.items():
        if field not in data or data[field] is None:
            continue
        value = data[field]
        updates[env_key] = str(value).lower() if isinstance(value, bool) else str(value)
        # Denetim kaydına API anahtarı YAZILMAZ
        changed_fields.append("nvidia_api_key (gizli)" if "api_key" in field else field)

    # Derinlemesine savunma: şema doğrulamasından sonra ikinci bir kapı.
    # `.env` satırına asla satır sonu / kontrol karakteri geçemez.
    for env_key, env_value in updates.items():
        if not _ENV_KEY_RE.match(env_key) or _ENV_LINE_UNSAFE.search(env_value):
            raise ValidationError(details={"reason": "invalid_env_value"})

    lines = env_path.read_text(encoding="utf-8").splitlines()
    remaining = dict(updates)
    for index, line in enumerate(lines):
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            lines[index] = f"{key}={remaining.pop(key)}"
    for key, value in remaining.items():
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    reload_providers()
    audit.record(
        db,
        action="update",
        entity_type="ai_config",
        user=current,
        summary=f"AI yapılandırması güncellendi: {', '.join(changed_fields)}",
        changes={"fields": changed_fields},
        commit=True,
    )
    return Message(
        code="common.updated",
        message=t("common.updated", lang),
        data={"updated_fields": changed_fields, "reloaded": True},
    )


@router.post("/reload", response_model=Message, summary="Sağlayıcıları yeniden yükle")
def reload(
    _: User = Depends(require_permissions(Perm.AI_CONFIGURE)),
    lang: str = Depends(get_language),
) -> Message:
    reload_providers()
    return Message(code="common.updated", message=t("common.updated", lang))
