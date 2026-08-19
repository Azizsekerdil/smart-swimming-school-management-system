# API Başvuru Kılavuzu

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'nin REST API'sini uçtan uca anlatır:
kimlik doğrulama, hata biçimi, sayfalama ve tüm modüllerin uç nokta listesi.
Buradaki yollar, izinler ve alan adları `backend/app/api/v1/` altındaki gerçek
kaynak koddan çıkarılmıştır.

- **Sürüm:** 0.9.0
- **Taban yol:** `/api/v1`
- **Etkileşimli dokümantasyon:** `http://127.0.0.1:8000/docs`
- **Uygulama girişi:** `backend/app/main.py`

---

## 1. Genel Bilgiler

### 1.1 Taban URL

Varsayılan geliştirme kurulumunda backend `127.0.0.1:8000` üzerinde çalışır
(`APP_HOST` / `APP_PORT` ile değiştirilebilir).

| Amaç | URL |
|------|-----|
| API kökü | `http://127.0.0.1:8000/api/v1` |
| Canlılık kontrolü | `http://127.0.0.1:8000/api/ping` |
| Sağlık raporu | `http://127.0.0.1:8000/api/v1/health` |
| Swagger UI | `http://127.0.0.1:8000/docs` |
| ReDoc | `http://127.0.0.1:8000/redoc` |
| OpenAPI şeması | `http://127.0.0.1:8000/openapi.json` |
| Yüklenen dosyalar | `http://127.0.0.1:8000/uploads/...` |

Frontend derlenmişse (`frontend/dist` mevcutsa) aynı sunucu SPA'yı da servis eder;
`api/`, `docs`, `redoc`, `openapi.json` ve `uploads/` dışındaki tüm yollar
`index.html`'e düşer.

### 1.2 İçerik türü ve kodlama

- İstek ve yanıt gövdeleri **JSON**'dur (`Content-Type: application/json`).
- Kodlama **UTF-8**'dir. Türkçe karakterler (`ş`, `ğ`, `İ`, `ı`, `ö`, `ü`, `ç`)
  doğrudan kullanılabilir.
- Tarih/saat alanları ISO-8601 biçimindedir: `2026-09-01T10:00:00`.
- Para alanları ondalıklı sayıdır; varsayılan para birimi `APP_CURRENCY` (`TRY`).
- Rapor dışa aktarma uçları JSON değil ikili (binary) içerik döner
  (`application/pdf`, `application/vnd.openxmlformats-...`, `text/csv`).

### 1.3 Dil seçimi (TR/EN)

API hata ve bilgi mesajları iki dilde tutulur (`backend/app/core/i18n.py`).
Dil şu sırayla belirlenir:

1. `?lang=tr` veya `?lang=en` sorgu parametresi
2. `Accept-Language` başlığı (`tr`, `tr-TR`, `en`, `en-US` …)
3. Varsayılan: `tr`

```bash
curl -H "Accept-Language: en" http://127.0.0.1:8000/api/v1/students
```

Desteklenmeyen bir dil verilirse sessizce `tr`'ye düşülür.

### 1.4 Yanıt başlıkları

Her yanıta `security_headers_middleware` tarafından şu başlıklar eklenir:

| Başlık | Değer |
|--------|-------|
| `X-Process-Time` | İsteğin sunucuda geçirdiği süre (ms) |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` (yalnızca `/api` yolları) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (yalnızca `APP_ENV=production`) |

CORS beyaz listesi `CORS_ORIGINS` ile yönetilir; `Content-Disposition` ve
`X-Process-Time` başlıkları tarayıcıya açılır (`expose_headers`).

---

## 2. Kimlik Doğrulama

Sistem **JWT Bearer** kimlik doğrulaması kullanır. Oturum durumu sunucuda
tutulmaz; her istek kendi jetonunu taşır.

### 2.1 Giriş akışı

```
POST /api/v1/auth/login
        │
        ├─ hız sınırı denetimi (login_attempts tablosu)
        ├─ kullanıcı arama (e-posta küçük harfe indirilir)
        ├─ parola doğrulama (bcrypt) — kullanıcı yoksa da maliyet ödenir
        ├─ hesap kilidi denetimi (locked_until)
        ├─ aktiflik denetimi (is_active)
        └─ access_token + refresh_token
```

**İstek**

```http
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "email": "admin@yuzmeokulu.local",
  "password": "YOUR_PASSWORD"
}
```

**Yanıt `200 OK`**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

### 2.2 Jeton süreleri ve içeriği

| Jeton | Ayar | Varsayılan | İçerik |
|-------|------|-----------|--------|
| `access_token` | `ACCESS_TOKEN_EXPIRE_MINUTES` | 120 dakika | `sub`, `type=access`, `iat`, `exp`, `jti`, `email`, `roles` |
| `refresh_token` | `REFRESH_TOKEN_EXPIRE_DAYS` | 14 gün | `sub`, `type=refresh`, `iat`, `exp`, `jti` |

- İmza algoritması: `HS256` (`JWT_ALGORITHM`), anahtar `SECRET_KEY`.
- `refresh` jetonu ile korumalı uca erişilemez; `get_current_user` yalnızca
  `type == "access"` olan jetonu kabul eder.
- `POST /auth/refresh` yeni bir **access + refresh** çifti üretir.

### 2.3 Jetonun kullanımı

```bash
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
     http://127.0.0.1:8000/api/v1/auth/me
```

`GET /auth/me` yanıtı, kullanıcının rollerinin birleşiminden hesaplanan
**efektif izin kümesini** de içerir:

```json
{
  "id": 1,
  "email": "admin@yuzmeokulu.local",
  "full_name": "Sistem Yöneticisi",
  "language": "tr",
  "theme": "light",
  "is_active": true,
  "is_superuser": true,
  "must_change_password": false,
  "onboarding_completed": true,
  "training_mode": false,
  "roles": [{ "id": 1, "code": "system_admin", "name_tr": "Sistem Yöneticisi", "name_en": "System Administrator" }],
  "permissions": ["ai:caio", "ai:configure", "ai:developer", "ai:use", "attendance:read", "..."],
  "student_id": null,
  "guardian_id": null,
  "instructor_id": null
}
```

### 2.4 Örnek curl akışı

```bash
# 1) Giriş yap ve access token'ı değişkene al
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yuzmeokulu.local","password":"YOUR_PASSWORD"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 2) Korumalı bir uca istek at
curl -s http://127.0.0.1:8000/api/v1/students?page=1&page_size=10 \
  -H "Authorization: Bearer $TOKEN"

