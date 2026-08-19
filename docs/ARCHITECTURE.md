# Mimari / Architecture

Bu belge Akıllı Yüzme Okulu Yönetim Sistemi'nin teknik mimarisini anlatır: katmanların
sorumlulukları, bir HTTP isteğinin izlediği yol, çekirdek servislerin görevleri ve
sisteme yeni bir modülün nasıl ekleneceği. Hedef kitle: sistemi geliştiren veya
bakımını üstlenen yazılımcılar.

- **Sürüm:** 0.9.0
- **Lisans:** MIT
- **Proje kökü:** `C:\SwimmingSchool`

---

## 1. Genel Bakış

Sistem, bir yüzme okulunun tüm operasyonunu tek bir masaüstü/ağ uygulamasında toplar:
öğrenci ve veli kayıtları, eğitmen yönetimi, havuz ve kulvar planlaması, ders takvimi,
yoklama, üyelik ve paketler, finans, sporcu performansı, yarışmalar, istatistik,
raporlama, yedekleme ve yapay zekâ destekli karar desteği.

### Ne yapar

| Alan | Yetenek |
|------|---------|
| Kişi yönetimi | Öğrenci, veli, eğitmen, grup kayıtları; sertifika ve izin takibi |
| Tesis | Çok havuzlu yapı, kulvar tanımları, bakım kaydı, su kalitesi ölçümü |
| Program | Ders, tekrarlanan ders serisi, takvim, **çakışma motoru**, boş kulvar önerisi |
| Operasyon | Yoklama (manuel/QR/kart), telafi dersi, ders hakkı düşümü |
| Ticari | Paket, üyelik, dondurma, fatura, tahsilat, gider, indirim, kasa hareketi |
| Spor | Performans kaydı, kişisel rekor, kulüp rekoru, yarışma ve seri dağıtımı |
| Analiz | İstatistik motoru, KPI paneli, 16 rapor türü, PDF/Excel/CSV dışa aktarma |
| Yapay zekâ | LM Studio (yerel) + NVIDIA Build (bulut) + OpenAI uyumlu sağlayıcılar |
| Sistem | RBAC, denetim kaydı, bildirim, yedekleme/geri yükleme, eğitim merkezi |

### Kimler kullanır

Sistem **21 rol** ve **52 izin** ile çalışır (`backend/app/core/permissions.py`).
Roller üç grupta toplanır:

| Grup | Roller |
|------|--------|
| Yönetim | `system_admin`, `school_director`, `operations_manager`, `finance`, `hr`, `reception`, `sales_marketing` |
| Eğitim | `head_coach`, `swim_coach`, `swim_instructor`, `kids_instructor`, `baby_instructor`, `private_instructor`, `adaptive_instructor`, `conditioning_coach` |
| Diğer | `lifeguard`, `pool_technician`, `medical_staff`, `athlete`, `student`, `parent` |

Her rol `kaynak:eylem` biçiminde ince taneli izin kümesine sahiptir
(`student:read`, `lesson:schedule`, `finance:write`, `ai:developer` gibi).
Bir kullanıcı birden fazla role sahip olabilir; efektif izin kümesi rollerin
**birleşimidir** (`User.permissions` özelliği).

Ayrıca **satır bazlı erişim kapsamı** vardır (`AccessScope`, `backend/app/api/deps.py`):

- `athlete`, `student`, `parent` rolleri yalnızca kendi (veya çocuklarının) kayıtlarını görür.
- Eğitmen rolleri öncelikle kendi derslerini görür.
- `system_admin`, `school_director`, `operations_manager` rollerinde kapsam kısıtı yoktur.

### Teknoloji yığını

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (Declarative, `Mapped[...]`), Pydantic v2 |
| Veritabanı | SQLite (WAL modu) + Alembic; `DATABASE_URL` değiştirilerek PostgreSQL'e geçilir |
| Frontend | React 18, TypeScript (strict), Vite, Tailwind CSS, TanStack Query, zustand, recharts, i18next |
| Yapay zekâ | `httpx` üzerinden OpenAI uyumlu HTTP API; sağlayıcı soyutlaması + fallback zinciri |
| Rapor | ReportLab (PDF), openpyxl (Excel), `csv` (CSV) |
| Masaüstü | pywebview (Edge WebView2), `START_SWIMMING_SCHOOL.bat` |

Sayısal durum: **240 API uç noktası**, **55 veritabanı tablosu**, **395 backend test fonksiyonu**,
**24 arayüz ekranı**, **1020 çeviri anahtarı** (TR/EN eşit).

---

## 2. Katmanlı Mimari

