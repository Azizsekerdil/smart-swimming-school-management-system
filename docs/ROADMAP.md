# Yol Haritası / Roadmap

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'nin v0.9.0 itibarıyla tamamlanmış
kapsamını, bilinen kısıtlamalarını ve sonraki üç sürüm için planlanan işleri
kaydeder. Amaç, pazarlama vaadi vermek değil; her maddenin **gerekçesini,
tahmini eforunu ve ön koşullarını** açıkça yazarak planı denetlenebilir kılmaktır.

**Belge sürümü:** 1.0 · **Güncelleme:** 18 Ağustos 2026 · **Ürün sürümü:** 0.9.0

> Tahminler tek geliştiricinin tam zamanlı çalışması varsayımıyla verilmiştir ve
> **adam-gün (a-g)** birimindedir. Aralık verilen yerlerde üst sınır, entegrasyon
> ve test süresini içerir.

---

## 1. Mevcut Durum (v0.9.0)

v0.9.0 ilk **yayın adayıdır**. Sistem uçtan uca çalışır: backend, arayüz,
masaüstü başlatıcı, yedekleme ve yapay zekâ katmanı birlikte ayağa kalkar.
Üretime alınmadan önce kurum verisiyle bir pilot dönem önerilir.

### 1.1 Ölçülebilir kapsam

| Ölçü | Değer | Kaynak |
|---|---|---|
| REST uç noktası | 244 | `backend/app/api/v1/` (22 yönlendirici modülü) |
| Veritabanı tablosu | 50 | `backend/app/models/` · Alembic `alembic upgrade head` |
| Backend testi | 395 test fonksiyonu / 533 çalıştırma (hepsi geçiyor) | `backend/tests/` |
| Arayüz ekranı | 24 | `frontend/src/pages/` |
| Çeviri anahtarı | 1020 (TR ve EN eşit) | `frontend/src/locales/{tr,en}/translation.json` |
| Rol | 21 | `backend/app/core/permissions.py` → `RoleCode` |
| İzin | 52 | `backend/app/core/permissions.py` → `Perm` |
| Doğrudan bağımlılık lisansı | %100 permissive (MIT/BSD/Apache-2.0/ISC) | `THIRD_PARTY_NOTICES.md` |

### 1.2 Modül durumu

| Modül | Durum | Not |
|---|---|---|
| Kimlik doğrulama ve oturum (JWT) | ✅ Tamam | Erişim 120 dk, yenileme 14 gün (`config.py`) |
| RBAC ve satır bazlı kapsam | ✅ Tamam | 21 rol × 52 izin; efektif izin = rollerin birleşimi |
| Öğrenci / veli / eğitmen yönetimi | ✅ Tamam | Sağlık notu `student:read_sensitive` ile korunur |
| Havuz, kulvar, bakım, su kalitesi | ✅ Tamam | Limit dışı su değeri otomatik bildirim üretir |
| Ders planlama ve çakışma motoru | ✅ Tamam | Eğitmen / kulvar / öğrenci çakışması engellenir |
| Takvim (gün · hafta · ay) | ✅ Tamam | Sürükle-bırak ile ders taşıma |
| Yoklama (manuel · QR · kart) | ✅ Tamam | 6 durum kodu, çift hak düşümü koruması |
| Üyelik ve paket | ✅ Tamam | Dondurma, yenileme, iptal, saklama limitleri |
| Finans (tahsilat, fatura, gider) | ✅ Tamam | İndirim, iade, yaşlandırma raporu |
| Performans ve istatistik motoru | ✅ Tamam | Persentil, eğilim, korelasyon, aykırı değer |
| Yarışma yönetimi | ✅ Tamam | Otomatik seri/kulvar dağıtımı, kulüp rekoru |
| Raporlama (16 tür) | ✅ Tamam | PDF / Excel / CSV, Türkçe karakter desteğiyle |
| AI sağlayıcı katmanı | ✅ Tamam | LM Studio + NVIDIA + OpenAI uyumlu, otomatik fallback |
| AI Kontrol Merkezi | ✅ Tamam | 6 aşamalı bağlantı testi, token ve gecikme izleme |
| AI Developer Console | ✅ Tamam | Beyaz liste + 19 yasak desen; `AI_DEVELOPER_ALLOW_APPLY` varsayılan `false` |
| CAIO gözlem ajanı | ✅ Tamam | Kural motoru AI olmadan da çalışır |
| Yedekleme / geri yükleme | ⚠️ Kısmi | Yalnızca SQLite (bkz. §2.1) |
| Bulut yedek hedefleri | 🟡 Soyutlama hazır | `BackupProvider` var, bağlayıcı yok (bkz. §2.3) |
| RAG / bilgi bankası | 🔴 Yok | Yalnızca model yönlendirmede `embedding` görev sınıfı var (bkz. §2.4) |
| Bildirim merkezi (uygulama içi) | ✅ Tamam | `/api/v1/system/notifications` |
| E-posta / SMS kanalları | 🔴 Yok | v1.1.0'a planlandı (bkz. §4.4) |
| Yerelleştirme (TR/EN) | ✅ Tamam | CI'da anahtar eşitliği zorunlu kılınır |
| Eğitim Merkezi ve kılavuz | ✅ Tamam | 12 interaktif eğitim, 28 bölümlük kılavuz |
| Masaüstü başlatıcı | ✅ Tamam | `START_SWIMMING_SCHOOL.bat` → `desktop/launcher.py` |
| Windows installer (MSI/NSIS) | 🔴 Yok | v1.0.0'a planlandı (bkz. §3.2) |
| CI hattı | ✅ Tamam | `.github/workflows/ci.yml` — 4 iş: backend, frontend, security, integration |
| Arayüz E2E testi | 🔴 Yok | v1.0.0'a planlandı (bkz. §3.4) |

**Açıklama:** ✅ Tamam · ⚠️ Kısmi (belirli koşullarda çalışır) · 🟡 Soyutlama
hazır, uygulama yok · 🔴 Henüz yok.

### 1.3 Kalite kapısı

Yayın öncesi tek komutla çalışan kapı:

```bat
FINAL_CHECK.bat
```

Arka planda `scripts/final_check.ps1` şunları sırayla yürütür: `ruff check`,
`mypy app`, `pytest tests`, frontend `tsc --noEmit`, `eslint`, `vite build`,
çeviri bütünlüğü ve gizli anahtar taraması. CI hattı aynı kontrolleri
`ubuntu-latest` üzerinde tekrarlar ve ek olarak `alembic check` ile migration
tutarlılığını, `pip-audit` ile bağımlılık zafiyetlerini denetler.

---

## 2. Bilinen Kısıtlamalar

CHANGELOG'daki beş kısıtlama burada nedeni ve planlanan çözümüyle genişletilmiştir.

### 2.1 Yedekleme yalnızca SQLite için çalışır

**Belirti.** `POST /api/v1/backup` çağrısı PostgreSQL bağlantısında şu hatayla
biter:

```
Bu sürümde otomatik yedekleme yalnızca SQLite için desteklenir.
PostgreSQL için pg_dump kullanın.
```

**Neden.** `backend/app/services/backup.py` içindeki `_snapshot_sqlite()`,
tutarlı kopyayı `sqlite3.Connection.backup()` çevrimiçi yedekleme API'siyle alır.
Bu API dosya tabanlı ve motora özgüdür; WAL modunda açık bağlantı varken bile
bütünlüklü kopya üretmesi tam olarak bu yüzdendir. PostgreSQL'de eşdeğeri
`pg_dump` harici sürecidir ve bambaşka bir akış gerektirir (kimlik bilgisi
yönetimi, `PGPASSWORD` yerine `.pgpass`, sürüm uyumu, çıktı formatı seçimi).
`create_backup()` bu yüzden `is_sqlite()` kontrolünden geçmeyen motorlarda
bilinçli olarak durur — yanlış/eksik yedek üretmektense hata vermeyi tercih eder.

