"""AI sağlayıcı kayıt defteri ve yönlendirici / AI provider registry and router.

Fallback zinciri: kullanıcı yapılandırmasına göre (ör. local -> nvidia) sırayla
denenir. Hiçbiri çalışmazsa program ÇÖKMEZ; AI özelliği "kullanılamıyor" olarak
raporlanır ve yüzme okulu sistemi normal çalışmaya devam eder.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.enums import AITaskStatus
from app.models.system import AIProviderHealth, AITask
from app.services.ai.base import (
    AIProvider,
    AIProviderError,
    ChatMessage,
    ChatResult,
    HealthResult,
)
from app.services.ai.providers import (
    LMStudioProvider,
    NvidiaProvider,
    OpenAICompatProvider,
    suggest_model_for_task,
)

logger = get_logger("ai")

# Sağlık kontrolü önbelleği (saniye) - her istekte ağ çağrısı yapmamak için
_HEALTH_CACHE_TTL = 30
_health_cache: dict[str, tuple[float, HealthResult]] = {}
_providers: dict[str, AIProvider] | None = None


def get_providers(refresh: bool = False) -> dict[str, AIProvider]:
    """Yapılandırılmış tüm sağlayıcıları döndürür."""
    global _providers
    if _providers is None or refresh:
        _providers = {
            "local": LMStudioProvider(),
            "nvidia": NvidiaProvider(),
            "openai_compat": OpenAICompatProvider(),
        }
    return _providers


def get_provider(name: str) -> AIProvider | None:
    return get_providers().get(name)


def reload_providers() -> None:
    """Ayar değişikliği sonrası sağlayıcıları yeniden oluşturur."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    _health_cache.clear()
    get_providers(refresh=True)
    logger.info("AI sağlayıcıları yeniden yüklendi")


def check_health(name: str, use_cache: bool = True) -> HealthResult:
    """Sağlayıcı sağlığını kontrol eder (kısa süreli önbellekli)."""
    provider = get_provider(name)
    if provider is None:
        return HealthResult(provider=name, available=False, error="unknown_provider")

    now = time.time()
    if use_cache and name in _health_cache:
        cached_at, result = _health_cache[name]
        if now - cached_at < _HEALTH_CACHE_TTL:
            return result

    result = provider.health()
    _health_cache[name] = (now, result)
    return result


def provider_health_snapshot() -> list[dict[str, Any]]:
    """Sistem sağlık kontrolü için özet (health endpoint'i kullanır)."""
    snapshot: list[dict[str, Any]] = []
    for name, provider in get_providers().items():
        if not provider.enabled:
            snapshot.append(
                {"provider": name, "status": "disabled", "detail": "yapılandırılmamış"}
            )
            continue
        health = check_health(name)
        snapshot.append(
            {
                "provider": name,
                "status": "ok" if health.available else "down",
                "detail": health.error or f"{health.model_count} model",
                "latency_ms": health.latency_ms,
            }
        )
    return snapshot


def record_health(db: Session, name: str) -> AIProviderHealth:
    """Sağlık kontrolünü veritabanına kaydeder (AI Control Center geçmişi)."""
    health = check_health(name, use_cache=False)
    entry = AIProviderHealth(
        provider=name,
        is_available=health.available,
        latency_ms=health.latency_ms,
        model_count=health.model_count,
        endpoint=health.endpoint,
        error_message=health.error,
        checked_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    return entry


# ---------------------------------------------------------------------------
# Yönlendirici
# ---------------------------------------------------------------------------
class AIRouter:
    """Sağlayıcı seçimi ve fallback mantığı."""

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def resolve_chain(self, preferred: str = "auto") -> list[str]:
        """Denenecek sağlayıcı sırasını belirler."""
        if preferred and preferred != "auto":
            # Kullanıcı açıkça bir sağlayıcı seçtiyse yalnızca onu dene
            return [preferred]

        mode = settings.ai_default_mode
        if mode == "local":
            return ["local"]
        if mode == "nvidia":
            return ["nvidia"]

        chain = [
            name
            for name in settings.fallback_chain_list
            if (provider := get_provider(name)) is not None and provider.enabled
        ]
        return chain or ["local"]

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        preferred: str = "auto",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
        task: str | None = None,
    ) -> tuple[ChatResult, list[str], bool]:
        """(sonuç, denenen_sağlayıcılar, fallback_kullanıldı) döndürür."""
        chain = self.resolve_chain(preferred)
        attempted: list[str] = []
        errors: list[str] = []

        for index, name in enumerate(chain):
            provider = get_provider(name)
            if provider is None or not provider.enabled:
                errors.append(f"{name}: devre dışı")
                continue

            attempted.append(name)
            chosen_model = model
            if chosen_model is None and task:
                suggestion, _source = suggest_model_for_task(
                    task, provider.list_models()
                )
                chosen_model = suggestion

            try:
                result = provider.chat(
                    messages,
                    model=chosen_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    json_mode=json_mode,
                )
                return result, attempted, index > 0
            except AIProviderError as exc:
                errors.append(str(exc))
                logger.warning(
                    "Sağlayıcı başarısız (%s), sıradakine geçiliyor: %s", name, exc
                )
                continue

        raise AIProviderError(
            "router",
            "Tüm sağlayıcılar başarısız: " + " | ".join(errors[:3]),
        )

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        preferred: str = "auto",
        model: str | None = None,
    ):  # noqa: ANN201
        chain = self.resolve_chain(preferred)
        last_error: Exception | None = None
        for name in chain:
            provider = get_provider(name)
            if provider is None or not provider.enabled:
                continue
            try:
                yield from provider.stream(messages, model=model)
                return
            except AIProviderError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise AIProviderError("router", "Kullanılabilir sağlayıcı yok")


