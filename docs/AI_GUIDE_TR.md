# Yapay Zekâ Kullanım Kılavuzu

Bu belge, programdaki yapay zekâ özelliklerini **teknik bilgi gerektirmeden**
anlatır: AI ne yapar, ne yapmaz, ekrandaki yeşil ve mor panellerin farkı nedir ve
bir AI yorumuna ne kadar güvenmelisiniz.

> Sürüm: 0.9.0 · Arayüz: **AI Merkezi** ekranı (`ai:use` izni gerekir)

---

## 1. Yapay Zekâ Bu Programda Ne Yapar

Programdaki yapay zekâ, **sayıları üretmez; hesaplanmış sayıları insan diline
çevirir.** İşleyiş şudur:

```
1. Program veritabanından gerçek sayıları hesaplar   → GERÇEK VERİ
2. Bu hesaplanmış özet yapay zekâya gönderilir
3. Yapay zekâ bunu yorumlar, olası nedenler ve öneriler yazar → AI YORUMU
4. Ekranda ikisi AYRI panellerde gösterilir
```

Yapay zekâya asla ham veritabanı verilmez. Ona her zaman **önceden hesaplanmış,
doğrulanabilir bir özet** gider ve "yukarıdaki gerçek verilere dayanarak yanıt ver,
sayıları değiştirme" talimatı verilir.

### AI'nın somut olarak yaptığı işler

| Ne yapar | Örnek |
|---|---|
| Sayıları cümleye çevirir | "Devam oranı %78" verisini alıp "Devam oranı hedefin 7 puan altında; düşüş özellikle Cumartesi sabah grubunda yoğunlaşıyor" der |
| Olası nedenleri listeler | Devamsızlık artışı için "okul sınav dönemi", "ulaşım", "ders saati" gibi hipotezler üretir |
| Öneri yazar | "Cumartesi 09:00 grubunu 10:30'a taşımayı deneyin" |
| Antrenman planı taslağı hazırlar | Sporcunun en zayıf stilini ve gelişim eğilimini görüp 4 haftalık taslak plan çıkarır |
| Yönetim özeti yazar | Haftalık operasyon ve finans özetini rapor diliyle toparlar |
| Sohbet eder | AI Merkezi → Sohbet sekmesinde serbest soru sorabilirsiniz |

### AI'nın YAPMADIĞI işler

* **Hesap yapmaz.** Devam oranı, doluluk, gelir, gelişim yüzdesi, hazırlık skoru —
  hepsini program hesaplar. AI kapalıyken bu sayılar aynen çalışır.
* **Veri değiştirmez.** Öğrenci kaydı açmaz, ders silmez, ödeme girmez.
* **Karar vermez.** Onaylamayı, uygulamayı ve sorumluluğu siz üstlenirsiniz.
* **Geleceği bilmez.** Yarışma sonucu, gelecek ayın geliri, bir öğrencinin ayrılıp
  ayrılmayacağı — bunlar tahmin değil, olsa olsa yorumdur.

---

## 2. GERÇEK VERİ ile AI YORUMU Ayrımı

Bu, programın en önemli tasarım kararıdır. Bir analiz sonucu her zaman **iki ayrı
panelde** gösterilir.

### 2.1 Yeşil panel — Gerçek Veri

```
┌─────────────────────────────────────────────────┐
│ ✓  GERÇEK VERİ                                  │  ← yeşil çerçeve, onay işareti
│    Bu bölüm veritabanından hesaplanmıştır       │
│                                                 │
│  • Ayşe Yılmaz · 24 performans kaydı            │
│  • 50 m serbest: en iyi 33.10, ilk→son          │
│    35.20→33.40 (-1.80 sn, %-5.11), eğilim:      │
│    improving                                    │
│                                                 │
│  [ Aktif Öğrenci: 412 ] [ Devam: %78.4 ] ...    │
└─────────────────────────────────────────────────┘
```

* **Kaynağı:** İstatistik Motoru (`statistics_engine.py`) — doğrudan veritabanı.
* **Doğruluğu:** Kesin. Aynı veriyle her zaman aynı sonucu verir, 395 test fonksiyonuyla
  doğrulanmıştır.
* **Nasıl kullanılır:** **Kararlarınızı bu panele dayandırın.** Bir rapora, veliyle
  görüşmeye veya personel toplantısına götüreceğiniz sayı buradadır.

### 2.2 Mor panel — AI Yorumu

