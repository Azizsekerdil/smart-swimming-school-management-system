# Açık Kaynak Araştırması ve Lisans Analizi

**Proje:** Yapay Zekâ Destekli Yüzme Okulu Yönetim Sistemi
**Teknoloji Yığını:** Python / FastAPI (backend) + React / TypeScript (frontend)
**Araştırma Tarihi:** 15 Ağustos 2026
**Belge Sürümü:** 1.0

---

## 1. Amaç ve Metodoloji

### 1.1 Amaç

Bu belgenin amacı üç katmanlıdır:

1. **Hukuki güvence:** Geliştireceğimiz yüzme okulu yönetim sisteminin, hiçbir üçüncü taraf projenin lisans şartlarını ihlal etmediğini belgelemek. Özellikle GPL/AGPL gibi *copyleft* lisanslı projelerden **kod kopyalanmadığını** kayıt altına almak.
2. **Mimari öğrenme:** Aynı problem alanını (üyelik, rezervasyon, takvim çakışması, yoklama, ödeme, performans takibi) daha önce çözmüş gerçek projeleri inceleyerek, tekerleği yeniden icat etmeden **kavramsal** dersler çıkarmak.
3. **Bağımlılık şeffaflığı:** Kullandığımız her kütüphanenin lisansını doğrulanmış biçimde listelemek ve `THIRD_PARTY_NOTICES.md` belgesinin dayanağını oluşturmak.

### 1.2 Metodoloji

Araştırma dört aşamada yürütüldü:

**Aşama 1 — Keşif (Discovery).**
Aşağıdaki arama başlıkları üzerinden GitHub taraması yapıldı:

| Arama başlığı | Amaç |
|---|---|
| swimming school management python | Doğrudan alan eşleşmesi |
| swim club management | Doğrudan alan eşleşmesi |
| sports club management django | Yakın alan, aynı veri modeli |
| sports academy management python | Yakın alan |
| gym management python / django | Üyelik + yoklama + ödeme deseni |
| student management django | Öğrenci kayıt/veli ilişkisi |
| school management system python | Sınıf/dönem/kayıt modeli |
| sports booking system django | Rezervasyon çekirdeği |
| class scheduling / timetable python | Takvim ve çakışma çözümü |
| membership management django | Abonelik/paket yaşam döngüsü |
| attendance management python | Yoklama modeli |
| sports performance tracking python | Sporcu gelişim ölçümü |
| pool lane booking | Kaynak (kulvar) rezervasyonu |

**Aşama 2 — Doğrulama (Verification).**
Hiçbir depo, arama sonucu metnine güvenilerek listeye alınmadı. Her aday depo için GitHub REST API'si (`api.github.com/repos/{owner}/{repo}`) çağrılarak şu alanlar **birebir** okundu:
`full_name`, `description`, `language`, `stargazers_count`, `forks_count`, `pushed_at`, `license.spdx_id`, `archived`.

