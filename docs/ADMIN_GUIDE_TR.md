# Yönetici Kılavuzu (Sistem Yöneticisi / Müdür)

Bu kılavuz, Akıllı Yüzme Okulu Yönetim Sistemi'ni kuran, yapılandıran ve işleten sistem yöneticileri ile okul müdürleri içindir. Kurulum, kullanıcı ve rol yönetimi, yetkilendirme mantığı, istatistik ve denetim araçları, yedekleme, bakım ve güncelleme adımlarını gerçek dosya yolları ve uç noktalarla anlatır.

> Günlük operasyon (öğrenci kaydı, ders açma, yoklama, tahsilat) için: [USER_GUIDE_TR.md](USER_GUIDE_TR.md)

**Sürüm:** 0.9.0 · **Lisans:** MIT · **Veritabanı:** SQLite (PostgreSQL'e geçişe hazır) · **API:** 240 uç nokta, 55 tablo

---

## İçindekiler

| # | Bölüm | # | Bölüm |
|---|-------|---|-------|
| 1 | [Kurulum](#1-kurulum) | 9 | [Yedekleme Yönetimi](#9-yedekleme-yönetimi) |
| 2 | [İlk Kurulum Sihirbazı](#2-ilk-kurulum-sihirbazı-onboarding) | 10 | [Sistem Sağlığı](#10-sistem-sağlığı) |
| 3 | [Kullanıcı ve Rol Yönetimi](#3-kullanıcı-ve-rol-yönetimi) | 11 | [Eğitim Modu](#11-eğitim-modu) |
| 4 | [Yetkilendirme Mantığı](#4-yetkilendirme-mantığı) | 12 | [Demo Verisi](#12-demo-verisi) |
| 5 | [Kurum Ayarları](#5-kurum-ayarları) | 13 | [Bakım Görevleri](#13-bakım-görevleri) |
| 6 | [KPI Hedefleri Belirleme](#6-kpi-hedefleri-belirleme) | 14 | [Güncelleme Prosedürü](#14-güncelleme-prosedürü) |
| 7 | [İstatistik Merkezi](#7-i̇statistik-merkezi-kullanımı) | 15 | [Sorun Giderme](#15-sorun-giderme) |
| 8 | [Denetim Kaydı](#8-denetim-kaydı) | | |

---

## 1. Kurulum

### 1.1 Gereksinimler

| Bileşen | Asgari | Not |
|---------|--------|-----|
| İşletim sistemi | Windows 10 / 11 | Masaüstü başlatıcı WebView2 kullanır. |
| Python | 3.11+ | Kurulumda **"Add Python to PATH"** işaretlenmelidir. |
| Bellek | 4 GB | Yerel AI kullanılacaksa 16 GB+ önerilir. |
| Disk | 2 GB boş alan | Veritabanı, yedekler ve loglar için. |
| Node.js | 20+ | **Yalnızca** arayüzü kendiniz derleyecekseniz gerekir. |
| Edge WebView2 | Güncel Windows'ta kurulu gelir | Yoksa program varsayılan tarayıcıda açılır. |

Ağ bağlantısı yalnızca ilk kurulumda (bağımlılık indirme) ve bulut AI kullanılacaksa gereklidir. Sistem çevrimdışı çalışabilir.

### 1.2 İlk çalıştırma

Proje klasöründeki **`START_SWIMMING_SCHOOL.bat`** dosyasına çift tıklayın. Betik sırasıyla şunları yapar:

1. `.venv` sanal ortamı yoksa oluşturur, `backend/requirements.txt` ve `pywebview` paketlerini kurar.
2. `.env` dosyası yoksa `.env.example`'ı kopyalar ve `SECRET_KEY` alanını rastgele 64 baytlık bir değerle doldurur.
3. `backend` dizininde `alembic upgrade head` çalıştırır.
4. `frontend/dist/index.html` yoksa uyarı verir (arayüz derlenmemiş).
5. `desktop/launcher.py` ile programı başlatır: backend arka planda çalışır, sağlık kontrolü beklenir, pencere açılır.

Uygulama adresleri:

| Adres | İçerik |
|-------|--------|
| `http://127.0.0.1:8000` | Arayüz (derlenmişse) |
| `http://127.0.0.1:8000/docs` | Etkileşimli API dokümantasyonu (Swagger UI) |
| `http://127.0.0.1:8000/redoc` | Alternatif API dokümantasyonu |
| `http://127.0.0.1:8000/api/ping` | Basit canlılık kontrolü |

Arayüzü derlemek için bir kez **`BUILD_FRONTEND.bat`** çalıştırın.

**Geliştirme ortamı** için ayrı bir betik vardır:

```powershell
# Backend (uvicorn --reload, port 8000) + frontend (Vite, port 5173)
.\scripts\dev.ps1

# Yalnızca backend
.\scripts\dev.ps1 -BackendOnly
```

### 1.3 İlk yönetici hesabı

Uygulama her açılışta veritabanını hazırlar (idempotent): 21 rol kod tanımıyla senkronlanır, varsayılan ayarlar, KPI hedefleri ve paketler yoksa oluşturulur, yönetici hesabı yoksa açılır.

| Alan | Varsayılan |
|------|-----------|
| E-posta | `admin@yuzmeokulu.local` (`.env` → `FIRST_ADMIN_EMAIL`) |
| Parola | `.env` → `FIRST_ADMIN_PASSWORD` |
| Rol | Sistem Yöneticisi (`system_admin`), süper kullanıcı |
| İlk girişte parola değiştir | **Açık** |

> **İlk yapılacak iş:** giriş yapın ve *Ayarlar → Profil* sekmesinden parolayı değiştirin. `.env` dosyasındaki `FIRST_ADMIN_PASSWORD` değerini de gerçek bir değere çekin; bu değer yalnızca hesap **ilk kez** oluşturulurken kullanılır, sonradan değiştirmek mevcut parolayı etkilemez.

### 1.4 `.env` yapılandırması

`.env` dosyası proje kökündedir ve **asla sürüm kontrolüne alınmaz**. Tüm ayarlar buradan okunur; kaynak koda hiçbir sır gömülmez.

**Uygulama**

| Anahtar | Varsayılan | Açıklama |
|---------|-----------|----------|
| `APP_NAME` | Akıllı Yüzme Okulu Yönetim Sistemi | Pencere ve API başlığı. |
| `APP_ENV` | `development` | `development` \| `production` \| `test`. |
| `APP_DEBUG` | `true` | Üretimde `false`. |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `8000` | Dinlenen adres. |
| `APP_DEFAULT_LANGUAGE` | `tr` | Yeni hesapların varsayılan dili. |
| `APP_TIMEZONE` | `Europe/Istanbul` | |
| `APP_CURRENCY` | `TRY` | Varsayılan para birimi. |

**Güvenlik**

| Anahtar | Varsayılan | Açıklama |
|---------|-----------|----------|
| `SECRET_KEY` | otomatik üretilir | JWT imzalama anahtarı. **Değiştirilirse tüm oturumlar düşer.** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Erişim jetonu ömrü. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | Yenileme jetonu ömrü. |
| `JWT_ALGORITHM` | `HS256` | |
| `FIRST_ADMIN_EMAIL` | `admin@yuzmeokulu.local` | Yalnızca ilk kurulumda kullanılır. |
| `FIRST_ADMIN_PASSWORD` | – | Yalnızca ilk kurulumda kullanılır. |
| `RATE_LIMIT_ENABLED` | `true` | Giriş hız sınırı. |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Dakikada azami başarısız giriş denemesi. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Virgülle ayrılmış beyaz liste. |

Ayrıca kod düzeyinde sabit iki koruma vardır: **8 hatalı denemeden sonra 15 dakikalık hesap kilidi**.

**Veritabanı**

```dotenv
# SQLite (varsayılan)
DATABASE_URL=sqlite:///./data/swimming_school.db

# PostgreSQL'e geçiş örneği
# DATABASE_URL=postgresql+psycopg://kullanici:parola@localhost:5432/swimming_school

DATABASE_ECHO=false
```

Göreli SQLite yolları proje köküne göre mutlaklaştırılır; veritabanı dosyası `data/` klasöründe tutulur.

**Yapay zekâ**

| Anahtar | Varsayılan | Açıklama |
|---------|-----------|----------|
| `LOCAL_AI_ENABLED` | `true` | LM Studio yerel sağlayıcısı. |
| `LOCAL_AI_BASE_URL` | `http://localhost:1234/v1` | LM Studio → Developer → Start Server. |
| `LOCAL_AI_MODEL` | – | Boşsa servisin sunduğu model otomatik seçilir. |
| `LOCAL_AI_TIMEOUT` | `180` | Yerel modeller yavaş olabilir. |
| `NVIDIA_ENABLED` | `false` | Bulut sağlayıcı. |
| `NVIDIA_API_KEY` | – | `https://build.nvidia.com` üzerinden alınır. **Yalnızca `.env`'de tutulur.** |
| `NVIDIA_MODEL` | `meta/llama-3.3-70b-instruct` | |
| `OPENAI_COMPAT_*` | kapalı | Genel OpenAI uyumlu sağlayıcı. |
| `AI_FALLBACK_CHAIN` | `local,nvidia` | Sırayla denenir. |
| `AI_DEFAULT_MODE` | `automatic` | `local` \| `nvidia` \| `automatic`. |
| `AI_RESPONSE_LANGUAGE` | `auto` | Arayüz dilini takip eder. |
| `AI_LOG_PROMPTS` | `false` | **Gizlilik: üretimde `false` bırakın.** |

API anahtarları arayüzde **yalnızca maskeli** gösterilir (`nva************1234`) ve loglara, denetim kaydına, yedeklere **hiçbir zaman** düz metin yazılmaz.

**AI Developer Console**

| Anahtar | Varsayılan | Açıklama |
|---------|-----------|----------|
| `AI_DEVELOPER_ENABLED` | `true` | Konsolun açık olup olmadığı. |
| `AI_DEVELOPER_ALLOW_APPLY` | `false` | `true` olmadan yamalar uygulanamaz. |
| `AI_DEVELOPER_ALLOW_SHELL` | `false` | Kabuk komutlarına izin. |
| `AI_DEVELOPER_AUTO_TEST` | `true` | Yama sonrası testleri otomatik çalıştır. |
| `AI_DEVELOPER_ROOT` | `.` | Ajanın yazabileceği kök dizin; dışına çıkamaz. |

> Üretim kurulumlarında `AI_DEVELOPER_ALLOW_APPLY` ve `AI_DEVELOPER_ALLOW_SHELL` değerlerini `false` bırakın.

**Yedekleme, loglama, demo**

| Anahtar | Varsayılan | Açıklama |
|---------|-----------|----------|
| `BACKUP_DIR` | `./backups` | |
| `BACKUP_SCHEDULE_ENABLED` | `false` | Zamanlanmış yedekleme. |
| `BACKUP_SCHEDULE_CRON` | `0 23 * * *` | Her gün 23:00. |
| `BACKUP_RETENTION_DAILY/WEEKLY/MONTHLY` | `7` / `4` / `12` | Saklama politikası. |
| `LOG_DIR` | `./logs` | |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`. |
| `LOG_JSON` | `false` | `true` ise satır başına JSON. |
| `SEED_DEMO_DATA` | `true` | **Üretimde `false` yapın.** |

`.env` değişiklikleri **uygulama yeniden başlatıldığında** geçerli olur.

### 1.5 Veritabanı migration

Migration komutları `backend` dizininden çalıştırılır:

```powershell
# Şemayı en güncel sürüme getir
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head

# Mevcut revizyonu göster
..\.venv\Scripts\python.exe -m alembic current

# Model ile şema arasında fark var mı?
..\.venv\Scripts\python.exe -m alembic check
Pop-Location
```

`START_SWIMMING_SCHOOL.bat` her açılışta `upgrade head` çalıştırdığı için normal kullanımda bu komutları elle girmenize gerek yoktur. Migration uygulanamazsa betik uyarı verir ama programı yine de başlatır — bu durumda logu inceleyin (bölüm 15).

**Migration öncesi mutlaka yedek alın** (bölüm 9).

### 1.6 Üretim kurulumu kontrol listesi

- [ ] `APP_ENV=production`, `APP_DEBUG=false`
- [ ] `SECRET_KEY` benzersiz ve uzun
- [ ] `FIRST_ADMIN_PASSWORD` değiştirildi ve yönetici parolası ilk girişte güncellendi
- [ ] `SEED_DEMO_DATA=false`, veritabanında demo kayıt yok
- [ ] `AI_LOG_PROMPTS=false`
- [ ] `AI_DEVELOPER_ALLOW_APPLY=false`, `AI_DEVELOPER_ALLOW_SHELL=false`
- [ ] `BACKUP_SCHEDULE_ENABLED=true` ve yedek klasörü ayrı bir diskte/paylaşımda
- [ ] `CORS_ORIGINS` yalnızca gerçek kullanılan adresleri içeriyor
- [ ] `FINAL_CHECK.bat` başarıyla tamamlanıyor

---

## 2. İlk Kurulum Sihirbazı (Onboarding)

Hesabında kurulum sihirbazı tamamlanmamış bir kullanıcı giriş yaptığında doğrudan **Kurulum Sihirbazı** ekranına yönlendirilir. Sihirbaz 9 adımdan oluşur ve **tamamlanma durumu gerçek veriden okunur** — adımı "yaptım" diye işaretlemeniz yetmez, ilgili kayıt gerçekten var mı diye bakılır.

| # | Adım | Gittiği ekran | "Tamamlandı" sayılma koşulu |
|---|------|---------------|------------------------------|
| 1 | **Kurum Bilgileri** | `/settings?tab=general` | Kurum adı girilmiş **ve** varsayılan "Akıllı Yüzme Okulu" değerinden farklı. |
| 2 | **İlk Yönetici** | `/settings?tab=profile` | Kullanıcının "ilk girişte parola değiştir" işareti kalkmış (parola değiştirilmiş). |
| 3 | **Havuz Oluştur** | `/pools?action=new` | Sistemde en az bir havuz var. |
| 4 | **Kulvarları Tanımla** | `/pools` | Havuz oluşturulduğunda birlikte tamamlanmış sayılır. |
| 5 | **İlk Eğitmeni Ekle** | `/instructors?action=new` | En az bir eğitmen kaydı var. |
| 6 | **İlk Öğrenciyi Ekle** | `/students?action=new` | En az bir öğrenci kaydı var. |
| 7 | **AI Ayarları** (isteğe bağlı) | `/ai` | Yerel **veya** NVIDIA sağlayıcısı etkin. |
| 8 | **Backup Ayarları** | `/settings?tab=backup` | Zamanlanmış yedekleme açık **veya** en az bir yedek kaydı var. |
| 9 | **Kurulumu Tamamla** | `/training` | Kullanıcı "Tamamla" veya "Şimdilik Geç" dedi. |

**Şimdilik Geç:** sihirbazı kapatır ve kullanıcıyı normal arayüze bırakır. Eksik adımlar daha sonra Eğitim Merkezi'nden tamamlanabilir; sihirbaz bir daha zorlamaz.

Önerilen sıra: kurum bilgileri → yönetici parolası → havuz ve kulvarlar → eğitmenler → gruplar → paketler → öğrenciler → ders programı → yedekleme.

---

## 3. Kullanıcı ve Rol Yönetimi

Tüm işlemler *Ayarlar → Kullanıcılar* sekmesindedir (yetki: `user:read` / `user:write`).

### 3.1 Kullanıcı ekleme

1. *Ayarlar → Kullanıcılar* → **Yeni Kullanıcı**.
2. Alanlar:

| Alan | Zorunlu | Açıklama |
|------|:-------:|----------|
| E-posta | ✔ | Benzersiz olmalı; giriş adı olarak kullanılır. |
| Ad Soyad | ✔ | |
| Parola | ✔ | Politika: **en az 8 karakter**, en az bir harf, en az bir rakam; `password`, `123456789`, `admin123`, `parola123` gibi yaygın parolalar reddedilir. |
| Telefon | – | |
| Dil | – | `tr` / `en`. |
| Roller | – | Birden fazla rol seçilebilir; izinler **birleşim** olarak uygulanır. |
| Aktif | ✔ (varsayılan) | |
| **İlk girişte parola değiştir** | – | Yeni personel için işaretleyin. |

3. **Kaydet**. İşlem denetim kaydına yazılır.

Personel için ayrıca bir **Eğitmen** kaydı açıp kullanıcıya bağlarsanız, eğitmen kapsamlı roller (bkz. bölüm 4) kendi derslerini görebilir.

### 3.2 Rol atama ve değiştirme

Kullanıcı satırında **Düzenle** → **Roller**. Rol değiştirmek için `role:manage` yetkisi (veya süper kullanıcı olmak) gerekir; `user:write` yetkisi tek başına rol değiştirmeye yetmez. Rol değişikliği denetim kaydına "önceki roller → yeni roller" olarak işlenir.

Roller ve izin kümeleri **kod tanımının otoritesindedir**: uygulama her açılışta sistem rollerinin izinlerini kod tanımıyla yeniden senkronlar. Yani veritabanından elle değiştirilen bir sistem rolü, yeniden başlatmada eski hâline döner. Bu, sürüm yükseltmelerinde yeni izinlerin otomatik yayılmasını sağlar.

### 3.3 21 rol ve eriştiği alanlar

| # | Rol kodu | Etiket | Ne yapabilir |
|---|----------|--------|--------------|
| 1 | `system_admin` | Sistem Yöneticisi | **Tüm 52 izin.** Kullanıcı/rol yönetimi, ayarlar, yedekleme + geri yükleme, denetim kaydı, AI yapılandırması, AI Developer Console, CAIO. |
| 2 | `school_director` | Yüzme Okulu Müdürü | AI Developer Console, rol yönetimi ve kullanıcı silme **dışında her şey**. Yedek geri yükleme ve CAIO dâhil. |
| 3 | `operations_manager` | Operasyon Müdürü | Öğrenci/veli/eğitmen okuma-yazma, havuz yönetimi ve bakımı, ders yazma-planlama-silme, yoklama, üyelik, **finans salt okunur**, performans, yarışma, rapor + dışa aktarma, istatistik, KPI hedefi, bildirim gönderme, ayar okuma, yedek alma, sistem sağlığı. |
| 4 | `finance` | Finans / Muhasebe | Öğrenci/veli/eğitmen salt okunur; üyelik okuma-yazma; **finans okuma-yazma-silme**; rapor + dışa aktarma; istatistik. |
| 5 | `hr` | İnsan Kaynakları | Eğitmen okuma-yazma-**silme**; **kullanıcı okuma-yazma**; ders ve yoklama salt okunur; rapor + dışa aktarma; istatistik. |
| 6 | `reception` | Resepsiyon | Öğrenci/veli okuma-yazma; eğitmen ve havuz salt okunur; ders okuma-yazma-planlama; yoklama okuma-yazma; üyelik okuma-yazma; **finans okuma-yazma**; rapor okuma. |
| 7 | `sales_marketing` | Satış / Pazarlama | Öğrenci/veli okuma-yazma; üyelik okuma-yazma; finans salt okunur; rapor + dışa aktarma; istatistik; **bildirim gönderme**. |
| 8 | `head_coach` | Baş Antrenör | Eğitmen tabanı + eğitmen yazma, ders yazma-planlama-silme, yarışma yazma, rapor dışa aktarma, KPI hedefi, öğrenci yazma, **hassas öğrenci verisi**, bildirim gönderme. |
| 9 | `swim_coach` | Yüzme Antrenörü | Eğitmen tabanı + ders yazma + yarışma yazma. |
| 10 | `swim_instructor` | Yüzme Eğitmeni | **Eğitmen tabanı**: öğrenci/veli/eğitmen/havuz/ders okuma, yoklama okuma-yazma, performans okuma-yazma, yarışma okuma, rapor okuma, istatistik, AI kullanımı. |
| 11 | `kids_instructor` | Çocuk Yüzme Eğitmeni | Eğitmen tabanı. |
| 12 | `baby_instructor` | Bebek Yüzme Eğitmeni | Eğitmen tabanı. |
| 13 | `private_instructor` | Özel Ders Eğitmeni | Eğitmen tabanı. |
| 14 | `adaptive_instructor` | Adaptif Yüzme Eğitmeni | Eğitmen tabanı + **hassas öğrenci verisi** (sağlık notu, özel ihtiyaç). |
| 15 | `conditioning_coach` | Kondisyon / Performans Antrenörü | Eğitmen tabanı. |
| 16 | `lifeguard` | Cankurtaran | Öğrenci, veli, eğitmen, havuz, ders ve yoklama **salt okunur**. |
| 17 | `pool_technician` | Havuz Teknik Personeli | Havuz okuma-yazma-**bakım**, ders salt okunur, **sistem sağlığı** ekranı. |
| 18 | `medical_staff` | Sağlık / İlk Yardım Personeli | Öğrenci okuma + **hassas veri**, veli/ders/yoklama salt okunur, bildirim gönderme. |
| 19 | `athlete` | Sporcu | **Yalnızca kendi verisi**: ders, yoklama, performans, yarışma, bildirim. |
| 20 | `student` | Öğrenci | **Yalnızca kendi verisi**: ders, yoklama, performans, bildirim. |
| 21 | `parent` | Veli | **Yalnızca çocuklarının verisi**: ders, yoklama, performans, üyelik, finans, bildirim. |

Roller arayüzde üç grupta listelenir: **Yönetim** (1–7), **Eğitim** (8–15), **Diğer** (16–21).

**Rol seçimi önerileri**

| Görev | Önerilen rol(ler) |
|-------|-------------------|
| Ön büro / danışma | `reception` |
| Muhasebe | `finance` |
| Program ve tesis sorumlusu | `operations_manager` |
| Antrenör ekibi başı | `head_coach` |
| Ders veren eğitmen | Uzmanlığına uygun eğitmen rolü |
| Havuz teknisyeni | `pool_technician` |
| Veli hesabı | `parent` (veli kaydı oluşturulurken "portal kullanıcısı oluştur" ile otomatik açılabilir) |

Aynı kişiye birden fazla rol verilebilir; izinler toplanır. Örneğin resepsiyon + satış rolü olan bir kullanıcı her ikisinin izinlerine sahiptir.

### 3.4 Parola sıfırlama

*Ayarlar → Kullanıcılar* → kullanıcı satırı → **Parola Sıfırla**:

1. Yeni parolayı girin (aynı parola politikası geçerlidir).
2. **"İlk girişte parola değiştirsin"** kutusunu işaretli bırakın (varsayılan).
3. Onaylayın.

İşlem sonucunda:

- kullanıcının parolası değişir,
- **başarısız giriş sayacı sıfırlanır ve hesap kilidi kaldırılır**,
- işlem denetim kaydına `reset_password` olarak yazılır.

Yeni parolayı kullanıcıya güvenli bir kanaldan iletin; sistem parola e-postası göndermez.

### 3.5 Devre dışı bırakma

**Sil** işlemi kullanıcıyı **silmez, devre dışı bırakır** (`is_active = false`):

- kullanıcı artık giriş yapamaz,
- geçmiş denetim kayıtları, işlem izleri ve ilişkili veriler korunur,
- gerektiğinde **Düzenle → Aktif** ile hesap yeniden açılabilir.

Kendi hesabınızı devre dışı bırakamazsınız; sistem bunu engeller. Bu işlem `user:delete` yetkisi ister (varsayılan olarak yalnızca `system_admin`).

**Personel ayrıldığında yapılacaklar:**

1. Kullanıcı hesabını devre dışı bırakın.
2. İlgili **Eğitmen** kaydını pasife alın.
3. Gelecekteki ders atamalarını başka bir eğitmene aktarın (ders başına düzenleme veya iptal + yeniden oluşturma).
4. Denetim kaydından son işlemlerini gözden geçirin.

---

## 4. Yetkilendirme Mantığı

### 4.1 Model

```
Kullanıcı ──(çoktan çoğa)── Rol ──(izin kümesi)── İzin kodu
```

- İzinler `kaynak:eylem` biçimindedir (örn. `student:read`, `finance:write`).
- Bir kullanıcı birden fazla role sahip olabilir; **efektif izin kümesi rollerin birleşimidir**.
- **Süper kullanıcı** (`is_superuser`) tüm izin denetimlerinden muaftır.
- Yetkisi olmayan kullanıcı için menü öğesi **hiç görünmez**; adresi elle yazsa bile "erişim reddedildi" ekranı gelir. Backend ayrıca isteği reddeder — arayüz gizlemesi tek başına güvenlik sayılmaz.

Yetki hatası döndüğünde yanıt, hangi iznin gerektiğini ve hangisinin eksik olduğunu içerir.

### 4.2 52 izin kodu

| Kaynak | İzinler | Ne sağlar |
|--------|---------|-----------|
| `student` | `read`, `write`, `delete`, **`read_sensitive`** | Öğrenci kayıtları; `read_sensitive` sağlık notu ve özel ihtiyaç alanlarını açar. |
| `guardian` | `read`, `write`, `delete` | Veli kayıtları. |
| `instructor` | `read`, `write`, `delete` | Eğitmen kayıtları, sertifika, müsaitlik, izin. |
| `pool` | `read`, `write`, `delete`, `maintenance` | Havuz ve kulvarlar; `maintenance` bakım ve su kalitesi kaydı. |
| `lesson` | `read`, `write`, `delete`, `schedule` | Dersler; `schedule` tekrarlanan seri ve saat önerisi. |
| `attendance` | `read`, `write` | Yoklama. |
| `membership` | `read`, `write`, `delete` | Üyelik ve paketler. |
| `finance` | `read`, `write`, `delete` | Ödeme, fatura, gider, indirim. |
| `performance` | `read`, `write` | Derece kayıtları ve analiz. |
| `competition` | `read`, `write` | Yarışma, etkinlik, seri, sonuç. |
| `report` | `read`, `export` | Rapor çalıştırma ve dosya olarak dışa aktarma. |
| `statistics` | `read` | İstatistik merkezi. |
| `kpi` | `write` | KPI hedefi belirleme. |
| `ai` | `use`, `configure`, `developer`, `caio` | AI analizleri; sağlayıcı yapılandırması; geliştirici konsolu; CAIO denetimi. |
| `user` | `read`, `write`, `delete` | Kullanıcı yönetimi. |
| `role` | `manage` | Rol atama. |
| `settings` | `read`, `write` | Sistem ayarları. |
| `audit` | `read` | Denetim kaydı. |
| `backup` | `read`, `create`, `restore` | Yedek listeleme, alma, geri yükleme. |
| `notification` | `read`, `send` | Bildirim okuma ve gönderme. |
| `system` | `health` | Sistem sağlığı ekranı. |
| `self` | `portal` | Kendi verisine erişim (portal). |

Tüm kodların listesini API'den de alabilirsiniz:

```http
GET /api/v1/users/permissions
Authorization: Bearer <erişim jetonu>
```

Yanıt hem düz listeyi hem de kaynak bazında gruplanmış hâlini döndürür (yetki: `role:manage`).

### 4.3 Satır bazlı erişim kapsamı

İzinler "hangi ekranı açabilirsin" sorusunu yanıtlar; **satır bazlı kapsam** ise "o ekranda hangi kayıtları görürsün" sorusunu yanıtlar. Kapsam veritabanı sorgusuna eklenir; arayüzde gizleme değil, veri düzeyinde filtrelemedir.

**Yönetici kapsamı (kısıt yok)**

Süper kullanıcı veya `system_admin`, `school_director`, `operations_manager` rollerinden birine sahip kullanıcılar tüm kayıtları görür.

**Kendi verisi kapsamı (`self`)**

`athlete`, `student`, `parent` rollerinden birine sahip **ve** `student:write` izni olmayan kullanıcılar bu kapsamdadır:

- Kendi öğrenci kaydını görür.
- Veli ise **bağlı olduğu tüm öğrencileri** görür.
- Hiçbir eşleşme yoksa **hiçbir kayıt dönmez** (boş liste) — "yanlışlıkla her şeyi gösterme" durumu oluşmaz.

Bu kapsam öğrenci listesi, arama sonuçları, yoklama kayıtları, ödemeler ve devam özeti gibi uçlarda uygulanır.

**Eğitmen kapsamı**

`swim_coach`, `swim_instructor`, `kids_instructor`, `baby_instructor`, `private_instructor`, `adaptive_instructor`, `conditioning_coach` rolleri eğitmen kapsamındadır: öncelikli olarak kendi dersleri ve o derslerdeki öğrencilerle çalışırlar.

**Hassas alanlar**

- `student:read_sensitive` izni olmayan kullanıcıya sağlık notu ve özel ihtiyaç alanları **döndürülmez** (boş gelir).
- **Maaş/ücret bilgisi** yalnızca `system_admin`, `school_director`, `finance`, `hr` rollerine (veya süper kullanıcıya) açıktır.

### 4.4 Yetkilendirmeyi doğrulama

Bir rolün gerçekten neye eriştiğini test etmenin en güvenilir yolu, o rolde bir test hesabı açıp giriş yapmaktır. Kontrol edilecekler:

1. Sol menüde hangi başlıklar görünüyor?
2. Yetkisiz bir adresi elle yazınca "erişim reddedildi" geliyor mu?
3. Listelerde beklenenden fazla kayıt görünüyor mu (kapsam sızıntısı)?
4. Hassas alanlar gizli mi?

Test hesabını iş bittiğinde devre dışı bırakın.

---

## 5. Kurum Ayarları

*Ayarlar → Genel* sekmesi (yetki: `settings:read` görüntüleme, `settings:write` düzenleme).

| Alan | Anahtar | Etkisi |
|------|---------|--------|
| Kurum adı | `name` | Arayüz başlıkları, rapor üst bilgileri, PDF çıktıları. |
| Logo adresi | `logo_url` | Rapor ve arayüz logosu. |
| Telefon / E-posta / Adres / Web sitesi | `phone`, `email`, `address`, `website` | Rapor alt bilgileri, iletişim listeleri. |
| Vergi dairesi / Vergi numarası | `tax_office`, `tax_number` | Fatura çıktıları. |
| **Para birimi** | `currency` | Tüm ekranlardaki tutar biçimlendirmesini **anında** değiştirir; ekran ekran düzenleme gerekmez. |
| **Dil** | `language` | Kurumun varsayılan dili (`tr`/`en`). Kullanıcı kendi tercihini ayrıca belirleyebilir. |
| **Saat dilimi** | `timezone` | Varsayılan `Europe/Istanbul`. |
| **Tarih biçimi** | `date_format` | Varsayılan `DD.MM.YYYY`. |

### 5.1 Operasyon ayarları

Genel sekmesinin altındaki kategorilerde davranışsal ayarlar bulunur:

**Yoklama** (`attendance`)

| Ayar | Varsayılan | Etkisi |
|------|-----------|--------|
| Geç kalma eşiği (dakika) | `10` | QR/kart ile girişte bu süreden sonra gelen "Geç Geldi" işaretlenir. |
| Otomatik ders hakkı düşümü | `true` | Yoklama ekranındaki kutunun varsayılan durumu. |
| Telafiye izin ver | `true` | Telafi dersi atama özelliği. |
| Telafi penceresi (gün) | `30` | Telafi tanımlanabilecek süre. |

**Üyelik** (`membership`)

| Ayar | Varsayılan | Etkisi |
|------|-----------|--------|
| Bitiş uyarı süresi (gün) | `14` | "Süresi dolacak üyelikler" listesi ve bildirim eşiği. |
| Düşük ders hakkı uyarısı | `2` | "Ders hakkı azalanlar" listesinin eşiği. |

**Finans** (`finance`)

| Ayar | Varsayılan | Etkisi |
|------|-----------|--------|
| Gecikme toleransı (gün) | `3` | Vadeden sonra kaç gün "gecikmiş" sayılmaz. |
| Vergi oranı | `0` | Fatura hesabı. |
| Fatura ön eki | `FT` | Fatura numarası biçimi. |

### 5.2 Değişikliklerin izlenmesi

Her ayar değişikliği denetim kaydına **"önceki değer → yeni değer"** biçiminde yazılır. Kim, ne zaman, hangi ayarı değiştirdi sorusu *Ayarlar → Denetim Kaydı* ekranından yanıtlanır.

Ayarları API üzerinden okumak/yazmak:

```http
GET /api/v1/settings                 # tüm ayarlar (gizli olanlar hariç)
GET /api/v1/settings/organization    # tek ayar
PUT /api/v1/settings                 # güncelleme (settings:write)
```

---

## 6. KPI Hedefleri Belirleme

*İstatistikler → KPI* sekmesi (hedef belirleme yetkisi: `kpi:write`).

### 6.1 Gösterge listesi

Sistem 11 göstergeyi her dönem için hesaplar:

| Gösterge | Birim | Yön | Nasıl hesaplanır |
|----------|-------|-----|------------------|
| Aktif Öğrenci | adet | Yüksek iyi | Durumu "Aktif" olan öğrenci sayısı. |
| Aylık Yeni Öğrenci | adet | Yüksek iyi | Dönemdeki yeni kayıtlar (önceki dönemle karşılaştırılır). |
| Öğrenci Tutundurma | % | Yüksek iyi | Dönem sonunda hâlâ aktif olan öğrenci oranı. |
| Devam Oranı | % | Yüksek iyi | Geldi + geç geldi + telafi / toplam yoklama. |
| Havuz Doluluk | % | Yüksek iyi | Kullanılan kulvar-dakika / kapasite. |
| Kulvar Doluluk | % | Yüksek iyi | Kulvar bazlı doluluk. |
| Aylık Gelir | para | Yüksek iyi | Net tahsilat (iadeler düşülmüş). |
| Öğrenci Başına Gelir | para | Yüksek iyi | Net tahsilat / aktif öğrenci. |
| Bekleyen Tahsilat | para | **Düşük iyi** | Kapanmamış fatura bakiyeleri toplamı. |
| Tahsilat Oranı | % | Yüksek iyi | Tahsil edilen / faturalanan. |
| Ortalama Performans Gelişimi | % | Yüksek iyi | Dönemde derecesi iyileşen sporcuların ortalama gelişimi. |

### 6.2 Varsayılan hedefler

Kurulumla birlikte beş hedef tanımlanır:

| Gösterge | Varsayılan hedef |
|----------|-----------------:|
| Devam Oranı | %90 |
| Havuz Doluluk | %80 |
| Tahsilat Oranı | %95 |
| Öğrenci Tutundurma | %85 |
| Kulvar Doluluk | %75 |

Diğer göstergelerde hedef tanımlı değildir; hedef girilmezse gösterge "nötr" olarak gösterilir ve renklendirilmez.

### 6.3 Hedef belirleme ve okuma

1. *İstatistikler → KPI* sekmesini açın.
2. Gösterge satırındaki **Hedef** alanına değeri girin ve kaydedin.
3. Sistem gerçekleşen değeri hedefle karşılaştırıp **gerçekleşme yüzdesi** üretir.

Renk kuralı:

| Durum | Koşul | Anlamı |
|-------|-------|--------|
| 🟢 İyi | gerçekleşme ≥ %100 | Hedef tutturuldu. |
| 🟡 Uyarı | %85 ≤ gerçekleşme < %100 | Hedefe yakın; izlenmeli. |
| 🔴 Kötü | gerçekleşme < %85 | Müdahale gerekiyor. |
| ⚪ Nötr | hedef tanımlı değil | Yalnızca ölçüm gösterilir. |

**"Düşük iyi" göstergelerde** (Bekleyen Tahsilat) hesap ters çevrilir: hedefin altında kalmak başarıdır.

Hedef belirlerken gerçekçi olun: geçmiş 3 ayın gerçekleşen değerine bakıp %5–10 iyileştirme hedefi koymak, ulaşılamayan bir hedefin göstergeyi sürekli kırmızı göstermesinden daha yararlıdır. Hedef değişiklikleri denetim kaydına yazılır.

---

## 7. İstatistik Merkezi Kullanımı

*İstatistikler* ekranı (`/statistics`, yetki: `statistics:read`). Buradaki tüm sayılar **veritabanından hesaplanır**; yapay zekâ tahmini içermez.

### 7.1 Dönem seçimi

Tüm sekmeler ortak dönem seçicisini kullanır:

| Seçenek | Kapsadığı aralık |
|---------|------------------|
| Bugün | Bugün |
| Bu hafta | Pazartesi–Pazar |
| Bu ay | Ayın 1'i – bugün |
| Bu çeyrek | Çeyrek başı – bugün |
| Son 6 ay | Bugünden 182 gün geriye |
| Bu yıl | 1 Ocak – bugün |
| Geçen yıl | Önceki yılın tamamı |
| Özel aralık | Girdiğiniz başlangıç ve bitiş tarihi |

Sistem, seçilen dönemi **aynı uzunluktaki önceki dönemle** otomatik karşılaştırır; değişim yüzdeleri bu karşılaştırmadan gelir.

### 7.2 Sekmeler

| Sekme | İçerik |
|-------|--------|
| **Öğrenci** | Aktif/pasif dağılımı, yeni kayıt ve ayrılma sayıları, seviye ve yaş dağılımı, tutundurma oranı. |
| **Eğitmen** | Eğitmen başına ders sayısı, toplam saat, doluluk, öğrenci sayısı. |
| **Havuz** | Havuz ve kulvar doluluğu, saatlik yük, **yoğunluk haritası**. |
| **Yoklama** | Durum kırılımı (geldi/gelmedi/geç/mazeretli/iptal/telafi), devam oranı ve eğilim. |
| **KPI** | 11 gösterge, hedefler ve gerçekleşme (bölüm 6). |
| **Gelişmiş** | Cohort analizi, devam aykırı değerleri, devam–performans korelasyonu, dağılım analizleri. |

### 7.3 Yoğunluk haritasını okuma

Havuz sekmesindeki ısı haritası **gün × saat** ızgarasında doluluğu gösterir: koyu hücre yoğun, açık hücre boş saat demektir.

Nasıl kullanılır:

1. **Koyu bloklar** — kapasite sınırına yaklaşan saatler. Buralarda yeni ders açmak çakışma ve kalabalık riski taşır; kulvar planından boş kulvar olup olmadığını doğrulayın.
2. **Açık bloklar** — atıl kapasite. Kampanya, deneme dersi veya yetişkin grupları için hedeflenecek saatler bunlardır.
3. **Gün karşılaştırması** — bir günün tamamı açıksa o gün için program ya da personel planlaması gözden geçirilmelidir.
4. Isı haritasını **Havuz Kullanım Raporu** ile birlikte okuyun; rapor aynı veriyi sayısal olarak verir ve dışa aktarılabilir.

### 7.4 Cohort (tutundurma) analizi

Cohort analizi, **aynı ay kaydolan öğrencilerin kaç ay sonra hâlâ aktif olduğunu** gösterir. Varsayılan 12 ay; 3 ile 24 ay arasında ayarlanabilir.

Tablo okuma:

- **Satır** = kayıt ayı (cohort). Örn. "2026-03" satırı, Mart 2026'da kaydolanlar.
- **Sütun** = kayıttan sonraki ay sayısı (0, 1, 2, …).
- **Hücre** = o ay hâlâ aktif olan öğrenci oranı.

Ne aranmalı:

| Gözlem | Yorum |
|--------|-------|
| İlk 1–2 ayda sert düşüş | Karşılama/uyum süreci sorunlu; deneme dersi sonrası takip zayıf olabilir. |
| Belirli bir cohort'un diğerlerinden kötü olması | O dönemdeki kampanya, eğitmen değişikliği veya program değişikliği araştırılmalı. |
| Genelde yatay seyir | Sağlıklı tutundurma. |
| 3. aydan sonra düşüş | Paket bitişleriyle örtüşüyor olabilir; yenileme görüşmelerinin zamanlamasını öne çekin. |

Cohort analizi, "Öğrenci Tutundurma" KPI'sinin arkasındaki ayrıntıyı verir; KPI tek sayı, cohort ise o sayının nereden geldiğidir.

### 7.5 Korelasyon uyarısı

Gelişmiş sekmesindeki **devam–performans korelasyonu**, öğrencilerin devam oranı ile derece gelişimi arasındaki ilişkiyi ölçer (varsayılan son 180 gün). Hesaba yalnızca yeterli veriye sahip öğrenciler dâhil edilir: **en az 5 yoklama kaydı ve en az 3 performans kaydı**.

> **Korelasyon nedensellik değildir.** Yüksek bir korelasyon "devam ettikçe hızlanır" demek değildir; her iki değişkeni birlikte etkileyen üçüncü bir etken (motivasyon, yaş grubu, eğitmen, antrenman hacmi) olabilir. Sonucu bir **hipotez** olarak alın, karar gerekçesi olarak değil.

Ayrıca:

- **Devam aykırı değerleri** — istatistiksel olarak gruptan belirgin biçimde sapan devam oranına sahip öğrenciler. Hem çok düşük hem çok yüksek uçlar listelenir; düşük uçlar görüşme, yüksek uçlar başarı örneği için kullanılabilir.
- **Dağılım analizleri** — `student_age` (yaş), `attendance_rate` (devam oranı), `lesson_occupancy` (ders doluluğu) metrikleri için ortalama, medyan, standart sapma ve histogram.

Örnek çağrı:

```http
GET /api/v1/statistics/correlation/attendance-performance?days=180
GET /api/v1/statistics/distribution/student_age?days=180
GET /api/v1/statistics/cohort?months=12
Authorization: Bearer <erişim jetonu>
```

---

## 8. Denetim Kaydı

*Ayarlar → Denetim Kaydı* sekmesi (yetki: `audit:read`). Kullanıcı menüsünden de doğrudan erişilir.

### 8.1 Ne kaydedilir?

Her kayıtta şu alanlar bulunur: **kullanıcı**, **kullanıcı e-postası**, **işlem**, **kayıt türü**, **kayıt kimliği**, **özet**, **değişiklikler**, **IP adresi**, **zaman**.

Kaydedilen işlem türlerinden bazıları:

| İşlem | Ne zaman |
|-------|----------|
| `login` | Başarılı giriş. |
| `create` / `update` | Kayıt oluşturma ve güncelleme (öğrenci, ders, kullanıcı, ayar, üyelik, ödeme…). |
| `soft_delete` / `delete` | Pasife alma ve kalıcı silme. |
| `deactivate` | Kullanıcı devre dışı bırakma. |
| `change_password` | Kullanıcının kendi parolasını değiştirmesi. |
| `reset_password` | Yönetici tarafından parola sıfırlama. |
| `record_attendance` | Yoklama kaydı (ders ve öğrenci sayısıyla). |
| `assign_makeup` | Telafi dersi atama. |
| `notify` | Bildirim gönderme. |

**Değişiklikler** alanı `{"alan": {"from": eski, "to": yeni}}` biçimindedir; ayar ve kullanıcı güncellemelerinde neyin değiştiği tam olarak görülür.

**Maskeleme:** parola, parola özeti, API anahtarı, jeton ve `secret`/`password` içeren tüm alanlar `***` olarak yazılır. 500 karakteri aşan metinler kısaltılır. Denetim kaydına hiçbir koşulda sır yazılmaz.

**Atomiklik:** denetim kaydı, ilgili iş verisiyle **aynı veritabanı işleminde** yazılır. İş kaydı geri alınırsa denetim kaydı da geri alınır; "işlem olmadı ama kaydı var" durumu oluşmaz.

Denetim kayıtları ayrıca `logs/audit.log` dosyasına da yazılır.

### 8.2 Filtreleme

Ekrandaki filtreler:

| Filtre | Açıklama |
|--------|----------|
| Kullanıcı | Belirli bir kullanıcının işlemleri. |
| İşlem türü | `create`, `update`, `delete`, `login`… |
| Kayıt türü | `student`, `lesson`, `user`, `app_setting`, `attendance`… |
| Kayıt kimliği | Tek bir kaydın tüm geçmişi. |
| Gün aralığı | **Varsayılan son 30 gün.** |

API üzerinden:

```http
GET /api/v1/audit?entity_type=student&entity_id=42&days=90&page=1&page_size=50
Authorization: Bearer <erişim jetonu>
```

### 8.3 Tipik kullanım senaryoları

| Soru | Nasıl bulunur |
|------|---------------|
| "Bu öğrencinin seviyesini kim değiştirdi?" | Kayıt türü `student`, kayıt kimliği = öğrenci id. |
| "Çakışmalı ders kim tarafından zorlandı?" | Kayıt türü `lesson`, özet metninde çakışma notu. |
| "Ayarı kim bozdu?" | Kayıt türü `app_setting`; değişiklikler alanında eski/yeni değer. |
| "Silinen ödeme neydi?" | Kayıt türü `payment`, işlem `delete`. |
| "Kim ne zaman giriş yaptı?" | İşlem `login`. Başarısız denemeler `logs/security.log` dosyasındadır. |

---

## 9. Yedekleme Yönetimi

> Ayrıntılı adımlar, doğrulama kontrolleri, geri yükleme akışı ve felaket kurtarma senaryoları için: **[BACKUP_RESTORE_TR.md](BACKUP_RESTORE_TR.md)**

### 9.1 Özet

- **Yedek biçimi:** ZIP arşivi + `backup_manifest.json` + SHA-256 sağlaması.
- **İçerik:** veritabanı anlık görüntüsü, ayarlar, isteğe bağlı olarak yüklenen dosyalar ve loglar.
- **İçermez:** API anahtarları ve parolalar **yedeğe dâhil edilmez**; manifest bunu `excludes_secrets: true` alanıyla beyan eder ve doğrulama bu alanı kontrol eder.
- **Konum:** `.env` → `BACKUP_DIR` (varsayılan `./backups`).
- **Ekran:** *Ayarlar → Yedekleme* (`/settings?tab=backup`), yetki: `backup:read`, `backup:create`, `backup:restore`.

### 9.2 Günlük yönetim işleri

| İş | Nasıl |
|----|-------|
| Elle yedek al | *Ayarlar → Yedekleme* → **Şimdi Yedekle**. Açıklama girin (örn. "sürüm yükseltme öncesi"). Kısayol: `Ctrl+K` → "Şimdi yedekle". |
| Yedeği doğrula | Yedek satırında **Doğrula**. Dosya varlığı, boyut, sağlama toplamı, ZIP bütünlüğü, manifest varlığı ve geçerliliği, sır içermeme beyanı ve veritabanının açılabilirliği kontrol edilir. |
| Kritik yedeği koru | **Koru** işareti; korumalı yedekler otomatik temizlikte **asla silinmez**. |
| Eski yedekleri temizle | **Temizle**: saklama politikasına göre (varsayılan son 7 gün, 4 hafta, 12 ay) fazlalıkları siler. |
| Zamanlanmış yedekleme | `.env` → `BACKUP_SCHEDULE_ENABLED=true`, `BACKUP_SCHEDULE_CRON=0 23 * * *`. Sonuç bildirim olarak düşer. |
| Geri yükleme | **Doğrula → güvenlik yedeği al → önizle → onayla → geri yükle**. Hata durumunda sistem otomatik geri döner. Yetki: `backup:restore` (yalnızca `system_admin` ve `school_director`). |

### 9.3 Kurallar

1. **Migration ve sürüm yükseltmesi öncesi mutlaka elle yedek alın.**
2. Geri yüklemeden önce **doğrulama** çalıştırın; bozuk yedek listede kırmızı gösterilir.
3. Geri yükleme sırasında **başka kullanıcı sistemde olmamalıdır**.
4. Yedek klasörünü düzenli olarak **ayrı bir diske veya ağ paylaşımına** kopyalayın. Aynı diskte duran yedek, disk arızasında yedek değildir.
5. Ayda bir **geri yükleme tatbikatı** yapın: bir kopya ortamda yedeği geri yükleyip açıldığını doğrulayın.

> **Bilinen kısıt:** yedekleme ve geri yükleme şu an yalnızca SQLite için desteklenir. PostgreSQL kurulumlarında `pg_dump` tabanlı akış v1.0'a planlanmıştır.

---

## 10. Sistem Sağlığı

*Ayarlar → Hakkında* ekranı ve sağlık uç noktası (yetki: `system:health`; sağlık uç noktası izleme araçları için açıktır).

```http
GET /api/v1/health
```

### 10.1 Bileşenler

| Bileşen | Ne kontrol edilir | Olası durumlar |
|---------|-------------------|----------------|
| `backend` | Uygulama ayakta mı, hangi sürüm | `ok` |
| `database` | `SELECT 1` sorgusu ve gecikme (ms) | `ok` / `down` |
| `ai:<sağlayıcı>` | Her AI sağlayıcısının erişilebilirliği ve gecikmesi | `ok` / `degraded` / `down` |
| `frontend` | `frontend/dist/index.html` derlenmiş mi | `ok` / `degraded` |

**Genel durum kuralı:** yalnızca `backend` ve `database` bileşenleri genel durumu belirler. AI sağlayıcısı kapalıysa veya arayüz derlenmemişse genel durum `degraded` olur ama **sistem çalışmaya devam eder**. AI olmadan da tüm sayısal analizler, raporlar ve operasyon çalışır.

### 10.2 Hakkında ekranı

| Bilgi | Ne işe yarar |
|-------|--------------|
| Uygulama adı ve sürüm | Destek talebinde ilk sorulan bilgi. |
| Derleme (`build`) | Ortam + sürüm (`production-0.9.0`). |
| Git commit | Kaynak sürümünün kimliği (varsa). |
| **Veritabanı revizyonu** | Alembic revizyon numarası; migration durumunun kanıtı. |
| Veritabanı motoru | SQLite / PostgreSQL. |
| Python sürümü / platform | Ortam bilgisi. |

Destek talebi açarken bu ekranın görüntüsünü ekleyin.

### 10.3 Ne zaman hangi durum

| Durum | Anlamı | Yapılacak |
|-------|--------|-----------|
| `database: down` | Veritabanına erişilemiyor | Dosya yolu ve disk alanını kontrol edin; `logs/database.log` inceleyin. Acil durumdur. |
| `ai:*: down` | Sağlayıcıya ulaşılamıyor | LM Studio kapalı olabilir veya bulut anahtarı geçersizdir. Operasyonu etkilemez. |
| `frontend: degraded` | Arayüz derlenmemiş | `BUILD_FRONTEND.bat` çalıştırın. |
| Yüksek `database` gecikmesi | Disk yavaş veya veritabanı büyümüş | Bakım görevlerini (bölüm 13) çalıştırın, disk sağlığını kontrol edin. |

---

## 11. Eğitim Modu

**Ne işe yarar:** Eğitim modu açık olan kullanıcıda arayüzün üstünde mor bir uyarı bandı görünür. Band, kullanıcıya demo kayıtlar üzerinde çalıştığını ve gerçek üretim verisine dokunmaması gerektiğini hatırlatır. Demo işaretli kayıtlar arayüzde ayrıca vurgulanır.

**Nasıl açılır:**

```http
POST /api/v1/training/mode/true     # açar
POST /api/v1/training/mode/false    # kapatır
Authorization: Bearer <erişim jetonu>
```

Ayar **kullanıcı bazındadır**: yalnızca modu açan hesabı etkiler, diğer kullanıcıları etkilemez.

**Ne zaman kullanılır:**

| Durum | Neden |
|-------|-------|
| Yeni personel eğitimi | Kişi demo verisiyle pratik yaparken gerçek kayıtları değiştirmediğini görsel olarak teyit eder. |
| Eğitim Merkezi turları | 12 interaktif eğitim adım adım gerçek ekranlarda ilerler; eğitim modu bandı bağlamı belli eder. |
| Sunum ve demo | Karşı tarafa gösterilen verinin gerçek olmadığı açıkça belirtilmiş olur. |
| Yeni özellik denemesi | Yönetici bir akışı denerken yanlışlıkla üretim verisi değiştirmeyi engellemeye yardımcı olur. |

> Eğitim modu bir **yetki kısıtı değildir**; kullanıcının izinlerini değiştirmez, yalnızca görsel uyarı sağlar. Gerçek koruma için eğitim ortamında ayrı bir veritabanı (`DATABASE_URL`) kullanın.

**Eğitim Merkezi** (`/training`) rol bazlı eğitim izleri sunar:

| İz | Eğitimler |
|----|-----------|
| Başlangıç | İlk öğrenci, ilk eğitmen, ilk havuz, ilk program, yoklama |
| Operasyon | Program, yoklama, üyelik + ödeme |
| Yönetici | İstatistik raporu, üyelik + ödeme, yedekleme |
| Antrenör | Performans kaydı, program, yoklama |
| Yapay Zekâ | Yerel AI, bulut AI, AI Developer Console |
| Sistem Yöneticisi | Yedekleme, yerel AI, AI Developer Console |

Kullanıcının rollerine göre önerilen izler otomatik seçilir; ilerleme kullanıcı bazında saklanır.

---

## 12. Demo Verisi

### 12.1 Nasıl üretilir

```powershell
# PowerShell betiği (önerilen)
.\scripts\seed_demo.ps1
.\scripts\seed_demo.ps1 -Reset -Students 100 -Instructors 15

# Doğrudan Python modülü (backend dizininden)
Push-Location backend
..\.venv\Scripts\python.exe -m app.db.seed --students 50 --instructors 10
..\.venv\Scripts\python.exe -m app.db.seed --reset
Pop-Location
```

Varsayılan üretim: **2 havuz**, kulvarlar, gruplar, **10 eğitmen**, **50 öğrenci** ve velileri, üyelikler, ödemeler, faturalar, giderler, dersler, yoklamalar, performans kayıtları, kişisel rekorlar ve yarışmalar. Üretim tekrarlanabilirdir (sabit rastgelelik tohumu), aynı komut aynı veriyi üretir.

**Demo kullanıcı hesapları** (parola: `Demo!2026`):

| Hesap | Rol |
|-------|-----|
| `mudur@yuzmeokulu.local` | Yüzme Okulu Müdürü |
| `resepsiyon@yuzmeokulu.local` | Resepsiyon |
| `finans@yuzmeokulu.local` | Finans / Muhasebe |
| `basantrenor@yuzmeokulu.local` | Baş Antrenör |
| `egitmen@yuzmeokulu.local` | Yüzme Eğitmeni |
| `veli@yuzmeokulu.local` | Veli (portal görünümü) |

Bu hesaplar rol bazlı yetkilendirmeyi ve satır bazlı kapsamı test etmek için idealdir: veli hesabıyla giriş yapıp yalnızca kendi çocuklarını gördüğünü doğrulayabilirsiniz.

### 12.2 Nasıl temizlenir

Üretilen **tüm demo kayıtlar `is_demo = true` ile işaretlenir** ve arayüzde "DEMO" rozetiyle gösterilir; gerçek veri gibi sunulmaz.

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.db.seed --reset
Pop-Location
```

`--reset` yalnızca `is_demo = true` işaretli kayıtları siler; elle girdiğiniz gerçek kayıtlara dokunmaz. Veritabanında zaten öğrenci varsa ve `--reset` vermezseniz betik yeni veri üretmeden çıkar ("Veritabanında zaten N öğrenci var" uyarısı).

### 12.3 Üretimde kullanmayın

- `SEED_DEMO_DATA` değerini üretim `.env` dosyasında **`false`** yapın.
- `APP_ENV=production` iken demo üretimi **kod düzeyinde engellenir**; betik "Üretim ortamında demo verisi oluşturulamaz" diyerek çıkar.
- Gerçek kuruma geçmeden önce demo kayıtları temizleyin ve *İstatistikler* ekranında sayıların sıfırlandığını doğrulayın.
- Demo verisiyle üretilmiş raporları kurum içinde paylaşmayın; rakamlar gerçek değildir.

---

## 13. Bakım Görevleri

### 13.1 Günlük

| # | Görev | Nerede |
|---|-------|--------|
| 1 | Kontrol panelindeki uyarıları gözden geçirin (yoklaması alınmamış dersler, geciken ödemeler). | `/` |
| 2 | Okunmamış **uyarı** ve **hata** bildirimlerini kapatın. | `/notifications` |
| 3 | Zamanlanmış yedeğin başarıyla alındığını doğrulayın. | *Ayarlar → Yedekleme* |
| 4 | Sistem sağlığında `down` bileşen var mı bakın. | *Ayarlar → Hakkında* |
| 5 | Su kalitesi uyarısı geldiyse teknik personele iletin. | `/notifications` |

### 13.2 Haftalık

| # | Görev | Nerede |
|---|-------|--------|
| 1 | Bekleyen alacak yaşlandırmasını inceleyin; 60+ gün grubunu önceliklendirin. | `/finance` |
| 2 | Süresi dolacak üyelikler ve ders hakkı azalanlar listelerini işleyin. | `/memberships` |
| 3 | Eğitmen iş yükü dağılımını kontrol edin. | `/instructors` |
| 4 | Süresi dolan sertifikaları kontrol edin. | `/instructors` |
| 5 | Denetim kaydında olağandışı işlem var mı bakın (zorlanmış çakışma, silme, parola sıfırlama). | *Ayarlar → Denetim Kaydı* |
| 6 | Yedek klasörünü ayrı bir diske/paylaşıma kopyalayın. | Dosya sistemi |
| 7 | CAIO gözlem modunu çalıştırıp yeni bulguları inceleyin. | `/caio` |

### 13.3 Aylık

| # | Görev | Nasıl |
|---|-------|-------|
| 1 | **Üyelik durumlarını tazeleyin** — süresi dolmuş üyelikleri toplu güncelle. | `POST /api/v1/memberships/refresh-statuses` |
| 2 | **Bildirim taramasını çalıştırın** — biten üyelik, geciken ödeme, yaklaşan yarışma vb. | `POST /api/v1/notifications/generate` |
| 3 | KPI gerçekleşmelerini gözden geçirin, hedefleri güncelleyin. | *İstatistikler → KPI* |
| 4 | Cohort analizinden tutundurma eğilimini okuyun. | *İstatistikler → Gelişmiş* |
| 5 | Aylık Yönetim Raporu üretin ve arşivleyin. | `/reports` |
| 6 | Log klasörü boyutunu kontrol edin (dosya başına 5 MB × 5 arşiv). | `logs/` |
| 7 | Eski yedekleri temizleyin (korumalılar silinmez). | *Ayarlar → Yedekleme → Temizle* |
| 8 | Kullanıcı listesini gözden geçirin: ayrılan personel devre dışı mı, roller güncel mi? | *Ayarlar → Kullanıcılar* |
| 9 | Geri yükleme tatbikatı yapın (kopya ortamda). | Bkz. BACKUP_RESTORE_TR.md |
| 10 | Çeviri bütünlüğünü denetleyin. | `GET /api/v1/i18n/validate` |

### 13.4 Yıllık

- Tatil takvimini yeni yıl için güncelleyin (*Havuzlar → Tatil Takvimi*).
- Paket fiyatlarını gözden geçirin.
- Parola politikasını ve kullanıcı listesini toplu olarak denetleyin.
- Bir önceki yılın verisiyle "Geçen yıl" dönemli raporları üretip arşivleyin.

---

## 14. Güncelleme Prosedürü

Sıra **kesinlikle** şu şekilde olmalıdır: **yedek → güncelle → migration → doğrula**.

### 14.1 Adım adım

**1) Yedek alın (atlanamaz)**

*Ayarlar → Yedekleme* → **Şimdi Yedekle** → açıklama: "v0.9.0 → vX.Y.Z yükseltme öncesi" → yedeği **Koru** işaretiyle kilitleyin → **Doğrula** çalıştırın.

**2) Kullanıcıları bilgilendirin ve sistemi durdurun**

Program penceresini ve konsol penceresini kapatın. Güncelleme sırasında kimse sistemde olmamalıdır.

**3) Yeni sürümü yerleştirin**

Yeni dosyaları proje klasörüne kopyalayın. **`.env`, `data/`, `backups/` ve `logs/` klasörlerinin üzerine yazmayın.**

**4) Bağımlılıkları güncelleyin**

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt --upgrade
```

**5) Migration uygulayın**

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m alembic current
Pop-Location
```

`current` çıktısında revizyonun `(head)` ile işaretli olduğunu görün.

**6) Arayüzü yeniden derleyin**

```
BUILD_FRONTEND.bat
```

**7) Kalite kapısını çalıştırın**

```
FINAL_CHECK.bat
```

Bu betik sırayla şunları kontrol eder: backend lint (ruff), biçim (black), tip denetimi (mypy), **testler (pytest — 395 test fonksiyonu)**, alembic `upgrade`/`current`/`check`, çeviri bütünlüğü, yedekleme modülü, frontend tip denetimi (tsc), frontend lint, frontend derlemesi, **gizli anahtar taraması** ve bağımlılık güvenlik taraması (pip-audit). Sonuçta PASS / FAIL / WARNING / SKIPPED özeti verir. **FAIL varsa yayına geçmeyin.**

**8) Doğrulayın**

- [ ] `START_SWIMMING_SCHOOL.bat` ile program açılıyor.
- [ ] *Ayarlar → Hakkında*: sürüm ve veritabanı revizyonu beklenen değerlerde.
- [ ] Sağlık ekranında `backend` ve `database` = `ok`.
- [ ] Kontrol panelindeki sayılar makul (öğrenci sayısı, bugünkü ders sayısı).
- [ ] Bir öğrenci profili, bir ders ve bir rapor açılıyor.
- [ ] Bir test yoklaması kaydedilip geri alınabiliyor.
- [ ] Farklı bir rolle (örn. resepsiyon) giriş yapılıp menüler doğru görünüyor.

**9) Geri dönüş planı**

Doğrulama başarısızsa:

1. Sistemi durdurun.
2. Bir önceki sürümün dosyalarını geri koyun.
3. *Ayarlar → Yedekleme → Geri Yükle* ile 1. adımdaki yedeği geri yükleyin (güvenlik yedeği seçeneği açık kalsın).
4. Sağlık ve veri kontrollerini tekrarlayın.

> Migration geri alma (`alembic downgrade`) her sürüm için garanti edilmez; geri dönüşün güvenli yolu **yedekten geri yüklemedir**.

---

## 15. Sorun Giderme

### 15.1 Loglar nerede, hangisi ne içerir

Tüm loglar proje kökündeki **`logs/`** klasöründedir (`.env` → `LOG_DIR`). Dosyalar döner: **dosya başına 5 MB, 5 arşiv kopyası** saklanır.

| Dosya | İçerik | Ne zaman bakılır |
|-------|--------|------------------|
| `logs/application.log` | Uygulama yaşam döngüsü, başlangıç, genel hatalar, yakalanmamış istisnalar. | Program açılmıyor, beklenmedik hata. |
| `logs/database.log` | Veritabanı katmanı; `DATABASE_ECHO=true` iken SQL sorguları. | Yavaşlık, kilitlenme, migration sorunu. |
| `logs/ai.log` | AI sağlayıcı çağrıları, gecikme, model seçimi, hatalar. | AI analizleri çalışmıyor. |
| `logs/security.log` | Başarılı/başarısız girişler, hesap kilitleri, hız sınırı, parola değişiklikleri. | Şüpheli erişim, giriş sorunları. |
| `logs/developer-agent.log` | AI Developer Console: plan, yama, komut politikası kararları. | Geliştirici konsolu davranışı. |
| `logs/audit.log` | Denetim kayıtlarının metin kopyası. | Denetim ekranına erişilemediğinde. |

**Maskeleme:** log yazımından önce her satır maskeleme filtresinden geçer. `nvapi-…`, `sk-…`, `ghp_…` gibi anahtar desenleri, `Bearer` jetonları ve `api_key`/`password`/`secret`/`token` alanları `***REDACTED***` olarak yazılır. Log dosyalarını paylaşmadan önce yine de gözden geçirin.

Log seviyesini geçici olarak ayrıntılandırmak için `.env` → `LOG_LEVEL=DEBUG` yapıp uygulamayı yeniden başlatın; sorun çözüldükten sonra `INFO`'ya geri alın.

### 15.2 Sık karşılaşılan hatalar

**Program açılmıyor / konsol hemen kapanıyor**

1. `logs/application.log` dosyasının sonuna bakın.
2. Python kurulu mu: `python --version` (3.11+ olmalı, PATH'te bulunmalı).
3. `.venv` bozulmuşsa klasörü silip `START_SWIMMING_SCHOOL.bat` ile yeniden kurulmasını sağlayın.
4. Port çakışması: 8000 portunu başka bir uygulama kullanıyorsa `.env` → `APP_PORT` değerini değiştirin.

**"Migration uygulanamadi" uyarısı**

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
```

Komutu elle çalıştırıp tam hata metnini okuyun. Şema ile model uyuşmuyorsa `alembic check` farkı gösterir. Migration başarısızsa **veri girişine devam etmeyin**; önce yedekten dönün.

**Arayüz açılıyor ama "Arayüz derlenmemiş" mesajı geliyor**

`BUILD_FRONTEND.bat` çalıştırın. Node.js 20+ kurulu olmalıdır. Sağlık ekranında `frontend: degraded` görürsünüz.

**Giriş yapılamıyor / hesap kilitli**

| Belirti | Neden | Çözüm |
|---------|-------|-------|
| "Çok fazla deneme" | 8 hatalı denemeden sonra 15 dakikalık kilit veya dakikada 10 denemelik hız sınırı | 15 dakika bekleyin **veya** yönetici olarak parola sıfırlayın (sıfırlama kilidi kaldırır). |
| "Geçersiz kimlik bilgileri" | Yanlış e-posta/parola | `logs/security.log` içinde denemeyi doğrulayın. |
| "Hesap pasif" | Kullanıcı devre dışı | *Ayarlar → Kullanıcılar* → Düzenle → Aktif. |
| Herkes aynı anda düştü | `SECRET_KEY` değişti | Eski anahtarı geri koyun veya kullanıcıların yeniden giriş yapmasını isteyin. |

**Yetki hataları**

Hata yanıtı hangi iznin gerektiğini ve eksik olanı içerir. Kullanıcının rollerini kontrol edin. Rolün izin kümesi kod tanımından gelir; rolü elle değiştirmek yerine **doğru rolü atayın**.

**AI sağlayıcı hataları**

| Belirti | Neden | Çözüm |
|---------|-------|-------|
| `ai:local: down` | LM Studio kapalı veya sunucu başlatılmamış | LM Studio → Developer → Start Server. |
| "Model bulunamadı" | `.env` → `LOCAL_AI_MODEL` kurulu değil | Model adını boş bırakın (otomatik seçim) veya kurulu bir model yazın. |
| `ai:nvidia: down` | Anahtar geçersiz veya internet yok | *AI Merkezi* → bağlantı testi; anahtarı `.env`'den güncelleyin. |
| Zaman aşımı | Yerel model yavaş | `LOCAL_AI_TIMEOUT` değerini artırın. |

AI kapalıyken **hesaplanmış veri panelleri çalışmaya devam eder**; istatistik, rapor ve operasyon etkilenmez.

**Veritabanı kilitli / yavaş (SQLite)**

- Aynı veritabanı dosyasına birden fazla uygulama örneği bağlanmadığından emin olun.
- Uzun süren rapor çalıştırmalarında dönemi daraltın.
- `logs/database.log` içindeki gecikmeleri inceleyin.
- Veri hacmi büyüdüyse PostgreSQL'e geçişi değerlendirin (`DATABASE_URL` değiştirilir; yedekleme kısıtına dikkat edin).

**Diskte yer kalmadı**

`backups/` ve `logs/` klasörleri zamanla büyür. Yedek temizliğini çalıştırın (korumalı yedekler silinmez) ve eski log arşivlerini taşıyın.

**Çeviri eksikleri**

```http
GET /api/v1/i18n/validate
Authorization: Bearer <erişim jetonu>
```

Yanıt toplam anahtar sayısını, eksik anahtarları ve bütünlük durumunu döndürür (yetki: `settings:read`).

### 15.3 Destek için toplanacak bilgiler

1. *Ayarlar → Hakkında* ekranının görüntüsü (sürüm, veritabanı revizyonu, platform).
2. `GET /api/v1/health` çıktısı.
3. Hatanın oluştuğu **tarih-saat** ve ekran adı.
4. İlgili log dosyasının o zaman aralığındaki satırları.
5. *Ayarlar → Denetim Kaydı* ekranından ilgili kayıt geçmişi.

---

*Bu belge sistemin 0.9.0 sürümüne göre hazırlanmıştır. İlgili belgeler: [USER_GUIDE_TR.md](USER_GUIDE_TR.md) · [BACKUP_RESTORE_TR.md](BACKUP_RESTORE_TR.md) · [../CHANGELOG.md](../CHANGELOG.md)*