```
┌──────────────────────────────────────────────────────────────────────────┐
│  İSTEMCİ / CLIENT                                                        │
│  React 18 SPA (TypeScript strict, Vite)                                  │
│  · react-router-dom  · TanStack Query (sunucu durumu)                    │
│  · zustand (oturum + UI durumu)  · i18next (TR/EN)  · recharts           │
│  frontend/src/pages/*.tsx , frontend/src/components/*                    │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │  HTTPS/HTTP · JSON
                                │  Authorization: Bearer <access_token>
                                │  Accept-Language: tr | en
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  MIDDLEWARE                                                              │
│  · CORSMiddleware (beyaz liste: CORS_ORIGINS)                            │
│  · security_headers_middleware → X-Process-Time, X-Content-Type-Options,  │
│    X-Frame-Options, Referrer-Policy, Permissions-Policy, CSP, HSTS       │
│  backend/app/main.py                                                     │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  BAĞIMLILIKLAR / DEPENDENCIES                                            │
│  db_session() → get_db()      · get_current_user() → JWT çözümleme       │
│  require_permissions(...)     · get_scope() → AccessScope (satır bazlı)  │
│  get_language()               · pagination()                             │
│  backend/app/api/deps.py                                                 │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  API KATMANI (FastAPI router)                                            │
│  /api/v1/{auth,users,students,guardians,instructors,groups,pools,        │
│           lessons,attendance,memberships,packages,finance,performance,   │
│           competitions,statistics,reports,ai,ai/developer,ai/caio,       │
│           backup,search,training} + sistem uçları                        │
│  Sorumluluk: HTTP sözleşmesi, Pydantic doğrulama, yetki, yanıt şekli     │
│  backend/app/api/v1/*.py , backend/app/schemas/*.py                      │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  SERVİS KATMANI (iş mantığı — HTTP'den bağımsız)                         │
│  scheduling · statistics_engine · reporting · backup · notifications     │
│  audit · formatting · tutorials · crud · ai/{base,providers,registry,    │
│  analysis,agent,caio,policy,prompts}                                     │
│  backend/app/services/                                                   │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  ORM (SQLAlchemy 2.0)                                                    │
│  Base + TimestampMixin + IntPKMixin, adlandırma kuralı (NAMING_CONVENTION)│
│  50 model · ilişkiler · indeksler · cascade kuralları                    │
│  backend/app/models/*.py , backend/app/db/base.py                        │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  VERİTABANI                                                              │
│  SQLite  data/swimming_school.db                                         │
│  PRAGMA foreign_keys=ON · journal_mode=WAL · synchronous=NORMAL          │
│  Alembic migration (render_as_batch=True)                                │
│  backend/app/db/session.py , backend/alembic/                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### Katman sorumlulukları

| Katman | Yapar | Yapmaz |
|--------|-------|--------|
| **İstemci (SPA)** | Görselleştirme, form doğrulama (ön kontrol), önbellek, dil/tema, yetkiye göre menü gizleme | Güvenlik kararı vermez — arayüzdeki gizleme yalnızca kolaylıktır, gerçek denetim sunucudadır |
| **Middleware** | Güvenlik başlıkları, CORS, istek süresi ölçümü | İş mantığı içermez |
| **Bağımlılıklar** | Oturum açma, JWT çözümü, izin denetimi, dil belirleme, sayfalama parametreleri | Veri yazmaz |
| **API (router)** | HTTP sözleşmesi, Pydantic v2 giriş/çıkış şemaları, yetki bağımlılıkları, denetim kaydı tetikleme | Karmaşık hesaplama yapmaz; servise devreder |
| **Servis** | İş kuralları, çakışma denetimi, istatistik, rapor üretimi, AI çağrısı, yedekleme | `Request`/`Response` nesnesi bilmez — test edilebilir saf Python |
| **ORM** | Tablo eşlemesi, ilişkiler, türetilmiş özellikler (`full_name`, `remaining_credits`) | SQL dizesi elle kurmaz |
| **Veritabanı** | Kalıcılık, yabancı anahtar bütünlüğü, indeksler | — |

Bu ayrım sayesinde 395 test fonksiyonunun çoğu servis katmanını doğrudan çağırarak HTTP yığını
olmadan çalışır; API testleri ise `TestClient` ile uçtan uca doğrulama yapar.

---

## 3. Dizin Yapısı

```
C:\SwimmingSchool\
├── START_SWIMMING_SCHOOL.bat     # Çift tıklama ile başlatma (venv kurulumu + migration + launcher)
├── BUILD_FRONTEND.bat            # Arayüz üretim derlemesi
├── FINAL_CHECK.bat               # Yayın öncesi kalite kapısı
├── CHANGELOG.md · LICENSE · THIRD_PARTY_NOTICES.md
├── .env / .env.example           # Yapılandırma (sırlar burada, koda gömülmez)
│
├── backend/
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt · requirements-dev.txt
│   ├── alembic/
│   │   ├── env.py                # render_as_batch=True, URL .env'den okunur
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 20260815_1529_0ca413b128ea_initial_schema.py
│   ├── app/
│   │   ├── main.py               # FastAPI uygulaması, lifespan, middleware, SPA servisi
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings — tüm ayarlar .env'den
│   │   │   ├── permissions.py    # RoleCode, Perm, ROLE_PERMISSIONS, kapsam kümeleri
│   │   │   ├── security.py       # Parola hash, JWT üretimi/çözümü, SHA-256 dosya özeti
│   │   │   ├── exceptions.py     # AppError ailesi + güvenli hata işleyicileri
│   │   │   ├── i18n.py           # Backend mesaj sözlüğü (TR/EN) ve t()
│   │   │   └── logging_config.py # Yapılandırılmış log, hassas veri maskeleme
│   │   ├── db/
│   │   │   ├── base.py           # DeclarativeBase, NAMING_CONVENTION, mixin'ler
│   │   │   ├── session.py        # engine, SQLite PRAGMA'ları, SessionLocal, get_db
│   │   │   ├── init_db.py        # Rol senkronizasyonu, ilk yönetici, varsayılan ayar/paket
│   │   │   └── seed.py           # Demo veri üretici
│   │   ├── models/               # 55 tablo — 10 alan dosyası + enums.py
│   │   │   ├── user.py · people.py · facility.py · lesson.py · attendance.py
│   │   │   ├── membership.py · finance.py · performance.py · competition.py
│   │   │   ├── system.py · enums.py
│   │   │   └── __init__.py       # Alembic'in metadata'yı görmesi için tek toplama noktası
│   │   ├── schemas/              # Pydantic v2 giriş/çıkış modelleri
│   │   │   ├── common.py · auth.py · people.py · facility.py · lesson.py
│   │   │   ├── operations.py · performance.py · statistics.py · ai.py · system.py
│   │   ├── api/
│   │   │   ├── deps.py           # Oturum, kullanıcı, RBAC, AccessScope, sayfalama
│   │   │   └── v1/               # 21 router dosyası + __init__.py (birleştirme)
│   │   └── services/
│   │       ├── scheduling.py         # Çakışma motoru, seri üretimi, kulvar planı
│   │       ├── statistics_engine.py  # Gerçek hesaplanmış metrikler
│   │       ├── reporting.py          # 16 rapor + PDF/Excel/CSV
│   │       ├── backup.py             # Yedekleme, doğrulama, geri yükleme, saklama
│   │       ├── notifications.py      # Sistem bildirimleri
│   │       ├── audit.py              # Denetim kaydı, hassas alan maskeleme
│   │       ├── formatting.py         # Derece/sayı/tarih biçimlendirme
│   │       ├── tutorials.py          # Eğitim Merkezi içeriği
│   │       ├── crud.py               # Ortak listeleme/sayfalama/arama yardımcıları
│   │       └── ai/
│   │           ├── base.py       # AIProvider soyut arayüzü, ChatMessage, Usage
│   │           ├── providers.py  # LMStudioProvider, NvidiaProvider, OpenAICompatProvider
│   │           ├── registry.py   # AIRouter (fallback), sağlık kontrolü, görev kaydı
│   │           ├── analysis.py   # İstatistik + AI birleşik analiz
│   │           ├── agent.py      # AI Developer Console ajanı
│   │           ├── caio.py       # CAIO gözlem/analiz/öneri döngüsü
│   │           ├── policy.py     # Komut güvenlik politikası
│   │           └── prompts.py    # Sistem istemleri + hazır prompt kütüphanesi
│   └── tests/                    # 395 test fonksiyonu
│       ├── conftest.py
│       ├── test_auth_rbac.py · test_scheduling.py · test_statistics.py
│       ├── test_business_modules.py · test_ai_providers.py
│
├── frontend/
│   ├── index.html · vite.config.ts · tailwind.config.js · tsconfig.json
│   ├── package.json
│   ├── dist/                     # Üretim derlemesi (backend bunu servis eder)
│   └── src/
│       ├── main.tsx              # QueryClient, BrowserRouter, i18n yüklemesi
│       ├── App.tsx               # Router, kod bölme, RequirePermission
│       ├── index.css             # Tailwind katmanları + tema değişkenleri
│       ├── pages/                # 24 ekran (LoginPage hariç tümü lazy)
│       ├── components/
│       │   ├── layout/           # AppLayout, CommandPalette, GlobalSearch
│       │   └── ui/               # Ortak bileşen kitaplığı (index.tsx)
│       ├── lib/
│       │   ├── api.ts            # axios istemcisi, token yenileme, ApiError
│       │   ├── store.ts          # zustand: useAuth, useUI, useToast
│       │   ├── i18n.ts           # i18next kurulumu
│       │   ├── format.ts         # Tarih/sayı/para biçimlendirme
│       │   └── types.ts          # Backend şemalarının TypeScript karşılıkları
│       ├── locales/tr/translation.json
│       └── locales/en/translation.json
│
├── desktop/
│   └── launcher.py               # Backend'i başlatır, WebView2 penceresi açar
│
├── scripts/
│   ├── dev.ps1                   # Geliştirme sunucuları
│   ├── seed_demo.ps1             # Demo veri yükleme
│   └── final_check.ps1           # Lint + tip + test + derleme + sır taraması
│
├── docs/
│   ├── ARCHITECTURE.md           # (bu belge)
│   ├── DATABASE.md
│   └── OPEN_SOURCE_RESEARCH.md
│
├── data/                         # SQLite veritabanı + uploads/
├── backups/                      # Yedek ZIP arşivleri
└── logs/                         # application, database, ai, security, audit
```

---

## 4. İstek Yaşam Döngüsü

Örnek: eğitmen rolündeki bir kullanıcı yeni bir ders oluşturuyor.

```
POST /api/v1/lessons
Authorization: Bearer eyJhbGciOi...
Accept-Language: tr
Content-Type: application/json
```

```
 1. CORSMiddleware
    └─ Origin CORS_ORIGINS beyaz listesinde mi? Değilse tarayıcı isteği reddeder.

 2. security_headers_middleware  (main.py)
    └─ time.perf_counter() başlatılır
    └─ İstek zincire devredilir (call_next)

 3. Yönlendirme
    └─ /api/v1 öneki → api_router → lessons.router (prefix="/lessons")
    └─ Eşleşen operasyon: create_lesson

 4. Bağımlılıklar (Depends) — sırayla çözülür
    ├─ db_session()        → SessionLocal() açılır (istek başına bir oturum)
    ├─ get_current_user()  → HTTPBearer → decode_token() → payload["type"] == "access"
    │                        → db.get(User, sub) → is_active kontrolü
    │                        → başarısızsa AuthenticationError (401)
    ├─ require_permissions(Perm.LESSON_WRITE)
    │                        → user.is_superuser ise geç
    │                        → değilse izin kümesi kontrolü; eksikse
    │                          PermissionDeniedError (403, details.missing)
    ├─ get_scope()         → AccessScope(user, db): is_admin / is_self_scoped /
    │                        is_instructor_scoped bayrakları hesaplanır
    └─ get_language()      → ?lang= > Accept-Language > "tr"

 5. Gövde doğrulama (Pydantic v2)
    └─ LessonCreate şeması: tip, zorunluluk, aralık kontrolleri
    └─ Hata varsa RequestValidationError → 422 + {"error": {...,"details":{"fields":[...]}}}

 6. Router gövdesi
    └─ İş kuralı servise devredilir

 7. Servis katmanı — ConflictChecker.check(...)  (services/scheduling.py)
    ├─ Zaman aralığı geçerli mi (end_at > start_at)
    ├─ Eğitmen çakışması        → HATA
    ├─ Kulvar çakışması         → HATA
    ├─ Öğrenci çakışması        → HATA
    ├─ Havuz bakımı             → HATA
    ├─ Eğitmen izni             → UYARI
    ├─ Havuz çalışma saati dışı → UYARI
    └─ Tatil günü               → UYARI

 8. ORM
    └─ Hata yoksa Lesson nesnesi oluşturulur, db.add(), db.flush()
    └─ audit.record(db, action="create", entity_type="Lesson", ..., commit=False)
       (denetim kaydı iş verisiyle AYNI işlemde — atomik)
    └─ db.commit()

 9. Veritabanı
    └─ SQLite: foreign_keys=ON zorlanır, WAL günlüğüne yazılır

