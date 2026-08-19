# Yedekleme ve Geri Yükleme Kılavuzu

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'nin yedekleme, bütünlük doğrulama ve
felaket kurtarma yeteneklerini uçtan uca anlatır. Amacı, bir veri kaybı anında ne
yapacağınızı önceden bilmenizi sağlamaktır.

> Sürüm: 0.9.0 · Kaynak: `backend/app/services/backup.py`, `backend/app/api/v1/backup.py`
> Arayüz: **Ayarlar → Yedekleme** sekmesi

---

## 1. Yedekleme Nedir, Neler Yedeklenir

Bir yedek, sistemin belirli bir andaki durumunun tek bir ZIP dosyasına sıkıştırılmış
kopyasıdır. Bu dosyayı saklarsanız, veritabanı silinse veya bozulsa bile okulu o ana
geri döndürebilirsiniz.

### 1.1 Yedeğe dahil edilenler

| İçerik | Arşiv içindeki yol | Açıklama |
|---|---|---|
| Veritabanı | `database/swimming_school.db` | Tüm öğrenci, veli, eğitmen, ders, yoklama, üyelik, finans, performans ve yarışma kayıtları (55 tablo) |
| Ayarlar | `settings.json` | Sürüm, ortam, para birimi, dil, saat dilimi ve **sırlardan arındırılmış** AI yapılandırması |
| Yüklenen belgeler | `uploads/...` | `data/uploads` klasöründeki tüm dosyalar (sağlık raporu, fotoğraf, sözleşme vb.) — isteğe bağlı |
| Log dosyaları | `logs/*.log` | Uygulama günlükleri — isteğe bağlı, varsayılan **kapalı** |
| Bildirim dosyası | `backup_manifest.json` | Yedeğin kimlik kartı: kimlik, tarih, tür, sürüm, şema revizyonu, kayıt sayıları, dosya listesi ve SHA-256 özetleri |

Veritabanı kopyası, `sqlite3.Connection.backup()` çevrimiçi yedekleme API'si ile
alınır. Bu, program çalışırken ve başka bağlantılar açıkken bile **tutarlı** bir
kopya üretir; yarım yazılmış işlem kalmaz.

Manifest içindeki `record_counts` alanı şu 12 tablonun satır sayısını tutar ve daha
sonra doğrulamada karşılaştırma ölçütü olarak kullanılır: `users`, `students`,
`guardians`, `instructors`, `pools`, `lessons`, `attendances`, `memberships`,
`payments`, `invoices`, `performance_records`, `competitions`.

### 1.2 Yedeğe ASLA dahil edilmeyenler — güvenlik gereği

Yedek dosyası dışarı taşınabilen, e-postayla gönderilebilen, USB'ye kopyalanabilen
bir dosyadır. Bu yüzden içine sır konulmaz:

| Dahil edilmeyen | Neden |
|---|---|
| `.env` dosyası | İçinde `SECRET_KEY`, `NVIDIA_API_KEY`, `FIRST_ADMIN_PASSWORD` gibi değerler vardır |
| API anahtarları | AI sağlayıcı anahtarları `settings.json` içine yazılmadan önce temizlenir (`_sanitized_ai_config`) — maskeli hâlleri bile yedeğe girmez |
| `.key`, `.pem` uzantılı dosyalar | Özel anahtar / sertifika |
| Adında `credentials`, `secrets`, `token`, `id_rsa` geçen dosyalar | Kimlik bilgisi taşıma ihtimali |

Bu filtre `EXCLUDED_PATTERNS` listesiyle uygulanır ve hem `uploads` hem `logs`
klasörlerine tarama yaparken çalışır.

> **Parolalar hakkında doğru bilgi:** Sistem hiçbir yerde açık metin parola
> saklamaz. Kullanıcı parolaları veritabanında yalnızca bcrypt özeti (hash) olarak
> tutulur ve yedek bu özetleri içerir — içermeseydi geri yükleme sonrası hiç kimse
> giriş yapamazdı. Açık parolalar ve API anahtarları yalnızca `.env` dosyasındadır
> ve **o dosya yedeğe alınmaz**. Bu nedenle bir yedeği geri yükledikten sonra `.env`
> dosyasını ayrıca elde etmeniz gerekir (bkz. §8c).

### 1.3 Yedek dosyasının yapısı

```
bkp_20260818_230000_scheduled.zip
├── backup_manifest.json          ← kimlik + SHA-256 özetleri
├── database/
│   └── swimming_school.db        ← tutarlı SQLite anlık görüntüsü
├── settings.json                 ← sırlardan arındırılmış yapılandırma
├── uploads/                      ← (include_uploads=true ise)
│   └── ...
└── logs/                         ← (include_logs=true ise)
    └── application.log
```

Yedek kimliği şu kalıpla üretilir: `bkp_YYYYAAGG_SSDDss_<tür>`.
Örnek: `bkp_20260818_230000_scheduled`.

Arşivin tamamının SHA-256 özeti `BackupRecord.checksum_sha256` alanında saklanır;
tek bir baytı değişse doğrulama başarısız olur.

---

## 2. Yedek Türleri

