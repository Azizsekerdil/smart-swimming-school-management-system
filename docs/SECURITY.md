# Güvenlik Kılavuzu

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'nin güvenlik modelini kaynak kod
düzeyinde açıklar: kimlik doğrulama, rol bazlı yetkilendirme, hassas veri
koruması, sır yönetimi, denetim kaydı ve üretime çıkış kontrol listesi.
Anlatılan her mekanizma `backend/app/` altında çalışan gerçek koddur.

- **Sürüm:** 0.9.0
- **Lisans:** MIT (garanti içermez — bkz. `LICENSE`)
- **Kalite kapısı:** `FINAL_CHECK.bat`

---

## 1. Güvenlik Modeli Özeti

Sistem, tek kurum içinde çalışan (on-premise) bir yüzme okulu yönetim
uygulamasıdır. Tehdit modeli buna göre kurulmuştur: birincil risk internetten
gelen anonim saldırgan değil, **yetkisiz iç erişim, sır sızıntısı ve veri
kaybıdır**.

| Katman | Mekanizma | Kaynak |
|--------|-----------|--------|
| Taşıma | CORS beyaz listesi, güvenlik başlıkları, üretimde HSTS | `backend/app/main.py` |
| Kimlik | bcrypt (12 tur) + JWT (HS256), erişim/yenileme jetonu ayrımı | `backend/app/core/security.py` |
| Giriş koruması | Hız sınırlama + hesap kilitleme + `login_attempts` kaydı | `backend/app/api/v1/auth.py` |
| Yetki | 21 rol, 52 ince taneli izin, izin birleşimi | `backend/app/core/permissions.py` |
| Satır bazlı erişim | `AccessScope` — kendi verisi / kendi dersleri | `backend/app/api/deps.py` |
| Alan bazlı maskeleme | Sağlık notu, özel ihtiyaç, maaş/ücret | `api/v1/students.py`, `api/v1/instructors.py` |
| Veri katmanı | SQLAlchemy 2.0 parametreli sorgular, Pydantic v2 doğrulama | `backend/app/models/`, `backend/app/schemas/` |
| Hata yüzeyi | Tek tip hata zarfı; yığın izi/SQL istemciye sızmaz | `backend/app/core/exceptions.py` |
| Log | Kategorili log + otomatik sır maskeleme filtresi | `backend/app/core/logging_config.py` |
| Denetim | `audit_logs` tablosu, hassas alanlar `***` | `backend/app/services/audit.py` |
| AI ajanı | Komut beyaz listesi + yasak desenler + yol kısıtı | `backend/app/services/ai/policy.py` |
| Yedek | ZIP + SHA-256; sır dosyaları arşive alınmaz | `backend/app/services/backup.py` |

**Tasarım ilkeleri**

1. **Hiçbir sır kaynak koda gömülmez.** Tüm sırlar `.env`'den okunur.
2. **Hata mesajları bilgi sızdırmaz.** İstemci yerelleştirilmiş bir mesaj ve
   kararlı bir kod görür; ayrıntı yalnızca sunucu logundadır.
3. **Varsayılan kapalıdır.** AI yama uygulama (`AI_DEVELOPER_ALLOW_APPLY`) ve
   kabuk erişimi (`AI_DEVELOPER_ALLOW_SHELL`) varsayılan olarak `false`.
4. **Veri minimizasyonu.** Yalnızca operasyon için gerekli kişisel veri tutulur.

---

## 2. Kimlik Doğrulama

### 2.1 Parola hashleme

```python
# backend/app/core/security.py
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
```

- **Algoritma:** bcrypt, **12 tur** (2^12 = 4096 iterasyon). Tuz (salt) her hash
  için rastgele üretilir ve hash içinde saklanır.
- Parolalar hiçbir yerde düz metin tutulmaz; `users.hashed_password` yalnızca
  bcrypt çıktısını içerir.

### 2.2 72 baytlık bcrypt sınırı ve SHA-256 ön özeti

bcrypt girdinin ilk 72 baytını kullanır; daha uzun parolalarda kalan kısım
sessizce yok sayılır. Bu, uzun parola kullanan kullanıcılar için gerçek entropiyi
düşürür. Sistem bunu bir SHA-256 ön özetiyle çözer:

```python
def hash_password(plain_password: str) -> str:
    # bcrypt 72 bayt sınırı - uzun parolaları önce SHA-256 ile özetleriz
    if len(plain_password.encode("utf-8")) > 72:
        plain_password = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.hash(plain_password)
```

Aynı dönüşüm `verify_password()` içinde de uygulanır, böylece doğrulama
simetriktir. SHA-256 çıktısı 64 karakterlik onaltılık metindir; bu da 72 baytın
altında kalır ve parolanın tamamı hesaba katılmış olur.

`verify_password()` ayrıca her istisnayı yutup `False` döner — bozuk veya farklı
şemayla üretilmiş bir hash, istemciye "bu hash geçersiz" bilgisini sızdırmaz.

### 2.3 Zamanlama saldırısı önlemi

Kullanıcı bulunamadığında hiçbir bcrypt işlemi yapılmazsa, yanıt süresi
"bu e-posta kayıtlı mı?" sorusunu ele verir. Bunu engellemek için modül yükleme
anında gerçek bir kukla hash üretilir ve kullanıcı yoksa da doğrulama maliyeti
ödenir:

```python
# backend/app/api/v1/auth.py
# Kullanıcı bulunamadığında da parola doğrulama maliyeti ödenir; böylece
# "kullanıcı var mı?" bilgisi yanıt süresinden çıkarılamaz (zamanlama saldırısı).
_DUMMY_PASSWORD_HASH = hash_password("zamanlama-saldirisi-onlemi")

user = db.scalar(select(User).where(func.lower(User.email) == email))
if user is None:
    verify_password(payload.password, _DUMMY_PASSWORD_HASH)
    _log_attempt(db, email, ip, ua, False)
    raise AuthenticationError("auth.invalid_credentials")
```

Ayrıca bilinmeyen kullanıcı ile hatalı parola **aynı** hata kodunu döner
(`auth.invalid_credentials`), böylece kullanıcı numaralandırması (enumeration)
yanıt içeriğinden de yapılamaz.

Sabit süreli dize karşılaştırması gereken yerler için
`constant_time_compare()` (`hmac.compare_digest`) kullanılır.

### 2.4 JWT yapısı

```python
payload = {
    "sub": str(subject),      # kullanıcı kimliği
    "type": token_type,       # "access" | "refresh"
    "iat": int(now.timestamp()),
    "exp": int((now + expires_delta).timestamp()),
    "jti": secrets.token_hex(8),   # her jetona benzersiz kimlik
}
```

| Özellik | Access | Refresh |
|---------|--------|---------|
| `type` iddiası | `access` | `refresh` |
| Ömür | `ACCESS_TOKEN_EXPIRE_MINUTES` (varsayılan 120 dk) | `REFRESH_TOKEN_EXPIRE_DAYS` (varsayılan 14 gün) |
| Ek iddialar | `email`, `roles` | yok |
| Korumalı uçlarda geçerli mi? | Evet | **Hayır** |