**Planlanan çözüm.** v1.0.0 · §3.1 — `PostgresDumpProvider` benzeri ikinci bir
anlık görüntü stratejisi; manifest'teki `database_engine` alanı zaten motor adını
taşıdığı için arşiv formatı değişmez.

**Geçici çözüm (bugün).** PostgreSQL kullanıyorsanız veritabanı yedeğini
işletim sistemi düzeyinde `pg_dump` ile alın; uygulama arayüzündeki yedekleme
ekranını yalnızca yüklenen belgeler ve ayar bilgisi için kullanmayın — bu
sürümde çağrı zaten hata döner.

### 2.2 Artımlı (incremental) yedekleme uygulanmadı

**Neden.** `BackupType` numaralandırmasında tür ayrımı mimaride tanımlı; ancak
her yedek bugün tam bir SQLite anlık görüntüsüdür. Artımlı yedek, doğru
yapıldığında sayfa düzeyinde değişiklik takibi (WAL frame diff) veya en azından
son tam yedeğe kıyaslı bir delta kaydı gerektirir. Yarım uygulanmış bir artımlı
zincir, geri yükleme sırasında **sessiz veri kaybı** riski taşır; bu riski
üstlenmektense özellik ertelenmiştir.

**Ölçek gerçeği.** Tipik bir yüzme okulunun tam veritabanı yedeği birkaç yüz
MB'ı geçmez; günlük tam yedek + saklama politikası (`apply_retention()` —
7 günlük / 4 haftalık / 12 aylık) pratikte yeterlidir. Bu nedenle özellik
"acil" sınıfında değildir.

**Planlanan çözüm.** v1.2.0 sonrası değerlendirilecek; önce gerçek pilot
verisiyle yedek boyutu ölçülecek. Yedek boyutu 2 GB'ı aşan bir kurulum
gözlenmedikçe önceliklendirilmeyecektir.

### 2.3 Bulut yedek hedefleri için bağlayıcı yok

**Neden.** `BackupProvider` soyut sınıfı (`store` / `retrieve` / `delete` /
`exists`) hazırdır ve `LocalDiskProvider` tek etkin uygulamadır. Bulut hedefi
eklemek teknik olarak küçük bir iştir; asıl engel teknik değil, **gizlilik
tasarımıdır.** Okul verisi öğrenci sağlık notu ve veli iletişim bilgisi içerir.
Bir yedeği üçüncü taraf depolamaya göndermek, KVKK/GDPR açısından yeni bir veri
aktarımı anlamına gelir ve açık, geri alınabilir bir kullanıcı onayı olmadan
yapılamaz.

**Planlanan çözüm.** v1.1.0 · §4.2 — sağlayıcı başına açık onay ekranı,
aktarılacak veri kalemlerinin listelenmesi ve tek tıkla iptal.

### 2.4 RAG / vektör katmanı henüz yok

**Neden.** Bugün mevcut olan tek şey, model yönlendiricisindeki `embedding`
görev sınıfıdır (`backend/app/services/ai/providers.py` → `TASK_MODEL_HINTS`,
`nomic-embed` ve `bge` ipuçlarıyla). Yani sistem, yüklü bir gömme modelini
**tanıyabilir**; ancak metni parçalayan, gömen, saklayan ve geri getiren bir
katman yoktur. Bağımlılık listesinde herhangi bir vektör veritabanı yer almaz
(`backend/requirements.txt`).

**Kapsam düzeltmesi.** CHANGELOG'da bu madde "v1.0'a bırakıldı" olarak
kaydedilmişti. Planlama gözden geçirildiğinde v1.0.0'ın **üretime alma
sertleştirmesine** odaklanması, RAG'ın ise yeni bir veri saklama biçimi ve yeni
bir gizlilik yüzeyi getirmesi nedeniyle özellik **v1.1.0'a taşınmıştır.**
Bu belge, bu konuda CHANGELOG'un üzerinde geçerlidir.

**Planlanan çözüm.** v1.1.0 · §4.1.

### 2.5 Model yetenek doğrulaması sağlayıcıya bağımlı

**Neden.** `suggest_model_for_task()`, bir modeli göreve atamadan önce
sağlayıcının `list_models()` çıktısını okur. Sağlayıcı yetenek alanı bildiriyorsa
öneri `capability_source="api"` olarak işaretlenir. LM Studio yerel sunucusu
OpenAI uyumlu `/v1/models` yanıtında yetenek bildirmediği için, eşleşme yalnızca
model **adı** üzerinden yapılır ve `capability_source="heuristic"` damgalanır.
Arayüz bu ayrımı gizlemez; "doğrulanmamış" rozetiyle gösterir.

**Bu bir hata değil, bilinçli tasarımdır.** Alternatif — ad benzerliğine bakıp
"bu model görüntü işleyebilir" demek — kullanıcıyı yanıltır. Sistem bilmediğini
bilmediğini söyler.

**Planlanan iyileştirme.** v1.1.0'da isteğe bağlı bir "yetenek yoklaması":
kullanıcı onayıyla modele küçük bir sonda isteği gönderilir (ör. 1 piksellik
görsel), yanıt başarılıysa yetenek `probe` kaynağıyla kaydedilir. Yoklama
varsayılan olarak **kapalı** olacaktır.

---

## 3. v1.0.0 — Üretim Hazırlığı (kısa vade)

**Hedef.** Yeni özellik eklemeden, v0.9.0'ı gerçek bir kurumda güvenle
çalıştırılabilir hâle getirmek. Bu sürümün başarı ölçütü özellik sayısı değil,
**bir pilot okulun günlük operasyonunu kesintisiz yürütebilmesidir.**

**Toplam tahmini efor:** 40–56 a-g.

### 3.1 PostgreSQL yedekleme desteği

**Gerekçe.** Tek şubeli ve tek eşzamanlı yazıcılı kurulumda SQLite fazlasıyla
yeterlidir. Ancak birden fazla resepsiyon terminali aynı anda yazdığında
(yoklama saati yoğunluğu) SQLite'ın tek yazıcı kilidi darboğaz olur. Veri katmanı
PostgreSQL'e hazırdır; tek eksik yedekleme akışıdır. Yedeği olmayan bir
veritabanı üretime alınamaz — bu madde §2.1'i kapatır ve PostgreSQL geçişinin
önündeki son engeldir.

**Kapsam.**

- `backend/app/services/backup.py` içinde motor ayrımı: `is_sqlite()` dalı
  korunur, karşısına `pg_dump -Fc` (custom format) ile anlık görüntü alan bir
  dal eklenir.
- Geri yükleme tarafında `pg_restore --clean --if-exists`; mevcut
  "doğrula → güvenlik yedeği → önizleme → onay → geri yükle → bütünlük kontrolü"
  akışı **aynen** korunur, yalnızca anlık görüntü/geri yükleme adımları motora
  göre dallanır.
- Kimlik bilgisi `DATABASE_URL`'den türetilir; parola komut satırına
  **yazılmaz**, `PGPASSWORD` ortam değişkeni yalnızca alt sürecin ömrü boyunca
  ayarlanır ve loglara asla düşmez (mevcut maskeleme politikası geçerlidir).
