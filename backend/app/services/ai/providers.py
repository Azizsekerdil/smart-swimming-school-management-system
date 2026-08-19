"""Somut AI sağlayıcıları / Concrete AI providers.

AIProvider
 ├── LMStudioProvider      (yerel, gizlilik dostu)
 ├── NvidiaProvider        (bulut, build.nvidia.com)
 └── OpenAICompatProvider  (genel amaçlı, yapılandırılabilir)
"""

from __future__ import annotations

from app.core.config import settings
from app.services.ai.base import ModelDescriptor, OpenAICompatibleProvider


class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio yerel sunucusu.

    Gizlilik notu: İstekler bilgisayardan çıkmaz. Hassas öğrenci verisi için
    tercih edilmesi gereken sağlayıcıdır.
    """

    def __init__(self) -> None:
        super().__init__(
            name="local",
            display_name="LM Studio (Yerel)",
            base_url=settings.local_ai_base_url,
            api_key=settings.local_ai_api_key,
            default_model=settings.local_ai_model,
            timeout=settings.local_ai_timeout,
            max_tokens=settings.local_ai_max_tokens,
            temperature=settings.local_ai_temperature,
            is_local=True,
            enabled=settings.local_ai_enabled,
        )

    def public_info(self) -> dict:
        info = super().public_info()
        info["privacy_note_tr"] = (
            "Yerel model: veriler bilgisayarınızdan dışarı çıkmaz. Hassas öğrenci "
            "verileri için önerilir."
        )
        info["privacy_note_en"] = (
            "Local model: data never leaves your computer. Recommended for "
            "sensitive student data."
        )
        return info


class NvidiaProvider(OpenAICompatibleProvider):
    """NVIDIA Build (integrate.api.nvidia.com) OpenAI uyumlu API.

    API anahtarı yalnızca ortam değişkeninden okunur; koda gömülmez, loglanmaz.
    """

    def __init__(self) -> None:
        super().__init__(
            name="nvidia",
            display_name="NVIDIA Build (Bulut)",
            base_url=settings.nvidia_base_url,
            api_key=settings.nvidia_api_key,
            default_model=settings.nvidia_model,
            timeout=settings.nvidia_timeout,
            max_tokens=settings.nvidia_max_tokens,
            temperature=settings.nvidia_temperature,
            is_local=False,
            enabled=settings.nvidia_enabled,
        )

    @property
    def enabled(self) -> bool:
        # API anahtarı olmadan bulut sağlayıcı etkin sayılmaz
        return super().enabled and bool(self.api_key)

    def public_info(self) -> dict:
        info = super().public_info()
        info["privacy_note_tr"] = (
            "Bulut model: gönderilen veriler NVIDIA sunucularında işlenir. Kişisel "
            "veri gönderirken dikkatli olun."
        )
        info["privacy_note_en"] = (
            "Cloud model: submitted data is processed on NVIDIA servers. Be careful "
            "when sending personal data."
        )
        return info


class OpenAICompatProvider(OpenAICompatibleProvider):
    """Genel amaçlı OpenAI uyumlu sağlayıcı (vLLM, LiteLLM, Ollama, kendi sunucunuz)."""

    def __init__(self) -> None:
        super().__init__(
            name="openai_compat",
            display_name="OpenAI Uyumlu Sağlayıcı",
            base_url=settings.openai_compat_base_url,
            api_key=settings.openai_compat_api_key,
            default_model=settings.openai_compat_model,
            timeout=120,
            is_local=False,
            enabled=settings.openai_compat_enabled,
        )

    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self.base_url)


# ---------------------------------------------------------------------------
# Model yönlendirme ipuçları
# ---------------------------------------------------------------------------
# ÖNEMLİ: Bu tablo yalnızca bir ÖNERİ mekanizmasıdır. Model adından yetenek
# VARSAYILMAZ; router bir modeli göreve atamadan önce sağlayıcının gerçekten o
# modeli sunduğunu `list_models()` ile doğrular. Yetenek doğrulanamıyorsa
# `capability_source="heuristic"` olarak işaretlenir ve arayüzde belirtilir.
TASK_MODEL_HINTS: dict[str, list[str]] = {
    "general": ["gemma", "llama", "qwen3", "mistral", "phi"],
    "reasoning": ["gemma", "qwen3", "llama-3.3", "deepseek"],
    "vision": ["vl", "vision", "moondream", "llava", "pixtral"],
    "math": ["math", "qwen2.5-math"],
    "code": ["coder", "code", "qwen2.5-coder", "starcoder", "codestral"],
    "embedding": ["embed", "nomic-embed", "bge"],
    "medical": ["biomistral", "medical", "med"],
}

TASK_LABELS = {
    "general": {"tr": "Genel analiz", "en": "General analysis"},
    "reasoning": {"tr": "Akıl yürütme", "en": "Reasoning"},
    "vision": {"tr": "Görsel analiz", "en": "Vision"},
    "math": {"tr": "Matematiksel analiz", "en": "Mathematical analysis"},
    "code": {"tr": "Kod üretimi", "en": "Code generation"},
    "embedding": {"tr": "Vektör gömme", "en": "Embeddings"},
    "medical": {"tr": "Sağlık metni", "en": "Medical text"},
}


def suggest_model_for_task(
    task: str, available_models: list[ModelDescriptor]
) -> tuple[str | None, str]:
    """Görev için model önerir.

    Dönüş: (model_id, kaynak). Kaynak "api" ise sağlayıcı yeteneği açıkça
    bildirmiştir; "heuristic" ise yalnızca ad eşleşmesine dayanır ve arayüzde
    doğrulanmamış olarak gösterilmelidir.
    """
    if not available_models:
        return None, "unavailable"

    # 1) API'nin açıkça bildirdiği yetenek
    for model in available_models:
        if task in [c.lower() for c in model.capabilities]:
            return model.id, "api"

    # 2) Ad eşleşmesi (doğrulanmamış sezgisel)
    for keyword in TASK_MODEL_HINTS.get(task, []):
        for model in available_models:
            if keyword in model.id.lower():
                return model.id, "heuristic"

    # 3) Eşleşme yoksa genel amaçlı ilk model
    return available_models[0].id, "fallback"
