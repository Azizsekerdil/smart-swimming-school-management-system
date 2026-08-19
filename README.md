<div align="center">

# 🏊 Akıllı Yüzme Okulu Yönetim Sistemi

**Smart Swimming School Management System**

Bir yüzme okulunun günlük operasyonunu, sporcu performans analizini ve
yapay zekâ destekli karar desteğini tek bir yerel kurulumda birleştiren,
uçtan uca çalışan yönetim sistemi.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/tests-395%20functions%20%C2%B7%20533%20runs-brightgreen)

**Türkçe** · [English summary](#english-summary)

</div>

---

## ⚠️ Önce okuyun: ilk giriş kimliği

Sistem ilk açılışta **belgelenmiş, tek kullanımlık** bir kurulum kimliğiyle gelir:

```
kullanıcı adı : admin
parola        : admin
```

**Bu parola ilk girişte MUTLAKA değiştirilmelidir.** Değiştirilene kadar:

* hiçbir korumalı ekrana veya veriye erişilemez (yalnızca parola değiştirme
  akışı çalışır),
* giriş **yalnızca sunucunun çalıştığı cihazdan** (`127.0.0.1`) kabul edilir;
  ağ üzerinden veya bir ters vekil arkasından yapılan kurulum girişi reddedilir.

Parola bir kez değiştiğinde `admin/admin` **kalıcı olarak geçersizdir** ve
yönetici parola sıfırlaması bile onu geri getiremez. Ayrıntı ve regresyon
testleri: [`SECURITY.md`](SECURITY.md),
`backend/tests/test_bootstrap_admin.py`.

---

## İçindekiler

- [Ne yapar, ne yapmaz](#ne-yapar-ne-yapmaz)
- [Olgunluk durumu](#olgunluk-durumu)
- [Özellikler](#özellikler)
- [Ekranlar ve sunum](#ekranlar-ve-sunum)
- [Mimari](#mimari)
- [Kurulum](#kurulum)
- [Çalıştırma ve demo](#çalıştırma-ve-demo)
- [Ortam değişkenleri](#ortam-değişkenleri)
- [Yapay zekâ](#yapay-zekâ)
- [Gizlilik ve insan onayı](#gizlilik-ve-insan-onayı)
- [Testleri çalıştırma](#testleri-çalıştırma)
- [Sayılarla sistem](#sayılarla-sistem)
- [Güvenlik açığı bildirimi](#güvenlik-açığı-bildirimi)
- [Bilinen sınırlar ve yol haritası](#bilinen-sınırlar-ve-yol-haritası)
- [Lisans ve üçüncü taraf bildirimleri](#lisans-ve-üçüncü-taraf-bildirimleri)
- [English summary](#english-summary)

---

## Ne yapar, ne yapmaz

### Yapar

* Öğrenci, veli, eğitmen ve personel kaydı; rol ve izin yönetimi.
* Havuz, kulvar, grup ve ders planlaması; **otomatik çakışma denetimi**.
* Yoklama, ders hakkı tüketimi, telafi dersi.
* Üyelik paketleri, dondurma, yenileme, ders hakkı takibi.
* Tahsilat, fatura, gider, indirim ve bekleyen borç takibi.
* Sporcu performans ölçümü (ara dereceler, dönüş, tepki süresi, kulaç
  frekansı), kişisel rekorlar, yarışma ve madalya yönetimi.
* İstatistik motoru (28 fonksiyon, 11 KPI) ve 16 rapor şablonu; XLSX/PDF
  dışa aktarma.
* Yerel (LM Studio) veya bulut (NVIDIA Build) modelle **yapay zekâ yorumu**.
* Yedekleme, doğrulama ve geri yükleme (SQLite).
* Tam iki dilli arayüz (TR/EN), açık ve koyu tema.

### Yapmaz

Aşağıdakiler **bilinçli olarak yoktur**. Tam liste:
[`docs/known-limitations.md`](docs/known-limitations.md).

* **Çok kiracılı (multi-tenant) değildir.** Modellerde kurum ayırıcı sütun
  yoktur. Birden çok kurumun verisini aynı kuruluma koymayın.
* **İnternete açık SaaS olarak tasarlanmamıştır.** Varsayılan kurulum
  `127.0.0.1` üzerinde SQLite ile çalışır. Ağa açmak isterseniz ters vekil,
  TLS ve gözden geçirilmiş CORS listesi **sizin sorumluluğunuzdadır**.
* **Yedekler şifrelenmez** (düz ZIP). `.env` yedeğe dâhil edilmez.
* **Otomatik saklama süresi (retention) motoru yoktur.**
* **Oturum iptali (token revocation) yoktur**; JWT süresi dolana kadar geçerlidir.
* **E-posta/SMS gönderimi, mobil uygulama, RFID/NFC donanım entegrasyonu ve
  bulut yedekleme yoktur.**
* **Yapay zekâ maliyet tavanı yoktur.**
* **Tıbbi, sağlık, beslenme, finansal, yatırım veya hukuki tavsiye vermez.**
  Sağlık notu alanları operasyonel not alanıdır; finans modülü tahsilat
  takibidir. Bunlar profesyonel görüşün yerine geçmez.
* **Hiçbir mevzuata (KVKK/GDPR) uyum garantisi vermez.** Teknik yapılar sunar;
  uyum kurumun sorumluluğundadır. Bkz. [`PRIVACY.md`](PRIVACY.md).

---

## Olgunluk durumu

| | |
|---|---|
| **Sürüm** | `1.0.0-public` — ilk kamuya açık yayın |
| **Durum** | Uçtan uca çalışır; **üretimde hiçbir gerçek kurumda çalıştırılmamıştır** |
| **Test** | 395 test fonksiyonu, parametreleştirme sonrası 533 çalıştırma — 2026-08-19'da CPython 3.11 üzerinde tamamı geçti (1 test Windows'ta sembolik bağ hakkı gerektirdiği için atlandı) |
| **Ölçek** | Yük/performans testi **yapılmamıştır**; ölçek hakkında bir iddia yoktur |
| **Bakım** | Tek kişilik, en iyi çaba; SLA yoktur |
| **Erişilebilirlik** | WCAG denetimi **yapılmamıştır** |

---

## Özellikler

<details>
<summary><b>Kişi yönetimi</b></summary>

Öğrenci kaydı (5 durum, 6 yüzme seviyesi), veli-öğrenci ilişkisi, eğitmen ve
personel kaydı, 21 rol ve 52 izin. Sağlık notu ve özel gereksinim alanları
ayrı bir izinle (`student:read_sensitive`) korunur; izni olmayan kullanıcı bu
alanları **göremez ve yazamaz**.
</details>

<details>
<summary><b>Tesis ve program</b></summary>

Havuz ve kulvar tanımı, grup yönetimi, 13 ders türü, 5 ders durumu, tekrarlı
ders serileri, takvim görünümü ve kulvar planı. Ders kaydedilmeden önce
kulvar, eğitmen ve öğrenci çakışmaları denetlenir.
</details>

<details>
<summary><b>Operasyon</b></summary>

6 durumlu yoklama, ders hakkı tüketimi, telafi, QR/kart ile giriş uçları,
7 paket türü ve 5 üyelik durumu, dondurma ve yenileme, 6 ödeme durumu,
5 ödeme yöntemi, 10 gider kategorisi, indirim tanımları.
</details>

<details>
<summary><b>Spor ve analiz</b></summary>

Performans kaydı (ara dereceler, dönüş süresi, çıkış tepkisi, kulaç
frekansı), kişisel rekorlar, kulüp rekorları, 5 seviyeli yarışma yönetimi,
seri (heat) oluşturma, madalya tablosu, gelişim eğilimi ve istatistiksel
yarışma hazırlık göstergesi (**yapay zekâ tahmini değildir**).
</details>

<details>
<summary><b>Yedekleme</b></summary>

7 yedek türü, manifest + özet doğrulaması, 11 denetimli bütünlük testi,
geri yükleme öncesi doğrulama. **Yedekler şifrelenmez**; `.env` yedeğe dâhil
edilmez.
</details>

---

## Ekranlar ve sunum

24 arayüz ekranı vardır. Tanıtım destesi (52 slayt, 4 varyant) bu depoda
**yayımlanmış PDF** olarak bulunur:

| Dosya | Dil | Tema |
|---|---|---|
| [`docs/presentation/Yuzme_Okulu_Tanitim_PUBLIC.pdf`](docs/presentation/Yuzme_Okulu_Tanitim_PUBLIC.pdf) | Türkçe | Koyu |
| [`docs/presentation/Yuzme_Okulu_Tanitim_Baski_PUBLIC.pdf`](docs/presentation/Yuzme_Okulu_Tanitim_Baski_PUBLIC.pdf) | Türkçe | Açık (baskı) |
| [`docs/presentation/Yuzme_Okulu_Intro_EN_PUBLIC.pdf`](docs/presentation/Yuzme_Okulu_Intro_EN_PUBLIC.pdf) | İngilizce | Koyu |
| [`docs/presentation/Yuzme_Okulu_Intro_EN_Print_PUBLIC.pdf`](docs/presentation/Yuzme_Okulu_Intro_EN_Print_PUBLIC.pdf) | İngilizce | Açık (baskı) |

> **Sunumdaki bütün veriler sentetiktir.** Ekran görüntüleri çalışan
> uygulamadan alınmıştır (elle çizilmemiş, taklit edilmemiştir) ama içlerindeki
> kayıtların tamamı demo tohumlayıcısının ürettiği kurgusal kayıtlardır:
> adlar sabit havuzlardan gelir, e-postalar yönlendirilemeyen `.local` alan
> adını kullanır ve telefon numaraları hiçbir numaralandırma planında tahsisli
> olmayan `0000` ön ekiyle üretildiği için **aranamaz**. Gerçek hiçbir öğrenci,
> veli, çocuk veya personel verisi yayımlanmamıştır.

PPTX, HTML görüntüleyici ve ham PNG kareleri sürümlenmez; `tools/` altındaki
kaynaktan tek komutla yeniden üretilir (bkz. [`sunum/README.md`](sunum/README.md)).

---

## Mimari

```
┌──────────────────────────────────────────────────────────┐
│  React 18 + TypeScript + Vite + Tailwind  (frontend/)    │
│  26 sayfa · TanStack Query · Zustand · i18next (TR/EN)   │
└───────────────────────────┬──────────────────────────────┘
                            │  REST /api/v1
┌───────────────────────────▼──────────────────────────────┐
│  FastAPI  (backend/app/)                                 │
│  ├── api/       240 uç · 193 yol · 23 modül grubu        │
│  ├── core/      RBAC · güvenlik · ilk kurulum kapısı     │
│  ├── services/  iş mantığı · istatistik · raporlama      │
│  │   ├── ai/    sağlayıcılar · yönlendirici · ajanlar    │
│  │   └── hsp/   GİZLİLİK GEÇİDİ (bütün AI çağrıları)     │
│  └── models/    SQLAlchemy 2.0 · 55 tablo                │
└───────────────────────────┬──────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        SQLite / PostgreSQL      LM Studio (yerel) │ NVIDIA (bulut)
        Alembic göçleri          varsayılan: yerel öncelik
```

Ayrıntı: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/DATABASE.md`](docs/DATABASE.md), [`docs/API.md`](docs/API.md).

---

## Kurulum

### Gereksinimler

* Python **3.11+**
* Node.js **20+**
* Windows, macOS veya Linux (masaüstü sarmalayıcı ve sunum PDF üretimi
  Windows'a özgüdür)

### Adımlar

```bash
git clone <bu-depo>
cd smart-swimming-school-management-system

# 1) Ortam dosyası
cp .env.example .env
# SECRET_KEY üretin ve .env içine yazın:
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 2) Backend
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt      # Windows
# source .venv/bin/activate && pip install -r backend/requirements.txt

cd backend
alembic upgrade head

# 3) Frontend
cd ../frontend
npm ci
npm run build
```

Yeniden üretilebilir kurulum için çözülmüş ağaç:
`pip install -r backend/requirements.lock.txt`.

---

## Çalıştırma ve demo

```bash
# Backend (proje kökünde .env okunur)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Geliştirme için arayüz (ayrı terminal)
cd frontend
npm run dev
```

Tarayıcıdan `http://127.0.0.1:8000` (derlenmiş arayüz) ya da
`http://localhost:5173` (geliştirme sunucusu).

**İlk giriş:** `admin` / `admin` → sistem sizi doğrudan zorunlu parola
değiştirme ekranına alır. Bunu geçmeden hiçbir ekran açılmaz.

### Demo verisi

```bash
cd backend
python -m app.db.seed --reset
```

> **Demo verisinin tamamı sentetiktir.** Adlar sabit havuzlardan üretilir,
> e-postalar `.local` alan adını kullanır, telefonlar `0000` ön ekiyle
> üretildiği için aranamaz ve her satır `is_demo = true` ile işaretlenir.
> `APP_ENV=production` iken tohumlama çalışmayı **reddeder**.
>
> Tohumlayıcı ayrıca her rol için bir demo giriş hesabı oluşturur
> (`mudur@`, `resepsiyon@`, `finans@`, `basantrenor@`, `egitmen@`,
> `veli@yuzmeokulu.local` — parola `Demo!2026`). Bunlar **yalnızca geliştirme
> içindir**; üretim veritabanında oluşturulmazlar.

---

## Ortam değişkenleri

Tam liste ve açıklamalar: [`.env.example`](.env.example).
`.env` dosyası **asla** depoya eklenmez (`.gitignore` ile engellenir; CI da
denetler).

| Değişken | Anlamı | Not |
|---|---|---|
| `SECRET_KEY` | JWT imzalama anahtarı | **Doldurun.** Boş bırakılırsa her süreç başlangıcında rastgele üretilir ve oturumlar geçersiz olur. |
| `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` | İlk kurulum hesabı | Varsayılan `admin` — sır değil, tek kullanımlık kapı. Bkz. yukarısı. |
| `DATABASE_URL` | Veritabanı | SQLite varsayılan; PostgreSQL desteklenir (yedekleme hariç). |
| `LOCAL_AI_*` | LM Studio (yerel model) | Varsayılan **açık**. Veri kurumdan çıkmaz. |
| `NVIDIA_*` | NVIDIA Build (bulut) | Varsayılan **kapalı**. Anahtar kullanıcı tarafından girilir. |
| `AI_LOG_PROMPTS` | İstem metnini sakla | Varsayılan **false**; üretimde false bırakın. |
| `AI_DEVELOPER_ALLOW_SHELL` / `_ALLOW_APPLY` | Geliştirici ajanı kilitleri | İkisi de varsayılan **kapalı**. |

**Depoda hiçbir gerçek API anahtarı, parola veya belirteç yoktur** — ne
kaynakta, ne testlerde, ne `.env.example` içinde, ne belgelerde, ne PDF'lerde,
ne ekran görüntülerinde, ne loglarda, ne de SBOM'da. `.env.example` yalnızca
boş değer veya `YOUR_PROVIDER_API_KEY_HERE` yer tutucusu taşır.

---

## Yapay zekâ

Ayrıntılı şeffaflık notu: [`AI_TRANSPARENCY.md`](AI_TRANSPARENCY.md).

| Sağlayıcı | Tür | Varsayılan | Veri nereye gider |
|---|---|---|---|
| **LM Studio** | Yerel (loopback) | **Açık** | Hiçbir yere — model kendi bilgisayarınızda çalışır. |
| **NVIDIA Build** | Bulut | **Kapalı** | NVIDIA altyapısına; açıkça etkinleştirmeniz gerekir. |
| Genel OpenAI-uyumlu uç | Yapılandırılabilir | **Kapalı** | Sizin belirlediğiniz uca. |

Anthropic, Gemini, Azure OpenAI, Ollama veya vLLM bağdaştırıcısı **yoktur**.

**Anahtar yoksa ne olur?** Sağlayıcı `NOT_CONFIGURED` durumunda kalır ve
**hiçbir ağ çağrısı yapmaz**. Yerel yapay zekâ ve yapay zekâ dışı bütün
özellikler normal çalışır. Arayüz bir anahtarı asla tam göstermez: yalnızca
sağlayıcı adı, durum ve **son 4 karakter** görünür. "Bağlantıyı test et"
yalnızca siz tıkladığınızda çalışır ve anahtar hiçbir koşulda loglanmaz.

---

## Gizlilik ve insan onayı

Ayrıntı: [`PRIVACY.md`](PRIVACY.md).

* **Bütün AI çağrıları tek bir gizlilik geçidinden geçer**
  (`backend/app/services/hsp/gateway.py`): analiz, sohbet, akışlı sohbet,
  geliştirici ajanı ve CAIO. Bu bir slogan değil, **testle zorlanan** bir
  kısıttır: `backend/tests/test_ai_privacy_gateway.py` kaynak kodu AST ile
  ayrıştırır ve geçidi atlayan doğrudan bir sağlayıcı çağrısı kalmadığını
  doğrular.
* Geçit: sınıflandır → sağlayıcı kanıtını çöz → politikayı **çağrıdan önce**
  uygula → gönder / takma adlaştır / yerele zorla / **engelle** → hak makbuzu.
  Karar `BLOCK` ise çağrı yapılmaz.
* **Serbest metin de taranır**: sohbet metni telefon, e-posta, kimlik numarası,
  sağlık ve özel gereksinim anahtar kelimeleri ve veritabanındaki gerçek
  kişi adlarına karşı taranır; bulunanlar takma adlaştırılır.
* **Satır ve nesne bazlı yetki:** veli/öğrenci/sporcu rolleri yalnızca kendi
  (ya da çocuklarının) kaydını görür. Ders listesi ve yoklama ekranı da
  süzülür — bir veli sınıftaki diğer çocukları görmez. Kurum geneli
  toplulaştırmalar bu rollere tamamen kapalıdır.
  Testler: `backend/tests/test_row_level_authorisation.py`.
* **İnsan onayı:** kod değişikliği uygulamak `confirm=true` ister ve varsayılan
  olarak kapalıdır; testler başarısızsa değişiklik otomatik geri alınır.
  Kabuk erişimi varsayılan olarak kapalıdır.
* **Yapay zekâ otonom karar vermez.** Kayıt oluşturma, silme, ödeme ve
  planlama yalnızca kullanıcı eylemiyle olur.
* **Gerçek veri ile AI yorumu ayrı gösterilir**; sayılar veritabanından gelir,
  yapay zekâ sayı üretmez.

> Bu yönetişim katmanı bir **kurumsal yönetişim özelliğidir**. "Patentli",
> "benzersiz" veya "dünyada bir ilk" gibi bir iddiada bulunulmaz.

---

## Testleri çalıştırma

```bash
cd backend
pytest -q                                   # tüm paket
pytest tests/test_bootstrap_admin.py -q     # ilk kurulum sözleşmesi
pytest tests/test_row_level_authorisation.py -q
pytest tests/test_ai_privacy_gateway.py -q
pytest tests/test_spa_path_traversal.py -q
pytest --cov=app --cov-report=term-missing  # kapsam
```

```bash
cd frontend
npm run typecheck && npm run lint && npm run build
```

Testler bellek içi SQLite kullanır ve gerçek veritabanına dokunmaz; hiçbir
test gerçek bir sağlayıcı API'sini çağırmaz.

**Sürekli tümleştirme** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))
şunları **bloklayıcı** olarak çalıştırır: ruff, black, pytest, alembic
tutarlılık denetimi, TS tip denetimi, eslint, arayüz derlemesi, TR↔EN çeviri
bütünlüğü, metin dosyalarında gizli anahtar taraması ve ilk kurulum kapısını da
sınayan API duman testi. `mypy` ve `pip-audit` **bilgilendiricidir** ve
derlemeyi düşürmez — adımların adında da böyle yazar.

---

## Sayılarla sistem

Aşağıdaki sayılar **bu depodaki koddan mekanik olarak ölçülmüştür**
(2026-08-19). Hiçbiri elle yazılmamıştır.

| Ölçüm | Değer | Nasıl ölçüldü |
|---|---:|---|
| API ucu (belgelenmiş işlem) | **240** | OpenAPI şeması |
| Farklı API yolu | **193** | OpenAPI şeması |
| Modül grubu (router etiketi) | **23** | OpenAPI şeması |
| Veritabanı tablosu | **55** | SQLAlchemy `Base.metadata` |
| Kullanıcı rolü | **21** | `RoleCode` üye sayısı |
| İzin | **52** | `Perm` üye sayısı |
| Test fonksiyonu | **395** | AST sayımı |
| Test çalıştırması (parametreleştirme sonrası) | **533** | pytest toplaması |
| İstatistik fonksiyonu | **28** | AST sayımı |
| KPI tanımı | **11** | `KPI_DEFINITIONS` |
| Rapor şablonu | **16** | `REPORT_DEFINITIONS` |
| Hazır istem | **18** | `PROMPT_LIBRARY` |
| Ders türü | **13** | `LessonType` |
| Çeviri anahtarı (TR ve EN, her biri) | **1.027** | JSON yaprak sayımı |
| Arayüz sayfası | **26** | `frontend/src/pages/*.tsx` |
| Yakalanan arayüz ekranı | **24** | `tools/capture_screens.py` |
| Sunum slaydı | **52** | Üretilen PDF sayfa sayısı |

Bir sayıyı değiştiren bir katkı, README'deki ve sunum içeriğindeki sayıyı da
**ölçerek** güncellemelidir.

---

## Güvenlik açığı bildirimi

**Güvenlik açıklarını herkese açık issue olarak açmayın.** GitHub'da
**Security > Report a vulnerability** yolunu kullanın. Kapsam, yanıt hedefleri
ve ürünün güvenlik sözleşmesi: [`SECURITY.md`](SECURITY.md).

Güvenlik mimarisinin ayrıntısı: [`docs/SECURITY.md`](docs/SECURITY.md).

---

## Bilinen sınırlar ve yol haritası

* **Bilinen sınırlar (doğrulanmış):** [`docs/known-limitations.md`](docs/known-limitations.md)
* **Yol haritası (planlanan, söz değil):** [`docs/ROADMAP.md`](docs/ROADMAP.md)

Öne çıkan açık maddeler: çok kiracılılık yok · saklama süresi motoru yok ·
yedek şifreleme yok · oturum iptali yok · AI maliyet tavanı yok · `mypy`
temiz değil (60 hata, tip borcu) · yük testi yok.

---

## Lisans ve üçüncü taraf bildirimleri

* Bu projenin kendi kodu: **MIT** — [`LICENSE`](LICENSE)
* Üçüncü taraf bileşenler, lisans dağılımı ve **kopyaleft durumu**:
  [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)
* Yazılım malzeme listesi: [`sbom.spdx.json`](sbom.spdx.json),
  [`sbom.cdx.json`](sbom.cdx.json)

> **Dürüstlük notu.** Bu belgenin önceki sürümü bağımlılık ağacında "sıfır
> kopyaleft" olduğunu söylüyordu. Bu, *doğrudan* bağımlılıklar için doğru ama
> *çözülmüş* çalışma zamanı ağacı için yanlıştı: `certifi` **MPL-2.0**
> lisanslıdır ve `httpx` üzerinden çalışma zamanında dağıtılır. MPL-2.0 dosya
> düzeyinde kopyalefttir, MIT lisanslı proje kodunu etkilemez ve bir çatışma
> oluşturmaz — ama iddia yanlıştı ve düzeltilmiştir. Ayrıca `caniuse-lite`
> (CC-BY-4.0) atıf yükümlülüğü taşır ve artık adlandırılmıştır.

Katkı rehberi: [`CONTRIBUTING.md`](CONTRIBUTING.md) ·
Davranış kuralları: [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) ·
Değişiklik günlüğü: [`CHANGELOG.md`](CHANGELOG.md)

---

## English summary

A single-tenant, locally installed management system for a swimming school:
students, guardians, instructors, pools and lanes, lesson scheduling with
automatic conflict detection, attendance, memberships, payments, athlete
performance analysis, competitions, a statistics engine and reports, plus an
optional AI layer that interprets **computed** metrics — it never invents
numbers.

**First login is `admin` / `admin`** and **must be changed immediately**.
Until it is changed, no protected endpoint is reachable and login is accepted
**only from the machine running the server**. After the change the default
credential is permanently dead and an administrative password reset cannot
restore it. See [`SECURITY.md`](SECURITY.md).

**What it does not do:** it is **not** multi-tenant, not designed as an
internet-facing SaaS, does not encrypt backups, has no retention engine, no
token revocation, no e-mail/SMS delivery, no mobile app, no RFID hardware
integration and no AI cost cap. It gives **no** medical, health, nutritional,
financial, investment or legal advice, and guarantees **no** regulatory
compliance. The full, verified list is in
[`docs/known-limitations.md`](docs/known-limitations.md).

**AI providers:** LM Studio (local, default on), NVIDIA Build (cloud, default
off) and a generic OpenAI-compatible endpoint. With no API key configured the
provider reports `NOT_CONFIGURED` and makes **no** call; local AI and every
non-AI feature keep working. **Every** AI call — chat, streaming chat, the
developer agent and the CAIO agent — passes through one privacy gateway that
classifies the payload, resolves provider evidence, applies policy *before*
the call, pseudonymises real names and issues a tamper-evident receipt. A test
parses the source and fails if any call path bypasses the gateway.

**Demo data is synthetic only:** names come from fixed pools, e-mail addresses
use the non-routable `.local` TLD, phone numbers are generated with a `0000`
prefix that is unallocated in any numbering plan and therefore **undialable**,
and every row is flagged `is_demo`. The published presentation PDFs contain no
real person's data.

**Install / run / test:** see the Turkish sections above — `cp .env.example
.env`, `pip install -r backend/requirements.txt`, `alembic upgrade head`,
`npm ci && npm run build`, `python -m uvicorn app.main:app`, `pytest -q`.

**Licence:** MIT ([`LICENSE`](LICENSE)). Third-party components and the
copyleft position (including `certifi`, MPL-2.0, shipped at runtime) are
documented in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

**Reporting a vulnerability:** use GitHub's *Security > Report a
vulnerability*; do not open a public issue. See [`SECURITY.md`](SECURITY.md).

---

<div align="center">

MIT Lisansı · Açık kaynak bileşenlerle geliştirildi

</div>
