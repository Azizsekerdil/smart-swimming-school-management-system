"""Yapay zekâ şemaları / AI schemas.

Önemli tasarım ilkesi: Gerçek (hesaplanmış) veri ile AI yorumu şemada ayrı
alanlarda taşınır. Arayüz bunları farklı bölümlerde gösterir.
"""

from __future__ import annotations

import re

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from app.models.enums import AITaskKind, AITaskStatus
from app.schemas.common import ORMModel

ProviderName = Literal["local", "nvidia", "openai_compat"]


class ChatMessageIn(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn] = Field(min_length=1)
    provider: ProviderName | Literal["auto"] = "auto"
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    language: Literal["tr", "en", "auto"] = "auto"
    json_mode: bool = False


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    duration_ms: int = 0
    fallback_used: bool = False
    attempted_providers: list[str] = Field(default_factory=list)
    finish_reason: str | None = None


class ModelInfo(BaseModel):
    id: str
    provider: str
    owned_by: str | None = None
    # Yetenekler yalnızca doğrulanabildiğinde işaretlenir; varsayım yapılmaz.
    capabilities: list[str] = Field(default_factory=list)
    capability_source: str = "unknown"  # api | metadata | heuristic | unknown
    context_length: int | None = None


class ProviderStatus(BaseModel):
    """AI Control Center satırı."""

    provider: str
    display_name: str
    enabled: bool
    available: bool
    endpoint: str | None = None
    model: str | None = None
    api_key_set: bool = False
    api_key_masked: str = ""
    latency_ms: int | None = None
    model_count: int | None = None
    last_checked_at: datetime | None = None
    error_message: str | None = None
    is_local: bool = False
    privacy_note_tr: str | None = None
    privacy_note_en: str | None = None


class AIControlCenter(BaseModel):
    mode: str
    fallback_chain: list[str]
    response_language: str
    providers: list[ProviderStatus]
    usage_today: TokenUsage = Field(default_factory=TokenUsage)
    usage_total: TokenUsage = Field(default_factory=TokenUsage)
    task_counts: dict[str, int] = Field(default_factory=dict)
    error_count_24h: int = 0
    local_only_mode: bool = False


# ---------------------------------------------------------------------------
# `.env` yazımına giden alanlar için güvenli tipler.
#
# Bu değerler `.env` dosyasına `ANAHTAR=deger` satırı olarak yazılır. Satır
# sonu ya da kontrol karakteri içeren bir değer, dosyaya FAZLADAN bir ortam
# değişkeni ataması enjekte ederdi (ör. SECRET_KEY veya
# AI_DEVELOPER_ALLOW_SHELL üzerine yazmak). Bu yüzden tip düzeyinde reddedilir.
# ---------------------------------------------------------------------------
_ENV_UNSAFE = re.compile(r"[\r\n\x00-\x1f\x7f]")


def _reject_env_injection(value: str) -> str:
    if _ENV_UNSAFE.search(value):
        raise ValueError("value must not contain newline or control characters")
    return value.strip()


def _validate_env_url(value: str) -> str:
    value = _reject_env_injection(value)
    if value and not value.startswith(("http://", "https://")):
        raise ValueError("url must start with http:// or https://")
    return value


EnvSafeStr = Annotated[
    str, StringConstraints(max_length=500), AfterValidator(_reject_env_injection)
]
EnvUrl = Annotated[
    str, StringConstraints(max_length=500), AfterValidator(_validate_env_url)
]
EnvProviderName = Literal["local", "nvidia", "openai_compat"]