- İmza: `HS256`, anahtar `SECRET_KEY`. `.env` içinde tanımlı değilse uygulama
  her başlangıçta `secrets.token_urlsafe(64)` ile rastgele bir anahtar üretir —
  bu, üretimde tüm oturumların yeniden başlatmada geçersiz olması demektir.
  Üretimde `SECRET_KEY` **mutlaka** sabitlenmelidir.
- `decode_token()` süresi dolmuş/imzası bozuk jeton için istisna fırlatmaz,
  `None` döner; çağıran taraf bunu `auth.invalid_token` hatasına çevirir.
- `get_current_user` yalnızca `type == "access"` olan jetonu kabul eder, ardından
  kullanıcıyı veritabanından tazeler ve `is_active` denetimi yapar. Bir kullanıcı
  pasife alındığında elindeki jeton, süresi dolmasa bile ilk istekte reddedilir.
- `jti` alanı jeton başına benzersizdir; ileride kara liste (revocation) eklemek
  için gereken alt yapıyı hazır tutar.

**Bilinen sınır:** Bu sürümde jeton iptal listesi (blacklist) yoktur.
`POST /auth/logout` sunucuda yalnızca denetim kaydı bırakır; jeton istemci
tarafında silinir ve doğal süresi dolana kadar teknik olarak geçerli kalır.
Erişim jetonu ömrünün kısa tutulması (varsayılan 120 dakika) bu riski sınırlar.

---

## 3. Yetkilendirme (RBAC)

### 3.1 Model

- İzinler `kaynak:eylem` biçimindedir (`student:read`, `finance:write` …).
- **52 izin**, **21 rol** tanımlıdır (`backend/app/core/permissions.py`).
- Bir kullanıcı birden fazla role sahip olabilir; efektif izin kümesi rollerin
  **birleşimidir** (`permissions_for_roles`).
- `is_superuser` olan kullanıcı tüm izin denetimlerini geçer.
- Roller `is_system=True` olarak tohumlanır; kod ile veritabanı arasında tek
  doğruluk kaynağı `ROLE_PERMISSIONS` sözlüğüdür.

Denetim uç noktada bağımlılık olarak yapılır:

```python
# backend/app/api/deps.py
def require_permissions(*permissions: str, require_all: bool = True) -> Callable:
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.is_superuser:
            return user
        owned = user.permissions
        needed = {str(p) for p in permissions}
        ok = needed.issubset(owned) if require_all else bool(needed & owned)
        if not ok:
            raise PermissionDeniedError(
                details={"required": sorted(needed), "missing": sorted(needed - owned)}
            )
        return user
    return _checker
```

### 3.2 İzin kataloğu (52 izin)

| Kaynak | İzinler |
|--------|---------|
| Öğrenci | `student:read`, `student:write`, `student:delete`, `student:read_sensitive` |
| Veli | `guardian:read`, `guardian:write`, `guardian:delete` |
| Eğitmen | `instructor:read`, `instructor:write`, `instructor:delete` |
| Havuz | `pool:read`, `pool:write`, `pool:delete`, `pool:maintenance` |
| Ders | `lesson:read`, `lesson:write`, `lesson:delete`, `lesson:schedule` |
| Yoklama | `attendance:read`, `attendance:write` |
| Üyelik | `membership:read`, `membership:write`, `membership:delete` |
| Finans | `finance:read`, `finance:write`, `finance:delete` |
| Performans | `performance:read`, `performance:write` |
| Yarışma | `competition:read`, `competition:write` |
| Rapor / istatistik | `report:read`, `report:export`, `statistics:read`, `kpi:write` |
| Yapay zekâ | `ai:use`, `ai:configure`, `ai:developer`, `ai:caio` |
| Kullanıcı / rol | `user:read`, `user:write`, `user:delete`, `role:manage` |
| Sistem | `settings:read`, `settings:write`, `audit:read`, `system:health` |
| Yedekleme | `backup:read`, `backup:create`, `backup:restore` |
| Bildirim | `notification:read`, `notification:send` |
| Portal | `self:portal` |

### 3.3 Rol özeti

| Rol kodu | Türkçe adı | İzin sayısı | Kapsam kısıtı |
|----------|-----------|-------------|---------------|
| `system_admin` | Sistem Yöneticisi | 52 | Yok (tam yetki) |
| `school_director` | Yüzme Okulu Müdürü | 49 | Yok |
| `operations_manager` | Operasyon Müdürü | 34 | Yok |
| `reception` | Resepsiyon | 19 | Yok |
| `finance` | Finans / Muhasebe | 14 | Yok |
| `sales_marketing` | Satış / Pazarlama | 14 | Yok |
| `hr` | İnsan Kaynakları | 13 | Yok |
| `head_coach` | Baş Antrenör | 25 | Yok |
| `swim_coach` | Yüzme Antrenörü | 17 | Eğitmen kapsamı |
| `swim_instructor` | Yüzme Eğitmeni | 15 | Eğitmen kapsamı |
| `kids_instructor` | Çocuk Yüzme Eğitmeni | 15 | Eğitmen kapsamı |
| `baby_instructor` | Bebek Yüzme Eğitmeni | 15 | Eğitmen kapsamı |
| `private_instructor` | Özel Ders Eğitmeni | 15 | Eğitmen kapsamı |
| `adaptive_instructor` | Adaptif Yüzme Eğitmeni | 16 | Eğitmen kapsamı |
| `conditioning_coach` | Kondisyon / Performans Antrenörü | 15 | Eğitmen kapsamı |
| `lifeguard` | Cankurtaran | 8 | Yok |
| `pool_technician` | Havuz Teknik Personeli | 7 | Yok |
| `medical_staff` | Sağlık / İlk Yardım Personeli | 8 | Yok |
| `athlete` | Sporcu | 6 | Kendi verisi |
| `student` | Öğrenci | 5 | Kendi verisi |
| `parent` | Veli | 7 | Kendi çocuklarının verisi |

### 3.4 Rol → izin matrisi (özet)

`R` = okuma, `W` = yazma, `D` = silme, `•` = ilgili izin var, boş = yok.