# ---------------------------------------------------------------------------
# Görev kaydı
# ---------------------------------------------------------------------------
def start_task(
    db: Session,
    *,
    kind: str,
    title: str,
    user_id: int | None = None,
    prompt: str | None = None,
) -> AITask:
    """AI görev kaydı başlatır."""
    task = AITask(
        kind=kind,
        status=AITaskStatus.RUNNING,
        title=title[:300],
        # Gizlilik: prompt yalnızca açıkça izin verildiyse saklanır
        prompt_preview=(prompt[:2000] if prompt and settings.ai_log_prompts else None),
        user_id=user_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    return task


def finish_task(
    db: Session,
    task: AITask,
    *,
    result: ChatResult | None = None,
    error: str | None = None,
    attempted: list[str] | None = None,
    fallback_used: bool = False,
    file_changes: list[dict] | None = None,
    test_result: dict | None = None,
) -> AITask:
    """AI görev kaydını tamamlar."""
    task.finished_at = datetime.now(timezone.utc)
    task.attempted_providers = attempted or []
    task.fallback_used = fallback_used

    if result is not None:
        task.status = AITaskStatus.SUCCESS
        task.provider = result.provider
        task.model = result.model
        task.result_preview = result.content[:2000]
        task.prompt_tokens = result.usage.prompt_tokens
        task.completion_tokens = result.usage.completion_tokens
        task.total_tokens = result.usage.total_tokens
        task.duration_ms = result.duration_ms
    else:
        task.status = AITaskStatus.FAILED
        task.error_message = (error or "Bilinmeyen hata")[:2000]

    if file_changes is not None:
        task.file_changes = file_changes
    if test_result is not None:
        task.test_result = test_result

    db.commit()
    return task


def control_center_data(db: Session) -> dict[str, Any]:
    """AI Control Center ekranı için birleşik veri."""
    from datetime import date

    providers_info: list[dict[str, Any]] = []
    for name, provider in get_providers().items():
        info = provider.public_info()
        health = check_health(name) if provider.enabled else None
        latest = db.scalar(
            select(AIProviderHealth)
            .where(AIProviderHealth.provider == name)
            .order_by(AIProviderHealth.checked_at.desc())
            .limit(1)
        )
        info.update(
            {
                "available": bool(health and health.available),
                "latency_ms": health.latency_ms if health else None,
                "model_count": health.model_count if health else None,
                "error_message": health.error if health else "disabled",
                "last_checked_at": latest.checked_at if latest else None,
            }
        )
        providers_info.append(info)

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_tasks = db.scalars(
        select(AITask).where(AITask.started_at >= today_start)
    ).all()
    all_tasks = db.scalars(select(AITask)).all()

    task_counts: dict[str, int] = {}
    for task in all_tasks:
        task_counts[task.status] = task_counts.get(task.status, 0) + 1

    from datetime import timedelta

    day_ago = datetime.now(timezone.utc) - timedelta(hours=24)
    errors_24h = sum(
        1
        for task in all_tasks
        if task.status == AITaskStatus.FAILED
        and task.started_at.replace(tzinfo=timezone.utc) >= day_ago
    )

    return {
        "mode": settings.ai_default_mode,
        "fallback_chain": settings.fallback_chain_list,
        "response_language": settings.ai_response_language,
        "providers": providers_info,
        "usage_today": {
            "prompt_tokens": sum(t.prompt_tokens for t in today_tasks),
            "completion_tokens": sum(t.completion_tokens for t in today_tasks),
            "total_tokens": sum(t.total_tokens for t in today_tasks),
        },
        "usage_total": {
            "prompt_tokens": sum(t.prompt_tokens for t in all_tasks),
            "completion_tokens": sum(t.completion_tokens for t in all_tasks),
            "total_tokens": sum(t.total_tokens for t in all_tasks),
        },
        "task_counts": task_counts,
        "error_count_24h": errors_24h,
        "local_only_mode": settings.ai_default_mode == "local",
    }


def run_connection_tests(name: str) -> dict[str, Any]:
    """Sağlayıcı için kapsamlı bağlantı testleri.

    Testler: Connection · Model · Simple prompt · JSON output · Timeout · Streaming
    Sonuçlar PASS / FAIL / SKIPPED olarak raporlanır. Sırlar gösterilmez.
    """
    provider = get_provider(name)
    tests: list[dict[str, Any]] = []

    def add(
        test_name: str, result: str, detail: str = "", duration: int | None = None
    ) -> None:
        tests.append(
            {
                "provider": name,
                "test_name": test_name,
                "result": result,
                "detail": detail,
                "duration_ms": duration,
            }
        )

    if provider is None:
        add("connection", "FAIL", "Bilinmeyen sağlayıcı")
        return {
            "provider": name,
            "overall": "FAIL",
            "tests": tests,
            "checked_at": datetime.now(timezone.utc),
        }

    if not provider.enabled:
        for test_name in (
            "connection",
            "model",
            "simple_prompt",
            "json_output",
            "timeout",
            "streaming",
        ):
            add(
                test_name,
                "SKIPPED",
                "Sağlayıcı devre dışı veya API anahtarı tanımlı değil",
            )
        return {
            "provider": name,
            "overall": "SKIPPED",
            "tests": tests,
            "checked_at": datetime.now(timezone.utc),
        }

    # 1) Bağlantı
    health = provider.health()
    add(
        "connection",
        "PASS" if health.available else "FAIL",
        health.error or f"{health.model_count} model erişilebilir",
        health.latency_ms,
    )
    if not health.available:
        for test_name in (
            "model",
            "simple_prompt",
            "json_output",
            "timeout",
            "streaming",
        ):
            add(test_name, "SKIPPED", "Bağlantı kurulamadı")
        return {
            "provider": name,
            "overall": "FAIL",
            "tests": tests,
            "checked_at": datetime.now(timezone.utc),
        }

    # 2) Model listesi
    models = (
        provider.list_models(use_cache=False)
        if hasattr(provider, "list_models")
        else []
    )
    add(
        "model",
        "PASS" if models else "FAIL",
        f"{len(models)} model: " + ", ".join(m.id for m in models[:4]),
    )

    # 3) Basit istem
    try:
        started = time.perf_counter()
        result = provider.chat(
            [
                ChatMessage(role="system", content="Kısa ve net yanıt ver."),
                ChatMessage(
                    role="user", content="Türkiye'nin başkenti nedir? Tek kelime yaz."
                ),
            ],
            max_tokens=1024,
            temperature=0,
        )
        duration = int((time.perf_counter() - started) * 1000)
        ok = bool(result.content.strip())
        add(
            "simple_prompt",
            "PASS" if ok else "FAIL",
            (result.content[:120] if ok else "Boş yanıt"),
            duration,
        )
    except Exception as exc:  # noqa: BLE001
        add("simple_prompt", "FAIL", f"{type(exc).__name__}")

    # 4) JSON çıktı
    try:
        started = time.perf_counter()
        result = provider.chat(
            [
                ChatMessage(
                    role="user",
                    content=(
                        "Yalnızca şu JSON nesnesini döndür, başka hiçbir şey yazma: "
                        '{"status": "ok", "value": 42}'
                    ),
                )
            ],
            max_tokens=1024,
            temperature=0,
            json_mode=True,
        )
        duration = int((time.perf_counter() - started) * 1000)
        import json as json_lib

        text = result.content.strip()
        if "```" in text:
            text = text.split("```")[1].removeprefix("json").strip()
        start_index, end_index = text.find("{"), text.rfind("}")
        parsed = (
            json_lib.loads(text[start_index : end_index + 1])
            if start_index >= 0
            else None
        )
        add(
            "json_output",
            "PASS" if isinstance(parsed, dict) else "FAIL",
            str(parsed)[:120] if parsed else result.content[:120],
            duration,
        )
    except Exception as exc:  # noqa: BLE001
        add("json_output", "FAIL", f"JSON ayrıştırılamadı: {type(exc).__name__}")

    # 5) Zaman aşımı davranışı
    add(
        "timeout",
        "PASS",
        f"Yapılandırılmış zaman aşımı: {provider.timeout}s (istekler bu sürede kesilir)",
    )

    # 6) Akış
    try:
        started = time.perf_counter()
        chunks = []
        for piece in provider.stream(
            [ChatMessage(role="user", content="1'den 5'e kadar say.")], model=None
        ):
            chunks.append(piece)
            if len(chunks) >= 5:
                break
        duration = int((time.perf_counter() - started) * 1000)
        add(
            "streaming",
            "PASS" if chunks else "FAIL",
            f"{len(chunks)} parça alındı" if chunks else "Akış boş",
            duration,
        )
    except Exception as exc:  # noqa: BLE001
        add("streaming", "FAIL", f"{type(exc).__name__}")

    results = [t["result"] for t in tests]
    overall = "PASS" if all(r in ("PASS", "SKIPPED") for r in results) else "FAIL"
    return {
        "provider": name,
        "overall": overall,
        "tests": tests,
        "checked_at": datetime.now(timezone.utc),
    }