10. Yanıt
    └─ LessonDetail şeması ile serileştirme (response_model)
    └─ Middleware: X-Process-Time ve güvenlik başlıkları eklenir
    └─ /api ile başlayan yollara katı CSP: "default-src 'none'; frame-ancestors 'none'"
    └─ 201 Created

11. Bağımlılık temizliği
    └─ get_db()'nin finally bloğu: db.close()
```

### Hata durumu

Tüm hatalar `register_exception_handlers()` ile tek biçime indirgenir
(`backend/app/core/exceptions.py`). İstemciye **asla** yığın izi, SQL veya dosya yolu
sızmaz; ayrıntı yalnızca sunucu logunda kalır.

| İstisna | HTTP | Yanıt kodu (`error.code`) |
|---------|------|---------------------------|
| `AuthenticationError` | 401 | `auth.not_authenticated` / `auth.invalid_token` / `auth.inactive_user` |
| `PermissionDeniedError` | 403 | `auth.forbidden` |
| `NotFoundError` | 404 | `common.not_found` |
| `ConflictError` / `SchedulingConflictError` | 409 | `common.already_exists` / `lesson.conflict_*` |
| `RateLimitError` | 429 | `auth.rate_limited` |
| `ValidationError` / `RequestValidationError` | 422 | `common.validation_error` |
| `AIProviderError` | 503 | `ai.provider_unavailable` |
| `SecurityPolicyError` | 403 | `ai.command_blocked` |
| `IntegrityError` (SQLAlchemy) | 409 | `common.already_exists` (UNIQUE) veya `common.in_use` |
| `SQLAlchemyError` | 500 | `common.internal_error` |
| Yakalanmamış `Exception` | 500 | `common.internal_error` |

Yanıt gövdesi her zaman aynı şekle sahiptir:

```json
{
  "error": {
    "code": "lesson.conflict_lane",
    "message": "Bu kulvar seçilen saatte başka bir derse ayrılmış.",
    "details": {
      "conflicts": [
        {
          "kind": "lane",
          "lesson_id": 412,
          "lesson_title": "Yıldızlar Grup",
          "entity_name": "Kulvar 3",
          "start_at": "2026-09-14T17:00:00",
          "end_at": "2026-09-14T18:00:00"
        }
      ]
    }
  }
}
```

Mesaj metni `Accept-Language` (veya `?lang=`) değerine göre Türkçe ya da İngilizce
döner; kod (`error.code`) dilden bağımsızdır ve arayüz kararlarını buna dayandırır.
Frontend tarafında `ApiError.conflicts` bu listeyi doğrudan okur
(`frontend/src/lib/api.ts`).

---

## 5. Çekirdek Modüller

### `services/scheduling.py` — Ders planlama ve çakışma motoru

> Aynı zaman diliminde aynı eğitmen, kulvar veya öğrencinin iki derse atanmasını
> engeller; havuz bakımı, çalışma saati ve tatil denetimlerini uygular.

| Fonksiyon / Sınıf | Görev |
|---|---|
| `ConflictChecker.check(...)` | Ana giriş noktası. `(errors, warnings)` ikilisi döndürür |
| `generate_series_dates(...)` | Seri için ders tarihlerini üretir; tatilleri atlayabilir |
| `build_lessons_from_series(...)` | Seriden `Lesson` nesneleri üretir (DB'ye eklemez) |
| `find_free_lanes(...)` | Verilen aralıkta boş kulvarları döndürür |
| `suggest_slot(...)` | Bir gün için çakışmasız zaman/kulvar önerileri üretir |
| `lane_plan(...)` | Bir günün saat × kulvar doluluk matrisini ve doluluk oranını üretir |
| `detect_all_conflicts(...)` | Mevcut takvimi tarar (sağlık kontrolü / CAIO için) |

### `services/statistics_engine.py` — İstatistik motoru

> **Gerçek, hesaplanmış** metrikleri üretir; içinde hiçbir yapay zekâ çağrısı yoktur.

| Grup | Fonksiyonlar |
|---|---|
| İstatistiksel temel | `mean`, `median`, `std_dev`, `percentile`, `moving_average`, `linear_slope`, `pearson_correlation`, `correlation_strength`, `detect_outliers`, `trend_direction` |
| Alan analizi | `student_statistics`, `instructor_statistics`, `pool_statistics`, `attendance_statistics` |
| Performans | `analyze_event`, `student_performance_summary`, `find_top_improvers`, `find_declining_athletes`, `competition_readiness` |
| İş zekâsı | `cohort_retention`, `trend_analysis`, `correlate`, `distribution_analysis`, `find_outliers_in_attendance` |
| KPI | `KPI_DEFINITIONS`, `compute_kpis`, `dashboard_summary` |
| Dönem yardımcıları | `resolve_period`, `previous_period` |

### `services/reporting.py` — Rapor üretici

> Her rapor ortak bir `ReportPreview` (sütunlar + satırlar + toplamlar) üretir;
> dışa aktarma katmanı bu tek yapıyı PDF/Excel/CSV'ye çevirir.

| Fonksiyon | Görev |
|---|---|
| `REPORT_DEFINITIONS` / `REPORT_INDEX` | 16 rapor tanımı ve anahtar dizini |
| `REPORT_BUILDERS` | `report_key → üretici fonksiyon` haritası |
| `build_report(db, request)` | İstenen raporu üretir |
| `to_csv` / `to_excel` / `to_pdf` | Ortak önizlemeyi hedef biçime dönüştürür |
| `export_report(...)` | Biçim seçimi + dosya adı + `Content-Disposition` üretimi |
| `_register_fonts()` | PDF'de Türkçe karakterler için font kaydı |

Rapor üreticileri: öğrenci listesi, yoklama, eğitmen iş yükü, havuz kullanımı,
kulvar doluluğu, finans, tahsilat, açık bakiye, üyelik, satış, performans, yarışma,
günlük yönetici özeti, yönetim özeti ve öğrenci gelişim raporu.

### `services/backup.py` — Yedekleme ve kurtarma

> Yedek = ZIP arşivi + `backup_manifest.json` + SHA-256 özetleri. Sırlar
> (`.env`, API anahtarları) **hiçbir zaman** yedeğe girmez.

| Fonksiyon | Görev |
|---|---|
| `BackupProvider` / `LocalDiskProvider` | Yedek hedefi soyutlaması (bulut hedefleri için hazır) |
| `_snapshot_sqlite(...)` | `sqlite3.Connection.backup()` ile WAL modunda tutarlı kopya alır |
| `create_backup(...)` | Arşivi oluşturur, manifest yazar, kayıt açar |
| `verify_backup(...)` | Bütünlük doğrulaması (SHA-256 + `PRAGMA integrity_check`) |
| `restore_preview(...)` | Geri yükleme öncesi fark önizlemesi |
| `restore_backup(...)` | Doğrula → güvenlik yedeği → geri yükle → doğrula → hata varsa rollback |
| `apply_retention(...)` | Günlük/haftalık/aylık saklama politikası |
| `backup_status(db)` | Son yedek, toplam boyut, sağlık özeti |
| `start_backup_scheduler()` / `stop_backup_scheduler()` | Cron tabanlı zamanlanmış yedekleme (uygulama yaşam döngüsüne bağlı) |

`EXCLUDED_PATTERNS` listesi (`.env`, `.key`, `.pem`, `credentials`, `secrets`,
`token`, `id_rsa`) arşive girecek dosyaları filtreler.

### `services/notifications.py` — Bildirimler

> Üyelik bitişi, gecikmiş ödeme, ders iptali, sertifika süresi, su kalitesi gibi
> olaylardan kullanıcı bildirimi üretir.

| Fonksiyon | Görev |
|---|---|
| `create(...)` | Tek kullanıcıya bildirim (TR/EN başlık-gövde çifti ile) |
| `broadcast(...)` | Belirli izin/role sahip tüm kullanıcılara yayın |
| `_recipients(...)` | Alıcı kümesini izin/role göre çözer |
| `_already_exists(...)` | Yinelenen bildirimi engeller |
| `generate_system_notifications(db, expiry_days=14)` | Periyodik tarama; üretilen bildirim sayılarını döndürür |

### `services/audit.py` — Denetim kaydı

> Kim, ne zaman, hangi kaydı, nasıl değiştirdi. Parola ve anahtarlar `***` ile maskelenir.

| Fonksiyon | Görev |
|---|---|
| `record(...)` | `AuditLog` satırı ekler; **varsayılan `commit=False`** — çağıran işlemle atomik kalır |
| `diff_changes(before, after)` | `{alan: {"from": x, "to": y}}` farkı üretir |
| `model_snapshot(obj, fields)` | ORM nesnesinden seçili alanların anlık görüntüsü |
| `system_event(...)` | Uygulama seviyesi olay (`SystemEvent`) |
| `_sanitize(...)` | `_SENSITIVE_FIELDS` ve `password`/`secret` içeren anahtarları maskeler, 500 karakteri aşan metni kırpar |

### `services/crud.py` — Ortak CRUD yardımcıları

| Fonksiyon | Görev |
|---|---|
| `get_or_404(...)` | Kayıt yoksa yerelleştirilmiş `NotFoundError` |
| `apply_search(...)` | Belirtilen alanlarda büyük/küçük harf duyarsız `LIKE` araması |
| `apply_sort(...)` | Yalnızca modelde var olan sütuna göre güvenli sıralama |
| `paginate(...)` | `(kayıtlar, toplam)` döndürür |
| `next_sequence_number(...)` | `OGR00001`, `FT00042` gibi artan numara üretir |
| `apply_updates(obj, payload)` | Pydantic `exclude_unset` alanlarını uygular ve farkı döndürür |

### `services/ai/` — Yapay zekâ katmanı

| Dosya | Tek cümlelik özet | Ana öğeler |
|---|---|---|
| `base.py` | Tüm sağlayıcıların uyduğu ortak arayüz | `AIProvider` (soyut), `OpenAICompatibleProvider`, `ChatMessage`, `ChatResult`, `Usage`, `HealthResult`, `AIProviderError` |
| `providers.py` | Üç somut sağlayıcı ve model önerisi | `LMStudioProvider`, `NvidiaProvider`, `OpenAICompatProvider`, `suggest_model_for_task` |
| `registry.py` | Sağlayıcı seçimi, fallback, sağlık kontrolü, görev kaydı | `AIRouter.chat/stream/resolve_chain`, `check_health`, `record_health`, `start_task`, `finish_task`, `control_center_data`, `run_connection_tests` |
| `analysis.py` | İstatistik çıktısını AI'ya verip doğal dil raporu üretir | `run_analysis`, `generate_training_plan`, 12 metrik toplayıcı, `_parse_sections`, `_resolve_language` |
| `prompts.py` | Sistem istemleri ve hazır prompt kütüphanesi | `analyst_system_prompt`, `coach_system_prompt`, `get_prompts` |
| `agent.py` | AI Developer Console ajanı (READ→…→APPLY) | `plan_changes`, `apply_patch`, `create_checkpoint`, `rollback_checkpoint`, `run_tests`, `make_diff`, `search_in_files` |
| `policy.py` | Ajanın çalıştırabileceği komutları sınırlayan güvenlik politikası | `CommandPolicy`, `PolicyDecision` |
| `caio.py` | Gözlem → analiz → öneri döngüsü; AI olmadan da kural motoruyla çalışır | `observe`, `analyze`, `run_caio`, `_observe_{logs,ai_usage,code_quality,database,security,backups}` |

`AIRouter.resolve_chain()` mantığı: kullanıcı açıkça bir sağlayıcı seçtiyse yalnızca
onu dener; `automatic` modda `AI_FALLBACK_CHAIN` (varsayılan `local,nvidia`) sırasıyla
etkin sağlayıcıları dener. Tüm sağlayıcılar başarısız olursa `AIProviderError` fırlatılır
ve sistem AI dışındaki tüm işlevleriyle çalışmaya devam eder.

---

## 6. Ders Planlama ve Çakışma Motoru

### Kesişim kuralı

İki zaman aralığı `[a_start, a_end)` ve `[b_start, b_end)` için:

```
Kesişim var  ⟺  a_start < b_end  AND  b_start < a_end
```

Aralıklar **yarı açıktır**: bitişik dersler (`14:00–15:00` ve `15:00–16:00`)
çakışma sayılmaz. Kural SQL düzeyinde tek bir yan tümceye indirgenmiştir
(`backend/app/services/scheduling.py`):

```python
def _overlap_clause(start_at: datetime, end_at: datetime):
    """SQL düzeyinde zaman kesişimi koşulu."""
    return and_(Lesson.start_at < end_at, start_at < Lesson.end_at)