| Rol | Öğrenci | Hassas | Veli | Eğitmen | Havuz | Ders | Yoklama | Üyelik | Finans | Perf. | Yarışma | Rapor | İstat. | AI | Kullanıcı | Ayar | Denetim | Yedek |
|-----|---------|--------|------|---------|-------|------|---------|--------|--------|-------|---------|-------|--------|----|-----------|------|---------|-------|
| `system_admin` | RWD | • | RWD | RWD | RWD | RWD | RW | RWD | RWD | RW | RW | R+dışa | R | tümü | RWD | RW | • | RC+geri |
| `school_director` | RWD | • | RWD | RWD | RWD | RWD | RW | RWD | RWD | RW | RW | R+dışa | R | use/conf/caio | RW | RW | • | RC+geri |
| `operations_manager` | RW | | RW | RW | RW+bakım | RWD | RW | RW | R | RW | RW | R+dışa | R | use | | R | | RC |
| `reception` | RW | | RW | R | R | RW | RW | RW | RW | | | R | | use | | | | |
| `finance` | R | | R | R | | | | RW | RWD | | | R+dışa | R | use | | | | |
| `hr` | | | | RWD | | R | R | | | | | R+dışa | R | use | RW | | | |
| `sales_marketing` | RW | | RW | | | | | RW | R | | | R+dışa | R | | | | | |
| `head_coach` | RW | • | R | RW | R | RWD | RW | | | RW | RW | R+dışa | R | use | | | | |
| `swim_coach` | R | | R | R | R | RW | RW | | | RW | RW | R | R | use | | | | |
| `swim_instructor` | R | | R | R | R | R | RW | | | RW | R | R | R | use | | | | |
| `kids_instructor` | R | | R | R | R | R | RW | | | RW | R | R | R | use | | | | |
| `baby_instructor` | R | | R | R | R | R | RW | | | RW | R | R | R | use | | | | |
| `private_instructor` | R | | R | R | R | R | RW | | | RW | R | R | R | use | | | | |
| `adaptive_instructor` | R | • | R | R | R | R | RW | | | RW | R | R | R | use | | | | |
| `conditioning_coach` | R | | R | R | R | R | RW | | | RW | R | R | R | use | | | | |
| `lifeguard` | R | | R | R | R | R | R | | | | | | | | | | | |
| `pool_technician` | | | | | RW+bakım | R | | | | | | | | | | | | |
| `medical_staff` | R | • | R | | | R | R | | | | | | | | | | | |
| `athlete` | | | | | | R | R | | | R | R | | | | | | | |
| `student` | | | | | | R | R | | | R | | | | | | | | |
| `parent` | | | | | | R | R | | R (R) | R | | | | | | | | |

> "Hassas" sütunu `student:read_sensitive` iznini, "Finans" sütunundaki
> parantezli `R` velinin yalnızca kendi çocuklarının ödemelerini görebildiğini
> anlatır. `parent` rolü `membership:read` ve `finance:read` izinlerine sahiptir
> ancak satır bazlı kapsam nedeniyle veri kümesi kendi çocuklarıyla sınırlıdır.

### 3.5 Rol → izin listeleri (tam)

<details>
<summary><b>Yönetim rolleri</b></summary>

**`system_admin`** — 52 izin: tüm `Perm` kümesi.

**`school_director`** — 49 izin: tüm izinler eksi `ai:developer`, `role:manage`,
`user:delete`.

**`operations_manager`** — 34 izin:
`student:read`, `student:write`, `guardian:read`, `guardian:write`,
`instructor:read`, `instructor:write`, `pool:read`, `pool:write`,
`pool:maintenance`, `lesson:read`, `lesson:write`, `lesson:schedule`,
`lesson:delete`, `attendance:read`, `attendance:write`, `membership:read`,
`membership:write`, `finance:read`, `performance:read`, `performance:write`,
`competition:read`, `competition:write`, `report:read`, `report:export`,
`statistics:read`, `kpi:write`, `ai:use`, `notification:read`,
`notification:send`, `settings:read`, `backup:read`, `backup:create`,
`system:health`, `self:portal`.

**`finance`** — 14 izin:
`student:read`, `guardian:read`, `instructor:read`, `membership:read`,
`membership:write`, `finance:read`, `finance:write`, `finance:delete`,
`report:read`, `report:export`, `statistics:read`, `ai:use`,
`notification:read`, `self:portal`.

**`hr`** — 13 izin:
`instructor:read`, `instructor:write`, `instructor:delete`, `user:read`,
`user:write`, `lesson:read`, `attendance:read`, `report:read`, `report:export`,
`statistics:read`, `ai:use`, `notification:read`, `self:portal`.

**`reception`** — 19 izin:
`student:read`, `student:write`, `guardian:read`, `guardian:write`,
`instructor:read`, `pool:read`, `lesson:read`, `lesson:write`,
`lesson:schedule`, `attendance:read`, `attendance:write`, `membership:read`,
`membership:write`, `finance:read`, `finance:write`, `report:read`,
`notification:read`, `ai:use`, `self:portal`.

**`sales_marketing`** — 14 izin:
`student:read`, `student:write`, `guardian:read`, `guardian:write`,
`membership:read`, `membership:write`, `finance:read`, `report:read`,
`report:export`, `statistics:read`, `notification:read`, `notification:send`,
`ai:use`, `self:portal`.

</details>

<details>
<summary><b>Eğitim rolleri</b></summary>

**Eğitmen temel kümesi (`_INSTRUCTOR_BASE`)** — 15 izin:
`student:read`, `guardian:read`, `instructor:read`, `pool:read`, `lesson:read`,
`attendance:read`, `attendance:write`, `performance:read`, `performance:write`,
`competition:read`, `report:read`, `statistics:read`, `ai:use`,
`notification:read`, `self:portal`.

| Rol | İzinler |
|-----|---------|
| `swim_instructor` | Temel küme (15) |
| `kids_instructor` | Temel küme (15) |
| `baby_instructor` | Temel küme (15) |
| `private_instructor` | Temel küme (15) |
| `conditioning_coach` | Temel küme (15) |
| `adaptive_instructor` | Temel küme + `student:read_sensitive` (16) |
| `swim_coach` | Temel küme + `lesson:write`, `competition:write` (17) |
| `head_coach` | Temel küme + `student:write`, `student:read_sensitive`, `instructor:write`, `lesson:write`, `lesson:schedule`, `lesson:delete`, `competition:write`, `report:export`, `kpi:write`, `notification:send` (25) |

</details>

<details>
<summary><b>Diğer roller</b></summary>

**`lifeguard`** — 8 izin: `student:read`, `guardian:read`, `instructor:read`,
`pool:read`, `lesson:read`, `attendance:read`, `notification:read`,
`self:portal`.

**`pool_technician`** — 7 izin: `pool:read`, `pool:write`, `pool:maintenance`,
`lesson:read`, `notification:read`, `system:health`, `self:portal`.

**`medical_staff`** — 8 izin: `student:read`, `student:read_sensitive`,
`guardian:read`, `lesson:read`, `attendance:read`, `notification:read`,
`notification:send`, `self:portal`.

**`athlete`** — 6 izin: `self:portal`, `lesson:read`, `attendance:read`,
`performance:read`, `competition:read`, `notification:read`.

**`student`** — 5 izin: `self:portal`, `lesson:read`, `attendance:read`,
`performance:read`, `notification:read`.

**`parent`** — 7 izin: `self:portal`, `lesson:read`, `attendance:read`,
`performance:read`, `membership:read`, `finance:read`, `notification:read`.

</details>

### 3.6 Satır bazlı erişim kapsamı

İzin "hangi uca girebilirim" sorusunu, kapsam "hangi satırları görebilirim"
sorusunu yanıtlar. İkisi bağımsız katmanlardır.

```python
# backend/app/api/deps.py
SELF_SCOPED_ROLES = {RoleCode.ATHLETE, RoleCode.STUDENT, RoleCode.PARENT}

INSTRUCTOR_SCOPED_ROLES = {
    RoleCode.SWIM_INSTRUCTOR, RoleCode.KIDS_INSTRUCTOR, RoleCode.BABY_INSTRUCTOR,
    RoleCode.PRIVATE_INSTRUCTOR, RoleCode.ADAPTIVE_INSTRUCTOR,
    RoleCode.CONDITIONING_COACH, RoleCode.SWIM_COACH,
}
```

`AccessScope` üç bayrak hesaplar:

| Bayrak | Koşul | Etki |
|--------|-------|------|
| `is_admin` | `is_superuser` **veya** `system_admin` / `school_director` / `operations_manager` rolü | Hiçbir satır kısıtı uygulanmaz |
| `is_self_scoped` | Admin değil **ve** `SELF_SCOPED_ROLES` içinden bir rol var **ve** `student:write` izni **yok** | Yalnızca kendi (ve çocuklarının) kayıtları |
| `is_instructor_scoped` | Admin değil, self-scoped değil **ve** `INSTRUCTOR_SCOPED_ROLES` içinden bir rol var | Öncelikle kendi dersleri |

`allowed_student_ids()` self-scoped kullanıcı için izinli öğrenci kimliklerini
üretir; kullanıcı hiçbir öğrenciyle ilişkilendirilmemişse `[-1]` döner, yani
**hiçbir kayıt** görünmez (fail-closed).

```python
def allowed_student_ids(self) -> list[int] | None:
    """None => kısıt yok. Liste => yalnızca bu öğrenciler görülebilir."""
    if not self.is_self_scoped:
        return None
    ids: list[int] = []
    if self.user.student:
        ids.append(self.user.student.id)
    if self.user.guardian:
        ids.extend(sg.student_id for sg in self.user.guardian.students)
    return ids or [-1]  # eşleşme yoksa hiçbir kaydı döndürme
```

Kapsam, sorgu düzeyinde uygulanır; veri önce çekilip sonra filtrelenmez:

```python
# backend/app/api/v1/lessons.py
def _scope_filter(scope: AccessScope, stmt):
    if scope.is_instructor_scoped and scope.instructor_id:
        return stmt.where(Lesson.instructor_id == scope.instructor_id)
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        return stmt.where(
            Lesson.id.in_(
                select(LessonEnrollment.lesson_id).where(
                    LessonEnrollment.student_id.in_(allowed)
                )
            )
        )
    return stmt
```

Aynı kapsam `/students`, `/attendance`, `/performance`, `/search` ve veli
portalı uçlarında da uygulanır — global arama sonuçları bile kullanıcının izin
ve kapsamına göre filtrelenir.

---

## 4. Hassas Veri Koruması

### 4.1 Sağlık notu ve özel ihtiyaç maskeleme

```python
# backend/app/api/v1/students.py
SENSITIVE_FIELDS = ("health_notes", "special_needs")

def _to_out(student: Student, scope: AccessScope) -> StudentOut:
    """ORM -> şema. Hassas alanlar yetkisiz kullanıcıdan gizlenir."""
    data = StudentOut.model_validate(student)
    if not scope.can_read_sensitive():
        for field in SENSITIVE_FIELDS:
            setattr(data, field, None)
    return data
```

- Maskeleme **çıkış şemasında**, listeleme ve detay uçlarının ikisinde de
  uygulanır.
- Yazma tarafında da denetim vardır: `student:read_sensitive` izni olmayan bir
  kullanıcı `PATCH /students/{id}` isteğinde bu alanları göndermeye çalışırsa
  istek reddedilir.
- Bu alanlar denetim kaydına da düz metin yazılmaz; `changes` sözlüğünde
  `"***"` olarak görünür.

`student:read_sensitive` iznine sahip roller: `system_admin`, `school_director`,
`head_coach`, `adaptive_instructor`, `medical_staff` (ve `_MANAGER_FULL`
üzerinden `school_director`).

### 4.2 Ücret ve maaş bilgisi maskeleme

```python
# backend/app/api/deps.py
def can_read_salary(self) -> bool:
    return self.user.has_any_role(
        {RoleCode.SYSTEM_ADMIN, RoleCode.SCHOOL_DIRECTOR, RoleCode.FINANCE, RoleCode.HR}
    ) or self.user.is_superuser
```

`monthly_salary` ve `hourly_rate` alanları bu dört rol dışındaki kullanıcılara
`null` olarak döner; güncelleme isteğinde de gövdeden düşürülür. Denetim
kaydında bu alanların eski/yeni değerleri `"***"` yazılır.

### 4.3 KVKK / GDPR veri minimizasyonu

`backend/app/models/people.py` başında belirtildiği gibi yalnızca operasyon için
gerekli veriler tutulur:

| Tutulan | Tutulmayan |
|---------|------------|
| Ad, soyad, doğum tarihi, cinsiyet | T.C. kimlik numarası |
| İletişim (telefon, e-posta, adres) | Banka/kart bilgisi |
| Yüzme seviyesi, grup, hedefler | Biyometrik veri |
| Operasyonel sağlık notu (izinle korumalı) | Tam tıbbi kayıt / tanı geçmişi |
| Veli ilişkisi ve iletişim | Üçüncü taraf pazarlama profilleri |

**Ödeme verisi:** Sistem kart numarası, CVV veya IBAN saklamaz. `Payment`
kaydı tutar, tarih, yöntem (`cash`, `card`, `transfer` …) ve referans metnini
tutar; kart işlemi bir POS/banka tarafında gerçekleşir.

### 4.4 Açık rıza kaydı

```python
# backend/app/models/people.py
# KVKK aydınlatma onayı
consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
consent_date:  Mapped[date | None] = mapped_column(Date)
```

Öğrenci oluşturulurken rıza işaretlenmişse `consent_date` o günün tarihiyle
yazılır (`api/v1/students.py`). Böylece rızanın **ne zaman** alındığı denetim
sırasında gösterilebilir.

**Öneriler (kurum sorumluluğu):**
- Aydınlatma metnini kayıt formunda göstererek rızayı belgeleyin.
- Silme talebinde `DELETE /api/v1/students/{id}` ile kaydı kaldırın; ilişkili
  kayıtlar nedeniyle silinemiyorsa (`common.in_use`) önce bağlı kayıtları
  arşivleyin.
- Veri saklama süresi politikanızı belirleyin; yedeklerin saklama süresi
  `BACKUP_RETENTION_*` ayarlarıyla yönetilir.

---

## 5. Sır Yönetimi

### 5.1 `.env` tek kaynaktır

`backend/app/core/config.py` başındaki kural nettir:

> Tüm ayarlar ortam değişkenlerinden (.env) okunur. Hiçbir sır kaynak koda gömülmez.

Sır taşıyan ayarlar: `SECRET_KEY`, `FIRST_ADMIN_PASSWORD`, `NVIDIA_API_KEY`,
`LOCAL_AI_API_KEY`, `OPENAI_COMPAT_API_KEY`, `DATABASE_URL` (uzak veritabanı
kullanılıyorsa).

`.env.example` şablon olarak depoda bulunur ve yalnızca `CHANGE_ME_...`
yer tutucuları içerir.

### 5.2 `.gitignore` koruması

```gitignore
# --- SIRLAR / SECRETS (ASLA COMMIT EDİLMEZ) ---
.env
.env.*
!.env.example
*.key
*.pem
*.pfx
*.p12
credentials*
secrets*
tokens*
*_secret*
*apikey*
*api_key*
.secrets/
```

Ayrıca veritabanı dosyaları (`*.db`, `*.sqlite`), `backups/*` ve `logs/*` de
sürüm kontrolü dışındadır.

### 5.3 `mask_secret()` — anahtar asla tam gösterilmez