`BackupType` (bkz. `backend/app/models/enums.py`) yedeğin **neden** alındığını
belirtir. İçerik ve doğrulama akışı hepsinde aynıdır.

| Tür | Kod | Ne zaman oluşur | Kim başlatır |
|---|---|---|---|
| Tam | `full` | Sistemin tamamının bilinçli olarak arşivlenmesi | Kullanıcı (tür seçerek) |
| Manuel | `manual` | "Şimdi Yedekle" düğmesi — **varsayılan tür** | Kullanıcı |
| Zamanlanmış | `scheduled` | Cron zamanı geldiğinde otomatik | Sistem (APScheduler) |
| Güncelleme öncesi | `pre_update` | Program sürümü yükseltilmeden önce | Kullanıcı / yükseltme adımı |
| Migration öncesi | `pre_migration` | Alembic şema değişikliğinden önce | Kullanıcı / yönetici |
| Güvenlik yedeği | `safety` | **Her geri yükleme öncesinde otomatik** | Sistem (geri yükleme akışı) |
| Artımlı | `incremental` | Mimaride tanımlı, bu sürümde **uygulanmadı** | — |

`safety` türündeki yedekler otomatik olarak `is_protected = true` işaretlenir; bu
sayede saklama politikası bunları asla silmez.

### 2.1 Yedek durumları

| Durum | Anlamı |
|---|---|
| `creating` | Arşiv yazılıyor |
| `completed` | Arşiv yazıldı, henüz doğrulanmadı |
| `verified` | Arşiv yazıldı **ve tüm bütünlük kontrolleri geçti** — güvenilir yedek budur |
| `corrupted` | En az bir bütünlük kontrolü başarısız |
| `failed` | Yedek alınamadı; yarım kalan arşiv dosyası silinir |

Geri yükleme için yalnızca `verified` durumundaki yedekleri kullanın.

---

## 3. Yedek Alma

### 3.1 Arayüzden adım adım

1. Sol menüden **Ayarlar** ekranını açın.
2. **Yedekleme** sekmesine geçin. (Sekme yalnızca `backup:read` izniniz varsa görünür.)
3. Sağ üstteki **Şimdi Yedekle** düğmesine basın. (`backup:create` izni gerekir.)
4. Açılan pencerede seçenekleri belirleyin:

| Seçenek | Varsayılan | Açıklama |
|---|---|---|
| **Yedek türü** | `manual` | §2'deki türlerden biri |
| **Not** | boş | Bu yedeği neden aldığınızı yazın ("v0.9 güncellemesi öncesi" gibi) |
| **Belgeleri dahil et** (`include_uploads`) | **Açık** | `data/uploads` altındaki dosyaları arşive ekler. Kapatırsanız yedek küçülür ama belgeler geri gelmez |
| **Logları dahil et** (`include_logs`) | **Kapalı** | `logs/*.log` dosyalarını ekler. Yalnızca bir sorunu inceletmek için gönderiyorsanız açın |
| **Koru** (`protect`) | Kapalı | Yedeği saklama politikasından muaf tutar; otomatik temizlik bu yedeği silmez |

5. **Yedekle**'yi onaylayın. İşlem bitince liste yenilenir ve satırda durum rozeti
   ile doğrulama mesajı görünür (`Tüm kontroller başarılı (11/11).` gibi).

Yedekler varsayılan olarak `C:\SwimmingSchool\backups` klasörüne yazılır. Klasör
yolunu **Yedek Konumu** kartındaki kopyalama kutusundan alabilirsiniz.

### 3.2 API ile

```bash
# Şimdi yedekle (belgeler dahil, loglar hariç, korumalı)
curl -X POST http://127.0.0.1:8000/api/v1/backup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "backup_type": "pre_update",
        "note": "0.9.0 -> 1.0.0 yükseltmesi öncesi",
        "include_uploads": true,
        "include_logs": false,
        "protect": true
      }'
```

Yanıt, `backup_id`, `size_mb`, `status` ve `verification_message` alanlarını içerir.

### 3.3 Yedekleme uçları

| Yöntem | Yol | İzin | Açıklama |
|---|---|---|---|
| GET | `/api/v1/backup/status` | `backup:read` | Son yedek, toplam boyut, korunan sayısı, sıradaki zamanlanmış yedek |
| GET | `/api/v1/backup` | `backup:read` | Yedek listesi (varsayılan 100 kayıt) |
| POST | `/api/v1/backup` | `backup:create` | Yeni yedek oluştur |
| POST | `/api/v1/backup/{backup_id}/verify` | `backup:read` | Bütünlük doğrulaması çalıştır |
| GET | `/api/v1/backup/{backup_id}/restore-preview` | `backup:restore` | Geri yükleme önizlemesi (hiçbir şey değiştirmez) |
| POST | `/api/v1/backup/restore` | `backup:restore` | Geri yükleme (`confirm=true` zorunlu) |
| POST | `/api/v1/backup/{backup_id}/protect` | `backup:create` | Koruma işaretini aç/kapat |
| DELETE | `/api/v1/backup/{backup_id}` | `backup:create` | Yedeği sil (korunan yedek silinemez) |
| POST | `/api/v1/backup/cleanup` | `backup:create` | Saklama politikasını uygula |
| GET | `/api/v1/backup/settings/current` | `backup:read` | Cron ve saklama ayarları |
| GET | `/api/v1/backup/location/open` | `backup:read` | Yedek klasörü yolu, dosya sayısı, son 10 dosya |
| GET | `/api/v1/backup/restores/history` | `backup:read` | Geri yükleme geçmişi |

