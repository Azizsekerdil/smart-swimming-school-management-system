# İstatistik ve Rapor Kılavuzu

Bu belge, İstatistik Merkezi'ndeki her sayının **nasıl hesaplandığını** ve nasıl doğru
yorumlanacağını açıklar. Amacı, ekrandaki bir yüzdeye bakıp "bu tam olarak neyi
ölçüyor?" sorusuna kesin cevap verebilmenizdir.

> Sürüm: 0.9.0 · Kaynak: `backend/app/services/statistics_engine.py`,
> `backend/app/services/reporting.py`, `backend/app/api/v1/statistics.py`
> Arayüz: **İstatistikler** ve **Raporlar** ekranları

---

## 1. İstatistik Merkezi Genel Bakış

İstatistik Merkezi'ndeki **her sayı, veritabanındaki kayıtlardan doğrudan
hesaplanır.** Yapay zekâ tahmini, model çıktısı veya "yaklaşık değer" yoktur.

```
Veritabanı  →  Statistics Engine  →  Ekrandaki sayı
   (SQL)         (saf fonksiyonlar)      (grafik / tablo)
```

Motorun tasarımı üç kurala dayanır:

1. **Saf fonksiyonlar.** `mean`, `median`, `std_dev`, `percentile`, `moving_average`,
   `linear_slope`, `pearson_correlation`, `detect_outliers` gibi her yardımcı ayrı
   ve test edilebilir bir fonksiyondur. 395 backend test fonksiyonunun bir bölümü doğrudan bu
   fonksiyonları doğrular.
2. **AI ayrı katman.** `statistics_engine.py` içinde hiçbir AI çağrısı yoktur. AI
   katmanı (`services/ai/analysis.py`) bu motorun **çıktısını girdi olarak** kullanır;
   sayıları üretmez, yalnızca yorumlar. Ayrıntı için `docs/AI_GUIDE_TR.md`.
3. **Tekrarlanabilirlik.** Aynı dönem ve aynı veriyle çalıştırıldığında motor her
   zaman aynı sonucu döndürür.

### 1.1 Ekran sekmeleri

| Sekme | İçerik | Uç nokta |
|---|---|---|
| Öğrenciler | Kayıt, tutundurma, churn, dağılımlar | `GET /api/v1/statistics/students` |
| Eğitmenler | Ders yükü, saat, doluluk, iptal | `GET /api/v1/statistics/instructors` |
| Havuz | Doluluk, saat/gün yükü, yoğunluk haritası | `GET /api/v1/statistics/pools` |
| Yoklama | Devam, devamsızlık, geç, mazeret oranları | `GET /api/v1/statistics/attendance` |
| KPI | 11 gösterge, hedef ve gerçekleşme | `GET /api/v1/statistics/kpi` |
| Gelişmiş | Cohort, korelasyon, dağılım, aykırı değer | `/cohort`, `/correlation/...`, `/distribution/{metric}`, `/outliers/attendance` |

Tüm istatistik uçları `statistics:read` izni gerektirir. KPI hedefi belirlemek için
ayrıca `kpi:write` gerekir.

### 1.2 Ana kontrol paneli

`GET /api/v1/statistics/dashboard` günlük operasyon sayaçlarını tek seferde üretir:
aktif öğrenci, bugünkü ders, tamamlanan ders, kullanımdaki kulvar, bugün tahsil
edilen, bugün vadesi gelen, geciken tutar, aylık gelir/gider, bugünkü devam oranı,
yoklaması alınmamış ders sayısı, bitmek üzere olan üyelik, yaklaşan deneme dersi,
performansı düşen sporcu sayısı, yaklaşan yarışma. Ayrıca 30 günlük gelir trendi ve
devam trendi döner.

Panel ayrıca **uyarı kartları** üretir: geciken ödeme, bitmek üzere olan üyelik,
yoklaması alınmamış ders, performans düşüşü, yaklaşan yarışma.

---

## 2. Dönem Seçimi ve Karşılaştırma

Her istatistik ekranının üstünde bir dönem seçici vardır. Seçim, `resolve_period()`
fonksiyonuyla somut bir `(başlangıç, bitiş)` tarih çiftine çevrilir.

### 2.1 Sekiz dönem seçeneği

| Anahtar | Etiket | Kapsadığı aralık |
|---|---|---|
| `today` | Bugün | Bugün → bugün |
| `week` | Bu hafta | Haftanın Pazartesi'si → Pazar'ı (tam 7 gün, geleceği de kapsar) |
| `month` | Bu ay | Ayın 1'i → **bugün** (ayın kalanı dahil değil) |
| `quarter` | Bu çeyrek | Çeyreğin ilk ayının 1'i → **bugün** |
| `half_year` | Son 6 ay | Bugünden 182 gün öncesi → bugün |
| `year` | Bu yıl | 1 Ocak → **bugün** |
| `last_year` | Geçen yıl | Geçen yılın 1 Ocak'ı → 31 Aralık'ı (tam yıl) |
| `custom` | Özel | Sizin girdiğiniz `date_from` → `date_to` |

> **Dikkat:** `month`, `quarter` ve `year` seçenekleri **bugüne kadar** olan kısmı
> ölçer, ayın/çeyreğin/yılın tamamını değil. Ayın 3'ünde "Bu ay" seçerseniz yalnızca
> 3 günlük veri görürsünüz. Tam ay karşılaştırması için `custom` kullanın.

### 2.2 Önceki dönemle karşılaştırma

`previous_period(start, end)` fonksiyonu, seçili dönemle **aynı uzunlukta, hemen
öncesinde biten** bir dönem üretir:

```
span     = (end - start).days + 1
prev_end = start - 1 gün
prev_start = prev_end - (span - 1) gün
```

Örnek: 1–18 Ağustos (18 gün) seçiliyse önceki dönem 14–31 Temmuz (18 gün) olur.
Bu, "geçen ay" değil "aynı uzunlukta önceki aralık"tır — dönem uzunlukları eşit
olduğu için oranlar adil karşılaştırılır.

### 2.3 Değişim yüzdesi

```
değişim_yüzdesi = (mevcut - önceki) / |önceki| × 100
```