```

Ayrıca iptal edilmiş ve ertelenmiş dersler çakışma taramasına dâhil edilmez:

```python
def _active_lesson_clause():
    return Lesson.status.notin_([LessonStatus.CANCELLED, LessonStatus.POSTPONED])
```

### Hangi kaynaklarda çakışma aranır

| Kaynak | Sorgu | Sonuç |
|---|---|---|
| **Eğitmen** | `Lesson.instructor_id == X` + kesişim + aktif ders | **HATA** — aynı eğitmen iki yerde olamaz |
| **Kulvar** | `Lesson.lane_id == X` + kesişim + aktif ders | **HATA** — bir kulvar aynı anda tek derse ayrılır |
| **Öğrenci** | `LessonEnrollment.student_id IN (...)` + `status == enrolled` + kesişim | **HATA** — öğrenci aynı anda iki derse kayıtlı olamaz |
| **Havuz bakımı** | `PoolMaintenance` kesişimi + `is_completed == False` | **HATA** — bakımdaki havuza ders planlanamaz |
| **Eğitmen izni** | `InstructorLeave.start_date <= gün <= end_date` | **UYARI** |
| **Havuz çalışma saati** | `start.time() >= opening_time` ve `end.time() <= closing_time` | **UYARI** |
| **Tatil günü** | `Holiday.date == gün` + `is_closed == True` | **UYARI** |
| **Zaman aralığı** | `end_at <= start_at` | **HATA** (diğer kontroller çalıştırılmadan döner) |

### Hata ile uyarı ayrımı

`ConflictChecker.check(...)` `(errors, warnings)` ikilisi döndürür:

- **Hata (`errors`)** — kayıt **engellenir**. API `409 Conflict` ile
  `SchedulingConflictError` döndürür; `details.conflicts` listesinde her çakışma
  için `kind`, `lesson_id`, `lesson_title`, `entity_id`, `entity_name`,
  `start_at`, `end_at` alanları bulunur. Bunlar fiziksel imkânsızlıklardır:
  bir kişi veya kulvar aynı anda iki yerde olamaz.
- **Uyarı (`warnings`)** — kayıt **yapılır**, ancak kullanıcı bilgilendirilir.
  `ConflictItem.severity = "warning"` işaretiyle döner. Bunlar politika ihlalleridir,
  fiziksel imkânsızlık değil: eğitmen izinli olabilir ama yine de derse gelebilir;
  havuz resmî saat dışında özel bir seans için açılabilir; tatilde telafi dersi
  yapılabilir.

`kind` alanının alabileceği değerler: `time_range`, `instructor`, `instructor_leave`,
`lane`, `student`, `pool_maintenance`, `pool_hours`, `holiday`.

### Ön denetim uç noktası

Arayüz, kaydetmeden önce çakışmayı sorabilir:

```
POST /api/v1/lessons/check-conflicts
```

Bu sayede kullanıcı formu doldururken çakışmayı görür; kaydetme anında sürpriz olmaz.
Ders taşıma (sürükle-bırak) da aynı motoru kullanır:

```
POST /api/v1/lessons/{lesson_id}/move
```

Güncelleme senaryolarında `exclude_lesson_id` parametresi verilir; böylece dersin
kendisi kendisiyle çakışmış sayılmaz.

### Tekrarlanan dersler

`LessonSeries` bir kural tanımıdır (haftanın günleri + saat + tarih aralığı);
`generate_series_dates()` bu kuraldan somut tarihleri üretir,
`build_lessons_from_series()` `Lesson` nesnelerini kurar. Böylece **çakışma denetimi
her zaman somut `Lesson` satırları üzerinde, tek ve basit bir sorguyla** yapılır —
tekrar kuralı çözümlemeye gerek kalmaz. Bu, `backend/app/models/lesson.py` dosyasında
açıkça belirtilmiş bir tasarım kararıdır.

---

## 7. İstatistik + AI Ayrımı

Sistemin en önemli tasarım ilkelerinden biri, **hesaplanmış gerçek ile model yorumunun
karıştırılmamasıdır**.

```
┌────────────┐   SQL    ┌──────────────────┐   dict    ┌──────────┐   metin   ┌─────────┐
│ Veritabanı │ ───────► │ Statistics       │ ────────► │   AI     │ ────────► │ Doğal   │
│  (SQLite)  │  agrega  │ Engine           │ yapılan-  │ Sağlayıcı│  yorum    │  dil    │
│            │          │ (saf Python)     │ dırılmış  │ (LLM)    │           │ raporu  │
└────────────┘          └──────────────────┘  metrik   └──────────┘           └─────────┘
                                │                                                  │
                                │                                                  │
                                ▼                                                  ▼
                    ┌───────────────────────┐                        ┌──────────────────────┐
                    │  metrics (JSON)       │                        │  summary / bulgular  │
                    │  → arayüzde "Gerçek   │                        │  → arayüzde "AI      │
                    │     Veri" paneli      │                        │     Yorumu" paneli   │
                    └───────────────────────┘                        └──────────────────────┘