# 3) Jetonu yenile
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<REFRESH_TOKEN>"}'
```

### 2.5 Parola politikası

`POST /auth/change-password` ve kullanıcı oluşturma sırasında uygulanır
(`backend/app/core/security.py::password_strength_issues`):

| Kural | Hata kodu |
|-------|-----------|
| En az 8 karakter | `min_length` |
| En az bir rakam | `needs_digit` |
| En az bir harf | `needs_letter` |
| Yaygın parola listesinde olmama | `too_common` |

İhlal durumunda `422` ve `details.issues` içinde ihlal listesi döner.

---

## 3. Hata Biçimi

Tüm hatalar tek bir zarf yapısıyla döner (`backend/app/core/exceptions.py`).
İç ayrıntılar (yığın izi, SQL metni, dosya yolu) istemciye **asla** sızmaz;
ayrıntı yalnızca sunucu loglarına yazılır.

```json
{
  "error": {
    "code": "lesson.conflict_lane",
    "message": "Çakışma: Kulvar bu saatte başka bir ders tarafından kullanılıyor.",
    "details": { }
  }
}
```

| Alan | Açıklama |
|------|----------|
| `code` | Kararlı, makine tarafından okunabilir mesaj anahtarı (`kaynak.durum`) |
| `message` | `Accept-Language`/`?lang=` ile seçilen dilde insan okunur metin |
| `details` | İsteğe bağlı. Yalnızca ek bağlam varsa bulunur |

### 3.1 HTTP durum kodları

| Kod | İstisna sınıfı | Ne zaman |
|-----|----------------|----------|
| `200` | — | Başarılı okuma/güncelleme |
| `201` | — | Kayıt oluşturuldu |
| `400` | `AppError` (taban) | Genel iş kuralı ihlali (ör. mevcut parola hatalı) |
| `401` | `AuthenticationError` | Jeton yok / geçersiz / süresi dolmuş / hesap pasif |
| `403` | `PermissionDeniedError`, `SecurityPolicyError` | İzin yetersiz, güvenlik politikası engelledi |
| `404` | `NotFoundError` | Kayıt bulunamadı |
| `409` | `ConflictError`, `SchedulingConflictError`, `IntegrityError` | Benzersizlik ihlali, ilişkili kayıt, ders çakışması |
| `422` | `ValidationError`, `RequestValidationError` | Şema doğrulaması veya iş kuralı doğrulaması başarısız |
| `429` | `RateLimitError` | Hız sınırı aşıldı veya hesap kilitli |
| `500` | `SQLAlchemyError`, işlenmemiş hata | Sunucu hatası (istemciye genel mesaj döner) |
| `503` | `AIProviderError` | Yapay zekâ sağlayıcısına ulaşılamıyor |

### 3.2 Sık kullanılan hata kodları

| `code` | HTTP | Türkçe mesaj |
|--------|------|--------------|
| `auth.invalid_credentials` | 401 | E-posta veya parola hatalı. |
| `auth.not_authenticated` | 401 | Bu işlem için giriş yapmanız gerekiyor. |
| `auth.invalid_token` | 401 | Oturum bilgisi geçersiz veya süresi dolmuş. |
| `auth.inactive_user` | 401 | Bu hesap devre dışı bırakılmış. |
| `auth.forbidden` | 403 | Bu işlem için yetkiniz bulunmuyor. |
| `auth.rate_limited` | 429 | Çok fazla deneme yapıldı. Lütfen bir dakika sonra tekrar deneyin. |
| `auth.password_weak` | 422 | Parola politikası karşılanmıyor: en az 8 karakter, harf ve rakam içermeli. |
| `common.not_found` | 404 | Kayıt bulunamadı. |
| `common.already_exists` | 409 | Bu kayıt zaten mevcut. |
| `common.in_use` | 409 | Bu kayıt başka kayıtlar tarafından kullanıldığı için silinemez. |
| `common.validation_error` | 422 | Girilen veriler geçersiz. |
| `common.internal_error` | 500 | Beklenmeyen bir hata oluştu. Sistem yöneticinize başvurun. |
| `lesson.conflict_instructor` | 409 | Çakışma: Eğitmen bu saatte başka bir derste görevli. |
| `lesson.conflict_lane` | 409 | Çakışma: Kulvar bu saatte başka bir ders tarafından kullanılıyor. |
| `lesson.conflict_student` | 409 | Çakışma: Öğrenci bu saatte başka bir derse kayıtlı. |
| `lesson.capacity_full` | 409 | Ders kontenjanı dolu. |
| `pool.under_maintenance` | 409 | Havuz seçilen tarihte bakımda. |
| `pool.outside_hours` | 409 | Seçilen saat havuzun çalışma saatleri dışında. |
| `membership.no_credits` | 409 | Pakette kalan ders hakkı bulunmuyor. |
| `payment.exceeds_balance` | 422 | Ödeme tutarı kalan borcu aşıyor. |
| `ai.provider_unavailable` | 503 | Yapay zekâ sağlayıcısına ulaşılamıyor. Yüzme okulu sistemi normal çalışmaya devam ediyor. |
| `ai.command_blocked` | 403 | Güvenlik politikası bu komutu engelledi. |
| `ai.path_outside_project` | 403 | Güvenlik: Proje dizini dışındaki dosyalara erişilemez. |
| `backup.integrity_failed` | 409 | Yedek bütünlük doğrulaması başarısız. Geri yükleme iptal edildi. |
| `report.unsupported_format` | 422 | Desteklenmeyen dışa aktarma biçimi. |

### 3.3 Yetki hatasının `details` yapısı

`require_permissions` bağımlılığı, hangi iznin eksik olduğunu döndürür:

```json
{
  "error": {
    "code": "auth.forbidden",
    "message": "Bu işlem için yetkiniz bulunmuyor.",
    "details": {
      "required": ["finance:write"],
      "missing": ["finance:write"]
    }
  }
}
```

### 3.4 Şema doğrulama hatasının `details` yapısı

```json
{
  "error": {
    "code": "common.validation_error",
    "message": "Girilen veriler geçersiz.",
    "details": {
      "fields": [
        { "field": "email", "type": "string_pattern_mismatch" },
        { "field": "password", "type": "string_too_short" }
      ]
    }
  }
}
```

### 3.5 Çakışma hatasının `details.conflicts` yapısı

Ders oluşturma/taşıma sırasında çakışma bulunursa `SchedulingConflictError`
(HTTP `409`) fırlatılır. `details` iki liste taşır: `conflicts` (engelleyici) ve
`warnings` (bilgilendirici).

```json
{
  "error": {
    "code": "lesson.conflict_lane",
    "message": "Çakışma: Kulvar bu saatte başka bir ders tarafından kullanılıyor.",
    "details": {
      "conflicts": [
        {
          "kind": "lane",
          "message_key": "lesson.conflict_lane",
          "message": "Çakışma: Kulvar bu saatte başka bir ders tarafından kullanılıyor.",
          "lesson_id": 412,
          "lesson_title": "Yıldızlar Grubu - Teknik",
          "entity_id": 3,
          "entity_name": "Kulvar 3",
          "start_at": "2026-09-01T10:00:00",
          "end_at": "2026-09-01T11:00:00",
          "severity": "error"
        },
        {
          "kind": "instructor",
          "message_key": "lesson.conflict_instructor",
          "message": "Çakışma: Eğitmen bu saatte başka bir derste görevli.",
          "lesson_id": 415,
          "lesson_title": "Özel Ders - Deniz K.",
          "entity_id": 7,
          "entity_name": "Ayşe Yıldız",
          "start_at": "2026-09-01T10:30:00",
          "end_at": "2026-09-01T11:15:00",
          "severity": "error"
        }
      ],
      "warnings": [
        {
          "kind": "pool_hours",
          "message_key": "pool.outside_hours",
          "message": "Seçilen saat havuzun çalışma saatleri dışında.",
          "entity_id": 1,
          "entity_name": "Ana Havuz",
          "severity": "warning"
        }
      ]
    }
  }
}
```

**`kind` alanının alabileceği değerler:** `instructor`, `lane`, `student`,
`pool_maintenance`, `pool_hours`, `holiday`.
**`severity`:** `error` (kaydı engeller) veya `warning` (yalnızca uyarır).

Yetkili kullanıcı `"force": true` göndererek engelleyici çakışmaları geçebilir;
bu durumda denetim kaydına `{"forced": true, "conflict_count": N}` yazılır.

---

## 4. Sayfalama ve Sıralama

Liste uçlarının çoğu `pagination` bağımlılığını kullanır
(`backend/app/api/deps.py`).

### 4.1 Sorgu parametreleri

| Parametre | Tip | Varsayılan | Sınırlar |
|-----------|-----|-----------|----------|
| `page` | int | `1` | En az `1` (küçük değerler `1`'e yükseltilir) |
| `page_size` | int | `25` | `1` – `200` arası kırpılır |
| `sort_by` | string | uca özel | Model üzerinde var olan bir sütun adı |
| `sort_dir` | string | `asc` | `asc` \| `desc` (başka değer `asc` sayılır) |

Geçersiz bir `sort_by` verilirse ucun varsayılan sıralaması uygulanır
(örneğin `/lessons` için `start_at`, `/students` için `last_name`).

### 4.2 `Page<T>` yanıt yapısı

```json
{
  "items": [ /* T tipinde kayıtlar */ ],
  "total": 137,
  "page": 2,
  "page_size": 25
}
```

| Alan | Açıklama |
|------|----------|
| `items` | Geçerli sayfadaki kayıtlar |
| `total` | Filtreler uygulandıktan sonraki toplam kayıt sayısı |
| `page` | Geçerli sayfa numarası (1 tabanlı) |
| `page_size` | Sayfa başına kayıt sayısı |

Toplam sayfa sayısı istemcide `Math.ceil(total / page_size)` ile hesaplanır.

### 4.3 Örnek

```bash
curl -G http://127.0.0.1:8000/api/v1/students \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "page=2" \
  --data-urlencode "page_size=50" \
  --data-urlencode "sort_by=last_name" \
  --data-urlencode "sort_dir=desc" \
  --data-urlencode "q=yıl" \
  --data-urlencode "status=active"