- `pg_dump` bulunamazsa veya sunucu sürümüyle uyumsuzsa açık, iki dilli hata:
  istemciye sürüm numaraları döner, yığın izi dönmez.
- Manifest'teki `database_engine` alanı `"postgresql"` yazar; `verify_backup()`
  içindeki 8 kontrolden SQLite'a özgü olan `PRAGMA integrity_check` yerine
  `pg_restore --list` ile arşiv okunabilirlik denetimi kullanılır.

**Kabul ölçütü.** PostgreSQL 15 ve 16 üzerinde: yedek al → veritabanını düşür →
geri yükle → `apply_retention()` çalıştır → kayıt sayıları manifest ile birebir
eşleşsin. Test CI'da bir `postgres` servis konteyneriyle koşsun.

**Tahmini efor.** 8–12 a-g.

**Bağımlılık.** Yok — bugün başlanabilir. `pg_dump`/`pg_restore` ikilileri
kurulum belgesinde ön koşul olarak yazılmalıdır (Windows'ta PostgreSQL istemci
araçları ayrı bileşendir).

**Risk.** `pg_dump` sürümü sunucu sürümünden eski olduğunda hata verir. Azaltma:
başlangıçta sürüm karşılaştırması yapıp kullanıcıyı erken uyarmak.

### 3.2 Windows installer (MSI/NSIS), kısayol ve uygulama ikonu

**Gerekçe.** Bugün kurulum `START_SWIMMING_SCHOOL.bat` çift tıklamasıyla
başlıyor; bu geliştirici için pratik, kurum BT'si için değildir. Bir yüzme
okulu resepsiyonunda Python'un kurulu olduğu, `.bat` dosyasının SmartScreen
uyarısı vermediği ve klasörün taşınmadığı varsayılamaz. Installer, ürünü
"bir klasör" olmaktan çıkarıp "kurulu bir uygulama" hâline getirir.

**Kapsam.**

- NSIS tabanlı tek dosya kurucu (MIT benzeri zlib/libpng lisansı — mevcut
  permissive politikamızla uyumlu; WiX/MSI alternatifi daha ağır kaldığı için
  ikinci seçenektir).
- Gömülü Python çalışma zamanı (embeddable dağıtım) — hedef makinede Python
  kurulumu gerektirmemek için.
- Başlat menüsü ve masaüstü kısayolu; kısayol `desktop/launcher.py`'yi çağırır.
- Uygulama ikonu (`.ico`, çok çözünürlüklü: 16/32/48/256 px) — pencere başlığı,
  görev çubuğu ve kısayol için.
- Kaldırma (uninstall) girdisi; **veri klasörü varsayılan olarak silinmez**,
  kullanıcıya ayrıca sorulur.
- Yükseltme senaryosu: aynı sürüm numarası üzerine kurulum engellenir, daha
  yeni sürüm mevcut `data/` ve `backups/` klasörlerini korur.

**Kabul ölçütü.** Temiz bir Windows 11 sanal makinesinde, Python kurulu değilken
kurucu çalıştırılır; masaüstü kısayolundan uygulama açılır; kaldırma sonrası
`data/` klasörü yerinde durur.

**Tahmini efor.** 6–10 a-g (kod imzalama sertifikası temin süreci hariç).

**Bağımlılık.** `BUILD_FRONTEND.bat` ile üretilen `frontend/dist` çıktısı
kurucuya gömülür; yani frontend derlemesi kurucu adımından önce gelmelidir.

**Not.** Kod imzalama sertifikası olmadan SmartScreen ilk çalıştırmada uyarı
gösterir. Sertifika temini teknik değil, idari bir adımdır ve bu belgede efor
tahminine dâhil edilmemiştir.

### 3.3 Pilot geri bildirimleri ve hata düzeltmeleri

**Gerekçe.** 395 test fonksiyonu, kodun **tasarlandığı gibi** çalıştığını gösterir;
gerçek kullanımda doğru davrandığını göstermez. Bir yüzme okulunun gerçek ders
programı, gerçek veli davranışı ve gerçek ödeme düzensizliği hiçbir test
verisinde yoktur. Bu sürümün en değerli maddesi budur ve tamamen dış girdiye
bağlıdır.

**Kapsam.**

- En az bir okulda 4–6 haftalık gerçek veri pilotu; başlangıçta mevcut
  sisteme paralel çalışma (çift kayıt), veri kaybı riskini sıfırlamak için.
- Haftalık geri bildirim toplantısı; her bulgunun `öncelik × sıklık` ile
  sıralanması.
- Öncelik sırası: (1) veri kaybı/bozulması, (2) yanlış hesaplama (özellikle
  finans ve ders hakkı düşümü), (3) engelleyici kullanılabilirlik sorunu,
  (4) kozmetik.
- Denetim kaydı (`/api/v1/system/audit`) ve log dosyaları üzerinden hata
  yeniden üretimi; her düzeltme için önce başarısız bir test yazılır.

**Kabul ölçütü.** Öncelik 1 ve 2 sınıfında açık bulgu kalmaması; pilot okulun
paralel kayıt tutmayı bırakmayı kabul etmesi.

**Tahmini efor.** 15–20 a-g geliştirme (pilot takvimi buna dâhil değildir;
takvim olarak 6–8 hafta sürer).

**Bağımlılık.** Pilot kurumun bulunması ve KVKK açık rıza sürecinin
tamamlanması. Bu madde **v1.0.0'ın kritik yolu üzerindedir**; diğer maddeler
paralel ilerleyebilir, bu ilerleyemez.

### 3.4 E2E arayüz testleri (Playwright)

**Gerekçe.** CI bugün frontend için `tsc`, `eslint` ve `vite build` çalıştırır —
yani kodun **derlendiğini** doğrular, **çalıştığını** değil. 24 ekranın hiçbiri
tarayıcıda otomatik olarak açılmıyor. Bir çeviri anahtarı eksikliği CI'da
yakalanıyor ama kırık bir form gönderimi yakalanmıyor. Playwright, mevcut
`integration` CI işindeki curl tabanlı duman testinin arayüz karşılığıdır.

**Kapsam — kritik yollar (yaklaşık 12–15 senaryo).**

| # | Senaryo | Doğrulanan |
|---|---|---|
| 1 | Giriş → panel → çıkış | Oturum yaşam döngüsü |
| 2 | Hatalı parola ile 3 deneme | Hız sınırı ve kilitleme geri bildirimi |
| 3 | Öğrenci oluştur → düzenle → arşivle | Temel CRUD + doğrulama mesajları |
| 4 | Çakışan ders oluşturma denemesi | Çakışma motorunun arayüze yansıması |
| 5 | Takvimde ders sürükle-bırak | Optimistik güncelleme ve geri alma |
| 6 | Yoklama al → ders hakkı düşümü | Çift düşüm korumasının UI tarafı |
| 7 | Ödeme kaydet → fatura üret | Finans akışı |
| 8 | Rapor üret → PDF indir | Dosya indirme ve Türkçe karakterler |
| 9 | Veli rolüyle giriş | Satır bazlı kapsam: yalnızca kendi çocuğu görünür |
| 10 | Eğitmen rolüyle giriş | Yetkisiz menülerin gizlenmesi |
| 11 | TR ↔ EN dil değişimi | Yeniden yükleme olmadan tam çeviri |
| 12 | Açık ↔ koyu tema | Kalıcılık ve kontrast |
| 13 | Ctrl+K komut paleti | Global arama sonuçları |

**Kapsam dışı.** AI çağrıları E2E'de **mock'lanır**; gerçek model çağrısı
yapılmaz (mevcut backend test politikasıyla aynı ilke).