```

Akış `backend/app/services/ai/analysis.py` içinde uygulanır:

1. İstek türüne göre bir **metrik toplayıcı** seçilir
   (`_student_performance_metrics`, `_attendance_metrics`, `_finance_metrics`,
   `_retention_metrics`, `_schedule_metrics`, `_payment_risk_metrics`, `_instructor_metrics`,
   `_declining_metrics`, `_top_improvers_metrics`, `_weakest_stroke_metrics`,
   `_readiness_metrics`, `_general_metrics`).
2. Toplayıcı **yalnızca `statistics_engine` fonksiyonlarını** çağırır — ortalama,
   eğilim eğimi, korelasyon, persentil, tutundurma oranı gibi değerler burada,
   deterministik olarak hesaplanır.
3. Sonuç JSON'a çevrilip AI'ya **girdi** olarak verilir.
4. AI'nın metni `_parse_sections()` ile özet / bulgular / öneriler bölümlerine ayrılır.
5. Yanıt (`AIAnalysisResponse`) hem `metrics` (gerçek veri) hem de AI yorumunu
   **ayrı alanlarda** taşır; arayüzde ayrı panellerde gösterilir.

Uç nokta: `POST /api/v1/ai/analyze` — özet başlığı bile bu ayrımı yansıtır:
*"Veri analizi (İstatistik + AI)"*.

### Neden AI'ya ham veri verilmiyor

| Gerekçe | Açıklama |
|---|---|
| **Doğruluk** | Dil modelleri aritmetik ve toplama işlemlerinde güvenilir değildir. Ortalama, eğim ve korelasyon Python'da hesaplanır; model yalnızca yorumlar. Aynı veri her zaman aynı sayıyı üretir. |
| **Tekrarlanabilirlik** | Metrikler deterministiktir ve `backend/tests/test_statistics.py` ile doğrulanır. Model çıktısı değişse bile sayılar değişmez. |
| **Gizlilik** | Sağlayıcıya öğrenci adı, telefon, sağlık notu gibi ham kişisel veri değil, toplulaştırılmış metrik gider. |
| **Maliyet ve hız** | Binlerce satır yerine birkaç kilobaytlık özet gönderilir; token tüketimi ve gecikme düşer. |
| **Bağlam sınırı** | Tüm ders/yoklama tablosu hiçbir modelin bağlam penceresine sığmaz; özet sığar. |
| **Şeffaflık** | Kullanıcı hangi sayının ölçüm, hangi cümlenin yorum olduğunu ayırt edebilir. AI yorumu kesin gerçek olarak sunulmaz. |
| **Dayanıklılık** | Hiçbir AI sağlayıcısı çalışmasa bile istatistik, KPI ve raporlar tam çalışır. |

`MIN_DATA_POINTS = 3` sabiti, yeterli veri yokken modelin yorum üretmesini engeller.

---

## 8. Frontend Mimarisi

### Router ve kod bölme

`frontend/src/App.tsx` içinde `LoginPage` dışındaki **24 sayfanın tamamı**
`React.lazy()` ile yüklenir; her sayfa ayrı bir JS parçasıdır. `Suspense` sınırı
`LoadingState` bileşenini gösterir.

Rota tablosu veri olarak tanımlanır ve `RequirePermission` ile sarılır:

```tsx
[
  ['students',     StudentsPage,     'student:read'],
  ['lessons',      LessonsPage,      'lesson:read'],
  ['finance',      FinancePage,      'finance:read'],
  ['ai-developer', AIDeveloperPage,  'ai:developer'],
  // ...
]
```

`RequirePermission` yalnızca **görsel** bir kolaylıktır; asıl yetki denetimi her
zaman sunucudadır (`require_permissions`). `AppLayout` altındaki tüm rotalar kimlik
doğrulaması gerektirir; oturum yoksa `/login`'e yönlendirilir. `user.onboarding_completed`
false ise kullanıcı kurulum sihirbazına (`OnboardingPage`) alınır.

Üretim derlemesinde `vite.config.ts` ayrıca `react`, `charts`, `query`, `i18n`
satıcı parçalarını ayırır (`manualChunks`).

### TanStack Query önbelleği

`frontend/src/main.tsx`:

```tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Yetki/doğrulama hatalarında tekrar deneme
        if (error instanceof ApiError && [400, 401, 403, 404, 422].includes(error.status)) {
          return false
        }
        return failureCount < 2
      },
    },
  },
})
```

- `staleTime: 30_000` — 30 saniye içinde aynı anahtar yeniden istenmez.
- `refetchOnWindowFocus: false` — masaüstü kullanımında pencere değiştirmek
  gereksiz ağ trafiği üretmez.
- İstemci hatalarında (400/401/403/404/422) yeniden deneme yapılmaz; yalnızca
  ağ/sunucu hatalarında en fazla iki deneme.
- Uzun ömürlü veriler kendi `staleTime` değerini verir; örneğin kurum ayarı
  `App.tsx` içinde `staleTime: 10 * 60_000` ile 10 dakika önbelleklenir.

### API istemcisi

`frontend/src/lib/api.ts` tek bir axios örneği kurar (`baseURL = '/api/v1'`):

- **İstek araya girmesi:** `Authorization: Bearer <access>` ve
  `Accept-Language` başlıklarını otomatik ekler.
- **Yanıt araya girmesi:** 401 alındığında `/auth/refresh` ile jetonu **bir kez**
  yenilemeyi dener; eşzamanlı isteklerin tek bir yenileme çağrısını paylaşması için
  `refreshPromise` tekilleştirmesi kullanılır. Yenileme başarısızsa
  `sws:session-expired` olayı yayılır ve `store.ts` oturumu kapatır.
- Backend hata biçimi `ApiError` sınıfına normalize edilir; `ApiError.conflicts`
  ders çakışmalarını doğrudan verir.
- `download()` yardımcı fonksiyonu `Content-Disposition` başlığındaki
  UTF-8 dosya adını çözerek PDF/Excel/CSV indirmelerini yönetir.

### zustand store

`frontend/src/lib/store.ts` üç ayrı store tutar:

| Store | Durum | Eylemler |
|---|---|---|
| `useAuth` | `user`, `status` (`idle`/`loading`/`authenticated`/`anonymous`) | `login`, `logout`, `loadSession`, `setUser`, `can`, `canAny`, `hasRole` |
| `useUI` | `theme`, `language`, `sidebarCollapsed`, `paletteOpen`, `searchOpen` | `setTheme`, `changeLanguage`, `toggleSidebar`, `setPaletteOpen`, `setSearchOpen` |
| `useToast` | `toasts` | `push`, `dismiss` (+ `toastError`, `toastSuccess` kısayolları) |

İş bölümü nettir: **sunucu durumu TanStack Query'de, istemci durumu zustand'da.**
Tema ve dil tercihleri hem `localStorage`'a hem de `POST /api/v1/auth/preferences`
ile sunucuya yazılır; sunucu erişilemezse yerel tercih korunur.

### Yerelleştirme (i18n)

`frontend/src/lib/i18n.ts` i18next'i `react-i18next` ile kurar:

- Kaynaklar: `frontend/src/locales/tr/translation.json` ve `.../en/translation.json`
- **1020 çeviri anahtarı**, iki dilde eşit sayıda
- Varsayılan ve yedek dil: `tr`
- Seçim `localStorage` anahtarı `sws-language` ile saklanır ve `<html lang>` güncellenir
- Geliştirme modunda eksik anahtar konsola uyarı yazar (`missingKeyHandler`)
- Aynı dil değeri API isteklerinde `Accept-Language` olarak gönderilir; böylece
  backend hata mesajları da aynı dilde döner

Tarih, sayı ve para birimi biçimlendirmesi `frontend/src/lib/format.ts` içindedir;
para birimi kurum ayarından (`applyOrganizationSettings`) okunur.

### Tema

Tema üç değerlidir: `light`, `dark`, `system`.

```ts
function applyTheme(theme: Theme): void {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = theme === 'dark' || (theme === 'system' && prefersDark)
  document.documentElement.classList.toggle('dark', dark)
}
```

Tailwind'in `dark:` varyantı bu sınıfa bağlıdır. `system` seçiliyken işletim
sisteminin tercihi dinlenir ve değişimde tema anında güncellenir.

### Hata sınırı

`App.tsx` içindeki `ErrorBoundary` sınıf bileşeni, render sırasında oluşan
yakalanmamış hataları yakalar ve iki dilli bir kurtarma ekranı ("Sayfayı yenile /
Reload") gösterir; böylece tek bir sayfa hatası tüm uygulamayı beyaz ekrana düşürmez.

---

## 9. Genişletme Kılavuzu

Yeni bir modül eklemek için izlenecek sıra. Örnek: **"Ekipman Envanteri"** modülü.

### Adım 1 — Model

`backend/app/models/facility.py` içine (veya yeni bir dosyaya) ekleyin:

```python
class Equipment(Base, IntPKMixin, TimestampMixin):
    """Havuz ekipmanı (palet, kickboard, kronometre ...)."""

    __tablename__ = "equipment"
    __table_args__ = (Index("ix_equipment_pool_status", "pool_id", "status"),)

    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    pool_id: Mapped[int | None] = mapped_column(
        ForeignKey("pools.id", ondelete="SET NULL")
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="available", nullable=False)
    purchased_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