Önceki dönem **0** ise veya veri yoksa değişim yüzdesi hesaplanmaz ve **boş (null)**
döner — sıfıra bölme yapılmaz, "%∞ artış" gibi yanıltıcı bir değer üretilmez.

Her karşılaştırma metriğinde bir `direction` alanı vardır:

* `up_good` — artış iyidir (yeni kayıt, gelir, devam oranı)
* `down_good` — azalış iyidir (kayıp öğrenci, bekleyen tahsilat)

Arayüzdeki yeşil/kırmızı renk bu alana göre seçilir; **her artış yeşil değildir.**

---

## 3. Öğrenci İstatistikleri

`GET /api/v1/statistics/students?period=month&group_id=3`

Öğrenci istatistikleri, seçili grup (veya tüm okul) için hesaplanır.

### 3.1 Sayaçlar

| Metrik | Tanım ve hesaplama |
|---|---|
| **Toplam öğrenci** | Kapsamdaki tüm öğrenci kayıtları (durumdan bağımsız, ayrılanlar dahil) |
| **Aktif öğrenci** | `status = active` olan kayıt sayısı |
| **Pasif öğrenci** | `status = passive` |
| **Deneme öğrencisi** | `status = trial` |
| **Yeni kayıt** | `registration_date` seçili dönem aralığında olan öğrenci sayısı |
| **Kayıp öğrenci** | `left_date` dolu **ve** seçili dönem aralığında olan öğrenci sayısı |

### 3.2 Tutundurma oranı (retention)

Önce dönem başındaki mevcut öğrenci kütlesi bulunur:

```
dönem_başı_aktif = kayıt_tarihi < başlangıç
                   VE (ayrılış_tarihi yok VEYA ayrılış_tarihi >= başlangıç)
```

Sonra:

```
tutundurma_oranı = (dönem_başı_aktif − kayıp) / dönem_başı_aktif × 100
```

**Payda dönem başındaki öğrencilerdir; dönem içinde kaydolanlar paydaya girmez.**
Bu bilinçli bir tercihtir: yeni kaydolan bir öğrencinin aynı ay ayrılması,
tutundurma oranını mekanik olarak bozmasın diye.

`dönem_başı_aktif = 0` ise (yeni açılmış okul, çok kısa dönem) tutundurma **%100.0**
kabul edilir. Bu, "mükemmel performans" değil, **ölçülecek kütle yok** demektir.

### 3.3 Kayıp oranı (churn)

```
churn = 100 − tutundurma_oranı
```

Tutundurmanın tam tümleyenidir; ayrı bir veri kaynağı yoktur.

### 3.4 Büyüme oranı (growth)

```
büyüme_oranı = (yeni_kayıt − kayıp) / dönem_başı_aktif × 100
```

Net değişimin, dönem başı kütleye oranıdır. Negatif değer küçülme demektir.
`dönem_başı_aktif = 0` ise büyüme **0.0** döner.

### 3.5 Ortalama üyelik süresi

```
her öğrenci için: süre = (ayrılış_tarihi ?? bugün) − kayıt_tarihi   [gün]
ortalama_üyelik_günü = mean(tüm süreler)
```

Üç önemli nokta:

* Ayrılmamış öğrenciler için **bugüne kadar geçen süre** kullanılır; yani hâlâ
  devam eden üyelikler ortalamayı her gün biraz yükseltir.
* Hesap **seçili dönemle sınırlı değildir** — kapsamdaki tüm öğrencilerin tüm
  geçmişini kapsar. Dönem filtresi bu metriği değiştirmez.
* Ayrılanlar da dahildir; bu yüzden metrik "ortalama müşteri ömrü"ne yaklaşır.

### 3.6 Devam oranı (öğrenci sekmesindeki)

```
devam_oranı = (present + late + makeup) / tüm_yoklama_kaydı × 100
```

`PRESENT_STATUSES` = `present`, `late`, `makeup`. Yani **geç gelen öğrenci gelmiş
sayılır**, telafi dersine katılan da gelmiş sayılır.

Payda, dönemdeki ders başlangıç zamanına göre filtrelenmiş **tüm yoklama satırı**
sayısıdır. Bu, öğrenci sayısı değil kayıt sayısıdır: haftada 3 derse giden bir
öğrenci paydaya 3 kez katkı verir.

> Bu metrik grup filtresinden **etkilenmez**; öğrenci sekmesindeki devam oranı her
> zaman okul geneli için hesaplanır. Grup bazlı devam için **Yoklama** sekmesini
> kullanın.

### 3.7 Dağılımlar

| Dağılım | Kırılım |
|---|---|
| Yaş | `0-5`, `6-9`, `10-13`, `14-17`, `18-29`, `30-49`, `50+` (doğum tarihi yoksa hariç) |
| Seviye | `swim_level` alanına göre |
| Grup | Gruba bağlı öğrenci sayısı (boş gruplar listelenmez) |
| Cinsiyet | `gender` alanına göre |

Her dağılım satırı `value` (adet) ve `percent` (toplam içindeki payı) taşır ve
adetten büyükten küçüğe sıralanır.

### 3.8 Kayıt trendi

Dönemin ilk ayından başlayarak her ay için o ay kaydolan öğrenci sayısı üretilir
(`2026-06`, `2026-07`, `2026-08` gibi). Kısa dönemlerde tek nokta çıkabilir; trend
okumak için en az `quarter` seçin.

---

## 4. Eğitmen İstatistikleri

`GET /api/v1/statistics/instructors?period=month`

Yalnızca `is_active = true` eğitmenler listelenir. Satırlar **toplam saate göre**
büyükten küçüğe sıralanır.

| Metrik | Hesaplama |
|---|---|
| **Öğrenci sayısı** | `primary_instructor_id` bu eğitmen olan öğrenci sayısı. **Dönemden bağımsızdır** — güncel atamayı gösterir |
| **Ders sayısı** | Dönemde başlayan ve `status ≠ cancelled` olan ders sayısı |
| **Toplam saat** | İptal edilmemiş derslerin `duration_minutes` toplamı ÷ 60 |
| **Doluluk oranı** | `Σ kayıtlı_öğrenci / Σ kapasite × 100` (yalnızca iptal edilmemiş dersler) |
| **Devam oranı** | Bu eğitmenin derslerindeki `(present+late+makeup) / tüm_yoklama × 100` |
| **İptal oranı** | `iptal_edilen_ders / dönemdeki_tüm_ders × 100` (payda iptaller **dahil**) |
| **Özel ders sayısı** | `lesson_type = private` olan iptal edilmemiş dersler |
| **Grup dersi sayısı** | İptal edilmemiş dersler − özel dersler |
| **Özel ders oranı** | `özel / iptal_edilmemiş_ders × 100` |