```
┌─────────────────────────────────────────────────┐
│ ✦  AI YORUMU              [ local · llama-3.3 ] │  ← mor çerçeve, ✦ işareti
│                                                 │
│  Sporcunun 50 m serbest derecesinde son üç ayda │
│  istikrarlı bir hızlanma görülüyor...           │
│                                                 │
│  Olası Nedenler                                 │
│   • Antrenman hacminin artması                  │
│   • Teknik düzeltmenin oturması                 │
│                                                 │
│  Öneriler                                       │
│   • Dönüş çalışmasına ağırlık verilebilir       │
│                                                 │
│  ⓘ Bu yorum bir yapay zekâ modeli tarafından    │
│    üretilmiştir ve kesin gerçek değildir.       │
│    Kararlarınızı yukarıdaki hesaplanmış         │
│    verilere dayandırın.                         │
└─────────────────────────────────────────────────┘
```

* **Kaynağı:** Bir dil modeli (yerel LM Studio veya bulut NVIDIA).
* **Doğruluğu:** Değişkendir. Aynı soruyu iki kez sorarsanız farklı ifadeler
  alabilirsiniz. Panelin altındaki uyarı metni her zaman görünür.
* **Rozet:** Panelin sağ üstünde hangi sağlayıcı ve hangi model kullanıldığı yazar.

### 2.3 Neden bu ayrım var

1. **Sorumluluk.** Bir veliye "çocuğunuzun devamı %62" diyorsanız bu sayı kesin
   olmalıdır. AI'nın cümle kurarken sayıyı yuvarlaması veya karıştırması ihtimali
   sıfır değildir — bu yüzden sayı hiçbir zaman yalnızca AI panelinden okunmaz.
2. **AI olmadan da çalışmak.** Yerel model kapalıysa, internet yoksa veya API
   anahtarı yoksa yeşil panel **aynen çalışır**. Sistem AI'ya bağımlı değildir.
3. **Denetlenebilirlik.** İki panel ayrı olduğu için, bir yorumun hangi veriye
   dayandığını satır satır kontrol edebilirsiniz.
4. **Yasal ve etik zemin.** Öğrenci ve veli hakkında verilen kararların
   izlenebilir, açıklanabilir bir dayanağı olmalıdır.

### 2.4 AI yorumuna nasıl yaklaşılmalı

| Yaklaşım | Doğru mu |
|---|---|
| "AI böyle dedi, uyguluyoruz" | ✗ Yanlış |
| "AI şu üç nedeni saydı; ikisi bize mantıklı geldi, veriyle kontrol ettik" | ✓ Doğru |
| Bir AI cümlesindeki sayıyı rapora kopyalamak | ✗ Yanlış — sayıyı yeşil panelden alın |
| AI önerisini eğitmen toplantısında tartışmaya açmak | ✓ Doğru |
| AI yorumunu veliye "sistem böyle diyor" diye sunmak | ✗ Yanlış |
| AI'yı ilk bakış / fikir üretici olarak kullanmak | ✓ Doğru |

**Altın kural:** AI yorumu bir **meslektaş görüşüdür**, bir ölçüm sonucu değil.
Meslektaşınıza da "neden böyle düşünüyorsun?" diye sorarsınız.

---

## 3. AI Merkezi Ekranı

Sol menüden **AI Merkezi**'ni açın. Ekran altı sekmeden oluşur:

| Sekme | Ne işe yarar |
|---|---|
| **Kontrol Merkezi** | Sağlayıcı durumu, gecikme, model listesi, token kullanımı |
| **Analiz** | Veri analizi yaptırma (asıl kullanacağınız sekme) |
| **Sohbet** | Serbest soru-cevap |
| **Yönlendirme** | Hangi görevde hangi modelin önerildiği |
| **Görev Geçmişi** | Geçmiş AI çağrıları: sağlayıcı, model, token, süre, sonuç |
| **Ayarlar** | Sağlayıcı yapılandırması (yalnızca `ai:configure` izniyle görünür) |

### 3.1 Sağlayıcı durumları

Kontrol Merkezi'nde her sağlayıcı için bir kart görürsünüz:

| Alan | Anlamı |
|---|---|
| **Etkin (enabled)** | Ayarlarda açık mı |
| **Erişilebilir (available)** | Şu anda gerçekten yanıt veriyor mu |
| **Adres (endpoint)** | Bağlanılan sunucu adresi (örn. `http://localhost:1234/v1`) |
| **Model** | Kullanılan model adı |
| **API anahtarı** | Tanımlı mı — **her zaman maskeli gösterilir** (`nvi************a1b2`) |
| **Gecikme (latency)** | Sunucunun yanıt süresi, milisaniye |
| **Model sayısı** | Sağlayıcıda erişilebilir model sayısı |
| **Son kontrol** | Durumun en son ne zaman ölçüldüğü |
| **Hata mesajı** | Erişilemiyorsa nedeni |
| **Gizlilik notu** | Yerel için "veriler bilgisayarınızdan çıkmaz", bulut için "veriler NVIDIA sunucularında işlenir" |