```

> Not: Bazı uçlar sayfalama yerine düz liste döner (örneğin `GET /pools`,
> `GET /packages`, `GET /finance/discounts`). Yanıt tipi Swagger UI'da
> `Page[...]` ya da `array` olarak görünür.

---

## 5. Uç Nokta Referansı

Tüm yollar `/api/v1` önekine eklenir. "Gerekli izin" sütunundaki değerler
`backend/app/core/permissions.py` içindeki `Perm` kodlarıdır.

- **Oturum** = geçerli access token yeterli, ek izin aranmaz.
- **Açık** = kimlik doğrulaması gerektirmez.
- `is_superuser` olan kullanıcı tüm izin denetimlerini geçer.

### 5.1 Kimlik Doğrulama — `/auth`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| POST | `/auth/login` | Giriş yapar, access + refresh jetonu üretir | Açık |
| POST | `/auth/refresh` | Refresh jetonu ile yeni jeton çifti üretir | Açık (geçerli refresh jetonu) |
| GET | `/auth/me` | Oturum bilgisi, roller ve efektif izinler | Oturum |
| POST | `/auth/change-password` | Kendi parolasını değiştirir | Oturum |
| PATCH | `/auth/preferences` | Dil, tema, eğitim modu, onboarding durumu | Oturum |
| POST | `/auth/logout` | Denetim kaydı bırakır (jeton istemcide silinir) | Oturum |

### 5.2 Kullanıcılar ve Roller — `/users`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/users` | Kullanıcıları listeler (`Page<UserOut>`) | `user:read` |
| POST | `/users` | Kullanıcı oluşturur ve rol atar | `user:write` |
| GET | `/users/permissions` | Tüm izin kodları, kaynağa göre gruplanmış | `role:manage` |
| GET | `/users/roles` | Veritabanındaki rolleri izin listeleriyle döner | Oturum |
| GET | `/users/roles/catalog` | Rol kataloğu (yönetim/eğitim/diğer, yerelleştirilmiş etiketler) | Açık |
| GET | `/users/{user_id}` | Kullanıcı detayı | `user:read` |
| PATCH | `/users/{user_id}` | Ad, telefon, dil, tema, aktiflik, roller | `user:write` |
| POST | `/users/reset-password` | Yönetici parola sıfırlama | `user:write` |
| DELETE | `/users/{user_id}` | Kullanıcıyı devre dışı bırakır (yumuşak silme) | `user:delete` |

### 5.3 Öğrenciler — `/students`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/students` | Öğrenci listesi; `q`, `status`, `swim_level`, `group_id`, `instructor_id`, `min_age`, `max_age`, `include_demo` filtreleri | `student:read` |
| POST | `/students` | Öğrenci oluşturur, numara üretir, KVKK rıza tarihi yazar | `student:write` |
| GET | `/students/stats/overview` | Öğrenci özet sayıları | `student:read` |
| GET | `/students/{student_id}` | Öğrenci detayı (veli, grup, eğitmen) | `student:read` |
| PATCH | `/students/{student_id}` | Öğrenci günceller | `student:write` |
| DELETE | `/students/{student_id}` | Öğrenciyi siler | `student:delete` |
| POST | `/students/{student_id}/guardians/{guardian_id}` | Veli bağlar | `student:write` |
| DELETE | `/students/{student_id}/guardians/{guardian_id}` | Veli bağını kaldırır | `student:write` |
| GET | `/students/{student_id}/timeline` | Ders, yoklama, ödeme, performans zaman çizelgesi | `student:read` |
| GET | `/students/groups/list` | Grupları hafif liste olarak döner | `student:read` |

> `health_notes` ve `special_needs` alanları yalnızca `student:read_sensitive`
> iznine sahip kullanıcılara döner; aksi hâlde `null` olarak maskelenir.

### 5.4 Veliler — `/guardians`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/guardians` | Veli listesi | `guardian:read` |
| POST | `/guardians` | Veli oluşturur | `guardian:write` |
| GET | `/guardians/portal/my-children` | Veli portalı: bağlı öğrencilerin özeti | Oturum (satır kapsamı uygulanır) |
| GET | `/guardians/{guardian_id}` | Veli detayı | `guardian:read` |
| PATCH | `/guardians/{guardian_id}` | Veli günceller | `guardian:write` |
| DELETE | `/guardians/{guardian_id}` | Veli siler | `guardian:delete` |

### 5.5 Eğitmenler — `/instructors`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/instructors` | Eğitmen listesi | `instructor:read` |
| POST | `/instructors` | Eğitmen oluşturur | `instructor:write` |
| GET | `/instructors/workload` | Eğitmen başına ders/saat/doluluk | `instructor:read` |
| GET | `/instructors/{instructor_id}` | Eğitmen detayı (sertifika, müsaitlik, izin) | `instructor:read` |
| PATCH | `/instructors/{instructor_id}` | Eğitmen günceller | `instructor:write` |
| DELETE | `/instructors/{instructor_id}` | Eğitmeni pasife alır | `instructor:delete` |
| POST | `/instructors/{instructor_id}/certificates` | Sertifika ekler | `instructor:write` |
| DELETE | `/instructors/{instructor_id}/certificates/{cert_id}` | Sertifika siler | `instructor:write` |
| PUT | `/instructors/{instructor_id}/availability` | Haftalık müsaitlik takvimini ayarlar | `instructor:write` |
| POST | `/instructors/{instructor_id}/leaves` | İzin ekler | `instructor:write` |
| DELETE | `/instructors/leaves/{leave_id}` | İzin siler | `instructor:write` |