Özet satırları: toplam saat, eğitmen başına ortalama öğrenci, ortalama doluluk.

### 4.1 KARAR DESTEĞİ UYARISI

**Bu tablo bir performans değerlendirme aracı değildir.** İş yükü ve operasyon
göstergeleri üretir. Personel kararı verirken şunları hesaba katın:

* **Doluluk oranı eğitmenin kontrolünde değildir.** Kapasiteyi ve kayıtları program
  yapan kişi belirler. Düşük doluluk çoğu zaman ders saatinin kötü seçilmiş
  olmasından kaynaklanır.
* **Devam oranını öğrenciler belirler.** Bebek ve çocuk gruplarında hastalık kaynaklı
  devamsızlık, yetişkin gruplarına göre yapısal olarak yüksektir. Farklı yaş
  gruplarıyla çalışan eğitmenleri bu metrikle karşılaştırmak yanıltıcıdır.
* **İptal oranının paydasında iptaller de vardır.** Ayda 4 ders veren ve 1'i iptal
  olan eğitmen %25, ayda 40 ders veren ve 4'ü iptal olan da %25 görünür — ama ikisi
  aynı şey değildir. Yanına **ders sayısı** sütununa mutlaka bakın.
* **İptal nedeni bu tabloda yoktur.** Havuz bakımı, tatil, su kalitesi kaynaklı iptal
  ile eğitmenin gelmemesi aynı sayıya karışır. Nedeni **Dersler** ekranından okuyun.
* **Küçük örneklem yanılgısı.** Dönemde 3 ders veren bir eğitmenin oranları
  istatistiksel olarak anlamsızdır. En az 15-20 ders olmadan oran karşılaştırması
  yapmayın.
* **Öğrenci sayısı dönemsel değildir.** Bu ay hiç ders vermemiş bir eğitmenin
  "öğrenci sayısı" yine de dolu görünür.

Doğru kullanım: iş yükü dengesizliğini fark etmek, program planlarken kimin boş
olduğunu görmek, sezon planı yaparken kapasite hesaplamak.

---

## 5. Havuz ve Kulvar İstatistikleri

`GET /api/v1/statistics/pools?period=month&pool_id=1`

### 5.1 Doluluk hesabı

Doluluk, **dakika bazlı** hesaplanır:

```
KULLANILAN DAKİKA
  = Σ (kulvara atanmış, iptal edilmemiş derslerin süresi)

KAPASİTE DAKİKASI
  = Σ_havuz [ (kapanış_saati − açılış_saati) dakika
              × aktif_kulvar_sayısı
              × dönemdeki_gün_sayısı ]

genel_doluluk = kullanılan / kapasite × 100
boş_kapasite_saati = max(0, kapasite − kullanılan) / 60
```

Bu formülün üç sonucu vardır ve üçü de bilinerek okunmalıdır:

1. **Kulvara atanmamış dersler paya girmez.** `lane_id` boş olan bir ders havuz
   kullanım dağılımında görünür ama doluluk oranının payına eklenmez. Doluluk
   beklenenden düşük çıkıyorsa önce kulvar atamalarını kontrol edin.
2. **Payda tüm günleri sayar.** Havuzun kapalı olduğu Pazar günleri, resmî tatiller
   ve bakım günleri de kapasiteye dahildir. Bu yüzden **%100 doluluk pratikte
   imkânsızdır.**
3. **Aktif kulvarı olmayan havuz 1 kulvar sayılır** (sıfıra bölmeyi önlemek için).

Pratik referans: haftada 6 gün, günde 8 saat çalışan bir havuzda gerçek üst sınır
%70-75 civarıdır. **%45-55 sağlıklı, %65 üstü çok yoğun, %25 altı ciddi boş kapasite**
olarak okunabilir. Kendi tesisiniz için bu bandı ilk sezon ölçüp not edin.

### 5.2 Yük dağılımları

| Grafik | İçerik |
|---|---|
| **Havuz kullanımı** | Havuz başına toplam ders dakikası ve yüzde payı |
| **Kulvar kullanımı** | `Havuz adı - Kulvar adı` başına toplam dakika |
| **Saatlik yük** | 06:00–23:00 arası her saat için toplam ders dakikası |
| **Günlük yük** | Haftanın 7 günü için toplam ders dakikası |
| **Haftalık yük** | ISO hafta numarasına göre (`2026-W33`) toplam dakika |

Türetilen değerler: **en yoğun saat** (saatlik yükün maksimumu), **en boş saat**
(minimumu — ders yapılan saatler arasından, hiç ders olmayan saat bu listeye
girmez), **en çok kullanılan kulvar**, **ders başına ortalama kulvar** (kulvara
atanmış ders sayısı ÷ toplam ders sayısı).

### 5.3 Yoğunluk haritası nasıl okunur

Yoğunluk haritası `(gün, saat)` hücrelerinden oluşur. Her hücrede iki bilgi vardır:

* `value` — o hücredeki toplam ders **dakikası**
* `lesson_count` — o hücredeki **ders sayısı**

Doğru okuma sırası:

1. **Koyu bantları bulun.** Bunlar tesisin gerçek talep zirveleridir — genellikle
   hafta içi 17:00-20:00 ve Cumartesi sabahı.
2. **Açık hücreleri işaretleyin.** Havuzun açık olduğu ama ders olmayan saatler
   satılabilir boş kapasitedir. Hafta içi 10:00-15:00 bandı tipik olarak boştur;
   emekli, ev hanımı veya kurumsal grup programı için hedeflenebilir.