**Kabul ölçütü.** Tüm senaryolar CI'da headless Chromium üzerinde geçsin;
başarısız adımda ekran görüntüsü ve iz (trace) artefakt olarak yüklensin.

**Tahmini efor.** 6–8 a-g (altyapı 2 a-g + senaryo başına yaklaşık 0,4 a-g).

**Bağımlılık.** Ekranlarda kararlı `data-testid` seçicileri gerekir; CSS sınıfı
veya metin tabanlı seçici kullanmak Tailwind ve iki dilli arayüzle kırılgan olur.
Bu, arayüz kodunda küçük ama yaygın bir dokunuş demektir.

### 3.5 Performans profilleme ve sorgu optimizasyonu

**Gerekçe.** Sistem bugüne kadar demo veri hacmiyle çalıştı. Üç yıllık gerçek
veriyle (yaklaşık 1.500 öğrenci, 200.000 yoklama satırı, 60.000 performans
kaydı) istatistik ve rapor uçlarının nasıl davranacağı **ölçülmedi**. Ölçmeden
optimize etmek erken optimizasyondur; ölçmeden üretime almak ise kumardır.

**Kapsam.**

- Ölçekli sentetik veri üreteci (`scripts/seed_demo.ps1` genişletilerek);
  hedef hacim yukarıdaki rakamlar.
- Her uç için p50/p95 gecikme ölçümü; yanıt başlığındaki mevcut `X-Process-Time`
  değeri toplanarak raporlanır (ek araç gerekmez).
- N+1 sorgu avı: `DATABASE_ECHO=true` ile ağır uçların sorgu sayısı sayılır;
  ilişkiler için `selectinload` uygulanır.
- Eksik indeks tespiti. Bugün `audit_logs` üzerinde `ix_audit_entity` ve
  `ix_audit_user_time` bileşik indeksleri mevcut; benzer desenin yoklama ve
  performans tablolarında da gerekip gerekmediği ölçümle belirlenecek.
- Ağır istatistik uçlarında (yoğunluk haritası, cohort tutundurma) sonuç
  önbellekleme değerlendirilecek — **yalnızca ölçüm gerekli olduğunu gösterirse.**

**Kabul ölçütü.** Hedef veri hacminde, panel ve ilk 10 sık kullanılan uç için
p95 < 800 ms (yerel makinede, soğuk önbellek). Bu eşik pilot sonrası gerçek
donanıma göre revize edilebilir.

**Tahmini efor.** 5–6 a-g.

**Bağımlılık.** §3.1 ile birlikte yürütülmesi verimlidir: PostgreSQL üzerinde
profilleme yapmak, SQLite üzerinde yapmaktan daha temsili sonuç verir.

---

## 4. v1.1.0 — Bilgi ve Entegrasyon (orta vade)

**Hedef.** Sistemin **bildiklerini** genişletmek ve dış dünyayla güvenli
bağlantılar kurmak. Bu sürümün ortak teması **açık kullanıcı onayıdır**:
üç maddenin de veri sınırını dışa taşıyan yönleri vardır.

**Toplam tahmini efor:** 46–64 a-g.

### 4.1 RAG bilgi bankası

**Gerekçe.** AI modülü bugün yalnızca **sistem verisini** yorumlayabiliyor:
istatistikleri, performans kayıtlarını, doluluk oranlarını. Okulun kendi
bilgisini — eğitim müfredatını, güvenlik prosedürlerini, antrenör notlarını —
bilmiyor. "Bebek yüzmesinde su sıcaklığı prosedürümüz nedir?" sorusuna bugün
verilecek yanıt modelin genel bilgisidir, **okulun kendi belgesi değildir.**
RAG bu boşluğu kapatır ve yanıtı kaynağa bağlar.

**Kapsam.**

- **Belge alımı:** PDF, DOCX ve düz metin; yüklenen dosyalar mevcut
  `data/uploads` yapısına yazılır.
- **Parçalama:** başlık farkındalıklı, örtüşmeli parçalar; her parça kaynak
  dosya + sayfa/bölüm bilgisini taşır.
- **Gömme:** mevcut yerel model altyapısı üzerinden `nomic-embed-text`
  (LM Studio ile birlikte çalışır). Model yönlendiricide `embedding` görev
  sınıfı zaten tanımlıdır (`TASK_MODEL_HINTS`), yani sağlayıcı katmanında
  değişiklik gerekmez.
- **Vektör deposu:** ilk uygulamada **yerel ve gömülü** — SQLite üzerinde
  vektör eklentisi ya da dosya tabanlı bir indeks. Ayrı bir sunucu servisi
  (Chroma/Qdrant) kurulum yükü getireceği için ilk turda tercih edilmez.
  PostgreSQL'e geçen kurulumlar için `pgvector` ikinci hedeftir.
- **Erişim denetimi:** her belgeye izin etiketi. Antrenör notu bir veliye
  görünmez; RBAC filtresi **arama sonucuna** uygulanır, yalnızca arayüzde
  gizlenerek değil.
- **Kaynak gösterimi:** her AI yanıtının altında hangi belgeden alındığı
  listelenir. Kaynak bulunamadıysa model **"bilmiyorum" der**, uydurmaz. Bu,
  mevcut "istatistik + AI ayrımı" ilkesinin devamıdır.

**Gizlilik.** Gömme işlemi varsayılan olarak **yerel modelle** yapılır; belge
içeriği bilgisayardan çıkmaz. Bulut sağlayıcıyla gömme yapılacaksa kullanıcı
ayrıca ve açıkça onaylar.

**Tahmini efor.** 18–24 a-g.

**Bağımlılık.** Kullanıcının LM Studio'da bir gömme modeli yüklü olması. Model
yoksa özellik kendini devre dışı bırakır ve nedenini söyler — sistemin geri
kalanı etkilenmez (mevcut fallback felsefesiyle aynı).

### 4.2 Bulut yedekleme hedefleri

> **Kesin ilke: KULLANICI AÇIK İZİN VERMEDEN HİÇBİR VERİ DIŞARI GÖNDERİLMEZ.**
> Bu ilke `backend/app/services/backup.py` dosyasının modül açıklamasında
> zaten yazılıdır ve kod tarafından uygulanır. Yeni sağlayıcılar bu ilkeyi
> gevşetemez.

**Gerekçe.** Yerel diske alınan yedek, yangın, hırsızlık veya disk arızasında
veriyle birlikte kaybolur. Coğrafi olarak ayrı bir kopya, felaket kurtarmanın
temel şartıdır. `BackupProvider` soyutlaması (`store` / `retrieve` / `delete` /
`exists`) tam olarak bunun için tasarlanmıştır; `LocalDiskProvider` referans
uygulamadır.

**Planlanan hedefler.**

| Hedef | Kimlik doğrulama | Not |
|---|---|---|
| NAS / ağ paylaşımı (SMB) | İşletim sistemi kimliği | En basit hedef; veri kurum ağından çıkmaz — **ilk uygulanacak** |
| S3 uyumlu (MinIO, Wasabi, AWS) | Erişim anahtarı + gizli anahtar | Kendi sunucusunu kuran kurumlar için |
| Google Drive | OAuth 2.0 | Kullanıcı hesabıyla, uygulama kendi hesabına yazmaz |
| OneDrive | OAuth 2.0 | Microsoft 365 kullanan okullar için |

**Gizlilik ve güvenlik kuralları (uygulanacak).**

1. Her sağlayıcı varsayılan olarak **kapalı** gelir.
2. Etkinleştirme ekranı, gönderilecek arşivin içeriğini kalem kalem listeler
   (veritabanı anlık görüntüsü, yüklenen belgeler, loglar) ve boyutunu gösterir.
