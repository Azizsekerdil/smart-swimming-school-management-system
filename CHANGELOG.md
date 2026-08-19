# Değişiklik Günlüğü / Changelog

Bu projedeki tüm önemli değişiklikler bu dosyada belgelenir.
Biçim [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) standardına,
sürümleme [Semantic Versioning](https://semver.org/lang/tr/) kurallarına dayanır.

All notable changes to this project are documented in this file.

---

## [1.0.0-public] — 2026-08-19

İlk **kamuya açık** yayın. Bu sürüm, yayımlanabilirlik için yapılan güvenlik,
gizlilik ve doğruluk düzeltmelerini içerir.

First **public** release. This version contains the security, privacy and
accuracy corrections made for publication.

### Güvenlik / Security

- **KRİTİK — SPA geri düşüş ucundaki kimliksiz dosya okuma kapatıldı.**
  `GET /{yol}` ucu, `frontend/dist` altındaki dosyayı kapsam denetimi yapmadan
  sunuyordu; `..` içeren bir yol ile proje kökündeki `.env`, veritabanı ve
  yedekler okunabiliyordu. Yeni `resolve_spa_asset()`, POSIX ve Windows mutlak
  yollarını, UNC yollarını, `..` geçişlerini, çözülmeden ulaşan yüzde
  kodlamasını, NUL baytını ve kapsam dışına çıkan sembolik bağları reddeder.
  Regresyon testi: `backend/tests/test_spa_path_traversal.py` (36 senaryo).
- **YÜKSEK — Satır/nesne bazlı yetkilendirme 22 uçta tamamlandı.** Veli,
  öğrenci ve sporcu rolleri başka ailelerin çocuk adlarını, borçlarını,
  üyeliklerini, ders listelerini ve yoklama kayıtlarını görebiliyordu. Tek
  ortak mekanizma (`AccessScope`) eklendi: sorgu süzme, tekil nesne doğrulama
  (IDOR) ve kurum geneli uçların bu rollere kapatılması. Ders listesi ve
  yoklama ekranı artık yalnızca kendi çocuğunu gösterir.
  Regresyon testi: `backend/tests/test_row_level_authorisation.py`.
- **İlk kurulum kimliği sözleşmesi.** `admin` / `admin` artık belgelenmiş ve
  zorlanan bir sözleşmedir: parola değişmeden hiçbir korumalı uca erişilemez,
  giriş yalnızca yerel cihazdan kabul edilir, değişimden sonra varsayılan
  kalıcı olarak geçersizdir ve yönetici sıfırlaması onu geri getiremez.
  Kaba kuvvete karşı artan gecikme eklendi.
  Regresyon testi: `backend/tests/test_bootstrap_admin.py` (34 senaryo).
- **AI geliştirici ajanı sertleştirildi.** `python -c` beyaz listeden çıkarıldı
  (dinamik kod çalıştırma, komut beyaz listesini tümüyle atlatıyordu);
  yorumlayıcı komutlarında artık **bütün** bayraklar denetlenir.
  `patch_id` / `checkpoint_id` biçim doğrulaması eklendi (dizin dışına çıkma).
- **`PUT /ai/config` üzerinden `.env` satır enjeksiyonu kapatıldı.** Değerler
  artık şema düzeyinde (satır sonu / kontrol karakteri reddi, URL şeması
  denetimi, sağlayıcı adı beyaz listesi) ve yazma anında ikinci bir kapıyla
  doğrulanır.
- `GET /system/about` artık kimlik doğrulaması ister; `GET /settings/{key}`
  artık `settings:read` iznini ister.
- Parola politikası `admin` ve benzeri yaygın değerleri kesin olarak reddeder.
- CI: en dar `permissions:` bloğu eklendi, bütün action'lar değişmez commit
  SHA'sına sabitlendi, kalite kapıları bloklayıcı yapıldı; bloklamayan iki
  adımın adında bunun yazması sağlandı.

### Gizlilik / Privacy

- **Gizlilik geçidi artık BÜTÜN AI çağrı yollarına uygulanıyor.** Önceden
  yalnızca analiz yolu geçitten geçiyordu; sohbet, akışlı sohbet, geliştirici
  ajanı ve CAIO doğrudan sağlayıcıya gidiyordu. Akış için `preflight()` /
  `issue_receipt()` ayrımı eklendi. Bir testin (`test_ai_privacy_gateway.py`)
  kaynak kodu AST ile ayrıştırarak geçidi atlayan çağrı kalmadığını doğrular.
- **Serbest metin tarayıcı** eklendi (`services/hsp/freetext.py`): sohbet
  metni telefon, e-posta, kimlik numarası, IBAN, doğum tarihi, sağlık ve özel
  gereksinim anahtar kelimeleri ve veritabanındaki gerçek adlar için taranır;
  bulunanlar geçide bildirilir ve takma adlaştırılır.
- **İstem metni artık `AI_LOG_PROMPTS` kapalıyken hiçbir alanda saklanmıyor.**
  Önceden her sohbetin ilk 200 karakteri görev başlığı olarak bayraktan
  bağımsız kaydediliyordu.
- **Demo telefon numaraları aranamaz hâle getirildi.** Önceki üreteç, Türkiye'de
  gerçek ve tahsisli olan `0530-0559` bandını kullanıyordu; artık hiçbir
  numaralandırma planında tahsisli olmayan `0000` ön eki kullanılır.

### Doğruluk / Accuracy

- **`THIRD_PARTY_NOTICES.md` içindeki "sıfır kopyaleft / MPL = 0" iddiası
  düzeltildi.** `certifi` **MPL-2.0** lisanslıdır ve `httpx` üzerinden çalışma
  zamanında dağıtılır. Bu bir çatışma değildir (dosya düzeyinde kopyaleft) ama
  iddia yanlıştı. `caniuse-lite` (CC-BY-4.0) atıf yükümlülüğü de eklendi.
  Uygulanamaz "MPL eklenemez" politikası, çözülmüş ağaca uygulanan
  gerçekçi bir politikayla değiştirildi.
- Sunum ve belgelerdeki bütün sayılar yeniden **ölçüldü**: 240 API ucu
  (193 yol, 23 modül grubu), 55 tablo, 395 test fonksiyonu (533 çalıştırma),
  1.027 çeviri anahtarı.
- Sunumun "demo kayıtları her zaman işaretlenir" ifadesi, ekran görüntüleriyle
  doğrulanamadığı için doğrulanabilir bir ifadeyle değiştirildi:
  **bütün kayıtlar sentetiktir.**
- `LICENSE` saf MIT metnine indirildi (ek not `THIRD_PARTY_NOTICES.md`'ye
  taşındı) — lisans algılayıcıları artık doğru sonuç veriyor.

### Eklendi / Added

- `SECURITY.md`, `PRIVACY.md`, `AI_TRANSPARENCY.md`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, `docs/known-limitations.md`
- `sbom.spdx.json`, `sbom.cdx.json` (SPDX + CycloneDX), `.gitleaks.toml`,
  `.github/dependabot.yml`
- `backend/requirements.lock.txt` — çözülmüş, yeniden üretilebilir ağaç
- `frontend/src/pages/ForcePasswordChangePage.tsx` — zorunlu parola değişimi
- `tools/capture_screens.py`: `--base-url` desteği ve sağlam oturum denetimi
- `tools/presentation_theme.py`: özgür yazı tipi tercihi
  (`SWS_PRESENTATION_FONT`)

### Kaldırıldı / Removed

- Depoya özel yayımlama yardımcıları (`PUSH_TO_GITHUB.bat`,
  `scripts/push_to_github.ps1`) — kapsam dışı.
- Özel iç tasarım/boşluk raporları (`docs/hsp/*.md`) — kapsam dışı.
- Sunum ikili çıktıları (`sunum/*.pptx`, `*.pdf`, `*.html`) artık sürümlenmez;
  yayımlanan PDF'ler `docs/presentation/*_PUBLIC.pdf` altındadır ve kaynaktan
  yeniden üretilebilir.

---

## [0.9.0] — 2026-08-18

İlk yayın adayı. Sistem uçtan uca çalışır durumda; üretim kullanımından önce
kurum verisiyle bir pilot dönem önerilir.

First release candidate. The system is functional end to end; a pilot period
with real data is recommended before production use.

### Eklendi / Added

#### Çekirdek altyapı
- FastAPI + SQLAlchemy 2.0 + Pydantic v2 tabanlı REST API (240 uç nokta)
- SQLite veritabanı, Alembic migration altyapısı (55 tablo)
- PostgreSQL'e geçişe hazır veri katmanı soyutlaması
- JWT tabanlı kimlik doğrulama (erişim + yenileme jetonu)
- 21 rol ve 52 ince taneli izinden oluşan RBAC sistemi
- Satır bazlı erişim kapsamı (öğrenci/veli kendi verisini, eğitmen kendi derslerini görür)
- Yapılandırılmış loglama (application, database, ai, security, developer-agent, audit)
- Hassas veri maskeleme: API anahtarları ve parolalar loglara asla yazılmaz
- Türkçe/İngilizce yerelleştirilmiş API hata mesajları

#### Kişi yönetimi
- Öğrenci profili: kimlik, iletişim, seviye, grup, eğitmen, hedefler, sağlık notu
- Sağlık ve özel ihtiyaç bilgisi `student:read_sensitive` izniyle korunur
- KVKK/GDPR açık rıza kaydı ve veri minimizasyonu
- Veli yönetimi: bir veli birden fazla öğrenciye bağlanabilir
- Veli portalı: ders takvimi, yoklama, ödeme, üyelik ve performans görünümü
- Eğitmen yönetimi: uzmanlık, sertifika (son geçerlilik takibi), müsaitlik, izin
- Grup tanımları (yaş aralığı, seviye, kapasite, renk)

#### Tesis ve program
- Çok havuzlu yapı; havuz başına kulvar, çalışma saati, bakım ve su kalitesi kaydı
- Su kalitesi limit dışına çıktığında otomatik bildirim
- Akıllı kulvar planlama: saat × kulvar doluluk şeması
- **Çakışma motoru**: aynı anda aynı eğitmen, kulvar veya öğrenci iki derse atanamaz
- Havuz bakımı, çalışma saati dışı ve tatil günü denetimleri
- Boş kulvar bulma ve çakışmasız zaman dilimi önerisi
- 13 ders türü, tekrarlanan ders serileri, sürükle-bırak ile taşıma
- Takvim: günlük, haftalık, aylık görünüm

#### Operasyon
- Yoklama: manuel, QR kod ve öğrenci kartı ile; 6 durum kodu
- Devam kaydı üzerinden otomatik ders hakkı düşümü (çift düşüm koruması)
- Telafi dersi atama
- Üyelik ve paket sistemi: dondurma, yenileme, iptal, saklama limitleri
- Finans: tahsilat, fatura, gider, indirim, iade, yaşlandırma raporu

#### Spor ve analiz
- Performans kaydı: derece, split, kulaç, stroke rate, reaksiyon, dönüş süresi
- Otomatik kişisel rekor takibi
- İstatistiksel analiz: ortalama, medyan, standart sapma, persentil, hareketli
  ortalama, eğilim eğimi, korelasyon, aykırı değer tespiti
- Yarışma modülü: etkinlik, seri (heat) dağıtımı, sonuç, madalya, kulüp rekoru
- Standart yüzme kuralına uygun otomatik seri/kulvar dağıtımı
- İstatistik merkezi: öğrenci, eğitmen, havuz, yoklama, finans analizleri
- Yoğunluk haritası (gün × saat havuz kullanımı)
- Cohort tutundurma analizi, churn/retention hesabı
- KPI paneli: 11 gösterge, hedef belirleme ve gerçekleşme takibi
- 16 rapor türü; PDF, Excel, CSV dışa aktarma (Türkçe karakter desteğiyle)

#### Yapay zekâ
- Sağlayıcı soyutlaması: `AIProvider` → LM Studio, NVIDIA, OpenAI uyumlu
- LM Studio yerel entegrasyonu (gizlilik: veriler bilgisayardan çıkmaz)
- NVIDIA Build bulut entegrasyonu (API anahtarı yalnızca `.env` üzerinden)
- Otomatik fallback zinciri; hiçbir sağlayıcı yoksa sistem çalışmaya devam eder
- AI Kontrol Merkezi: durum, gecikme, model listesi, token kullanımı, hata sayacı
- 6 aşamalı bağlantı testi (bağlantı, model, istem, JSON, zaman aşımı, akış)
- Model yönlendirme: görev türüne göre model önerisi; yetenek yalnızca API
  bildirdiğinde "doğrulanmış" sayılır, ad eşleşmesi "doğrulanmamış" işaretlenir
- **İstatistik + AI ayrımı**: gerçek hesaplanmış veri ile model yorumu arayüzde
  ayrı panellerde gösterilir; AI yorumu kesin gerçek olarak sunulmaz
- 18 hazır prompt kütüphanesi
- AI görev geçmişi: sağlayıcı, model, token, süre, sonuç kaydı

#### AI geliştirme altyapısı
- AI Developer Console: READ → SEARCH → ANALYZE → PLAN → PATCH → TEST → DIFF →
  ONAY → APPLY akışı
- Komut güvenlik politikası: beyaz liste + 19 yasak işlem deseni
- Proje dizini dışına yazma, registry, disk, hesap ve kimlik erişimi engellenir
- `.env` ve veritabanı dosyalarına ajan erişimi yasak
- Yama uygulamadan önce otomatik checkpoint; test başarısızsa otomatik geri alma
- CAIO (Chief AI Officer) ajanı: log, güvenlik, test kapsamı, teknik borç, veri
  kalitesi, yedekleme ve maliyet gözlemi; kural motoru AI olmadan da çalışır

#### Yedekleme ve kurtarma
- ZIP arşivi + `backup_manifest.json` + SHA-256 sağlaması
- API anahtarları ve parolalar yedeğe **dahil edilmez**
- Otomatik bütünlük doğrulaması (8 kontrol)
- Güvenli geri yükleme: doğrula → güvenlik yedeği → önizleme → onay → geri yükle
  → bütünlük kontrolü → hata durumunda otomatik rollback
- Saklama politikası (günlük/haftalık/aylık), korunan yedek işaretleme
- Zamanlanmış yedekleme (cron)
- `BackupProvider` soyutlaması (ileride bulut hedefleri için)

#### Arayüz
- React 18 + TypeScript (strict) + Vite + Tailwind CSS
- 24 ekran, kod bölme ile tembel yükleme
- Açık/koyu tema, tam responsive tasarım
- Global arama (öğrenci, veli, eğitmen, ders, ödeme, havuz, yarışma)
- Ctrl+K komut paleti
- Türkçe/İngilizce tam yerelleştirme; tarih, sayı ve para birimi biçimlendirmesi
- Bildirim merkezi

#### Eğitim ve dokümantasyon
- Program içi kullanım kılavuzu (28 bölüm, iki dilli)
- Eğitim Merkezi: 12 adım adım interaktif eğitim
- Rol bazlı eğitim izleri, ilerleme takibi
- Kurulum sihirbazı (onboarding)
- Eğitim modu (demo veri üzerinde güvenli çalışma)

#### Kalite ve dağıtım
- 395 backend test fonksiyonu (birim, API, RBAC, çakışma, istatistik, AI, yedekleme)
- AI testleri gerçek API çağrısı yapmaz (mock)
- GitHub Actions CI: lint, tip denetimi, test, derleme, gizli anahtar taraması
- Tek komutla yayın öncesi kalite kapısı (`FINAL_CHECK.bat`)
- Windows masaüstü başlatıcı (WebView2 tabanlı, düşük bellek kullanımı)
- Çift tıklamayla çalışan `START_SWIMMING_SCHOOL.bat`

### Güvenlik / Security
- bcrypt (12 tur) parola hashleme, 72 bayt sınırı için SHA-256 ön özet
- Zamanlama saldırısına karşı sabit maliyetli giriş doğrulama
- Giriş hız sınırlaması ve hesap kilitleme
- Denetim kaydı (audit log) — parolalar ve anahtarlar maskelenir
- Güvenli hata mesajları: yığın izi ve SQL istemciye sızmaz
- Güvenlik başlıkları (X-Frame-Options, X-Content-Type-Options, CSP, HSTS)
- SQLAlchemy parametreli sorgular ile SQL enjeksiyonu koruması
- CORS beyaz listesi

### Bilinen kısıtlamalar / Known limitations
- Yedekleme ve geri yükleme şu an yalnızca SQLite için desteklenir
  (PostgreSQL için `pg_dump` akışı planlanmıştır)
- Artımlı (incremental) yedekleme mimaride tanımlı, henüz uygulanmadı
- Bulut yedekleme hedefleri (Drive, OneDrive, S3) soyutlama hazır, bağlayıcı yok
- RAG / vektör veritabanı katmanı soyutlanmış durumda, gömme (embedding)
  entegrasyonu v1.0'a bırakıldı
- Model yetenek doğrulaması sağlayıcı API'sine bağlıdır; LM Studio yetenek
  bildirmediği için öneriler "doğrulanmamış" olarak işaretlenir

---

## Sürüm planı / Release plan

| Sürüm | Kapsam |
|-------|--------|
| 0.9.0 | İlk yayın adayı (mevcut) |
| 1.0.0 | Pilot geri bildirimleri, PostgreSQL yedekleme, Windows installer |
| 1.1.0 | RAG bilgi bankası, bulut yedekleme hedefleri, mobil uyumlu veli portalı |
| 1.2.0 | RFID/NFC donanım entegrasyonu, SMS/e-posta bildirimleri |

Ayrıntılı yol haritası: [docs/ROADMAP.md](docs/ROADMAP.md)