3. **`value` ve `lesson_count` arasındaki farka bakın.** Yüksek dakika + düşük ders
   sayısı = uzun süreli az sayıda ders (antrenman grubu). Düşük dakika + yüksek ders
   sayısı = kısa özel dersler.
4. **Boş hücre ile kapalı saati karıştırmayın.** Harita yalnızca ders olan hücreleri
   üretir; havuzun kapalı olduğu saat de boş hücre olarak görünür. Havuzun çalışma
   saatlerini **Havuzlar** ekranından teyit edin.

---

## 6. Yoklama İstatistikleri

`GET /api/v1/statistics/attendance?period=month&group_id=3`

Yoklama satırları, bağlı oldukları dersin başlangıç zamanına göre döneme girer.
Grup ve eğitmen filtresi uygulanabilir.

### 6.1 Oran tanımları

Bütün oranların paydası, **dönemdeki toplam yoklama kaydı sayısıdır**.

| Oran | Formül | Not |
|---|---|---|
| **Genel devam oranı** | `(present + late + makeup) / toplam × 100` | Geç gelen ve telafiye katılan **gelmiş** sayılır |
| **Devamsızlık (no-show) oranı** | `absent / toplam × 100` | Yalnızca `absent`; mazeretli devamsızlık buraya girmez |
| **Geç kalma oranı** | `late / toplam × 100` | Bu kayıtlar aynı zamanda devam oranının payında da vardır |
| **Mazeret oranı** | `excused / toplam × 100` | Devam oranının payında **yoktur**; yani mazeretli devamsızlık devam oranını düşürür |
| **Telafi oranı** | `makeup / toplam × 100` | Devam oranının payındadır |

Ham sayaçlar da ayrıca döner: `present`, `absent`, `late`, `excused`, `cancelled`,
`makeup`.

> `genel_devam + devamsızlık + mazeret` toplamı %100 etmeyebilir — `cancelled`
> durumundaki kayıtlar paydada olup hiçbir orana girmez.

### 6.2 Kırılımlar

* **Gruba göre** ve **eğitmene göre** devam oranı: her etiket için
  `gelen / toplam × 100`, orandan büyükten küçüğe sıralı.
* **En düşük devamlı öğrenciler:** Dönemde **en az 3 yoklama kaydı** olan ve devam
  oranı **%75'in altında** kalan öğrenciler; orandan küçükten büyüğe sıralı, ilk 20
  kayıt. 3 kayıt eşiği, tek bir devamsızlıkla listeye düşmeyi engellemek içindir.
* **Trend:** Her gün için o günün devam oranı (`%d.%m` etiketiyle).

---

## 7. Performans Analizi

`analyze_event()` fonksiyonu, bir sporcunun **tek bir etkinliğindeki**
(stil + mesafe + kulvar tipi) tüm derecelerini kronolojik sırada analiz eder.

`GET /api/v1/performance/students/{id}/summary` bu analizi her etkinlik için ayrı
ayrı üretir.

### 7.1 Hesaplanan istatistikler

| İstatistik | Yöntem | Not |
|---|---|---|
| **En iyi derece** | `min(dereceler)` | Yüzmede en küçük süre en iyidir |
| **En kötü derece** | `max(dereceler)` | |
| **Ortalama** | `numpy.mean`, 3 ondalık | Aykırı bir yavaş derece ortalamayı yukarı çeker |
| **Medyan** | `numpy.median` | Aykırı değerlere dayanıklı; ortalamadan çok farklıysa dağılım çarpıktır |
| **Standart sapma** | `numpy.std(ddof=1)` — örneklem sapması | **En az 2 kayıt** gerekir, yoksa boş döner. Düşük değer = tutarlı sporcu |
| **25. persentil** | `numpy.percentile(25)` | Derecelerin en hızlı %25'inin sınırı |
| **75. persentil** | `numpy.percentile(75)` | En yavaş %25'in sınırı |
| **Hareketli ortalama** | 3 noktalık pencere, `min_periods=1` | İlk noktalarda pencere genişleyerek çalışır; grafikte gürültüyü siler |
| **Eğim (slope)** | `numpy.polyfit(x, y, 1)` en küçük kareler | Birimi **saniye / gün**. `x` = ilk kayıttan geçen gün sayısı |

Eğim için en az 2 kayıt ve en az 2 farklı tarih gerekir; aynı gün alınmış kayıtlar
tek nokta sayılır ve eğim boş döner.

### 7.2 Eğilim yönü nasıl belirlenir

```python
def trend_direction(slope, lower_is_better=False):
    if slope is None or abs(slope) < 1e-6:
        return "stable"
    improving = slope < 0 if lower_is_better else slope > 0
    return "improving" if improving else "declining"
```

**Yüzme derecelerinde `lower_is_better=True` kullanılır.** Yani:

| Eğim | Anlamı | Etiket |
|---|---|---|
| Negatif (süre düşüyor) | Sporcu **hızlanıyor** | `improving` (gelişiyor) |
| Pozitif (süre artıyor) | Sporcu **yavaşlıyor** | `declining` (geriliyor) |
| \|eğim\| < 0.000001 | Anlamlı değişim yok | `stable` (sabit) |

Devam oranı, gelir, kayıt sayısı gibi metriklerde `lower_is_better=False` kullanılır
ve işaret tersine döner: artış `improving` olur.

### 7.3 Gelişim yüzdesi formülü

```
gelişim_saniye  = ilk_derece − son_derece          (pozitif = hızlandı)
gelişim_yüzdesi = gelişim_saniye / ilk_derece × 100
```

Örnek: ilk kayıt 35.20 sn, son kayıt 33.10 sn →
`gelişim = 2.10 sn`, `gelişim_yüzdesi = 2.10 / 35.20 × 100 = %5.97`.

> Bu formül **yalnızca ilk ve son kaydı** kullanır; aradaki dalgalanmayı görmez.
> İlk kayıt kötü bir günse gelişim abartılı çıkar. Gerçek eğilim için **eğim** ve
> **hareketli ortalama** grafiğine birlikte bakın.

### 7.4 Kısa ve orta vadeli değişim

```
change_30d = mean(son 30 gün) − mean(90 günden eski kayıtlar)
change_90d = mean(son 90 gün) − mean(90 günden eski kayıtlar)
```