3. Sırlar yedeğe **zaten dahil değildir**; `EXCLUDED_PATTERNS` (`.env`, `.key`,
   `.pem`, `credentials`, `secrets`, `token`, `id_rsa`) bulut hedefinde de aynen
   geçerlidir.
4. Yükleme öncesi **istemci tarafı şifreleme**: arşiv, kullanıcının belirlediği
   bir parolayla şifrelenir. Sağlayıcı şifresiz içerik göremez.
5. Sağlayıcı kimlik bilgileri yalnızca `.env` üzerinden okunur, veritabanına
   yazılmaz, arayüzde maskelenir (`mask_secret()`), loglara düşmez.
6. Her yükleme denetim kaydına yazılır: kim, ne zaman, hangi hedefe, kaç bayt.
7. Tek tıkla iptal: bağlantı kesildiğinde hedefteki yedeklerin silinip
   silinmeyeceği kullanıcıya sorulur; varsayılan **silmemektir**.

**Tahmini efor.** 12–16 a-g (NAS + S3 için 6–8; OAuth gerektiren iki sağlayıcı
için 6–8).

**Bağımlılık.** §3.1 (PostgreSQL yedekleme) tamamlanmış olmalı — aksi hâlde
bulut hedefi yalnızca SQLite kurulumlarında kullanılabilir olur.

### 4.3 Mobil uyumlu veli portalı (PWA)

**Gerekçe.** Veli portalı bugün mevcut ve responsive; ancak veliler sistemi
masaüstünden değil, telefondan kullanır. Bir PWA, tarayıcı yer imi ile
uygulama arasındaki farkı kapatır: ana ekran simgesi, tam ekran görünüm ve
çevrimdışı temel görüntüleme.

**Kapsam.**

- Web App Manifest + ikon seti; ana ekrana ekleme akışı.
- Service worker ile önbellek: son görüntülenen ders programı ve yoklama
  özeti çevrimdışı okunabilir. **Yazma işlemleri çevrimdışı kuyruğa alınmaz** —
  ödeme veya kayıt işleminin "gönderildi sanılıp gönderilmemesi" kabul edilemez.
- Mobil öncelikli düzen revizyonu: takvim ve tablo görünümleri dar ekranda
  kart düzenine geçer.
- Web Push bildirimi **kapsam dışıdır**; bildirim §4.4'te e-posta/SMS ile
  ele alınır (push, iOS tarafında ek kısıtlar ve sertifika gerektirir).

**Tahmini efor.** 8–12 a-g.

**Bağımlılık.** §3.4 (E2E testleri) — mobil görünüm regresyonu ancak otomatik
testle korunabilir. Playwright'ın cihaz emülasyonu bu senaryolar için kullanılır.

### 4.4 E-posta / SMS bildirim kanalları

**Gerekçe.** Bildirim merkezi bugün yalnızca uygulama içidir
(`/api/v1/system/notifications`). Bu, sisteme giriş yapmayan bir veliye
ulaşamamak demektir — oysa en kritik bildirimler (ders iptali, ödeme hatırlatma,
sağlık raporu süresi dolumu) tam olarak o kişilere gitmelidir. Bildirim
üretimi (`generate`) ve şiddet seviyeleri zaten mevcut; eksik olan yalnızca
**taşıma katmanıdır.**

**Kapsam.**

- Kanal soyutlaması: `NotificationChannel` (uygulama içi · e-posta · SMS).
  `BackupProvider` ile aynı desen — tek arayüz, çok uygulama.
- E-posta: SMTP üzerinden; kurumun kendi sunucusu ya da bir sağlayıcı.
  Ayarlar `.env`'de, parola maskelenir.
- SMS: sağlayıcı bağımsız HTTP arayüzü; Türkiye'de yaygın sağlayıcılar için
  bir uyarlayıcı. Birim maliyeti olduğu için **varsayılan kapalı.**
- Şablonlar TR/EN, mevcut `title_tr`/`title_en`/`body_tr`/`body_en` alanları
  doğrudan kullanılır — veri modeli değişikliği gerekmez.
- **Abonelik tercihi (zorunlu):** her veli hangi kanaldan hangi bildirimi
  alacağını seçer; tek tıkla tamamen çıkabilir (opt-out). İzin kaydı KVKK açık
  rıza kaydıyla ilişkilendirilir.
- Hız sınırı ve tekrar koruması: aynı bildirim aynı kişiye 24 saat içinde iki
  kez gönderilmez.
- Gönderim başarısızlıkları geri bildirimli kuyruğa yazılır; sessizce yutulmaz.

**Tahmini efor.** 8–12 a-g.

**Bağımlılık.** Yok (teknik olarak); ancak SMS için kurumsal sağlayıcı
sözleşmesi ve gönderici başlığı (originator) başvurusu idari ön koşuldur.

---

## 5. v1.2.0 — Donanım ve Otomasyon (uzun vade)

**Hedef.** Fiziksel dünyayla bağlantı ve operasyonel kararların otomasyonu.
Bu maddeler v1.0.0/v1.1.0'a göre daha spekülatiftir; kapsamları pilot
kurumların gerçek talebine göre daralabilir veya genişleyebilir.

**Toplam tahmini efor:** 60–90 a-g (kapsam netleştikçe revize edilecektir).

### 5.1 RFID/NFC turnike entegrasyonu

**Gerekçe.** Yoklama bugün manuel, QR kod veya öğrenci kartı ile alınabiliyor;
üçü de bir personelin işlem yapmasını gerektiriyor. Turnikeye entegre bir kart
okuyucu, giriş anında yoklamayı otomatik oluşturur ve resepsiyonun yoğun saat
yükünü ortadan kaldırır.

**Kapsam.**

- Cihaz soyutlaması: `AccessDevice` arayüzü (okuma olayı → öğrenci eşleştirme →
  yoklama kaydı). Belirli bir marka/modele bağımlılık kurulmaz.
- İlk uygulama: yaygın Wiegand/TCP turnike denetleyicileri için bir uyarlayıcı.
- Çevrimdışı dayanıklılık: ağ koptuğunda cihaz olayları yerel olarak biriktirir,
  bağlantı dönünce senkronize edilir. Yoklamanın kaybolması kabul edilemez.
- Güvenlik kararı: **turnike açma yetkisi sistemin sorumluluğunda değildir.**
  Sistem yoklama kaydı üretir ve üyelik geçerliliğini bildirir; fiziksel
  kilit kararını turnike denetleyicisi verir. Bir yazılım hatasının kimseyi
  havuzda veya dışarıda kilitli bırakmaması için bu ayrım korunur.
- Kart kaybı/klonlama: kart kimliği ham olarak saklanmaz, özetlenir.

**Tahmini efor.** 15–20 a-g + donanım temin ve saha testi süresi.

**Bağımlılık.** Fiziksel test donanımı olmadan geliştirilemez. En az bir pilot
okulun turnike yatırımı yapması ön koşuldur.

### 5.2 Video analiz desteği

**Gerekçe.** Yüzme tekniği görsel bir olgudur; kulaç uzunluğu, vücut pozisyonu
ve dönüş tekniği sayısal ölçümle değil, gözle değerlendirilir. Model
yönlendiricide `vision` görev sınıfı zaten tanımlıdır (`TASK_MODEL_HINTS` →
`vl`, `vision`, `moondream`, `llava`, `pixtral`); yani altyapı görsel modelleri
tanıyabilir durumdadır.

**Kapsam.**