### 3.4 Kim yedek alabilir, kim geri yükleyebilir

| İzin | Sahip roller |
|---|---|
| `backup:read` | Sistem Yöneticisi, Yüzme Okulu Müdürü, Operasyon Müdürü |
| `backup:create` | Sistem Yöneticisi, Yüzme Okulu Müdürü, Operasyon Müdürü |
| `backup:restore` | **Yalnızca Sistem Yöneticisi ve Yüzme Okulu Müdürü** |

Geri yükleme izni bilinçli olarak en dar tutulmuştur; veri kaybı riski taşıyan tek
işlem odur.

---

## 4. Bütünlük Doğrulama

Her yedek oluşturulduktan **hemen sonra otomatik olarak** doğrulanır. Ayrıca listede
her satırın **Doğrula** düğmesiyle istediğiniz zaman yeniden çalıştırabilirsiniz.

Doğrulama 8 aşamada, toplam 11 kontrol maddesiyle yürür. Her madde `PASS` / `FAIL`
olarak raporlanır; **bir tanesi bile başarısızsa yedek `corrupted` işaretlenir.**

| # | Aşama | Kontrol kodu | Ne doğrular | Başarısızsa ne anlama gelir |
|---|---|---|---|---|
| 1 | Dosya var mı | `file_exists` | `BackupRecord.file_path` yolundaki ZIP dosyası diskte duruyor mu | Dosya elle silinmiş, taşınmış ya da disk bağlı değil. Doğrulama burada durur |
| 2 | Boyut mantıklı mı | `size_reasonable` | Arşiv 1024 bayttan büyük mü | Yazma yarıda kesilmiş; içi boş bir kabuk dosya |
| 3 | Sağlama toplamı | `checksum_matches` | Diskteki dosyanın SHA-256'sı, oluşturma anında kaydedilen özetle birebir aynı mı | Dosya oluşturulduktan sonra **değişmiş**: bozuk kopyalama, disk hatası veya kurcalama |
| 4 | Arşiv bütünlüğü | `archive_intact` | `ZipFile.testzip()` — arşivdeki her girdinin CRC'si tutuyor mu | ZIP içindeki bir veya birden fazla dosya bozulmuş |
| 5 | Manifest | `manifest_present`, `manifest_valid`, `secrets_excluded`, `database_present` | `backup_manifest.json` arşivde var mı; içindeki `backup_id` kayıtla eşleşiyor mu; `excludes_secrets: true` mi; `database/swimming_school.db` girdisi duruyor mu | Yedek yanlış/başka bir yedekle karışmış, ya da sır dışlama garantisi taşımıyor |
| 6 | Veritabanı açılıyor mu | `database_integrity` | Arşivden geçici klasöre çıkarılan `.db` dosyası açılıp `PRAGMA integrity_check` çalıştırılır; sonuç `ok` olmalı | SQLite dosyası sayfa düzeyinde bozuk — geri yüklenirse çalışmaz |
| 7 | Tablolar okunuyor mu | `tables_readable` | `sqlite_master` üzerinden tablo sayısı okunur, 10'dan fazla olmalı | Şema eksik ya da boş bir veritabanı yedeklenmiş |
| 8 | Kayıt sayıları tutuyor mu | `record_counts_match` | Arşivdeki veritabanındaki `students` satır sayısı, manifestte kayıtlı beklenen sayıya eşit mi | Anlık görüntü ile manifest arasında tutarsızlık; yedek güvenilir değil |

Doğrulama bitince özet mesaj kaydedilir:
`Tüm kontroller başarılı (11/11).` veya `Doğrulama başarısız: 9/11 kontrol geçti.`
Bu metin liste ekranında **Bütünlük** sütununda görünür.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/backup/bkp_20260818_230000_scheduled/verify \
  -H "Authorization: Bearer $TOKEN"