Her iki taraf da doluysa hesaplanır, aksi hâlde boş döner. **Negatif değer iyidir**
(yeni dönem daha hızlı). `change_30d` forma göstergesi, `change_90d` sezon
göstergesidir.

### 7.5 En çok gelişenler ve gerileyenler

**En çok gelişenler** (`find_top_improvers`, varsayılan 90 gün, en az 3 kayıt):
`(öğrenci, stil, mesafe)` üçlüsü bazında gruplanır; `ilk − son > 0` olanlar gelişim
yüzdesine göre sıralanır.

**Gerileyen sporcular** (`find_declining_athletes`, varsayılan 90 gün, en az 4 kayıt):

```
bölme_noktası = max(1, kayıt_sayısı × 2 // 3)
baz_ortalama  = mean(ilk 2/3 kayıt)
son_ortalama  = mean(son 1/3 kayıt)
gerileme      = son_ortalama − baz_ortalama        (pozitif = yavaşladı)
gerileme_yüzdesi = gerileme / baz_ortalama × 100
```

Yalnızca `gerileme > 0` **ve** `gerileme_yüzdesi ≥ %1.0` olanlar listelenir. %1
eşiği, normal günlük dalgalanmayı (gürültüyü) elemek içindir.

---

## 8. Yarışma Hazırlık Skoru

`competition_readiness()` — son **60 gün**, etkinlik başına **en az 3 kayıt**.

### 8.1 Bileşenler ve ağırlıklar

```
hazırlık_skoru = tutarlılık × 0.25
               + forma      × 0.35
               + eğilim     × 0.25
               + hacim      × 0.15
```

| Bileşen | Ağırlık | Formül | Neyi ölçer |
|---|---|---|---|
| **Tutarlılık** | **%25** | `max(0, 100 − (σ / son_ortalama × 100) × 10)` | Derecelerin oturmuşluğu. σ = standart sapma. Değişkenlik %1 arttığında skor 10 puan düşer — bilinçli olarak sert bir ceza |
| **Forma** | **%35** | `max(0, 100 − (son_ortalama − en_iyi) / en_iyi × 100 × 5)` | Sporcunun **kendi en iyisine** yakınlığı. Son 3 derecenin ortalaması kişisel rekorun %1 üstündeyse 5 puan kaybeder |
| **Eğilim** | **%25** | `clamp(50 − eğim × 500, 0, 100)` | Gelişme yönü. Negatif eğim (hızlanma) skoru 50'nin üstüne çıkarır; pozitif eğim aşağı çeker |
| **Hacim** | **%15** | `min(100, kayıt_sayısı / 12 × 100)` | Antrenman yoğunluğu. 12 kayıtta doygunluğa ulaşır |

Varsayılan değerler: standart sapma hesaplanamıyorsa tutarlılık **100**, en iyi
derece yoksa forma **50**, eğim hesaplanamıyorsa eğilim **50**.

Sonuç, skorlara göre büyükten küçüğe sıralanır. Her satır ayrıca `readiness_basis`
alanını taşır:

> `tutarlılık %25 + forma yakınlık %35 + gelişim eğilimi %25 + antrenman hacmi %15
> (istatistiksel, AI değil)`

### 8.2 Bu skor İSTATİSTİKSELDİR, AI TAHMİNİ DEĞİLDİR

Bu vurgu kaynak kodda da açıkça yazılıdır. Skor:

* Yalnızca **kendi geçmiş derecelerinizden** üretilir. Dört formül, dört sabit
  ağırlık. Aynı veriyle her zaman aynı sonucu verir.
* **Bir dil modeli çağırmaz.** AI sağlayıcıları kapalıyken de tam olarak çalışır.
* **Yarışma sonucunu tahmin etmez.** Rakip dereceleri, havuz tipi farkı, ısınma
  kalitesi, uyku, stres, hastalık, yaş grubu — hiçbiri modelde yoktur.
* **Mutlak değil, göreli bir araçtır.** "80 puan iyi mi?" sorusunun evrensel cevabı
  yoktur. Doğru kullanım: aynı etkinlikteki sporcuları birbirine göre sıralamak ve
  aynı sporcunun skorunu haftalar içinde izlemek.

Yorumlama örneği: yüksek forma + düşük tutarlılık = hızlı ama oturmamış; teknik
istikrar çalışması gerekir. Yüksek tutarlılık + düşük forma = düzenli ama kişisel
rekorunun uzağında; tapering/hız çalışması gerekir. Düşük hacim = skor zaten
güvenilir değildir, önce yeterli kayıt toplayın.

---

## 9. Gelişmiş Analizler

**İstatistikler → Gelişmiş** sekmesi.

### 9.1 Cohort tutundurma analizi

`GET /api/v1/statistics/cohort?months=12`

Öğrenciler **kayıt ayına** göre gruplanır (cohort). Her cohort için, kayıttan sonraki
her ay hâlâ aktif olan üye yüzdesi hesaplanır:

```
ay_N_tutundurma = (ayrılmamış veya N. ayda hâlâ kayıtlı üye) / cohort_büyüklüğü × 100
```

Çıktı bir üçgen tablodur: satırlar cohort ayı (`2026-01`, `2026-02`, ...), sütunlar
kayıttan sonraki ay numarası. Ay 0 daima %100'dür.

Neye bakılır: **düşüşün en sert olduğu ay hangisi?** Genellikle 2. ve 3. ay kritik
eşiktir. Ayrıca kampanyalı aylarda kaydolan cohortların, normal aylara göre daha
hızlı erimesi tipik bir bulgudur.

Uyarı: 5-10 kişilik cohortlarda tek bir ayrılış %10-20'lik düşüş gösterir. Cohort
büyüklüğü sütununu her zaman yanında okuyun.

### 9.2 Korelasyon — NEDENSELLİK UYARISI

`GET /api/v1/statistics/correlation/attendance-performance?days=180`

Öğrenci bazında **devam oranı** ile **performans gelişim yüzdesi** arasındaki Pearson
korelasyon katsayısı hesaplanır. Bir öğrencinin analize girmesi için o dönemde
**en az 5 yoklama kaydı ve en az 3 performans kaydı** olması gerekir.

Katsayı yorumlama tablosu:

| \|r\| | Etiket |
|---|---|
| ≥ 0.80 | `very_strong` (çok güçlü) |
| ≥ 0.60 | `strong` (güçlü) |
| ≥ 0.40 | `moderate` (orta) |
| ≥ 0.20 | `weak` (zayıf) |
| < 0.20 | `negligible` (ihmal edilebilir) |

En az 3 veri çifti ve her iki değişkende de değişkenlik gerekir; aksi hâlde sonuç
**boş** döner (uydurma değer üretilmez).

> ### KORELASYON NEDENSELLİK DEĞİLDİR
>
> Bu uyarı kaynak kodda hem fonksiyon açıklamasında hem de uç nokta açıklamasında
> yazılıdır. `r = 0.7` görmek "devama gelmek performansı artırır" demek **değildir**.
> En az üç alternatif açıklama her zaman masadadır:
>
> 1. **Ters yön:** Gelişen sporcu motive olur ve daha düzenli gelir. Neden ile sonuç
>    yer değiştirmiş olabilir.
> 2. **Üçüncü değişken:** Aile desteği, sağlık, ekonomik durum, ulaşım kolaylığı —
>    hem devamı hem gelişimi aynı anda etkiler. İkisi arasında doğrudan bağ olmayabilir.
> 3. **Seçilim yanlılığı:** Analize yalnızca ≥5 yoklama ve ≥3 performans kaydı olan
>    öğrenciler girer. Bir ay sonra bırakanlar zaten örneklemin dışındadır; bu tek
>    başına korelasyonu yukarı çeker.
>
> Nedensellik iddiası için kontrollü karşılaştırma gerekir: benzer yaş, seviye ve
> başlangıç derecesine sahip iki grubu farklı devam düzeninde izlemek gibi.

### 9.3 Dağılım analizi

`GET /api/v1/statistics/distribution/{metric}?days=180`

Desteklenen metrikler: `student_age`, `attendance_rate`, `lesson_occupancy`.

Çıktı: `count`, `mean`, `median`, `std_dev`, `min_value`, `max_value`,
`percentile_25`, `percentile_75`, `percentile_90` ve **10 kutulu histogram**
(`numpy.histogram`, her kutuda adet ve yüzde).

Okuma ipucu: **ortalama ile medyan arasındaki fark dağılımın çarpıklığını gösterir.**
Ortalama medyandan belirgin yüksekse birkaç büyük değer dağılımı sağa çekiyor
demektir; bu durumda "ortalama" tipik öğrenciyi temsil etmez, medyanı kullanın.

`attendance_rate` metriğinde en az 3 yoklama kaydı, `lesson_occupancy` metriğinde
kapasitesi tanımlı ders gerekir.

### 9.4 Aykırı değer tespiti

`GET /api/v1/statistics/outliers/attendance?period=month`

Devam oranında istatistiksel olarak sıra dışı öğrencileri bulur:

```
z = (öğrencinin_oranı − ortalama) / standart_sapma
|z| ≥ 2.0  →  aykırı
```

Koşullar: öğrencinin dönemde **en az 4 yoklama kaydı** olmalı; analize giren öğrenci
sayısı **en az 4** olmalı; standart sapma sıfır olmamalı (herkes aynı orandaysa
aykırı yoktur).

Her satır `direction` alanı taşır: `below` (ortalamanın altında — ilgilenilmesi
gereken öğrenci) veya `above` (ortalamanın üstünde — örnek öğrenci).

> z-skoru **ortalamaya göre** sıra dışılığı ölçer, "kötü" demez. Devam oranı genel
> olarak yüksek bir okulda %85 devamlı bir öğrenci bile `below` aykırı çıkabilir.

---

## 10. KPI Sistemi

`GET /api/v1/statistics/kpi?period=month` — 11 gösterge tek çağrıda hesaplanır.

### 10.1 11 KPI'nın tanımı

| Anahtar | Etiket | Birim | Yön | Hesaplama |
|---|---|---|---|---|
| `active_students` | Aktif Öğrenci | adet | artış iyi | `status = active` öğrenci sayısı |
| `new_students_monthly` | Aylık Yeni Öğrenci | adet | artış iyi | Dönemde kaydolan öğrenci sayısı (önceki dönemle karşılaştırılır) |
| `student_retention` | Öğrenci Tutundurma | % | artış iyi | §3.2'deki tutundurma oranı |
| `attendance_rate` | Devam Oranı | % | artış iyi | §6.1'deki genel devam oranı |
| `pool_occupancy` | Havuz Doluluk | % | artış iyi | §5.1'deki genel doluluk |
| `lane_occupancy` | Kulvar Doluluk | % | artış iyi | Aynı hesap — bu sürümde `pool_occupancy` ile **aynı değeri** döndürür |
| `monthly_revenue` | Aylık Gelir | para | artış iyi | `Σ (ödeme − iade)`, iptal edilmiş ödemeler hariç (önceki dönemle karşılaştırılır) |
| `revenue_per_student` | Öğrenci Başına Gelir | para | artış iyi | `dönem_geliri / aktif_öğrenci` (aktif öğrenci 0 ise 0) |
| `outstanding_payments` | Bekleyen Tahsilat | para | **azalış iyi** | `Σ (fatura_tutarı − ödenen)`, tüm zamanlar — dönemden bağımsız |
| `collection_rate` | Tahsilat Oranı | % | artış iyi | `Σ ödenen / Σ faturalanan × 100` (dönemde kesilen faturalar; fatura yoksa %100) |
| `average_performance_improvement` | Ortalama Performans Gelişimi | % | artış iyi | Dönem + 30 gün geriye bakarak, en az 2 kaydı olan gelişen sporcuların gelişim yüzdelerinin ortalaması |

### 10.2 Hedef belirleme

**İstatistikler → KPI** sekmesinde bir göstergenin **Hedef Belirle** düğmesine basın.

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/statistics/kpi/targets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "kpi_key": "attendance_rate",
        "target_value": 85,
        "unit": "percent",
        "period": "monthly",
        "notes": "2026 sezon hedefi"
      }'
