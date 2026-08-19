# Yapay Zekâ Mimarisi

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'ndeki yapay zekâ katmanının nasıl
tasarlandığını, hangi dosyaların hangi işi yaptığını ve gerçek veri ile model
yorumunun neden birbirinden ayrı tutulduğunu anlatır. Amaç, sistemi hiçbir
yapay zekâ firmasına bağımlı bırakmadan, AI olmadan da tam çalışır durumda
tutmaktır.

**Sürüm:** 0.9.0 · **Kapsam:** `backend/app/services/ai/`, `backend/app/api/v1/ai*.py`,
`backend/app/api/v1/caio.py`, `backend/app/core/config.py`

---

## İçindekiler

1. [Tasarım İlkeleri](#1-tasarım-i̇lkeleri)
2. [Sağlayıcı Soyutlaması](#2-sağlayıcı-soyutlaması)
3. [Yönlendirme ve Fallback](#3-yönlendirme-ve-fallback)
4. [Model Yönlendirme](#4-model-yönlendirme)
5. [İstatistik + AI Boru Hattı](#5-i̇statistik--ai-boru-hattı)
6. [Görev Kaydı ve Token Takibi](#6-görev-kaydı-ve-token-takibi)
7. [Sağlık Kontrolü ve Bağlantı Testi](#7-sağlık-kontrolü-ve-bağlantı-testi)
8. [Prompt Kütüphanesi](#8-prompt-kütüphanesi)
9. [CAIO Ajanı](#9-caio-ajanı)
10. [Gizlilik](#10-gizlilik)
11. [Yeni Sağlayıcı Ekleme](#11-yeni-sağlayıcı-ekleme)

---

## 1. Tasarım İlkeleri

Yapay zekâ katmanı dört ilke üzerine kuruludur. Bu ilkeler kodda yorum
satırı değil, yapısal karşılığı olan kurallardır.

### 1.1 Tek sağlayıcıya bağımlılık yok

Tüm sağlayıcılar `AIProvider` soyut taban sınıfını uygular
(`backend/app/services/ai/base.py`). Uygulama kodunun hiçbir yerinde
"LM Studio", "NVIDIA" veya "OpenAI" adı geçen özel bir dal yoktur; çağrılar
`AIRouter` üzerinden yapılır. Yeni bir sağlayıcı eklemek, mevcut analiz veya
sohbet kodunu değiştirmeyi gerektirmez (bkz. [Bölüm 11](#11-yeni-sağlayıcı-ekleme)).

Üç sağlayıcı hazır gelir:

| Ad | Sınıf | Tür | Varsayılan |
|----|-------|-----|-----------|
| `local` | `LMStudioProvider` | Yerel (LM Studio) | Etkin |
| `nvidia` | `NvidiaProvider` | Bulut (build.nvidia.com) | Kapalı |
| `openai_compat` | `OpenAICompatProvider` | Genel OpenAI uyumlu (vLLM, LiteLLM, Ollama, kendi sunucunuz) | Kapalı |

### 1.2 AI olmadan sistem çalışır

Yapay zekâ katmanı **isteğe bağlı bir eklentidir**, çekirdek bir bağımlılık
değil. Hiçbir sağlayıcı erişilebilir değilse:

* `POST /api/v1/ai/analyze` yine **200** döner; yanıtta yalnızca hesaplanmış
  metrikler bulunur, `ai_available=false` ve `ai_interpretation=null` olur.
* CAIO kural motoru bulgularını AI'sız üretmeye devam eder
  (`caio.analyze()` tamamen deterministiktir).
* Öğrenci, ders, yoklama, finans, performans ve rapor modüllerinin hiçbiri
  yapay zekâ katmanına dokunmaz.

Kod tarafındaki karşılığı `registry.py` başındaki sözleşmedir: fallback zinciri
tükendiğinde `AIProviderError` fırlatılır, çağıran katman bunu yakalar ve
"AI kullanılamıyor" durumuna düşer — uygulama çökmez.

### 1.3 Gerçek veri ile AI yorumu ayrılır

Bir dil modeli sayı üretmez; sayıları **Statistics Engine** üretir. Akış her
zaman şu sıradadır:

```
Veritabanı → statistics_engine → yapılandırılmış metrikler → AI → doğal dil yorumu
```

`AIAnalysisResponse` şemasında (`backend/app/schemas/ai.py`) bu ayrım alan
düzeyinde korunur: `metrics`, `metrics_summary_tr/en`, `data_points` gerçek
veridir; `ai_interpretation`, `ai_possible_causes`, `ai_recommendations` bir
model yorumudur ve yanıt gövdesinde her zaman bir sorumluluk reddi
(`ai_disclaimer_tr` / `ai_disclaimer_en`) ile birlikte döner. Arayüzde
(AI Merkezi > AI Analizi) bu iki blok ayrı panellerde gösterilir.

Sistem istemi de aynı kuralı modele dayatır (`prompts.py`):

> "Sana verilen HESAPLANMIŞ İSTATİSTİKLER gerçek verilerdir. Sayıları asla
> değiştirme veya uydurma."

### 1.4 Sırlar korunur

* API anahtarları yalnızca ortam değişkenlerinden okunur; kaynak kodda
  gömülü anahtar yoktur (`config.py` başlığındaki kural).
* `GET /api/v1/ai/config` anahtarları **asla** tam döndürmez; `mask_secret()`
  ile `abc************wxyz` biçiminde maskeler.
* Sağlayıcıdan gelen HTTP hata gövdesi, kullanıcıya gösterilmeden önce
  `redact()` filtresinden geçirilir (`base.py` içindeki `_post`), çünkü hata
  gövdesi anahtarı yansıtabilir.
* Log kayıtları `RedactingFilter` ile taranır; `nvapi-`, `sk-`, `ghp_`,
  `Bearer ...` ve `api_key=`/`password=` kalıpları `***REDACTED***` olur.
* İstem metinleri veritabanına yalnızca `AI_LOG_PROMPTS=true` iken yazılır
  (varsayılan `false`, bkz. [Bölüm 10](#10-gizlilik)).

---

## 2. Sağlayıcı Soyutlaması

### 2.1 Sınıf hiyerarşisi

```
AIProvider (ABC)                          backend/app/services/ai/base.py
│   name / display_name / is_local
│   chat()            @abstractmethod
│   stream()          @abstractmethod
│   list_models()     @abstractmethod
│   health()          @abstractmethod
│   enabled           @abstractproperty
│   test_connection() → health()          (varsayılan uygulama)
│   estimate_usage()                      (varsayılan uygulama)
│   public_info()
│
└── OpenAICompatibleProvider              /v1/chat/completions konuşan her sunucu
    │   _headers() · _resolve_model() · _post()
    │   _declared_capabilities()
    │
    ├── LMStudioProvider     name="local"          is_local=True   providers.py
    ├── NvidiaProvider       name="nvidia"         is_local=False  providers.py
    └── OpenAICompatProvider name="openai_compat"  is_local=False  providers.py
```

### 2.2 Ortak metotlar

| Metot | İmza (özet) | Döndürür | Notlar |
|-------|-------------|----------|--------|
| `chat` | `chat(messages, *, model, temperature, max_tokens, json_mode)` | `ChatResult` | Senkron tek atımlık istek. `json_mode=True` iken `response_format={"type":"json_object"}` gönderilir. |
| `stream` | `stream(messages, *, model, temperature, max_tokens)` | `Iterator[str]` | SSE `data:` satırlarını ayrıştırır, `[DONE]` ile biter. |
| `test_connection` | `test_connection()` | `HealthResult` | Taban sınıfta `health()`'e delege edilir. |
| `list_models` | `list_models(use_cache=True)` | `list[ModelDescriptor]` | `GET {base_url}/models`. Hata durumunda boş liste (istisna fırlatmaz). |
| `health` | `health()` | `HealthResult` | Gecikme + model sayısı ölçer. **Asla istisna fırlatmaz.** |
| `estimate_usage` | `estimate_usage(messages)` | `Usage` | Kaba tahmin: karakter sayısı / 3.7 (Türkçe token yoğunluğuna göre ayarlı). |

### 2.3 Veri sınıfları

```python
@dataclass
class ChatResult:
    content: str
    provider: str
    model: str
    usage: Usage           # prompt_tokens / completion_tokens / total_tokens
    duration_ms: int
    finish_reason: str | None
    raw: dict[str, Any]

@dataclass
class ModelDescriptor:
    id: str
    provider: str
    owned_by: str | None
    capabilities: list[str]
    capability_source: str      # "api" | "unknown"
    context_length: int | None

@dataclass
class HealthResult:
    provider: str
    available: bool
    latency_ms: int | None
    model_count: int | None
    endpoint: str | None
    error: str | None
```

### 2.4 `OpenAICompatibleProvider` taban sınıfı

Alt sınıflar yalnızca **yapılandırma** sağlar; HTTP mantığı tek yerdedir:

* `_resolve_model()` — açık model → varsayılan model → sunucudaki ilk model
  sırasıyla çözer. Hiç model yoksa `AIProviderError("Kullanılabilir model bulunamadı")`.
* `_post()` — `httpx.Client` ile POST atar. Zaman aşımı → "Zaman aşımı (Ns)",
  bağlantı hatası → "Bağlantı hatası: <TipAdı>", HTTP ≥ 400 → maskelenmiş gövde.
* `chat()` — yanıt boşsa `reasoning_content` / `reasoning` alanlarına da bakar
  (bazı akıl yürütme modelleri içeriği orada döndürür).
* `enabled` — `_enabled and bool(base_url)`. `NvidiaProvider` bunu daraltır:
  **API anahtarı yoksa bulut sağlayıcı etkin sayılmaz.**

---

## 3. Yönlendirme ve Fallback

Yönlendirici: `AIRouter` (`backend/app/services/ai/registry.py`).

### 3.1 `resolve_chain(preferred)` mantığı

```python
def resolve_chain(self, preferred: str = "auto") -> list[str]:
    if preferred and preferred != "auto":
        return [preferred]            # 1) Kullanıcı açıkça seçtiyse: fallback YOK

    mode = settings.ai_default_mode
    if mode == "local":
        return ["local"]              # 2) Yalnızca yerel
    if mode == "nvidia":
        return ["nvidia"]             # 3) Yalnızca bulut

    chain = [                         # 4) automatic: zinciri filtrele
        name for name in settings.fallback_chain_list
        if (provider := get_provider(name)) is not None and provider.enabled
    ]
    return chain or ["local"]
```

| Durum | Zincir | Açıklama |
|-------|--------|----------|
| İstekte `provider="nvidia"` | `["nvidia"]` | Kullanıcı bilinçli seçim yaptı; başarısız olursa **fallback denenmez**. |
| `AI_DEFAULT_MODE=local` | `["local"]` | Kapalı devre / gizlilik modu. |
| `AI_DEFAULT_MODE=nvidia` | `["nvidia"]` | Yalnızca bulut. |
| `AI_DEFAULT_MODE=automatic` | `AI_FALLBACK_CHAIN` sırası, yalnızca etkin sağlayıcılar | Varsayılan: `local,nvidia`. |
| Zincir boş kaldı | `["local"]` | Güvenli varsayılan. |

### 3.2 Hata durumunda sıradakine geçiş

`AIRouter.chat()` zinciri sırayla dener:

1. Sağlayıcı yok veya `enabled=False` → hata listesine `"<ad>: devre dışı"`
   eklenir, **denenen listesine yazılmaz**, sıradakine geçilir.
2. Sağlayıcı denenir, `attempted` listesine eklenir.
3. `AIProviderError` yakalanırsa `ai` günlüğüne
   `"Sağlayıcı başarısız (%s), sıradakine geçiliyor"` yazılır ve döngü devam eder.
4. Başarı → `(ChatResult, attempted, fallback_used)` döner.
   `fallback_used = index > 0`, yani ilk sağlayıcı dışında bir sağlayıcı
   yanıt verdiyse `True`.
5. Zincir tükenirse:
   `AIProviderError("router", "Tüm sağlayıcılar başarısız: " + ilk 3 hata)`.

```python
result, attempted, fallback_used = AIRouter(db).chat(
    [ChatMessage(role="user", content="Devam oranını yorumla")],
    preferred="auto",
    task="general",
)
# attempted -> ["local", "nvidia"]   fallback_used -> True
```

`attempted` ve `fallback_used` değerleri `ai_tasks` tablosuna yazılır ve
`POST /api/v1/ai/chat` yanıtında `attempted_providers` / `fallback_used` olarak
istemciye döner — hangi sağlayıcının gerçekten yanıtladığı her zaman görünürdür.

### 3.3 Akış (streaming) fallback'i

`AIRouter.stream()` aynı zinciri kullanır, ancak dikkat edilmesi gereken bir
davranış farkı vardır: hata akış **başladıktan sonra** oluşursa, o ana kadar
gönderilmiş parçalar istemciye ulaşmış olur ve sıradaki sağlayıcı baştan
üretmeye başlar. Bu nedenle akış uçları (`POST /api/v1/ai/chat/stream`)
kritik/otomatik iş akışlarında değil, etkileşimli sohbette kullanılmalıdır.

---

## 4. Model Yönlendirme

Kaynak: `backend/app/services/ai/providers.py`, uç:
`GET /api/v1/ai/routing/tasks`, arayüz: **AI Merkezi > Model Yönlendirme**.

### 4.1 `TASK_MODEL_HINTS` tablosu

Bu tablo bir **öneri mekanizmasıdır**, atama kuralı değil. Router bir modeli
göreve önermeden önce sağlayıcının o modeli gerçekten sunduğunu
`list_models()` ile doğrular.

| Görev | Etiket (TR) | Etiket (EN) | Aranan ad parçaları |
|-------|-------------|-------------|---------------------|
| `general` | Genel analiz | General analysis | `gemma`, `llama`, `qwen3`, `mistral`, `phi` |
| `reasoning` | Akıl yürütme | Reasoning | `gemma`, `qwen3`, `llama-3.3`, `deepseek` |
| `vision` | Görsel analiz | Vision | `vl`, `vision`, `moondream`, `llava`, `pixtral` |
| `math` | Matematiksel analiz | Mathematical analysis | `math`, `qwen2.5-math` |
| `code` | Kod üretimi | Code generation | `coder`, `code`, `qwen2.5-coder`, `starcoder`, `codestral` |
| `embedding` | Vektör gömme | Embeddings | `embed`, `nomic-embed`, `bge` |
| `medical` | Sağlık metni | Medical text | `biomistral`, `medical`, `med` |

Hangi görevin nerede kullanıldığı:

| Çağıran | `task` değeri |
|---------|---------------|
| `analysis.run_analysis` — antrenörlük kapsamları | `reasoning` |
| `analysis.run_analysis` — analitik kapsamlar | `general` |
| `caio.run_caio` | `reasoning` |
| `agent.plan_changes` | `code` |

### 4.2 `capability_source` değerleri

`suggest_model_for_task(task, available_models)` üç aşamalı çalışır ve seçimin
**nereden geldiğini** birlikte döndürür:

| Değer | Ne anlama gelir | Arayüzde |
|-------|-----------------|----------|
| `api` | Sağlayıcı API'si modelin yeteneğini `capabilities` / `modalities` / `supported_features` alanında **açıkça bildirmiştir**. | `verified: true` — doğrulanmış |
| `heuristic` | Yalnızca model **adında** anahtar kelime eşleşmiştir. Yetenek doğrulanmamıştır. | `verified: false` — tahmin |
| `fallback` | Hiçbir eşleşme yok; listedeki ilk model önerilmiştir. | `verified: false` |
| `unavailable` | Sağlayıcıda hiç model yok (sunucu kapalı veya model yüklenmemiş). | Öneri yok |

`ModelDescriptor.capability_source` alanı ise doğrudan `list_models()` içinde
belirlenir: API bir yetenek bildirdiyse `"api"`, aksi halde `"unknown"`.

### 4.3 Neden varsayım yapılmıyor?

Model adından yetenek çıkarmak yanlış sonuç üretir: `llava` adı geçen bir
model gerçekten görsel girdi kabul etmeyebilir, `qwen2.5-coder` bir sohbet
türevi olabilir, aynı ada sahip iki quantization farklı bağlam uzunluğuna
sahip olabilir. Sistem bu nedenle **ad eşleşmesini gerçek olarak sunmaz**:

```python
@staticmethod
def _declared_capabilities(item: dict) -> list[str]:
    """API'nin AÇIKÇA bildirdiği yetenekleri döndürür; tahmin yapmaz."""
```

`GET /api/v1/ai/routing/tasks` yanıtı bu ayrımı metinle de taşır:

```json
{
  "tasks": [
    {
      "task": "vision",
      "label": "Görsel analiz",
      "keywords": ["vl", "vision", "moondream", "llava", "pixtral"],
      "providers": {
        "local": {
          "suggested_model": "google/gemma-4-12b-qat",
          "capability_source": "fallback",
          "verified": false
        }
      }
    }
  ],
  "note_tr": "Yetenek bilgisi yalnızca sağlayıcı API'si bildirdiğinde doğrulanmış sayılır. 'heuristic' kaynağı model adına dayanan tahmindir."
}
```

> **Bilinen kısıt:** LM Studio `/v1/models` yanıtında yetenek alanı
> bildirmediği için yerel modeller için kaynak neredeyse her zaman
> `heuristic` veya `fallback` olur. Bu bir hata değil, kasıtlı
> "doğrulanmadıysa doğrulanmış deme" davranışıdır.

---

## 5. İstatistik + AI Boru Hattı

Kaynak: `backend/app/services/ai/analysis.py`, uç: `POST /api/v1/ai/analyze`.

### 5.1 Akış

```
AIAnalysisRequest (question, scope, student_id, tarih aralığı, provider, language)
        │
        ├─ 1) _resolve_language()      istek dili → AI_RESPONSE_LANGUAGE → kullanıcı dili
        │
        ├─ 2) SCOPE_COLLECTORS[scope]  ► statistics_engine  ► GERÇEK METRİKLER
        │        döndürür: (metrics, data_points, summary_tr, summary_en)
        │
        ├─ 3) data_points < 3 ?  ──► EVET: ai_available=False, yalnızca metrikler döner (AI çağrılmaz)
        │                              HAYIR ↓
        ├─ 4) sistem istemi seç        coach_system_prompt | analyst_system_prompt
        │
        ├─ 5) start_task(kind=ANALYSIS)
        │
        ├─ 6) AIRouter.chat(system + user)       user içeriği = soru + özet + JSON metrikler (≤6000 karakter)
        │
        ├─ 7) _parse_sections()        yorum / olası nedenler / öneriler
        │
        └─ 8) finish_task()  ──►  AIAnalysisResponse
```

`MIN_DATA_POINTS = 3`: üçten az veri noktasıyla model çağrılmaz. Bu, "üç
kayıttan trend çıkarmak" gibi güvenilmez yorumları kaynağında keser.

### 5.2 `SCOPE_COLLECTORS` tablosu (14 kapsam)

| `scope` | Toplayıcı | Veri kaynağı | `data_points` neyi sayar |
|---------|-----------|--------------|--------------------------|
| `student_performance` | `_student_performance_metrics` | `student_performance_summary()` | Öğrencinin toplam performans kaydı |
| `training_suggestion` | `_student_performance_metrics` | Aynı | Aynı |
| `weakest_stroke` | `_weakest_stroke_metrics` | Aynı + `focus="weakest_stroke"` | Aynı |
| `declining_students` | `_declining_metrics` | `find_declining_athletes(90 gün, ≥4 kayıt)` | Gerileyen sporcu-etkinlik sayısı |
| `top_improvers` | `_top_improvers_metrics` | `find_top_improvers(90 gün, ≥3 kayıt)` | Gelişen sporcu-etkinlik sayısı |
| `competition_readiness` | `_readiness_metrics` | `competition_readiness(60 gün)` | Skorlanan sporcu-etkinlik sayısı |
| `attendance` | `_attendance_metrics` | `attendance_statistics()` | Geldi + gelmedi + geç + mazeretli |
| `retention` | `_retention_metrics` | `student_statistics()` + `cohort_retention(6 ay)` | Toplam öğrenci |
| `finance` | `_finance_metrics` | `Payment` / `Expense` / `Invoice` toplamları | Gelir veya gider varsa 1 |
| `instructor_workload` | `_instructor_metrics` | `instructor_statistics()` | Eğitmen satırı sayısı |
| `schedule_optimization` | `_schedule_metrics` | `pool_statistics()` | 1 (havuz özeti) |
| `free_lanes` | `_schedule_metrics` | Aynı | 1 |
| `payment_risk` | `_payment_risk_metrics` | Geciken faturalar + 14 gün içinde biten üyelikler | Geciken fatura + biten üyelik |
| `general` | `_general_metrics` | `dashboard_summary()` | Toplam öğrenci |

Tanımsız bir `scope` gelirse `_general_metrics` kullanılır (`.get(..., _general_metrics)`).

Antrenörlük istemi (`coach_system_prompt`) şu dört kapsamda devreye girer:
`training_suggestion`, `student_performance`, `weakest_stroke`,
`competition_readiness`. Diğerlerinde analist istemi kullanılır.

### 5.3 `AIAnalysisResponse` alanlarının anlamı

| Alan | Kaynak | Anlamı |
|------|--------|--------|
| `question` | İstek | Sorulan soru |
| `scope` | İstek | Hangi toplayıcının çalıştığı |
| **`metrics`** | Statistics Engine | **GERÇEK VERİ.** Hesaplanmış, doğrulanabilir sayılar. |
| **`metrics_summary_tr` / `_en`** | Statistics Engine | Aynı verinin insan okunur özeti (AI'ya da bu gönderilir) |
| `data_points` | Toplayıcı | Analizin dayandığı kayıt sayısı |
| `data_sufficient` | `data_points >= 3` | `false` ise AI hiç çağrılmamıştır |
| `ai_available` | Router | Model yanıt verdi mi |
| **`ai_interpretation`** | Model | **YORUM.** Kesin gerçek değildir. |
| `ai_possible_causes` | Model (`## Olası Nedenler`) | En fazla 8 madde |
| `ai_recommendations` | Model (`## Öneriler`) | En fazla 8 madde |
| `ai_disclaimer_tr` / `_en` | Sabit | Arayüzde yorum panelinin altında gösterilir |
| `provider` / `model` | Router | Yanıtı kim üretti |
| `duration_ms` | Sağlayıcı | Model çağrısının süresi |
| `task_id` | `ai_tasks` | Görev geçmişindeki kayıt kimliği |

`_parse_sections()` model yanıtını başlıklara göre böler; hem Türkçe
(`Olası Nedenler`, `Öneriler`, `Yorum`, `Değerlendirme`, `Analiz`) hem İngilizce
(`Possible Causes`, `Recommendations`, `Interpretation`, `Assessment`)
başlıkları tanınır. Başlık bulunamazsa tüm metin `ai_interpretation` olur.

### 5.4 Antrenman planı üretimi

`generate_training_plan()` aynı boru hattını `scope="training_suggestion"` ile
çalıştırır ve sonucu `training_plans` tablosuna **`is_approved=False`** olarak
yazar. Plan, bir eğitmen onaylamadan yürürlüğe girmez; yanıtta
`requires_approval: true` ve dil karşılığı `disclaimer` alanı döner.

Uç: `POST /api/v1/ai/training-plan/{student_id}?weeks=4`
(izinler: `ai:use` **ve** `performance:read`, `weeks` 1–12 arasına sıkıştırılır).

---

## 6. Görev Kaydı ve Token Takibi

### 6.1 `ai_tasks` tablosu

Model: `AITask` (`backend/app/models/system.py`), indeks:
`ix_ai_task_kind_status` (`kind`, `status`).

| Sütun | Tip | Açıklama |
|-------|-----|----------|
| `kind` | `String(30)` | `AITaskKind`: `chat`, `analysis`, `developer`, `caio` vb. |
| `status` | `String(20)` | `AITaskStatus`: `pending` / `running` / `success` / `failed` |
| `title` | `String(300)` | Görev başlığı (istem ilk 280–300 karakteri) |
| `provider` / `model` | `String` | Yanıtı üreten sağlayıcı ve model |
| `prompt_preview` | `Text` | **Yalnızca `AI_LOG_PROMPTS=true` iken doldurulur** (≤2000 karakter) |
| `result_preview` | `Text` | Yanıtın ilk 2000 karakteri |
| `error_message` | `Text` | Başarısızlık nedeni (≤2000 karakter) |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | `Integer` | Sağlayıcının `usage` alanından |
| `duration_ms` | `Integer` | Model çağrı süresi |
| `fallback_used` | `Boolean` | İlk sağlayıcı dışında biri yanıtladıysa `true` |
| `attempted_providers` | `JSON` | Denenen sağlayıcı sırası |
| `file_changes` | `JSON` | Developer ajanı: diff hariç dosya değişiklik özeti |
| `test_result` | `JSON` | Developer ajanı: pytest sonucu |
| `user_id` | FK → `users.id` | `ON DELETE SET NULL` |
| `started_at` / `finished_at` | `DateTime(tz)` | |

### 6.2 `start_task` / `finish_task`

```python
from app.models.enums import AITaskKind
from app.services.ai.registry import AIRouter, finish_task, start_task
from app.services.ai.base import AIProviderError, ChatMessage

task = start_task(
    db,
    kind=AITaskKind.ANALYSIS,
    title="[attendance] Devam oranları neden düştü?",
    user_id=user.id,
    prompt=user_content,          # yalnızca AI_LOG_PROMPTS=true ise saklanır
)

try:
    result, attempted, fallback_used = AIRouter(db).chat(messages, task="general")
    finish_task(db, task, result=result, attempted=attempted, fallback_used=fallback_used)
except AIProviderError as exc:
    finish_task(db, task, error=str(exc))     # status=FAILED, error_message dolu
```

* `start_task` kaydı `RUNNING` olarak açar ve hemen commit eder — çağrı ortada
  kesilse bile görev geçmişinde iz kalır.
* `finish_task` sonuç varsa `SUCCESS`, yoksa `FAILED` yazar; token alanlarını
  `ChatResult.usage`'dan doldurur.

### 6.3 Token toplamları

`control_center_data(db)` iki toplam üretir ve
`GET /api/v1/ai/control-center` ile döner:

* `usage_today` — bugün başlayan görevlerin prompt/completion/total toplamı
* `usage_total` — tüm zamanlar
* `task_counts` — duruma göre görev sayısı
* `error_count_24h` — son 24 saatteki başarısız görev sayısı
* `local_only_mode` — `AI_DEFAULT_MODE == "local"`

Görev geçmişi filtrelenebilir: `GET /api/v1/ai/tasks?kind=analysis&status=failed&provider=nvidia`.

---

## 7. Sağlık Kontrolü ve Bağlantı Testi

### 7.1 Sağlık kontrolü (hafif)

`check_health(name, use_cache=True)` — `GET {base_url}/models` çağırır, gecikme
ve model sayısı ölçer. Sonuç **30 saniye** önbelleklenir (`_HEALTH_CACHE_TTL`),
böylece her sayfa yenilemesi ağ trafiği üretmez. `record_health(db, name)`
önbelleği atlar ve sonucu `ai_provider_health` tablosuna yazar
(`POST /api/v1/ai/providers/{provider}/health`).

### 7.2 Bağlantı testi (kapsamlı, 6 aşama)

`run_connection_tests(name)` — uç: `POST /api/v1/ai/providers/{provider}/test`
(izin: `ai:configure`), arayüz: **AI Merkezi > Kontrol Merkezi > Bağlantıyı Test Et**.

| # | Test | Ne yapar | Ne doğrular |
|---|------|----------|-------------|
| 1 | `connection` | `provider.health()` | Sunucu ayakta mı, uç nokta doğru mu, gecikme ne kadar. **FAIL ise kalan 5 test `SKIPPED` olur.** |
| 2 | `model` | `list_models(use_cache=False)` | Sunucuda yüklü/erişilebilir model var mı; ilk 4 model adı raporlanır. |
| 3 | `simple_prompt` | "Türkiye'nin başkenti nedir? Tek kelime yaz." (`max_tokens=1024`, `temperature=0`) | Model gerçekten üretim yapıyor mu; boş yanıt döndürmüyor mu. |
| 4 | `json_output` | `{"status":"ok","value":42}` istenir, `json_mode=True` | Model yapılandırılmış çıktı üretebiliyor mu. Kod ```` ``` ```` çitlerini temizler ve `{...}` bloğunu ayrıştırır. Analiz ve Developer akışları JSON'a bağımlı olduğu için kritiktir. |
| 5 | `timeout` | Yapılandırılmış zaman aşımını raporlar | Bilgilendirme amaçlıdır; her zaman `PASS` döner ve isteklerin kaç saniyede kesileceğini söyler. |
| 6 | `streaming` | `stream()` ile ilk 5 parça alınır | SSE akışı çalışıyor mu (sohbet ekranındaki canlı yazım için). |

Genel sonuç: tüm testler `PASS` veya `SKIPPED` ise `PASS`, aksi halde `FAIL`.
Sağlayıcı devre dışıysa (veya bulut sağlayıcıda anahtar tanımlı değilse)
altı testin tamamı `SKIPPED` döner ve genel sonuç `SKIPPED` olur.

Test çıktılarında **API anahtarı görünmez**; hata gövdeleri `redact()`
filtresinden geçmiştir. Her test çalıştırması denetim kaydına (`audit`)
`ai_test` eylemiyle yazılır.

---

## 8. Prompt Kütüphanesi

Kaynak: `backend/app/services/ai/prompts.py`, uç: `GET /api/v1/ai/prompts?category=...`

### 8.1 Sistem istemleri

| Sabit | Kullanan | Öne çıkan kurallar |
|-------|----------|--------------------|
| `SYSTEM_ANALYST_TR` / `_EN` | Analitik kapsamlar | Sayıları değiştirme; veride olmayanı uydurma; korelasyonu nedensellik sayma; birey hakkında kesin performans yargısı verme; tıbbi tanı koyma. Biçim: `## Yorum` / `## Olası Nedenler` / `## Öneriler` |
| `SYSTEM_COACH_TR` / `_EN` | Antrenörlük kapsamları | Dereceleri değiştirme; yaşa ve seviyeye uygun öner; aşırı yüklenme riskine dikkat et; sağlık şüphesinde sağlık personeline yönlendir; **öneri eğitmen onayı olmadan uygulanmaz**. Biçim: `## Değerlendirme` / `## Odak Alanları` / `## Haftalık Plan` / `## Ölçüm Noktaları` |
| `SYSTEM_DEVELOPER` | AI Developer Console | Yalnızca gösterilen dosyalara dayan; değişiklikleri minimal tut; mevcut stile uy; sır yazma, SQL enjeksiyonu üretme, RBAC'ı atlama; yanıtı istenen JSON şemasında döndür |
| `SYSTEM_CAIO` | CAIO ajanı | Ölçümler gerçektir, uydurma sayı ekleme; öneriler önceliklendirilmiş olsun; **üretim koduna doğrudan değişiklik yapamazsın**; her öneri için neden/etki/efor belirt |

### 8.2 Hazır prompt kütüphanesi (18 şablon, 5 kategori)

Her şablon `PromptTemplate` şemasındadır: `id`, `category`, `title_tr/en`,
`prompt_tr/en`, `description_tr/en`, `requires_context`, `icon`.

| Kategori | Şablon `id` | Başlık (TR) | Bağlam gereksinimi |
|----------|-------------|-------------|--------------------|
| `performance` | `student_performance` | Öğrenci performansını analiz et | `student_id` |
| `performance` | `declining_students` | Performansı düşen öğrencileri bul | — |
| `performance` | `training_suggestion` | 4 haftalık antrenman önerisi oluştur | `student_id` |
| `performance` | `weakest_stroke` | En zayıf yüzme stilini belirle | `student_id` |
| `performance` | `top_improvers` | Son 10 antrenmanda en çok gelişenler | — |
| `performance` | `competition_readiness` | Yarışma öncesi hazır sporcular | — |
| `operations` | `schedule_optimization` | Ders programını optimize et | — |
| `operations` | `free_lanes` | Boş kulvarları bul | — |
| `operations` | `instructor_balance` | Antrenör yükünü dengele | — |
| `operations` | `attendance_analysis` | Devam oranlarını analiz et | — |
| `finance` | `payment_risk` | Ödeme riski taşıyan üyelikleri göster | — |
| `management` | `retention_analysis` | Öğrenci kaybı neden arttı? | — |
| `management` | `weekly_report` | Bu haftanın performans raporunu oluştur | — |
| `developer` | `dev_analyze_errors` | Kod hatalarını analiz et | — |
| `developer` | `dev_write_test` | Test yaz | `{module}` yer tutucusu |
| `developer` | `dev_refactor` | Bu modülü refactor et | `{module}` yer tutucusu |
| `developer` | `dev_optimize_db` | Database sorgularını optimize et | — |
| `developer` | `dev_add_export` | Ekrana Excel export ekle | — |

Örnek — performans kategorisindeki şablonları çekmek:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "http://127.0.0.1:8000/api/v1/ai/prompts?category=performance"
```

`{student}` ve `{module}` yer tutucuları arayüz tarafından seçilen kayıtla
doldurulur; `requires_context` alanı hangi kimliğin gerekli olduğunu söyler.

---

## 9. CAIO Ajanı

CAIO = *Chief AI Officer*. Kaynak: `backend/app/services/ai/caio.py`,
uçlar `/api/v1/ai/caio/*`, arayüz: **CAIO** ekranı (`/caio`, izin `ai:caio`).

> CAIO üretim koduna **kendi başına değişiklik yapamaz**. Yalnızca gözlem
> yapar, bulgu üretir ve öneri sunar. Yama üretimi ve uygulama, AI Developer
> Console'un onay akışından geçer.

### 9.1 Observe → Analyze → Propose

```
observe(db)                  ölçülebilir gerçekler toplanır (AI çağrısı YOK)
    ↓
analyze(observations)        kural motoru → deterministik bulgular (AI çağrısı YOK)
    ↓
caio_findings tablosuna yaz  aynı başlık "open" ise yinelenmez, kanıt güncellenir
    ↓
[include_ai=true ise] AIRouter.chat(SYSTEM_CAIO, ölçümler + kural bulguları)
    ↓
ai_summary (≤5 cümle) + ai_proposals (≤5 madde) → "ai_suggestion" bulguları
    ↓
SystemEvent("caio_run") kaydı + açık bulguların tazelenmiş listesi
```

`POST /api/v1/ai/caio/run` gövdesi: `{"include_ai": true, "categories": [], "provider": "auto"}`.
`include_ai=false` gönderilirse veya hiçbir sağlayıcı erişilebilir değilse
kural motoru sonuçları yine tam olarak döner — **CAIO AI olmadan da çalışır.**
Yalnızca ölçüm almak için: `GET /api/v1/ai/caio/observe` (hiç AI çağırmaz).

### 9.2 Gözlem kategorileri (6)

| Kategori | Fonksiyon | Ne ölçer |
|----------|-----------|----------|
| `logs` | `_observe_logs()` | `logs/*.log` dosyalarının son 400 KB'ı; hata/uyarı sayısı, normalize edilmiş imzalarla en sık 10 hata |
| `ai_usage` | `_observe_ai_usage(db)` | Toplam/başarılı/başarısız görev, başarı oranı, **yerel oran**, bulut token sayısı, ortalama süre, fallback sayısı, türe göre dağılım |
| `code_quality` | `_observe_code_quality()` | Backend/frontend dosya ve satır sayısı, test dosyası sayısı, test/kaynak oranı, TODO-FIXME-XXX sayısı, 700 satırı aşan dosyalar, test edilmemiş servis modülleri |
| `database` | `_observe_database(db)` | Öğrenci/ders/yoklama/ödeme/fatura/performans kayıt sayıları, veritabanı boyutu, veri kalitesi (eksik doğum tarihi, eksik iletişim, rızasız aktif öğrenci, yoklaması alınmamış geçmiş dersler), takvim çakışmaları |
| `security` | `_observe_security(db)` | Son 24 saatteki başarısız girişler, kilitli hesaplar, parolasını değiştirmemiş kullanıcılar, süper kullanıcı sayısı, `.env` var mı / `.gitignore`'da mı, debug modu, kabuk ve yama izinleri, istem loglama |
| `backups` | `_observe_backups(db)` | Toplam/doğrulanmış/bozuk yedek, son doğrulanmış yedekten bu yana geçen gün, zamanlama etkin mi, toplam boyut |

### 9.3 Kural motorunun ürettiği bulgu türleri

`analyze()` tamamen deterministiktir — aynı gözlemden her zaman aynı bulguyu
üretir ve hiçbir model çağırmaz.

| Kategori | Önem | Tetikleyen koşul |
|----------|------|------------------|
| `security` | `critical` | `.env` var ama `.gitignore` içinde değil |
| `security` | `high` | Üretim ortamında `APP_DEBUG=true` |
| `security` | `high` | Son 24 saatte 20'den fazla başarısız giriş |
| `security` | `medium` | Varsayılan parolasını değiştirmemiş kullanıcı var |
| `security` | `medium` | `AI_DEVELOPER_ALLOW_SHELL=true` |
| `security` | `low` | 3'ten fazla süper kullanıcı |
| `backup` | `high` | Hiç yedek yok |
| `backup` | `high` | Bozuk yedek var |
| `backup` | `medium` | Son doğrulanmış yedek 7 günden eski |
| `testing` | `medium` | Test/kaynak oranı %10'un altında |
| `testing` | `medium` | Test edilmemiş servis modülü var |
| `technical_debt` | `low` | 20'den fazla TODO/FIXME/XXX |
| `technical_debt` | `low` | 700 satırı aşan dosyalar var |
| `reliability` | `high` | Loglarda 50'den fazla hata |
| `reliability` | `medium` | Loglarda 10–50 arası hata |
| `data_quality` | `medium` | 5'ten fazla geçmiş derste yoklama alınmamış |
| `compliance` | `medium` | KVKK rızası olmayan aktif öğrenci var |
| `operations` | `high` | Takvimde çakışma var (−7 / +30 gün penceresi) |
| `ai_quality` | `medium` | AI görev başarı oranı %70'in altında |
| `ai_quality` | `medium` | Son 24 saatte 5'ten fazla başarısız AI görevi |
| `cost` | `low` | Yerel oran %50'nin altında **ve** buluta 50.000'den fazla token gönderilmiş |
| `ai_suggestion` | `info` | AI'nın ürettiği ek öneriler (`is_ai_generated=true`) |

Bulgular önem sırasına göre sıralanır:
`critical → high → medium → low → info` (`SEVERITY_ORDER`).

Her bulgu `CAIOFinding` olarak saklanır: `category`, `severity`, `title`,
`description`, `recommendation`, `evidence` (JSON kanıt), `source`
(`rule_engine` veya `ai`), `status`, `is_ai_generated`, `ai_provider`,
`created_at`, `resolved_at`.

Bulgu durumu `PATCH /api/v1/ai/caio/findings/{id}` ile yönetilir:
`open` → `acknowledged` → `in_progress` → `resolved` / `dismissed`
(ayrıntı: [DEVELOPER_AGENT.md](DEVELOPER_AGENT.md#8-caio-ajanı)).

---

## 10. Gizlilik

### 10.1 Yerel mi, bulut mu?

| | LM Studio (`local`) | NVIDIA Build (`nvidia`) | OpenAI uyumlu (`openai_compat`) |
|---|---|---|---|
| İstek nereye gider | `http://localhost:1234/v1` — **bilgisayardan çıkmaz** | `https://integrate.api.nvidia.com/v1` — NVIDIA sunucuları | Sizin yapılandırdığınız adrese |
| Öğrenci adı/derecesi | Yerelde kalır | **Buluta gider** | Hedefe bağlı |
| İnternet gerekir mi | Hayır | Evet | Hedefe bağlı |
| API anahtarı | `lm-studio` (yer tutucu) | Gerçek anahtar zorunlu | Hedefe bağlı |
| Maliyet | Elektrik + donanım | Sağlayıcı kotası/ücreti | Hedefe bağlı |
| Varsayılan | Etkin | Kapalı | Kapalı |

Sağlayıcı bilgisi arayüze `privacy_note_tr` / `privacy_note_en` alanlarıyla
taşınır ve AI Merkezi > Kontrol Merkezi satırında gösterilir.

### 10.2 Hangi veri nereye gider?

Model çağrısına giren içerik `analysis.run_analysis()` içinde açıkça kurulur:

```python
user_content = (
    f"SORU: {request.question}\n\n"
    f"HESAPLANMIŞ İSTATİSTİKLER (gerçek veri):\n{summary}\n\n"
    f"AYRINTILI METRİKLER (JSON):\n{json.dumps(metrics, ...)[:6000]}\n"
)
```

Buna göre modele giden veri:

* **Gider:** soru metni, hesaplanmış metrikler (dereceler, oranlar, tutarlar),
  ilgili öğrencinin **adı** (`student_name`), ilk 6000 karakterlik JSON özeti.
* **Gitmez:** ham veritabanı satırları, TC/kimlik bilgisi, iletişim bilgisi,
  parola, API anahtarı, sağlık notu alanı, tam tablo dökümleri.

Bulut sağlayıcı kullanılıyorsa **öğrenci adları ve performans dereceleri
üçüncü tarafa iletilir.** Kişisel veri işleme açısından bunun değerlendirilmesi
gerekir; ayrıntı için [NVIDIA_AI.md](NVIDIA_AI.md#8-gizlilik) bölümüne bakın.
Hassas veri için önerilen yapılandırma:

```dotenv
AI_DEFAULT_MODE=local
AI_FALLBACK_CHAIN=local
NVIDIA_ENABLED=false
```

### 10.3 `AI_LOG_PROMPTS`

| Değer | Davranış |
|-------|----------|
| `false` (**varsayılan**) | `ai_tasks.prompt_preview` alanı `NULL` bırakılır. Gönderilen istem hiçbir yerde saklanmaz. |
| `true` | İstemin ilk 2000 karakteri veritabanına yazılır. Hata ayıklamayı kolaylaştırır ama **kişisel veri içerebilir**. |

Kod karşılığı (`registry.start_task`):

```python
prompt_preview=(prompt[:2000] if prompt and settings.ai_log_prompts else None),
```

CAIO, `AI_LOG_PROMPTS=true` durumunu bir güvenlik gözlemi olarak raporlar
(`security.prompt_logging_enabled`). Üretimde `false` bırakın.

### 10.4 Sır sızıntısına karşı katmanlar

| Katman | Mekanizma |
|--------|-----------|
| Yapılandırma | Anahtarlar yalnızca `.env`'den okunur; `.env` `.gitignore` içindedir |
| API yanıtı | `mask_secret()` — `GET /api/v1/ai/config` yalnızca maskeli değer döner |
| Hata gövdesi | `redact()` — sağlayıcı hata metni istemciye gitmeden maskelenir |
| Loglar | `RedactingFilter` — her log kaydı `nvapi-`, `sk-`, `ghp_`, `Bearer`, `api_key=` kalıplarına karşı taranır |
| Denetim kaydı | Anahtar değiştiğinde audit'e yalnızca `"nvidia_api_key (gizli)"` yazılır, değer yazılmaz |
| Yedekleme | API anahtarları ve parolalar yedeğe dahil edilmez |
| Developer ajanı | `.env` yolu `FORBIDDEN_PATH_PARTS` içindedir; ajan okuyamaz da yazamaz da |

---

## 11. Yeni Sağlayıcı Ekleme

Aşağıdaki örnek, OpenAI uyumlu bir bulut sağlayıcı olan "Örnek AI"yı
(`example`) sisteme ekler. Sağlayıcı `/v1/chat/completions` ve `/v1/models`
uçlarını sunuyorsa **HTTP kodu yazmanız gerekmez**.

### Adım 1 — Ayarları tanımlayın

`backend/app/core/config.py` içinde `Settings` sınıfına ekleyin:

```python
    # ---------- Örnek AI ----------
    example_enabled: bool = False
    example_api_key: str = ""
    example_base_url: str = "https://api.example-ai.com/v1"
    example_model: str = "example/instruct-8b"
    example_timeout: int = 120
    example_max_tokens: int = 2048
    example_temperature: float = 0.3
```

Aynı dosyadaki `public_ai_config()` sözlüğüne de maskeli bir blok ekleyin ki
ayarlar ekranı sağlayıcıyı görebilsin:

```python
            "example": {
                "enabled": self.example_enabled,
                "base_url": self.example_base_url,
                "model": self.example_model,
                "api_key_set": bool(self.example_api_key),
                "api_key_masked": mask_secret(self.example_api_key),
                "timeout": self.example_timeout,
                "max_tokens": self.example_max_tokens,
                "temperature": self.example_temperature,
            },
```

### Adım 2 — `.env.example` dosyasına belgeleyin

```dotenv
# ---------- ÖRNEK AI / EXAMPLE AI ----------
# Anahtarı sağlayıcının panelinden alın. ANAHTARI ASLA KODA YAZMAYIN.
EXAMPLE_ENABLED=false
EXAMPLE_API_KEY=
EXAMPLE_BASE_URL=https://api.example-ai.com/v1
EXAMPLE_MODEL=example/instruct-8b
EXAMPLE_TIMEOUT=120
EXAMPLE_MAX_TOKENS=2048
EXAMPLE_TEMPERATURE=0.3
```

### Adım 3 — Sağlayıcı sınıfını yazın

`backend/app/services/ai/providers.py`:

```python
class ExampleProvider(OpenAICompatibleProvider):
    """Örnek AI bulut sağlayıcısı (OpenAI uyumlu).

    API anahtarı yalnızca ortam değişkeninden okunur; koda gömülmez, loglanmaz.
    """

    def __init__(self) -> None:
        super().__init__(
            name="example",
            display_name="Örnek AI (Bulut)",
            base_url=settings.example_base_url,
            api_key=settings.example_api_key,
            default_model=settings.example_model,
            timeout=settings.example_timeout,
            max_tokens=settings.example_max_tokens,
            temperature=settings.example_temperature,
            is_local=False,
            enabled=settings.example_enabled,
        )

    @property
    def enabled(self) -> bool:
        # Anahtar yoksa bulut sağlayıcı etkin sayılmaz
        return super().enabled and bool(self.api_key)

    def public_info(self) -> dict:
        info = super().public_info()
        info["privacy_note_tr"] = (
            "Bulut model: gönderilen veriler Örnek AI sunucularında işlenir."
        )
        info["privacy_note_en"] = (
            "Cloud model: submitted data is processed on Example AI servers."
        )
        return info
```

### Adım 4 — Kayıt defterine ekleyin

`backend/app/services/ai/registry.py` → `get_providers()`:

```python
        _providers = {
            "local": LMStudioProvider(),
            "nvidia": NvidiaProvider(),
            "openai_compat": OpenAICompatProvider(),
            "example": ExampleProvider(),      # ← yeni satır
        }
```

Import satırını da güncelleyin:

```python
from app.services.ai.providers import (
    ExampleProvider,
    LMStudioProvider,
    NvidiaProvider,
    OpenAICompatProvider,
    suggest_model_for_task,
)
```

### Adım 5 — Şemaya tanıtın

`backend/app/schemas/ai.py`:

```python
ProviderName = Literal["local", "nvidia", "openai_compat", "example"]
```

Bu satır olmadan `provider="example"` gönderen istekler Pydantic doğrulamasında
**422** ile reddedilir.

### Adım 6 — Fallback zincirine yerleştirin

`.env` dosyanızda:

```dotenv
AI_DEFAULT_MODE=automatic
AI_FALLBACK_CHAIN=local,example,nvidia
```

Zincir sırası önemlidir: gizlilik açısından yerel sağlayıcıyı her zaman başa
koyun; bulut yalnızca yerel başarısız olduğunda devreye girsin.

### Adım 7 — Doğrulayın

```bash
# 1) Sağlayıcıları yeniden yükle (ayarları yeniden okur, sağlık önbelleğini temizler)
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/reload

# 2) Model listesi geliyor mu
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/example/models

# 3) Altı aşamalı bağlantı testi
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/example/test

# 4) Regresyon kontrolü
cd backend && python -m pytest tests -q
```

### Adım 8 — Test yazın

`backend/tests/` altındaki mevcut AI testleri gerçek API çağrısı yapmaz;
`httpx` katmanı taklit edilir (mock). Yeni sağlayıcı için aynı deseni izleyin:
`enabled` mantığı (anahtarsızken `False` olmalı), `chat()` yanıt ayrıştırma ve
`health()` hata yolları test edilmelidir.

### Ne zaman `OpenAICompatibleProvider` yetmez?

Sağlayıcı OpenAI şeması dışında bir gövde bekliyorsa (örneğin farklı bir
`messages` biçimi veya farklı `usage` alan adları), doğrudan `AIProvider`
soyut sınıfını uygulayın ve altı metodu kendiniz yazın: `chat`, `stream`,
`list_models`, `health`, `enabled` ve gerekiyorsa `estimate_usage`. Router,
`AIProvider` arayüzüne uyan her nesneyle çalışır.

---

## İlgili belgeler

* [LOCAL_AI.md](LOCAL_AI.md) — LM Studio kurulum ve kullanım kılavuzu
* [NVIDIA_AI.md](NVIDIA_AI.md) — NVIDIA Build API entegrasyonu
* [DEVELOPER_AGENT.md](DEVELOPER_AGENT.md) — AI Developer Console ve CAIO güvenlik kılavuzu
* [../CHANGELOG.md](../CHANGELOG.md) — Sürüm notları ve bilinen kısıtlamalar