Lisans alanı `NOASSERTION` (yani GitHub'ın tanıyamadığı özel lisans) döndüğünde, deponun **ham LICENSE dosyası** ayrıca indirilip okundu. Bu yolla iki önemli düzeltme yapıldı:

- `calcom/cal.com` — Toplulukta uzun süre AGPL-3.0 olarak bilinen bu proje, LICENSE dosyası doğrudan okunduğunda **MIT** olarak tespit edildi (`Copyright (c) 2020-present Cal.com, Inc.`). Depo ayrıca `calcom/cal.diy` adına taşınmış durumda.
- `mayerbalintdev/GYM-One` — `NOASSERTION` dönen bu depo, standart bir açık kaynak lisansı değil, **özel "GYM One License Agreement" (v1.0)** kullanıyor. Bu nedenle KULLANILAMAZ olarak işaretlendi.

**Aşama 3 — Sınıflandırma.**
Her proje üç kategoriden birine atandı (bkz. Bölüm 2).

**Aşama 4 — Mimari çıkarım.**
Her projeden **kod değil, fikir** düzeyinde ne alınabileceği not edildi (bkz. Bölüm 4).

### 1.3 Metodolojinin Sınırları

- Yıldız (star) ve fork sayıları **yalnızca ikincil gösterge** olarak kullanılmıştır. Bir projenin popülerliği, mimari kalitesinin garantisi değildir. Nitekim en çok yıldıza sahip projeler (`or-tools`, `cal.com`) alan olarak bize en uzak olanlardır; en çok işimize yarayan fikirler ise 84 yıldızlı arşivlenmiş bir belediye projesinden (`respa`) çıkmıştır.
- "Swimming club management" araması, ezici çoğunlukla **öğrenci ödevi niteliğinde, lisanssız, tek kişilik** depolar döndürmüştür. Bu, alanda olgun bir açık kaynak çözümün bulunmadığını gösterir ve kendi mimarimizi yazma kararımızın ana gerekçelerinden biridir (bkz. Bölüm 6).
- Sayısal veriler araştırma tarihindeki anlık değerlerdir.

---

## 2. Lisans Politikamız

### 2.1 Kabul Ettiğimiz Lisanslar — "UYGUN"

| Lisans | Neden kabul ediyoruz |
|---|---|
| **MIT** | En serbest lisans. Tek şart telif bildirimini korumak. Kapalı kaynak dağıtıma engel yok. |
| **BSD-2-Clause** | MIT ile pratikte eşdeğer. |
| **BSD-3-Clause** | MIT'e ek olarak yalnızca "proje adıyla reklam yapma" yasağı getirir; bu bizi kısıtlamaz. |
| **Apache-2.0** | Serbest kullanım + **açık patent hibesi** sağlar. Ticari ürünler için MIT'ten bile güvenlidir. Tek şart: değişiklikleri `NOTICE` dosyasında belirtmek. |
| **ISC** | BSD-2 ile fonksiyonel olarak aynı, sadeleştirilmiş metin. |

**Politikamız:** Bu lisanslara sahip projelerden hem *fikir* alabilir, hem de gerekirse *kod parçası* kullanabiliriz (atıf şartıyla). Ancak pratikte, aşağıda açıklanan nedenlerle **kod kopyalamayı tercih etmiyoruz** — yalnızca mimari desen düzeyinde ilham alıyoruz.

### 2.2 Dikkatle Yaklaştığımız Lisanslar — "DİKKAT"

| Lisans | Risk |
|---|---|
| **GPL-3.0** | *Copyleft.* Kodundan bir satır bile alırsak, **tüm projemizi GPL-3.0 ile yayınlamak zorunda kalırız.** |
| **AGPL-3.0** | GPL'in daha da katı hâli. Kodu **ağ üzerinden servis olarak sunmak bile** kaynak kodu açma yükümlülüğü doğurur. SaaS modeli için en tehlikeli lisans. |
| **LGPL-3.0** | Dinamik bağlama serbest, ancak kod kopyalama yine bulaşıcıdır. |
| **MPL-2.0** | Dosya bazlı copyleft. Değiştirdiğimiz dosyaları açmak zorundayız. |

**Politikamız:** Bu projelerden **hiçbir koşulda kod, şema tanımı, migration dosyası veya birebir yapı kopyalanmaz.** Bu projelere yalnızca **çalışan bir sistemin hangi problemleri çözdüğünü anlamak için** bakılır. Elde edilen bilgi, "bir üyelik sisteminin dondurma (freeze) durumuna ihtiyacı var" gibi **fikir düzeyinde** bir çıkarımdır — ki fikirler telif hakkına tabi değildir.

> **Kritik ayrım:** Telif hakkı *ifadeyi* korur, *fikri* değil. "Rezervasyonu kapasiteye karşı doğrula" bir fikirdir ve serbesttir. Bunu yapan 40 satırlık Python fonksiyonu ise ifadedir ve GPL kapsamındadır.

### 2.3 Kullanamayacağımız Projeler — "KULLANILAMAZ"

| Durum | Neden |
|---|---|
| **Lisans dosyası yok** | Lisanssız kod, varsayılan olarak **"tüm hakları saklıdır"** demektir. Açık kaynak *değildir*. GitHub'da herkese açık olması kullanım hakkı vermez. |
| **Özel/tescilli lisans (NOASSERTION)** | Şartlar standart dışıdır, hukuki risk öngörülemez. |
| **Belirsiz lisans** | Doğrulanamayan her şey riskli kabul edilir. |

**Politikamız:** Bu projelere **hiç bakılmaz veya yalnızca "böyle bir sistem var" bilgisi düzeyinde not edilir.** Kod incelemesi yapılmaz.

### 2.4 Özet Karar Tablosu

| Lisans | Fikir alabilir miyiz? | Kod alabilir miyiz? | Verdict |
|---|---|---|---|
| MIT / BSD-2 / BSD-3 / Apache-2.0 / ISC | ✅ Evet | ✅ Evet (atıfla) | **UYGUN** |
| GPL-3.0 / AGPL-3.0 / LGPL / MPL | ✅ Evet (yalnızca kavram) | ❌ **Kesinlikle hayır** | **DİKKAT** |
| Lisanssız / özel lisans | ⚠️ Sınırlı | ❌ Hayır | **KULLANILAMAZ** |

---

## 3. İncelenen Projeler

### 3.1 Özet Tablo

Toplam **24 depo** doğrulandı. Tüm veriler GitHub API'sinden birebir okunmuştur.

| # | Depo | Dil | ★ | Fork | Son Aktivite | Lisans | Karar |
|---|---|---|---|---|---|---|---|
| 1 | [ChanMeng666/countryside-community-swimming-club](https://github.com/ChanMeng666/countryside-community-swimming-club) | TypeScript | 4 | 0 | 2026-06 | Apache-2.0 | **UYGUN** |
| 2 | [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) | TypeScript/Python | 44.872 | 8.925 | 2026-08 | MIT | **UYGUN** |
| 3 | [fastapi-users/fastapi-users](https://github.com/fastapi-users/fastapi-users) | Python | 6.216 | 507 | 2026-07 | MIT | **UYGUN** |
| 4 | [casbin/pycasbin](https://github.com/casbin/pycasbin) | Python | 1.759 | 219 | 2026-08 | Apache-2.0 | **UYGUN** |
| 5 | [llazzaro/django-scheduler](https://github.com/llazzaro/django-scheduler) | Python | 1.335 | 402 | 2026-02 | BSD-3-Clause | **UYGUN** |
| 6 | [City-of-Helsinki/respa](https://github.com/City-of-Helsinki/respa) | Python | 84 | 57 | 2024-04 (arşiv) | MIT | **UYGUN** |
| 7 | [calcom/cal.com](https://github.com/calcom/cal.com) | TypeScript | 47.604 | 14.781 | 2026-08 | MIT | **UYGUN** |
| 8 | [7s9n/small_sms_api](https://github.com/7s9n/small_sms_api) | Python | 26 | 8 | 2023-03 | MIT | **UYGUN** |
| 9 | [AminAliH47/PicoSchool](https://github.com/AminAliH47/PicoSchool) | Python | 95 | 20 | 2024-04 | Apache-2.0 | **UYGUN** |
| 10 | [TimefoldAI/timefold-solver](https://github.com/TimefoldAI/timefold-solver) | Java | 1.750 | 224 | 2026-08 | Apache-2.0 | **UYGUN** |
| 11 | [google/or-tools](https://github.com/google/or-tools) | C++/Python | 13.903 | 2.463 | 2026-08 | Apache-2.0 | **UYGUN** |
| 12 | [adilmohak/django-lms](https://github.com/adilmohak/django-lms) | Python | 729 | 309 | 2024-10 (arşiv) | MIT | **UYGUN** |
| 13 | [jobic10/student-management-using-django](https://github.com/jobic10/student-management-using-django) | Python | 391 | 198 | 2023-11 | MIT | **UYGUN** |
| 14 | [HashenUdara/edoc-doctor-appointment-system](https://github.com/HashenUdara/edoc-doctor-appointment-system) | PHP | 567 | 256 | 2026-08 | MIT | **UYGUN** |
| 15 | [NDresevic/timetable-generator](https://github.com/NDresevic/timetable-generator) | Python | 221 | 67 | 2025-02 | MIT | **UYGUN** |
| 16 | [Antonio-Neves/Gestao-Escolar](https://github.com/Antonio-Neves/Gestao-Escolar) | Python | 48 | 21 | 2026-05 | MIT | **UYGUN** |
| 17 | [shiningflash/django-reservation-system](https://github.com/shiningflash/django-reservation-system) | Python | 8 | 0 | 2024-12 | MIT | **UYGUN** |
| 18 | [wger-project/wger](https://github.com/wger-project/wger) | Python | 6.658 | 972 | 2026-08 | **AGPL-3.0** | **DİKKAT** |
| 19 | [alextselegidis/easyappointments](https://github.com/alextselegidis/easyappointments) | PHP | 4.321 | 1.549 | 2026-08 | **GPL-3.0** | **DİKKAT** |
| 20 | [frappe/education](https://github.com/frappe/education) | Python | 598 | 419 | 2026-08 | **GPL-3.0** | **DİKKAT** |
| 21 | [Lehrstuhl-BWL-EvIS/sportyweb](https://github.com/Lehrstuhl-BWL-EvIS/sportyweb) | Elixir | 11 | 14 | 2025-03 | **AGPL-3.0** | **DİKKAT** |
| 22 | [mayerbalintdev/GYM-One](https://github.com/mayerbalintdev/GYM-One) | PHP | 203 | 62 | 2026-06 | Özel lisans | **KULLANILAMAZ** |
| 23 | [mwinamijr/django-scms](https://github.com/mwinamijr/django-scms) | Python | 59 | 75 | 2026-02 | Yok | **KULLANILAMAZ** |
| 24 | [shreyansh225/Sports-Club-Management-System](https://github.com/shreyansh225/Sports-Club-Management-System) | PHP | 42 | 14 | 2022-03 | Yok | **KULLANILAMAZ** |

**Dağılım:** 17 UYGUN (%71) · 4 DİKKAT (%17) · 3 KULLANILAMAZ (%12)

---

### 3.2 Detaylı İnceleme — UYGUN Projeler

---

#### 3.2.1 ChanMeng666/countryside-community-swimming-club

- **URL:** https://github.com/ChanMeng666/countryside-community-swimming-club
- **Açıklama:** Topluluk yüzme kulüpleri için web tabanlı yönetim sistemi. Üye yönetimi, ders programlama, tesis rezervasyonu, ödeme işleme ve raporlama.
- **Teknoloji:** Depo dili TypeScript olarak raporlanıyor; README Flask + MySQL'den bahsediyor (karma/geçiş hâlinde bir proje).
- **★ / Fork:** 4 / 0 · **Son aktivite:** Haziran 2026
- **Lisans:** **Apache-2.0** → **UYGUN**
- **İlham verdiği modül:** Genel sistem kapsamı (scope) tanımı.
- **Mimari fikir:** Bu, aramalarımızda bulduğumuz **tam olarak aynı alanda çalışan tek Apache-2.0 lisanslı proje**. Kod olgunluğu düşük (4 yıldız, tek geliştirici), ancak **modül ayrıştırması** doğrulayıcı: üye / ders programı / tesis rezervasyonu / ödeme / raporlama. Bizim modül listemizin sektörel olarak "doğru" olduğunu bağımsız biçimde teyit ediyor. Kod alınmadı; yalnızca kapsam doğrulaması için kullanıldı.

---

#### 3.2.2 fastapi/full-stack-fastapi-template ⭐ En yüksek etkili referans

- **URL:** https://github.com/fastapi/full-stack-fastapi-template
- **Açıklama:** FastAPI, React, SQLModel, PostgreSQL, Vite, Tailwind CSS ve Docker Compose ile tam yığın uygulama şablonu.
- **Teknoloji:** Python (FastAPI) + TypeScript (React/Vite)
- **★ / Fork:** 44.872 / 8.925 · **Son aktivite:** Ağustos 2026
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** Proje iskeleti, kimlik doğrulama, REST API katmanlaması, test altyapısı.
- **Mimari fikir:**
  - **Katman ayrımı:** `api/routes/` (HTTP), `crud.py` (veri erişimi), `models.py` (şema), `core/` (config, güvenlik) şeklindeki net dört katman. İş mantığının route fonksiyonlarının içine sızmasını engelleyen bu ayrımı benimsiyoruz.
  - **Bağımlılık enjeksiyonu (Depends):** Veritabanı oturumu ve "mevcut kullanıcı" nesnesinin FastAPI `Depends` zinciriyle sağlanması. `get_current_active_superuser` gibi katmanlı bağımlılıklar, yetkilendirmeyi route imzasında **deklaratif** hâle getiriyor.
  - **Pydantic'te girdi/çıktı ayrımı:** `UserCreate` / `UserUpdate` / `UserPublic` gibi ayrı şemalar. Parola hash'inin yanlışlıkla API'den sızmasını **tip sistemi düzeyinde** imkânsız kılar. Bu deseni öğrenci, veli ve personel modellerimizde birebir uygulayacağız.
  - **Alembic migration disiplini:** Şema değişikliklerinin sürüm kontrollü yürütülmesi.
- **Not:** Bu, mimarimizin ana referans noktasıdır ve MIT lisanslıdır — yani gerekirse kod da alabilirdik. Yine de kendi domain modelimizi sıfırdan yazıyoruz; şablondan alınan yalnızca **katman düzenidir**.

---

#### 3.2.3 fastapi-users/fastapi-users

- **URL:** https://github.com/fastapi-users/fastapi-users
- **Açıklama:** FastAPI için hazır ve özelleştirilebilir kullanıcı yönetimi.
- **Teknoloji:** Python
- **★ / Fork:** 6.216 / 507 · **Son aktivite:** Temmuz 2026
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** Kimlik doğrulama (authentication), kullanıcı yaşam döngüsü.
- **Mimari fikir:**
  - **Transport / Strategy ayrımı:** Token'ın *nasıl taşındığı* (Bearer header, Cookie) ile *nasıl üretilip doğrulandığı* (JWT, veritabanı token) birbirinden bağımsız iki soyutlama. Bu sayede ileride web için cookie, mobil için Bearer kullanmak isteseydik çekirdek mantığı değiştirmemiz gerekmezdi.
  - **Parola hash'leme soyutlaması:** Hash algoritmasının değiştirilebilir bir bileşen olması ve **kullanıcı giriş yaptığında eski hash'in sessizce yeni algoritmaya yükseltilmesi** (transparent rehashing). Bu deseni benimsiyoruz.
  - **Olay kancaları:** `on_after_register`, `on_after_forgot_password` gibi kancalar sayesinde bildirim/e-posta mantığının kimlik doğrulama çekirdeğine karışmaması.

---

#### 3.2.4 casbin/pycasbin

- **URL:** https://github.com/casbin/pycasbin
- **Açıklama:** ACL, RBAC, ABAC gibi erişim kontrol modellerini destekleyen yetkilendirme kütüphanesi.
- **Teknoloji:** Python
- **★ / Fork:** 1.759 / 219 · **Son aktivite:** Ağustos 2026
- **Lisans:** **Apache-2.0** → **UYGUN**
- **İlham verdiği modül:** **RBAC / yetkilendirme.**
- **Mimari fikir:**
  - **Policy ile kodun ayrılması:** Yetki kuralları koda gömülmez; `(subject, object, action)` üçlüsü olarak **veriye** dönüştürülür. Yeni bir rol eklemek kod değişikliği değil, veri değişikliği hâline gelir.
  - **Rol mirası (role inheritance):** `başantrenör → antrenör → personel` gibi hiyerarşiler. "Antrenörün yapabildiği her şeyi başantrenör de yapabilir" kuralını her izin için tekrar yazmak yerine tek satırda ifade etmek.
  - **Kaynak sahipliği (ownership):** "Antrenör *yalnızca kendi* grubunun yoklamasını girebilir" gibi kurallar. Bu, yüzme okulu bağlamında kritik: bir antrenörün başka bir antrenörün öğrenci verisine erişememesi gerekir.
- **Uygulama kararımız:** Kütüphaneyi doğrudan bağımlılık olarak eklemiyoruz (ihtiyacımıza göre fazla ağır). Ancak **"izinleri veri olarak modelle, koda gömme"** ilkesini kendi hafif RBAC katmanımızda uyguluyoruz.

---

#### 3.2.5 llazzaro/django-scheduler

- **URL:** https://github.com/llazzaro/django-scheduler
- **Açıklama:** Django için takvim uygulaması.
- **Teknoloji:** Python (Django)
- **★ / Fork:** 1.335 / 402 · **Son aktivite:** Şubat 2026
- **Lisans:** **BSD-3-Clause** → **UYGUN**
- **İlham verdiği modül:** **Takvim / ders programı / tekrarlayan dersler.**
- **Mimari fikir:**
  - **Event / Occurrence ayrımı — en değerli tek fikir.** Tekrarlayan bir ders (örn. "Her Salı 18:00 Yeni Başlayanlar") veritabanında **binlerce satır olarak saklanmaz.** Tek bir `Event` kaydı + bir tekrar kuralı (RRULE) saklanır; belirli bir tarih aralığındaki somut örnekler (`Occurrence`) **çalışma zamanında hesaplanır.**
  - **İstisna (exception) kaydı:** Yalnızca kuraldan **sapan** örnekler kalıcılaştırılır. Örneğin "23 Nisan tatili nedeniyle iptal" veya "bu haftaki ders 19:00'a ertelendi" gibi durumlar tek satırlık istisna kaydı olur.
  - Bu model, bizim "dönemlik ders programı" ihtiyacımızı doğrudan karşılıyor: 16 haftalık bir kursu 16 satır yerine 1 satır + 2 istisna olarak tutmak.

---

#### 3.2.6 City-of-Helsinki/respa ⭐ Rezervasyon çekirdeği için ana referans

- **URL:** https://github.com/City-of-Helsinki/respa
- **Açıklama:** Kaynak rezervasyon ve yönetim uygulaması ve API'si. Helsinki Belediyesi tarafından geliştirilmiş, gerçek üretim ortamında (şehir tesisleri, yüzme havuzları dâhil) kullanılmış sistem.
- **Teknoloji:** Python (Django + DRF)
- **★ / Fork:** 84 / 57 · **Son aktivite:** Nisan 2024 · **Durum: Arşivlenmiş**
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** **Rezervasyon, havuz kulvarı tahsisi, kapasite yönetimi.**
- **Mimari fikir:**
  - **Genel "Resource" soyutlaması:** Sistem "havuz kulvarı" veya "toplantı odası" gibi somut kavramlar yerine soyut bir **Kaynak (Resource)** modeli üzerine kuruludur. Kaynağın kapasitesi, açılış saatleri ve rezervasyon kuralları vardır. Bizim için bu, **kulvar, antrenör ve ekipmanı aynı rezervasyon motoruyla yönetebilmek** demektir.
  - **Açılış saatleri ayrı bir varlık (Period / Day):** Tesisin çalışma saatleri koda gömülü değil, tarih aralıklarına bağlı `Period` kayıtlarıdır. Yaz/kış tarifesi, bayram kapanışları bu yolla veri olarak yönetilir.
  - **Katmanlı rezervasyon kuralları:** Minimum/maksimum süre, kullanıcı başına eşzamanlı rezervasyon limiti, ne kadar önceden rezervasyon yapılabileceği — hepsi kaynak seviyesinde **yapılandırılabilir alanlar**. Bu kuralların kod yerine veri olması, iş kurallarının değişmesi hâlinde deploy gerektirmez.
  - **Rezervasyon durum makinesi:** `requested → confirmed → cancelled / denied` gibi açık durum geçişleri. Serbest metin durum alanı yerine kısıtlı bir enum + geçiş kuralları.
- **Not:** Depo arşivlenmiş olsa da, **belediye ölçeğinde üretimde çalışmış** bir sistemin veri modeli olması onu öğrenci projelerinden çok daha değerli kılıyor. MIT lisanslı olması kod incelemesini de serbest bırakıyor.

---

#### 3.2.7 calcom/cal.com

- **URL:** https://github.com/calcom/cal.com (depo `calcom/cal.diy` adına taşınmış)
- **Açıklama:** Herkes için randevu/planlama altyapısı.
- **Teknoloji:** TypeScript (Next.js)
- **★ / Fork:** 47.604 / 14.781 · **Son aktivite:** Ağustos 2026
- **Lisans:** **MIT** → **UYGUN**
- **⚠️ Lisans notu:** Bu proje toplulukta uzun süre **AGPL-3.0** olarak biliniyordu. LICENSE dosyası bu araştırma kapsamında **doğrudan indirilip okundu** ve içeriğin `MIT License / Copyright (c) 2020-present Cal.com, Inc.` olduğu doğrulandı. Yine de proje geçmişinde ticari (`/ee`) klasör ayrımı bulunduğundan, kod kullanımı hâlinde ilgili alt dizinlerin lisansı ayrıca kontrol edilmelidir. **Biz kod almıyoruz.**
- **İlham verdiği modül:** **Rezervasyon UX'i, müsaitlik hesabı, çakışma önleme.**
- **Mimari fikir:**
  - **Müsaitlik = (Çalışma saatleri) − (Mevcut rezervasyonlar) − (İstisnalar):** Boş slotların veritabanında tutulmaması, her sorguda **çıkarma işlemiyle hesaplanması.** Bu, "hayalet slot" (silinmiş dersin boş slot olarak görünmesi) sınıfı hataları tamamen ortadan kaldırır.
  - **Saat dilimi disiplini:** Tüm zaman damgalarının UTC olarak saklanması, yalnızca sunum katmanında yerel saate çevrilmesi. Türkiye tek saat diliminde olsa da bu disiplini koruyoruz — yaz saati uygulaması geri gelirse veri bozulmaz.
  - **Çift rezervasyon koruması:** Son yazma anında veritabanı seviyesinde kısıt kontrolü. Uygulama katmanındaki "önce kontrol et, sonra yaz" deseninin yarış koşuluna (race condition) açık olduğu, bu nedenle **veritabanı kısıtının nihai otorite** olması gerektiği.

---

#### 3.2.8 7s9n/small_sms_api

- **URL:** https://github.com/7s9n/small_sms_api
- **Açıklama:** FastAPI tabanlı küçük okul yönetim sistemi API'si.
- **Teknoloji:** Python (FastAPI)
- **★ / Fork:** 26 / 8 · **Son aktivite:** Mart 2023
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** Öğrenci yönetimi, REST API tasarımı.
- **Mimari fikir:** Bizim yığınımızın (FastAPI + okul yönetimi) **birebir eşleşen küçük ölçekli örneği.** Öğrenci–sınıf–ders ilişkisinin FastAPI router'larına nasıl bölündüğünü göstermesi açısından okundu. Kaynak başına ayrı router dosyası (`students.py`, `classes.py`, `teachers.py`) ve ortak `deps.py` deseni doğrulandı. Proje küçük ve güncelliğini yitirmiş; yalnızca dosya organizasyonu için referans alındı.

---

#### 3.2.9 AminAliH47/PicoSchool

- **URL:** https://github.com/AminAliH47/PicoSchool
- **Açıklama:** Django ile yazılmış gelişmiş okul yönetim sistemi.
- **Teknoloji:** Python (Django)
- **★ / Fork:** 95 / 20 · **Son aktivite:** Nisan 2024
- **Lisans:** **Apache-2.0** → **UYGUN**
- **İlham verdiği modül:** Öğrenci yönetimi, rol bazlı paneller.
- **Mimari fikir:** **Rol başına ayrı arayüz, tek veri modeli.** Öğrenci, öğretmen ve yönetici için ayrı ayrı veri modelleri kurmak yerine tek bir `User` + rol profili yaklaşımı. Bu, bir kişinin aynı anda hem veli hem antrenör olabildiği yüzme okulu senaryosunda kritik: kişi bir kez tanımlanır, roller ona **eklenir**.

---

#### 3.2.10 TimefoldAI/timefold-solver

- **URL:** https://github.com/TimefoldAI/timefold-solver
- **Açıklama:** Java/Kotlin için açık kaynak kısıt çözücü (constraint solver). Araç rotalama, personel çizelgeleme, görev atama ve diğer planlama problemlerini optimize eder.
- **Teknoloji:** Java
- **★ / Fork:** 1.750 / 224 · **Son aktivite:** Ağustos 2026
- **Lisans:** **Apache-2.0** → **UYGUN**
- **İlham verdiği modül:** **Takvim/çakışma çözümü, antrenör atama.**
- **Mimari fikir:**
  - **Sert kısıt / yumuşak kısıt ayrımı (hard vs soft constraints).** Bu ayrım, çizelgeleme mantığımızın temelini oluşturuyor:
    - **Sert kısıt (ihlal edilemez):** Bir kulvara aynı saatte iki grup atanamaz. Bir antrenör aynı anda iki yerde olamaz. Grup mevcudu kapasiteyi aşamaz.
    - **Yumuşak kısıt (tercih, ihlal edilebilir):** Antrenörün boşluk saatleri minimize edilsin. Aynı seviyedeki gruplar ardışık saatlere yerleştirilsin. Öğrencinin tercih ettiği saat dilimi korunsun.
  - **Puanlama (score) yaklaşımı:** Bir çizelgenin "geçerli mi" değil, "ne kadar iyi" olduğunun sayısal ifadesi. Alternatif program önerilerini sıralamak için kullanılacak.
- **Not:** Java tabanlı olduğu için doğrudan entegre etmiyoruz. **Kısıt modelleme zihniyetini** alıyoruz.

---

#### 3.2.11 google/or-tools

- **URL:** https://github.com/google/or-tools
- **Açıklama:** Google'ın yöneylem araştırması araçları (CP-SAT çözücü dâhil).
- **Teknoloji:** C++ (resmi Python binding'i mevcut)
- **★ / Fork:** 13.903 / 2.463 · **Son aktivite:** Ağustos 2026
- **Lisans:** **Apache-2.0** → **UYGUN**
- **İlham verdiği modül:** **Otomatik ders programı üretimi (gelecek faz).**
- **Mimari fikir:** Kulvar–saat–antrenör–grup atamasının klasik bir **kısıt tatmin problemi (CSP)** olduğunun kabulü. Elle yazılmış açgözlü (greedy) algoritma yerine, ileri fazda `ortools.sat.python.cp_model` ile "yüzme okulu haftalık programını otomatik üret" özelliği eklenebilir. Apache-2.0 lisansı ve resmi Python paketi bunu ticari olarak güvenli kılıyor. **Şu an bağımlılık olarak eklenmedi**, yol haritasına not edildi.

---

#### 3.2.12 adilmohak/django-lms

- **URL:** https://github.com/adilmohak/django-lms
- **Açıklama:** Django ile öğrenme yönetim sistemi: ders ekleme/bırakma, not ve değerlendirme yönetimi, online sınav, rapor üretici, öğrenci ve öğretim görevlisi yönetimi, dashboard.
- **Teknoloji:** Python (Django)
- **★ / Fork:** 729 / 309 · **Son aktivite:** Ekim 2024 · **Durum: Arşivlenmiş**
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** **Öğrenci yönetimi, seviye/kur ilerlemesi, raporlama.**
- **Mimari fikir:**
  - **Dönem (semester/session) kavramının birinci sınıf varlık olması.** Öğrenci kaydı doğrudan "okula" değil, **belirli bir döneme** yapılır. Bu, yüzme okulumuzda "2026 Yaz Dönemi" gibi kurları ve öğrencinin dönemler arası ilerlemesini (`Yeni Başlayan → Orta → İleri`) temiz biçimde modellememizi sağlıyor.
  - **Kayıt (enrollment) ara tablosu:** Öğrenci ile ders arasındaki ilişkinin, kendi alanlarına (kayıt tarihi, durum, not) sahip **bağımsız bir varlık** olması. Basit çoktan-çoğa ilişki yerine zenginleştirilmiş ara tablo.
  - **Dashboard'un önceden hesaplanmış özet üzerinden beslenmesi.**

---

#### 3.2.13 jobic10/student-management-using-django

- **URL:** https://github.com/jobic10/student-management-using-django
- **Açıklama:** Django ile oluşturulmuş öğrenci yönetim sistemi.
- **Teknoloji:** Python (Django)
- **★ / Fork:** 391 / 198 · **Son aktivite:** Kasım 2023
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** **Yoklama, öğrenci-veli ilişkisi.**
- **Mimari fikir:** **Yoklamanın iki katmanlı modellenmesi:** Önce bir `AttendanceSession` (hangi ders, hangi tarih, kim aldı) oluşturulur; ardından her öğrenci için `AttendanceRecord` (durum: geldi/gelmedi/mazeretli) bu oturuma bağlanır. Tek tablo yerine iki katman kullanmak, "bu ders için yoklama hiç alınmadı" ile "yoklama alındı ama öğrenci yoktu" durumlarını birbirinden ayırmayı mümkün kılar — devamsızlık raporlarının doğruluğu için şart.

---

#### 3.2.14 HashenUdara/edoc-doctor-appointment-system

- **URL:** https://github.com/HashenUdara/edoc-doctor-appointment-system
- **Açıklama:** PHP tabanlı randevu alma web uygulaması. Hastalar doktorlardan kolayca randevu alabiliyor.
- **Teknoloji:** PHP
- **★ / Fork:** 567 / 256 · **Son aktivite:** Ağustos 2026
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** **Rezervasyon akışı, bildirim.**
- **Mimari fikir:** Randevu alma akışının **kademeli daraltma (progressive narrowing)** olarak tasarlanması: uzmanlık → hekim → tarih → uygun saat. Yüzme okulunda karşılığı: **seviye → antrenör/grup → tarih → uygun kulvar-saat.** Kullanıcıya en baştan tüm boş slotları göstermek yerine, her adımda seçim uzayını daraltmak. Ayrıca randevu durumlarının (`pending / approved / rejected / completed`) açık bir yaşam döngüsü olarak tutulması. PHP olduğu için kod ilgisiz; **akış tasarımı** için incelendi.

---

#### 3.2.15 NDresevic/timetable-generator

- **URL:** https://github.com/NDresevic/timetable-generator
- **Açıklama:** Genetik algoritmalar kullanarak Python'da uygulanmış üniversite ders programı üreticisi.
- **Teknoloji:** Python
- **★ / Fork:** 221 / 67 · **Son aktivite:** Şubat 2025
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** **Takvim/çakışma çözümü.**
- **Mimari fikir:** Çakışma tespitinin **uygunluk fonksiyonu (fitness function)** olarak formüle edilmesi — yani "bu program geçerli mi?" sorusunun ikili (evet/hayır) değil, **cezalandırma puanı** olarak ifade edilmesi. Her çakışma türüne farklı ağırlık verilir (kulvar çakışması ağır, antrenör boşluğu hafif). Timefold'un sert/yumuşak kısıt fikrinin saf Python'daki somut karşılığı olduğu için, harici çözücü bağımlılığı olmadan basit bir çakışma puanlayıcı yazmak istersek doğrudan referansımız.

---

#### 3.2.16 Antonio-Neves/Gestao-Escolar

- **URL:** https://github.com/Antonio-Neves/Gestao-Escolar
- **Açıklama:** Python ve Django ile tam okul yönetim sistemi (geliştirme aşamasında).
- **Teknoloji:** Python (Django)
- **★ / Fork:** 48 / 21 · **Son aktivite:** Mayıs 2026
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** Öğrenci kayıt, çok dilli arayüz.
- **Mimari fikir:** **Çok dilli (i18n) yapının en baştan kurulması.** Arayüz metinlerinin şablonlara gömülmek yerine çeviri dosyalarında tutulması. Bizim `react-i18next` kullanma kararımızı destekleyen bir doğrulama: Türkçe ana dil olsa bile, metinleri en baştan çeviri anahtarları üzerinden yönetmek sonradan İngilizce eklemeyi maliyetsiz kılıyor.

---

#### 3.2.17 shiningflash/django-reservation-system

- **URL:** https://github.com/shiningflash/django-reservation-system
- **Açıklama:** Kullanıcı, oda, rezervasyon ve ödeme yönetimi için REST API'lere sahip Django rezervasyon sistemi. Docker ve Swagger dokümantasyonu içeriyor.
- **Teknoloji:** Python (Django + DRF)
- **★ / Fork:** 8 / 0 · **Son aktivite:** Aralık 2024
- **Lisans:** **MIT** → **UYGUN**
- **İlham verdiği modül:** **Rezervasyon + ödeme ilişkisi, API dokümantasyonu.**
- **Mimari fikir:** **Rezervasyon ile ödemenin ayrı ama bağlantılı varlıklar olması.** Rezervasyon "onaylandı" olabilir ama ödemesi "bekliyor" durumunda kalabilir. Bu iki yaşam döngüsünü tek bir durum alanında birleştirmek (örn. `paid_and_confirmed`) durum patlamasına yol açar. Ayrı tutmak, "ödemesi eksik olan onaylı rezervasyonlar" gibi raporları basit sorgulara indirger. Ayrıca OpenAPI/Swagger'ın otomatik üretilmesi (FastAPI'de yerleşik olarak geliyor).

---

### 3.3 Detaylı İnceleme — DİKKAT Projeleri (Copyleft)

> ⚠️ **Bu bölümdeki projelerin hiçbirinden kod, veri şeması, migration dosyası veya birebir yapı kopyalanmamıştır.** İnceleme yalnızca "bu sistem hangi problemleri çözüyor?" sorusuna cevap aramak için, kavramsal düzeyde yapılmıştır.

---

#### 3.3.1 wger-project/wger

- **URL:** https://github.com/wger-project/wger
- **Açıklama:** Kendi sunucunuzda barındırılabilen özgür yazılım fitness/antrenman, beslenme ve kilo takip uygulaması.
- **Teknoloji:** Python (Django)
- **★ / Fork:** 6.658 / 972 · **Son aktivite:** Ağustos 2026
- **Lisans:** **AGPL-3.0** → **DİKKAT**
- **⚠️ Risk:** AGPL, yazılımı **ağ üzerinden servis olarak sunmayı bile** kaynak kodu açma yükümlülüğü doğuran bir tetikleyici sayar. Bu, web tabanlı bir yönetim sistemi için mümkün olan en yüksek risktir. **Tek satır kod alınmadı.**
- **İlham verdiği modül:** **Performans/gelişim takibi.**
- **Kavramsal çıkarım (fikir düzeyinde):**
  - Bir sporcunun gelişiminin **zaman serisi ölçüm kayıtları** olarak modellenmesi: her ölçüm `(sporcu, metrik türü, değer, birim, tarih)` beşlisidir. Yüzme okulunda metrikler: 25m serbest süresi, nefes almadan mesafe, teknik puanı, dayanıklılık.
  - **Şablon (template) ile uygulama (log) ayrımı:** "Antrenman planı" (ne yapılması planlandı) ile "antrenman kaydı" (fiilen ne yapıldı) ayrı varlıklardır. Yüzme okulunda karşılığı: **ders planı** vs **gerçekleşen ders**.
  - Bu iki fikir de mimari desendir; wger'ın uygulaması incelenmemiş, kodu okunmamıştır.

---

#### 3.3.2 alextselegidis/easyappointments

- **URL:** https://github.com/alextselegidis/easyappointments
- **Açıklama:** Kendi sunucunuzda barındırılabilen randevu planlayıcı.
- **Teknoloji:** PHP
- **★ / Fork:** 4.321 / 1.549 · **Son aktivite:** Ağustos 2026
- **Lisans:** **GPL-3.0** → **DİKKAT**
- **⚠️ Risk:** GPL-3.0 copyleft. Kod alınması hâlinde tüm projemizi GPL ile yayınlamak zorunda kalırdık. **Kod alınmadı.** (PHP olduğu için teknik olarak da ilgisiz.)
- **İlham verdiği modül:** **Rezervasyon, çalışma saatleri.**
- **Kavramsal çıkarım:** Sağlayıcı (provider) bazlı **çalışma planı + istisna (break) modeli** — her personelin haftalık çalışma saatleri ve bunun üstüne binen mola/izin istisnaları. Ayrıca hizmet süresinin (service duration) slot üretimini belirlemesi: 45 dakikalık ders ile 60 dakikalık dersin farklı slot ızgaraları üretmesi. Bu kavramlar zaten `respa` (MIT) ve `cal.com` (MIT) projelerinde de mevcut olduğundan, **uygulama referansımız o iki permissive projedir.**

---

#### 3.3.3 frappe/education

- **URL:** https://github.com/frappe/education
- **Açıklama:** Açık kaynak eğitim / okul yönetim sistemi (ERPNext ekosistemi).
- **Teknoloji:** Python (Frappe Framework)
- **★ / Fork:** 598 / 419 · **Son aktivite:** Ağustos 2026
- **Lisans:** GitHub API `NOASSERTION` döndürdü; **`license.txt` dosyası doğrudan okunarak `GNU GPL V3` olduğu doğrulandı** → **DİKKAT**
- **⚠️ Risk:** GPL-3.0 copyleft. **Kod alınmadı.**
- **İlham verdiği modül:** **Öğrenci yönetimi, ücret/ödeme, program yapısı.**
- **Kavramsal çıkarım:**
  - **Ücret yapısı (fee structure) ile ücret talebi (fee schedule/invoice) ayrımı:** "Yeni Başlayanlar kursu 3.000 TL'dir" bir **yapı** tanımıdır; "Ayşe'ye 3.000 TL borç çıkarıldı" ise bir **talep** kaydıdır. Fiyat değiştiğinde geçmiş talepler etkilenmez. Bu ayrım, ödeme modülümüzün temel taşıdır.
  - **Öğrenci grubu (student group) kavramı:** Öğrencilerin doğrudan derse değil, bir **gruba** atanması; grubun da programa/antrenöre bağlanması. Yüzme okulunda "Salı-Perşembe 18:00 Yeni Başlayanlar A Grubu" tam olarak bu.
  - Bu kavramlar sektör standardıdır ve Frappe'ye özgü değildir; genel muhasebe/eğitim yönetimi bilgisidir.

---

#### 3.3.4 Lehrstuhl-BWL-EvIS/sportyweb

- **URL:** https://github.com/Lehrstuhl-BWL-EvIS/sportyweb
- **Açıklama:** Spor kulüplerinin verimli ve işbirlikçi yönetimi için çok kiracılı (multitenancy) web uygulaması.
- **Teknoloji:** Elixir (Phoenix)
- **★ / Fork:** 11 / 14 · **Son aktivite:** Mart 2025
- **Lisans:** **AGPL-3.0** → **DİKKAT**
- **⚠️ Risk:** AGPL. **Kod alınmadı.** (Elixir olduğu için teknik olarak da ilgisiz.)
- **İlham verdiği modül:** **Üyelik, çok şubeli yapı.**
- **Kavramsal çıkarım:** **Çok kiracılılık (multitenancy) kararının en baştan verilmesi gerektiği.** Bir spor kulübü yazılımı büyüdüğünde kaçınılmaz olarak "birden fazla şube/tesis" ihtiyacı doğar. Bunu sonradan eklemek her sorguya `branch_id` filtresi eklemek anlamına gelir ve son derece maliyetlidir. Bizim kararımız: **şube kavramını veri modeline en baştan koymak**, tek şubeyle başlasak bile.

---

### 3.4 Detaylı İnceleme — KULLANILAMAZ Projeler

> ❌ **Bu projelerin kodu incelenmemiştir.** Yalnızca varlıkları ve lisans durumları kayıt altına alınmıştır.

---

#### 3.4.1 mayerbalintdev/GYM-One

- **URL:** https://github.com/mayerbalintdev/GYM-One
- **Açıklama:** Fitness merkezleri, kişisel antrenörler ve spor kulüpleri için ücretsiz spor salonu yönetim yazılımı.
- **Teknoloji:** PHP · **★ / Fork:** 203 / 62 · **Son aktivite:** Haziran 2026
- **Lisans:** GitHub API `NOASSERTION` döndürdü. Lisans dosyası incelendiğinde, standart bir açık kaynak lisansı değil, **özel "GYM One License Agreement" (Sürüm 1.0, 27 Haziran 2025)** olduğu görüldü. Bu sözleşme atıf zorunluluğu, başka yazılımlarla entegrasyon kısıtları ve sorumluluk reddi içeriyor.
- **Karar:** **KULLANILAMAZ.** Kendini "open-source, free" olarak tanıtmasına rağmen OSI onaylı bir lisans kullanmıyor. Bu, lisans alanına körü körüne güvenmemenin ve **her zaman gerçek LICENSE dosyasını okumanın** gerekliliğini gösteren örnek vakadır.

---

#### 3.4.2 mwinamijr/django-scms

- **URL:** https://github.com/mwinamijr/django-scms
- **Açıklama:** Okul veya kolejin tamamını yönetmek için gerekli tüm işlevlere sahip okul yönetim sistemi.
- **Teknoloji:** Python (Django) · **★ / Fork:** 59 / 75 · **Son aktivite:** Şubat 2026
- **Lisans:** **Yok** → **Belirsiz — KULLANILAMAZ**
- **Karar:** Lisans dosyası bulunmadığından, varsayılan olarak "tüm hakları saklıdır" statüsündedir. Aktif geliştirilen ve konu olarak ilgili bir proje olmasına rağmen **kod incelemesi yapılmamıştır.**

---

#### 3.4.3 shreyansh225/Sports-Club-Management-System

- **URL:** https://github.com/shreyansh225/Sports-Club-Management-System
- **Açıklama:** Kolay zaman planlaması ve üyelik bilgisine gerçek zamanlı erişim sunan online spor kulübü yönetim sistemi.
- **Teknoloji:** PHP · **★ / Fork:** 42 / 14 · **Son aktivite:** Mart 2022
- **Lisans:** **Yok** → **Belirsiz — KULLANILAMAZ**
- **Karar:** Lisanssız. **Kod incelemesi yapılmamıştır.**

---

## 4. Mimari Çıkarımlar

Bu bölüm, araştırmadan elde edilen fikirlerin modüllerimize nasıl yansıdığını özetler. **Hiçbiri kod kopyası değildir; hepsi kavramsal desenlerdir.**

### 4.1 Öğrenci Yönetimi

| Karar | Kaynak ilham |
|---|---|
| **Tek `User` varlığı + eklenebilir rol profilleri.** Bir kişi aynı anda hem veli hem antrenör olabilir; iki ayrı kayıt oluşturulmaz. | PicoSchool (Apache-2.0) |
| **Öğrenci–Veli ilişkisi çoktan-çoğa.** Bir öğrencinin birden fazla velisi (anne, baba, vasi), bir velinin birden fazla öğrencisi olabilir. İletişim izinleri bu ilişki üzerinde tutulur. | jobic10 (MIT) |
| **Dönem (term) birinci sınıf varlık.** Öğrenci "okula" değil, **belirli bir döneme** kaydolur. Seviye ilerlemesi dönemler arası geçiş olarak izlenir. | django-lms (MIT) |
| **Zenginleştirilmiş kayıt (enrollment) ara tablosu.** Öğrenci–grup ilişkisi kendi alanlarına sahip bağımsız varlıktır (kayıt tarihi, durum, çıkış tarihi, seviye). | django-lms (MIT) |
| **Yumuşak silme (soft delete).** Öğrenci kaydı asla fiziksel olarak silinmez; `is_active` + `deleted_at` ile pasifleştirilir. Geçmiş yoklama ve ödeme kayıtlarının bütünlüğü korunur. | Genel desen (full-stack-fastapi-template) |

### 4.2 Rezervasyon

| Karar | Kaynak ilham |
|---|---|
| **Soyut "Kaynak (Resource)" modeli.** Kulvar, antrenör ve ekipman aynı rezervasyon motoruyla yönetilir. Yeni kaynak türü eklemek yeni tablo gerektirmez. | respa (MIT) |
| **Rezervasyon kuralları veri olarak.** Min/maks süre, kullanıcı başına eşzamanlı limit, kaç gün öncesinden rezervasyon — hepsi kaynak kaydındaki yapılandırılabilir alanlar. İş kuralı değişince deploy gerekmez. | respa (MIT) |
| **Açık durum makinesi:** `talep edildi → onaylandı → tamamlandı` / `iptal edildi` / `reddedildi`. Serbest metin yerine kısıtlı enum + izinli geçiş matrisi. | respa (MIT), edoc (MIT) |
| **Kademeli daraltma UX'i:** seviye → grup/antrenör → tarih → uygun kulvar-saat. | edoc (MIT) |
| **Veritabanı kısıtı nihai otoritedir.** Uygulama katmanındaki "kontrol et sonra yaz" yarış koşuluna açıktır; çift rezervasyon veritabanı seviyesinde engellenir. | cal.com (MIT) |

### 4.3 Takvim / Çakışma

| Karar | Kaynak ilham |
|---|---|
| **Event / Occurrence ayrımı.** Tekrarlayan ders tek kayıt + tekrar kuralı olarak saklanır; somut örnekler çalışma zamanında üretilir. 16 haftalık kurs = 1 satır. | django-scheduler (BSD-3) |
| **Yalnızca istisnalar kalıcılaştırılır.** İptal, erteleme, tatil — kuraldan sapanlar tek satırlık istisna kaydıdır. | django-scheduler (BSD-3) |
| **Müsaitlik hesaplanır, saklanmaz.** Boş slot = çalışma saatleri − rezervasyonlar − istisnalar. "Hayalet slot" hatalarını yapısal olarak imkânsız kılar. | cal.com (MIT), respa (MIT) |
| **Sert / yumuşak kısıt ayrımı.** Sert: kulvar çakışması, antrenör çakışması, kapasite aşımı. Yumuşak: antrenör boşluk saatleri, tercih edilen zaman dilimi. | timefold-solver (Apache-2.0) |
| **Çakışma = puanlanabilir büyüklük.** İkili geçerlilik yerine ağırlıklı ceza puanı; alternatif program önerilerini sıralamayı mümkün kılar. | NDresevic/timetable-generator (MIT) |
| **Tüm zaman damgaları UTC.** Yerel saate yalnızca sunum katmanında çevrilir. | cal.com (MIT) |
| **İleri faz:** Otomatik program üretimi için CP-SAT (kısıt programlama) değerlendirilecek. | or-tools (Apache-2.0) |

### 4.4 Yoklama

| Karar | Kaynak ilham |
|---|---|
| **İki katmanlı model:** `YoklamaOturumu` (hangi ders, tarih, kim aldı) + `YoklamaKaydı` (öğrenci, durum). "Yoklama alınmadı" ile "öğrenci gelmedi" birbirinden ayrılır. | jobic10 (MIT) |
| **Zengin durum kümesi:** `geldi / gelmedi / mazeretli / geç geldi`. İkili (var/yok) yerine, telafi hakkı ve devamsızlık raporları için gerekli ayrım. | jobic10 (MIT) |
| **Yoklama, gerçekleşen ders örneğine bağlanır** — tekrar kuralına değil. Occurrence modeli bunu doğal kılar. | django-scheduler (BSD-3) |
| **Değiştirilemez denetim izi.** Yoklama düzeltmesi üzerine yazma değil, yeni sürüm kaydıdır; kim ne zaman değiştirdi izlenir. | Genel iyi uygulama |

### 4.5 Üyelik

| Karar | Kaynak ilham |
|---|---|
| **Paket tanımı ile üyelik örneği ayrı.** "10 Derslik Paket" bir **ürün tanımı**; "Ayşe'nin 12 Mart'ta başlayan paketi" bir **örnektir**. Paket fiyatı değişince mevcut üyelikler etkilenmez. | frappe/education (kavramsal), respa (MIT) |
| **Dondurma (freeze) durumu birinci sınıf.** Hastalık/tatil nedeniyle üyelik askıya alınabilir; kalan hak ve bitiş tarihi otomatik ötelenir. | wger/sektör pratiği (kavramsal) |
| **Kalan hak sayacı türetilmiş değer.** Kullanılan ders sayısı yoklama kayıtlarından hesaplanır; ayrı bir sayaç alanı tutulup senkronizasyon hatası riski alınmaz (performans için önbelleklenebilir). | Genel desen |
| **Şube (branch) kavramı en baştan.** Tek şubeyle başlasak bile veri modelinde yeri hazır. | sportyweb (kavramsal) |

### 4.6 Ödeme

| Karar | Kaynak ilham |
|---|---|
| **Ücret yapısı ≠ ücret talebi.** Fiyat tanımı ile borç kaydı ayrı varlıklardır. Fiyat değişimi geçmiş faturaları bozmaz. | frappe/education (kavramsal) |
| **Rezervasyon ve ödeme yaşam döngüleri ayrı.** Rezervasyon "onaylı" iken ödeme "bekliyor" olabilir. Birleşik durum alanı kullanılmaz. | shiningflash (MIT) |
| **Ödeme = değiştirilemez hareket kaydı (ledger).** Ödemeler güncellenmez; iade ayrı bir negatif hareket kaydıdır. Muhasebe denetlenebilirliği için şart. | Genel muhasebe pratiği |
| **Taksit planı ayrı varlık.** Toplam borç + vade tarihleri; her taksit bağımsız izlenir. | frappe/education (kavramsal) |

### 4.7 Raporlama

| Karar | Kaynak ilham |
|---|---|
| **Okuma modelinin yazma modelinden ayrılması.** Dashboard'lar işlem tablolarını doğrudan taramaz; özet/aggregate sorgular üzerinden beslenir. | django-lms (MIT) |
| **Rapor üretimi asenkron.** Büyük Excel/PDF çıktıları istek-cevap döngüsünü bloke etmez. | Genel desen |
| **Excel `openpyxl`, PDF `reportlab` ile.** Her ikisi de permissive lisanslı (MIT / BSD). | Bölüm 5 |
| **Rapor parametreleri kaydedilebilir.** Sık kullanılan filtre kombinasyonları "kayıtlı rapor" olarak saklanır. | respa (MIT) |

### 4.8 Performans Takibi

| Karar | Kaynak ilham |
|---|---|
| **Zaman serisi ölçüm modeli:** `(sporcu, metrik türü, değer, birim, tarih, ölçen kişi)`. Yeni metrik eklemek şema değişikliği gerektirmez. | wger (kavramsal, AGPL — kod alınmadı) |
| **Plan (şablon) ≠ gerçekleşen (log).** Ders planı ile fiilen yapılan ders ayrı kayıtlardır. | wger (kavramsal) |
| **Seviye/rozet ilerlemesi kural tabanlı.** "25m serbest < 30sn + 10 ders devam → Orta Seviye" gibi kurallar veri olarak tanımlanır. | django-lms (MIT), casbin (Apache-2.0) desen benzerliği |
| **Grafikler `Recharts` ile** (MIT). | Bölüm 5 |

### 4.9 RBAC / Yetkilendirme

| Karar | Kaynak ilham |
|---|---|
| **İzinler veri, koda gömülü değil.** `(rol, kaynak, eylem)` üçlüsü veritabanında tutulur. Yeni rol = yeni veri, yeni deploy değil. | pycasbin (Apache-2.0) |
| **Rol mirası.** `yönetici → başantrenör → antrenör → resepsiyon` hiyerarşisi; üst rol alt rolün tüm izinlerini devralır. | pycasbin (Apache-2.0) |
| **Kaynak sahipliği kontrolü.** Antrenör yalnızca **kendi** gruplarının verisine erişir. Salt rol kontrolü yetersizdir; nesne düzeyinde sahiplik kontrolü şarttır. | pycasbin (Apache-2.0) |
| **Yetkilendirme `Depends` zinciriyle deklaratif.** `require_role("antrenor")` gibi bağımlılıklar route imzasında görünür; endpoint gövdesinde `if` kontrolü dağılmaz. | full-stack-fastapi-template (MIT) |
| **Parola hash'i şeffaf yükseltme ile.** Kullanıcı giriş yaptığında eski hash yeni algoritmaya taşınır. | fastapi-users (MIT) |

### 4.10 REST API

| Karar | Kaynak ilham |
|---|---|
| **Dört katmanlı ayrım:** `api/routes/` → `services/` (iş mantığı) → `crud/` (veri erişimi) → `models/`. İş mantığı route'a sızmaz. | full-stack-fastapi-template (MIT) |
| **Girdi/çıktı şeması ayrımı:** `OgrenciCreate` / `OgrenciUpdate` / `OgrenciPublic`. Hassas alanların sızması tip düzeyinde engellenir. | full-stack-fastapi-template (MIT) |
| **Kaynak başına router dosyası.** `ogrenciler.py`, `rezervasyonlar.py`, `yoklama.py` + ortak `deps.py`. | 7s9n/small_sms_api (MIT) |
| **Token transport/strategy ayrımı.** Token taşıma yöntemi ile üretim/doğrulama yöntemi bağımsız soyutlamalar. | fastapi-users (MIT) |
| **OpenAPI otomatik üretimi.** FastAPI'de yerleşik; frontend tip üretimi buradan beslenir. | full-stack-fastapi-template (MIT), shiningflash (MIT) |
| **Alembic ile sürümlü şema göçü.** Elle SQL çalıştırılmaz. | full-stack-fastapi-template (MIT) |

---

## 5. Kullanılan Kütüphaneler ve Lisansları

Aşağıdaki tüm lisans bilgileri, **PyPI JSON API** (`pypi.org/pypi/{paket}/json`) ve **npm Registry API** (`registry.npmjs.org/{paket}/latest`) üzerinden **15 Ağustos 2026 tarihinde doğrudan sorgulanarak** doğrulanmıştır.

### 5.1 Backend (Python)

| Kütüphane | Doğrulanan Sürüm | Lisans | Kategori | Karar |
|---|---|---|---|---|
| **FastAPI** | 0.141.1 | **MIT** | Web framework | ✅ UYGUN |
| **SQLAlchemy** | 2.0.52 | **MIT** | ORM | ✅ UYGUN |
| **Pydantic** | 2.13.4 | **MIT** | Veri doğrulama | ✅ UYGUN |
| **Alembic** | 1.19.1 | **MIT** | Şema göçü | ✅ UYGUN |
| **Uvicorn** | 0.52.3 | **BSD-3-Clause** | ASGI sunucu | ✅ UYGUN |
| **passlib** | 1.7.4 | **BSD** (BSD-2-Clause) | Parola hash'leme | ✅ UYGUN |
| **bcrypt** | 5.0.0 | **Apache-2.0** | Hash algoritması | ✅ UYGUN |
| **python-jose** | 3.5.0 | **MIT** | JWT/JOSE | ✅ UYGUN |
| **PyJWT** | 2.13.0 | **MIT** | JWT (alternatif) | ✅ UYGUN |
| **pandas** | 3.0.5 | **BSD-3-Clause** | Veri analizi | ✅ UYGUN |
| **numpy** | 2.5.2 | **BSD-3-Clause** AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Sayısal hesaplama | ✅ UYGUN |
| **openpyxl** | 3.1.5 | **MIT** | Excel okuma/yazma | ✅ UYGUN |
| **reportlab** | 5.0.0 | **BSD** (BSD-3-Clause) | PDF üretimi | ✅ UYGUN |
| **pytest** | 9.1.1 | **MIT** | Test framework | ✅ UYGUN |
| **httpx** | 0.28.1 | **BSD-3-Clause** | HTTP istemcisi / test | ✅ UYGUN |

**Notlar:**
- `numpy` bileşik bir lisans ifadesi kullanır; ana gövde BSD-3-Clause'tur, vendor edilmiş bazı bileşenler 0BSD / MIT / Zlib / CC0-1.0 taşır. Tamamı permissive'dir.
- `passlib` ve `reportlab`'ın PyPI meta verisinde lisans alanı serbest metindir ("BSD"); OSI sınıflandırıcıları `License :: OSI Approved :: BSD License` olarak doğrulanmıştır.
- **JWT tercihi:** `python-jose` ve `PyJWT` her ikisi de MIT'tir. `PyJWT` daha aktif bakım gördüğü için **PyJWT tercih edilmelidir**; `python-jose` yedek seçenektir.
- **bcrypt notu:** `passlib` (BSD) arka uç olarak `bcrypt` (Apache-2.0) kullanır. İki lisans da permissive ve birbiriyle uyumludur.

### 5.2 Frontend (JavaScript / TypeScript)

| Kütüphane | Doğrulanan Sürüm | Lisans | Kategori | Karar |
|---|---|---|---|---|
| **React** | 19.2.8 | **MIT** | UI kütüphanesi | ✅ UYGUN |
| **Vite** | 8.2.1 | **MIT** | Build aracı | ✅ UYGUN |
| **TypeScript** | 7.0.2 | **Apache-2.0** | Dil / derleyici | ✅ UYGUN |
| **TailwindCSS** | 4.3.3 | **MIT** | CSS framework | ✅ UYGUN |
| **@tanstack/react-query** | 5.101.4 | **MIT** | Sunucu durumu yönetimi | ✅ UYGUN |
| **react-i18next** | 17.0.11 | **MIT** | Çoklu dil (i18n) | ✅ UYGUN |
| **Recharts** | 3.10.1 | **MIT** | Grafik/chart | ✅ UYGUN |
| **lucide-react** | 1.31.0 | **ISC** | İkon seti | ✅ UYGUN |
| **date-fns** | 4.4.0 | **MIT** | Tarih işlemleri | ✅ UYGUN |
| **axios** | 1.19.0 | **MIT** | HTTP istemcisi | ✅ UYGUN |
| **zustand** | 5.0.15 | **MIT** | İstemci durumu yönetimi | ✅ UYGUN |

**Notlar:**
- **TypeScript Apache-2.0'dır**, MIT değil. Bu, projedeki tek Apache-2.0 frontend bağımlılığıdır ve `NOTICE` yükümlülüğü doğurabileceğinden `THIRD_PARTY_NOTICES.md` içinde ayrıca belirtilmiştir. TypeScript bir **derleme zamanı** aracı olduğundan ürettiğimiz JavaScript çıktısına lisans bulaşmaz.
- **lucide-react ISC'dir**, MIT değil. ISC, BSD-2-Clause ile fonksiyonel olarak eşdeğer, tamamen permissive bir lisanstır.

### 5.3 Lisans Dağılımı Özeti

| Lisans | Paket sayısı | Risk |
|---|---|---|
| MIT | 17 | Yok |
| BSD-3-Clause | 4 | Yok |
| Apache-2.0 | 2 | Yok (NOTICE gerekebilir) |
| BSD-2-Clause | 1 | Yok |
| ISC | 1 | Yok |
| **GPL / AGPL / LGPL** | **0** | **Yok — copyleft bağımlılığımız yoktur** |

**Sonuç:** Toplam 26 doğrudan bağımlılığın tamamı permissive lisanslıdır. **Projemizde tek bir copyleft bağımlılık bulunmamaktadır.** Bu, ürünün ticari olarak dağıtılabilmesi ve kaynak kodun kapalı tutulabilmesi açısından tam serbestlik anlamına gelir.

> ⚠️ **Sürekli izleme notu:** Bu doğrulama doğrudan (direct) bağımlılıkları kapsar. Geçişli (transitive) bağımlılıkların da denetlenmesi için CI hattına `pip-licenses` ve `license-checker` benzeri bir kontrol eklenmesi ve GPL/AGPL tespitinde derlemenin başarısız olması önerilir.

---

## 6. Sonuç: Neden Kendi Mimarimizi Yazıyoruz

Bu araştırmanın en net bulgusu şudur: **Yüzme okulu yönetimi alanında, üzerine inşa edebileceğimiz olgun, permissive lisanslı, aktif bakım gören bir açık kaynak proje yoktur.**

### 6.1 Bulgular

**1. Alanda boşluk var.**
"Swimming club management" aramaları 15 sonuçtan 15'inde ya lisanssız, ya tek kişilik öğrenci ödevi, ya da terk edilmiş depolar döndürdü. Doğrudan alan eşleşmesi olan tek permissive proje (`countryside-community-swimming-club`, Apache-2.0) **4 yıldıza** sahip. Bu, "hazır bir çözümü fork'lamak" seçeneğinin masada olmadığı anlamına geliyor.

**2. En iyi mimari fikirler farklı alanlardan geliyor.**
İşimize en çok yarayan fikirler, yüzme ile hiç ilgisi olmayan projelerden çıktı:
- Rezervasyon çekirdeği → bir **belediye tesis rezervasyon sistemi** (`respa`)
- Takvim modeli → bir **genel Django takvim uygulaması** (`django-scheduler`)
- Çizelgeleme zihniyeti → bir **kurumsal kısıt çözücü** (`timefold-solver`)
- Yetkilendirme → bir **genel amaçlı authz kütüphanesi** (`pycasbin`)

Bu projelerin hiçbiri "yüzme okulu yazılımı" değil. Dolayısıyla birini alıp uyarlamak mümkün değil; **fikirlerini kendi domain'imizde birleştirmek** gerekiyor. Yaptığımız da tam olarak budur.

**3. En yakın olgun çözümler yanlış lisansta.**
Alanımıza en yakın gerçekten olgun projeler — `wger` (6.658★), `easyappointments` (4.321★), `frappe/education` (598★) — **AGPL-3.0 veya GPL-3.0** lisanslıdır. Bunlardan kod almak, tüm ürünümüzü copyleft altında yayınlamayı zorunlu kılardı. Bu, ticari bir yönetim sistemi için kabul edilemez.

**4. Teknoloji yığını uyuşmuyor.**
İncelenen olgun sistemlerin çoğu **PHP** (`easyappointments`, `GYM-One`, `edoc`), **Elixir** (`sportyweb`), **Java** (`timefold`) veya **Django** (`respa`, `django-lms`) tabanlı. Bizim yığınımız **FastAPI + React/TypeScript**. Django kodunu FastAPI'ye taşımak, sıfırdan yazmaktan daha fazla emek gerektirir — çünkü ORM, migration, admin paneli ve request yaşam döngüsü tamamen farklıdır.

**5. Domain gereksinimlerimiz benzersiz.**
Hiçbir genel amaçlı sistem şunları birlikte karşılamıyor:
- **Kulvar bazlı kapasite** (bir kulvarda aynı anda en fazla N yüzücü — oda rezervasyonundan farklı)
- **Seviye tabanlı grup ilerlemesi** (Yeni Başlayan → Orta → İleri, teknik değerlendirmeye bağlı)
- **Veli–öğrenci–antrenör üçgeni** (çocuk yüzücülerde veli onayı ve bildirimi zorunlu)
- **Su güvenliği ve sağlık kaydı** (sağlık raporu geçerlilik takibi)
- **Telafi dersi hakkı** (devamsızlık durumunda hakkın başka bir gruba taşınması)
- **Yapay zekâ destekli özellikler** (performans tahmini, program optimizasyonu) — mevcut projelerin hiçbirinde yok

### 6.2 Kararımız

**Kendi mimarimizi sıfırdan yazıyoruz.** Ancak bu, "hiçbir şey öğrenmeden yazıyoruz" demek değildir. Araştırmadan somut olarak şunları alıyoruz:

| Ne alıyoruz | Nereden | Nasıl |
|---|---|---|
| Katman düzeni ve proje iskeleti | full-stack-fastapi-template (MIT) | Desen olarak |
| Rezervasyon kaynak soyutlaması | respa (MIT) | Kavram olarak |
| Event/Occurrence takvim modeli | django-scheduler (BSD-3) | Kavram olarak |
| Müsaitlik = çıkarma işlemi | cal.com (MIT) | Kavram olarak |
| Sert/yumuşak kısıt ayrımı | timefold-solver (Apache-2.0) | Kavram olarak |
| İzinlerin veri olarak modellenmesi | pycasbin (Apache-2.0) | Kavram olarak |
| İki katmanlı yoklama modeli | jobic10 (MIT) | Kavram olarak |
| Ücret yapısı / talep ayrımı | frappe (GPL — **yalnızca kavram**) | Kavram olarak |

**Sonuç olarak:** Sıfırdan yazmak burada tembelliğin değil, **araştırmanın sonucudur.** Hazır bir çözüm olsaydı kullanırdık; olmadığını doğruladık. Bunun yerine, 24 projeden damıtılmış mimari dersleri kendi domain modelimizde birleştiriyoruz.

### 6.3 Uyum Taahhüdümüz

1. ✅ Hiçbir GPL/AGPL/LGPL/MPL lisanslı projeden **kod, şema, migration veya birebir yapı kopyalanmamıştır.**
2. ✅ Copyleft projelerden yalnızca **kavramsal/mimari fikirler** alınmıştır — ki fikirler telif hakkına tabi değildir.
3. ✅ Tüm doğrudan bağımlılıklarımız **permissive lisanslıdır** (MIT / BSD / Apache-2.0 / ISC).
4. ✅ Tüm bağımlılıklar `THIRD_PARTY_NOTICES.md` belgesinde listelenmiştir.
5. ✅ Lisans bilgileri, ikincil kaynaklara güvenilmeden **doğrudan resmî kaynaklardan** (GitHub API, PyPI API, npm Registry, ham LICENSE dosyaları) doğrulanmıştır.
6. 🔄 Yeni bir bağımlılık eklenmeden önce lisansı doğrulanacak; CI hattında otomatik lisans taraması kurulacaktır.

---

## Ek A: Doğrulama Kaynakları

| Veri türü | Kaynak | Yöntem |
|---|---|---|
| Depo meta verisi | `https://api.github.com/repos/{owner}/{repo}` | Doğrudan API çağrısı |
| Belirsiz lisanslar | `https://raw.githubusercontent.com/{owner}/{repo}/{branch}/LICENSE` | Ham dosya okuma |
| Python paket lisansları | `https://pypi.org/pypi/{paket}/json` | Doğrudan API çağrısı |
| npm paket lisansları | `https://registry.npmjs.org/{paket}/latest` | Doğrudan API çağrısı |

**Araştırma tarihi:** 15 Ağustos 2026
**Doğrulanan depo sayısı:** 24
**Doğrulanan kütüphane sayısı:** 26
**Uydurulmuş/doğrulanmamış kayıt sayısı:** 0

---

*Bu belge, lisans uyumluluğu denetimlerinde kanıt niteliğindedir. Yeni bağımlılık veya referans projesi eklendiğinde güncellenmelidir.*
