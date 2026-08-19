# Üçüncü Taraf Bildirimleri / Third-Party Notices

**Proje / Project:** Yapay Zekâ Destekli Yüzme Okulu Yönetim Sistemi
*AI-Powered Swimming School Management System*

**Son güncelleme / Last updated:** 19 Ağustos 2026 / 19 August 2026

---

## TR — Genel Beyan

Bu belge, Yüzme Okulu Yönetim Sistemi'nde kullanılan tüm üçüncü taraf açık kaynak kütüphaneleri ve bunların lisanslarını listeler.

Aşağıdaki yazılım bileşenleri, ilgili lisansları altında dağıtılmaktadır. Her bileşenin telif hakkı, kendi sahiplerine aittir. Bu ürünün kendi kaynak kodu, aşağıda listelenen bileşenlerden bağımsız olarak geliştirilmiştir.

## EN — General Statement

This document lists all third-party open-source libraries used in the Swimming School Management System, together with their licenses.

The software components below are distributed under their respective licenses. Copyright for each component remains with its respective owners. The source code of this product was developed independently of the components listed below.

---

## 1. Lisans Uyumluluk Beyanı / License Compliance Statement

### TR — Türkçe

**1.1. GPL / AGPL / LGPL kaynaklı kod kullanılmamıştır.**

Bu projede, GPL-3.0, AGPL-3.0, LGPL-3.0, MPL-2.0 veya başka herhangi bir *copyleft* lisansa sahip hiçbir projeden **kaynak kodu, veritabanı şeması, migration dosyası, yapılandırma dosyası veya birebir yapısal kopya alınmamıştır.**

Geliştirme öncesinde yürütülen açık kaynak araştırması kapsamında (bkz. `docs/OPEN_SOURCE_RESEARCH.md`) bazı copyleft lisanslı projeler **yalnızca kavramsal düzeyde** incelenmiştir. Bu inceleme, "bu tür bir sistem hangi problemleri çözmek zorundadır?" sorusuna cevap aramakla sınırlı kalmıştır. İncelenen copyleft projeler:

| Proje | Lisans | Alınan | Alınmayan |
|---|---|---|---|
| `wger-project/wger` | AGPL-3.0 | Zaman serisi ölçüm modeli **fikri** | Hiçbir kod, şema veya dosya |
| `alextselegidis/easyappointments` | GPL-3.0 | Çalışma saatleri + istisna **fikri** | Hiçbir kod, şema veya dosya |
| `frappe/education` | GPL-3.0 | Ücret yapısı / ücret talebi ayrımı **fikri** | Hiçbir kod, şema veya dosya |
| `Lehrstuhl-BWL-EvIS/sportyweb` | AGPL-3.0 | Çok kiracılılık kararının erken alınması **fikri** | Hiçbir kod, şema veya dosya |

Telif hakkı hukuku, bir eserin **ifadesini** korur; ardındaki **fikri** değil. "Rezervasyonu kapasiteye karşı doğrula" bir fikirdir ve serbestçe uygulanabilir; bunu gerçekleştiren belirli bir kod ise ifadedir ve ilgili lisansa tabidir. Bu projede yalnızca birinci kategoriden yararlanılmıştır.

**1.2. Yalnızca permissive lisanslı projelerden mimari kavramlar uyarlanmıştır.**

Mimari ilhamın ana kaynağı, MIT / BSD / Apache-2.0 / ISC lisanslı projelerdir:

| Proje | Lisans | Uyarlanan mimari kavram |
|---|---|---|
| `fastapi/full-stack-fastapi-template` | MIT | Katmanlı proje yapısı, girdi/çıktı şema ayrımı, bağımlılık enjeksiyonu |
| `City-of-Helsinki/respa` | MIT | Soyut "Kaynak" rezervasyon modeli, veri olarak rezervasyon kuralları |
| `llazzaro/django-scheduler` | BSD-3-Clause | Event / Occurrence ayrımı, istisna tabanlı tekrar modeli |
| `calcom/cal.com` | MIT | Müsaitliğin çıkarma işlemiyle hesaplanması, UTC disiplini |
| `casbin/pycasbin` | Apache-2.0 | İzinlerin veri olarak modellenmesi, rol mirası, kaynak sahipliği |
| `TimefoldAI/timefold-solver` | Apache-2.0 | Sert / yumuşak kısıt ayrımı |
| `fastapi-users/fastapi-users` | MIT | Token transport/strategy ayrımı, şeffaf hash yükseltme |
| `adilmohak/django-lms` | MIT | Dönem varlığı, zenginleştirilmiş kayıt ara tablosu |
| `jobic10/student-management-using-django` | MIT | İki katmanlı yoklama modeli |
| `AminAliH47/PicoSchool` | Apache-2.0 | Tek kullanıcı + eklenebilir rol profilleri |