```

Yeni dosya açtıysanız **`backend/app/models/__init__.py` içine import ve `__all__`
girdisi eklemeyi unutmayın** — Alembic tabloları yalnızca `Base.metadata` üzerinden
görür.

### Adım 2 — Migration

```powershell
cd C:\SwimmingSchool\backend
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add equipment table"
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Üretilen dosyayı gözden geçirin; `alembic/env.py` `render_as_batch=True` ile
çalıştığı için SQLite'ta `ALTER` işlemleri de güvenlidir.

### Adım 3 — Şema (Pydantic v2)

`backend/app/schemas/facility.py`:

```python
class EquipmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=40)
    pool_id: int | None = None
    quantity: int = Field(default=1, ge=0)
    status: str = "available"
    notes: str | None = None


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    quantity: int | None = Field(default=None, ge=0)
    status: str | None = None
    notes: str | None = None


class EquipmentOut(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
```

### Adım 4 — İzin

`backend/app/core/permissions.py` içinde `Perm` sınıfına ekleyin ve ilgili rollere
dağıtın:

```python
class Perm(StrEnum):
    ...
    EQUIPMENT_READ = "equipment:read"
    EQUIPMENT_WRITE = "equipment:write"
```

```python
RoleCode.POOL_TECHNICIAN: {
    Perm.POOL_READ, Perm.POOL_WRITE, Perm.POOL_MAINTENANCE,
    Perm.EQUIPMENT_READ, Perm.EQUIPMENT_WRITE,
    ...
},
```