```

> Doğrulama sırasında `backups/.verify_<backup_id>` adında geçici bir klasör açılır
> ve işlem bitince her koşulda silinir. Yedeğin kendisine dokunulmaz.

---

## 5. Otomatik Yedekleme

Otomatik yedekleme `.env` dosyasından açılır ve program başlarken APScheduler ile
kurulur (`start_backup_scheduler`). Zamanlayıcı, `APP_TIMEZONE` ayarındaki saat
dilimine göre çalışır (varsayılan `Europe/Istanbul`).

```ini
# .env
BACKUP_SCHEDULE_ENABLED=true
BACKUP_SCHEDULE_CRON=0 23 * * *     # her gün 23:00
BACKUP_DIR=./backups
BACKUP_RETENTION_DAILY=7
BACKUP_RETENTION_WEEKLY=4
BACKUP_RETENTION_MONTHLY=12
```

Değişiklikten sonra programı yeniden başlatın (`START_SWIMMING_SCHOOL.bat`).

### 5.1 Cron ifadesi örnekleri

Biçim: `dakika saat ayın_günü ay haftanın_günü`

| İfade | Anlamı |
|---|---|
| `0 23 * * *` | **Her gün saat 23:00** (varsayılan) |
| `30 2 * * *` | Her gece 02:30 |
| `0 23 * * 0` | **Her Pazar 23:00** (0 = Pazar) |
| `0 23 * * 6` | Her Cumartesi 23:00 |
| `0 3 1 * *` | **Ayın ilk günü 03:00** |
| `0 12,23 * * *` | Her gün 12:00 ve 23:00 (günde iki kez) |
| `0 23 * * 1-5` | Hafta içi her gün 23:00 |
| `0 */6 * * *` | Altı saatte bir |

Havuzun kapandığı, kimsenin veri girmediği bir saati seçin. Yoğun saatte alınan
yedek de tutarlıdır, ancak disk ve işlemciyi gereksiz meşgul eder.

### 5.2 Zamanlanmış yedek çalıştığında ne olur

1. `scheduled` türünde yedek alınır ve otomatik doğrulanır.
2. Hemen ardından **saklama politikası uygulanır** (`apply_retention`) — eski
   yedekler temizlenir.
3. `system_admin` rolündeki kullanıcılara bir bildirim gönderilir. Başlık:
   *"Otomatik yedek tamamlandı (24.6 MB)"*, gövde kısmında doğrulama mesajı yer alır.
   Yedek `verified` değilse bildirim **uyarı** seviyesinde gönderilir.

Sıradaki çalışma zamanını **Ayarlar → Yedekleme → Sıradaki Yedek** kartından
görebilirsiniz.

---

## 6. Saklama Politikası

Saklama politikası, disk dolmasın diye eski yedekleri **kademeli olarak seyreltir**:
yakın geçmişte her gün, orta vadede haftada bir, uzak geçmişte ayda bir yedek kalır.

| Ayar | Varsayılan | Anlamı |
|---|---|---|
| `BACKUP_RETENTION_DAILY` | 7 | Son 7 günün **tüm** yedekleri saklanır |
| `BACKUP_RETENTION_WEEKLY` | 4 | 7 günden eski, 28 (4×7) günden yeni aralıkta **her ISO haftasından bir** yedek saklanır |
| `BACKUP_RETENTION_MONTHLY` | 12 | 28 günden eski, 372 (12×31) günden yeni aralıkta **her aydan bir** yedek saklanır |

Karar sırası (`apply_retention`, yedekler en yeniden eskiye doğru taranır):

1. Yedeğin yaşı `daily` değerinden küçük veya eşitse → **sakla**.
2. Değilse, yaşı `weekly × 7` gününden küçük veya eşitse ve o ISO haftasından
   henüz bir yedek saklanmadıysa → **sakla** (o haftanın en yenisi).
3. Değilse, yaşı `monthly × 31` gününden küçük veya eşitse ve o aydan henüz bir
   yedek saklanmadıysa → **sakla** (o ayın en yenisi).
4. Hiçbiri geçerli değilse → **sil**.

### 6.1 Korunan yedekler

`is_protected = true` işaretli yedekler bu taramaya **hiç girmez**; saklama
politikası onları asla silmez ve `DELETE /api/v1/backup/{id}` çağrısı da
`backup.protected` hatasıyla reddedilir. Bir yedeği kalıcı hâle getirmek için:

* Listede satırın **Koru** düğmesine basın, veya
* `POST /api/v1/backup/{backup_id}/protect?protect=true` çağırın.

Korumayı kaldırmak için aynı uca `protect=false` gönderin.

Şu yedekleri korumaya almanız önerilir: sezon sonu arşivi, büyük sürüm yükseltmesi
öncesi `pre_update` yedeği, denetim/muhasebe kapanışı yedeği.

### 6.2 Politikayı elle çalıştırma

**Ayarlar → Yedekleme → Temizle** düğmesi veya:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/backup/cleanup \
  -H "Authorization: Bearer $TOKEN"
```

Yanıt: silinen yedek sayısı, silinen kimlikler, boşalan alan (MB) ve saklanan sayı.

---

## 7. Geri Yükleme

Geri yükleme, mevcut veritabanını yedekteki veritabanıyla **değiştirir**. Yedek
alındıktan sonra girilen tüm kayıtlar kaybolur. Bu yüzden akış çok adımlı ve
geri alınabilir tasarlanmıştır.

### 7.1 Güvenli geri yükleme akışı

```
1. DOĞRULA        verify_backup() — 11 kontrol
                  ✗ başarısız → işlem burada DURUR, hiçbir şey değişmez
2. GÜVENLİK YEDEĞİ create_backup(type=safety, protect=true)
                  ✗ alınamazsa → işlem DURUR, hiçbir şey değişmez
3. ÖNİZLEME       restore-preview — neyin değişeceğini gösterir
4. ONAY           confirm=true olmadan uç çalışmaz
5. GERİ YÜKLE     bağlantıları kapat → .db.pre_restore kopyası → -wal/-shm temizle
                  → yedekteki .db dosyasını yerine koy → belgeleri geri yaz
6. BÜTÜNLÜK       PRAGMA integrity_check + öğrenci sayımı + SELECT 1 sağlık testi
7. ROLLBACK       herhangi bir adım patlarsa .db.pre_restore geri konur
```