Bu projelerin lisansları kod kullanımına da izin vermektedir; buna rağmen **kod kopyalanmamış**, yalnızca mimari desenler kendi domain modelimizde bağımsız olarak uygulanmıştır.

**1.3. Lisanssız projelerden yararlanılmamıştır.**

Lisans dosyası bulunmayan veya standart dışı özel lisans kullanan depoların (`mayerbalintdev/GYM-One`, `mwinamijr/django-scms`, `shreyansh225/Sports-Club-Management-System`) **kodu incelenmemiş ve kullanılmamıştır.**

**1.4. Copyleft bağımlılık yoktur.**

Bu ürünün doğrudan bağımlılıklarının tamamı permissive lisanslıdır. **Projede tek bir GPL, AGPL veya LGPL bağımlılık bulunmamaktadır.**

---

### EN — English

**1.1. No GPL / AGPL / LGPL-derived code has been used.**

**No source code, database schema, migration file, configuration file, or verbatim structural copy** has been taken from any project licensed under GPL-3.0, AGPL-3.0, LGPL-3.0, MPL-2.0, or any other *copyleft* license.

During the open-source research conducted prior to development (see `docs/OPEN_SOURCE_RESEARCH.md`), certain copyleft-licensed projects were examined **at a conceptual level only**. This examination was limited to answering the question "what problems must a system of this kind solve?". The copyleft projects examined were:

| Project | License | What was taken | What was NOT taken |
|---|---|---|---|
| `wger-project/wger` | AGPL-3.0 | The **idea** of a time-series measurement model | No code, schema, or file |
| `alextselegidis/easyappointments` | GPL-3.0 | The **idea** of working hours plus exceptions | No code, schema, or file |
| `frappe/education` | GPL-3.0 | The **idea** of separating fee structure from fee invoice | No code, schema, or file |
| `Lehrstuhl-BWL-EvIS/sportyweb` | AGPL-3.0 | The **idea** of deciding multitenancy early | No code, schema, or file |

Copyright law protects the **expression** of a work, not the **idea** behind it. "Validate a booking against capacity" is an idea and may be freely implemented; the specific code that implements it is expression and is subject to its license. Only the former category was used in this project.

**1.2. Architectural concepts were adapted only from permissively-licensed projects.**

The primary sources of architectural inspiration are projects licensed under MIT / BSD / Apache-2.0 / ISC:

| Project | License | Architectural concept adapted |
|---|---|---|
| `fastapi/full-stack-fastapi-template` | MIT | Layered project structure, input/output schema separation, dependency injection |
| `City-of-Helsinki/respa` | MIT | Abstract "Resource" reservation model, booking rules as data |
| `llazzaro/django-scheduler` | BSD-3-Clause | Event / Occurrence separation, exception-based recurrence |
| `calcom/cal.com` | MIT | Availability computed by subtraction, UTC discipline |
| `casbin/pycasbin` | Apache-2.0 | Permissions modelled as data, role inheritance, resource ownership |
| `TimefoldAI/timefold-solver` | Apache-2.0 | Hard / soft constraint separation |
| `fastapi-users/fastapi-users` | MIT | Token transport/strategy separation, transparent hash upgrade |
| `adilmohak/django-lms` | MIT | Term as first-class entity, enriched enrollment join table |
| `jobic10/student-management-using-django` | MIT | Two-layer attendance model |
| `AminAliH47/PicoSchool` | Apache-2.0 | Single user entity with attachable role profiles |

Although the licenses of these projects would also permit code reuse, **no code was copied**; the architectural patterns were implemented independently within our own domain model.

**1.3. No unlicensed projects were used.**

Repositories without a license file or using non-standard proprietary licenses (`mayerbalintdev/GYM-One`, `mwinamijr/django-scms`, `shreyansh225/Sports-Club-Management-System`) were **neither reviewed at code level nor used.**