class AIConfigUpdate(BaseModel):
    """Ayarlar ekranından güncellenebilen AI parametreleri.

    API anahtarları burada DÖNDÜRÜLMEZ; yalnızca ayarlanabilir ve maskelenmiş
    olarak gösterilir.
    """

    mode: Literal["local", "nvidia", "automatic"] | None = None
    fallback_chain: list[EnvProviderName] | None = Field(default=None, max_length=8)
    response_language: Literal["tr", "en", "auto"] | None = None
    local_enabled: bool | None = None
    local_base_url: EnvUrl | None = None
    local_model: EnvSafeStr | None = None
    local_timeout: int | None = Field(default=None, ge=5, le=900)
    local_max_tokens: int | None = Field(default=None, ge=1, le=32000)
    local_temperature: float | None = Field(default=None, ge=0, le=2)
    nvidia_enabled: bool | None = None
    nvidia_base_url: EnvUrl | None = None
    nvidia_model: EnvSafeStr | None = None
    nvidia_api_key: EnvSafeStr | None = None  # yalnızca yazma yönünde
    nvidia_timeout: int | None = Field(default=None, ge=5, le=900)
    nvidia_max_tokens: int | None = Field(default=None, ge=1, le=32000)
    nvidia_temperature: float | None = Field(default=None, ge=0, le=2)


class ConnectionTestResult(BaseModel):
    provider: str
    test_name: str
    result: Literal["PASS", "FAIL", "SKIPPED"]
    detail: str | None = None
    duration_ms: int | None = None


class ConnectionTestReport(BaseModel):
    provider: str
    overall: Literal["PASS", "FAIL", "SKIPPED"]
    tests: list[ConnectionTestResult]
    checked_at: datetime


class AITaskOut(ORMModel):
    id: int
    kind: AITaskKind
    status: AITaskStatus
    title: str
    provider: str | None = None
    model: str | None = None
    prompt_preview: str | None = None
    result_preview: str | None = None
    error_message: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int = 0
    fallback_used: bool = False
    attempted_providers: list[str] = Field(default_factory=list)
    file_changes: list[dict] = Field(default_factory=list)
    test_result: dict = Field(default_factory=dict)
    user_id: int | None = None
    started_at: datetime
    finished_at: datetime | None = None


class PromptTemplate(BaseModel):
    id: str
    category: str
    title_tr: str
    title_en: str
    prompt_tr: str
    prompt_en: str
    description_tr: str | None = None
    description_en: str | None = None
    requires_context: list[str] = Field(default_factory=list)
    icon: str | None = None


# ---------------------------------------------------------------------------
# Analiz istekleri - Statistics Engine + AI birleşimi
# ---------------------------------------------------------------------------
class AIAnalysisRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    scope: Literal[
        "student_performance",
        "declining_students",
        "training_suggestion",
        "weakest_stroke",
        "top_improvers",
        "competition_readiness",
        "attendance",
        "finance",
        "retention",
        "instructor_workload",
        "schedule_optimization",
        "free_lanes",
        "payment_risk",
        "general",
    ] = "general"
    student_id: int | None = None
    instructor_id: int | None = None
    pool_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    provider: ProviderName | Literal["auto"] = "auto"
    language: Literal["tr", "en", "auto"] = "auto"


class AIAnalysisResponse(BaseModel):
    """AI analiz yanıtı.

    `metrics` bölümü Statistics Engine tarafından hesaplanmış GERÇEK VERİDİR.
    `ai_interpretation` bölümü bir dil modelinin yorumudur ve kesin gerçek
    olarak sunulmamalıdır.
    """

    question: str
    scope: str
    # --- Gerçek veri ---
    metrics: dict[str, Any] = Field(default_factory=dict)
    metrics_summary_tr: str = ""
    metrics_summary_en: str = ""
    data_points: int = 0
    data_sufficient: bool = True
    # --- AI yorumu ---
    ai_available: bool = False
    ai_interpretation: str | None = None
    ai_possible_causes: list[str] = Field(default_factory=list)
    ai_recommendations: list[str] = Field(default_factory=list)
    ai_disclaimer_tr: str = (
        "Bu yorum bir yapay zekâ modeli tarafından üretilmiştir ve kesin gerçek "
        "değildir. Kararlarınızı yukarıdaki hesaplanmış verilere dayandırın."
    )
    ai_disclaimer_en: str = (
        "This interpretation was generated by an AI model and is not established "
        "fact. Base your decisions on the computed metrics above."
    )
    provider: str | None = None
    model: str | None = None
    duration_ms: int = 0
    task_id: int | None = None
    # --- HSP yönetişimi ---
    # Yapay zekâya veri gönderilmeden önce verilen politika kararı ve kanıtı.
    # `hsp_blocked_reason` doluysa modele hiçbir şey gönderilmemiştir;
    # yukarıdaki `metrics` yine de gerçek veridir ve geçerlidir.
    hsp_decision: str | None = None
    hsp_receipt_id: int | None = None
    hsp_pseudonymised: int = 0
    hsp_blocked_reason: str | None = None