Her adımın sonucu (`success` / `failed`) yanıtın `steps` dizisinde ve
`RestoreRecord` tablosunda saklanır; **Geri Yükleme Geçmişi** kartından görülebilir.

### 7.2 Arayüzden adım adım

1. **Ayarlar → Yedekleme** sekmesini açın.
2. Geri yüklemek istediğiniz yedeği bulun. Durumunun **`verified`** olduğunu
   doğrulayın. Değilse önce **Doğrula**'ya basın.
3. Satırdaki **Geri Yükle** düğmesine basın. (`backup:restore` izni gerekir.)
4. **Önizleme ekranı açılır. Kapatmadan önce mutlaka okuyun** (bkz. §7.3).
5. **Güvenlik yedeği al** kutusunun işaretli kaldığından emin olun (varsayılan açık).
6. Onay kutusunu işaretleyip **Geri Yükle**'yi tıklayın.
7. İşlem bitince adım listesi ve sonuç mesajı görünür.
8. **Programı kapatıp yeniden başlatın.** Sonuç mesajı da bunu söyler:
   *"Geri yükleme tamamlandı. Değişikliklerin tam olarak etkin olması için
   uygulamayı yeniden başlatın."*

### 7.3 Önizleme ekranı nasıl okunur

Önizleme (`GET /api/v1/backup/{backup_id}/restore-preview`) hiçbir şeyi
değiştirmez; yalnızca karşılaştırma yapar.

| Alan | Ne gösterir | Nasıl okunur |
|---|---|---|
| `integrity_ok` | Yedek doğrulamayı geçti mi | `false` ise geri yüklemeyin |
| `backup_created_at` | Yedeğin alındığı an | Bu andan sonraki her şey kaybolacak |
| `backup_app_version` / mevcut sürüm | Program sürümleri | Farklıysa uyarı çıkar |
| `backup_db_revision` / `current_db_revision` | Alembic şema revizyonları | Farklıysa geri yükleme sonrası migration gerekebilir |
| `revision_compatible` | Şema revizyonları aynı mı | `false` → dikkatli ilerleyin |
| `current_counts` | Şu andaki kayıt sayıları | 12 tablo için |
| `backup_counts` | Yedekteki kayıt sayıları | 12 tablo için |
| `differences` | `yedek − mevcut` farkı | **Negatif sayı = o tabloda kayıt kaybedeceksiniz** |
| `warnings` | İnsan diliyle uyarılar | Aşağıya bakın |

**Kayıp uyarısı — en kritik satır.** Fark negatifse şu uyarı üretilir:

> Bu geri yükleme sonucunda bazı kayıtlar KAYBOLACAK: students: 14, payments: 37

Bu, "yedek alındıktan sonra 14 öğrenci ve 37 ödeme girilmiş, geri yükleme bunları
silecek" demektir. Bu satırı gördüğünüzde:

* Kaybolacak kayıtları önce dışa aktarın (Raporlar → Excel/CSV), veya
* Daha yeni bir yedek seçin, veya
* Kaybı kabul edip devam edin — güvenlik yedeği sayesinde geri dönebilirsiniz.

Diğer uyarı metinleri:

| Uyarı | Anlamı |
|---|---|
| *Yedek bütünlük doğrulamasından geçemedi. Geri yükleme önerilmez.* | `corrupted` yedek — kullanmayın |
| *Veritabanı şema sürümü farklı (yedek: `abc123`, mevcut: `def456`)...* | Yedek eski bir şemadan; geri yükleme sonrası `alembic upgrade head` gerekebilir |
| *Program sürümü farklı (yedek: 0.8.0, mevcut: 0.9.0).* | Yedek eski bir program sürümünden alınmış |

### 7.4 API ile geri yükleme

```bash
# 1) Önce önizleme (hiçbir şeyi değiştirmez)
curl http://127.0.0.1:8000/api/v1/backup/bkp_20260818_230000_scheduled/restore-preview \
  -H "Authorization: Bearer $TOKEN"

# 2) Onaylı geri yükleme
curl -X POST http://127.0.0.1:8000/api/v1/backup/restore \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "backup_id": "bkp_20260818_230000_scheduled",
        "confirm": true,
        "create_safety_backup": true
      }'
```

`confirm` alanı `false` veya eksikse istek `confirmation_required` doğrulama
hatasıyla reddedilir. `create_safety_backup` alanını `false` yapmayın — güvenlik
ağınızı kendi elinizle kaldırmış olursunuz.

Yanıt:

```json
{
  "success": true,
  "backup_id": "bkp_20260818_230000_scheduled",
  "safety_backup_id": "bkp_20260819_101512_safety",
  "message": "Geri yükleme tamamlandı. Değişikliklerin tam olarak etkin olması için uygulamayı yeniden başlatın.",
  "rolled_back": false,
  "steps": [
    {"step": "verify_backup",   "status": "success", "detail": "Tüm kontroller başarılı (11/11)."},
    {"step": "safety_backup",   "status": "success", "detail": "bkp_20260819_101512_safety"},
    {"step": "extract_archive", "status": "success", "detail": "128 belge"},
    {"step": "restore_database","status": "success", "detail": "C:\\SwimmingSchool\\data\\swimming_school.db"},
    {"step": "restore_uploads", "status": "success", "detail": ""},
    {"step": "integrity_check", "status": "success", "detail": "öğrenci sayısı: 412"},
    {"step": "health_check",    "status": "success", "detail": "şema sürümü: a1b2c3d4e5f6"}
  ]
}
```