**1.4. No copyleft dependencies.**

All direct dependencies of this product are permissively licensed. **The project contains no GPL, AGPL, or LGPL dependency whatsoever.**

---

## 2. Backend Bağımlılıkları / Backend Dependencies (Python)

| Kütüphane / Library | Sürüm / Version | Lisans / License | Telif / Copyright |
|---|---|---|---|
| **FastAPI** | 0.141.1 | MIT | © Sebastián Ramírez |
| **SQLAlchemy** | 2.0.52 | MIT | © Michael Bayer and SQLAlchemy contributors |
| **Pydantic** | 2.13.4 | MIT | © Pydantic Services Inc. and individual contributors |
| **Alembic** | 1.19.1 | MIT | © Michael Bayer and Alembic contributors |
| **Uvicorn** | 0.52.3 | BSD-3-Clause | © Encode OSS Ltd. |
| **passlib** | 1.7.4 | BSD-2-Clause | © Assurance Technologies, LLC |
| **bcrypt** | 5.0.0 | Apache-2.0 | © The Python Cryptographic Authority |
| **python-jose** | 3.5.0 | MIT | © Michael Davis |
| **PyJWT** | 2.13.0 | MIT | © José Padilla |
| **pandas** | 3.0.5 | BSD-3-Clause | © AQR Capital Management LLC, Lambda Foundry Inc., PyData Development Team, and open source contributors |
| **NumPy** | 2.5.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | © NumPy Developers |
| **openpyxl** | 3.1.5 | MIT | © Eric Gazoni, Charlie Clark |
| **ReportLab** | 5.0.0 | BSD-3-Clause | © ReportLab Europe Ltd. |
| **pytest** | 9.1.1 | MIT | © Holger Krekel and pytest contributors |
| **httpx** | 0.28.1 | BSD-3-Clause | © Encode OSS Ltd. |

---

## 3. Frontend Bağımlılıkları / Frontend Dependencies (JavaScript / TypeScript)

| Kütüphane / Library | Sürüm / Version | Lisans / License | Telif / Copyright |
|---|---|---|---|
| **React** | 19.2.8 | MIT | © Meta Platforms, Inc. and affiliates |
| **Vite** | 8.2.1 | MIT | © VoidZero Inc. and Vite contributors |
| **TypeScript** | 7.0.2 | **Apache-2.0** | © Microsoft Corporation |
| **TailwindCSS** | 4.3.3 | MIT | © Tailwind Labs, Inc. |
| **TanStack Query** (`@tanstack/react-query`) | 5.101.4 | MIT | © Tanner Linsley |
| **react-i18next** | 17.0.11 | MIT | © i18next |
| **Recharts** | 3.10.1 | MIT | © Recharts Group |
| **lucide-react** | 1.31.0 | **ISC** | © Lucide Contributors |
| **date-fns** | 4.4.0 | MIT | © Sasha Koss and Lesha Koss |
| **axios** | 1.19.0 | MIT | © Matt Zabriskie and collaborators |
| **zustand** | 5.0.15 | MIT | © Paul Henschel |

---

## 4. Özel Lisans Notları / Special License Notes

### TR

**4.1. Apache-2.0 bileşenleri (`TypeScript`, `bcrypt`).**
Apache License 2.0, değiştirilmiş dosyaların belirtilmesini ve mevcut `NOTICE` bildirimlerinin korunmasını gerektirir. Bu projede her iki bileşen de **değiştirilmeden**, yayınlandıkları hâlleriyle kullanılmaktadır. TypeScript yalnızca bir **derleme zamanı** aracıdır; ürettiği JavaScript çıktısı Apache-2.0 kapsamına girmez.

**4.2. ISC lisansı (`lucide-react`).**
ISC, BSD-2-Clause ile fonksiyonel olarak eşdeğer, sadeleştirilmiş metne sahip permissive bir lisanstır. Telif bildiriminin korunması dışında kısıtlama getirmez.

**4.3. NumPy bileşik lisansı.**
NumPy'ın ana gövdesi BSD-3-Clause'tur. Paket içinde vendor edilmiş bazı bileşenler 0BSD, MIT, Zlib ve CC0-1.0 lisansları taşır. Bunların tamamı permissive'dir ve copyleft yükümlülüğü doğurmaz.