- Kısa video (10–30 sn) yükleme; kare örnekleme ile anahtar kareler çıkarma.
- Görsel model ile teknik gözlem üretimi; çıktı **öneri** olarak sunulur.
- Antrenör notu ile yan yana gösterim; model çıktısı antrenörün yerine geçmez.

**Sınırlar — dürüst beklenti yönetimi.**

- Bu özellik **biyomekanik ölçüm yapmaz.** Genel amaçlı bir görsel dil modeli,
  kulaç açısını dereceyle ölçemez. Üretilen çıktı niteliksel bir gözlemdir.
- Sağlık veya sakatlık yorumu **üretilmez ve üretilmeyecektir.**
- Video, öğrenci ve veli açık rızası olmadan işlenmez; çocuk görüntüsü
  söz konusu olduğu için rıza kaydı ayrıca ve yazılı tutulur.
- İşleme varsayılan olarak **yereldir**; bulut modeline video gönderimi ayrı ve
  açık onay gerektirir.

**Tahmini efor.** 15–25 a-g (kalite hedefi belirsizliği nedeniyle geniş aralık).

**Bağımlılık.** Kullanıcının yeterli donanımda yerel görsel model çalıştırabilmesi.
Bu, tipik bir resepsiyon bilgisayarının kapasitesinin üzerindedir — özellik
büyük olasılıkla opsiyonel kalacaktır.

### 5.3 Otomatik ders programı optimizasyonu

**Gerekçe.** Çakışma motoru bugün bir programın **geçerli olup olmadığını**
söyler; **iyi olup olmadığını** söylemez. Haftalık programı elle kurmak,
20 eğitmen ve 6 kulvarlı bir okulda saatler alan bir iştir. Kulvar–saat–eğitmen–
grup ataması klasik bir kısıt tatmin problemidir (CSP).

**Yaklaşım.** `docs/OPEN_SOURCE_RESEARCH.md` §3.2.10–3.2.11'de kayıtlı
araştırmanın doğrudan çıktısıdır:

- **Sert kısıtlar (ihlal edilemez):** aynı kulvara aynı saatte iki grup
  atanamaz; bir eğitmen aynı anda iki yerde olamaz; grup mevcudu kapasiteyi
  aşamaz; havuz bakım ve çalışma saati dışı bloklarına ders konulamaz. Bu
  kurallar zaten çakışma motorunda kodludur — çözücü aynı kuralları kullanır.
- **Yumuşak kısıtlar (tercih):** eğitmenin boşluk saatleri minimize edilsin;
  aynı seviyedeki gruplar ardışık saatlere yerleşsin; öğrencinin tercih ettiği
  zaman dilimi korunsun.
- **Puanlama:** bir programın "geçerli mi" değil, "ne kadar iyi" olduğunun
  sayısal ifadesi; alternatif öneriler bu puanla sıralanır.
- **Kütüphane:** `google/or-tools` (Apache-2.0, resmî Python paketi
  `ortools.sat.python.cp_model`). Lisans politikamızla uyumludur ve araştırmada
  "yol haritasına not edildi" olarak kayıtlıdır. Timefold Java tabanlı olduğu
  için entegre edilmez; ondan yalnızca **kısıt modelleme zihniyeti** alınmıştır.

**Kritik tasarım kararı.** Çözücü **öneri üretir, uygulamaz.** Üretilen program
kullanıcıya sunulur, kullanıcı düzenler ve onaylar. Otomatik uygulama, bir
eğitmenin haberi olmadan programının değişmesi anlamına gelir ki bu operasyonel
olarak kabul edilemez.

**Tahmini efor.** 12–18 a-g.

**Bağımlılık.** Eğitmen müsaitlik verisinin (`InstructorAvailability`) gerçek
kurumda düzenli doldurulmuş olması. Veri yoksa çözücünün üreteceği program
kâğıt üzerinde kalır. Bu, pilot dönemde ölçülecek bir ön koşuldur.

### 5.4 Çoklu şube desteği

**Gerekçe.** Mevcut veri modeli tek kuruma göre tasarlanmıştır. Birden fazla
şubesi olan bir zincir bugün her şube için ayrı kurulum yapmak zorundadır —
bu da konsolide raporlamayı ve şubeler arası eğitmen paylaşımını imkânsız kılar.

**Kapsam ve dürüst risk değerlendirmesi.**

- Kiracı/şube ayrımı için tüm ana tablolara şube kimliği eklenmesi ve **her
  sorguya** şube filtresi uygulanması gerekir. Bu, sistemin en geniş yüzeyli
  değişikliğidir; 55 tablonun büyük kısmını ve neredeyse tüm servis katmanını
  etkiler.
- Erişim kapsamı üç boyuta çıkar: rol × satır × şube. Mevcut RBAC bunu
  destekleyecek biçimde genişletilmelidir.
- Şubeler arası kaynak paylaşımı (bir eğitmenin iki şubede ders vermesi)
  çakışma motorunu şube üstü çalışmaya zorlar.
- Konsolide raporlama: mevcut 16 rapor türünün şube kırılımı ve toplamı.

**Neden en sona bırakıldı.** Bu değişikliğin maliyeti, tek şubeli kurulumlarda
**hiçbir fayda üretmez** ve regresyon riski yüksektir. Somut bir çok şubeli
müşteri talebi doğrulanmadan başlanmayacaktır.

**Tahmini efor.** 20–30 a-g. Bu tahminin belirsizliği yüksektir ve kapsam
netleşmeden bağlayıcı değildir.

---

## 6. Değerlendirilen ama Ertelenen Fikirler

Bu bölüm, düşünülüp **bilinçli olarak yapılmamaya** karar verilen işleri
kaydeder. Bir yol haritasının yapılmayacakları listesi, yapılacaklar listesi
kadar bilgilendiricidir.