> `monthly_salary` ve `hourly_rate` alanları yalnızca `system_admin`,
> `school_director`, `finance`, `hr` rollerine (veya superuser'a) döner;
> diğer kullanıcılarda `null`'lanır.

### 5.6 Gruplar — `/groups`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/groups` | Grupları listeler (yaş aralığı, seviye, kapasite, renk) | `student:read` |
| POST | `/groups` | Grup oluşturur | `student:write` |
| PATCH | `/groups/{group_id}` | Grup günceller | `student:write` |
| DELETE | `/groups/{group_id}` | Grup siler | `student:write` |

### 5.7 Havuzlar, Kulvarlar ve Tesis — `/pools`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/pools` | Havuzları listeler | `pool:read` |
| POST | `/pools` | Havuz oluşturur | `pool:write` |
| GET | `/pools/summary` | Havuz doluluk özeti | `pool:read` |
| GET | `/pools/{pool_id}` | Havuz detayı | `pool:read` |
| PATCH | `/pools/{pool_id}` | Havuz günceller | `pool:write` |
| DELETE | `/pools/{pool_id}` | Havuz siler | `pool:delete` |
| GET | `/pools/{pool_id}/lanes` | Kulvarları listeler | `pool:read` |
| POST | `/pools/lanes` | Kulvar ekler | `pool:write` |
| PATCH | `/pools/lanes/{lane_id}` | Kulvar günceller | `pool:write` |
| DELETE | `/pools/lanes/{lane_id}` | Kulvar siler | `pool:delete` |
| GET | `/pools/{pool_id}/lane-plan` | Günlük saat × kulvar doluluk şeması | `pool:read` |
| GET | `/pools/{pool_id}/free-lanes` | Verilen aralıkta boş kulvarları bulur | `pool:read` |
| GET | `/pools/{pool_id}/suggest-slots` | Çakışmasız zaman dilimi önerir | `lesson:schedule` |
| GET | `/pools/{pool_id}/maintenance` | Bakım kayıtları | `pool:read` |
| POST | `/pools/maintenance` | Bakım planlar | `pool:maintenance` |
| PATCH | `/pools/maintenance/{maintenance_id}` | Bakım günceller | `pool:maintenance` |
| GET | `/pools/{pool_id}/water-quality` | Su kalitesi ölçümleri | `pool:read` |
| POST | `/pools/water-quality` | Su ölçümü kaydeder (limit dışıysa bildirim üretir) | `pool:maintenance` |
| GET | `/pools/calendar/holidays` | Tatil günlerini listeler | `pool:read` |
| POST | `/pools/calendar/holidays` | Tatil ekler | `lesson:schedule` |
| DELETE | `/pools/calendar/holidays/{holiday_id}` | Tatil siler | `lesson:schedule` |

### 5.8 Dersler ve Takvim — `/lessons`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/lessons` | Ders listesi; `date_from`, `date_to`, `pool_id`, `lane_id`, `instructor_id`, `group_id`, `lesson_type`, `status` | `lesson:read` |
| POST | `/lessons` | Ders oluşturur (çakışma denetimli, `force` ile zorlanabilir) | `lesson:write` |
| POST | `/lessons/check-conflicts` | Kaydetmeden önce çakışma önizlemesi | `lesson:read` |
| GET | `/lessons/calendar` | Takvim olayları (`start`, `end`; en fazla 120 gün) | `lesson:read` |
| POST | `/lessons/series` | Haftalık tekrarlanan ders serisi üretir | `lesson:schedule` |
| GET | `/lessons/series` | Serileri listeler | `lesson:read` |
| DELETE | `/lessons/series/{series_id}` | Seriyi siler | `lesson:delete` |
| GET | `/lessons/{lesson_id}` | Ders detayı ve kayıtlı öğrenciler | `lesson:read` |
| PATCH | `/lessons/{lesson_id}` | Ders günceller | `lesson:write` |
| POST | `/lessons/{lesson_id}/move` | Sürükle-bırak ile taşır (çakışma denetimli) | `lesson:schedule` |
| POST | `/lessons/{lesson_id}/cancel` | Dersi iptal eder (gerekçeli) | `lesson:write` |
| DELETE | `/lessons/{lesson_id}` | Dersi siler | `lesson:delete` |
| POST | `/lessons/{lesson_id}/enroll` | Derse öğrenci kaydeder | `lesson:write` |
| DELETE | `/lessons/{lesson_id}/enroll/{student_id}` | Ders kaydını kaldırır | `lesson:write` |
| GET | `/lessons/{lesson_id}/roster` | Ders listesi (yoklama öncesi) | `lesson:read` |
| GET | `/lessons/today/list` | Bugünün derslerini döner | `lesson:read` |

> Satır bazlı kapsam: eğitmen rolleri yalnızca kendi derslerini, öğrenci/veli
> rolleri yalnızca kayıtlı oldukları dersleri görür.

### 5.9 Yoklama — `/attendance`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/attendance/sheet/{lesson_id}` | Yoklama ekranı verisi (öğrenciler + mevcut durum + kalan hak) | `attendance:read` |
| POST | `/attendance` | Toplu yoklama kaydeder/günceller, ders hakkı düşer | `attendance:write` |
| GET | `/attendance` | Yoklama kayıtlarını sayfalı listeler | `attendance:read` |
| PATCH | `/attendance/{attendance_id}` | Tek kaydı düzeltir | `attendance:write` |
| GET | `/attendance/student/{student_id}/summary` | Öğrenci devam özeti | `attendance:read` |
| POST | `/attendance/qr/generate/{lesson_id}` | Ders için tek kullanımlık QR jetonu üretir | `attendance:write` |
| POST | `/attendance/qr/checkin` | QR jetonu + kart kodu ile giriş kaydeder | `attendance:write` |
| POST | `/attendance/cards/{student_id}` | Öğrenci kartı (kart kodu) oluşturur | `student:write` |
| POST | `/attendance/{attendance_id}/makeup` | Telafi dersi atar | `attendance:write` |

**Durum kodları (`AttendanceStatus`):** `present`, `absent`, `late`, `excused`,
`cancelled`, `makeup`.
**Yöntemler (`AttendanceMethod`):** `manual`, `qr`, `card`, `rfid`, `nfc`.

### 5.10 Üyelikler — `/memberships`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/memberships` | Üyelik listesi | `membership:read` |
| POST | `/memberships` | Üyelik oluşturur | `membership:write` |
| GET | `/memberships/expiring` | Süresi yaklaşan üyelikler | `membership:read` |
| GET | `/memberships/low-credit` | Ders hakkı azalan üyelikler | `membership:read` |
| GET | `/memberships/{membership_id}` | Üyelik detayı | `membership:read` |
| PATCH | `/memberships/{membership_id}` | Üyelik günceller | `membership:write` |
| POST | `/memberships/{membership_id}/freeze` | Üyeliği dondurur (paket limitine bakar) | `membership:write` |
| POST | `/memberships/{membership_id}/unfreeze` | Dondurmayı kaldırır | `membership:write` |
| POST | `/memberships/{membership_id}/renew` | Üyeliği yeniler | `membership:write` |
| POST | `/memberships/{membership_id}/cancel` | Üyeliği iptal eder | `membership:write` |
| POST | `/memberships/refresh-statuses` | Tüm üyelik durumlarını yeniden hesaplar | `membership:write` |

### 5.11 Paketler — `/packages`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/packages` | Paketleri listeler | `membership:read` |
| POST | `/packages` | Paket oluşturur | `membership:write` |
| PATCH | `/packages/{package_id}` | Paket günceller | `membership:write` |
| DELETE | `/packages/{package_id}` | Paketi pasife alır | `membership:write` |

### 5.12 Finans — `/finance`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/finance/payments` | Ödemeleri listeler | `finance:read` |
| POST | `/finance/payments` | Ödeme alır (fatura bakiyesini günceller) | `finance:write` |
| PATCH | `/finance/payments/{payment_id}` | Ödeme günceller | `finance:write` |
| POST | `/finance/payments/{payment_id}/refund` | İade işler | `finance:write` |
| DELETE | `/finance/payments/{payment_id}` | Ödemeyi iptal eder | `finance:delete` |
| GET | `/finance/invoices` | Faturaları listeler | `finance:read` |
| POST | `/finance/invoices` | Fatura oluşturur | `finance:write` |
| GET | `/finance/outstanding` | Bekleyen borçlar / yaşlandırma | `finance:read` |
| GET | `/finance/expenses` | Giderleri listeler | `finance:read` |
| POST | `/finance/expenses` | Gider ekler | `finance:write` |
| PATCH | `/finance/expenses/{expense_id}` | Gider günceller | `finance:write` |
| DELETE | `/finance/expenses/{expense_id}` | Gider siler | `finance:delete` |
| GET | `/finance/discounts` | İndirimleri listeler | `finance:read` |
| POST | `/finance/discounts` | İndirim tanımlar | `finance:write` |
| GET | `/finance/summary` | Finans panosu (gelir, gider, net) | `finance:read` |

### 5.13 Performans — `/performance`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/performance` | Performans kayıtlarını listeler | `performance:read` |
| POST | `/performance` | Performans kaydeder, kişisel rekoru günceller | `performance:write` |
| GET | `/performance/events/catalog` | Stil, mesafe ve kulvar türü kataloğu | Açık |
| GET | `/performance/student/{student_id}/summary` | Sporcu performans özeti | `performance:read` |
| GET | `/performance/student/{student_id}/event` | Tek etkinlik analizi (eğilim, split) | `performance:read` |
| GET | `/performance/student/{student_id}/personal-bests` | Kişisel rekorlar | `performance:read` |
| GET | `/performance/top-improvers` | En çok gelişen sporcular | `performance:read` |
| GET | `/performance/declining` | Performansı düşen sporcular | `performance:read` |
| GET | `/performance/readiness` | Yarışma hazırlık göstergesi | `performance:read` |
| PATCH | `/performance/{record_id}` | Kaydı günceller | `performance:write` |
| DELETE | `/performance/{record_id}` | Kaydı siler | `performance:write` |
| GET | `/performance/training-plans` | Antrenman planlarını listeler | `performance:read` |
| POST | `/performance/training-plans` | Antrenman planı oluşturur | `performance:write` |
| POST | `/performance/training-plans/{plan_id}/approve` | AI taslak planını onaylar | `performance:write` |

### 5.14 Yarışmalar — `/competitions`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/competitions` | Yarışmaları listeler | `competition:read` |
| POST | `/competitions` | Yarışma oluşturur | `competition:write` |
| GET | `/competitions/records` | Kulüp rekorları | `competition:read` |
| GET | `/competitions/medals/summary` | Madalya tablosu | `competition:read` |
| GET | `/competitions/{competition_id}` | Yarışma detayı | `competition:read` |
| PATCH | `/competitions/{competition_id}` | Yarışma günceller | `competition:write` |
| DELETE | `/competitions/{competition_id}` | Yarışma siler | `competition:write` |
| POST | `/competitions/events` | Yarışmaya etkinlik ekler | `competition:write` |
| DELETE | `/competitions/events/{event_id}` | Etkinlik siler | `competition:write` |
| POST | `/competitions/entries` | Sporcuyu etkinliğe kaydeder | `competition:write` |
| PATCH | `/competitions/entries/{entry_id}/result` | Sonuç girer (rekor kontrolü yapar) | `competition:write` |
| DELETE | `/competitions/entries/{entry_id}` | Yarışma kaydını siler | `competition:write` |
| POST | `/competitions/events/{event_id}/seed-heats` | Standart kurala göre seri/kulvar dağıtır | `competition:write` |
| GET | `/competitions/{competition_id}/results` | Yarışma sonuç raporu | `competition:read` |

### 5.15 İstatistikler — `/statistics`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/statistics/dashboard` | Ana kontrol paneli özeti | `statistics:read` |
| GET | `/statistics/students` | Öğrenci istatistikleri | `statistics:read` |
| GET | `/statistics/instructors` | Eğitmen istatistikleri | `statistics:read` |
| GET | `/statistics/pools` | Havuz ve kulvar istatistikleri | `statistics:read` |
| GET | `/statistics/attendance` | Yoklama istatistikleri | `statistics:read` |
| GET | `/statistics/kpi` | KPI panosu (gerçekleşme + hedef) | `statistics:read` |
| GET | `/statistics/kpi/targets` | KPI hedeflerini listeler | `statistics:read` |
| PUT | `/statistics/kpi/targets` | KPI hedefi belirler | `kpi:write` |
| GET | `/statistics/cohort` | Cohort tutundurma analizi | `statistics:read` |
| GET | `/statistics/outliers/attendance` | Devam aykırı değerleri | `statistics:read` |
| GET | `/statistics/correlation/attendance-performance` | Devam-performans korelasyonu | `statistics:read` |
| GET | `/statistics/distribution/{metric}` | Dağılım analizi (histogram, persentil) | `statistics:read` |
| GET | `/statistics/overview` | Tüm istatistiklerin tek çağrıda özeti | `statistics:read` |

### 5.16 Raporlar — `/reports`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/reports/definitions` | Kullanıcının yetkili olduğu rapor kataloğu | Oturum |
| POST | `/reports/preview` | Raporu ekranda önizler (JSON) | `report:read` + rapora özel izin |
| POST | `/reports/export` | Raporu PDF/Excel/CSV/JSON olarak indirir | `report:export` + rapora özel izin |
| GET | `/reports/templates` | Kendi ve paylaşılan şablonlar | `report:read` |
| POST | `/reports/templates` | Şablon kaydeder | `report:read` |
| DELETE | `/reports/templates/{template_id}` | Şablon siler (yalnızca sahibi veya superuser) | `report:read` |

Her rapor tanımının kendi `required_permission` değeri vardır; örneğin
`finance` raporu `finance:read`, `student_progress` raporu `performance:read`
gerektirir. Yetkisiz `report_key` ile istek `403 auth.forbidden` döner,
tanımsız `report_key` ise `404 common.not_found` döner.

Rapor anahtarlarından bazıları: `daily_manager`, `weekly_management`,
`monthly_management`, `student_list`, `student_progress`, `attendance`,
`instructor_workload`, `pool_usage`, `lane_occupancy`, `finance`,
`collections`, `outstanding`, `membership`.

### 5.17 Yapay Zekâ — `/ai`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/ai/control-center` | Sağlayıcı durumu, gecikme, model ve token sayaçları | `ai:use` |
| GET | `/ai/providers/{provider}/models` | Sağlayıcının model listesi | `ai:use` |
| POST | `/ai/providers/{provider}/health` | Sağlayıcı sağlık kontrolü | `ai:use` |
| POST | `/ai/providers/{provider}/test` | 6 aşamalı bağlantı testi (anahtar görünmez) | `ai:configure` |
| GET | `/ai/routing/tasks` | Görev türüne göre model yönlendirme tablosu | `ai:use` |
| POST | `/ai/chat` | Sohbet (fallback zinciriyle) | `ai:use` |
| POST | `/ai/chat/stream` | Sohbet, akış (`text/plain; charset=utf-8`) | `ai:use` |
| POST | `/ai/analyze` | İstatistik motoru + AI yorumu | `ai:use` |
| POST | `/ai/training-plan/{student_id}` | AI antrenman planı taslağı (onay gerektirir) | `ai:use` **ve** `performance:read` |
| GET | `/ai/prompts` | Hazır prompt kütüphanesi | `ai:use` |
| GET | `/ai/tasks` | AI görev geçmişi (sağlayıcı, model, token, süre) | `ai:use` |
| GET | `/ai/config` | AI yapılandırması — API anahtarları maskeli | `ai:configure` |
| PUT | `/ai/config` | Yapılandırmayı `.env`'e yazar ve sağlayıcıları yeniler | `ai:configure` |
| POST | `/ai/reload` | Sağlayıcı kayıt defterini yeniden yükler | `ai:configure` |

`provider` yol parametresi: `local` (LM Studio), `nvidia` (NVIDIA Build),
`openai_compat` (genel OpenAI uyumlu uç).

### 5.18 AI Developer Console — `/ai/developer`

Tüm uçlar `ai:developer` izni ister. Ayrıca `AI_DEVELOPER_ENABLED`,
`AI_DEVELOPER_ALLOW_APPLY` ve `AI_DEVELOPER_ALLOW_SHELL` ortam değişkenleri
ikinci bir kapı görevi görür.

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/ai/developer/policy` | Beyaz liste, yasak desenler, onay gerektiren işlemler | `ai:developer` |
| GET | `/ai/developer/files` | Proje dosya ağacını listeler | `ai:developer` |
| GET | `/ai/developer/file` | Tek dosyayı okur | `ai:developer` |
| GET | `/ai/developer/search` | Kaynak kodda arama | `ai:developer` |
| POST | `/ai/developer/plan` | Görevi planlar ve yama üretir | `ai:developer` |
| GET | `/ai/developer/patches` | Üretilmiş yamaları listeler | `ai:developer` |
| GET | `/ai/developer/patches/{patch_id}` | Yama detayı ve diff | `ai:developer` |
| POST | `/ai/developer/apply` | Yamayı uygular (önce checkpoint alır) | `ai:developer` |
| GET | `/ai/developer/checkpoints` | Geri alma noktaları | `ai:developer` |
| POST | `/ai/developer/rollback` | Değişiklikleri geri alır | `ai:developer` |
| POST | `/ai/developer/run-tests` | Test paketini çalıştırır | `ai:developer` |
| POST | `/ai/developer/shell` | Politika denetimli kabuk komutu | `ai:developer` |
| POST | `/ai/developer/check-command` | Komutu çalıştırmadan politikaya sorar | `ai:developer` |

### 5.19 CAIO Ajanı — `/ai/caio`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| POST | `/ai/caio/run` | Tam CAIO analizini çalıştırır | `ai:caio` |
| GET | `/ai/caio/observe` | Yalnızca kural motoru gözlemi (AI çağırmaz) | `ai:caio` |
| GET | `/ai/caio/findings` | Bulguları sayfalı listeler | `ai:caio` |
| PATCH | `/ai/caio/findings/{finding_id}` | Bulgu durumunu günceller | `ai:caio` |
| GET | `/ai/caio/summary` | CAIO özet kartı | `ai:caio` |

### 5.20 Yedekleme — `/backup`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/backup/status` | Son yedek, zamanlama ve disk durumu | `backup:read` |
| GET | `/backup` | Yedekleri listeler | `backup:read` |
| POST | `/backup` | Şimdi yedek alır (ZIP + manifest + SHA-256) | `backup:create` |
| POST | `/backup/{backup_id}/verify` | Yedeğin bütünlüğünü doğrular | `backup:read` |
| GET | `/backup/{backup_id}/restore-preview` | Geri yükleme önizlemesi (ne değişecek) | `backup:restore` |
| POST | `/backup/restore` | Güvenli geri yükleme akışını çalıştırır | `backup:restore` |
| POST | `/backup/{backup_id}/protect` | Yedeği saklama politikasından korur | `backup:create` |
| DELETE | `/backup/{backup_id}` | Yedeği siler (korunanlar silinemez) | `backup:create` |
| POST | `/backup/cleanup` | Saklama politikasına göre eskileri temizler | `backup:create` |
| GET | `/backup/settings/current` | Yedekleme ayarları | `backup:read` |
| GET | `/backup/location/open` | Yedek klasörünün dosya sistemi yolu | `backup:read` |
| GET | `/backup/restores/history` | Geri yükleme geçmişi | `backup:read` |

### 5.21 Arama — `/search`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/search?q=...&limit=8` | Öğrenci, veli, eğitmen, ders, ödeme, havuz, yarışma araması | Oturum (sonuçlar izne göre filtrelenir) |
| GET | `/search/commands` | Ctrl+K komut paleti komutları | Oturum |
| GET | `/search/quick-stats` | Arama kutusu hızlı sayaçları | Oturum |

`q` en az 2 karakter olmalıdır; daha kısa sorgu boş sonuç döner. Her grup
yalnızca kullanıcının ilgili `*:read` iznine sahip olduğu durumda doldurulur ve
satır bazlı kapsam ayrıca uygulanır.

### 5.22 Eğitim Merkezi — `/training`

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/training/tutorials` | Eğitimleri listeler (`category`, `recommended_only`) | Oturum |
| GET | `/training/tutorials/{tutorial_id}` | Eğitim detayı ve adımları | Oturum |
| POST | `/training/progress` | Eğitim ilerlemesini kaydeder | Oturum |
| GET | `/training/overview` | Eğitim ilerleme özeti | Oturum |
| GET | `/training/onboarding` | Onboarding durumu | Oturum |
| GET | `/training/onboarding/steps` | Onboarding adımları | Oturum |
| POST | `/training/onboarding/complete` | Onboarding'i tamamlar | Oturum |
| POST | `/training/onboarding/skip` | Onboarding'i geçer | Oturum |
| POST | `/training/mode/{enabled}` | Eğitim modunu açar/kapatır | Oturum |

### 5.23 Sistem — önek yok

Bu uçlar `/api/v1` altında, ek bir modül öneki olmadan sunulur.

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/health` | Backend, veritabanı, AI ve frontend bileşen durumu | Açık |
| GET | `/about` | Sürüm, derleme, git commit, DB revizyonu, Python/platform | Açık |
| GET | `/settings` | Uygulama ayarlarını listeler (sır işaretli olanlar hariç) | `settings:read` |
| GET | `/settings/{key}` | Tek ayarı okur (sır ise `404`) | Oturum |
| PUT | `/settings` | Ayar oluşturur/günceller | `settings:write` |
| GET | `/i18n/validate` | Backend mesajlarında eksik çeviri denetimi | `settings:read` |
| GET | `/audit` | Denetim kayıtlarını sayfalı listeler | `audit:read` |
| GET | `/notifications` | Kullanıcının bildirimleri | Oturum |
| GET | `/notifications/counts` | Okunmamış bildirim sayaçları | Oturum |
| POST | `/notifications/{notification_id}/read` | Bildirimi okundu işaretler | Oturum |
| POST | `/notifications/read-all` | Tümünü okundu işaretler | Oturum |
| POST | `/notifications` | Bildirim gönderir | `notification:send` |
| POST | `/notifications/generate` | Otomatik bildirimleri üretir | `notification:send` |

Ayrıca `/api/v1` dışında, sürümsüz bir canlılık ucu bulunur:

| Metod | Yol | Açıklama | Gerekli izin |
|-------|-----|----------|--------------|
| GET | `/api/ping` | `{"status":"ok","app":...,"version":...}` | Açık |

---

## 6. Önemli Akışlar

### 6.1 Giriş ve oturum

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -H "Accept-Language: tr" \
  -d '{"email":"admin@yuzmeokulu.local","password":"YOUR_PASSWORD"}'
```

Başarılı yanıt (`200`):

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 7200
}
```

Hatalı parola (`401`):

```json
{
  "error": {
    "code": "auth.invalid_credentials",
    "message": "E-posta veya parola hatalı."
  }
}
```

Aynı e-posta için son bir dakikada `RATE_LIMIT_LOGIN_PER_MINUTE` (varsayılan 10)
başarısız deneme olursa `429 auth.rate_limited` döner. 8 ardışık başarısız
denemede hesap 15 dakika kilitlenir; kilit süresince de `429` döner.

### 6.2 Çakışma denetimli ders oluşturma

**Adım 1 — Önizleme**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/lessons/check-conflicts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "start_at": "2026-09-01T10:00:00",
        "end_at":   "2026-09-01T11:00:00",
        "pool_id": 1,
        "lane_id": 3,
        "instructor_id": 7,
        "student_ids": [15, 22, 31]
      }'