**4.4. JWT kütüphanesi tercihi.**
`PyJWT` (MIT) ve `python-jose` (MIT) her ikisi de permissive'dir. Aktif bakım durumu nedeniyle **PyJWT** birincil tercihtir.

**4.5. passlib + bcrypt birlikte kullanımı.**
`passlib` (BSD-2-Clause) parola hash'leme için arka uç olarak `bcrypt` (Apache-2.0) kullanır. Her iki lisans permissive ve birbiriyle tam uyumludur.

### EN

**4.1. Apache-2.0 components (`TypeScript`, `bcrypt`).**
The Apache License 2.0 requires stating modifications and preserving existing `NOTICE` declarations. Both components are used **unmodified**, exactly as published. TypeScript is a **build-time** tool only; the JavaScript output it produces is not covered by Apache-2.0.

**4.2. ISC license (`lucide-react`).**
ISC is a permissive license functionally equivalent to BSD-2-Clause with simplified wording. It imposes no restriction beyond preserving the copyright notice.

**4.3. NumPy composite license.**
NumPy's main body is BSD-3-Clause. Certain vendored components within the package carry 0BSD, MIT, Zlib, and CC0-1.0 licenses. All are permissive and create no copyleft obligation.

**4.4. JWT library choice.**
Both `PyJWT` (MIT) and `python-jose` (MIT) are permissive. **PyJWT** is the primary choice due to its more active maintenance.

**4.5. passlib + bcrypt combination.**
`passlib` (BSD-2-Clause) uses `bcrypt` (Apache-2.0) as a backend for password hashing. Both licenses are permissive and fully compatible.

---

## 5. Lisans Dağılımı / License Distribution

> **DÜZELTME — 19 Ağustos 2026.** Bu bölümün önceki sürümü "MPL = 0" ve
> "copyleft bağımlılık bulunmamaktadır" diyordu. Bu ifade **doğrudan**
> bağımlılıklar için doğru, **çözülmüş çalışma zamanı ağacı** için yanlıştı.
> Aşağıdaki tablo çözülmüş ağacı esas alır ve tek zayıf-kopyaleft paketi
> açıkça adlandırır.
>
> **CORRECTION — 19 August 2026.** An earlier version of this section stated
> "MPL = 0" and "there are no copyleft dependencies". That was true of the
> *direct* dependencies but false of the *resolved runtime tree*. The table
> below is based on the resolved tree and names the one weak-copyleft package
> explicitly.

### 5.1 Çözülmüş çalışma zamanı ağacı (Python) / Resolved runtime tree

Ölçüm: `backend/requirements.lock.txt` — CPython 3.11 üzerinde `pip install -r
requirements.txt` sonrası `pip freeze` (pip/setuptools hariç), **48 paket**.

| Lisans / License | Paket sayısı / Package count |
|---|---|
| MIT (ve MIT-CMU, MIT AND PSF-2.0 dâhil) | 26 |
| BSD-3-Clause / BSD (metin varyantları dâhil) | 13 |
| Apache-2.0 | 3 |
| ISC | 1 |
| 0BSD | 1 |
| PSF-2.0 | 1 |
| Unlicense (public domain) | 1 |
| Dual (BSD/Apache — `python-dateutil`) | 1 |
| **MPL-2.0 (zayıf kopyaleft)** | **1 — `certifi`** |
| **GPL / AGPL / LGPL** | **0** |
| **Toplam / Total** | **48** |

### 5.2 `certifi` — MPL-2.0, çalışma zamanında dağıtılır

| | |
|---|---|
| Paket | `certifi` (ölçüm anındaki sürüm: `2026.7.22`) |
| Lisans | **MPL-2.0** (Mozilla Public License 2.0) — **zayıf kopyaleft** |
| Nasıl geliyor | `httpx` (doğrudan bağımlılık) → `certifi` |
| Rolü | TLS kök sertifika deposu; çalışma zamanında yüklenir ve dağıtılır |
| İçerik | Mozilla'nın CA kök sertifika listesi |

**Bu bir lisans çatışması DEĞİLDİR.** MPL-2.0 **dosya düzeyinde** kopyalefttir:
yükümlülük yalnızca MPL lisanslı dosyaların *kendisini* değiştirip dağıtmaya
bağlıdır. Bu proje `certifi`'yi değiştirmez; pip aracılığıyla değiştirilmemiş
olarak kurar. MIT lisanslı proje kodunu etkilemez.