| Fikir | Neden ertelendi | Yeniden değerlendirme koşulu |
|---|---|---|
| **Çok kiracılı (multi-tenant) SaaS** | Ürün, kurumun kendi bilgisayarında çalışan bir masaüstü/yerel sunucu uygulaması olarak tasarlandı. SaaS'a geçmek yalnızca teknik değil, hukuki (veri işleyen sıfatı), operasyonel (7/24 hizmet) ve ticari bir dönüşümdür. | Ticari model değişirse; §5.4'ün tamamlanması ön koşuldur |
| **Mikroservis mimarisi** | 240 uç noktalık bir monolit tek süreçte sorunsuz çalışıyor. Mikroservis, dağıtık işlem karmaşıklığını ve operasyon yükünü hiçbir mevcut sorunu çözmeden getirirdi. | Tek süreç ölçek sınırına dayanırsa (bugün için işaret yok) |
| **GraphQL API** | REST + OpenAPI, 24 ekranlık bilinen bir istemci için yeterli. GraphQL'in asıl faydası çok sayıda bilinmeyen istemcidedir. İkinci bir API yüzeyi, ikinci bir yetkilendirme yüzeyi demektir — RBAC'ı iki kez doğrulamak risktir. | Üçüncü taraf istemci ekosistemi doğarsa |
| **Gerçek zamanlı işbirliği (WebSocket)** | Yoklama ve takvim ekranlarında canlı güncelleme çekici; ancak TanStack Query'nin yeniden getirme aralığı pratikte yeterli. Kalıcı bağlantı yönetimi, kimlik doğrulama ve yeniden bağlanma mantığı ciddi bir maliyet. | Aynı ekranda eşzamanlı düzenleme çakışması pilotta gerçek sorun olursa |
| **Mobil yerel uygulama (iOS/Android)** | İki ayrı platform, iki ayrı mağaza süreci ve iki ayrı sürüm döngüsü demek. PWA (§4.3), maliyetin küçük bir kısmıyla faydanın büyük kısmını verir. | PWA'nın yetmediği bir ihtiyaç (ör. arka plan konum/push zorunluluğu) doğarsa |
| **Kendi AI modelimizi eğitmek** | Yüzme performansı için özel model eğitmek, elimizde olmayan büyüklükte etiketli veri ister. Mevcut genel modeller + iyi istem mühendisliği + gerçek istatistik motoru, kıyaslanamayacak kadar iyi bir maliyet/fayda oranı sunuyor. | Çok yıllık, çok kurumlu veri havuzu oluşursa (öngörülebilir gelecekte hayır) |
| **Blockchain tabanlı sertifika doğrulama** | Sertifika doğrulama için imzalı PDF ve veritabanı kaydı yeterlidir. Blockchain burada çözülmemiş bir sorunu çözmez, yalnızca bağımlılık ve maliyet ekler. | Yok — bu fikir kapatılmıştır |
| **Ödeme ağ geçidi entegrasyonu (online tahsilat)** | Kart verisi işlemek PCI-DSS uyum yükümlülüğü doğurur. Mevcut finans modülü tahsilatı **kaydeder**, işlemez — bu ayrım bilinçlidir ve sistemi tüm bir uyum sınıfının dışında tutar. | Kurumlar somut talep ederse; ancak entegrasyon yalnızca barındırılan ödeme sayfası (hosted checkout) yöntemiyle, kart verisi sisteme hiç girmeden yapılacaktır |
| **Artımlı yedekleme** | §2.2'de açıklandı: mevcut veri hacminde tam yedek yeterli, yarım uygulanmış artımlı zincir veri kaybı riski taşır. | Bir kurulumda yedek boyutu 2 GB'ı aşarsa |
| **Web Push bildirimi** | iOS tarafındaki kısıtlar ve sertifika/anahtar yönetimi, e-posta/SMS'e (§4.4) göre çok daha yüksek maliyetli. | E-posta/SMS kanalları yetersiz kaldığında |

---

## 7. Katkı Rehberi

### 7.1 Geliştirme ortamı