```

Yanıt (`200`) — çakışma yoksa:

```json
{ "has_conflict": false, "conflicts": [], "warnings": [] }
```

**Adım 2 — Oluşturma**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/lessons \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Yıldızlar Grubu - Teknik",
        "lesson_type": "group",
        "start_at": "2026-09-01T10:00:00",
        "end_at":   "2026-09-01T11:00:00",
        "pool_id": 1,
        "lane_id": 3,
        "instructor_id": 7,
        "group_id": 2,
        "capacity": 8,
        "student_ids": [15, 22, 31],
        "force": false
      }'
```

Başarılı yanıt (`201`, `LessonDetail`):

```json
{
  "id": 512,
  "title": "Yıldızlar Grubu - Teknik",
  "lesson_type": "group",
  "status": "scheduled",
  "start_at": "2026-09-01T10:00:00",
  "end_at": "2026-09-01T11:00:00",
  "duration_minutes": 60,
  "pool_id": 1,
  "pool_name": "Ana Havuz",
  "lane_id": 3,
  "lane_name": "Kulvar 3",
  "instructor_id": 7,
  "instructor_name": "Ayşe Yıldız",
  "group_name": "Yıldızlar",
  "capacity": 8,
  "enrolled_count": 3,
  "occupancy_rate": 37.5,
  "enrollments": [
    { "id": 990, "lesson_id": 512, "student_id": 15, "student_name": "Deniz Kaya", "student_number": "STU-0015", "status": "active", "membership_id": null }
  ]
}
```