`system_admin` rolü `set(Perm)` kullandığı için yeni izni otomatik alır. Uygulama
her açılışta `init_db()` → `sync_roles()` çalıştırır ve **sistem rollerinin izinleri
kod tanımından yeniden yazılır**; yani yeni izin veritabanına kendiliğinden yayılır.

### Adım 5 — Router

`backend/app/api/v1/pools.py` içine (veya yeni bir `equipment.py` dosyasına):

```python
equipment_router = APIRouter(prefix="/equipment", tags=["Ekipman"])


@equipment_router.get("", response_model=Page[EquipmentOut], summary="Ekipman listesi")
def list_equipment(
    q: str | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.EQUIPMENT_READ)),
) -> Page[EquipmentOut]:
    stmt = select(Equipment)
    stmt = apply_search(stmt, Equipment, q, ["name", "code"])
    stmt = apply_sort(stmt, Equipment, params, default_field="name")
    rows, total = paginate(db, stmt, params)
    return Page(items=rows, total=total, page=params.page, page_size=params.page_size)


@equipment_router.post("", response_model=EquipmentOut, status_code=201, summary="Ekipman ekle")
def create_equipment(
    payload: EquipmentCreate,
    request: Request,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.EQUIPMENT_WRITE)),
) -> EquipmentOut:
    item = Equipment(**payload.model_dump())
    db.add(item)
    db.flush()
    audit.record(
        db,
        action="create",
        entity_type="Equipment",
        entity_id=item.id,
        user=user,
        summary=item.name,
        ip_address=client_ip(request),
    )
    db.commit()
    return item
```

Yeni dosya açtıysanız `backend/app/api/v1/__init__.py` içinde import edip
`api_router.include_router(...)` ile bağlayın.

### Adım 6 — Test

`backend/tests/test_business_modules.py` (veya yeni bir dosya):

```python
def test_equipment_crud(client, admin_headers):
    created = client.post(
        "/api/v1/equipment",
        json={"name": "Kickboard", "code": "EKP-001", "quantity": 20},
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["quantity"] == 20

    listing = client.get("/api/v1/equipment", headers=admin_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_equipment_requires_permission(client, instructor_headers):
    response = client.get("/api/v1/equipment", headers=instructor_headers)
    assert response.status_code == 403
```

Çalıştırma:

```powershell
cd C:\SwimmingSchool\backend
..\.venv\Scripts\python.exe -m pytest tests -q
```

### Adım 7 — Tip tanımı ve sayfa

`frontend/src/lib/types.ts` içine karşılık gelen arayüzü ekleyin:

```ts
export interface Equipment {
  id: number
  name: string
  code: string
  pool_id: number | null
  quantity: number
  status: string
  notes: string | null
}
```

`frontend/src/pages/EquipmentPage.tsx` oluşturun ve `App.tsx` içinde kaydedin:

```tsx
const EquipmentPage = lazy(() => import('@/pages/EquipmentPage'))
// rota tablosuna:
['equipment', EquipmentPage, 'equipment:read'],
```

Menü girdisi için `frontend/src/components/layout/AppLayout.tsx` dosyasını güncelleyin.

### Adım 8 — Çeviri

**İki dosyaya da aynı anahtarları ekleyin** — `FINAL_CHECK.bat` iki dilin anahtar
sayısını karşılaştırır ve eşit değilse başarısız olur:

```jsonc
// frontend/src/locales/tr/translation.json
{ "equipment": { "title": "Ekipman", "quantity": "Adet", "status": "Durum" } }
```

```jsonc
// frontend/src/locales/en/translation.json
{ "equipment": { "title": "Equipment", "quantity": "Quantity", "status": "Status" } }
```

Backend hata mesajı ekleyecekseniz `backend/app/core/i18n.py` içindeki `MESSAGES`
sözlüğüne `tr` ve `en` karşılıklarıyla girin.

### Adım 9 — Kalite kapısı

```
FINAL_CHECK.bat
```

Lint, tip denetimi, 395 test fonksiyonu, arayüz derlemesi ve gizli anahtar taraması tek
komutla çalışır. Yeşil değilse modül tamamlanmış sayılmaz.

---