# ---------------------------------------------------------------------------
# AI Developer Console
# ---------------------------------------------------------------------------
class DeveloperCommand(BaseModel):
    instruction: str = Field(min_length=3, max_length=8000)
    provider: ProviderName | Literal["auto"] = "auto"
    model: str | None = None
    auto_test: bool | None = None
    max_files: int = Field(default=8, ge=1, le=40)


class FileChange(BaseModel):
    path: str
    action: Literal["create", "modify", "delete"]
    diff: str | None = None
    original_size: int | None = None
    new_size: int | None = None
    lines_added: int = 0
    lines_removed: int = 0


class AgentStep(BaseModel):
    step: Literal[
        "READ",
        "SEARCH",
        "ANALYZE",
        "PLAN",
        "GENERATE_PATCH",
        "RUN_TEST",
        "SHOW_DIFF",
        "APPLY_PATCH",
        "ROLLBACK",
    ]
    status: Literal["pending", "running", "success", "failed", "skipped"]
    detail: str | None = None
    duration_ms: int | None = None
    output: str | None = None


class DeveloperPlanResponse(BaseModel):
    task_id: int
    instruction: str
    plan: list[str] = Field(default_factory=list)
    analysis: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)
    changes: list[FileChange] = Field(default_factory=list)
    patch_id: str | None = None
    test_result: dict[str, Any] | None = None
    requires_approval: bool = True
    apply_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    provider: str | None = None
    model: str | None = None


class PatchApplyRequest(BaseModel):
    patch_id: str
    confirm: bool
    run_tests_after: bool = True


class PatchApplyResult(BaseModel):
    success: bool
    patch_id: str
    checkpoint_id: str | None = None
    applied_files: list[str] = Field(default_factory=list)
    test_result: dict[str, Any] | None = None
    rolled_back: bool = False
    message: str


class RollbackRequest(BaseModel):
    checkpoint_id: str
    confirm: bool


class CommandPolicyInfo(BaseModel):
    """Terminal güvenlik politikasının şeffaf gösterimi."""

    shell_enabled: bool
    apply_enabled: bool
    project_root: str
    allowed_commands: list[str]
    blocked_patterns: list[str]
    write_scope: str
    requires_confirmation: list[str]


# ---------------------------------------------------------------------------
# CAIO
# ---------------------------------------------------------------------------
class CAIOFindingOut(ORMModel):
    id: int
    category: str
    severity: str
    title: str
    description: str
    recommendation: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    source: str
    status: str
    is_ai_generated: bool = False
    ai_provider: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class CAIORunRequest(BaseModel):
    include_ai: bool = True
    categories: list[str] = Field(default_factory=list)
    provider: ProviderName | Literal["auto"] = "auto"


class CAIOReport(BaseModel):
    run_at: datetime
    duration_ms: int
    # Ölçülen gerçek veriler
    observations: dict[str, Any] = Field(default_factory=dict)
    findings: list[CAIOFindingOut] = Field(default_factory=list)
    findings_by_severity: dict[str, int] = Field(default_factory=dict)
    # AI yorumu (varsa)
    ai_available: bool = False
    ai_summary: str | None = None
    ai_proposals: list[str] = Field(default_factory=list)
    provider: str | None = None


class CAIOFindingUpdate(BaseModel):
    status: Literal["open", "acknowledged", "in_progress", "resolved", "dismissed"]
    note: str | None = None