Çakışma varsa `409` ve `details.conflicts` (bkz. bölüm 3.5). Yetkili kullanıcı
aynı isteği `"force": true` ile tekrar göndererek dersi yine de oluşturabilir.

### 6.3 Yoklama alma

**Adım 1 — Yoklama listesini çek**

```bash
curl -s http://127.0.0.1:8000/api/v1/attendance/sheet/512 \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "lesson_id": 512,
  "lesson_title": "Yıldızlar Grubu - Teknik",
  "start_at": "2026-09-01T10:00:00",
  "end_at": "2026-09-01T11:00:00",
  "pool_name": "Ana Havuz",
  "lane_name": "Kulvar 3",
  "instructor_name": "Ayşe Yıldız",
  "is_recorded": false,
  "rows": [
    {
      "student_id": 15,
      "student_number": "STU-0015",
      "full_name": "Deniz Kaya",
      "photo_url": null,
      "enrollment_status": "active",
      "attendance_id": null,
      "status": null,
      "late_minutes": null,
      "notes": null,
      "membership_remaining": 7
    }
  ]
}
```

**Adım 2 — Yoklamayı kaydet**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/attendance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "lesson_id": 512,
        "method": "manual",
        "consume_credits": true,
        "entries": [
          { "student_id": 15, "status": "present" },
          { "student_id": 22, "status": "late", "late_minutes": 8 },
          { "student_id": 31, "status": "excused", "excuse_reason": "Sağlık raporu" }
        ]
      }'