### 7.5 Rollback — bir şey ters giderse

Geri yükleme sırasında dosya kopyalanmadan hemen önce mevcut veritabanının bir
kopyası `swimming_school.db.pre_restore` adıyla alınır. Sonraki adımlardan biri
başarısız olursa (dosya kilitli, disk dolu, bozuk veritabanı) bu kopya otomatik
olarak geri konur ve yanıtta `rolled_back: true` döner:

> Geri yükleme başarısız: RuntimeError. Sistem önceki durumuna döndürüldü.

Rollback de başarısız olursa yanıt, adım 2'de alınan **güvenlik yedeğinin
kimliğini** gösterir. O yedekle ikinci bir geri yükleme deneyebilirsiniz.

Her şey yolunda giderse `.pre_restore` dosyası silinir.

---

## 8. Felaket Kurtarma Senaryoları

### (a) Yanlış toplu silme

**Belirti:** Bir kullanıcı yanlışlıkla bir grubu, bir dönemin derslerini veya çok
sayıda öğrenciyi sildi.

**Çözüm:**

1. **Hemen yeni veri girişini durdurun.** Her geçen dakika, geri yükleme ile
   kaybedilecek yeni kayıt üretir.
2. **Ayarlar → Yedekleme**'yi açın, silme işleminden **önceki** en yeni `verified`
   yedeği bulun. Silmenin ne zaman olduğunu **Denetim Kaydı** (audit log)
   ekranından öğrenebilirsiniz.
3. **Geri Yükle** → önizlemeyi okuyun. Kayıp uyarısındaki tablolar, silme sonrası
   girilen gerçek yeni kayıtları gösterir.
4. Kaybolacak yeni kayıtlar varsa önce onları rapor olarak dışa aktarın
   (Raporlar → Öğrenci Listesi / Tahsilat Raporu → Excel).
5. Onaylayıp geri yükleyin, programı yeniden başlatın.
6. Adım 4'te dışa aktardığınız kayıtları elle yeniden girin.

### (b) Veritabanı bozulması

**Belirti:** Program açılmıyor, "database disk image is malformed" benzeri hata,
ekranlar boş geliyor, loglarda SQLite hataları.

**Çözüm:**

1. Programı kapatın.
2. `C:\SwimmingSchool\data\swimming_school.db` dosyasını **silmeyin**; adını
   `swimming_school.db.bozuk` yapıp kenara alın. İnceleme gerekebilir.
3. Programı başlatın — boş bir veritabanı oluşturulur ve varsayılan roller yüklenir.
4. Yönetici hesabıyla girin (varsayılan e-posta: `admin@yuzmeokulu.local`).
5. **Ayarlar → Yedekleme** → en yeni `verified` yedeği seçin → **Doğrula** →
   **Geri Yükle**.
6. Programı yeniden başlatın ve öğrenci sayısı, son ödemeler gibi birkaç kaydı
   gözle kontrol edin.

> Yedek listesi de veritabanında tutulduğu için boş veritabanında liste boş görünebilir.
> Bu durumda ZIP dosyaları hâlâ `backups` klasöründedir; onları geri yüklemek için
> §8c adımlarını izleyin.

### (c) Donanım arızası — bilgisayar tamamen kayboldu

**Belirti:** Disk öldü, bilgisayar çalındı veya yandı.

**Ön koşul:** Yedeklerin bir kopyası **dış ortamda** duruyor (bkz. §9). Yalnızca
aynı diskte duran yedek, disk arızasında sizi kurtarmaz.

**Çözüm:**

1. Yeni bilgisayara programı kurun ve bir kez çalıştırıp kapatın
   (`START_SWIMMING_SCHOOL.bat`) — klasör yapısı oluşsun.
2. Dış ortamdaki `bkp_*.zip` dosyalarını yeni makinedeki `backups` klasörüne kopyalayın.
3. `.env` dosyasını yeniden oluşturun — **yedekte yoktur**. `.env.example` dosyasını
   kopyalayıp `SECRET_KEY`, `NVIDIA_API_KEY` gibi değerleri yeniden girin.
   `SECRET_KEY` değişirse yalnızca açık oturumlar düşer, veri kaybı olmaz.
4. Programı başlatın, yönetici hesabıyla girin.
5. Veritabanı boş olduğu için yedek listesi de boştur. En kolay yol: en yeni ZIP
   dosyasının içindeki `database/swimming_school.db` dosyasını çıkarıp
   `data\swimming_school.db` olarak kopyalayın; `uploads/` klasörünü de
   `data\uploads` altına açın. Programı yeniden başlatın.
6. Açılan sistemde **Ayarlar → Yedekleme** listesi eski yedekleri yeniden gösterir;
   bundan sonrasında normal geri yükleme akışı kullanılabilir.