**Yükümlülük:** `certifi` yeniden dağıtılırsa (ör. tek dosyalık bir kurulum
paketi içinde), MPL lisanslı dosyalar kendi lisans ve bildirim metinleriyle
birlikte taşınmalı ve kaynak kodun nereden edinileceği belirtilmelidir.
Kaynak: https://github.com/certifi/python-certifi

**This is not a licence conflict.** MPL-2.0 is *file-level* copyleft; the
obligation attaches to modified MPL files only. This project does not modify
`certifi`; pip installs it unmodified. The MIT licence of this project's own
code is unaffected. If `certifi` is redistributed (e.g. inside a bundled
installer), the MPL files must keep their licence and notice text and the
source must be obtainable.

`pathspec` (MPL-2.0) da bağımlılık ağacında görülebilir, ancak yalnızca
`black` üzerinden **geliştirme** bağımlılığıdır ve dağıtılmaz.

### 5.3 Arayüz bağımlılıkları (npm) / Frontend dependencies

Ölçüm: `frontend/package-lock.json`, **çalışma zamanı (dev olmayan) 87 benzersiz
paket**; ayrıca 271 yalnızca-geliştirme paketi (dağıtılmaz).

| Lisans / License | Paket sayısı |
|---|---|
| MIT | 72 |
| ISC | 12 |
| BSD-3-Clause | 3 |
| Apache-2.0 | 1 |
| MIT AND ISC (`victory-vendor`) | 1 |
| **GPL / AGPL / LGPL / MPL** | **0** |

### 5.4 Atıf yükümlülüğü olan paket / Package with an attribution obligation