```

Yanıt (`201`, `AttendanceOut` listesi):

```json
[
  {
    "id": 3301,
    "lesson_id": 512,
    "student_id": 15,
    "student_name": "Deniz Kaya",
    "student_number": "STU-0015",
    "lesson_title": "Yıldızlar Grubu - Teknik",
    "lesson_start": "2026-09-01T10:00:00",
    "status": "present",
    "method": "manual",
    "checked_in_at": "2026-09-01T10:03:11",
    "late_minutes": null,
    "excuse_reason": null,
    "notes": null,
    "makeup_lesson_id": null
  }
]
```

`consume_credits: true` iken `present`, `late` ve `makeup` durumları aktif
üyelikten bir ders hakkı düşer. Aynı kayıt için düşüm **bir kez** yapılır
(`LessonEnrollment.credit_consumed` bayrağı); yoklama düzeltmesi çift düşüm
yaratmaz. Hak biterse üyelik `expired` durumuna geçer.

**QR ile giriş**

```bash
# Eğitmen ders için tek kullanımlık jeton üretir
curl -s -X POST http://127.0.0.1:8000/api/v1/attendance/qr/generate/512 \
  -H "Authorization: Bearer $TOKEN"

# Turnike/tablet, öğrenci kartıyla giriş kaydeder
curl -s -X POST http://127.0.0.1:8000/api/v1/attendance/qr/checkin \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"token":"<QR_TOKEN>","card_code":"CARD-0015"}'
```

### 6.4 Rapor dışa aktarma

**Adım 1 — Yetkili raporları öğren**

```bash
curl -s http://127.0.0.1:8000/api/v1/reports/definitions \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  {
    "key": "finance",
    "title_tr": "Finans Raporu",
    "title_en": "Finance Report",
    "description_tr": "Gelir, gider ve net kâr",
    "description_en": "Income, expenses and net profit",
    "category": "finance",
    "filters": ["period"],
    "required_permission": "finance:read"
  }
]
```

**Adım 2 — Önizle**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/reports/preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"report_key":"finance","period":"month","language":"tr"}'
```

**Adım 3 — İndir**

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/reports/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "report_key": "finance",
        "format": "pdf",
        "period": "month",
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "language": "tr",
        "include_charts": true
      }' \
  -OJ
```

Yanıt JSON değildir; ikili içerik ve şu başlık döner:

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="Finans_Raporu_2026-08.pdf"; filename*=UTF-8''Finans_Raporu_2026-08.pdf
```

`filename*` parametresi RFC 5987 biçiminde yüzde kodlamalıdır; Türkçe karakterli
dosya adları bu sayede bozulmadan iner. Desteklenen `format` değerleri:
`pdf`, `xlsx`, `csv`, `json`. Her dışa aktarma denetim kaydına yazılır.

### 6.5 AI analizi (İstatistik + AI ayrımı)

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/ai/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "question": "Ağustos ayında devam oranı neden düştü?",
        "scope": "attendance",
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "provider": "auto",
        "language": "tr"
      }'
