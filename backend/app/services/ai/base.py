"""AI sağlayıcı soyutlaması / AI provider abstraction.

Tüm sağlayıcılar aynı arayüzü uygular:
    chat() · stream() · test_connection() · list_models() · health() · estimate_usage()

Program tek bir yapay zekâ firmasına bağımlı değildir.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import mask_secret
from app.core.logging_config import get_logger, redact

logger = get_logger("ai")


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ChatResult:
    content: str
    provider: str
    model: str
    usage: Usage = field(default_factory=Usage)
    duration_ms: int = 0
    finish_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelDescriptor:
    id: str
    provider: str
    owned_by: str | None = None
    capabilities: list[str] = field(default_factory=list)
    capability_source: str = "unknown"
    context_length: int | None = None


@dataclass
class HealthResult:
    provider: str
    available: bool
    latency_ms: int | None = None
    model_count: int | None = None
    endpoint: str | None = None
    error: str | None = None


class AIProviderError(Exception):
    """Sağlayıcı hatası - üst katman fallback için yakalar."""

    def __init__(
        self, provider: str, message: str, status_code: int | None = None
    ) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class AIProvider(ABC):
    """Tüm AI sağlayıcılarının ortak arayüzü."""

    name: str = "base"
    display_name: str = "AI Provider"
    is_local: bool = False

    @abstractmethod
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> ChatResult: ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]: ...

    @abstractmethod
    def list_models(self) -> list[ModelDescriptor]: ...

    @abstractmethod
    def health(self) -> HealthResult: ...

    def test_connection(self) -> HealthResult:
        return self.health()

    def estimate_usage(self, messages: list[ChatMessage]) -> Usage:
        """Kaba token tahmini (~4 karakter = 1 token; Türkçe için ~3.5)."""
        characters = sum(len(m.content) for m in messages)
        estimated = max(1, int(characters / 3.7))
        return Usage(prompt_tokens=estimated, total_tokens=estimated)

    @property
    @abstractmethod
    def enabled(self) -> bool: ...

    def public_info(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "display_name": self.display_name,
            "is_local": self.is_local,
            "enabled": self.enabled,
        }


class OpenAICompatibleProvider(AIProvider):
    """OpenAI uyumlu `/v1/chat/completions` API'si konuşan sağlayıcılar için taban.

    LM Studio, NVIDIA Build, vLLM, Ollama (OpenAI modu), LiteLLM vb. bu şemayı
    kullanır; alt sınıflar yalnızca yapılandırmayı sağlar.
    """

    def __init__(
        self,
        *,
        name: str,
        display_name: str,
        base_url: str,
        api_key: str = "",
        default_model: str = "",
        timeout: int = 120,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        is_local: bool = False,
        enabled: bool = True,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout
        self.default_max_tokens = max_tokens
        self.default_temperature = temperature
        self.is_local = is_local
        self._enabled = enabled
        self._cached_models: list[ModelDescriptor] | None = None
        # OpenAI'nin `response_format: {"type": "json_object"}` alanı her sunucuda
        # desteklenmez (ör. LM Studio yalnızca `json_schema` veya `text` kabul eder).
        # Sunucu reddederse alan bırakılır ve oturum boyunca bir daha denenmez.
        self._supports_json_object: bool = True

    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self._enabled and bool(self.base_url)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _is_response_format_rejection(error: AIProviderError) -> bool:
        """Hatanın `response_format` alanının reddedilmesinden kaynaklandığını anlar."""
        if error.status_code not in (400, 422):
            return False
        message = str(error).lower()
        return "response_format" in message or "json_schema" in message

    def _resolve_model(self, model: str | None) -> str:
        if model:
            return model
        if self.default_model:
            return self.default_model
        # Model belirtilmemişse sunucudaki ilk modeli kullan
        models = self.list_models()
        if not models:
            raise AIProviderError(self.name, "Kullanılabilir model bulunamadı")
        return models[0].id

    def _post(
        self, path: str, payload: dict[str, Any], timeout: int | None = None
    ) -> dict:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=timeout or self.timeout) as client:
                response = client.post(url, json=payload, headers=self._headers())
        except httpx.TimeoutException as exc:
            raise AIProviderError(self.name, f"Zaman aşımı ({self.timeout}s)") from exc
        except httpx.RequestError as exc:
            raise AIProviderError(
                self.name, f"Bağlantı hatası: {type(exc).__name__}"
            ) from exc

        if response.status_code >= 400:
            # Hata gövdesi API anahtarı içerebilir - maskele
            detail = redact(response.text[:400])
            raise AIProviderError(
                self.name,
                f"HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
            )
        return response.json()

    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        json_mode: bool = False,
    ) -> ChatResult:
        resolved_model = self._resolve_model(model)
        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": [m.to_dict() for m in messages],
            "temperature": (
                temperature if temperature is not None else self.default_temperature
            ),
            "max_tokens": max_tokens or self.default_max_tokens,
            "stream": False,
        }
        use_json_field = json_mode and self._supports_json_object
        if use_json_field:
            payload["response_format"] = {"type": "json_object"}

        started = time.perf_counter()
        try:
            data = self._post("/chat/completions", payload)
        except AIProviderError as exc:
            # Sunucu `response_format` alanını reddettiyse (LM Studio yalnızca
            # `json_schema`/`text` kabul eder) alanı bırakıp bir kez daha dene.
            # İstem zaten modelden JSON istiyor ve yanıt ayrıştırıcı kod
            # bloklarını temizleyebiliyor, bu yüzden davranış korunur.
            if use_json_field and self._is_response_format_rejection(exc):
                logger.info(
                    "%s sağlayıcısı response_format=json_object desteklemiyor; "
                    "alan bırakılarak yeniden denendi.",
                    self.name,
                )
                self._supports_json_object = False
                retry_payload = {
                    key: value
                    for key, value in payload.items()
                    if key != "response_format"
                }
                data = self._post("/chat/completions", retry_payload)
            else:
                raise
        duration_ms = int((time.perf_counter() - started) * 1000)

        choices = data.get("choices") or []
        if not choices:
            raise AIProviderError(self.name, "Yanıt boş döndü (choices yok)")

        message = choices[0].get("message", {})
        content = message.get("content") or ""
        # Bazı akıl yürütme modelleri içeriği reasoning alanında döndürebilir
        if not content.strip():
            content = message.get("reasoning_content") or message.get("reasoning") or ""

        usage_data = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        logger.info(
            "AI chat | provider=%s model=%s tokens=%s süre=%sms",
            self.name,
            resolved_model,
            usage.total_tokens,
            duration_ms,
        )
        return ChatResult(
            content=content.strip(),
            provider=self.name,
            model=resolved_model,
            usage=usage,
            duration_ms=duration_ms,
            finish_reason=choices[0].get("finish_reason"),
        )

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Iterator[str]:
        import json as json_lib

        resolved_model = self._resolve_model(model)
        payload = {
            "model": resolved_model,
            "messages": [m.to_dict() for m in messages],
            "temperature": (
                temperature if temperature is not None else self.default_temperature
            ),
            "max_tokens": max_tokens or self.default_max_tokens,
            "stream": True,
        }
        url = f"{self.base_url}/chat/completions"
        try:
            with httpx.Client(timeout=self.timeout) as client, client.stream(
                "POST", url, json=payload, headers=self._headers()
            ) as response:
                if response.status_code >= 400:
                    raise AIProviderError(self.name, f"HTTP {response.status_code}")
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[5:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        parsed = json_lib.loads(chunk)
                        delta = parsed.get("choices", [{}])[0].get("delta", {})
                        if piece := delta.get("content"):
                            yield piece
                    except (json_lib.JSONDecodeError, IndexError, KeyError):
                        continue
        except httpx.RequestError as exc:
            raise AIProviderError(
                self.name, f"Akış hatası: {type(exc).__name__}"
            ) from exc

    def list_models(self, use_cache: bool = True) -> list[ModelDescriptor]:
        if use_cache and self._cached_models is not None:
            return self._cached_models
        try:
            with httpx.Client(timeout=min(20, self.timeout)) as client:
                response = client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
            if response.status_code >= 400:
                return []
            data = response.json().get("data", [])
        except (httpx.RequestError, ValueError):
            return []

        models = [
            ModelDescriptor(
                id=item.get("id", ""),
                provider=self.name,
                owned_by=item.get("owned_by"),
                # Yetenekler yalnızca API metadata'sı sağladığında doldurulur.
                # Model adından yetenek VARSAYILMAZ.
                capabilities=self._declared_capabilities(item),
                capability_source=(
                    "api" if self._declared_capabilities(item) else "unknown"
                ),
                context_length=item.get("context_length") or item.get("max_model_len"),
            )
            for item in data
            if item.get("id")
        ]
        self._cached_models = models
        return models

    @staticmethod
    def _declared_capabilities(item: dict) -> list[str]:
        """API'nin AÇIKÇA bildirdiği yetenekleri döndürür; tahmin yapmaz."""
        declared: list[str] = []
        for key in ("capabilities", "modalities", "supported_features"):
            value = item.get(key)
            if isinstance(value, list):
                declared.extend(str(v) for v in value)
            elif isinstance(value, dict):
                declared.extend(k for k, enabled in value.items() if enabled)
        return sorted(set(declared))

    def health(self) -> HealthResult:
        if not self.enabled:
            return HealthResult(
                provider=self.name,
                available=False,
                endpoint=self.base_url,
                error="disabled",
            )
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=min(15, self.timeout)) as client:
                response = client.get(
                    f"{self.base_url}/models", headers=self._headers()
                )
            latency = int((time.perf_counter() - started) * 1000)
            if response.status_code >= 400:
                return HealthResult(
                    provider=self.name,
                    available=False,
                    latency_ms=latency,
                    endpoint=self.base_url,
                    error=f"HTTP {response.status_code}",
                )
            count = len(response.json().get("data", []))
            return HealthResult(
                provider=self.name,
                available=True,
                latency_ms=latency,
                model_count=count,
                endpoint=self.base_url,
            )
        except Exception as exc:  # noqa: BLE001 - sağlık kontrolü asla patlamamalı
            return HealthResult(
                provider=self.name,
                available=False,
                latency_ms=int((time.perf_counter() - started) * 1000),
                endpoint=self.base_url,
                error=f"{type(exc).__name__}",
            )

    def public_info(self) -> dict[str, Any]:
        info = super().public_info()
        info.update(
            {
                "endpoint": self.base_url,
                "model": self.default_model or "(otomatik)",
                "api_key_set": bool(self.api_key),
                "api_key_masked": mask_secret(self.api_key),
                "timeout": self.timeout,
            }
        )
        return info