| Paket | Lisans | Yükümlülük |
|---|---|---|
| `caniuse-lite` | **CC-BY-4.0** | Atıf gerekir. Veri kaynağı: [caniuse.com](https://caniuse.com), Alexis Deveria ve katkıcıları, Creative Commons Attribution 4.0 International lisansı altında. Yalnızca derleme zamanında (`browserslist`/`autoprefixer`) kullanılır; üretilen arayüz paketine dâhil edilmez. |

### 5.5 Yazı tipi / Font

Yayımlanan sunum PDF'leri **Calibri** ile üretilmiştir. Calibri, Microsoft
Corporation'a ait **tescilli** bir yazı tipidir ve Windows/Office lisansı
kapsamında kullanılır; bu depo Calibri'nin yazı tipi dosyalarını **içermez**,
yalnızca üretilen PDF'lerde gömülü alt kümesi bulunur.

`tools/presentation_theme.py`, derleme makinesinde kurulu ise önce **özgür**
bir yazı tipi seçer — sırasıyla **Inter** (SIL OFL 1.1), **Source Sans 3**
(SIL OFL 1.1), **DejaVu Sans** (Bitstream Vera türevi izin) ve **Noto Sans**
(SIL OFL 1.1). Bu depodaki PDF'leri üreten makinede bunların hiçbiri kurulu
olmadığı için Calibri'ye düşülmüştür. `SWS_PRESENTATION_FONT` ortam
değişkeniyle geçersiz kılınabilir.

---

## 6. Doğrulama Yöntemi / Verification Method

**TR:** Doğrudan bağımlılıkların lisansları aşağıdaki resmî kaynaklardan
sorgulanarak doğrulanmıştır (15 Ağustos 2026). **Çözülmüş çalışma zamanı
ağacı** (bölüm 5.1) ayrıca 19 Ağustos 2026'da, kurulu dağıtımların kendi paket
meta verisinden okunarak ölçülmüştür — bu ölçüm, "sıfır kopyaleft" iddiasının
yanlış olduğunu ortaya çıkaran adımdır. Kapsam farkı burada açıkça belirtilir:
*doğrudan* bağımlılık bildirimi ile *çözülmüş* ağaç aynı şey değildir.

**EN:** The licences of the *direct* dependencies were verified against the
official sources below (15 August 2026). The **resolved runtime tree**
(section 5.1) was additionally measured on 19 August 2026 by reading the
installed distributions' own package metadata — this is the step that disproved
the earlier "zero copyleft" claim. The scope difference is stated explicitly
here: a *declared direct* dependency list is not the same thing as a *resolved*
tree.

| Veri türü / Data type | Kaynak / Source |
|---|---|
| Python paket lisansları / Python package licenses | `https://pypi.org/pypi/{package}/json` |
| npm paket lisansları / npm package licenses | `https://registry.npmjs.org/{package}/latest` |
| Depo meta verisi / Repository metadata | `https://api.github.com/repos/{owner}/{repo}` |
| Belirsiz lisanslar / Ambiguous licenses | Ham `LICENSE` dosyası / Raw `LICENSE` file |

---

## 7. Bakım / Maintenance

**TR:**
- Yeni bir bağımlılık eklenmeden **önce** lisansı doğrulanmalı ve bu belgeye eklenmelidir.
- **Güçlü kopyaleft (GPL, AGPL, LGPL) lisanslı hiçbir bağımlılık eklenemez.**
- **Zayıf kopyaleft (MPL-2.0, EPL) yasak değildir**, ancak bilinçli bir karar
  gerektirir: dosya düzeyindeki yükümlülük bölüm 5.2'deki gibi belgelenmelidir.
  Politika, çözülmüş ağaçta zaten bulunan `certifi`'yi yasaklayacak biçimde
  yazılmamalıdır — uygulanamayan bir politika, politika değildir.
- Politika **çözülmüş ağaca** uygulanır, yalnızca doğrudan bağımlılıklara değil.
  Ölçüm için `backend/requirements.lock.txt` kullanılır.
- Bağımlılık sürümleri yükseltildiğinde lisans değişikliği olup olmadığı kontrol edilmelidir (lisanslar zaman içinde değişebilir).
- CI hattına otomatik lisans taraması eklenmesi ve **güçlü kopyaleft** tespitinde derlemenin başarısız olması önerilir. Bu şu an uygulanmamaktadır.

**EN:**
- The licence of any new dependency must be verified and added to this document **before** it is introduced.
- **No strong-copyleft (GPL, AGPL, LGPL) dependency may be added.**
- **Weak copyleft (MPL-2.0, EPL) is not forbidden** but requires a conscious
  decision, with the file-level obligation documented as in section 5.2. The
  policy must not be written so as to forbid `certifi`, which the resolved tree
  already contains — an unenforceable policy is not a policy.
- The policy applies to the **resolved tree**, not only to direct dependencies.
  Use `backend/requirements.lock.txt` as the measurement basis.
- When dependency versions are upgraded, check whether the licence has changed.
- Adding automated licence scanning to CI, failing the build on **strong**
  copyleft, is recommended. It is not implemented today.

---

## 8. Kapsam ve doğrulanabilirlik notu / Scope and verifiability note

**TR:** Bölüm 1'deki "copyleft projelerden kod alınmadı" beyanı bir
**beyandır**, depo içinden doğrulanabilir bir kanıt değildir. Doğrulanabilir
olan şudur: depoda satır içine kopyalanmış (vendored) üçüncü taraf kaynak
dizini **yoktur**; bütün bağımlılıklar paket yöneticisi üzerinden gelir ve
`backend/requirements.lock.txt` ile `frontend/package-lock.json` içinde
sürümleriyle sabitlenmiştir. Bu ayrımı okuyucunun bilmesi gerekir.

**EN:** The statement in section 1 that no code was taken from copyleft
projects is a **declaration**, not evidence verifiable from inside the
repository. What *is* verifiable: there is no vendored third-party source
directory; every dependency arrives through a package manager and is pinned in
`backend/requirements.lock.txt` and `frontend/package-lock.json`. Readers
should know the difference.

---

## 9. İlgili Belgeler / Related Documents

- `docs/OPEN_SOURCE_RESEARCH.md` — Ayrıntılı açık kaynak araştırması / open-source research
- `backend/requirements.lock.txt` — Çözülmüş çalışma zamanı ağacı / resolved runtime tree
- `sbom.spdx.json`, `sbom.cdx.json` — Yazılım malzeme listesi / software bill of materials
- `LICENSE` — Bu projenin lisansı (MIT) / this project's licence (MIT)

---

*Bu belge lisans uyumluluk denetimlerinde kanıt niteliğindedir.*
*This document serves as evidence in licence compliance audits.*