```python
# backend/app/core/config.py
def mask_secret(value: str | None) -> str:
    """API anahtarlarını güvenli biçimde maskeler. Tam değer ASLA gösterilmez."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}{'*' * 12}{value[-4:]}"
```

`GET /api/v1/ai/config` ucu `settings.public_ai_config()` döndürür; her sağlayıcı
için `api_key_set` (boolean) ve `api_key_masked` (ör. `nva************a1b2`)
alanları bulunur. Tam anahtar hiçbir API yanıtında, hiçbir test çıktısında ve
hiçbir arayüz ekranında görünmez. `POST /ai/providers/{provider}/test`
dokümantasyonunda da bu açıkça belirtilir.

### 5.4 Log redaksiyonu

Her log kaydı, dosyaya yazılmadan önce bir maskeleme filtresinden geçer:

```python
# backend/app/core/logging_config.py
_SENSITIVE_PATTERNS = [
    (re.compile(r"(nvapi-)[A-Za-z0-9_\-]{10,}", re.I), r"\1***REDACTED***"),
    (re.compile(r"(sk-)[A-Za-z0-9_\-]{16,}", re.I), r"\1***REDACTED***"),
    (re.compile(r"(gh[pousr]_)[A-Za-z0-9]{20,}", re.I), r"\1***REDACTED***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\._\-]{16,}", re.I), r"\1***REDACTED***"),
    (
        re.compile(r'("?(?:api[_-]?key|apikey|secret|password|passwd|token|authorization)"?\s*[:=]\s*"?)([^"\s,}]{4,})', re.I),
        r"\1***REDACTED***",
    ),
]
```

`RedactingFilter` hem konsol hem dosya handler'ına eklenir; mesaj metni,
biçimlendirme argümanları ve istisna izleri ayrı ayrı maskelenir. Loglar altı
kategoriye ayrılır: `application`, `database`, `ai`, `security`,
`developer-agent`, `audit` (`logs/` dizini, 5 MB döngüsel, 5 yedek).

Ek olarak `AI_LOG_PROMPTS` varsayılan olarak `false`'tur — model istemleri
(içinde kişisel veri olabilir) loga yazılmaz.

### 5.5 Yedeklerde sır bulunmaz

```python
# backend/app/services/backup.py
EXCLUDED_PATTERNS = (
    ".env", ".key", ".pem", "credentials", "secrets", "token", "id_rsa",
)
```

Bu desenlerden birini içeren dosya adı arşive **hiç alınmaz**. Manifest'e
yazılan AI yapılandırması da ek olarak temizlenir:

```python
def _sanitized_ai_config() -> dict[str, Any]:
    """AI yapılandırması - SIRLAR HARİÇ."""
    config = settings.public_ai_config()
    for section in config.values():
        if isinstance(section, dict):
            section.pop("api_key_masked", None)
    return config
```

Yani yedek dosyasından ne API anahtarı ne de maskeli hâli çıkarılabilir. Yedek
geri yüklendikten sonra `.env` içindeki anahtarların hedef makinede yeniden
girilmesi gerekir — bu bilinçli bir tasarım kararıdır.

### 5.6 Otomatik sır taraması

`FINAL_CHECK.bat` ve GitHub Actions `security` işi aynı denetimleri yapar:

| Denetim | Başarısızlık koşulu |
|---------|--------------------|
| `.gitignore` içinde `.env` satırı | Yoksa **FAIL** |
| Git index'inde sır dosyası (`.env`, `.key`, `.pem`, `credentials`, `secrets.`, `token*.json`) | Varsa **FAIL** |
| Kaynak kodda `nvapi-…`, `sk-…`, `gh[pousr]_…`, `AKIA…`, `BEGIN … PRIVATE KEY` deseni | Bulunursa **FAIL** |
| `pip-audit` bağımlılık taraması | Bulgu varsa **WARNING** |

Taranan dizinler: `backend/app`, `frontend/src`, `scripts`, `desktop`, `docs`.

---

## 6. Giriş Güvenliği

### 6.1 Hız sınırlama (rate limiting)

```python
# backend/app/api/v1/auth.py
def _rate_limited(db: Session, email: str) -> bool:
    """Son 1 dakikadaki başarısız deneme sayısını kontrol eder."""
    if not settings.rate_limit_enabled:
        return False
    since = datetime.now(timezone.utc) - timedelta(minutes=1)
    count = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.email == email,
            LoginAttempt.attempted_at >= since.replace(tzinfo=None),
            LoginAttempt.successful.is_(False),
        )
    )
    return bool(count and count >= settings.rate_limit_login_per_minute)
```

| Ayar | Varsayılan | Anlamı |
|------|-----------|--------|
| `RATE_LIMIT_ENABLED` | `true` | Hız sınırlamayı açar/kapatır |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | E-posta başına dakikadaki azami başarısız deneme |

Sınır aşıldığında `429` + `auth.rate_limited` döner ve olay `security` log
kategorisine yazılır. Sınır e-posta bazlıdır; IP değişimi sınırı sıfırlamaz.

### 6.2 Hesap kilitleme (8 deneme / 15 dakika)

```python
MAX_FAILED_ATTEMPTS = 8
LOCKOUT_MINUTES = 15

if not verify_password(payload.password, user.hashed_password):
    user.failed_login_count += 1
    if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
        user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
        security_logger.warning("Hesap kilitlendi: %s (%s)", email, ip)
    db.commit()
```

- Sayaç `users.failed_login_count`, kilit bitişi `users.locked_until`
  sütununda tutulur.
- Kilit süresince giriş denemeleri `429 auth.rate_limited` döner (parola doğru
  olsa bile).
- **Başarılı girişte** sayaç sıfırlanır ve kilit temizlenir; ayrıca
  `last_login_at` güncellenir ve bir `login` denetim kaydı oluşur.
- Kilidi süresi dolmadan kaldırmak için bir yönetici kullanıcıyı düzenleyebilir
  ya da `POST /api/v1/users/reset-password` ile parolayı sıfırlayabilir.

### 6.3 `login_attempts` tablosu

```python
class LoginAttempt(Base, IntPKMixin):
    """Giriş denemesi kaydı - rate limiting ve güvenlik denetimi için."""

    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_email_time", "email", "attempted_at"),)

    email:        Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address:   Mapped[str | None] = mapped_column(String(64))
    user_agent:   Mapped[str | None] = mapped_column(String(300))
    successful:   Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
```

| Alan | İçerik | Not |
|------|--------|-----|
| `email` | Denenen e-posta (küçük harfe indirilmiş) | Parola **kaydedilmez** |
| `ip_address` | `X-Forwarded-For` varsa ilk değer, yoksa bağlantı IP'si | `client_ip()` |
| `user_agent` | İlk 300 karakter | Uzun değerler kırpılır |
| `successful` | Başarı bayrağı | Hem başarılı hem başarısız denemeler yazılır |
| `attempted_at` | Deneme zamanı (UTC) | Bileşik indeks ile hızlı sorgulanır |

Bu tablo hem hız sınırlamanın veri kaynağıdır hem de olay sonrası inceleme
(kim, nereden, ne zaman denedi) için kalıcı bir izdir.

---

## 7. Enjeksiyon ve XSS Koruması