7. Son adım: hemen yeni bir `manual` yedek alın ve **koru** işaretleyin.

### (d) Hatalı migration

**Belirti:** Alembic ile şema güncellendi, ardından ekranlar hata veriyor ya da
veri yanlış görünüyor.

**Çözüm:**

1. Programı durdurun.
2. Migration'dan önce aldığınız `pre_migration` yedeğini kullanın. (Bu yüzden her
   şema değişikliğinden önce bu türde yedek alın ve **koru** işaretleyin.)
3. Şemayı geri alın:
   ```bash
   cd C:\SwimmingSchool\backend
   alembic downgrade -1
   ```
4. Programı başlatın, **Ayarlar → Yedekleme** → `pre_migration` yedeği →
   **Doğrula** → **Geri Yükle**.
5. Önizlemede `revision_compatible` alanına dikkat edin; geri yüklenen veritabanının
   şema revizyonu ile kodun beklediği revizyon aynı olmalıdır.
6. Programı yeniden başlatın.

> Migration sorunları veri kaybından çok şema uyumsuzluğu yaratır. Doğru sıralama
> her zaman **önce yedek, sonra migration**'dır.

---

## 9. Yedeklerin Dış Ortama Kopyalanması

Bu sürümde bulut yedekleme hedefi yoktur (bkz. §10). Yedekler yalnızca yerel diske
yazılır. Bu, **tek nokta arızası** demektir: disk giderse yedek de gider.

### 9.1 3-2-1 kuralı

| Rakam | Kural | Bu sistemde karşılığı |
|---|---|---|
| **3** | En az 3 kopya | Canlı veritabanı + `backups` klasörü + dış ortam kopyası |
| **2** | En az 2 farklı ortam | Bilgisayarın diski + harici disk / NAS / bulut sürücü |
| **1** | En az 1 kopya farklı fiziksel konumda | Okul dışında: müdür ofisi, banka kasası veya bulut hesabı |

### 9.2 Pratik uygulama

**Haftalık el ile kopyalama (en basit yöntem):**

1. **Ayarlar → Yedekleme → Klasörü Aç** ile yolu kopyalayın
   (varsayılan `C:\SwimmingSchool\backups`).
2. Harici diski takın.
3. Son 1-2 haftanın `bkp_*.zip` dosyalarını kopyalayın. Windows'ta:
   ```powershell
   robocopy "C:\SwimmingSchool\backups" "E:\YuzmeOkulu_Yedek" bkp_*.zip /XO
   ```
   `/XO` yalnızca yeni/güncellenmiş dosyaları kopyalar.
4. Diski çıkarın ve **bilgisayardan uzakta** saklayın.

**Bulut sürücü ile otomatik kopyalama:** OneDrive / Google Drive / Dropbox
istemcisinde eşitlenen bir klasör oluşturun ve `.env` içinde yedek yolunu oraya
gösterin:

```ini
BACKUP_DIR=C:/Users/kullanici/OneDrive/YuzmeOkulu_Yedek
```

Bu durumda program yedeği doğrudan eşitlenen klasöre yazar ve istemci onu buluta
yükler. Yedeğin içinde API anahtarı ve `.env` bulunmadığını unutmayın — yine de
klasörü paylaşıma açmayın; **öğrenci kişisel verisi içerir (KVKK/GDPR)**.

### 9.3 Kurtarma tatbikatı

Yılda en az bir kez, tercihen sezon başında:

1. Bir dış ortam kopyasını **başka bir bilgisayara** taşıyın.
2. Orada §8c adımlarını uygulayarak sistemi ayağa kaldırın.
3. Öğrenci sayısı, son ayın tahsilat toplamı ve birkaç performans kaydını gözle
   doğrulayın.

Denenmemiş yedek, yedek sayılmaz.

---

## 10. Sınırlamalar

Bu sürümde (0.9.0) bilinçli olarak yapılmayanlar:

| Sınırlama | Ayrıntı | Ne zaman |
|---|---|---|
| **Yalnızca SQLite** | Otomatik yedekleme ve geri yükleme SQLite için çalışır. Veritabanı PostgreSQL ise `create_backup` şu hatayı verir: *"Bu sürümde otomatik yedekleme yalnızca SQLite için desteklenir. PostgreSQL için pg_dump kullanın."* Geri yükleme de aynı şekilde reddedilir | PostgreSQL için `pg_dump` akışı 1.0.0'a planlandı |
| **Artımlı yedek yok** | `BackupType.INCREMENTAL` enum'da tanımlı, ancak uygulanmadı. Her yedek tam yedektir | Yol haritasında |
| **Bulut hedefi yok** | `BackupProvider` soyutlaması hazır, fakat yalnızca `LocalDiskProvider` uygulanmış durumda. Drive / OneDrive / S3 bağlayıcısı yok | 1.1.0 |
| **Yedek indirme ucu yok** | Yedek dosyası API üzerinden indirilemez; klasöre erişmeniz gerekir. `GET /backup/location/open` yalnızca yolu döndürür | — |
| **Şifreleme yok** | ZIP dosyası parolasız ve şifresizdir. Kişisel veri içerdiği için **fiziksel erişimi kısıtlayın** | — |
| **Yalnızca `.log` uzantısı** | `include_logs` seçeneği `logs` klasöründeki yalnızca `*.log` dosyalarını alır; döndürülmüş (`.log.1`) dosyalar dahil edilmez | — |
| **Yeniden başlatma gerekir** | Geri yükleme sonrası açık bağlantılar eski dosyaya işaret edebilir; program yeniden başlatılmalıdır | — |