## 10. Teknoloji Kararları ve Gerekçeleri

### Neden FastAPI

| Gerekçe | Açıklama |
|---|---|
| Pydantic v2 ile bütünleşik doğrulama | Giriş şeması, çıkış şeması ve tip ipuçları tek yerde; şema ile kod ayrışamaz. |
| Otomatik OpenAPI | 240 uç noktanın tamamı `/docs` (Swagger) ve `/redoc` altında elle bakım gerektirmeden belgelenir. |
| Bağımlılık enjeksiyonu | Oturum, kullanıcı, izin, dil ve sayfalama `Depends(...)` ile bildirimsel biçimde eklenir. Yetki denetimi router imzasında görünür — unutulması zorlaşır. |
| Performans | Starlette/ASGI tabanı, senkron veritabanı çağrılarını iş parçacığı havuzunda çalıştırır; tek makinelik kurulum için fazlasıyla yeterli. |
| Alternatiflere göre | Django ORM + admin ağır ve varsayımları katı; Flask'ta doğrulama, şema ve OpenAPI'yi elle bir araya getirmek gerekirdi. |

### Neden SQLite ile başlangıç

| Gerekçe | Açıklama |
|---|---|
| Sıfır kurulum | Yüzme okulunun BT personeli yoktur. `START_SWIMMING_SCHOOL.bat` çift tıklanır; sunucu, servis veya parola yapılandırması gerekmez. |
| Tek dosya | Veritabanı `data/swimming_school.db`. Yedekleme = dosyayı kopyalamak; taşıma = USB'ye atmak. |
| Yeterli kapasite | Tek tesisin öğrenci, ders ve yoklama hacmi SQLite için önemsizdir. |
| WAL modu | `journal_mode=WAL` ile okuma ve yazma birbirini kilitlemez; `synchronous=NORMAL` WAL ile güvenli ve hızlıdır; `busy_timeout=30000` kısa süreli kilitlerde yeniden dener. |
| Bütünlük | SQLite'ta yabancı anahtar zorlaması **varsayılan olarak kapalıdır**; her bağlantıda `PRAGMA foreign_keys=ON` çalıştırılır (`db/session.py`). |
| Tutarlı yedek | `sqlite3.Connection.backup()` çevrimiçi yedekleme API'si, açık bağlantılar varken bile bütünlüklü kopya üretir. |
| Geçiş yolu açık | Veri katmanı saf SQLAlchemy 2.0'dır; ham SQL yoktur. `DATABASE_URL` değiştirilerek PostgreSQL'e geçilir (ayrıntı: `docs/DATABASE.md`). |

### Neden TanStack Query

| Gerekçe | Açıklama |
|---|---|
| Sunucu durumu ≠ istemci durumu | Sunucudan gelen veri bir önbellektir; Redux benzeri bir global depoya kopyalanması gereksiz karmaşıklık üretir. |
| Otomatik yaşam döngüsü | `isLoading`, `isError`, `refetch`, mutasyon sonrası geçersizleme hazır gelir; her ekranda elle `useEffect` + `useState` yazmaya gerek kalmaz. |
| Akıllı yeniden deneme | 401/403/422 gibi kalıcı hatalarda deneme yapılmaz, geçici ağ hatalarında iki deneme yapılır. |
| İstemci durumu ayrı | Oturum, tema, dil ve tost gibi gerçek istemci durumu için hafif `zustand` kullanılır — iki araç birbirinin işini yapmaz. |
| Masaüstü uyumu | `refetchOnWindowFocus: false` ile pencere değiştirme gereksiz istek üretmez. |

### Neden pywebview (Electron değil)

| Ölçüt | pywebview + WebView2 | Electron |
|---|---|---|
| Bellek | İşletim sistemindeki Edge WebView2 çalışma zamanı kullanılır; ek tarayıcı motoru yüklenmez | Her uygulama kendi Chromium'unu taşır, belirgin biçimde daha fazla RAM |
| Dağıtım boyutu | Yalnızca Python paketi | Yüzlerce MB'lık Chromium |
| Dil tutarlılığı | Başlatıcı da Python (`desktop/launcher.py`) — backend ile aynı dil, aynı sanal ortam | Ayrı bir Node.js araç zinciri ve derleme hattı gerekir |
| Güncelleme | Tarayıcı motoru Windows Update ile güncellenir; güvenlik yamaları uygulamayı beklemez | Chromium sürümünü uygulama taşır; güncelleme sorumluluğu geliştiricide |
| Kapsam | Uygulama zaten bir web arayüzüdür; ihtiyaç duyulan tek şey bir pencere | Electron'un sunduğu geniş masaüstü API yüzeyine ihtiyaç yok |

`desktop/launcher.py` backend'i arka planda başlatır, sağlık kontrolüyle hazır
olmasını bekler (`STARTUP_TIMEOUT = 90`), boş port bulur ve WebView penceresini
açar. pywebview kurulu değilse **varsayılan tarayıcıda açarak zarifçe geri düşer**;
pencere kapatıldığında backend süreci temiz biçimde durdurulur.

### Diğer kararlar

| Karar | Gerekçe |
|---|---|
| **StrEnum tabanlı enum'lar** | Veritabanında okunabilir metin olarak saklanır (`"beginner"`), JSON'a doğrudan serileşir, i18n etiketleri `ENUM_LABELS` ile ayrı tutulur. Sayısal kodlar okunamaz veri üretirdi. |
| **Adlandırma kuralı (`NAMING_CONVENTION`)** | SQLite'ta isimsiz kısıtlamalar `ALTER` edilemez. `db/base.py` her indeks/kısıtlamaya deterministik ad verir; Alembic autogenerate güvenle çalışır. |
| **`render_as_batch=True`** | SQLite `ALTER TABLE` desteği sınırlıdır. Batch modu tabloyu yeniden oluşturup veriyi taşır. |
| **JWT (erişim + yenileme)** | Sunucu tarafında oturum durumu tutulmaz; masaüstü ve tarayıcı istemcileri aynı akışı kullanır. Erişim jetonu 120 dakika, yenileme jetonu 14 gün. |
| **İzinler rolde JSON olarak** | `Role.permissions` bir JSON listesidir; ayrı bir izin tablosu ve join maliyeti olmadan `sync_roles()` ile kod tanımından yeniden yazılabilir. |
| **`audit.record(commit=False)`** | Denetim kaydı iş verisiyle aynı işlemde yazılır; iş verisi geri alınırsa denetim kaydı da geri alınır — "hayalet" kayıt oluşmaz. |
| **Sırlar yalnızca `.env`** | `config.py` hiçbir sır içermez; `SECRET_KEY` verilmezse `secrets.token_urlsafe(64)` ile üretilir. `mask_secret()` API anahtarlarını UI ve loglarda maskeler. |
| **SPA'yı backend'in servis etmesi** | `frontend/dist` varsa FastAPI `/assets` ve SPA geri düşüş rotasını mount eder — üretimde tek süreç, tek port, ayrı web sunucusu yok. |
| **AI sağlayıcı soyutlaması** | `AIProvider` arayüzü sayesinde sistem tek bir yapay zekâ firmasına bağımlı değildir; LM Studio ile veriler bilgisayardan hiç çıkmaz, bulut yalnızca istenirse devreye girer. |