### 7.1 SQL enjeksiyonu — parametreli sorgular

Tüm veri erişimi SQLAlchemy 2.0 `select()` API'si üzerinden yapılır; kullanıcı
girdisi asla SQL metnine birleştirilmez.

```python
# backend/app/api/v1/students.py — arama bile parametrelidir
stmt = apply_search(
    stmt, Student, q, ["first_name", "last_name", "student_number", "phone", "email"]
)
```

- `LIKE` kalıpları `func.lower(...).like(pattern)` biçiminde bağlı parametre
  olarak geçirilir (`backend/app/api/v1/search.py`).
- Ham SQL yalnızca sabit, kullanıcı girdisi içermeyen iki yerde kullanılır:
  `SELECT 1` (sağlık kontrolü) ve `SELECT version_num FROM alembic_version`
  (sürüm bilgisi).
- Sıralama parametresi (`sort_by`) doğrudan SQL'e yazılmaz; `apply_sort()`
  yalnızca modelde gerçekten var olan sütun adlarını kabul eder, aksi hâlde
  varsayılana döner.

### 7.2 Girdi doğrulama — Pydantic v2

Her istek gövdesi bir Pydantic şemasıyla doğrulanır. Şema dışı alanlar reddedilir
veya yok sayılır; tip, uzunluk ve desen kısıtları uygulanır:

```python
# backend/app/schemas/common.py
EMAIL_PATTERN = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=255, pattern=EMAIL_PATTERN),
]
```

Örnek kısıtlar: `page_size` 1–200 arası kırpılır, `max_tokens` 1–32000,
`late_minutes` 0–240, takvim aralığı en fazla 120 gün, parola en az 8 karakter.
Doğrulama hatası tek tip `422 common.validation_error` yanıtına dönüşür ve
`details.fields` içinde yalnızca alan adı ile hata tipi paylaşılır — girilen
değer yankılanmaz.

### 7.3 XSS — React otomatik kaçış

- Arayüz React 18 + TypeScript (strict) ile yazılmıştır. JSX içine gömülen tüm
  değerler React tarafından otomatik olarak HTML-kaçışlanır.
- Projede `dangerouslySetInnerHTML` kullanımı yoktur; kullanıcı içeriği metin
  düğümü olarak render edilir.
- API tarafında da HTML üretilmez; yanıtlar JSON'dur ve
  `X-Content-Type-Options: nosniff` başlığı tarayıcının içerik türünü tahmin
  etmesini engeller.

### 7.4 CSP başlığı

```python
# backend/app/main.py
# API yanıtları için katı CSP; /app altındaki SPA kendi CSP'sini kullanır
if request.url.path.startswith("/api"):
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
```

`/api` altındaki tüm yanıtlar en katı politikayla döner: hiçbir alt kaynak
yüklenemez, sayfa hiçbir çerçeveye gömülemez. Bu, bir API yanıtının tarayıcıda
doğrudan açılıp içerik olarak yorumlanması hâlinde saldırı yüzeyini sıfırlar.

**Bilinen sınır:** SPA'nın kendisi (`/` ve statik varlıklar) şu an ayrı bir CSP
başlığı almaz; `frontend/index.html` içinde de CSP `<meta>` etiketi yoktur.
Tersine vekil (reverse proxy) arkasında dağıtım yapıyorsanız SPA yolları için
aşağıdaki gibi bir politika eklemeniz önerilir (bkz. bölüm 11):

```nginx
add_header Content-Security-Policy
  "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
```

### 7.5 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Process-Time"],
)
```

`CORS_ORIGINS` virgülle ayrılmış bir **beyaz listedir**; joker (`*`) kullanılmaz.
Varsayılan değer yalnızca yerel Vite geliştirme sunucusunu içerir
(`http://localhost:5173`, `http://127.0.0.1:5173`). Üretimde bu liste gerçek
arayüz adresiyle daraltılmalıdır.

### 7.6 Yol geçişi (path traversal)

AI geliştirici ajanının dosya erişimi `settings.developer_root_path` ile
mutlaklaştırılmış proje kökünün altına kilitlenir; dışına çıkan her istek
`403 ai.path_outside_project` döner. Yüklenen dosyalar ayrı bir statik dizinden
(`data/uploads`) servis edilir ve SPA yönlendirmesi `api/`, `docs`, `redoc`,
`openapi.json`, `uploads/` öneklerini açıkça dışlar.

---

## 8. Güvenlik Başlıkları

`backend/app/main.py` içindeki `security_headers_middleware` her yanıta şu
başlıkları ekler:

| Başlık | Değer | Amaç | Koşul |
|--------|-------|------|-------|
| `X-Content-Type-Options` | `nosniff` | Tarayıcının MIME türü tahmin etmesini engeller | Her yanıt |
| `X-Frame-Options` | `SAMEORIGIN` | Clickjacking'e karşı çerçeveleme kısıtı | Her yanıt |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Dış sitelere tam URL sızmasını engeller | Her yanıt |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Hassas tarayıcı API'lerini kapatır | Her yanıt |
| `X-Process-Time` | İstek süresi (ms) | Performans gözlemi | Her yanıt |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | API yanıtları için katı içerik politikası | Yalnızca `/api…` yolları |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HTTPS'i bir yıl boyunca zorunlu kılar | Yalnızca `APP_ENV=production` |

> `Strict-Transport-Security` başlığının etkili olması için uygulamanın gerçekten
> HTTPS üzerinden sunulması gerekir. Yerel kurulumda (`http://127.0.0.1:8000`)
> `APP_ENV=development` olduğu için bu başlık gönderilmez.

CORS ayrıca `Content-Disposition` ve `X-Process-Time` başlıklarını tarayıcı
koduna açar; bu, rapor indirmenin dosya adını doğru okuyabilmesi içindir.

---

## 9. Denetim Kaydı

Denetim kayıtları `audit_logs` tablosunda tutulur ve `GET /api/v1/audit` ucundan
(`audit:read` izniyle) sorgulanır. Ayrıca `logs/audit.log` dosyasına da yazılır.

### 9.1 Kaydedilen alanlar

| Alan | Açıklama |
|------|----------|
| `user_id`, `user_email` | İşlemi yapan kullanıcı (sistem işlemlerinde `null`) |
| `action` | `create`, `update`, `delete`, `login`, `logout`, `change_password`, `export`, `ai_test`, `restore` … |
| `entity_type` | `student`, `lesson`, `payment`, `user`, `app_setting`, `report`, `ai_provider` … |
| `entity_id` | Etkilenen kaydın kimliği (metin) |
| `summary` | İnsan okunur özet (`"Ders oluşturuldu: … @ 01.09.2026 10:00"`) |
| `changes` | Alan bazlı `{"alan": {"from": eski, "to": yeni}}` farkı |
| `ip_address` | İstemci IP'si (`X-Forwarded-For` varsa ilk değer) |
| `occurred_at` | UTC zaman damgası |

### 9.2 Atomiklik

`audit.record()` varsayılan olarak **commit etmez**:

> `commit=False` varsayılandır; çağıran işlem kendi commit'ini yapar, böylece
> denetim kaydı iş verisiyle aynı işlemde atomik olur.