```powershell
# 1) Depoyu alın ve backend bağımlılıklarını kurun
cd C:\SwimmingSchool\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

# 2) Veritabanı şemasını oluşturun
alembic upgrade head

# 3) Frontend bağımlılıkları
cd ..\frontend
npm ci

# 4) Geliştirme sunucularını birlikte başlatın
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

Ortam değişkenleri proje kökündeki `.env` dosyasından okunur
(`backend/app/core/config.py`). **`.env` asla depoya eklenmez**; CI bunu ayrıca
denetler ve `.gitignore` içinde `.env` satırı yoksa hattı düşürür.

### 7.2 Kod standartları

| Alan | Araç | Kural |
|---|---|---|
| Python biçim | `black` | 24.10.0, varsayılan ayarlar |
| Python lint | `ruff` | `ruff check .` uyarısız geçmeli |
| Python tip | `mypy` | `mypy app --ignore-missing-imports` |
| TypeScript tip | `tsc` | `strict` açık; `any` gerekçesiz kullanılmaz |
| TypeScript lint | `eslint` | `npm run lint` — `--max-warnings 0` |
| TypeScript biçim | `prettier` | `npm run format` |

**Kodlama ilkeleri.**

1. **Sır yok.** Hiçbir API anahtarı, parola veya bağlantı dizesi kaynak koda
   yazılmaz. Her şey `.env` üzerinden `Settings` nesnesine gelir.
2. **Loga sır yazılmaz.** Kullanıcıya veya loga bir anahtar gösterilecekse
   `mask_secret()` kullanılır.
3. **İzin kontrolü uçta yapılır.** Yeni bir uç nokta ekliyorsanız `Perm`
   içinden uygun izni bağlayın; arayüzde menü gizlemek yetkilendirme değildir.
4. **Hata mesajı iki dillidir.** Kullanıcıya dönen her mesaj `Accept-Language`
   başlığına göre TR/EN çözülür; yığın izi ve SQL istemciye asla sızmaz.
5. **Çeviri anahtarları eşit kalır.** TR'ye eklenen her anahtar EN'e de eklenir.
   CI'daki çeviri bütünlük adımı eksik anahtarda hattı düşürür.
6. **Migration'sız şema değişikliği olmaz.** Model değiştiyse Alembic revizyonu
   üretilir; CI `alembic check` ile modelle şemanın uyumunu doğrular.
7. **Yeni bağımlılık lisansı önce doğrulanır.** Yalnızca MIT / BSD / Apache-2.0 /
   ISC kabul edilir. Gerekçe ve lisans `THIRD_PARTY_NOTICES.md` belgesine
   işlenir (bkz. `docs/OPEN_SOURCE_RESEARCH.md` §2).
8. **Kopyalanan kod yok.** GPL/AGPL/LGPL/MPL lisanslı projelerden kod, şema veya
   migration kopyalanmaz; yalnızca kavramsal fikirler alınabilir.

### 7.3 Test beklentisi

- Her hata düzeltmesi için **önce başarısız olan bir test** yazılır; düzeltme
  o testi geçirir.
- Yeni bir uç nokta en az iki testle gelir: yetkili erişimin başarılı olduğu ve
  **yetkisiz erişimin 403 döndüğü**.
- Yeni bir iş kuralı için sınır durumu testi zorunludur (çakışma, kapasite,
  çift düşüm, negatif tutar).
- AI testleri **gerçek API çağrısı yapmaz**; sağlayıcılar mock'lanır. Bu kural
  istisnasızdır — CI'nın dış servise veya ücretli API'ye bağımlı olması kabul
  edilmez.

Test çalıştırma:

```powershell
cd C:\SwimmingSchool\backend
pytest tests -q                                    # tümü
pytest tests/test_scheduling.py -q                 # tek dosya
pytest tests -q --cov=app --cov-report=term-missing  # kapsamla
```

### 7.4 Dal ve commit düzeni

- Dallar `main` ve `develop` üzerinden akar; CI bu iki dala açılan
  pull request'lerde tetiklenir.
- Dal adları: `feature/<kısa-ad>`, `fix/<kısa-ad>`, `docs/<kısa-ad>`,
  `refactor/<kısa-ad>`.
- Commit başlığı [Conventional Commits](https://www.conventionalcommits.org/)
  biçiminde ve **72 karakterden kısa**:

```
feat(backup): PostgreSQL icin pg_dump anlik goruntu destegi
fix(attendance): telafi dersinde cift hak dusumu engellendi
docs(roadmap): v1.1 kapsamina RAG bilgi bankasi eklendi
test(scheduling): ayni kulvara es zamanli atama senaryosu
```

### 7.5 Pull request süreci

1. **Açmadan önce yerelde `FINAL_CHECK.bat` çalıştırın.** Kırmızı bir kapıyla
   PR açmayın.
2. PR açıklaması şunları içermelidir: ne değişti, **neden** değişti, nasıl test
   edildi, arayüz değişikliği varsa ekran görüntüsü.
3. Şema değişikliği varsa Alembic revizyon kimliği açıklamada belirtilir.
4. Yeni bağımlılık varsa lisansı ve gerekçesi yazılır.
5. CI'daki dört iş de (backend · frontend · security · integration) yeşil
   olmalıdır. `security` işinin gizli anahtar taraması **hiçbir koşulda**
   atlanmaz.
6. En az bir gözden geçirenin onayı gerekir. Gözden geçiren özellikle şunlara
   bakar: izin kontrolü var mı, iki dil eşit mi, sınır durumu test edildi mi,
   hata mesajı sızıntı yapıyor mu.
7. CHANGELOG'a giren değişiklikler (kullanıcıya görünen her şey) aynı PR içinde
   `CHANGELOG.md` dosyasının ilgili başlığına eklenir.

### 7.6 Güvenlik açığı bildirimi

Güvenlik açığı **herkese açık issue olarak bildirilmez.** Bulgu, proje
sorumlusuna doğrudan iletilir; düzeltme yayınlanana kadar ayrıntı paylaşılmaz.
Bildirimde etkilenen sürüm, yeniden üretim adımları ve etki değerlendirmesi yer
almalıdır.

---

## 8. Sürüm Politikası

### 8.1 Semantik sürümleme

Proje [Semantic Versioning 2.0.0](https://semver.org/lang/tr/) kurallarını
uygular: `BÜYÜK.KÜÇÜK.YAMA`.

| Bileşen | Ne zaman artar | Örnek |
|---|---|---|
| **BÜYÜK** | Geriye dönük uyumsuz değişiklik: uç nokta kaldırılması, yanıt şemasının bozulması, elle müdahale gerektiren veri göçü | 1.0.0 → 2.0.0 |
| **KÜÇÜK** | Geriye dönük uyumlu yeni özellik: yeni uç nokta, yeni ekran, yeni isteğe bağlı alan | 1.0.0 → 1.1.0 |
| **YAMA** | Geriye dönük uyumlu hata düzeltmesi, güvenlik yaması, performans iyileştirmesi, belge düzeltmesi | 1.0.0 → 1.0.1 |

**Sürüm numarasının tek kaynağı** `backend/app/core/config.py` içindeki
`app_version` alanıdır. `frontend/package.json` ve `desktop/launcher.py` bu
değerle uyumlu tutulur; sürüm bilgisi `/api/ping` ve `/api/v1/system/about`
uçlarından okunabilir.

**0.x dönemi uyarısı.** SemVer'e göre 1.0.0 öncesinde uyumluluk garantisi
verilmez. v0.9.0 → v1.0.0 geçişinde uç nokta imzalarında değişiklik olabilir;
bu değişiklikler CHANGELOG'da ayrıca listelenecektir.

### 8.2 API uyumluluğu

- Yayınlanmış bir uç nokta doğrudan silinmez. Önce **kullanımdan kaldırıldı
  (deprecated)** işaretlenir, OpenAPI açıklamasına not düşülür ve en az bir
  KÜÇÜK sürüm boyunca çalışmaya devam eder.
- Yanıt şemasına **alan eklemek** uyumlu bir değişikliktir; alan **kaldırmak**
  veya alanın tipini değiştirmek BÜYÜK sürüm gerektirir.
- API yolu `/api/v1/` önekiyle sürümlenmiştir. Uyumsuz bir toplu değişiklik
  gerekirse `/api/v2/` açılır ve `/api/v1/` bir geçiş dönemi boyunca yaşar.

### 8.3 Veritabanı göçü

- Her şema değişikliği bir Alembic revizyonudur; revizyonlar sıralı uygulanır.
- Uygulama açılışta şemayı **otomatik yükseltmez**; yükseltme bilinçli bir
  `alembic upgrade head` adımıdır. Bunun nedeni, kullanıcının haberi olmadan
  veri dönüşümü yapılmamasıdır.
- **Kural: yükseltmeden önce yedek.** Installer (§3.2) yükseltme akışında
  otomatik yedek alacak, ancak yedeğin varlığı yine de doğrulanacaktır.
- Geri alma (downgrade) revizyonları yazılır; ancak veri kaybına yol açacak bir
  geri alma varsa revizyon açıklamasında **açıkça belirtilir.**

### 8.4 Destek ve LTS yaklaşımı

Proje tek geliştiricili ve MIT lisanslıdır. Kurumsal bir SLA verilmez; buna
karşın öngörülebilir bir destek çerçevesi şudur:

| Sürüm hattı | Durum | Ne alır |
|---|---|---|
| Güncel KÜÇÜK sürüm (ör. 1.1.x) | Aktif | Yeni özellik + hata düzeltmesi + güvenlik yaması |
| Bir önceki KÜÇÜK sürüm (ör. 1.0.x) | Bakım | Yalnızca güvenlik yaması ve kritik hata düzeltmesi |
| Daha eski sürümler | Destek dışı | Yükseltme önerilir |

- **v1.0.0 uzun dönem referans sürümü olarak işaretlenecektir.** Pilot kurumların
  hemen yükseltmek zorunda kalmaması için, v1.0.x hattı v1.2.0 yayınlanana kadar
  güvenlik yaması almaya devam eder.
- Kritik güvenlik açıkları, destek dışı sürümler için de duyurulur; ancak yama
  yalnızca aktif ve bakımdaki hatlara üretilir.
- "Kritik hata" tanımı: veri kaybı, veri bozulması, yanlış finansal hesaplama
  veya yetkilendirme atlatma. Bu dört sınıf her zaman öncelikli işlenir.

### 8.5 Yayın kontrol listesi

Her yayın öncesi sırasıyla:

1. `FINAL_CHECK.bat` tümüyle yeşil (uyarı kabul, hata kabul değil).
2. `app_version` (`backend/app/core/config.py`) ve `frontend/package.json`
   sürüm alanları güncel ve birbiriyle tutarlı.
3. `CHANGELOG.md` içine tarihli yeni sürüm başlığı; bilinen kısıtlamalar bölümü
   gözden geçirilmiş.
4. Bu belgenin (`docs/ROADMAP.md`) durum tablosu (§1.2) gerçeği yansıtıyor.
5. `alembic upgrade head` temiz bir veritabanında hatasız çalışıyor;
   `alembic check` uyumlu.
6. Temiz bir Windows makinesinde `START_SWIMMING_SCHOOL.bat` ile duman testi:
   giriş, panel, bir öğrenci kaydı, bir rapor çıktısı.
7. Yedek al → doğrula → geri yükle turu bir kez elle koşuluyor.
8. `THIRD_PARTY_NOTICES.md` yeni bağımlılıkları içeriyor.
9. Sürüm etiketi (`git tag v<sürüm>`) atılıyor.

---

## Ek: Sürüm özeti

| Sürüm | Tema | Ana çıktı | Tahmini efor |
|---|---|---|---|
| **0.9.0** | Yayın adayı | Uçtan uca çalışan sistem, 240 uç nokta, 395 test fonksiyonu | — (tamamlandı) |
| **1.0.0** | Üretim hazırlığı | PostgreSQL yedekleme, Windows installer, pilot düzeltmeleri, E2E testleri, performans profilleme | 40–56 a-g |
| **1.1.0** | Bilgi ve entegrasyon | RAG bilgi bankası, bulut yedek hedefleri, PWA veli portalı, e-posta/SMS | 46–64 a-g |
| **1.2.0** | Donanım ve otomasyon | RFID/NFC turnike, video analiz, program optimizasyonu, çoklu şube | 60–90 a-g |

**Bu yol haritası bağlayıcı bir taahhüt değil, bir planlama belgesidir.**
Pilot bulguları, kullanıcı talebi ve teknik gerçekler değiştikçe kapsam ve
sıralama revize edilir. Her revizyon bu belgede tarihiyle kaydedilir.

---

*İlgili belgeler:* [`CHANGELOG.md`](../CHANGELOG.md) ·
[`docs/OPEN_SOURCE_RESEARCH.md`](OPEN_SOURCE_RESEARCH.md) ·
[`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) ·
[`LICENSE`](../LICENSE)