Kartın rengi durumu özetler: erişilebilir sağlayıcı yeşil, kapalı olan gri,
hata veren kırmızıdır.

### 3.2 Gecikme (latency) nasıl okunur

Gecikme, sağlayıcının **sağlık kontrolüne** verdiği yanıt süresidir; bir analizin
tamamlanma süresi değildir.

| Gecikme | Yorum |
|---|---|
| < 200 ms | Çok iyi (tipik olarak yerel model) |
| 200–800 ms | Normal |
| 800–3000 ms | Yavaş; bulut sağlayıcıda ağ gecikmesi olabilir |
| Yanıt yok / zaman aşımı | LM Studio kapalı, model yüklü değil ya da internet yok |

Gerçek analiz süresi mor panelde ve **Görev Geçmişi** sekmesinde `duration_ms`
olarak görünür. Yerel bir modelde uzun bir analiz 20-60 saniye sürebilir; bu
normaldir (varsayılan zaman aşımı 180 saniyedir).

### 3.3 Token kullanımı

**Token**, modelin metni işlerken saydığı birimdir; kabaca 4 karakter ≈ 1 token.
Kontrol Merkezi iki sayaç gösterir:

* **Bugün** — bugünkü toplam token (istem + yanıt)
* **Toplam** — tüm zamanlar

Neden önemli: bulut sağlayıcıda token tüketimi **maliyet ve kota** demektir. Yerel
modelde ücret yoktur, ancak yüksek token sayısı yanıtın yavaşlaması demektir.

Ayrıca **24 saatlik hata sayacı** ve **görev türü sayaçları** gösterilir. Hata
sayacı sürekli artıyorsa sağlayıcı yapılandırmasında bir sorun vardır.

### 3.4 Bağlantı testi

Her sağlayıcı için **6 aşamalı test** çalıştırabilirsiniz. Her aşama
`PASS` / `FAIL` / `SKIPPED` döner:

| # | Test | Ne dener |
|---|---|---|
| 1 | `connection` | Sunucuya erişilebiliyor mu, kaç model listeleniyor |
| 2 | `model` | Model listesi çekilebiliyor mu |
| 3 | `simple_prompt` | Basit bir soruya yanıt geliyor mu |
| 4 | `json_output` | Model istenen JSON biçiminde çıktı verebiliyor mu |
| 5 | `timeout` | Zaman aşımı sınırı içinde yanıt dönüyor mu |
| 6 | `streaming` | Akış (kelime kelime yanıt) çalışıyor mu |

Sağlayıcı kapalıysa veya API anahtarı yoksa altı test de `SKIPPED` döner.
Bağlantı kurulamıyorsa 1 `FAIL`, kalan beşi `SKIPPED` olur.

---

## 4. Analiz Yapma

**AI Merkezi → Analiz** sekmesi.

### 4.1 Adım adım

1. **Analiz konusunu (kapsamı) seçin.** Bu, programın hangi verileri hesaplayıp
   AI'ya göndereceğini belirler.
2. **Sorunuzu yazın** veya hazır sorulardan birine tıklayın.
3. Konu bir öğrenciyle ilgiliyse (`Öğrenci gerekli` etiketi görünür) **öğrenciyi
   seçin**.
4. İsterseniz **tarih aralığı** ve **sağlayıcı** (otomatik / yerel / bulut) seçin.
5. **Analiz Et**'e basın.
6. Önce yeşil panel, ardından mor panel görünür.

### 4.2 Analiz konuları

| Konu | Hangi veriyi hesaplar |
|---|---|
| Genel bakış | Kontrol paneli sayaçlarının tamamı |
| Öğrenci performansı | Seçili sporcunun tüm etkinlik dereceleri ve gelişimi |
| Antrenman önerisi | Aynı performans verisi, antrenör bakış açısıyla |
| En zayıf stil | Aynı performans verisi, stil karşılaştırması odaklı |
| Performansı düşenler | Son 90 günde gerileyen sporcu-etkinlik listesi |
| En çok gelişenler | Son 90 günde en çok hızlanan sporcu-etkinlik listesi |
| Yarışma hazırlığı | Son 60 günün istatistiksel hazırlık skorları |
| Yoklama | Dönemin devam, devamsızlık, geç, mazeret oranları |
| Tutundurma | Kayıt/ayrılma, tutundurma, churn ve cohort verisi |
| Finans | Dönem geliri, gideri, net, bekleyen alacak, geciken fatura |
| Eğitmen iş yükü | Eğitmen başına ders, saat, doluluk, devam, iptal |
| Program optimizasyonu | Havuz doluluğu, saatlik/günlük yük, boş kapasite |
| Boş kulvarlar | Aynı havuz verisi, boş saat odaklı |
| Ödeme riski | Geciken faturalar ve 14 gün içinde bitecek üyelikler |

### 4.3 Hazır sorular

