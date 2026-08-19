# Veritabanı / Database

Bu belge Akıllı Yüzme Okulu Yönetim Sistemi'nin veri modelini anlatır: 55 tablonun
tamamı, gerçek sütun adları, ilişkiler, indeksler, enum değerleri, migration yönetimi
ve bakım işlemleri. Hedef kitle: veri katmanında değişiklik yapacak veya sorgu
yazacak geliştiriciler.

- **Kaynak:** `backend/app/models/*.py`, `backend/app/db/`, `backend/alembic/`
- **Sürüm:** 0.9.0

---

## 1. Genel Bakış

| Özellik | Değer |
|---|---|
| Motor | SQLite 3 (PostgreSQL'e geçişe hazır) |
| Tablo sayısı | **50** |
| ORM | SQLAlchemy 2.0 — `DeclarativeBase`, `Mapped[...]`, `mapped_column(...)` |
| Migration | Alembic (`render_as_batch=True`) |
| Veritabanı dosyası | `data/swimming_school.db` |
| Varsayılan URL | `sqlite:///./data/swimming_school.db` |
| Birincil anahtar | Tümü `INTEGER` otomatik artan (`IntPKMixin`) |
| Zaman damgaları | Çoğu tabloda `created_at` / `updated_at` (`TimestampMixin`) |
| Enum saklama | `StrEnum` → veritabanında **okunabilir metin** (`VARCHAR`) |

### Bağlantı ayarları

Her SQLite bağlantısında dört PRAGMA çalıştırılır (`backend/app/db/session.py`):

```python
@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()
```

| PRAGMA | Neden gerekli |
|---|---|
| `foreign_keys=ON` | **SQLite'ta yabancı anahtar zorlaması varsayılan olarak KAPALIDIR.** Bu satır olmadan `ON DELETE CASCADE` ve `RESTRICT` kuralları hiç çalışmaz, yetim kayıtlar oluşur. |
| `journal_mode=WAL` | Write-Ahead Logging: okuyucular yazarı, yazar okuyucuları bloklamaz. Rapor üretilirken yoklama alınabilir. |
| `synchronous=NORMAL` | WAL ile birlikte güvenli ve belirgin biçimde hızlı. (`FULL` gereksiz yavaş, `OFF` güvensiz.) |
| `busy_timeout=30000` | Kilit varsa hemen hata vermek yerine 30 saniye yeniden dener. |

Motor ayrıca SQLite için `check_same_thread=False` ve `timeout=30` ile kurulur;
FastAPI'nin senkron uç noktaları iş parçacığı havuzunda çalıştığı için bu gereklidir.

### Adlandırma kuralı

`backend/app/db/base.py` tüm indeks ve kısıtlamalara deterministik ad verir:

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

Bu kural **zorunludur**: SQLite'ta isimsiz kısıtlamalar `ALTER` edilemez ve Alembic
`--autogenerate` güvenilir bir fark üretemez.

### Ortak karışımlar (mixin)

| Mixin | Sağladığı sütunlar |
|---|---|
| `IntPKMixin` | `id INTEGER PRIMARY KEY AUTOINCREMENT` |
| `TimestampMixin` | `created_at`, `updated_at` (`DateTime(timezone=True)`, `server_default=now()`, `onupdate=now()`) |

`TimestampMixin` kullanmayan tablolar (`login_attempts`, `attendance_tokens`,
`audit_logs`, `notifications`, `backup_records`, `restore_records`, `ai_tasks`,
`ai_provider_health`, `caio_findings`, `system_events`, `cash_transactions`,
`water_quality_logs`, `holidays`, `student_guardians`, `instructor_availabilities`)
zamanı kendi alan adlarıyla tutar (`occurred_at`, `attempted_at`, `checked_at`,
`measured_at`, `started_at` gibi).

---

## 2. Şema Diyagramı

### Genel yerleşim

```
   ┌──────────────────────── KİMLİK ────────────────────────┐
   │   roles ──< user_roles >── users        login_attempts │
   └───────────────────────────┬────────────────────────────┘
                               │ (isteğe bağlı portal bağlantısı)
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
   ┌─────────┐           ┌──────────┐          ┌────────────┐
   │students │           │guardians │          │instructors │
   └────┬────┘           └────┬─────┘          └─────┬──────┘
        │   student_guardians │                      │ certificates
        └──────────◄──────────┘                      │ availabilities
        │                                            │ leaves
        │  groups ◄──────────────────────────────────┘
        │
        │        ┌─────────── TESİS ───────────┐
        │        │  pools ──< lanes            │
        │        │    ├──< pool_maintenances   │
        │        │    └──< water_quality_logs  │
        │        │  holidays                   │
        │        └──────────┬──────────────────┘
        │                   │
        │        ┌──────────▼──────── PROGRAM ─────────────┐
        │        │  lesson_series ──< lessons              │
        └────────┼──────< lesson_enrollments >─────────────┤
                 │              lessons ──< attendances    │
                 └─────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌──────────┐        ┌────────────┐        ┌──────────────┐
   │ TİCARİ   │        │   SPOR     │        │   SİSTEM     │
   │ packages │        │performance_│        │ audit_logs   │
   │  └<member│        │  records   │        │ notifications│
   │    ships │        │personal_   │        │ app_settings │
   │     └<fre│        │  bests     │        │ backup_/     │
   │      ezes│        │training_   │        │ restore_     │
   │ invoices │        │  plans     │        │  records     │
   │  └<payme │        │competitions│        │ ai_tasks     │
   │    nts   │        │ └<events   │        │ ai_provider_ │
   │ expenses │        │    └<entrie│        │  health      │
   │ discounts│        │      s     │        │ caio_findings│
   │ cash_    │        │club_records│        │ kpi_targets  │
   │ transact.│        │            │        │ training_    │
   └──────────┘        └────────────┘        │  progress    │
                                             │ report_templ.│
                                             │ system_events│
                                             └──────────────┘
```

### Çekirdek varlıklar (mermaid)

```mermaid
erDiagram
    users ||--o{ user_roles : "sahip"
    roles ||--o{ user_roles : "atanır"
    users ||--o| students : "portal"
    users ||--o| guardians : "portal"
    users ||--o| instructors : "portal"

    students }o--o| groups : "üye"
    students }o--o| instructors : "primary_instructor"
    students ||--o{ student_guardians : "veli bağı"
    guardians ||--o{ student_guardians : "öğrenci bağı"

    pools ||--o{ lanes : "kulvar"
    pools ||--o{ pool_maintenances : "bakım"
    pools ||--o{ water_quality_logs : "ölçüm"
    pools ||--o{ lessons : "ev sahibi"
    lanes ||--o{ lessons : "ayrılmış"

    lesson_series ||--o{ lessons : "üretir"
    instructors ||--o{ lessons : "verir"
    lessons ||--o{ lesson_enrollments : "kayıt"
    students ||--o{ lesson_enrollments : "kayıtlı"
    lessons ||--o{ attendances : "yoklama"
    students ||--o{ attendances : "devam"

    packages ||--o{ memberships : "satılır"
    students ||--o{ memberships : "sahip"
    memberships ||--o{ membership_freezes : "dondurma"
    memberships ||--o{ payments : "ödeme"
    invoices ||--o{ payments : "tahsilat"
    students ||--o{ invoices : "borç"

    students ||--o{ performance_records : "derece"
    students ||--o{ personal_bests : "rekor"
    students ||--o{ training_plans : "plan"
    competitions ||--o{ competition_events : "etkinlik"
    competition_events ||--o{ competition_entries : "katılım"
    students ||--o{ competition_entries : "yarışır"
```

---

## 3. Tablo Referansı

Sütun listelerinde `PK` birincil anahtar, `FK` yabancı anahtar, `UQ` tekil kısıt,
`IX` indeksli sütun anlamına gelir. `+ts` işareti tablonun `created_at` /
`updated_at` sütunlarını da taşıdığını gösterir.

---

### 3.1 Kimlik (4 tablo)

#### `roles` — Sistem rolü `+ts`
**Amaç:** 21 rolün tanımı; her rol bir izin listesi taşır.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `code` | VARCHAR(50) | UQ, IX — `system_admin`, `parent` … |
| `name_tr` | VARCHAR(120) | Türkçe ad |
| `name_en` | VARCHAR(120) | İngilizce ad |
| `description` | VARCHAR(400) | |
| `permissions` | JSON | İzin kodu listesi (`["student:read", ...]`) |
| `is_system` | BOOLEAN | `True` ise izinler her açılışta koddan yeniden yazılır |

**İlişkiler:** `users` ← `user_roles` (çoktan çoğa, `lazy="selectin"`).
**İndeksler:** `ix_roles_code` (unique).

#### `users` — Sisteme giriş yapan kullanıcı `+ts`
**Amaç:** Kimlik doğrulama, tercihler, hesap kilitleme.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `email` | VARCHAR(255) | UQ, IX |
| `hashed_password` | VARCHAR(255) | bcrypt (12 tur) |
| `full_name` | VARCHAR(200) | |
| `phone` | VARCHAR(30) | |
| `avatar_url` | VARCHAR(500) | |
| `language` | VARCHAR(5) | `tr` / `en`, varsayılan `tr` |
| `theme` | VARCHAR(10) | varsayılan `light` |
| `is_active` | BOOLEAN | `False` ise giriş reddedilir |
| `is_superuser` | BOOLEAN | Tüm izinlere sahip |
| `must_change_password` | BOOLEAN | İlk yöneticide `True` |
| `last_login_at` | DATETIME(tz) | |
| `failed_login_count` | INTEGER | Hesap kilitleme sayacı |
| `locked_until` | DATETIME(tz) | Kilit bitişi |
| `onboarding_completed` | BOOLEAN | Kurulum sihirbazı tamamlandı mı |
| `training_mode` | BOOLEAN | Demo veri üzerinde güvenli çalışma |

**İlişkiler:** `roles` (çoktan çoğa), `student` / `guardian` / `instructor`
(bire bir, isteğe bağlı portal bağlantısı).
**Türetilmiş özellikler:** `role_codes`, `permissions` (rollerin birleşimi),
`has_permission()`, `has_any_role()`.
**İndeksler:** `ix_users_email` (unique).

#### `user_roles` — Kullanıcı ↔ rol bağı
**Amaç:** Çoktan çoğa bağlantı tablosu (`Table` nesnesi, ORM sınıfı yok).

| Sütun | Tip | Not |
|---|---|---|
| `user_id` | INTEGER | PK + FK → `users.id` `ON DELETE CASCADE` |
| `role_id` | INTEGER | PK + FK → `roles.id` `ON DELETE CASCADE` |

#### `login_attempts` — Giriş denemesi
**Amaç:** Hız sınırlama ve güvenlik denetimi.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `email` | VARCHAR(255) | |
| `ip_address` | VARCHAR(64) | |
| `user_agent` | VARCHAR(300) | |
| `successful` | BOOLEAN | |
| `attempted_at` | DATETIME(tz) | IX |

**İndeksler:** `ix_login_attempts_email_time` (`email`, `attempted_at`) —
"son bir dakikada bu e-posta kaç kez denedi" sorgusu tek indeksle karşılanır.

---

### 3.2 Kişiler (4 + 4 tablo)

#### `groups` — Öğrenci grubu `+ts`
**Amaç:** Yaş/seviye bazlı sınıf tanımı (ör. "Yıldızlar – Başlangıç Çocuk").

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | VARCHAR(120) | IX |
| `description` | VARCHAR(400) | |
| `level` | VARCHAR(30) | `SwimLevel`, varsayılan `beginner` |
| `min_age` / `max_age` | INTEGER | |
| `color` | VARCHAR(20) | Takvim rengi, varsayılan `#0ea5e9` |
| `capacity` | INTEGER | varsayılan 12 |
| `is_active` | BOOLEAN | |
| `default_instructor_id` | INTEGER | FK → `instructors.id` `SET NULL` |

#### `students` — Öğrenci / sporcu `+ts`
**Amaç:** Merkezî kişi kaydı. Sağlık ve özel ihtiyaç alanları `student:read_sensitive`
izniyle korunur.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_number` | VARCHAR(30) | UQ, IX — `next_sequence_number()` üretir |
| `first_name` / `last_name` | VARCHAR(80) | |
| `birth_date` | DATE | |
| `gender` | VARCHAR(20) | `Gender`, varsayılan `unspecified` |
| `photo_url` | VARCHAR(500) | |
| `phone` | VARCHAR(30) | |
| `email` | VARCHAR(255) | IX |
| `address` | VARCHAR(400) | |
| `emergency_contact_name` | VARCHAR(160) | |
| `emergency_contact_phone` | VARCHAR(30) | |
| `swim_level` | VARCHAR(30) | `SwimLevel` |
| `status` | VARCHAR(20) | `StudentStatus`, IX |
| `registration_date` | DATE | IX |
| `left_date` | DATE | |
| `group_id` | INTEGER | FK → `groups.id` `SET NULL` |
| `primary_instructor_id` | INTEGER | FK → `instructors.id` `SET NULL` |
| `health_notes` | TEXT | **Hassas** |
| `special_needs` | TEXT | **Hassas** |
| `goals` | TEXT | |
| `notes` | TEXT | |
| `consent_given` | BOOLEAN | KVKK açık rıza |
| `consent_date` | DATE | |
| `is_demo` | BOOLEAN | IX — demo veri ayıklaması için |
| `user_id` | INTEGER | FK → `users.id` `SET NULL` (portal erişimi) |

**İlişkiler:** `guardians` (`StudentGuardian` üzerinden), `enrollments`,
`attendances`, `memberships`, `payments`, `performance_records`,
`competition_entries` — hepsi `cascade="all, delete-orphan"` (`payments` hariç).
**Türetilmiş:** `full_name`, `age`, `guardian_list`.
**İndeksler:** `ix_students_student_number` (unique), `ix_students_email`,
`ix_students_status`, `ix_students_registration_date`, `ix_students_is_demo`,
`ix_students_name` (`last_name`, `first_name`),
`ix_students_status_level` (`status`, `swim_level`).

#### `guardians` — Veli `+ts`
**Amaç:** Bir veli birden fazla öğrenciye bağlanabilir.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `first_name` / `last_name` | VARCHAR(80) | |
| `relationship_type` | VARCHAR(40) | varsayılan `parent` |
| `phone` | VARCHAR(30) | Zorunlu, IX |
| `secondary_phone` | VARCHAR(30) | |
| `email` | VARCHAR(255) | IX |
| `national_id_last4` | VARCHAR(4) | **Veri minimizasyonu** — TC kimlik tamamı saklanmaz |
| `address` | VARCHAR(400) | |
| `occupation` | VARCHAR(120) | |
| `notes` | TEXT | |
| `is_demo` | BOOLEAN | IX |
| `user_id` | INTEGER | FK → `users.id` `SET NULL` |

#### `student_guardians` — Öğrenci ↔ veli bağı
**Amaç:** Çoktan çoğa ilişki + rol bilgisi (kim alabilir, kim faturayı alır).

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_id` | INTEGER | FK → `students.id` `CASCADE` |
| `guardian_id` | INTEGER | FK → `guardians.id` `CASCADE` |
| `is_primary` | BOOLEAN | Birincil veli |
| `can_pickup` | BOOLEAN | Çocuğu teslim alabilir |
| `is_billing_contact` | BOOLEAN | Fatura muhatabı |

**İndeksler:** `ix_student_guardian_unique` (`student_id`, `guardian_id`) — **unique**,
aynı çift iki kez bağlanamaz.

#### `instructors` — Eğitmen / antrenör `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `employee_number` | VARCHAR(30) | UQ, IX |
| `first_name` / `last_name` | VARCHAR(80) | |
| `birth_date` | DATE | |
| `gender` | VARCHAR(20) | `Gender` |
| `phone` | VARCHAR(30) | |
| `email` | VARCHAR(255) | IX |
| `photo_url` | VARCHAR(500) | |
| `title` | VARCHAR(120) | ör. "Baş Antrenör" |
| `specialties` | JSON | Uzmanlık listesi |
| `hire_date` | DATE | |
| `is_active` | BOOLEAN | IX |
| `hourly_rate` | NUMERIC(10,2) | **Hassas** — `can_read_salary()` ile korunur |
| `monthly_salary` | NUMERIC(12,2) | **Hassas** |
| `max_weekly_hours` | INTEGER | varsayılan 40 |
| `bio` / `notes` | TEXT | |
| `is_demo` | BOOLEAN | IX |
| `user_id` | INTEGER | FK → `users.id` `SET NULL` |

**İlişkiler:** `students` (primary instructor), `lessons`, `certificates`,
`availabilities`, `leaves`.

#### `instructor_certificates` — Sertifika `+ts`
**Amaç:** TYF antrenörlük, cankurtaran, ilk yardım belgeleri ve geçerlilik takibi.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `instructor_id` | INTEGER | FK → `instructors.id` `CASCADE` |
| `name` | VARCHAR(200) | |
| `issuer` | VARCHAR(200) | |
| `issued_date` | DATE | |
| `expiry_date` | DATE | **IX** — süresi dolan sertifika taraması |
| `document_url` | VARCHAR(500) | |

**Türetilmiş:** `is_expired`.

#### `instructor_availabilities` — Haftalık müsaitlik

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `instructor_id` | INTEGER | FK → `instructors.id` `CASCADE` |
| `weekday` | INTEGER | **0 = Pazartesi … 6 = Pazar** |
| `start_time` | TIME | |
| `end_time` | TIME | |

#### `instructor_leaves` — İzin / devamsızlık `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `instructor_id` | INTEGER | FK → `instructors.id` `CASCADE` |
| `start_date` | DATE | IX |
| `end_date` | DATE | IX |
| `leave_type` | VARCHAR(40) | varsayılan `annual` |
| `reason` | VARCHAR(400) | |
| `approved` | BOOLEAN | |

Çakışma motoru bu tabloyu **uyarı** kaynağı olarak kullanır (hata değil).

---

### 3.3 Tesis (5 tablo)

#### `pools` — Havuz `+ts`
**Amaç:** Sistem birden fazla havuzu destekler.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | VARCHAR(120) | UQ, IX |
| `code` | VARCHAR(20) | |
| `location` | VARCHAR(200) | |
| `length_m` | NUMERIC(6,2) | varsayılan 25 |
| `width_m` | NUMERIC(6,2) | |
| `depth_min_m` / `depth_max_m` | NUMERIC(4,2) | |
| `lane_count` | INTEGER | varsayılan 6 |
| `capacity` | INTEGER | varsayılan 60 |
| `course_type` | VARCHAR(10) | `CourseType` — `short` (25 m) / `long` (50 m) |
| `opening_time` | TIME | varsayılan 07:00 |
| `closing_time` | TIME | varsayılan 22:00 |
| `status` | VARCHAR(20) | `PoolStatus`, IX |
| `water_temperature_c` | NUMERIC(4,1) | |
| `air_temperature_c` | NUMERIC(4,1) | |
| `is_indoor` / `is_heated` | BOOLEAN | |
| `notes` | TEXT | |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `operating_hours` (`"07:00-22:00"`).
Çalışma saatleri dışı planlama **uyarı** üretir.

#### `lanes` — Kulvar `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `pool_id` | INTEGER | FK → `pools.id` `CASCADE`, IX |
| `lane_number` | INTEGER | |
| `name` | VARCHAR(80) | Boşsa `"Kulvar {n}"` |
| `width_m` / `depth_m` | NUMERIC(4,2) | |
| `max_swimmers` | INTEGER | varsayılan 8 |
| `is_active` | BOOLEAN | |
| `purpose` | VARCHAR(80) | ör. "Eğitim", "Serbest" |
| `notes` | VARCHAR(300) | |

**İndeksler:** `ix_lane_pool_number` (`pool_id`, `lane_number`) — **unique**,
bir havuzda aynı kulvar numarası iki kez tanımlanamaz.

#### `pool_maintenances` — Bakım kaydı `+ts`
**Amaç:** Bakım süresince o havuza ders planlanamaz (**hata** üretir).

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `pool_id` | INTEGER | FK → `pools.id` `CASCADE`, IX |
| `start_at` | DATETIME(tz) | IX |
| `end_at` | DATETIME(tz) | IX |
| `maintenance_type` | VARCHAR(60) | varsayılan `routine` |
| `description` | TEXT | |
| `cost` | NUMERIC(12,2) | |
| `performed_by` | VARCHAR(160) | |
| `is_completed` | BOOLEAN | `False` olanlar çakışma taramasına girer |

#### `water_quality_logs` — Su kalitesi ölçümü

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `pool_id` | INTEGER | FK → `pools.id` `CASCADE`, IX |
| `measured_at` | DATETIME(tz) | IX |
| `ph` | NUMERIC(4,2) | |
| `chlorine_ppm` | NUMERIC(5,2) | |
| `temperature_c` | NUMERIC(4,1) | |
| `turbidity_ntu` | NUMERIC(5,2) | |
| `measured_by` | VARCHAR(160) | |
| `is_within_limits` | BOOLEAN | `False` ise bildirim üretilir |
| `notes` | VARCHAR(400) | |

#### `holidays` — Tatil / kapalı gün

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `date` | DATE | UQ, IX |
| `name` | VARCHAR(160) | |
| `is_closed` | BOOLEAN | `True` ise seri üretiminde atlanır, planlamada **uyarı** üretir |

---

### 3.4 Program (3 tablo)

#### `lesson_series` — Tekrarlanan ders tanımı `+ts`
**Amaç:** "Her Salı ve Perşembe 17:00–18:00" gibi bir kuralı saklar. Bu kural
`generate_series_dates()` ile somut `lessons` satırlarına dönüştürülür.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `title` | VARCHAR(160) | |
| `lesson_type` | VARCHAR(30) | `LessonType` |
| `group_id` | INTEGER | FK → `groups.id` `SET NULL` |
| `instructor_id` | INTEGER | FK → `instructors.id` `SET NULL` |
| `pool_id` | INTEGER | FK → `pools.id` `CASCADE`, zorunlu |
| `lane_id` | INTEGER | FK → `lanes.id` `SET NULL` |
| `weekdays` | JSON | `[0, 2]` = Pazartesi ve Çarşamba |
| `start_time` / `end_time` | TIME | |
| `start_date` / `end_date` | DATE | |
| `capacity` | INTEGER | varsayılan 10 |
| `color` | VARCHAR(20) | |
| `is_active` | BOOLEAN | |
| `notes` | TEXT | |

**İlişkiler:** `lessons` — `cascade="all, delete-orphan"`; seri silinince üretilen
dersler de silinir.

#### `lessons` — Somut ders oturumu `+ts`
**Amaç:** Sistemin operasyonel merkezi. Çakışma denetimi **yalnızca bu tablo**
üzerinde çalışır.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `title` | VARCHAR(160) | |
| `lesson_type` | VARCHAR(30) | `LessonType`, IX |
| `status` | VARCHAR(20) | `LessonStatus`, IX |
| `start_at` | DATETIME(tz) | IX |
| `end_at` | DATETIME(tz) | |
| `pool_id` | INTEGER | FK → `pools.id` `CASCADE`, zorunlu |
| `lane_id` | INTEGER | FK → `lanes.id` `SET NULL` |
| `instructor_id` | INTEGER | FK → `instructors.id` `SET NULL` |
| `group_id` | INTEGER | FK → `groups.id` `SET NULL` |
| `series_id` | INTEGER | FK → `lesson_series.id` `CASCADE`, IX |
| `capacity` | INTEGER | varsayılan 10 |
| `price` | NUMERIC(10,2) | |
| `color` | VARCHAR(20) | |
| `cancellation_reason` | VARCHAR(300) | |
| `notes` | TEXT | |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `duration_minutes`, `enrolled_count`, `occupancy_rate`.
**İndeksler (çakışma motorunun temeli):**

| İndeks | Sütunlar | Hangi sorgu |
|---|---|---|
| `ix_lessons_start_end` | `start_at`, `end_at` | Takvim aralığı taraması |
| `ix_lessons_instructor_time` | `instructor_id`, `start_at` | Eğitmen çakışması |
| `ix_lessons_lane_time` | `lane_id`, `start_at` | Kulvar çakışması |
| `ix_lessons_pool_time` | `pool_id`, `start_at` | Havuz doluluğu, kulvar planı |
| `ix_lessons_start_at` | `start_at` | Günlük liste |
| `ix_lessons_lesson_type`, `ix_lessons_status`, `ix_lessons_series_id` | tekil | Filtreleme |

**Not:** `attendances` ilişkisi `foreign_keys="Attendance.lesson_id"` ile açıkça
belirtilir — `attendances` tablosunda `lessons`'a iki yabancı anahtar vardır
(`lesson_id` ve `makeup_lesson_id`), SQLAlchemy hangisini kullanacağını bilemez.

#### `lesson_enrollments` — Derse kayıt `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `lesson_id` | INTEGER | FK → `lessons.id` `CASCADE`, IX |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `status` | VARCHAR(20) | `EnrollmentStatus` — `enrolled` / `waitlist` / `cancelled` |
| `membership_id` | INTEGER | FK → `memberships.id` `SET NULL` |
| `credit_consumed` | BOOLEAN | **Çift düşüm koruması** |
| `notes` | VARCHAR(400) | |

**İndeksler:** `ix_enrollment_unique` (`lesson_id`, `student_id`) — **unique**.

---

### 3.5 Operasyon (3 tablo)

#### `attendances` — Yoklama `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `lesson_id` | INTEGER | FK → `lessons.id` `CASCADE`, IX |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `status` | VARCHAR(20) | `AttendanceStatus`, IX |
| `method` | VARCHAR(20) | `AttendanceMethod` — `manual` / `qr` / `card` / `rfid` / `nfc` |
| `checked_in_at` | DATETIME(tz) | |
| `late_minutes` | INTEGER | |
| `excuse_reason` | VARCHAR(300) | |
| `notes` | TEXT | |
| `makeup_lesson_id` | INTEGER | FK → `lessons.id` `SET NULL` — telafi dersi bağı |
| `counts_toward_credit` | BOOLEAN | Ders hakkı düşülsün mü |
| `recorded_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `is_present` (`present`, `late` veya `makeup` ise `True`).
**İndeksler:** `ix_attendance_unique` (`lesson_id`, `student_id`) — **unique**;
`ix_attendance_student_status` (`student_id`, `status`) — devam oranı hesabı.

#### `attendance_tokens` — QR / kart tokeni

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `token` | VARCHAR(64) | UQ, IX |
| `lesson_id` | INTEGER | FK → `lessons.id` `CASCADE` |
| `expires_at` | DATETIME(tz) | |
| `used_count` | INTEGER | |
| `created_at` | DATETIME(tz) | Elle tanımlı (mixin değil) |

#### `student_cards` — Öğrenci kartı `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `card_code` | VARCHAR(80) | UQ, IX |
| `card_type` | VARCHAR(20) | varsayılan `qr` |
| `is_active` | BOOLEAN | |
| `issued_at` | DATETIME(tz) | |

---

### 3.6 Ticari (8 tablo)

#### `packages` — Satılabilir paket tanımı `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | VARCHAR(120) | UQ |
| `name_en` | VARCHAR(120) | |
| `package_type` | VARCHAR(30) | `PackageType` |
| `description` | TEXT | |
| `lesson_count` | INTEGER | `NULL` ⇒ sınırsız |
| `duration_days` | INTEGER | |
| `price` | NUMERIC(12,2) | Zorunlu |
| `currency` | VARCHAR(3) | varsayılan `TRY` |
| `max_freeze_days` | INTEGER | varsayılan 30 |
| `is_active` | BOOLEAN | |
| `color` | VARCHAR(20) | |

`init_db.py` dokuz varsayılan paket oluşturur (4/8/12 Ders, Aylık Sınırsız,
3 Aylık, 6 Aylık, Yıllık, Özel Ders 10'lu, Deneme Dersi).

#### `memberships` — Satın alınmış paket örneği `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `package_id` | INTEGER | FK → `packages.id` **`RESTRICT`** — kullanımdaki paket silinemez |
| `start_date` | DATE | |
| `end_date` | DATE | IX |
| `status` | VARCHAR(20) | `MembershipStatus`, IX |
| `total_credits` | INTEGER | `NULL` ⇒ sınırsız |
| `used_credits` | INTEGER | |
| `price_paid` | NUMERIC(12,2) | |
| `discount_amount` | NUMERIC(12,2) | |
| `discount_reason` | VARCHAR(200) | |
| `auto_renew` | BOOLEAN | |
| `cancelled_at` | DATE | |
| `cancellation_reason` | VARCHAR(300) | |
| `notes` | TEXT | |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `remaining_credits`, `days_remaining`, `is_expiring_soon`
(14 gün), `usage_rate`, `expiring_within(n)`.
**İndeksler:** `ix_membership_student_status` (`student_id`, `status`),
`ix_membership_end_date` (`end_date`) — süresi yaklaşan üyelik taraması.

#### `membership_freezes` — Dondurma `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `membership_id` | INTEGER | FK → `memberships.id` `CASCADE`, IX |
| `start_date` / `end_date` | DATE | |
| `reason` | VARCHAR(300) | |
| `approved_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |

**Türetilmiş:** `days` (uç günler dâhil).

#### `invoices` — Fatura / borç `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `invoice_number` | VARCHAR(40) | UQ, IX |
| `student_id` | INTEGER | FK → `students.id` `SET NULL`, IX |
| `membership_id` | INTEGER | FK → `memberships.id` `SET NULL` |
| `issue_date` | DATE | IX |
| `due_date` | DATE | IX |
| `subtotal` | NUMERIC(12,2) | |
| `discount_amount` | NUMERIC(12,2) | |
| `tax_amount` | NUMERIC(12,2) | |
| `total_amount` | NUMERIC(12,2) | |
| `paid_amount` | NUMERIC(12,2) | |
| `currency` | VARCHAR(3) | |
| `status` | VARCHAR(20) | `PaymentStatus`, IX |
| `description` | TEXT | |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `balance`, `is_overdue`, `days_overdue` (yaşlandırma raporu).
**İndeksler:** `ix_invoice_student_status` (`student_id`, `status`).

#### `payments` — Tahsilat `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `receipt_number` | VARCHAR(40) | UQ, IX |
| `student_id` | INTEGER | FK → `students.id` `SET NULL`, IX |
| `membership_id` | INTEGER | FK → `memberships.id` `SET NULL` |
| `invoice_id` | INTEGER | FK → `invoices.id` `SET NULL`, IX |
| `amount` | NUMERIC(12,2) | Zorunlu |
| `currency` | VARCHAR(3) | |
| `method` | VARCHAR(20) | `PaymentMethod` |
| `status` | VARCHAR(20) | `PaymentStatus`, IX |
| `payment_date` | DATE | IX |
| `reference` | VARCHAR(120) | POS / dekont numarası |
| `description` | VARCHAR(400) | |
| `refunded_amount` | NUMERIC(12,2) | |
| `refund_reason` | VARCHAR(300) | |
| `received_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `net_amount` (`amount − refunded_amount`).
**İndeksler:** `ix_payment_date_method` (`payment_date`, `method`) — kasa/gün sonu;
`ix_payment_student_date` (`student_id`, `payment_date`) — öğrenci ödeme geçmişi.

#### `expenses` — Gider `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `title` | VARCHAR(200) | |
| `category` | VARCHAR(30) | `ExpenseCategory`, IX |
| `amount` | NUMERIC(12,2) | |
| `currency` | VARCHAR(3) | |
| `expense_date` | DATE | IX |
| `method` | VARCHAR(20) | `PaymentMethod`, varsayılan `transfer` |
| `vendor` | VARCHAR(200) | |
| `invoice_reference` | VARCHAR(120) | |
| `description` | TEXT | |
| `is_recurring` | BOOLEAN | |
| `created_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `is_demo` | BOOLEAN | |

**İndeksler:** `ix_expense_date_category` (`expense_date`, `category`) — kâr/zarar raporu.

#### `discounts` — İndirim / kampanya `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `code` | VARCHAR(40) | UQ, IX |
| `name` | VARCHAR(160) | |
| `description` | TEXT | |
| `percentage` | NUMERIC(5,2) | |
| `fixed_amount` | NUMERIC(12,2) | |
| `valid_from` / `valid_until` | DATE | |
| `max_uses` | INTEGER | `NULL` ⇒ sınırsız |
| `used_count` | INTEGER | |
| `is_active` | BOOLEAN | |

**Türetilmiş:** `is_valid_now` (aktif + tarih aralığında + kullanım hakkı var).

#### `cash_transactions` — Kasa hareketi
**Amaç:** Nakit/banka/POS bakiyesini izlemek için birleşik defter.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `direction` | VARCHAR(10) | `TransactionDirection` — `income` / `expense`, IX |
| `amount` | NUMERIC(12,2) | |
| `method` | VARCHAR(20) | `PaymentMethod` |
| `occurred_at` | DATETIME(tz) | IX |
| `description` | VARCHAR(400) | |
| `payment_id` | INTEGER | FK → `payments.id` `SET NULL` |
| `expense_id` | INTEGER | FK → `expenses.id` `SET NULL` |

---

### 3.7 Spor (7 tablo)

#### `performance_records` — Yüzme derecesi `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `instructor_id` | INTEGER | FK → `instructors.id` `SET NULL` |
| `lesson_id` | INTEGER | FK → `lessons.id` `SET NULL` |
| `stroke` | VARCHAR(20) | `Stroke`, IX |
| `distance_m` | INTEGER | IX |
| `course_type` | VARCHAR(10) | `CourseType` |
| `time_seconds` | NUMERIC(8,2) | Derece, saniye (ör. `32.45`) |
| `splits` | JSON | Her 25/50 m için ara dereceler |
| `stroke_rate` | NUMERIC(6,2) | Vuruş/dakika |
| `stroke_count` | INTEGER | Toplam kulaç |
| `reaction_time` | NUMERIC(5,3) | Çıkış reaksiyonu (sn) |
| `turn_time` | NUMERIC(5,2) | Dönüş süresi (sn) |
| `recorded_date` | DATE | IX |
| `is_personal_best` | BOOLEAN | |
| `is_competition` | BOOLEAN | |
| `heart_rate_avg` | INTEGER | |
| `perceived_effort` | INTEGER | 1–10 RPE |
| `notes` | TEXT | |
| `is_demo` | BOOLEAN | |

**Türetilmiş:** `event_name`, `pace_per_100m`, `speed_ms`.
**İndeksler:** `ix_perf_student_stroke_distance` (`student_id`, `stroke`, `distance_m`) —
etkinlik bazlı gelişim eğrisi; `ix_perf_student_date` (`student_id`, `recorded_date`) —
zaman serisi analizi.

#### `personal_bests` — Kişisel rekor `+ts`
**Amaç:** En iyi derecenin materyalize (önceden hesaplanmış) kopyası — her sorguda
tüm geçmişi taramamak için.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `stroke` | VARCHAR(20) | |
| `distance_m` | INTEGER | |
| `course_type` | VARCHAR(10) | |
| `time_seconds` | NUMERIC(8,2) | |
| `achieved_date` | DATE | |
| `performance_record_id` | INTEGER | FK → `performance_records.id` `SET NULL` |

**İndeksler:** `ix_pb_unique` (`student_id`, `stroke`, `distance_m`, `course_type`) —
**unique**; bir sporcunun bir etkinlikte tek rekoru olur.

#### `training_plans` — Antrenman planı `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `instructor_id` | INTEGER | FK → `instructors.id` `SET NULL` |
| `title` | VARCHAR(200) | |
| `start_date` / `end_date` | DATE | |
| `focus_areas` | JSON | |
| `weekly_sessions` | JSON | |
| `goals` / `notes` | TEXT | |
| `ai_generated` | BOOLEAN | **Şeffaflık** — AI ürettiyse işaretlenir |
| `ai_provider` | VARCHAR(40) | |
| `ai_model` | VARCHAR(120) | |
| `approved_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `is_approved` | BOOLEAN | AI planı insan onayı olmadan uygulanmaz |

#### `competitions` — Yarışma `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | VARCHAR(200) | IX |
| `location` | VARCHAR(200) | |
| `organizer` | VARCHAR(200) | |
| `level` | VARCHAR(20) | `CompetitionLevel` |
| `course_type` | VARCHAR(10) | `CourseType` |
| `start_date` | DATE | IX |
| `end_date` | DATE | |
| `registration_deadline` | DATE | |
| `description` | TEXT | |
| `is_completed` | BOOLEAN | |
| `is_demo` | BOOLEAN | |

#### `competition_events` — Yarışma etkinliği `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `competition_id` | INTEGER | FK → `competitions.id` `CASCADE`, IX |
| `stroke` | VARCHAR(20) | |
| `distance_m` | INTEGER | |
| `gender_category` | VARCHAR(20) | varsayılan `mixed` |
| `age_category` | VARCHAR(60) | ör. "12-13" |
| `event_order` | INTEGER | |
| `scheduled_date` | DATE | |

**Türetilmiş:** `name` (`"50 m freestyle"`).

#### `competition_entries` — Katılım ve sonuç `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `event_id` | INTEGER | FK → `competition_events.id` `CASCADE`, IX |
| `student_id` | INTEGER | FK → `students.id` `CASCADE`, IX |
| `seed_time_seconds` | NUMERIC(8,2) | Seri/kulvar dağıtımının girdisi |
| `heat_number` | INTEGER | Seri numarası |
| `lane_number` | INTEGER | |
| `result_time_seconds` | NUMERIC(8,2) | |
| `rank` | INTEGER | |
| `medal` | VARCHAR(20) | `gold` / `silver` / `bronze` |
| `is_personal_best` | BOOLEAN | |
| `is_club_record` | BOOLEAN | |
| `is_disqualified` | BOOLEAN | |
| `disqualification_reason` | VARCHAR(200) | |
| `notes` | TEXT | |

**Türetilmiş:** `improvement_seconds` (negatif = daha hızlı).
**İndeksler:** `ix_entry_unique` (`event_id`, `student_id`) — **unique**.

#### `club_records` — Kulüp rekoru `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `stroke` | VARCHAR(20) | |
| `distance_m` | INTEGER | |
| `course_type` | VARCHAR(10) | |
| `gender_category` | VARCHAR(20) | varsayılan `mixed` |
| `age_category` | VARCHAR(60) | varsayılan `open` |
| `student_id` | INTEGER | FK → `students.id` `SET NULL` |
| `holder_name` | VARCHAR(200) | Öğrenci silinse de rekor sahibi adı kalır |
| `time_seconds` | NUMERIC(8,2) | |
| `achieved_date` | DATE | |
| `competition_name` | VARCHAR(200) | |

**İndeksler:** `ix_club_record_unique` (`stroke`, `distance_m`, `course_type`,
`gender_category`, `age_category`) — **unique**.

---

### 3.8 Sistem (12 tablo)

#### `audit_logs` — Denetim kaydı
**Amaç:** Kim, ne zaman, hangi kaydı, nasıl değiştirdi.

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `user_email` | VARCHAR(255) | Kullanıcı silinse de kim olduğu kalır |
| `action` | VARCHAR(60) | `create` / `update` / `delete` / `login` …, IX |
| `entity_type` | VARCHAR(60) | ör. `Lesson` |
| `entity_id` | VARCHAR(40) | |
| `summary` | VARCHAR(400) | |
| `changes` | JSON | `{alan: {"from": x, "to": y}}` — **parolalar `***`** |
| `ip_address` | VARCHAR(64) | |
| `occurred_at` | DATETIME(tz) | IX |

**İndeksler:** `ix_audit_entity` (`entity_type`, `entity_id`) — "bu kaydın geçmişi";
`ix_audit_user_time` (`user_id`, `occurred_at`) — "bu kullanıcı ne yaptı".

#### `notifications` — Kullanıcı bildirimi

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `user_id` | INTEGER | FK → `users.id` `CASCADE`, IX |
| `notification_type` | VARCHAR(40) | `NotificationType`, IX |
| `severity` | VARCHAR(20) | `NotificationSeverity` |
| `title_tr` / `title_en` | VARCHAR(200) | İki dilli |
| `body_tr` / `body_en` | TEXT | İki dilli |
| `link` | VARCHAR(300) | Arayüzdeki hedef |
| `entity_type` / `entity_id` | VARCHAR | İlgili kayıt |
| `is_read` | BOOLEAN | |
| `read_at` | DATETIME(tz) | |
| `created_at` | DATETIME(tz) | IX |

**İndeksler:** `ix_notification_user_read` (`user_id`, `is_read`) — okunmamış sayacı.

#### `app_settings` — Anahtar-değer ayar `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `key` | VARCHAR(120) | UQ, IX |
| `value` | JSON | Sözlük, liste veya skaler |
| `category` | VARCHAR(60) | IX — `general` / `operations` / `finance` / `ai` / `backup` / `developer` |
| `description` | VARCHAR(400) | |
| `is_secret` | BOOLEAN | |
| `updated_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |

Varsayılan anahtarlar (`init_db.py`): `organization`, `attendance`, `membership`,
`finance`, `developer`, `backup`, `ai_runtime`. **API anahtarları burada değil,
`.env` dosyasında tutulur.**

#### `backup_records` — Yedek kaydı

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `backup_id` | VARCHAR(60) | UQ, IX |
| `backup_type` | VARCHAR(20) | `BackupType`, IX |
| `status` | VARCHAR(20) | `BackupStatus`, IX |
| `file_path` | VARCHAR(600) | |
| `file_name` | VARCHAR(300) | |
| `size_bytes` | INTEGER | |
| `checksum_sha256` | VARCHAR(64) | Bütünlük özeti |
| `manifest` | JSON | `backup_manifest.json` içeriği |
| `app_version` | VARCHAR(30) | |
| `db_revision` | VARCHAR(60) | Alembic revizyonu — uyumluluk kontrolü |
| `record_counts` | JSON | Yedek anındaki kayıt sayıları |
| `is_protected` | BOOLEAN | Saklama politikası bunu silmez |
| `verified_at` | DATETIME(tz) | |
| `verification_message` | VARCHAR(400) | |
| `error_message` | TEXT | |
| `created_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `created_at` | DATETIME(tz) | IX |

**Türetilmiş:** `size_mb`.

#### `restore_records` — Geri yükleme kaydı

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `backup_id` | VARCHAR(60) | IX |
| `safety_backup_id` | VARCHAR(60) | Geri yükleme öncesi alınan güvenlik yedeği |
| `status` | VARCHAR(20) | varsayılan `pending` |
| `message` | TEXT | |
| `performed_by_user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `started_at` | DATETIME(tz) | |
| `finished_at` | DATETIME(tz) | |

#### `ai_tasks` — AI görev kaydı

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `kind` | VARCHAR(30) | `AITaskKind`, IX |
| `status` | VARCHAR(20) | `AITaskStatus`, IX |
| `title` | VARCHAR(300) | |
| `provider` | VARCHAR(40) | IX |
| `model` | VARCHAR(160) | |
| `prompt_preview` | TEXT | **Yalnızca `AI_LOG_PROMPTS=true` iken doldurulur** |
| `result_preview` | TEXT | |
| `error_message` | TEXT | |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | INTEGER | |
| `duration_ms` | INTEGER | |
| `fallback_used` | BOOLEAN | Yedek sağlayıcıya düşüldü mü |
| `attempted_providers` | JSON | Denenen sağlayıcı sırası |
| `file_changes` | JSON | AI Developer Console yamaları |
| `test_result` | JSON | Yama sonrası test çıktısı |
| `user_id` | INTEGER | FK → `users.id` `SET NULL` |
| `started_at` | DATETIME(tz) | IX |
| `finished_at` | DATETIME(tz) | |

**İndeksler:** `ix_ai_task_kind_status` (`kind`, `status`).

#### `ai_provider_health` — Sağlayıcı sağlık geçmişi

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `provider` | VARCHAR(40) | IX |
| `is_available` | BOOLEAN | |
| `latency_ms` | INTEGER | |
| `model_count` | INTEGER | |
| `endpoint` | VARCHAR(300) | |
| `error_message` | VARCHAR(600) | |
| `checked_at` | DATETIME(tz) | IX |

#### `caio_findings` — CAIO bulgusu

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `category` | VARCHAR(60) | IX — log / güvenlik / test / teknik borç / veri kalitesi … |
| `severity` | VARCHAR(20) | IX, varsayılan `info` |
| `title` | VARCHAR(300) | |
| `description` | TEXT | |
| `recommendation` | TEXT | |
| `evidence` | JSON | Bulgunun dayanağı |
| `source` | VARCHAR(40) | varsayılan `analysis` |
| `status` | VARCHAR(20) | IX, varsayılan `open` |
| `is_ai_generated` | BOOLEAN | Kural motoru mu, AI mı üretti |
| `ai_provider` | VARCHAR(40) | |
| `created_at` | DATETIME(tz) | IX |
| `resolved_at` | DATETIME(tz) | |

#### `kpi_targets` — KPI hedefi `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `kpi_key` | VARCHAR(80) | UQ, IX |
| `target_value` | FLOAT | |
| `unit` | VARCHAR(20) | varsayılan `percent` |
| `period` | VARCHAR(20) | varsayılan `monthly` |
| `is_active` | BOOLEAN | |
| `notes` | VARCHAR(400) | |

Varsayılan hedefler: `attendance_rate` 90, `pool_occupancy` 80,
`collection_rate` 95, `student_retention` 85, `lane_occupancy` 75.

#### `training_progress` — Eğitim Merkezi ilerlemesi `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `user_id` | INTEGER | FK → `users.id` `CASCADE`, IX |
| `tutorial_id` | VARCHAR(80) | |
| `status` | VARCHAR(20) | `TrainingStatus` |
| `current_step` | INTEGER | |
| `total_steps` | INTEGER | |
| `completed_at` | DATETIME(tz) | |

**Türetilmiş:** `progress_percent`.
**İndeksler:** `ix_training_user_tutorial` (`user_id`, `tutorial_id`) — **unique**.

#### `report_templates` — Kayıtlı rapor şablonu `+ts`

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `name` | VARCHAR(200) | |
| `report_key` | VARCHAR(80) | IX — `REPORT_INDEX` anahtarı |
| `filters` | JSON | Report Builder filtreleri |
| `description` | VARCHAR(400) | |
| `is_shared` | BOOLEAN | Diğer kullanıcılar görebilir mi |
| `owner_user_id` | INTEGER | FK → `users.id` `SET NULL` |

#### `system_events` — Uygulama olayı

| Sütun | Tip | Not |
|---|---|---|
| `id` | INTEGER | PK |
| `event_type` | VARCHAR(60) | IX — başlangıç, migration, yedek … |
| `severity` | VARCHAR(20) | varsayılan `info` |
| `message` | VARCHAR(600) | |
| `details` | JSON | Hassas alanlar maskelenir |
| `occurred_at` | DATETIME(tz) | IX |

---

## 4. Enum Değerleri

Tümü `StrEnum`'dur (`backend/app/models/enums.py`): veritabanında **okunabilir metin**
olarak saklanır, JSON'a doğrudan serileşir, i18n etiketleri `ENUM_LABELS` sözlüğünde
ayrı tutulur. Etiket almak için `label(group, value, lang)` kullanılır.

| Enum | Değerler | Kullanıldığı sütunlar |
|---|---|---|
| `Gender` | `female`, `male`, `unspecified` | `students.gender`, `instructors.gender` |
| `SwimLevel` | `beginner`, `elementary`, `intermediate`, `advanced`, `competitive`, `elite` | `students.swim_level`, `groups.level` |
| `StudentStatus` | `active`, `passive`, `trial`, `frozen`, `left` | `students.status` |
| `LessonType` | `group`, `private`, `kids`, `baby`, `adult`, `beginner`, `intermediate`, `advanced`, `competition_team`, `adaptive`, `conditioning`, `trial`, `makeup` | `lessons.lesson_type`, `lesson_series.lesson_type` |
| `LessonStatus` | `scheduled`, `in_progress`, `completed`, `cancelled`, `postponed` | `lessons.status` |
| `EnrollmentStatus` | `enrolled`, `waitlist`, `cancelled` | `lesson_enrollments.status` |
| `AttendanceStatus` | `present`, `absent`, `late`, `excused`, `cancelled`, `makeup` | `attendances.status` |
| `AttendanceMethod` | `manual`, `qr`, `card`, `rfid`, `nfc` | `attendances.method` |
| `PackageType` | `lesson_pack`, `monthly`, `quarterly`, `biannual`, `annual`, `private_pack`, `trial` | `packages.package_type` |
| `MembershipStatus` | `active`, `expired`, `frozen`, `cancelled`, `pending` | `memberships.status` |
| `PaymentMethod` | `cash`, `card`, `transfer`, `online`, `other` | `payments.method`, `expenses.method`, `cash_transactions.method` |
| `PaymentStatus` | `paid`, `pending`, `partial`, `overdue`, `refunded`, `cancelled` | `payments.status`, `invoices.status` |
| `TransactionDirection` | `income`, `expense` | `cash_transactions.direction` |
| `ExpenseCategory` | `salary`, `rent`, `utilities`, `chemicals`, `maintenance`, `equipment`, `marketing`, `tax`, `insurance`, `other` | `expenses.category` |
| `Stroke` | `freestyle`, `backstroke`, `breaststroke`, `butterfly`, `medley` | `performance_records.stroke`, `personal_bests.stroke`, `competition_events.stroke`, `club_records.stroke` |
| `CourseType` | `short` (25 m), `long` (50 m) | `pools.course_type`, `performance_records.course_type`, `competitions.course_type`, `personal_bests.course_type`, `club_records.course_type` |
| `PoolStatus` | `operational`, `maintenance`, `closed` | `pools.status` |
| `CompetitionLevel` | `club`, `local`, `regional`, `national`, `international` | `competitions.level` |
| `NotificationType` | `membership_expiring`, `payment_overdue`, `lesson_cancelled`, `instructor_leave`, `pool_maintenance`, `performance_drop`, `competition_upcoming`, `ai_report_ready`, `backup_result`, `system`, `trial_lesson`, `new_registration` | `notifications.notification_type` |
| `NotificationSeverity` | `info`, `success`, `warning`, `error` | `notifications.severity` |
| `AITaskStatus` | `pending`, `running`, `success`, `failed`, `cancelled` | `ai_tasks.status` |
| `AITaskKind` | `analysis`, `chat`, `developer`, `caio`, `report`, `health_check` | `ai_tasks.kind` |
| `BackupType` | `full`, `incremental`, `manual`, `scheduled`, `pre_update`, `pre_migration`, `safety` | `backup_records.backup_type` |
| `BackupStatus` | `creating`, `completed`, `failed`, `verified`, `corrupted` | `backup_records.status` |
| `TrainingStatus` | `not_started`, `in_progress`, `completed` | `training_progress.status` |

### Yerelleştirilmiş etiketler

`ENUM_LABELS` sözlüğü şu gruplar için TR/EN etiket taşır: `gender`, `swim_level`,
`student_status`, `lesson_type`, `attendance_status`, `stroke`, `payment_method`,
`payment_status`, `membership_status`, `pool_status`.

```python
from app.models.enums import label

label("stroke", "breaststroke", "tr")   # "Kurbağalama"
label("stroke", "breaststroke", "en")   # "Breaststroke"
label("payment_status", "overdue", "tr")  # "Gecikmiş"
```

Sözlükte bulunmayan bir değer istenirse ham değer döner — hiçbir zaman istisna
fırlatmaz.

---

## 5. Migration Yönetimi

Alembic yapılandırması: `backend/alembic.ini`, ortam betiği `backend/alembic/env.py`,
revizyonlar `backend/alembic/versions/`.

Mevcut temel revizyon: `20260815_1529_0ca413b128ea_initial_schema.py`
(55 tablonun tamamını oluşturur).

### Temel komutlar

Tüm komutlar `backend/` dizininden çalıştırılır:

```powershell
cd C:\SwimmingSchool\backend

# Mevcut revizyonu göster
..\.venv\Scripts\python.exe -m alembic current

# Geçmişi listele
..\.venv\Scripts\python.exe -m alembic history --verbose

# Model değişikliğinden yeni revizyon üret
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "add equipment table"

# En son revizyona yükselt
..\.venv\Scripts\python.exe -m alembic upgrade head

# Bir adım geri al
..\.venv\Scripts\python.exe -m alembic downgrade -1

# Belirli bir revizyona dön
..\.venv\Scripts\python.exe -m alembic downgrade 0ca413b128ea

# Modeller ile veritabanı arasında fark var mı (CI kontrolü)
..\.venv\Scripts\python.exe -m alembic check
```

`START_SWIMMING_SCHOOL.bat` her açılışta `alembic upgrade head` çalıştırır;
kullanıcı bu komutları elle girmek zorunda değildir.

### Veritabanı URL'i nereden gelir

`alembic.ini` içinde **sır yoktur**. `env.py` uygulama ayarlarından okur:

```python
from app.core.config import settings
from app.models import Base   # tüm modelleri metadata'ya kaydeder

config = context.config
config.set_main_option("sqlalchemy.url", settings.resolved_database_url())
target_metadata = Base.metadata
```

`from app.models import Base` satırı kritiktir: `backend/app/models/__init__.py`
tüm model modüllerini import ettiği için `Base.metadata` 55 tablonun tamamını görür.
**Yeni bir model dosyası eklerseniz mutlaka `__init__.py` içine import edin**, aksi
halde `--autogenerate` o tabloyu görmez (veya "silinmiş" sanıp `drop_table` üretir).

### `render_as_batch` neden zorunlu

```python
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    render_as_batch=True,   # SQLite ALTER desteği için şart
    compare_type=True,
)
```

SQLite `ALTER TABLE` komutunu çok sınırlı destekler: sütun ekleyebilir ve tabloyu
yeniden adlandırabilir, ancak **sütun silemez, sütun tipini değiştiremez, kısıtlama
ekleyip kaldıramaz**. Batch modu bu kısıtı şöyle aşar:

```
1. Geçici tablo oluştur (yeni şema ile)
2. Eski tablodan veriyi kopyala
3. Eski tabloyu düşür
4. Geçici tabloyu eski adla yeniden adlandır
5. İndeksleri yeniden oluştur
```

Bu işlem yalnızca kısıtlamaların **adı varsa** güvenlidir — bu yüzden
`NAMING_CONVENTION` (bkz. bölüm 1) zorunludur. `compare_type=True` ise sütun tipi
değişikliklerinin de fark listesine girmesini sağlar.

### Autogenerate kontrol listesi

`--autogenerate` bir başlangıç noktasıdır, son söz değildir. Üretilen dosyayı
gözden geçirirken:

| Kontrol | Neden |
|---|---|
| `drop_table` / `drop_column` var mı | Modeli `__init__.py`'ye eklemeyi unutmuş olabilirsiniz — **veri kaybı riski** |
| `downgrade()` doğru mu | Geri alma yolu her zaman çalışır durumda olmalı |
| Sunucu tarafı varsayılan | Alembic `default=` (Python tarafı) değerlerini görmez; gerekiyorsa `server_default` elle eklenir |
| Veri taşıma gerekiyor mu | Sütun bölme/birleştirme durumunda `op.execute(...)` ile veri taşıyın |
| `NOT NULL` eklenen sütun | Mevcut satırlar için önce varsayılan doldurun, sonra `NOT NULL` yapın |

### Üretimde migration öncesi yedek

`BackupType.PRE_MIGRATION` tipi tam bu senaryo içindir. Şema değiştiren bir
sürüm uygulanmadan önce yedek alın:

```powershell
# Uygulama üzerinden: Ayarlar → Yedekleme → Yedek Al (tip: pre_migration)
# veya API ile:
#   POST /api/v1/backup  { "backup_type": "pre_migration" }
```

---

## 6. İndeks Stratejisi

İndeksler rastgele değil, **gerçekte çalışan sorgulara** göre eklenmiştir.

### Çakışma sorguları (en kritik)

Çakışma motoru her ders kaydı/güncellemesinde 3–5 sorgu çalıştırır. Sorgu deseni:

```sql
SELECT * FROM lessons
WHERE instructor_id = ?
  AND start_at < ?            -- yeni dersin bitişi
  AND ? < end_at              -- yeni dersin başlangıcı
  AND status NOT IN ('cancelled', 'postponed');
```

| İndeks | Sütunlar | Karşıladığı sorgu |
|---|---|---|
| `ix_lessons_instructor_time` | `instructor_id`, `start_at` | Eğitmen çakışması — önce eşitlik, sonra aralık |
| `ix_lessons_lane_time` | `lane_id`, `start_at` | Kulvar çakışması + boş kulvar bulma |
| `ix_lessons_pool_time` | `pool_id`, `start_at` | Havuz doluluğu, kulvar planı, `suggest_slot()` |
| `ix_lessons_start_end` | `start_at`, `end_at` | Takvim aralığı, `detect_all_conflicts()` |

Sütun sırası bilinçlidir: **eşitlik koşulu önce, aralık koşulu sonra**. Ters sırada
(`start_at`, `instructor_id`) indeks yalnızca aralık kısmını kullanabilirdi.

`suggest_slot()` bir gün için onlarca zaman dilimini denediğinden bu indeksler
performansın belirleyicisidir.

### Tarih aralığı sorguları

Neredeyse her rapor ve istatistik "şu tarih ile bu tarih arasında" sorar:

| İndeks | Tablo | Kullanım |
|---|---|---|
| `ix_payment_date_method` (`payment_date`, `method`) | `payments` | Gün sonu kasa, ödeme yöntemi kırılımı |
| `ix_payment_student_date` (`student_id`, `payment_date`) | `payments` | Öğrenci ödeme geçmişi |
| `ix_expense_date_category` (`expense_date`, `category`) | `expenses` | Kâr/zarar, kategori dağılımı |
| `ix_perf_student_date` (`student_id`, `recorded_date`) | `performance_records` | Gelişim eğrisi, eğilim eğimi |
| `ix_membership_end_date` (`end_date`) | `memberships` | Süresi yaklaşan üyelik taraması |
| `ix_invoices_due_date`, `ix_invoices_issue_date` | `invoices` | Yaşlandırma raporu |
| `ix_instructor_certificates_expiry_date` | `instructor_certificates` | Süresi dolan sertifika uyarısı |
| `ix_audit_user_time` (`user_id`, `occurred_at`) | `audit_logs` | Kullanıcı etkinlik geçmişi |
| `ix_login_attempts_email_time` (`email`, `attempted_at`) | `login_attempts` | Hız sınırlama penceresi |

### Durum filtreleri

Listeleme ekranları neredeyse her zaman duruma göre filtreler:

| İndeks | Kullanım |
|---|---|
| `ix_students_status_level` (`status`, `swim_level`) | "Aktif + orta seviye öğrenciler" |
| `ix_membership_student_status` (`student_id`, `status`) | Öğrencinin aktif üyeliği |
| `ix_invoice_student_status` (`student_id`, `status`) | Öğrencinin açık borcu |
| `ix_attendance_student_status` (`student_id`, `status`) | Devam oranı hesabı |
| `ix_ai_task_kind_status` (`kind`, `status`) | AI görev paneli |
| `ix_notification_user_read` (`user_id`, `is_read`) | Okunmamış bildirim sayacı |

### Arama indeksleri

| İndeks | Kullanım |
|---|---|
| `ix_students_name` (`last_name`, `first_name`) | Alfabetik listeleme ve isim araması |
| `ix_students_student_number`, `ix_instructors_employee_number` | Numara ile hızlı erişim |
| `ix_students_email`, `ix_guardians_email`, `ix_guardians_phone` | Global arama (`/api/v1/search`) |

**Sınırlama:** `apply_search()` `LIKE '%terim%'` kalıbı kullanır; öndeki joker
karakter nedeniyle bu indeksler tam metin araması için devreye giremez. Veri hacmi
büyürse SQLite FTS5 sanal tablosu değerlendirilmelidir.

### Tekillik + indeks

Bazı indeksler hem performans hem **veri bütünlüğü** amaçlıdır:

| İndeks | Engellediği durum |
|---|---|
| `ix_enrollment_unique` (`lesson_id`, `student_id`) | Aynı öğrenci aynı derse iki kez kaydedilemez |
| `ix_attendance_unique` (`lesson_id`, `student_id`) | Bir derste iki yoklama satırı olamaz |
| `ix_student_guardian_unique` (`student_id`, `guardian_id`) | Aynı veli-öğrenci bağı tekrarlanamaz |
| `ix_lane_pool_number` (`pool_id`, `lane_number`) | Bir havuzda aynı kulvar numarası iki kez tanımlanamaz |
| `ix_pb_unique` (`student_id`, `stroke`, `distance_m`, `course_type`) | Bir etkinlikte tek kişisel rekor |
| `ix_entry_unique` (`event_id`, `student_id`) | Aynı sporcu aynı etkinliğe iki kez kaydedilemez |
| `ix_club_record_unique` (5 sütun) | Her kategoride tek kulüp rekoru |
| `ix_training_user_tutorial` (`user_id`, `tutorial_id`) | Tek ilerleme kaydı |

---

## 7. Veri Bütünlüğü

### Yabancı anahtar davranışları

`ON DELETE` kuralları veri kaybı riski ile yetim kayıt riski arasında bilinçli bir
denge kurar.

| Davranış | Nerede | Gerekçe |
|---|---|---|
| **CASCADE** | `lanes → pools`, `pool_maintenances → pools`, `water_quality_logs → pools`, `lesson_enrollments → lessons/students`, `attendances → lessons/students`, `membership_freezes → memberships`, `memberships → students`, `student_guardians → students/guardians`, `instructor_certificates/availabilities/leaves → instructors`, `competition_events → competitions`, `competition_entries → events/students`, `performance_records → students`, `personal_bests → students`, `training_plans → students`, `training_progress → users`, `notifications → users`, `user_roles → users/roles`, `lessons → lesson_series`, `attendance_tokens → lessons`, `student_cards → students` | Alt kayıt üst kayıt olmadan **anlamsızdır**. Havuz silinince kulvarları da gider. |
| **SET NULL** | `students.group_id`, `students.primary_instructor_id`, `lessons.instructor_id`, `lessons.lane_id`, `lessons.group_id`, `payments.student_id`, `invoices.student_id`, `expenses.created_by_user_id`, `attendances.recorded_by_user_id`, `attendances.makeup_lesson_id`, `club_records.student_id`, tüm `*_user_id` alanları | Alt kayıt üst kayıt olmadan da **anlamlıdır**. Eğitmen işten ayrılsa da geçmiş dersler ve tahsilatlar kalmalıdır — finansal ve denetim kayıtları asla kaybolmaz. |
| **RESTRICT** | `memberships.package_id → packages.id` | Kullanımda olan bir paket tanımı silinemez; silinirse üyeliklerin fiyat ve hak bilgisi anlamını yitirir. Paket önce `is_active = False` yapılmalıdır. |

**Kritik uyarı:** Bu kuralların hiçbiri `PRAGMA foreign_keys=ON` olmadan çalışmaz.
SQLite'ta zorlama varsayılan olarak kapalıdır ve `db/session.py` bunu her bağlantıda
açar. Veritabanına harici bir araçla (DB Browser, `sqlite3` CLI) bağlanıp silme
yaparsanız **pragmayı elle açmanız gerekir**:

```sql
PRAGMA foreign_keys = ON;
```

### ORM düzeyi cascade

Yabancı anahtar kuralına ek olarak SQLAlchemy ilişkilerinde
`cascade="all, delete-orphan"` kullanılır. İkisi farklı katmanlarda çalışır:

- **`ondelete="CASCADE"`** — veritabanı motoru uygular; ham SQL ile silme yapılsa
  bile geçerlidir.
- **`cascade="all, delete-orphan"`** — SQLAlchemy oturumu uygular; ilişki
  listesinden çıkarılan nesne (yetim kalan) silinir.

İkisi birlikte kullanıldığında hem ORM üzerinden hem doğrudan SQL ile yapılan
silmeler tutarlı sonuç verir.

### Tekil kısıtlar

| Tablo | Sütun(lar) | Anlam |
|---|---|---|
| `users` | `email` | Bir e-posta bir hesap |
| `roles` | `code` | Rol kodu benzersiz |
| `students` | `student_number` | Öğrenci numarası benzersiz |
| `instructors` | `employee_number` | Sicil numarası benzersiz |
| `pools` | `name` | Havuz adı benzersiz |
| `packages` | `name` | Paket adı benzersiz |
| `invoices` | `invoice_number` | Fatura numarası benzersiz |
| `payments` | `receipt_number` | Fiş numarası benzersiz |
| `discounts` | `code` | İndirim kodu benzersiz |
| `holidays` | `date` | Bir güne tek tatil kaydı |
| `app_settings` | `key` | Ayar anahtarı benzersiz |
| `kpi_targets` | `kpi_key` | KPI başına tek hedef |
| `backup_records` | `backup_id` | Yedek kimliği benzersiz |
| `attendance_tokens` | `token` | Token benzersiz |
| `student_cards` | `card_code` | Kart kodu benzersiz |

Ardışık numaralar (`OGR00001`, `FT00042`) `crud.next_sequence_number()` ile
üretilir. Eşzamanlı iki kayıt aynı numarayı denerse tekil kısıt `IntegrityError`
fırlatır; bu, `exceptions.py` içinde `409 Conflict` + `common.already_exists`
koduna dönüştürülür — hiçbir zaman 500 hatası olarak sızmaz.

### Uygulama düzeyi kurallar

Bazı kurallar veritabanı kısıtıyla ifade edilemez ve servis katmanında uygulanır:

| Kural | Nerede |
|---|---|
| Zaman çakışması (eğitmen/kulvar/öğrenci) | `services/scheduling.py` → `ConflictChecker` |
| `end_at > start_at` | `ConflictChecker.check()` |
| Ders hakkı çift düşümü | `lesson_enrollments.credit_consumed` bayrağı |
| Kapasite aşımı | Kayıt uç noktası, `Lesson.enrolled_count` ile karşılaştırma |
| Parola politikası | `core/security.py`, `auth.password_weak` mesajı |
| Hassas alan maskeleme | `AccessScope.can_read_sensitive()` / `can_read_salary()` |

### Hassas veri ve KVKK/GDPR

| Önlem | Uygulama |
|---|---|
| Veri minimizasyonu | `guardians.national_id_last4` — TC kimlik numarasının tamamı **saklanmaz** |
| Açık rıza | `students.consent_given` + `students.consent_date` |
| Erişim kısıtı | `health_notes`, `special_needs` yalnızca `student:read_sensitive` izniyle döner |
| Maaş gizliliği | `hourly_rate`, `monthly_salary` yalnızca `system_admin`, `school_director`, `finance`, `hr` rollerine |
| Denetim maskeleme | `audit_logs.changes` içinde parola/anahtar `***` |
| Prompt gizliliği | `ai_tasks.prompt_preview` yalnızca `AI_LOG_PROMPTS=true` iken doldurulur |
| Yedek gizliliği | `.env`, `.key`, `.pem`, `credentials`, `secrets`, `token`, `id_rsa` desenleri yedeğe **girmez** |
| Demo ayrımı | `is_demo` bayrağı gerçek veriyle demo veriyi ayırır |

---

## 8. PostgreSQL'e Geçiş

Veri katmanı saf SQLAlchemy 2.0'dır; hiçbir yerde ham SQL veya SQLite'a özgü
sözdizimi yoktur. Geçiş temelde bir yapılandırma değişikliğidir.

### Adım 1 — Bağımlılık

```powershell
C:\SwimmingSchool\.venv\Scripts\python.exe -m pip install "psycopg[binary]"
```

### Adım 2 — `.env`

```ini
DATABASE_URL=postgresql+psycopg://swim_user:GUCLU_PAROLA@localhost:5432/swimming_school
```

`config.py` içindeki `resolved_database_url()` yalnızca `sqlite:///` ile başlayan
göreli yolları mutlaklaştırır; PostgreSQL URL'i olduğu gibi kullanılır.
`session.py` `_is_sqlite` bayrağını otomatik olarak `False` yapar; bunun sonucunda:

- SQLite PRAGMA dinleyicisi **kaydedilmez** (PostgreSQL'de gereksiz — yabancı
  anahtarlar zaten her zaman zorlanır)
- `connect_args` boş geçilir (`check_same_thread` PostgreSQL'de anlamsız)
- `pool_pre_ping=True` etkinleşir — kopuk bağlantılar otomatik yenilenir

### Adım 3 — Şema oluşturma

```powershell
cd C:\SwimmingSchool\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Alembic aynı revizyonları PostgreSQL üzerinde çalıştırır. `render_as_batch=True`
PostgreSQL'de zararsızdır (batch modu yalnızca gerektiğinde devreye girer).

### Adım 4 — Veri taşıma

Şema uyumlu olduğu için tablo bazlı kopyalama yeterlidir. Yaklaşım: SQLite'tan
oku, PostgreSQL'e yaz — bağımlılık sırasına dikkat ederek
(`roles` → `users` → `user_roles` → `groups` → `instructors` → `students` → …).
`sequence` değerlerini taşıdıktan sonra sıfırlamayı unutmayın:

```sql
SELECT setval('students_id_seq', (SELECT COALESCE(MAX(id), 1) FROM students));
-- her tablo için tekrarlayın
```

### Dikkat edilecek noktalar

| Konu | SQLite | PostgreSQL | Etki |
|---|---|---|---|
| **Yedekleme** | `sqlite3.Connection.backup()` çalışır | **Desteklenmiyor** — `pg_dump` akışı v1.0'a planlandı | `services/backup.py` PostgreSQL'de yedek üretmez; harici `pg_dump` kullanın |
| **Yabancı anahtar** | Pragma ile açılmalı | Her zaman açık | Davranış aynılaşır, sürpriz yok |
| **Tarih/saat** | Metin olarak saklanır, tz bilgisi zayıf | Gerçek `timestamptz` | `scheduling._naive()` SQLite karşılaştırmaları için tz düşürür; PostgreSQL'de tz farkındalığı korunur, karşılaştırmalar gözden geçirilmeli |
| **Tip esnekliği** | Dinamik tip (`VARCHAR(20)`'ye 40 karakter yazılabilir) | Katı tip zorlaması | SQLite'ta fark edilmeyen taşmalar PostgreSQL'de hata verir; geçiş öncesi veri doğrulaması yapın |
| **`LIKE` duyarlılığı** | ASCII'de büyük/küçük harf duyarsız | Duyarlı (`ILIKE` gerekir) | `crud.apply_search()` zaten `func.lower(...)` kullandığı için **etkilenmez** |
| **NUMERIC** | Float olarak saklanır | Gerçek keyfi hassasiyet | Para hesaplarında **iyileşme** — yuvarlama farkları azalır |
| **JSON sütunları** | Metin | `json` (istenirse `jsonb`) | `permissions`, `splits`, `weekdays`, `changes` çalışır; sorgulanabilirlik için `jsonb`'ye geçilebilir |
| **Eşzamanlılık** | Tek yazar (WAL ile iyileşir) | Çok yazarlı MVCC | Çok kullanıcılı kurulumda asıl kazanç budur |
| **Boolean** | 0/1 tamsayı | Gerçek `boolean` | SQLAlchemy şeffaf biçimde çevirir |
| **Sıra numaraları** | `AUTOINCREMENT` | `SEQUENCE` | Taşıma sonrası `setval()` şart |

### Ne değişmez

- Model dosyalarında **tek satır değişiklik gerekmez**
- Alembic revizyonları aynen çalışır
- Servis katmanı, API ve arayüz etkilenmez
- 395 test fonksiyonunun tamamı aynı kalır

### Kontrol listesi

```
[ ] pip install "psycopg[binary]"
[ ] Veritabanı ve kullanıcı oluştur (CREATE DATABASE / CREATE USER / GRANT)
[ ] SQLite'tan tam yedek al (geri dönüş noktası)
[ ] .env → DATABASE_URL güncelle
[ ] alembic upgrade head
[ ] Veriyi taşı, sequence değerlerini setval() ile düzelt
[ ] pytest tests -q  → 395 test fonksiyonu yeşil
[ ] Yedekleme akışını pg_dump ile yeniden kur (yerleşik akış SQLite'a özgüdür)
[ ] Kayıt sayılarını karşılaştır (students, lessons, payments …)
```

---

## 9. Bakım

### Veritabanı boyutu

CAIO gözlemcisi (`services/ai/caio.py` → `_observe_database`) veritabanı boyutunu
ve veri kalitesi göstergelerini izler:

- `database_size_mb`
- Eksik doğum tarihi olan öğrenci sayısı
- İletişim bilgisi olmayan öğrenci sayısı
- Rızası alınmamış aktif öğrenci sayısı
- Yoklaması alınmamış geçmiş ders sayısı
- Takvimdeki çakışma sayısı

Bu göstergeler `/api/v1/ai/caio` uçları ve CAIO ekranı üzerinden görülebilir.

### VACUUM

SQLite silinen satırların yerini otomatik geri vermez; `VACUUM` dosyayı yeniden
yazarak boş alanı işletim sistemine iade eder ve parçalanmayı giderir.

```powershell
# Uygulama KAPALIYKEN çalıştırın
C:\SwimmingSchool\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect(r'C:\SwimmingSchool\data\swimming_school.db'); c.execute('VACUUM'); c.close(); print('VACUUM tamam')"
```

| Kural | Açıklama |
|---|---|
| Ne zaman | Yılda bir veya toplu demo veri silme sonrası. Rutin olarak gerekmez. |
| Uygulama açıkken | **Çalıştırmayın.** VACUUM tüm veritabanını kilitler ve dosyayı yeniden yazar. |
| Disk alanı | İşlem sırasında geçici olarak veritabanının bir kopyası kadar boş alan gerekir. |
| Öncesinde | **Mutlaka yedek alın.** |

`ANALYZE` ise sorgu planlayıcı istatistiklerini günceller ve çok daha ucuzdur;
veri hacmi belirgin biçimde değiştiyse çalıştırılabilir:

```sql
ANALYZE;
```

### WAL checkpoint

WAL modunda yazmalar önce `swimming_school.db-wal` dosyasına gider ve periyodik
olarak ana dosyaya aktarılır (checkpoint). Veri dizininde üç dosya bulunur:

```
data/swimming_school.db        ← ana veritabanı
data/swimming_school.db-wal    ← yazma günlüğü
data/swimming_school.db-shm    ← paylaşılan bellek indeksi
```

SQLite bunu kendiliğinden yönetir; elle müdahale normalde gerekmez. WAL dosyası
beklenmedik biçimde büyürse (uzun ömürlü bir okuma işlemi checkpoint'i engelliyorsa):

```powershell
C:\SwimmingSchool\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect(r'C:\SwimmingSchool\data\swimming_school.db'); print(c.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()); c.close()"
```

Dönen üçlü `(busy, log_pages, checkpointed_pages)` anlamına gelir; `busy = 0`
başarılı checkpoint demektir.

**Uyarı:** `-wal` ve `-shm` dosyalarını **elle silmeyin**. Uygulama düzgün
kapandığında SQLite bunları kendisi temizler; zorla silmek son işlemlerin
kaybına yol açabilir.

### Yedekleme etkileşimi

Yedekleme servisi WAL modunu doğru biçimde ele alır (`services/backup.py`):

```python
def _snapshot_sqlite(destination: Path) -> bool:
    """SQLite veritabanının tutarlı bir kopyasını alır.

    `sqlite3.Connection.backup()` çevrimiçi yedekleme API'sini kullanır; bu,
    WAL modunda açık bağlantılar varken bile bütünlüklü kopya üretir.
    """
```

| Yaklaşım | Sonuç |
|---|---|
| `.db` dosyasını elle kopyalamak | **Yanlış.** WAL'daki henüz aktarılmamış işlemleri kaçırır; bozuk yedek üretebilir. |
| `sqlite3.Connection.backup()` | **Doğru.** Uygulama çalışırken bile tutarlı, tek dosyalık kopya üretir. Sistemin kullandığı yöntem budur. |

Yedek akışının ilgili özellikleri:

| Özellik | Davranış |
|---|---|
| Biçim | ZIP arşivi + `backup_manifest.json` + SHA-256 özetleri |
| Sırlar | `.env`, `.key`, `.pem`, `credentials`, `secrets`, `token`, `id_rsa` **dâhil edilmez** |
| Bütünlük | Yedek sonrası otomatik doğrulama; içerik `PRAGMA integrity_check` ile denetlenir |
| Sürüm bilgisi | `app_version` ve `db_revision` (Alembic) manifeste yazılır |
| Kayıt sayıları | 12 ana tablo için `record_counts` alanına yazılır — geri yükleme öncesi karşılaştırma |
| Geri yükleme | Doğrula → **güvenlik yedeği al** → önizle → onayla → geri yükle → bütünlük kontrolü → hata varsa **otomatik rollback** |
| Saklama | Günlük 7 / haftalık 4 / aylık 12 (varsayılan); `is_protected` işaretli yedekler silinmez |
| Zamanlama | `BACKUP_SCHEDULE_ENABLED=true` ise cron (`0 23 * * *`) ile uygulama yaşam döngüsüne bağlı çalışır |

### Bütünlük kontrolü

```powershell
C:\SwimmingSchool\.venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect(r'C:\SwimmingSchool\data\swimming_school.db'); print(c.execute('PRAGMA integrity_check').fetchone()[0]); print(c.execute('PRAGMA foreign_key_check').fetchall()); c.close()"
```

- `integrity_check` → `ok` beklenir
- `foreign_key_check` → **boş liste** beklenir; dolu geliyorsa yetim kayıtlar var
  demektir (büyük olasılıkla pragma kapalıyken harici bir araçla silme yapılmış)

### Log dosyaları

Veritabanı bakımıyla birlikte `logs/` dizini de gözden geçirilmelidir:
`application`, `database`, `ai`, `security`, `developer-agent`, `audit`.
Bunlar veritabanına yazılmaz, döner (rotating) dosya olarak tutulur.

### Bakım takvimi önerisi

| Sıklık | İşlem |
|---|---|
| Günlük | Otomatik yedek (23:00), yedek doğrulaması |
| Haftalık | `backup_status()` gözden geçirme, CAIO veri kalitesi bulguları |
| Aylık | `PRAGMA integrity_check` + `PRAGMA foreign_key_check`, saklama politikası kontrolü |
| Yıllık / toplu silme sonrası | `VACUUM` (uygulama kapalıyken, yedek aldıktan sonra) + `ANALYZE` |
| Sürüm yükseltmesi öncesi | `pre_update` / `pre_migration` tipli yedek |