---

## 11. Sorun Giderme

| Belirti | Olası neden | Çözüm |
|---|---|---|
| Yedekleme sekmesi görünmüyor | `backup:read` izniniz yok | Sistem Yöneticisi, Okul Müdürü veya Operasyon Müdürü rolü gerekir |
| "Şimdi Yedekle" düğmesi yok | `backup:create` izniniz yok | Aynı roller gerekir |
| "Geri Yükle" düğmesi yok | `backup:restore` izniniz yok | Yalnızca Sistem Yöneticisi ve Yüzme Okulu Müdürü |
| Yedek `failed` durumunda | Disk dolu, klasör yazılamıyor veya veritabanı dosyası bulunamadı | Satırdaki hata mesajını okuyun; `backups` klasörünün yazılabilir olduğunu ve boş alanı kontrol edin |
| Doğrulama `file_exists` FAIL | ZIP dosyası elle silinmiş/taşınmış | Dosyayı geri koyun veya kaydı silip yeni yedek alın |
| Doğrulama `checksum_matches` FAIL | Dosya oluşturulduktan sonra değişmiş (bozuk kopyalama, disk hatası) | Yedeği kullanmayın; dış ortamdaki kopyayı deneyin, yeni yedek alın, diski kontrol edin |
| Doğrulama `database_integrity` FAIL | Arşivdeki SQLite dosyası bozuk | Bu yedek kurtarılamaz; bir önceki `verified` yedeğe dönün |
| Doğrulama `record_counts_match` FAIL | Manifest ile anlık görüntü tutmuyor | Yedeği geri yüklemeyin, yeni yedek alın |
| Yedek silinemiyor | Yedek korumalı (`backup.protected` hatası) | Önce **Koru**'yu kapatın (`protect=false`), sonra silin |
| Geri yükleme "confirmation_required" hatası veriyor | `confirm` alanı gönderilmedi | Arayüzde onay kutusunu işaretleyin; API'de `"confirm": true` gönderin |
| Geri yükleme "Güvenlik yedeği alınamadı" diyor | Disk dolu veya klasör yazılamıyor | Yer açın; işlem hiçbir şeyi değiştirmeden durdurulmuştur, veri güvendedir |
| Geri yükleme başarısız, `rolled_back: true` | Dosya kilitliydi veya kopyalama patladı | Sistem eski hâline döndü. Programı tamamen kapatın (görev yöneticisinden `python`/`uvicorn` süreçlerini kontrol edin) ve tekrar deneyin |
| Geri yükleme sonrası eski veriler görünüyor | Uygulama yeniden başlatılmadı | `START_SWIMMING_SCHOOL.bat` ile kapatıp açın |
| Zamanlanmış yedek çalışmıyor | `BACKUP_SCHEDULE_ENABLED=false` veya cron ifadesi hatalı | `.env` değerini `true` yapın, cron biçimini §5.1'e göre düzeltin, programı yeniden başlatın. Log dosyasında *"Yedekleme zamanlayıcısı başlatıldı: 0 23 * * *"* satırını arayın |
| Zamanlanmış yedek alınmış ama bildirim gelmemiş | Bildirim yalnızca `system_admin` rolüne gider | Yönetici hesabıyla **Bildirimler** ekranına bakın |
| Yedek dosyası çok büyük | `include_uploads` açık ve çok belge var | Belge klasörünü ayrı bir arşiv stratejisiyle yönetin; günlük yedeklerde belgeleri kapatıp haftada bir belgeli yedek alın |
| PostgreSQL'de yedek alınamıyor | Bu sürümde desteklenmiyor | `pg_dump` kullanın (§10) |

### 11.1 Log dosyasından takip

Yedekleme olayları `logs/` klasöründeki uygulama günlüğüne yazılır:

```
Yedek oluşturuldu: bkp_20260818_230000_scheduled (24.63 MB, durum: verified)
Saklama politikası: 3 yedek silindi (71.20 MB)
Yedekleme zamanlayıcısı başlatıldı: 0 23 * * *
```

Hata durumunda tam yığın izi (traceback) de aynı dosyaya yazılır; arayüzde yalnızca
kısa mesaj gösterilir.

### 11.2 Denetim kaydı

Her yedekleme ve geri yükleme işlemi denetim kaydına (`audit log`) yazılır:
`create`, `restore_started`, `restore_finished`, `protect`, `unprotect`, `delete`,
`cleanup`. Kim, ne zaman, hangi IP adresinden yaptı sorusunun cevabı buradadır.

---

## İlgili belgeler

* `CHANGELOG.md` — sürüm notları ve bilinen kısıtlamalar
* `docs/STATISTICS_GUIDE_TR.md` — istatistik ve rapor kılavuzu
* `docs/AI_GUIDE_TR.md` — yapay zekâ kullanım kılavuzu
* `.env.example` — tüm yapılandırma anahtarları