Yani iş işlemi başarısız olup geri alınırsa, ona ait denetim kaydı da geri
alınır; "yapılmamış bir işlemin kaydı" oluşmaz.

### 9.3 Kaydedilmeyenler

`_sanitize()` fonksiyonu şu alanları `"***"` ile değiştirir ve bunları **asla**
düz metin yazmaz:

```python
_SENSITIVE_FIELDS = {
    "password", "hashed_password", "new_password", "current_password",
    "api_key", "nvidia_api_key", "local_ai_api_key", "secret_key",
    "token", "refresh_token", "access_token",
}
```

Ayrıca adında `password` veya `secret` geçen **her** alan otomatik maskelenir,
500 karakteri aşan metinler kırpılır ve iç içe sözlükler özyinelemeli olarak
temizlenir.

| Kaydedilir | Kaydedilmez |
|------------|-------------|
| Kim, ne zaman, hangi kayıt, hangi eylem | Parolalar (eski veya yeni) |
| Alan bazlı eski/yeni değer farkı | API anahtarları ve jetonlar |
| Rapor dışa aktarma isteği (anahtar + biçim) | Raporun içeriği |
| AI bağlantı testi sonucu | Sağlayıcı API anahtarı |
| Giriş/çıkış olayları ve IP | Denenen parola metni |
| Sağlık notu **alanının değiştiği** bilgisi | Sağlık notunun kendisi (`"***"`) |
| Maaş **alanının değiştiği** bilgisi | Maaş tutarı (`"***"`) |

Sistem seviyesi olaylar (başlangıç, migration, yedekleme) ayrıca
`system_events` tablosuna yazılır ve aynı temizleme fonksiyonundan geçer.

---

## 10. AI Ajanı Güvenliği

AI Developer Console, modelin proje üzerinde kod okuyup yama önerebildiği bir
konsoldur. Temel ilke `backend/app/services/ai/policy.py` başında yazılıdır:

> **TEMEL İLKE: Yapay zekâ Windows terminaline sınırsız erişemez.**

### 10.1 Dört katmanlı kapı

| Katman | Mekanizma |
|--------|-----------|
| 1. İzin | `ai:developer` — yalnızca `system_admin` rolünde vardır (`_MANAGER_FULL` bu izni açıkça dışlar) |
| 2. Anahtar | `AI_DEVELOPER_ENABLED`, `AI_DEVELOPER_ALLOW_APPLY`, `AI_DEVELOPER_ALLOW_SHELL` — son ikisi varsayılan `false` |
| 3. Politika | Komut beyaz listesi + yasak desen taraması + yol kısıtı |
| 4. Geri alma | Yama öncesi otomatik checkpoint; test başarısızsa otomatik rollback |

### 10.2 Komut beyaz listesi

Yalnızca şu çalıştırılabilirler kabul edilir: `pytest`, `python`, `ruff`,
`black`, `mypy`, `alembic`, `npm`, `npx`, `git`. Bunların da alt komutları
sınırlıdır — örneğin `git` için yalnızca `status`, `diff`, `log`, `show`, `add`,
`stash`, `rev-parse`, `branch`; `npm` için `run`, `ci`, `test`, `install`,
`list`, `audit`.

### 10.3 Yasak desenler

`BLOCKED_PATTERNS` listesi, komut beyaz listeyi geçse bile eşleşme hâlinde
işlemi `403 ai.command_blocked` ile durdurur. Kapsanan başlıklar:

| Kategori | Örnek engellenen |
|----------|------------------|
| Yıkıcı silme | `rm -rf`, `del /s`, `rmdir /s`, `Remove-Item -Recurse -Force` |
| Disk / önyükleme | `format c:`, `diskpart`, `bcdedit`, `vssadmin` |
| Registry | `reg add/delete`, `Set-ItemProperty HKLM:` |
| Hesap / grup | `net user`, `New-LocalUser`, `Add-LocalGroupMember` |
| İzin / sahiplik | `icacls`, `cacls`, `takeown` |
| Servis / görev | `sc config`, `Set-Service`, `schtasks`, `Register-ScheduledTask` |
| Güvenlik yazılımı | `netsh firewall`, `Set-MpPreference` |
| Uzaktan kod | `curl … \| bash`, `Invoke-WebRequest … \| iex`, `Invoke-Expression` |
| Yetki yükseltme | `Start-Process -Verb RunAs`, `runas` |
| Kimlik hırsızlığı | `Get-Credential`, `cmdkey`, `vaultcmd`, `mimikatz`, `lsass` |
| Tarayıcı sırları | `Login Data`, `logins.json`, `key4.db`, `cookies.sqlite` |
| Sır sızıntısı | `.env` erişimi |
| Tedarik zinciri | `pip install`, `npm publish/login/token`, `git push`, `git config --global` |
| Kabuk hileleri | Komut zincirleme (`;`, `&&`, `\|`), komut ikamesi (`` ` ``, `$(`), mutlak yola yönlendirme |

### 10.4 Yol kısıtı

Ajan hiçbir koşulda şu yolları okuyamaz veya yazamaz:
`.env`, `.git/config`, `id_rsa`, `credentials`, `secrets`, `.venv`,
`node_modules`, `backups`, `data/swimming_school.db`.

Yazma yalnızca `settings.developer_root_path` (mutlaklaştırılmış proje kökü)
altında ve izin verilen uzantılarda (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`,
`.json`, `.md`, `.css`, `.html` …) mümkündür.

### 10.5 Onay gerektiren işlemler

`REQUIRES_CONFIRMATION`: dosya silme, alembic migration, yama uygulama,
geri alma, 10'dan fazla dosyayı etkileyen değişiklik.

> **Ayrıntılı akış, prompt sözleşmesi, checkpoint/rollback mekaniği ve CAIO
> ajanının gözlem kuralları için bkz. [`docs/DEVELOPER_AGENT.md`](DEVELOPER_AGENT.md).**

---

## 11. Dağıtım Güvenlik Kontrol Listesi

Üretime (veya kurum içi gerçek kullanıma) çıkmadan önce sırayla uygulayın.

### 11.1 Sırlar ve yapılandırma

- [ ] `SECRET_KEY` üretildi ve `.env`'e yazıldı:
      `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] İlk kurulum parolası (`admin`) değiştirildi — sistem bunu zaten
      zorunlu kılar; onay kutusu, değişimin *yapıldığını* doğrulamak içindir
      (bkz. `SECURITY.md` > "İlk kurulum kimliği")
- [ ] İlk girişten sonra `admin@yuzmeokulu.local` hesabının parolası
      `POST /api/v1/auth/change-password` ile yenilendi
- [ ] `.env` dosyası yalnızca sunucu kullanıcısı tarafından okunabilir
      (Windows: dosya ACL; Linux: `chmod 600`)
- [ ] `git status` temiz — `.env`, `*.db`, `backups/` izlenmiyor
- [ ] `FINAL_CHECK.bat` çalıştırıldı ve **sır taraması PASS** verdi

### 11.2 Ortam

- [ ] `APP_ENV=production`
- [ ] `APP_DEBUG=false`
- [ ] `SEED_DEMO_DATA=false` (gerçek veriyle çalışılacaksa)
- [ ] `AI_DEVELOPER_ALLOW_APPLY=false` ve `AI_DEVELOPER_ALLOW_SHELL=false`
      (kod değişikliği yapılmayacak kurulumlarda `AI_DEVELOPER_ENABLED=false`)
- [ ] `AI_LOG_PROMPTS=false`
- [ ] `DATABASE_ECHO=false`
- [ ] `LOG_LEVEL=INFO` (veya `WARNING`), `LOG_JSON=true` (log toplama varsa)

### 11.3 Ağ ve taşıma

- [ ] Uygulama HTTPS arkasında sunuluyor (tersine vekil: nginx / IIS / Caddy)
- [ ] `Strict-Transport-Security` başlığının ulaştığı doğrulandı
      (`APP_ENV=production` gerektirir)
- [ ] `CORS_ORIGINS` yalnızca gerçek arayüz adresini içeriyor; `*` yok
- [ ] `APP_HOST=127.0.0.1` ile bağlanıp dışarıya yalnızca vekil üzerinden
      açıldı (doğrudan `0.0.0.0` bağlamaktan kaçının)
- [ ] SPA yolları için CSP başlığı vekil katmanında eklendi (bkz. 7.4)
- [ ] `/docs`, `/redoc` ve `/openapi.json` erişimi kurum içi ağla sınırlandı
      veya kapatıldı

### 11.4 Kimlik ve yetki

- [ ] Her personel kendi hesabıyla giriş yapıyor; paylaşımlı hesap yok
- [ ] Roller en az yetki ilkesine göre atandı (bkz. bölüm 3.3)
- [ ] `ai:developer` yalnızca sistem yöneticisinde
- [ ] `backup:restore` yalnızca `system_admin` ve `school_director`'da
- [ ] Ayrılan personelin hesabı `DELETE /api/v1/users/{id}` ile pasife alındı
- [ ] `RATE_LIMIT_ENABLED=true` doğrulandı

### 11.5 Veri ve yedek

- [ ] `BACKUP_SCHEDULE_ENABLED=true` ve `BACKUP_SCHEDULE_CRON` ayarlandı
- [ ] Saklama politikası belirlendi
      (`BACKUP_RETENTION_DAILY/WEEKLY/MONTHLY`)
- [ ] En az bir yedek `POST /api/v1/backup/{id}/verify` ile doğrulandı
- [ ] **Geri yükleme tatbikatı yapıldı** — yedek ayrı bir makinede açıldı
- [ ] Yedek klasörü ayrı bir fiziksel/ağ diskine kopyalanıyor
- [ ] Yedeklerin dosya sistemi izinleri kısıtlandı (yalnızca yöneticiler)

### 11.6 İzleme

- [ ] `logs/security.log` ve `logs/audit.log` düzenli inceleniyor
- [ ] `GET /api/v1/health` bir izleme aracıyla periyodik sorgulanıyor
- [ ] Disk doluluk uyarısı kuruldu (log + yedek büyümesi)
- [ ] `login_attempts` tablosu için saklama/temizleme planı yapıldı

### 11.7 Kod ve bağımlılık

- [ ] `FINAL_CHECK.bat` tüm kontrollerden geçti (lint, tip, 395 test fonksiyonu, sır
      taraması, bağımlılık denetimi)
- [ ] `pip-audit` bulguları incelendi
- [ ] `npm audit` bulguları incelendi
- [ ] Bağımlılıklar sabitlenmiş sürümlerle kuruldu

---

## 12. Güvenlik Açığı Bildirimi

### 12.1 Nasıl bildirilir

Bir güvenlik açığı bulduğunuzu düşünüyorsanız:

1. **Açığı herkese açık bir kanalda paylaşmayın** — genel issue, forum,
   sosyal medya veya ekran görüntüsü paylaşımı yapmayın.
2. Kurum içi bir kurulumsa doğrudan **sistem yöneticinize** bildirin.
3. Kaynak depo üzerinden çalışıyorsanız deponun **özel güvenlik bildirim
   kanalını** (GitHub: *Security → Report a vulnerability*) kullanın.
4. Bildiriminizde şunları paylaşın:
   - Etkilenen sürüm (`GET /api/v1/about` çıktısı) ve ortam (`APP_ENV`)
   - Yeniden üretme adımları (mümkünse en küçük örnek istek)
   - Beklenen ve gözlenen davranış
   - Etkinin sizce büyüklüğü (veri sızıntısı, yetki yükseltme, hizmet reddi …)
5. **Kişisel veri göndermeyin.** Ekran görüntüsü veya log paylaşacaksanız
   öğrenci/veli adlarını, e-postaları ve jetonları önce karartın.

### 12.2 Kapsam

**Kapsam içi:** kimlik doğrulama atlatma, yetki yükseltme, satır bazlı kapsam
ihlali (başkasının verisini görme), SQL enjeksiyonu, XSS, yol geçişi, sır
sızıntısı (log/API/yedek), AI ajanı politika atlatma, denetim kaydı manipülasyonu.

**Kapsam dışı (bilinen ve belgelenmiş davranışlar):**
- `SECRET_KEY` ayarlanmadığında oturumların yeniden başlatmada geçersiz olması
  (bölüm 2.4)
- Jeton iptal listesinin bulunmaması (bölüm 2.4)
- SPA yollarında CSP başlığının olmaması (bölüm 7.4)
- `APP_ENV=development` iken HSTS gönderilmemesi
- Varsayılan yönetici parolasının değiştirilmemesinden kaynaklanan erişim
- Yedekleme/geri yüklemenin yalnızca SQLite'ı desteklemesi
  (bkz. `CHANGELOG.md` → *Bilinen kısıtlamalar*)

### 12.3 Beklenen süreç

| Aşama | Hedef |
|-------|-------|
| Alındı bildirimi | 3 iş günü |
| İlk değerlendirme ve önem derecesi | 7 iş günü |
| Düzeltme veya azaltma planı | Önem derecesine göre |
| Yayın notunda duyuru | `CHANGELOG.md` → *Güvenlik* bölümü |

Bulgunuzu bildirdiğiniz için — isterseniz — sürüm notlarında teşekkür
edilecektir.

### 12.4 Sorumluluk reddi

Bu yazılım **MIT lisansı** ile, "olduğu gibi" (as-is), açık veya zımni hiçbir
garanti verilmeden dağıtılır (bkz. `LICENSE`). Kurum verilerinin güvenliği,
dağıtım yapılandırması, yedeklerin saklanması ve KVKK/GDPR yükümlülüklerinin
yerine getirilmesi sistemi kuran ve işleten kurumun sorumluluğundadır.

---

## İlgili belgeler

- Uç nokta referansı, hata biçimi ve örnekler: [`docs/API.md`](API.md)
- AI geliştirici ajanı ayrıntıları: [`docs/DEVELOPER_AGENT.md`](DEVELOPER_AGENT.md)
- Sürüm notları ve bilinen kısıtlamalar: [`CHANGELOG.md`](../CHANGELOG.md)
- Kaynak: `backend/app/core/security.py`, `backend/app/core/permissions.py`,
  `backend/app/api/deps.py`, `backend/app/core/exceptions.py`,
  `backend/app/core/logging_config.py`, `backend/app/services/audit.py`,
  `backend/app/services/ai/policy.py`