Ekranın altında **18 hazır sorudan** oluşan bir kütüphane vardır (5'i geliştiriciye
yöneliktir ve yalnızca AI Geliştirici Konsolu'nda görünür). Birine tıkladığınızda
soru metni kutuya yazılır ve doğru analiz konusu otomatik seçilir.

Kullanıma hazır 13 soru: öğrenci performansı analizi, performansı düşenleri bulma,
4 haftalık antrenman önerisi, en zayıf stili belirleme, en çok gelişenler, yarışmaya
hazır sporcular, ders programını optimize etme, boş kulvarları bulma, eğitmen yükünü
dengeleme, ödeme riski, öğrenci kaybı analizi, haftalık yönetim raporu, devam oranı
analizi.

### 4.4 Sonucun okunması

| Bölüm | Nereden gelir | Nasıl okunur |
|---|---|---|
| Yeşil panel — madde listesi | Hesaplanmış özet | Karar dayanağınız |
| Yeşil panel — kartlar ve tablolar | Ayrıntılı metrikler | Sayıları buradan alın |
| Mor panel — yorum | AI | Bir görüş; kontrol edin |
| Mor panel — Olası Nedenler | AI | En çok 8 madde; hipotezdir, kanıt değil |
| Mor panel — Öneriler | AI | En çok 8 madde; uygulamadan önce değerlendirin |
| Mor panel — rozet | Sistem | Hangi sağlayıcı ve model kullanıldı |
| Alt uyarı | Sistem | Her zaman görünür, kapatılamaz |

**"Yeterli veri yok" uyarısı:** Hesaplanan veri noktası sayısı **3'ün altındaysa**
AI hiç çağrılmaz. Yeşil panel yine görünür, mor panel yerine bilgi mesajı çıkar. Bu
bilinçli bir korumadır: 2 kayıttan "eğilim" çıkarmak yanıltıcıdır.

---

## 5. Örnek Sorular ve Nasıl Yorumlanacağı

### Örnek 1 — Tek sporcunun performansı

> **"Ahmet'in son 3 aylık 50 m serbest performansını analiz et"**
> Konu: *Öğrenci performansı* · Öğrenci: Ahmet Kaya · Tarih: son 3 ay

**Yeşil panelde göreceğiniz:** kayıt sayısı, en iyi/ortalama/medyan derece, standart
sapma, ilk→son derece, gelişim saniyesi ve yüzdesi, 30 ve 90 günlük değişim, eğilim
etiketi (`improving` / `declining` / `stable`).

**Nasıl yorumlanır:** Önce **eğilim etiketine** ve **gelişim yüzdesine** bakın.
Yüzmede küçük derece iyidir, dolayısıyla negatif saniye farkı iyi haberdir. AI'nın
"belirgin gelişme var" cümlesini yeşil paneldeki `%-5.11` ile doğrulayın. Kayıt
sayısı 5'in altındaysa hem eğilim hem yorum zayıftır.

---

### Örnek 2 — Performansı düşen sporcular

> **"Performansı düşen öğrencileri bul ve olası nedenleri değerlendir"**
> Konu: *Performansı düşenler*

**Yeşil panelde:** Son 90 günde gerileyen sporcu-etkinlik çiftleri; her satırda baz
ortalama, son ortalama, gerileme saniyesi ve yüzdesi, kayıt sayısı, son kayıt tarihi.

**Nasıl yorumlanır:** Listeye girmek için en az 4 kayıt ve en az %1 gerileme gerekir.
%1-2 bandı normal dalgalanma olabilir; **%4 üstü gerçek bir sinyaldir.** AI'nın
sıraladığı nedenler (yorgunluk, teknik bozulma, motivasyon) **hipotezdir** — sporcuyla
ve eğitmenle konuşmadan karar vermeyin. Aynı sporcunun yoklama kaydına da bakın.

---

### Örnek 3 — Yarışma hazırlığı

> **"Yarışma öncesi hangi sporcular daha hazır görünüyor? Gerekçeleriyle açıkla"**
> Konu: *Yarışma hazırlığı*

**Yeşil panelde:** Her sporcu-etkinlik için hazırlık skoru (0-100), en iyi derece,
son ortalama, tutarlılık (standart sapma), eğilim ve son dönem kayıt sayısı.

**Nasıl yorumlanır:** Skor **istatistikseldir, AI tahmini değildir**: tutarlılık %25 +
forma %35 + eğilim %25 + hacim %15. Rakipleri, havuz tipini ve günlük formu bilmez.
Doğru kullanım, **aynı etkinlikteki sporcuları birbirine göre sıralamak**. "Kim
kazanır" sorusunun cevabı burada yoktur.

---

### Örnek 4 — Devam oranı

> **"Devam oranlarını analiz et ve devamsızlığı azaltmak için öneri ver"**
> Konu: *Yoklama*

**Yeşil panelde:** Genel devam oranı, geldi/gelmedi/geç/mazeretli sayıları,
devamsızlık oranı, gruba ve eğitmene göre kırılım, en düşük devamlı öğrenciler.

**Nasıl yorumlanır:** Geç gelen ve telafiye katılan **gelmiş** sayılır; mazeretli
devamsızlık ise oranı **düşürür**. AI "devam düştü" diyorsa mevsim etkisini kendiniz
ekleyin — sınav dönemi ve hastalık sezonu bu oranı yapısal olarak düşürür. Grup
kırılımında az kayıtlı grupların oranı oynak olur.

---

### Örnek 5 — Öğrenci kaybı

> **"Son üç ayda öğrenci kaybımız neden arttı? Verilere dayanarak açıkla"**
> Konu: *Tutundurma*

**Yeşil panelde:** Aktif öğrenci, yeni kayıt, ayrılan, tutundurma %, churn %,
ortalama üyelik günü, önceki dönemle karşılaştırma ve son 6 ayın cohort tablosu.

**Nasıl yorumlanır:** En değerli bilgi **cohort tablosudur**: hangi ay kaydolanların
hangi ayda eridiğini gösterir. AI'nın "fiyat artışı" gibi nedenleri sistemde veri
karşılığı olmayan tahminlerdir — kendi bildiğiniz olaylarla eşleştirin. Cohort
büyüklüğü 5-10 kişiyse tek ayrılış bile %10-20 düşüş gösterir.

---

### Örnek 6 — Ders programı

> **"Mevcut ders programını incele ve doluluk açısından iyileştirme öner"**
> Konu: *Program optimizasyonu*

**Yeşil panelde:** Genel havuz doluluğu, en yoğun ve en boş saat, en çok kullanılan
kulvar, kullanılmayan kapasite (saat), saatlik ve günlük yük dağılımı.

**Nasıl yorumlanır:** Doluluk paydası havuzun tüm açık saatlerini ve **tüm günleri**
kapsar; %100 imkânsızdır. AI "doluluk düşük" dediğinde panik yapmayın, kendi
tesisinizin gerçekçi bandını (genellikle %45-55) referans alın. AI'nın saat taşıma
önerisini uygulamadan önce **eğitmen müsaitliği ve havuz bakım takvimini** kontrol
edin — bunlar AI'ya gönderilen özette yoktur.

---

### Örnek 7 — Eğitmen yükü

> **"Eğitmen ders yüklerini incele ve dengeleme önerisi getir"**
> Konu: *Eğitmen iş yükü*

**Yeşil panelde:** Eğitmen başına ders sayısı, toplam saat, doluluk %, devam %,
iptal %, özel/grup ders dağılımı.

**Nasıl yorumlanır:** Bu tablo **performans değerlendirmesi değildir**. Doluluğu
program belirler, devamı öğrenciler belirler. AI "X eğitmeni verimsiz" derse bunu
kabul etmeyin — düşük doluluk büyük olasılıkla kötü seçilmiş bir ders saatidir.
Dönemde 3 ders veren bir eğitmenin oranları istatistiksel olarak anlamsızdır.

---

### Örnek 8 — Ödeme riski

> **"Ödeme riski taşıyan üyelikleri belirle ve tahsilat stratejisi öner"**
> Konu: *Ödeme riski*

**Yeşil panelde:** Geciken fatura sayısı ve toplam tutarı, en fazla 40 fatura detayı
(öğrenci, bakiye, kaç gün gecikmiş, vade), 14 gün içinde bitecek üyelik sayısı.

**Nasıl yorumlanır:** Sayılar kesindir; **iletişim tonu ve önceliklendirme** için
AI'dan yararlanın. Veliye giden hiçbir mesajı AI metniyle olduğu gibi göndermeyin —
ödeme konusu hassastır, kurumsal dilinizi ve KVKK yükümlülüklerinizi siz belirlersiniz.

---

### Örnek 9 — Yönetim özeti

> **"Bu haftanın operasyon ve performans özetini yönetim için yaz"**
> Konu: *Genel bakış*

**Yeşil panelde:** Aktif öğrenci, bugünkü ders, havuz doluluğu, aylık gelir/gider,
geciken ödeme, bitmek üzere olan üyelik, yaklaşan yarışma, performansı düşen sporcu
sayısı.

**Nasıl yorumlanır:** AI'nın yazdığı özet iyi bir **taslaktır**. Yönetim kuruluna
gitmeden önce her sayıyı yeşil panelden doğrulayın ve **Raporlar → Haftalık Yönetim
Raporu**'nu (PDF/Excel) resmî belge olarak ekleyin.

---

### Örnek 10 — En zayıf stil

> **"Bu sporcunun en zayıf yüzme stilini belirle ve gelişim önerisi ver"**
> Konu: *En zayıf stil* · Öğrenci seçimi zorunlu

**Yeşil panelde:** Stil bazında ortalama gelişim yüzdesi; en güçlü ve en zayıf stil
etiketi.

**Nasıl yorumlanır:** "En zayıf stil", **en az geliştiği stildir** — mutlak olarak en
yavaş olduğu stil değil. Sporcu kelebekte zaten çok az yarışıyorsa o stil kayıt
azlığından zayıf görünebilir. Etkinlik başına kayıt sayısını mutlaka kontrol edin.

---

## 6. Antrenman Planı Önerisi

**Performans → Öğrenci → AI Antrenman Planı** veya AI Merkezi'nde
*Antrenman önerisi* konusu.

Program, sporcunun performans özetini hesaplar, AI'ya gönderir ve gelen yanıttan bir
plan kaydı oluşturur.

### 6.1 Plan bir TASLAKTIR

Oluşturulan plan veritabanına **`is_approved = false`** olarak yazılır ve yanıtta
`requires_approval: true` alanı döner. Yani:

* Plan **yürürlükte değildir**. Kimseye ders programı olarak atanmaz.
* **Bir eğitmen onaylamadan uygulanmaz.**
* Kaydın üzerinde `ai_generated = true`, hangi sağlayıcı ve hangi model kullanıldığı
  yazılıdır — sonradan kimin ne ürettiği izlenebilir.
* Yanıtın sonunda kapatılamayan bir uyarı metni bulunur.

### 6.2 Eğitmenin yapması gerekenler

1. Planı açın ve **odak alanını** kontrol edin (sporcunun en zayıf stiline göre
   otomatik doldurulur).
2. Sporcunun **yaşını, seviyesini ve sağlık notunu** kontrol edin — bunlar AI'ya
   gönderilen özette **yoktur**. Bebek/çocuk gruplarında bu adım zorunludur.
3. Haftalık ders sayısını, havuz müsaitliğini ve yarışma takvimini planla eşleştirin.
4. Gerekli düzenlemeleri yapın.
5. Onaylayın. Onaysız plan hiçbir yerde uygulanmaz.

> **Sağlık uyarısı:** AI, sporcunun sakatlık geçmişini, kronik rahatsızlığını veya
> doktor kısıtını bilmez. Adaptif yüzme ve sağlık notu olan sporcularda AI planını
> **başlangıç noktası bile saymayın**; ilgili eğitmen ve sağlık personeliyle birlikte
> hazırlayın.

---

## 7. Yerel AI ve Bulut AI

Program üç sağlayıcı türünü destekler: **LM Studio (yerel)**, **NVIDIA Build (bulut)**
ve genel **OpenAI uyumlu** sunucular.

| | Yerel (LM Studio) | Bulut (NVIDIA Build) |
|---|---|---|
| **Veri nereye gider** | Hiçbir yere — kendi bilgisayarınızda kalır | NVIDIA sunucularına gönderilir |
| **İnternet gerekir mi** | Hayır | Evet |
| **Ücret** | Yok | Sağlayıcı kotasına/tarifesine bağlı |
| **Hız** | Bilgisayarınızın gücüne bağlı; güçlü makinede çok hızlı | Genelde hızlı, ağa bağlı |
| **Model kalitesi** | İndirdiğiniz modele bağlı | Büyük modeller erişilebilir |
| **Kurulum** | LM Studio kurup model indirmeniz gerekir | Yalnızca API anahtarı |
| **Kesinti** | Program açıksa çalışır | Sağlayıcı kesintisinden etkilenir |

Kontrol Merkezi'ndeki gizlilik notları bunu her kartta hatırlatır:

* Yerel: *"Yerel model: veriler bilgisayarınızdan dışarı çıkmaz. Hassas öğrenci
  verileri için önerilir."*
* Bulut: *"Bulut model: gönderilen veriler NVIDIA sunucularında işlenir. Kişisel veri
  gönderirken dikkatli olun."*

### 7.1 Hangisini ne zaman

| Durum | Öneri |
|---|---|
| Öğrenci adı, sağlık notu veya veli bilgisi içeren analiz | **Yerel** |
| Reşit olmayan sporcularla ilgili her analiz | **Yerel** |
| Yalnızca toplam/oran içeren yönetim özeti (isim yok) | Bulut kabul edilebilir |
| İnternet yok | Yerel (tek seçenek) |
| Yerel bilgisayar zayıf ve analiz çok yavaş | Bulut — ama önce isim içerip içermediğini kontrol edin |
| Kurumsal gizlilik politikanız veri çıkışını yasaklıyor | **Yalnızca yerel**; bulut sağlayıcıyı ayarlardan kapatın |

### 7.2 Otomatik fallback

Varsayılan çalışma kipi **otomatik**tir. Sistem, `.env` dosyasındaki zincire göre
sırayla dener (varsayılan: `local,nvidia`). İlk sağlayıcı yanıt vermezse ikinciye
geçer. Hangisinin kullanıldığını mor panelin rozetinde görürsünüz.

Yalnızca yerel çalışmak istiyorsanız çalışma kipini **yerel** yapın; bu durumda hiçbir
veri internete çıkmaz.

---

## 8. AI Çalışmadığında

**Sistemin geri kalanı normal çalışmaya devam eder.** Bu, mimarinin temel
garantisidir: AI bir eklentidir, bir bağımlılık değil.

AI kapalıyken **çalışmaya devam eden** her şey:

* Öğrenci, veli, eğitmen, ders, yoklama, üyelik, finans kayıtları
* Takvim, çakışma denetimi, kulvar planlama
* **Tüm istatistikler** — devam oranı, doluluk, tutundurma, gelişim yüzdesi
* **Yarışma hazırlık skoru** (istatistikseldir, AI değil)
* **16 rapor türü ve PDF/Excel/CSV dışa aktarma**
* KPI paneli, bildirimler, yedekleme

Kaybettiğiniz tek şey **mor paneldeki yorum metnidir**.

### 8.1 Belirti ve çözüm

| Belirti | Olası neden | Ne yapmalı |
|---|---|---|
| Mor panel yerine "AI kullanılamıyor" uyarısı | Sağlayıcı yanıt vermiyor | Kontrol Merkezi → sağlayıcı kartına bakın |
| "Yeterli veri yok" mesajı | Hesaplanan veri noktası 3'ten az | Daha geniş bir tarih aralığı seçin veya daha fazla kayıt girin |
| Yerel sağlayıcı kırmızı | LM Studio kapalı veya model yüklenmemiş | LM Studio'yu açın, bir model yükleyin, sunucuyu başlatın |
| Bulut sağlayıcı kırmızı | API anahtarı yok/geçersiz ya da internet yok | Anahtarı `.env` dosyasında `NVIDIA_API_KEY` olarak tanımlayın; anahtar olmadan bulut sağlayıcı **etkin sayılmaz** |
| Analiz çok yavaş | Yerel model büyük, bilgisayar zorlanıyor | Daha küçük bir model deneyin veya bulut sağlayıcıya geçin |
| Zaman aşımı hatası | Model 180 saniyede yanıt veremedi | Ayarlardan zaman aşımını artırın veya daha küçük model kullanın |
| AI Merkezi ekranı hiç görünmüyor | `ai:use` izniniz yok | Yöneticinizden izin talep edin |
| Ayarlar sekmesi görünmüyor | `ai:configure` izniniz yok | Bu izin yalnızca yöneticidedir |

### 8.2 AI hatası veri kaybına yol açmaz

Bir AI çağrısı başarısız olduğunda program hata fırlatmaz; yalnızca yeşil paneli
döndürür ve `ai_available: false` işaretler. Başarısız çağrı **Görev Geçmişi**
sekmesine hata mesajıyla birlikte yazılır, böylece sorunu sonradan inceleyebilirsiniz.

---

## 9. Sınırlamalar ve Dikkat Edilecekler

### 9.1 AI ne zaman yanılır

| Durum | Neden yanılır | Ne yapmalı |
|---|---|---|
| **Veri az** | 3-5 kayıttan çıkarılan "eğilim" gürültüdür | Yeşil paneldeki kayıt sayısına bakın; azsa yorumu ciddiye almayın |
| **Mevsimsellik** | AI'ya gönderilen özette mevsim bilgisi yoktur; yaz düşüşünü "kriz" sanabilir | Geçen yılın aynı dönemiyle kendiniz karşılaştırın |
| **Bağlam eksikliği** | Havuz tadilatı, eğitmen değişikliği, fiyat zammı, okul sınav takvimi — hiçbiri veride yoktur | Bildiğiniz olayları yoruma siz ekleyin |
| **Neden-sonuç kurma eğilimi** | Dil modelleri "çünkü" cümlesi kurmaya yatkındır; korelasyonu nedensellik gibi sunabilir | Her "çünkü" cümlesine şüpheyle yaklaşın |
| **Sayı uydurma** | Nadiren de olsa modeller özette olmayan bir sayı üretebilir | Yorumdaki her sayıyı yeşil panelde arayın; yoksa güvenmeyin |
| **Aşırı kendinden emin dil** | Model "kesinlikle", "açıkça" gibi ifadeler kullanabilir | Bu ifadeler kanıt değildir |
| **Model farkı** | Küçük yerel model ile büyük bulut modelin yorum kalitesi farklıdır | Rozetten hangi modelin kullanıldığını görün |

### 9.2 Asla yapılmaması gerekenler

* AI yorumunu **veliye, öğrenciye veya personele resmî bir değerlendirme** olarak
  sunmak.
* AI çıktısını **performans değerlendirmesi, işten çıkarma, sözleşme yenilememe**
  gibi kararlarda tek dayanak yapmak.
* AI'nın önerdiği antrenman planını **eğitmen onayı olmadan** uygulamak.
* Sağlık, sakatlık veya tıbbi konularda AI yorumunu esas almak — bu alan **sağlık
  personelinin** sorumluluğundadır.
* Bir çocuk hakkındaki kişisel değerlendirmeyi bulut sağlayıcıya göndermek.

### 9.3 Her zaman hatırlayın

> Mor panelin altındaki uyarı kapatılamaz ve her yanıtta görünür:
>
> *"Bu yorum bir yapay zekâ modeli tarafından üretilmiştir ve kesin gerçek değildir.
> Kararlarınızı yukarıdaki hesaplanmış verilere dayandırın."*
>
> Bu cümle bir formalite değil, kullanım kuralıdır.

---

## 10. Gizlilik — Hangi Veri Nereye Gider

### 10.1 Bir analizde AI'ya ne gönderilir

Gönderilen paket üç parçadan oluşur:

1. **Sorunuz** (yazdığınız metin)
2. **Hesaplanmış özet** — örneğin "Ayşe Yılmaz · 24 performans kaydı · 50 m serbest:
   en iyi 33.10..."
3. **Ayrıntılı metrikler (JSON)** — en fazla 6000 karakterle sınırlıdır

Kapsam öğrenci bazlıysa **sporcunun adı soyadı** da gönderilir.

### 10.2 AI'ya ASLA gönderilmeyenler

| Gönderilmeyen | Neden |
|---|---|
| T.C. kimlik numarası, adres, e-posta | Metrik özetinde yer almaz |
| Veli iletişim bilgileri | Özette yoktur |
| Parolalar ve parola özetleri | Sistemin hiçbir katmanında dışarı çıkmaz |
| API anahtarları | Arayüzde bile maskeli gösterilir |
| Sağlık notu ve özel ihtiyaç bilgisi | `student:read_sensitive` ile korunur, metrik özetine girmez |
| Ham veritabanı tabloları | AI yalnızca hesaplanmış özet alır |
| Ödeme kartı bilgisi | Sistemde tutulmaz |

### 10.3 Veri hangi yolu izler

| Sağlayıcı | Rota | Kim görebilir |
|---|---|---|
| **Yerel (LM Studio)** | Program → `http://localhost:1234` → aynı bilgisayardaki model | Yalnızca siz. Veri ağdan çıkmaz |
| **Bulut (NVIDIA Build)** | Program → HTTPS → `integrate.api.nvidia.com` | NVIDIA'nın hizmet koşulları geçerlidir |
| **OpenAI uyumlu** | Program → sizin tanımladığınız adres | Adresi kimin işlettiğine bağlıdır |

### 10.4 Kayıt ve loglama

* Her AI çağrısı **Görev Geçmişi**'ne yazılır: sağlayıcı, model, token sayısı, süre,
  başarı/hata. Bu kayıt yerel veritabanınızdadır.
* **İstem metinleri varsayılan olarak loglanmaz.** `AI_LOG_PROMPTS` ayarı
  varsayılan olarak kapalıdır; yalnızca hata ayıklama için açılır.
* API anahtarları hiçbir log satırına yazılmaz; arayüzde de yalnızca maskeli görünür.

### 10.5 KVKK / GDPR pratiği

1. **Kişisel veri içeren analizleri yerel sağlayıcıyla yapın.** En basit ve en güvenli
   kural budur.
2. Bulut sağlayıcı kullanacaksanız, kurumunuzun aydınlatma metninde **yurt dışına veri
   aktarımı** başlığının bulunduğundan emin olun.
3. Reşit olmayan sporcularla ilgili analizlerde bulut sağlayıcıdan kaçının.
4. Bulut kullanımını tamamen kapatmak için: **AI Merkezi → Ayarlar** → NVIDIA
   sağlayıcısını devre dışı bırakın, çalışma kipini **yerel** yapın. Bu durumda hiçbir
   veri bilgisayardan çıkmaz.

---

## İlgili belgeler

* `docs/STATISTICS_GUIDE_TR.md` — yeşil paneldeki her sayının nasıl hesaplandığı
* `docs/BACKUP_RESTORE_TR.md` — yedekleme ve geri yükleme
* `CHANGELOG.md` — sürüm notları ve bilinen kısıtlamalar
* Program içi **Yardım** ekranı — 28 bölümlük kullanım kılavuzu