```

Yanıt (`200`):

```json
{
  "question": "Ağustos ayında devam oranı neden düştü?",
  "scope": "attendance",
  "metrics": {
    "attendance_rate": 78.4,
    "previous_rate": 88.1,
    "delta": -9.7,
    "absent_count": 142,
    "trend_slope": -0.42
  },
  "metrics_summary_tr": "Devam oranı %88,1'den %78,4'e düştü (-9,7 puan).",
  "metrics_summary_en": "Attendance dropped from 88.1% to 78.4% (-9.7 points).",
  "data_points": 1184,
  "data_sufficient": true,
  "ai_available": true,
  "ai_interpretation": "Düşüşün yaz tatili dönemine denk gelmesi...",
  "ai_possible_causes": ["Yaz tatili", "Sıcaklık artışı", "Sabah seanslarının doluluğu"],
  "ai_recommendations": ["Ağustos için esnek telafi hakkı tanımlayın", "..."],
  "ai_disclaimer_tr": "Bu yorum bir yapay zekâ modeli tarafından üretilmiştir ve kesin gerçek değildir. Kararlarınızı yukarıdaki hesaplanmış verilere dayandırın.",
  "provider": "local",
  "model": "qwen2.5-14b-instruct"
}
```

Tasarım kuralı: `metrics` ve `metrics_summary_*` alanları **İstatistik Motoru
tarafından hesaplanmış gerçek veridir**; `ai_*` alanları bir dil modelinin
yorumudur. Arayüz bunları ayrı panellerde gösterir.

Hiçbir sağlayıcı erişilebilir değilse istek yine `200` döner: `ai_available`
`false` olur, `ai_interpretation` `null` kalır, `metrics` dolu gelir. Yalnızca
`/ai/chat` gibi doğrudan model çağrıları `503 ai.provider_unavailable` veya
`ai.all_providers_failed` döndürür.

`scope` değerleri: `student_performance`, `declining_students`,
`training_suggestion`, `weakest_stroke`, `top_improvers`,
`competition_readiness`, `attendance`, `finance`, `retention`,
`instructor_workload`, `schedule_optimization`, `free_lanes`, `payment_risk`,
`general`.

---

## 7. Kod Örnekleri

Aşağıdaki üç örnek aynı işi yapar: giriş yapar, aktif öğrencilerin ilk
sayfasını çeker ve toplam sayıyı yazdırır.

### 7.1 curl

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE="http://127.0.0.1:8000/api/v1"

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yuzmeokulu.local","password":"YOUR_PASSWORD"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -G "$BASE/students" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept-Language: tr" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=25" \
  --data-urlencode "status=active" \
  | python -c "import sys,json; d=json.load(sys.stdin); print('Toplam:', d['total'])"
```

### 7.2 Python (httpx)

```python
"""Akıllı Yüzme Okulu API - Python istemci örneği."""

import httpx

BASE = "http://127.0.0.1:8000/api/v1"


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        # 1) Giriş
        login = client.post(
            "/auth/login",
            json={"email": "admin@yuzmeokulu.local", "password": "YOUR_PASSWORD"},
        )
        login.raise_for_status()
        tokens = login.json()

        client.headers.update(
            {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Accept-Language": "tr",
            }
        )

        # 2) Aktif öğrencilerin ilk sayfası
        response = client.get(
            "/students",
            params={"page": 1, "page_size": 25, "status": "active"},
        )

        if response.status_code >= 400:
            error = response.json()["error"]
            raise SystemExit(f"[{error['code']}] {error['message']}")

        page = response.json()
        print(f"Toplam: {page['total']}")
        for student in page["items"]:
            print(f"  {student['student_number']} - {student['full_name']}")


if __name__ == "__main__":
    main()
```

### 7.3 JavaScript (fetch)

```javascript
// Akıllı Yüzme Okulu API - fetch istemci örneği (Node 18+ veya tarayıcı)
const BASE = 'http://127.0.0.1:8000/api/v1'

async function request(path, { token, ...options } = {}) {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Accept-Language': 'tr',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const error = body?.error
    throw new Error(error ? `[${error.code}] ${error.message}` : `HTTP ${response.status}`)
  }

  return response.json()
}

async function main() {
  // 1) Giriş
  const { access_token: token } = await request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      email: 'admin@yuzmeokulu.local',
      password: 'YOUR_PASSWORD',
    }),
  })

  // 2) Aktif öğrencilerin ilk sayfası
  const params = new URLSearchParams({ page: '1', page_size: '25', status: 'active' })
  const page = await request(`/students?${params}`, { token })

  console.log(`Toplam: ${page.total}`)
  for (const student of page.items) {
    console.log(`  ${student.student_number} - ${student.full_name}`)
  }
}

main().catch((err) => {
  console.error(err.message)
  process.exit(1)
})
```

### 7.4 Rapor indirme (Python)

```python
import httpx

with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=120.0) as client:
    token = client.post(
        "/auth/login",
        json={"email": "admin@yuzmeokulu.local", "password": "YOUR_PASSWORD"},
    ).json()["access_token"]

    response = client.post(
        "/reports/export",
        headers={"Authorization": f"Bearer {token}"},
        json={"report_key": "finance", "format": "xlsx", "period": "month", "language": "tr"},
    )
    response.raise_for_status()

    # Sunucu dosya adını Content-Disposition ile bildirir
    with open("finans_raporu.xlsx", "wb") as f:
        f.write(response.content)
```

---

## 8. Etkileşimli Dokümantasyon

FastAPI, OpenAPI 3 şemasını çalışma zamanında üretir. Backend ayaktayken:

| Adres | Araç | Kullanım |
|-------|------|----------|
| `http://127.0.0.1:8000/docs` | **Swagger UI** | Uçları tarayıcıdan deneyin |
| `http://127.0.0.1:8000/redoc` | **ReDoc** | Okumaya odaklı, yazdırılabilir referans |
| `http://127.0.0.1:8000/openapi.json` | **OpenAPI şeması** | İstemci kodu üretimi, Postman/Insomnia içe aktarma |

### 8.1 Swagger UI'da jetonla deneme

1. `POST /api/v1/auth/login` ucunu açın, **Try it out** deyin ve yönetici
   bilgileriyle çalıştırın.
2. Yanıttan `access_token` değerini kopyalayın.
3. Sayfanın sağ üstündeki **Authorize** düğmesine tıklayın.
4. Alana yalnızca jetonu yapıştırın (`HTTPBearer` şeması `Bearer` önekini kendisi
   ekler) ve **Authorize** deyin.
5. Artık korumalı uçları doğrudan deneyebilirsiniz. Yetkiniz yetmezse yanıt
   `403` ve `details.missing` içinde eksik izin kodu görünür.

### 8.2 Şemayı istemci üretimi için kullanma

```bash
# OpenAPI şemasını indir
curl -s http://127.0.0.1:8000/openapi.json -o openapi.json

# Örnek: TypeScript tipleri üret
npx openapi-typescript openapi.json -o src/api/schema.d.ts
```

### 8.3 Belge içindeki gruplama

Uçlar Swagger UI'da Türkçe etiketlerle gruplanır: *Kimlik Doğrulama*,
*Kullanıcılar*, *Öğrenciler*, *Veliler*, *Eğitmenler*, *Gruplar*, *Havuzlar*,
*Dersler*, *Yoklama*, *Üyelikler*, *Paketler*, *Finans*, *Performans*,
*Yarışmalar*, *İstatistikler*, *Raporlar*, *Yapay Zekâ*, *AI Developer Console*,
*CAIO*, *Yedekleme*, *Arama*, *Eğitim Merkezi*, *Sistem*.

---

## İlgili belgeler

- Güvenlik modeli, RBAC matrisi ve dağıtım kontrol listesi: [`docs/SECURITY.md`](SECURITY.md)
- Sürüm notları ve bilinen kısıtlamalar: [`CHANGELOG.md`](../CHANGELOG.md)
- Kaynak: `backend/app/api/v1/`, `backend/app/core/`, `backend/app/schemas/`