```

`kpi:write` izni gerekir. Hedefler `KpiTarget` tablosunda saklanır ve yalnızca
`is_active = true` olanlar hesaba katılır.

### 10.3 Gerçekleşme hesabı

Yön etiketine göre iki farklı formül kullanılır:

```
artış iyi   (up_good)  : gerçekleşme = değer / hedef × 100
azalış iyi (down_good): gerçekleşme = hedef / değer × 100
```

İkinci formül şunu sağlar: bekleyen tahsilat hedefi 10.000 iken gerçek 8.000 ise
`10000 / 8000 = %125` — hedefin altında kalmak **başarı** sayılır.

Durum rengi:

| Gerçekleşme | Durum | Renk |
|---|---|---|
| ≥ %100 | `good` | Yeşil |
| %85 – %99.9 | `warning` | Sarı |
| < %85 | `bad` | Kırmızı |
| Hedef tanımlı değil | `neutral` | Gri |

Hedef **0** veya tanımsızsa gerçekleşme hesaplanmaz; gösterge yalnızca değer olarak
görünür.

---

## 11. Raporlar

**Raporlar** ekranı. Uçlar: `GET /reports/definitions`, `POST /reports/preview`,
`POST /reports/export`, `GET/POST/DELETE /reports/templates`.

Her rapor ortak bir yapı üretir: **sütunlar + satırlar + toplamlar + özet**. Bu sayede
aynı rapor dört biçime de aynı içerikle aktarılır.

### 11.1 16 rapor türü

| # | Anahtar | Ad | Kategori | Filtreler | İçerik | İzin |
|---|---|---|---|---|---|---|
| 1 | `daily_manager` | Günlük Yönetici Raporu | Yönetim | tarih | Günün dersleri, yoklama ve tahsilat özeti | `report:read` |
| 2 | `weekly_management` | Haftalık Yönetim Raporu | Yönetim | dönem | Haftalık operasyon ve finans özeti | `report:read` |
| 3 | `monthly_management` | Aylık Yönetim Raporu | Yönetim | dönem | Aylık KPI, gelir ve öğrenci hareketleri | `report:read` |
| 4 | `student_list` | Öğrenci Listesi | Öğrenci | grup, durum, seviye | No, ad, yaş, seviye, durum, grup, eğitmen, kayıt tarihi, telefon | `student:read` |
| 5 | `student_progress` | Öğrenci Gelişim Raporu | Öğrenci | öğrenci, dönem | Tek öğrencinin performans ve devam gelişimi | `performance:read` |
| 6 | `attendance` | Yoklama Raporu | Operasyon | dönem, grup, eğitmen | Devam oranları ve devamsızlık analizi | `attendance:read` |
| 7 | `instructor_workload` | Eğitmen İş Yükü Raporu | Personel | dönem | Eğitmen başına ders, saat ve doluluk | `instructor:read` |
| 8 | `pool_usage` | Havuz Kullanım Raporu | Tesis | dönem, havuz | Havuz ve saat bazlı doluluk | `pool:read` |
| 9 | `lane_occupancy` | Kulvar Doluluk Raporu | Tesis | dönem, havuz | Kulvar bazlı kullanım dağılımı | `pool:read` |
| 10 | `finance` | Finans Raporu | Finans | dönem | Gelir, gider ve net kâr | `finance:read` |
| 11 | `collections` | Tahsilat Raporu | Finans | dönem | Tahsilatlar ve ödeme yöntemi dağılımı | `finance:read` |
| 12 | `outstanding` | Bekleyen Alacak Raporu | Finans | — | Geciken ve bekleyen ödemeler (yaşlandırma) | `finance:read` |
| 13 | `membership` | Üyelik Raporu | Satış | durum | Aktif, biten ve dondurulmuş üyelikler | `membership:read` |
| 14 | `sales` | Satış Raporu | Satış | dönem | Paket bazlı satış ve gelir | `finance:read` |
| 15 | `performance` | Performans Raporu | Spor | dönem, öğrenci | Sporcu dereceleri ve gelişim | `performance:read` |
| 16 | `competition` | Yarışma Raporu | Spor | dönem | Yarışma sonuçları ve madalyalar | `competition:read` |

Rapor kataloğu (`GET /reports/definitions`) **yalnızca sizin izinlerinizle
erişebileceğiniz raporları** döndürür.

### 11.2 Dışa aktarma biçimleri

| Biçim | Dosya | MIME | Özellikler |
|---|---|---|---|
| `pdf` | `<rapor>_YYYYAAGG_SSDD.pdf` | `application/pdf` | 5'ten fazla sütunda otomatik yatay A4. Türkçe karakter için sırasıyla DejaVu Sans → Arial → Calibri fontu kaydedilir. **En fazla 1500 satır basılır**, fazlası için not düşülür |
| `xlsx` | `.xlsx` | `...spreadsheetml.sheet` | Kurum adı + başlık + dönem + oluşturma zamanı başlıkta, mavi başlık satırı, kenarlıklar, otomatik sütun genişliği, **dondurulmuş başlık satırı**, altta toplamlar bloğu |
| `csv` | `.csv` | `text/csv; charset=utf-8` | **Noktalı virgül (`;`) ayraç** ve **UTF-8 BOM** — Excel'in Türkçe karakterleri doğru açması için |
| `json` | `.json` | `application/json` | Ham yapı: sütun tanımları, satırlar, toplamlar, özet. Başka bir sisteme aktarım için |

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reports/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -o rapor.xlsx \
  -d '{
        "report_key": "attendance",
        "format": "xlsx",
        "period": "month",
        "group_id": 3,
        "language": "tr"
      }'
```

Dışa aktarma `report:export` izni gerektirir; önizleme (`/reports/preview`) için
raporun kendi izni yeterlidir.

### 11.3 Şablonlar

Sık kullandığınız filtre setini **Şablon Kaydet** ile saklayabilirsiniz
(`ReportTemplate`). Sonraki sefer tek tıkla aynı raporu aynı filtrelerle üretirsiniz.

---

## 12. Metriklerin Doğru Yorumlanması

Bu bölüm, sistemde en sık yapılan yorum hatalarını ve bunlardan nasıl kaçınılacağını
listeler.

### 12.1 Küçük örneklem yanılgısı

Motorun kendi koyduğu eşikler zaten bir uyarı listesidir:

| Hesap | Minimum gereksinim | Altındaysa |
|---|---|---|
| Standart sapma | 2 kayıt | Boş döner |
| Eğim (trend) | 2 kayıt + 2 farklı tarih | Boş döner |
| Korelasyon | 3 veri çifti + iki değişkende de değişkenlik | Boş döner |
| Aykırı değer | 4 değer (öğrenci başına 4 yoklama, en az 4 öğrenci) | Boş liste |
| Gerileyen sporcu | 4 kayıt + ≥ %1 gerileme | Listelenmez |
| En çok gelişen | 3 kayıt | Listelenmez |
| Düşük devamlı öğrenci | 3 yoklama kaydı | Listelenmez |
| AI yorumu | 3 veri noktası (`MIN_DATA_POINTS`) | AI çağrılmaz |

**Kural:** Bir oran gördüğünüzde önce **paydayı** arayın. 2 dersten 1'ine gelen
öğrenci "%50 devam" gösterir; 40 dersten 20'sine gelen de. İkisi aynı bilgi değildir.
Tabloların "kayıt sayısı" / "ders sayısı" sütunları tam olarak bunun için vardır.

### 12.2 Mevsimsellik

Yüzme okulu mevsimsel bir iştir ve motor bunu **otomatik düzeltmez**.

* Haziran-Ağustos kayıt patlaması, Aralık-Şubat düşüşü normaldir.
* Ramazan, yarıyıl tatili, sınav dönemleri devam oranını yapısal olarak düşürür.
* **Doğru karşılaştırma: geçen yılın aynı dönemi.** `custom` dönem seçip geçen yılın
  aynı tarih aralığını girin. `previous_period` size bir önceki eş uzunlukta aralığı
  verir — Ağustos'u Temmuz'la karşılaştırır ve mevsimselliği gizler.
* `trend_analysis()` fonksiyonu basit bir mevsimsellik sezgisi üretir: bir ayın
  ortalaması genel ortalamanın **%125'ini** aşıyorsa o ay "zirve ay" olarak
  işaretlenir. Bu bir istatistiksel mevsimsellik ayrıştırması değil, kaba bir
  işarettir.

### 12.3 Korelasyon–nedensellik karışıklığı

En sık ve en pahalı hata budur. Kontrol listesi:

1. **Ters nedensellik olabilir mi?** (Gelişen sporcu daha çok mu geliyor, çok gelen
   mi gelişiyor?)
2. **Ortak bir üçüncü etken var mı?** (Aile ilgisi hem devamı hem gelişimi artırır.)
3. **Örneklem nasıl seçildi?** (Eşiği geçemeyen öğrenciler analize hiç girmedi.)
4. **Örneklem kaç kişi?** (`sample_size` alanı yanıtta vardır — mutlaka okuyun.)
5. **Katsayı ne kadar güçlü?** (`weak` ve `negligible` etiketli sonuçlar üzerine
   politika kurmayın.)

### 12.4 Diğer yaygın hatalar

| Hata | Doğrusu |
|---|---|
| "Havuz doluluğumuz %48, kötü" | Payda tüm çalışma saatlerini ve tüm günleri kapsar; %100 imkânsızdır. Kendi tesisinizin gerçekçi bandını ölçün |
| "Tutundurma %100, harika" | Dönem başında aktif öğrenci yoksa motor varsayılan olarak %100 döndürür. Payda sıfır olabilir |
| "Ortalama devam süremiz 240 gün" | Ayrılmamış öğrenciler için bugüne kadar geçen süre kullanılır; bu sayı her gün büyür ve dönem filtresinden etkilenmez |
| "Devam oranı düştü, eğitmen sorunlu" | Mazeretli devamsızlık (`excused`) da oranı düşürür. Hastalık sezonu ve tatil etkisini ayırın |
| "Eğitmen A'nın doluluğu düşük" | Doluluğu program belirler, eğitmen değil. Önce ders saatine bakın |
| "Bu ay geliri geçen aya göre düşük" | `month` dönemi **bugüne kadarını** ölçer. Ayın 10'unda bakıyorsanız 10 günü 30 günle karşılaştırıyorsunuz |
| "İptal oranı %25, çok yüksek" | Paydayı kontrol edin: 4 dersten 1'i mi, 40 dersten 10'u mu? |
| "Hazırlık skoru 92, yarışmayı kazanır" | Skor rakipleri, yarışma koşullarını ve günlük formu bilmez. Yalnızca kendi geçmişine göre hazırlığı ölçer |
| "Korelasyon 0.65, demek ki neden bu" | Korelasyon nedensellik değildir (§9.2) |
| "Aykırı değer çıktı, öğrenci sorunlu" | z-skoru ortalamadan sapmayı ölçer; yüksek devamlı bir okulda %85 bile aykırı olabilir |
| "AI paneli farklı sayı söylüyor" | AI yorumu metinsel bir çıkarımdır. **Karar dayanağı her zaman yeşil paneldeki hesaplanmış sayıdır** (bkz. `docs/AI_GUIDE_TR.md`) |

### 12.5 Sağlıklı bir okuma rutini

1. Dönemi seç, **paydayı** kontrol et.
2. Aynı dönemi geçen yılla karşılaştır (mevsimsellik).
3. Oranın yanındaki ham sayıya bak (yüzde tek başına yalan söyleyebilir).
4. Trend grafiğinde son 3-4 noktayı gör, tek bir sıçramaya karar bağlama.
5. Aykırı bir sonuç gördüğünde önce **veri girişi hatası** ihtimalini ele —
   yanlış girilmiş bir derece veya çift kaydedilmiş bir yoklama sık rastlanır.
6. Kararı yazarken hangi metriğe, hangi dönemde, hangi paydayla baktığını not et.

---

## İlgili belgeler

* `docs/AI_GUIDE_TR.md` — gerçek veri / AI yorumu ayrımı ve AI kullanımı
* `docs/BACKUP_RESTORE_TR.md` — yedekleme ve geri yükleme
* `CHANGELOG.md` — sürüm notları
* `http://127.0.0.1:8000/docs` — canlı API dokümantasyonu (240 uç nokta)
