# Kullanım Kılavuzu (Son Kullanıcı)

Bu kılavuz, Akıllı Yüzme Okulu Yönetim Sistemi'ni günlük işlerinde kullanan resepsiyon, eğitmen, antrenör ve öğretmen personeli içindir. Her bölüm, programdaki gerçek ekran akışını adım adım anlatır; ekranların ve alanların adları arayüzde gördüğünüz karşılıklarıyla birebir aynıdır.

> Sistem yöneticisi ve müdür işlemleri (kurulum, kullanıcı/rol yönetimi, yedekleme, KPI hedefleri, denetim kaydı) için: [ADMIN_GUIDE_TR.md](ADMIN_GUIDE_TR.md)

**Sürüm:** 0.9.0 · **Lisans:** MIT · **Program içi kısa kılavuz:** sol menü → *Kullanım Kılavuzu* (`/help`) · **İnteraktif eğitimler:** sol menü → *Eğitim Merkezi* (`/training`)

---

## İçindekiler

| # | Bölüm | # | Bölüm |
|---|-------|---|-------|
| 1 | [Programa Giriş](#1-programa-giriş) | 12 | [Üyelik ve Paket](#12-üyelik-ve-paket) |
| 2 | [Dashboard Kullanımı](#2-dashboard-kullanımı) | 13 | [Ödeme Alma](#13-ödeme-alma) |
| 3 | [Öğrenci Yönetimi](#3-öğrenci-yönetimi) | 14 | [Performans Kaydı](#14-performans-kaydı) |
| 4 | [Veli Yönetimi](#4-veli-yönetimi) | 15 | [Yarışma Yönetimi](#15-yarışma-yönetimi) |
| 5 | [Eğitmen Yönetimi](#5-eğitmen-yönetimi) | 16 | [Rapor Oluşturma](#16-rapor-oluşturma) |
| 6 | [Havuz ve Kulvar](#6-havuz-ve-kulvar) | 17 | [Bildirimler](#17-bildirimler) |
| 7 | [Ders Oluşturma](#7-ders-oluşturma) | 18 | [Dil Değiştirme ve Tema](#18-dil-değiştirme-ve-tema) |
| 8 | [Tekrarlanan Ders](#8-tekrarlanan-ders-serisi) | 19 | [Klavye Kısayolları](#19-klavye-kısayolları) |
| 9 | [Ders Takvimi](#9-ders-takvimi) | 20 | [Sık Sorulan Sorular](#20-sık-sorulan-sorular) |
| 10 | [Kulvar Planlama](#10-kulvar-planlama) | 21 | [Sorun Giderme](#21-sorun-giderme) |
| 11 | [Yoklama Alma](#11-yoklama-alma) | | |

---

## 1. Programa Giriş

### 1.1 Programı başlatma

Program bir masaüstü uygulaması gibi çalışır; ayrı bir sunucu kurmanız gerekmez.

1. Proje klasöründeki **`START_SWIMMING_SCHOOL.bat`** dosyasına çift tıklayın.
2. Siyah bir konsol penceresi açılır. İlk çalıştırmada:
   - Python sanal ortamı (`.venv`) oluşturulur ve bağımlılıklar kurulur (birkaç dakika sürebilir),
   - `.env` yapılandırma dosyası `.env.example`'dan üretilir ve güvenlik anahtarı otomatik atanır,
   - veritabanı güncellemeleri (`alembic upgrade head`) uygulanır.
3. Ardından program penceresi açılır (Windows WebView2 tabanlı). Pencere açılmazsa program varsayılan tarayıcınızda `http://127.0.0.1:8000` adresinde açılır.
4. Konsol penceresini **kapatmayın**; program o pencerede çalışıyor demektir. Kapatmak programı durdurur.

> Arayüz derlemesi yoksa konsolda `Arayuz derlemesi bulunamadi` uyarısı çıkar. Bu durumda bir kez **`BUILD_FRONTEND.bat`** dosyasını çalıştırın.

### 1.2 Giriş yapma

Giriş ekranında iki alan vardır:

| Alan | Açıklama |
|------|----------|
| **E-posta** | Yöneticinizin size tanımladığı hesap adresi (örn. `resepsiyon@yuzmeokulu.local`). |
| **Parola** | Hesabınızın parolası. |

Sağ üstteki **Türkçe / English** düğmesiyle giriş ekranının dilini daha oturum açmadan değiştirebilirsiniz.

Dikkat edilecekler:

- Parolanız **8 karakterden kısa olamaz**, en az bir harf ve bir rakam içermelidir.
- Üst üste **8 hatalı deneme** hesabınızı **15 dakika** kilitler. Kilitliyken doğru parolayı girseniz de giriş yapamazsınız; süreyi bekleyin veya yöneticinize başvurun.
- Oturumunuz **120 dakika** sonra düşer; program arka planda otomatik yenileme yapar, yenilenemezse tekrar giriş istenir.
- Yönetici hesabınıza "ilk girişte parola değiştir" işareti koyduysa, *Ayarlar → Profil* sekmesinden parolanızı değiştirmeniz beklenir.

### 1.3 Kurulum sihirbazı (yalnızca ilk kullanıcı)

Hesabınızda kurulum sihirbazı henüz tamamlanmadıysa giriş sonrası doğrudan **Kurulum Sihirbazı** ekranı açılır. Bu ekran 9 adımdan oluşur (kurum bilgileri → yönetici parolası → havuz → kulvarlar → eğitmen → öğrenci → AI → yedekleme → bitiş). Sihirbazı **"Şimdilik Geç"** ile atlayabilirsiniz; daha sonra *Eğitim Merkezi*'nden devam edebilirsiniz. Ayrıntı için yönetici kılavuzuna bakın.

### 1.4 Arayüz turu

```
┌────────────┬────────────────────────────────────────────────────────────┐
│            │  [Arama kutusu  /]        [⌘] [TR] [☀] [🔔] [Kullanıcı ▾]  │  ← üst çubuk
│  SOL MENÜ  ├────────────────────────────────────────────────────────────┤
│            │                                                            │
│            │                     İÇERİK ALANI                           │
│            │                                                            │
└────────────┴────────────────────────────────────────────────────────────┘
```

**Sol menü** başlıklara ayrılmıştır. Yalnızca yetkiniz olan başlıklar görünür; yetkiniz yoksa satır menüde hiç yer almaz.

| Bölüm | Ekranlar |
|-------|----------|
| Genel Bakış | Kontrol Paneli |
| Kişiler | Öğrenciler, Veliler, Eğitmenler |
| Operasyon | Takvim, Dersler, Havuzlar, Kulvar Planı, Yoklama |
| Finans | Üyelikler, Finans |
| Spor | Performans, Yarışmalar |
| Analitik | İstatistikler, Raporlar |
| Yapay Zekâ | AI Merkezi, AI Developer Console, CAIO |
| Sistem | Eğitim Merkezi, Kullanım Kılavuzu, Bildirimler, Ayarlar |

Menünün en altındaki **Daralt** düğmesi menüyü ikon şeridine küçültür; ekranı dar monitörlerde rahatlatır.

**Üst çubuk** öğeleri:

| Öğe | İşlevi |
|-----|--------|
| Arama kutusu | Global arama panelini açar. Kısayol: `/` |
| Terminal ikonu | Komut paletini açar. Kısayol: `Ctrl+K` |
| **TR / EN** | Arayüz dilini anında değiştirir |
| Güneş / ay ikonu | Tema döngüsü: Açık → Koyu → Sistem |
| Zil ikonu | Bildirimler ekranı; okunmamış bildirim varsa kırmızı nokta çıkar |
| Kullanıcı adı | Hesabım, Denetim Kaydı (yetkiliyse), Çıkış |

**Global arama** (`/`): en az **2 karakter** yazınca çalışır. Öğrenci, veli, eğitmen, ders, ödeme, paket, havuz, grup ve yarışma kayıtlarında aynı anda arar; sonuçlar gruplar hâlinde listelenir. Yalnızca yetkiniz olan kayıt türleri gösterilir. `Esc` paneli kapatır.

**Komut paleti** (`Ctrl+K`): sık kullanılan işlemlere ekran değiştirmeden gitmenizi sağlar. Yazarak filtreleyin, `↑` `↓` ile gezinin, `Enter` ile çalıştırın, `Esc` ile kapatın. Palette yalnızca yetkiniz olan komutlar listelenir:

Yeni öğrenci · Yeni veli · Yeni eğitmen · Yeni ders · Tekrarlanan ders · Yoklama al · Yeni ödeme · Yeni üyelik · Performans kaydı · Yeni yarışma · Kulvar planı · AI analizi · AI Developer Console · CAIO raporu · Rapor oluştur · İstatistik merkezi · Şimdi yedekle · Ayarları aç · Denetim kaydı · Eğitim merkezi · Kullanım kılavuzu

**Eğitim modu bandı:** hesabınızda eğitim modu açıksa üst çubuğun altında mor bir şerit görünür. Bu şerit görünüyorken demo kayıtlar üzerinde çalıştığınızı hatırlatır.

---

## 2. Dashboard Kullanımı

Kontrol paneli (`/`) giriş yaptığınızda açılan ekrandır ve okulun o anki durumunu özetler. Veriler **2 dakikada bir** kendiliğinden tazelenir; sayfayı yenilemenize gerek yoktur.

### 2.1 Kartların anlamı

| Kart | Ne gösterir |
|------|-------------|
| Aktif öğrenci | Durumu "Aktif" olan öğrenci sayısı (toplam kayıt sayısı ayrıca gösterilir) |
| Bugünkü ders | Bugün başlayan ders sayısı ve bunlardan kaçının tamamlandığı |
| Aktif eğitmen | Kaydı aktif olan eğitmen sayısı |
| Havuz doluluk | Bugünün kulvar-dakika kullanımına göre hesaplanan doluluk yüzdesi |
| Kulvar durumu | Şu anda kullanılan / boş / toplam kulvar sayısı |
| Bugün tahsilat | Bugün girilen ödemelerin net toplamı (iadeler düşülmüş) |
| Bugün vadesi gelen | Vadesi bugün olan ve henüz kapanmamış fatura tutarı |
| Aylık gelir / gider | Ayın 1'inden bugüne toplam tahsilat ve gider |
| Bugünkü devam oranı | Bugünkü yoklamalarda geldi + geç geldi + telafi oranı |
| Ay içi yeni kayıt | Bu ay kaydolan öğrenci sayısı |

Finans içeren kartlar yalnızca **finans okuma** yetkisi olan kullanıcılara görünür.

### 2.2 Uyarılar

Kartların üstündeki uyarı alanı aksiyon gerektiren durumları öne çıkarır:

- **Yoklaması alınmamış ders** — bitiş saati geçmiş, iptal edilmemiş ve hiç yoklama kaydı olmayan dersler.
- **Biten üyelik** — önümüzdeki **14 gün** içinde süresi dolacak aktif üyelikler.
- **Geciken ödeme** — vadesi geçmiş ve bakiyesi kapanmamış fatura sayısı ve tutarı.
- **Yaklaşan deneme dersi** — önümüzdeki 7 gün içindeki deneme dersleri.
- **Performansı gerileyen sporcu** — son 90 günde derecesi kötüleşen sporcu sayısı.
- **Yaklaşan yarışma** — önümüzdeki 30 gün içindeki yarışmalar.

Uyarıya tıkladığınızda ilgili listeye gidersiniz.

### 2.3 Bugünün programı

Tabloda her ders için saat, havuz, kulvar, eğitmen ve `kayıtlı/kapasite` bilgisi yer alır. Yoklaması alınmış dersler ayrı bir rozetle işaretlenir; böylece eksik kalan dersi tek bakışta görürsünüz. Satıra tıklayarak ders detayına ve oradan yoklama ekranına geçebilirsiniz.

### 2.4 Grafikler

- **Gelir eğilimi** — son 30 günün günlük net tahsilatı.
- **Saatlik havuz yoğunluğu** — hangi saatlerde havuzun ne kadar dolu olduğunu gösterir; boş saatleri değerlendirmek için kullanın.
- **Devam eğilimi** ve **seviye dağılımı** — son 30 günün devam oranı ve öğrencilerin yüzme seviyelerine göre dağılımı.

---

## 3. Öğrenci Yönetimi

### 3.1 Yeni öğrenci ekleme

1. Sol menü → **Öğrenciler**. (Kısayol: `Ctrl+K` → "Yeni öğrenci")
2. Sağ üstteki **Yeni Öğrenci** düğmesine basın.
3. Formu doldurun:

| Alan | Zorunlu | Açıklama |
|------|:-------:|----------|
| Ad | ✔ | En fazla 80 karakter. |
| Soyad | ✔ | En fazla 80 karakter. |
| Doğum tarihi | – | Gelecek bir tarih girilemez; yaş bu alandan hesaplanır. |
| Cinsiyet | – | Kadın / Erkek / Belirtilmemiş. |
| Öğrenci numarası | – | **Boş bırakın**: sistem `OGR00001` biçiminde otomatik üretir. |
| Telefon / E-posta | – | Öğrencinin kendi iletişim bilgisi (yetişkin öğrenciler için). |
| Adres | – | En fazla 400 karakter. |
| Acil durum kişisi / telefonu | – | Kaza ve rahatsızlık durumunda aranacak kişi. |
| Yüzme seviyesi | ✔ (varsayılan) | Başlangıç · Temel · Orta · İleri · Yarışma · Elit. |
| Durum | ✔ (varsayılan) | Aktif · Pasif · Deneme · Donduruldu · Ayrıldı. |
| Grup | – | Sonradan da atanabilir. |
| Birincil eğitmen | – | Raporlarda ve filtrelerde kullanılır. |
| Hedefler | – | Serbest metin (örn. "50 m serbest tekniği"). |
| Notlar | – | Genel not. |
| Sağlık notu | – | **Hassas alan**: yalnızca `student:read_sensitive` yetkisi olanlar görebilir. |
| Özel ihtiyaç | – | Hassas alan; adaptif yüzme planlamasında kullanılır. |
| KVKK açık rıza | – | İşaretlenmezse CAIO denetim modülü kaydı eksik olarak raporlar. |

4. **Kaydet**'e basın. Kayıt sonrası öğrenci profili açılır.

> **Kayıt tarihi** boş bırakılırsa bugünün tarihi kullanılır. Öğrenci 18 yaşından küçükse mutlaka bir veli bağlayın (bkz. bölüm 4).

### 3.2 Arama ve filtreleme

Öğrenciler listesinde şu filtreler vardır:

- **Arama kutusu** — ad, soyad, öğrenci numarası, telefon ve e-postada arar.
- **Durum** — aktif / pasif / deneme / donduruldu / ayrıldı.
- **Yüzme seviyesi**
- **Grup**
- **Eğitmen**
- **Yaş aralığı** — en küçük ve en büyük yaş.
- **Kayıt tarihi aralığı**

Filtreler birlikte çalışır. Liste sayfalıdır; sayfa boyutu ve sıralama sütun başlıklarından değiştirilir. Sonuç boş geliyorsa önce **Filtreleri temizle** bağlantısına basın.

### 3.3 Öğrenci profili sekmeleri

| Sekme | İçerik |
|-------|--------|
| **Genel** | Kimlik ve iletişim bilgileri, seviye, grup, eğitmen, bağlı veliler, aktif üyelik özeti, devam oranı, açık bakiye, kişisel rekor sayısı. |
| **Yoklama** | Öğrencinin devam kayıtları ve devam oranı özeti (varsayılan son 90 gün). |
| **Üyelik** | Geçmiş ve güncel üyelikler; kalan ders hakkı, kullanım oranı, dondurma kayıtları. |
| **Ödemeler** | Tahsilatlar, fatura eşleşmeleri, iadeler. |
| **Performans** | Derece kayıtları, kişisel rekorlar, gelişim grafiği. |
| **Zaman çizelgesi** | Kayıt, ders, ödeme ve üyelik hareketlerinin kronolojik dökümü. |

Sekmeler yetkiye bağlıdır: finans yetkiniz yoksa *Ödemeler*, performans yetkiniz yoksa *Performans* sekmesi görünmez.

### 3.4 Düzenleme

Profildeki **Düzenle** düğmesi aynı formu doldurulmuş hâlde açar. Değiştirdiğiniz alanlar denetim kaydına "önceki değer → yeni değer" biçiminde yazılır.

### 3.5 Pasife alma (silme)

Öğrenciler listesinde **Sil** işlemi varsayılan olarak kaydı **silmez**:

- Öğrencinin durumu **Pasif** yapılır ve **ayrılış tarihi** bugün olarak işaretlenir.
- Geçmiş dersler, yoklamalar, ödemeler ve performans kayıtları korunur; raporlar tutarlı kalır.
- Kaydı geri getirmek için öğrenciyi düzenleyip durumunu **Aktif** yapmanız yeterlidir.

Kalıcı silme yalnızca `student:delete` yetkisiyle ve özel bir onayla yapılır; bu işlem **geri alınamaz** ve öğrenciye bağlı tüm kayıtları etkiler. Günlük operasyonda pasife alma tercih edilmelidir.

---

## 4. Veli Yönetimi

### 4.1 Veli ekleme

1. Sol menü → **Veliler** → **Yeni Veli**.
2. Alanlar:

| Alan | Zorunlu | Açıklama |
|------|:-------:|----------|
| Ad / Soyad | ✔ | |
| Yakınlık | ✔ (varsayılan "veli") | Anne, baba, veli, büyükanne/büyükbaba, kardeş, diğer. |
| Telefon | ✔ | En az 5 karakter; bildirim ve acil durum iletişiminde esas alınır. |
| İkinci telefon | – | |
| E-posta | – | Portal hesabı açılacaksa gereklidir. |
| Adres / Meslek / Notlar | – | |
| Bağlanacak öğrenciler | – | Kayıt sırasında birden fazla öğrenci seçilebilir. |
| Portal kullanıcısı oluştur | – | İşaretlenirse veliye "Veli" rolünde bir giriş hesabı açılır. |

3. **Kaydet**.

**Bir veli birden fazla öğrenciye bağlanabilir.** Kardeşler için ayrı veli kaydı açmayın; mevcut veliyi ikinci öğrenciye de bağlayın.

### 4.2 Öğrenciye bağlama

Öğrenci profili → **Veliler** bölümü → **Veli bağla**. Bağlama sırasında üç işaret vardır:

| İşaret | Anlamı |
|--------|--------|
| **Birincil veli** | Acil durum ve iletişim listelerinde ilk sırada gösterilir. |
| **Öğrenciyi teslim alabilir** | Ders sonrası teslim yetkisi. |
| **Fatura muhatabı** | Finans yazışmalarında esas alınan kişi. |

Bağlantıyı kaldırmak veli kaydını silmez; yalnızca öğrenci–veli ilişkisini kaldırır.

### 4.3 Veli portalı

Veli rolüne sahip bir hesapla giriş yapıldığında portal görünümü açılır. Veli **yalnızca kendi çocuklarının** verisini görür; bu kısıt satır bazlı erişim kapsamıyla veritabanı sorgusu düzeyinde uygulanır. Portalda gösterilenler:

- Yaklaşan dersler ve ders saatleri,
- Son yoklama kayıtları ve devam oranı,
- Aktif üyelik, kalan ders hakkı ve bitiş tarihi,
- Ödeme geçmişi ve açık bakiye,
- Performans dereceleri ve kişisel rekorlar,
- Kendisine gönderilen bildirimler.

Veli hiçbir kaydı değiştiremez; portal salt görüntülemedir.

---

## 5. Eğitmen Yönetimi

### 5.1 Eğitmen ekleme

1. Sol menü → **Eğitmenler** → **Yeni Eğitmen**.
2. Ad, soyad ve unvan girin. **Personel numarası boş bırakılırsa** `EGT0001` biçiminde otomatik üretilir.
3. Uzmanlık alanlarını seçin (bebek yüzme, çocuk yüzme, adaptif yüzme, yarışma antrenörlüğü, kondisyon vb.). Uzmanlıklar ders ataması yaparken filtre olarak kullanılır.
4. İletişim bilgilerini ve işe başlama tarihini girin, **Kaydet**.

### 5.2 Sertifikalar

Eğitmen detayında **Sertifikalar** bölümünden belge ekleyin:

| Alan | Açıklama |
|------|----------|
| Sertifika adı | Örn. "TYF 1. Kademe Antrenörlük", "Cankurtaran", "İlk Yardım". |
| Veren kurum | |
| Veriliş tarihi | |
| **Geçerlilik bitişi** | Boş bırakılabilir; girilirse süresi dolan sertifikalar listede uyarı rengiyle işaretlenir. |
| Belge bağlantısı | Taranmış belgenin adresi. |

Süresi dolmuş sertifikalar CAIO denetiminde de bulgu olarak raporlanır.

### 5.3 Müsaitlik

**Müsaitlik** sekmesinde haftalık çalışma saatlerini tanımlarsınız: gün (Pazartesi = 0 … Pazar = 6), başlangıç saati, bitiş saati. Aynı gün için birden fazla aralık girilebilir (örn. 09:00–12:00 ve 17:00–21:00).

Müsaitlik dışına ders atarsanız sistem çakışma denetiminde **uyarı** üretir; kayıt engellenmez ama bilerek yaptığınızı görmüş olursunuz.

### 5.4 İzin

**İzinler** sekmesinden başlangıç–bitiş tarihi ve gerekçe girilerek izin kaydı açılır. İzinli tarihlerde o eğitmene ders atanmaya çalışılırsa çakışma denetimi **sarı uyarı** verir (engelleyici değildir).

### 5.5 İş yükü

Eğitmenler ekranındaki **İş Yükü** görünümü, seçtiğiniz tarih aralığında eğitmen başına toplam ders sayısı, toplam saat ve doluluk dağılımını gösterir. Ders dağılımını dengelemek ve fazla mesai riskini görmek için kullanın.

### 5.6 Pasife alma

Eğitmen listesindeki **Sil** işlemi eğitmeni **pasife alır**; geçmiş ders ve yoklama kayıtları korunur. Pasif eğitmen yeni ders atamalarında listelenmez.

---

## 6. Havuz ve Kulvar

### 6.1 Havuz tanımlama

1. Sol menü → **Havuzlar** → **Yeni Havuz**.
2. Alanlar:

| Alan | Açıklama |
|------|----------|
| Havuz adı | Örn. "Ana Havuz", "Öğretim Havuzu". |
| Uzunluk (m) | **25 m / 50 m** seçimi performans kayıtlarındaki kısa/uzun kulvar ayrımını belirler. |
| Genişlik / derinlik | Bilgi amaçlı; kapasite hesabında kullanılmaz. |
| Kulvar sayısı | Bu sayıya göre kulvarlar oluşturulur. |
| Açılış / kapanış saati | Ders planlarken "çalışma saati dışı" uyarısının eşiğidir. |
| Kapalı havuz / ısıtmalı | Bilgi alanı. |
| Su sıcaklığı / hava sıcaklığı | Bilgi alanı. |
| Durum | Faal · Bakımda · Kapalı. |

### 6.2 Kulvar düzenleme

Havuz detayındaki **Kulvarlar** bölümünden her kulvara numara, ad ve kullanım amacı (Eğitim, Serbest, Yarışma vb.) verebilirsiniz. Kullanılmayan kulvarı **pasife alın**; pasif kulvarlar ders atamasında ve doluluk hesabında dikkate alınmaz.

### 6.3 Su kalitesi kaydı

Havuz detayı → **Su Kalitesi** → **Ölçüm Ekle**. Girilen değerler geçmişe dönük izlenir ve grafikte gösterilir.

| Ölçüm | Kabul aralığı | Aralık dışında ne olur? |
|-------|---------------|-------------------------|
| **pH** | 6.8 – 7.6 | Sistem otomatik **uyarı bildirimi** üretir. |
| **Klor (ppm)** | 0.5 – 3.0 | Sistem otomatik **uyarı bildirimi** üretir. |
| Bulanıklık (NTU) | en fazla 0.5 | Kayıt tutulur. |
| Sıcaklık | – | Kayıt tutulur. |

Bildirim, havuz teknik personeli ve yöneticilere düşer; Bildirimler ekranından görülebilir.

### 6.4 Bakım kaydı

Havuz detayı → **Bakım** → **Bakım Planla**. Başlangıç–bitiş tarihi, bakım türü ve açıklama girilir.

Bakım tarihlerinde o havuza ders açılmaya çalışılırsa çakışma denetimi **engelleyici hata** verir. Bakımı iptal etmek veya bitişini öne çekmek için bakım kaydını güncelleyin.

### 6.5 Tatil günleri

*Havuzlar* modülü altındaki **Tatil Takvimi**'ne resmî tatiller ve okulun kapalı olduğu günler eklenir. "Kapalı" işaretli tatiller, tekrarlanan ders serisi üretilirken atlanır (bkz. bölüm 8).

---

## 7. Ders Oluşturma

### 7.1 Tekil ders açma

1. **Takvim** ekranını açın (veya `Ctrl+K` → "Yeni ders").
2. Sağ üstteki **Yeni Ders** düğmesine basın.
3. Formu doldurun:

| Alan | Zorunlu | Açıklama |
|------|:-------:|----------|
| Ders başlığı | ✔ | Takvimde görünen ad. |
| Ders türü | ✔ | 13 tür: Grup, Özel, Çocuk, Bebek, Yetişkin, Başlangıç, Orta, İleri, Yarışma Takımı, Adaptif, Kondisyon, Deneme, Telafi. |
| Havuz | ✔ | Havuz seçilince kulvar listesi güncellenir. |
| Kulvar | – | Boş bırakılırsa ders belirli bir kulvara bağlanmaz. |
| Eğitmen | – | Boş bırakılabilir, sonradan atanabilir. |
| Grup | – | Grup seçmek öğrenci kaydını kolaylaştırır. |
| Başlangıç / bitiş | ✔ | Bitiş başlangıçtan sonra olmalı; bir ders **en fazla 8 saat** sürebilir. |
| Kapasite | ✔ (varsayılan 10) | 1 ile 100 arası. |
| Ücret | – | Özel ders ve tekil satışlar için. |
| Renk | – | Takvimde ayırt etmek için. |

4. **Kaydet**'e basın.

### 7.2 Çakışma uyarılarını okuma

Kaydet'e bastığınızda program **önce çakışma denetimi** yapar, sonra kaydeder. İki tür sonuç görebilirsiniz:

**Kırmızı (engelleyici) çakışmalar — ders kaydedilmez:**

| Tür | Anlamı |
|-----|--------|
| **Eğitmen** | Aynı eğitmen o saat aralığında başka bir derste. |
| **Kulvar** | Aynı kulvarda o saat aralığında başka bir ders var. |
| **Öğrenci** | Derse eklenen bir öğrenci aynı saatte başka bir derse kayıtlı. |
| **Havuz bakımı** | Seçtiğiniz tarihte havuz bakım kaydı var. |
| **Saat aralığı** | Bitiş saati başlangıçtan önce/eşit. |

**Sarı (bilgilendirici) uyarılar — kayıt engellenmez:**

| Tür | Anlamı |
|-----|--------|
| **Eğitmen izni** | Eğitmen o tarihlerde izinli. |
| **Çalışma saati** | Ders, havuzun açılış–kapanış saatleri dışında. |
| **Tatil günü** | O gün tatil takviminde tanımlı. |

Uyarı listesinde çakışan dersin adı, saati ve ilgili kişi/kulvar adı yazar. Çakışmayı gidermek için saati, kulvarı veya eğitmeni değiştirip tekrar **Kaydet**'e basın.

> Bitişik dersler çakışma sayılmaz: 14:00–15:00 ile 15:00–16:00 arasında çakışma yoktur.

### 7.3 "Yine de oluştur"

Engelleyici bir çakışma bulunduğunda kaydet düğmesi **"Yine de oluştur"** düğmesine dönüşür. Bu düğme çakışma denetimini bilerek geçer.

- Yalnızca gerçekten üst üste ders yapılacaksa kullanın (örn. iki eğitmenin aynı kulvarda ortak yürüttüğü telafi seansı).
- Bu seçim **denetim kaydına yazılır**; kimin, ne zaman, hangi çakışmayı geçtiği geriye dönük görülebilir.
- Çakışmayı geçmek çakışmayı ortadan kaldırmaz; kulvar ve eğitmen gerçekte hâlâ meşguldür.

### 7.4 Öğrenci kaydetme

Ders oluşturulduktan sonra **Dersler** ekranından derse öğrenci eklersiniz. Ekleme sırasında iki denetim çalışır:

1. **Kapasite** — kapasite dolmuşsa öğrenci eklenmez.
2. **Öğrenci çakışması** — öğrencinin aynı saatte başka dersi varsa uyarı verilir.

Öğrenciyi dersten çıkarmak için kayıt satırındaki kaldır işaretini kullanın.

### 7.5 Ders iptali

Takvimde derse tıklayın → **Dersi İptal Et** → **iptal gerekçesi zorunludur**. İptal edilen ders:

- takvimde üstü çizili ve soluk görünür,
- silinmez; geçmiş raporlarda yerinde kalır,
- çakışma denetiminde artık meşgul sayılmaz.

Dersi tamamen silmek (`Dersler` ekranındaki **Sil**) yalnızca yanlışlıkla açılmış, hiç kullanılmamış dersler için düşünülmelidir.

---

## 8. Tekrarlanan Ders (Seri)

Aynı programın haftalarca tekrar ettiği durumlarda tek tek ders açmak yerine **seri** oluşturun.

1. **Takvim** → **Tekrarlanan Ders** düğmesi (yetki: `lesson:schedule`).
2. Formu doldurun:

| Alan | Açıklama |
|------|----------|
| Başlık | Üretilecek tüm derslerin ortak adı. |
| Ders türü | 13 türden biri. |
| Havuz / kulvar / eğitmen / grup | Serideki tüm derslere uygulanır. |
| **Haftanın günleri** | Gün düğmelerine tıklayarak seçin. Varsayılan: Pazartesi, Çarşamba, Cuma. En az bir gün seçilmelidir. |
| Başlangıç / bitiş saati | Örn. 17:00 – 18:00. Bitiş, başlangıçtan sonra olmalı. |
| Başlangıç / bitiş tarihi | Serinin kapsadığı dönem. **En fazla 400 gün**. |
| Kapasite | Her ders için ayrı ayrı geçerlidir. |
| **Tatilleri atla** | Varsayılan **açık**. Açıkken tatil takviminde "kapalı" işaretli günlerde ders üretilmez. |
| **Çakışmaları zorla** | Varsayılan kapalı. Kapalıyken çakışan tarihler **atlanır**; açıkken çakışsa bile ders üretilir. |

3. **Kaydet**'e basın.

### Sonucun okunması

İşlem bittiğinde bir bildirim çıkar: *"N ders oluşturuldu"*. Sistem:

- seçtiğiniz gün ve tarih aralığındaki tüm tarihleri üretir,
- tatilleri (seçenek açıksa) çıkarır,
- kalan her tarih için **tek tek çakışma denetimi** yapar,
- çakışan tarihleri **atlar** ve bunları ayrı bir uyarı bildirimi olarak Bildirimler ekranına düşürür.

Yani "20 tarih ürettim ama 18 ders oluştu" durumu normaldir: 2 tarihte çakışma vardı. Hangi tarihlerin atlandığını **Bildirimler** ekranından görebilirsiniz. Atlanan tarihler için tekil ders açarak boşluğu kapatabilirsiniz.

Seriyi silmek: **Dersler** ekranındaki seri listesinden **Sil**. Silerken "yalnızca gelecekteki dersler" seçeneğini kullanarak geçmiş dersleri koruyabilirsiniz.

---

## 9. Ders Takvimi

**Takvim** ekranı (`/calendar`) dersleri renk kodlu olarak gösterir.

### 9.1 Görünümler

Üst çubuktaki üç düğme: **Gün · Hafta · Ay**

| Görünüm | Nasıl çalışır |
|---------|---------------|
| **Gün** | Tek günün saat çizelgesi. Aynı saatte birden fazla ders varsa yan yana sütunlara yerleşir. |
| **Hafta** | Pazartesi–Pazar, saat ızgarası üzerinde. Varsayılan görünümdür. |
| **Ay** | 7 sütunlu takvim; her hücrede o günün dersleri. Bir güne tıklayınca gün görünümüne geçer. |

**‹** ve **›** düğmeleri dönemi ileri/geri alır, **Bugün** düğmesi bugüne döner.

### 9.2 Filtreler ve renklendirme

- Filtreler: **Havuz**, **Eğitmen**, **Grup**, **Ders türü**. Hepsi birlikte çalışır; **Filtreleri temizle** ile sıfırlanır.
- **Renklendirme** açılır listesi: türe göre · eğitmene göre · havuza göre · gruba göre. Seçime uygun renk açıklaması (lejant) takvimin üstünde çıkar.

Ders kutusunda başlık, saat aralığı, kulvar/havuz, eğitmen ve `kayıtlı/kapasite` bilgisi yer alır (kutu yüksekliği elverdiği ölçüde). İptal edilmiş dersler üstü çizili ve soluk gösterilir.

### 9.3 Ders detayı

Bir derse tıkladığınızda detay penceresi açılır: kayıtlı öğrenci listesi, kulvar, eğitmen, kapasite ve yoklamanın alınıp alınmadığı. Pencere altındaki düğmeler:

- **Yoklama Al** — o dersin yoklama ekranına gider.
- **Dersi İptal Et** — gerekçe girerek iptal eder (yetki: `lesson:write`).

### 9.4 Dersi taşıma

Arayüzde ders kutusunu fare ile sürükleme özelliği bulunmaz. Bir dersin saatini, kulvarını veya eğitmenini değiştirmenin iki yolu vardır:

1. **Dersi iptal edip yeni saatle yeni ders açmak** (öğrenci kaydını yeniden yapmanız gerekir).
2. **Taşıma uç noktasını kullanmak** — API üzerinden çakışma denetiminden geçen taşıma:

```http
POST /api/v1/lessons/{lesson_id}/move
Content-Type: application/json
Authorization: Bearer <erişim jetonu>

{
  "start_at": "2026-09-14T18:00:00",
  "end_at":   "2026-09-14T19:00:00",
  "lane_id": 3,
  "instructor_id": 5,
  "force": false
}
```

`force: false` iken çakışma varsa taşıma reddedilir ve çakışan kayıtlar listelenir; `true` yaparsanız çakışmaya rağmen taşınır ve bu tercih denetim kaydına yazılır.

---

## 10. Kulvar Planlama

**Kulvar Planı** ekranı (`/lane-plan`), bir günün kulvar kullanımını tek tabloda gösterir ve boş yer bulmayı kolaylaştırır.

### 10.1 Günlük plan

1. Üstten **havuz** ve **tarih** seçin.
2. Ekranda **saat × kulvar** ızgarası oluşur. Dolu hücrelerde dersin adı, saat aralığı ve eğitmeni yazar; boş hücreler açık renkte kalır.
3. Bir derse tıklayarak detayını görebilirsiniz.

Bu ekran, "Salı 18:00'de hangi kulvar boş?" sorusunun en hızlı yanıtıdır.

### 10.2 Boş kulvar bulma

**Boş Kulvar** panelinde başlangıç ve bitiş saatini girin. Sistem o aralıkta **hiçbir dersle çakışmayan** kulvarları döndürür:

- boş kulvar sayısı,
- kulvar numaraları ve adları.

Hesaplama yalnızca iptal edilmemiş ve ertelenmemiş dersleri dikkate alır.

### 10.3 Saat önerisi

**Zaman Dilimi Öner** panelinde:

| Alan | Açıklama |
|------|----------|
| Tarih | Ders açmak istediğiniz gün. |
| Süre (dakika) | Varsayılan 60. |
| Eğitmen | Seçilirse yalnızca o eğitmenin de müsait olduğu dilimler önerilir. |

Sistem, havuzun **açılış saatinden kapanış saatine** kadar **30'ar dakikalık adımlarla** ilerler ve her adımda:

- o aralıkta boş kulvar var mı,
- eğitmen seçtiyseniz eğitmenin başka dersi var mı

kontrol eder. Sonuç listesinde her öneri için başlangıç–bitiş saati, boş kulvar sayısı ve kulvar adları görünür. Beğendiğiniz diliminizi not alıp *Takvim* ekranında ders oluştururken kullanın.

---

## 11. Yoklama Alma

### 11.1 Ekrana giriş

Yoklama ekranına iki yoldan gidilir:

- Sol menü → **Yoklama** (varsayılan olarak bugünün dersleri listelenir), veya
- Takvimde derse tıklayıp **Yoklama Al**.

Sol panelde dersler listelenir; yoklaması alınmamış olanlar işaretlidir. Bir derse tıklayınca sağ panelde o dersin **yoklama listesi** açılır.

### 11.2 Manuel işaretleme

Listede her öğrenci için altı durumdan biri seçilir:

| Durum | Ne zaman kullanılır | Ders hakkı düşer mi? |
|-------|---------------------|:--------------------:|
| **Geldi** | Öğrenci derse katıldı. | Evet |
| **Geç Geldi** | Katıldı ama geç. Dakika girebilirsiniz (0–240). | Evet |
| **Gelmedi** | Haber vermeden katılmadı. | Hayır |
| **Mazeretli** | Önceden bildirilmiş devamsızlık. Gerekçe yazabilirsiniz. | Hayır |
| **İptal** | Ders o öğrenci için iptal edildi. | Hayır |
| **Telafi** | Bu ders, başka bir dersin telafisi olarak işleniyor. | Hayır |

Her satıra ayrıca serbest **not** yazılabilir.

### 11.3 Toplu işaretleme

Listenin üstündeki **Tümünü Geldi İşaretle** düğmesi bütün öğrencileri tek tıkla "Geldi" yapar. Sonra yalnızca gelmeyenleri tek tek değiştirmeniz yeterlidir — kalabalık gruplarda en hızlı yöntem budur.

### 11.4 Ders hakkı düşümü

Listenin altındaki **"Ders hakkını düş"** kutusu varsayılan olarak **işaretlidir**.

- İşaretliyken kaydettiğinizde, **Geldi** veya **Geç Geldi** işaretlenen her öğrencinin **aktif üyeliğinden bir ders hakkı** düşülür.
- Düşüm **kayıt başına yalnızca bir kez** yapılır: aynı dersin yoklamasını sonradan düzeltseniz bile hak ikinci kez düşmez (çift düşüm koruması).
- Bitiş tarihi en yakın olan aktif üyelikten düşülür.
- Son hak da kullanıldığında üyelik durumu otomatik olarak **Süresi Doldu** olur.
- Sınırsız (aylık/yıllık süre bazlı) paketlerde hak sayısı tutulmaz, düşüm yapılmaz.

Kutuyu **kapatırsanız** devam kaydı tutulur ama üyelik hakkı harcanmaz. Deneme dersleri, ücretsiz seanslar ve kurum içi etkinliklerde kapatın.

Her satırda öğrencinin **kalan ders hakkı** görünür; kaydetmeden önce kontrol edebilirsiniz.

### 11.5 Kaydetme

**Kaydet**'e bastığınızda:

- yoklama kayıtları oluşturulur veya güncellenir,
- ders hakları (seçiliyse) düşülür,
- bitiş saati geçmiş "Planlandı" durumundaki ders otomatik olarak **Tamamlandı** yapılır,
- işlem denetim kaydına yazılır.

Yanlış işaretlemeyi düzeltmek için aynı ekrandan durumu değiştirip tekrar kaydedin; düzeltme de denetim kaydına işlenir.

### 11.6 QR kod ile yoklama

Ders yoğunsa girişte QR okutarak yoklama alabilirsiniz.

1. Yoklama ekranının sağ alt bölümündeki **QR Kodu** kartını açın.
2. **Geçerlilik süresi** seçin: 30, 60, 90 (varsayılan) veya 120 dakika.
3. **QR Üret** düğmesine basın.
4. Ekranda dersin QR içeriği görünür:

```
SWS:ATT:<üretilen-jeton>
```

Bu içeriği kopyalayıp bir QR ekranında/etikette gösterebilirsiniz. Süre dolduğunda jeton geçersiz olur; yeni bir tane üretin.

**Öğrenci kartı:** her öğrenci için profilinden bir kart üretilir. Kart içeriği `SWS:CARD:<kart-kodu>` biçimindedir. Yeni kart üretildiğinde öğrencinin eski kartları otomatik pasife alınır.

**Girişte ne olur?** Öğrenci kartı okutulduğunda:

- yoklama kaydı otomatik oluşturulur,
- ders başlangıcından **10 dakikadan fazla** geçmişse durum **Geç Geldi** olur ve gecikme dakikası yazılır; değilse **Geldi**,
- ders hakkı düşülür,
- aynı öğrenci ikinci kez okutursa "zaten kaydedilmiş" hatası döner.

### 11.7 Telafi dersi

Gelmeyen veya mazeretli bir öğrenciye telafi tanımlamak için:

1. Öğrencinin yoklama satırında **Telafi Ata**'yı seçin.
2. Telafi olarak kullanılacak dersi listeden seçin.
3. Onaylayın.

Sonuç:

- Telafi kaydı orijinal yoklamaya bağlanır; öğrenci geçmişinde izlenir.
- Öğrenci, seçtiğiniz derse "Telafi dersi" notuyla otomatik kaydedilir (zaten kayıtlıysa tekrar eklenmez).
- Telafi yalnızca durumu **Gelmedi** veya **Mazeretli** olan kayıtlar için tanımlanabilir; "Geldi" işaretli bir kayda telafi atanamaz.

---

## 12. Üyelik ve Paket

### 12.1 Paketler

**Üyelikler → Paketler** sekmesinde satılabilir paketler tanımlıdır. Kurulumla birlikte gelen varsayılan paketler:

| Paket | Tür | Ders adedi | Süre | Fiyat |
|-------|-----|-----------:|-----:|------:|
| 4 Ders | Ders paketi | 4 | 60 gün | 1.600 |
| 8 Ders | Ders paketi | 8 | 90 gün | 3.000 |
| 12 Ders | Ders paketi | 12 | 120 gün | 4.200 |
| Aylık Sınırsız | Aylık | sınırsız | 30 gün | 3.500 |
| 3 Aylık | 3 aylık | 36 | 90 gün | 9.500 |
| 6 Aylık | 6 aylık | 72 | 180 gün | 18.000 |
| Yıllık | Yıllık | 144 | 365 gün | 33.000 |
| Özel Ders 10'lu | Özel ders | 10 | 120 gün | 9.000 |
| Deneme Dersi | Deneme | 1 | 14 gün | 0 |

Fiyatlar kurumun para birimindedir ve düzenlenebilir. Yeni paket eklerken ders adedi, geçerlilik süresi (gün), fiyat ve **azami dondurma günü** (varsayılan 30) belirlenir.

### 12.2 Üyelik oluşturma

1. **Üyelikler** → **Yeni Üyelik** (veya `Ctrl+K` → "Yeni üyelik").
2. Alanlar:

| Alan | Açıklama |
|------|----------|
| Öğrenci | Zorunlu. |
| Paket | Zorunlu. |
| Başlangıç tarihi | Boş bırakılırsa bugün. **Bitiş tarihi paket süresine göre otomatik hesaplanır.** |
| İndirim tutarı | Kardeş indirimi, kampanya vb. |
| İndirim gerekçesi | Rapora yansır; boş bırakmayın. |
| Otomatik yenileme | İşaretlenirse takip listesinde ayrıca gösterilir. |
| **Ödeme oluştur** | İşaretlenirse üyelikle birlikte tahsilat kaydı da açılır. |
| Ödeme tutarı | Boş bırakılırsa paket fiyatından indirim düşülerek hesaplanır. |
| Ödeme yöntemi | Nakit · Kredi Kartı (POS) · Havale/EFT · Online · Diğer. |

3. **Kaydet**.

Üyelik açıldığında öğrencinin toplam ders hakkı paketten gelir; her yoklamada bir azalır.

### 12.3 Dondurma

Hastalık, tatil veya sakatlık durumunda üyelik dondurulur.

1. Üyelik satırında **Dondur**.
2. **Başlangıç** ve **bitiş tarihi** girin (bitiş, başlangıçtan önce olamaz). Gerekçe yazın.
3. Onaylayın.

Sonuç: dondurulan gün sayısı kadar **bitiş tarihi ileriye ötelenir**, üyelik durumu **Dondurulmuş** olur. Paketin azami dondurma günü aşılamaz.

**Dondurmayı kaldır** işlemi üyeliği kaldığı yerden devam ettirir.

### 12.4 Yenileme

Süresi dolmuş veya dolmak üzere olan üyelikte **Yenile**:

- aynı paketle veya **farklı bir paketle** yenileyebilirsiniz,
- başlangıç tarihi ve indirim girilebilir,
- isterseniz **yeni ödeme kaydı** birlikte oluşturulur,
- yeni dönem başlar, eski üyelik kapanır.

### 12.5 İptal

**İptal** işlemi üyeliği **İptal** durumuna alır. Kayıt silinmez; geçmiş yoklama ve tahsilat ilişkileri korunur.

### 12.6 Takip listeleri

| Liste | Ne gösterir |
|-------|-------------|
| **Süresi dolacak üyelikler** | Varsayılan olarak 14 gün içinde bitecek aktif üyelikler. |
| **Ders hakkı azalanlar** | Kalan hakkı eşiğin (varsayılan 2) altına düşen üyelikler. |

Bu iki listeyi haftada en az bir kez kontrol edin; yenileme görüşmelerinin zamanlaması buradan çıkar.

---

## 13. Ödeme Alma

### 13.1 Tahsilat kaydı

1. **Finans** ekranı → **Yeni Ödeme** (veya `Ctrl+K` → "Yeni ödeme").
2. Alanlar:

| Alan | Zorunlu | Açıklama |
|------|:-------:|----------|
| Öğrenci | – | Boş bırakılabilir (kurum dışı tahsilatlar için). |
| Üyelik | – | Seçilirse ödeme o üyelikle ilişkilendirilir. |
| Fatura | – | Seçilirse faturanın ödenen tutarı ve bakiyesi otomatik güncellenir. |
| Tutar | ✔ | Sıfırdan büyük olmalı. |
| Para birimi | ✔ | Varsayılan kurum para birimi. |
| Yöntem | ✔ | Nakit · Kredi Kartı (POS) · Havale/EFT · Online · Diğer. |
| Ödeme tarihi | – | Boş bırakılırsa bugün. |
| Referans | – | Dekont / işlem numarası. |
| Açıklama | – | Serbest metin. |

3. **Kaydet**. Fiş numarası `FIS000001` biçiminde **otomatik** üretilir.

Yöntem alanı gün sonu ve tahsilat raporlarında kırılım olarak kullanılır; doğru seçmek raporun doğruluğunu belirler.

### 13.2 Fatura

**Finans → Faturalar → Yeni Fatura**: öğrenci, üyelik, düzenleme tarihi, **vade tarihi**, ara toplam, indirim ve vergi girilir. Toplam tutar hesaplanır; ödeme geldikçe **ödenen tutar** ve **bakiye** güncellenir. Vadesi geçmiş ve bakiyesi kapanmamış faturalar "Gecikmiş" olarak işaretlenir ve kontrol panelindeki uyarıya düşer.

Fatura numarası otomatik üretilir; ön eki (varsayılan `FT`) yönetici ayarlarından değiştirilebilir.

### 13.3 İade

1. Ödeme satırında **İade**.
2. **Tutar** (sıfırdan büyük) ve **gerekçe** (en az 3 karakter) **zorunludur**.
3. Onaylayın.

Orijinal ödeme **silinmez**; iade ayrı bir hareket olarak eklenir ve ödemenin net tutarı azalır. Böylece kasa hareketleri geriye dönük izlenebilir kalır.

### 13.4 Ödeme iptali

**Ödeme İptal** işlemi kaydı iptal durumuna alır. Yanlış girilen kayıtlar için kullanın; işlem denetim kaydına yazılır.

### 13.5 Bekleyen alacaklar

**Finans → Bekleyen Alacaklar** ekranı açık tutarları yaşlandırma gruplarında listeler:

| Grup | Anlamı |
|------|--------|
| Güncel | Vadesi henüz gelmemiş. |
| 1–30 gün | 1 ile 30 gün arasında gecikmiş. |
| 31–60 gün | |
| 60+ gün | En yüksek riskli grup. |

Aramaya bu listenin **en alttaki grubundan** başlayın. Liste öğrenci, veli iletişim bilgisi ve tutarla birlikte gelir; "Bekleyen Alacak Raporu" olarak dışa aktarılabilir (bkz. bölüm 16).

### 13.6 Giderler ve indirimler

- **Giderler**: başlık, kategori (personel, kira, elektrik/su, havuz kimyasalı, bakım, ekipman, pazarlama, vergi, sigorta, diğer), tutar, tarih, ödeme yöntemi, tedarikçi ve fatura referansı ile kaydedilir. Aylık gider dağılımı grafikte gösterilir.
- **İndirimler**: kod, ad, yüzde **veya** sabit tutar, geçerlilik tarihleri ve azami kullanım sayısı ile tanımlanır; üyelik açarken listeden seçilir.

---

## 14. Performans Kaydı

### 14.1 Derece girme

1. Sol menü → **Performans** → **Yeni Kayıt** (veya `Ctrl+K` → "Performans kaydı").
2. Alanlar:

| Alan | Zorunlu | Açıklama |
|------|:-------:|----------|
| Sporcu | ✔ | |
| Stil | ✔ | Serbest · Sırtüstü · Kurbağalama · Kelebek · Karışık. |
| Mesafe (m) | ✔ | 10–10.000 m. Standart mesafeler: 25, 50, 100, 200, 400, 800, 1500. |
| Kulvar tipi | ✔ | Kısa (25 m havuz) / Uzun (50 m havuz). |
| **Derece** | ✔ | Aşağıdaki biçimlerden biri. |
| Ölçüm tarihi | ✔ | |
| Yarışma kaydı mı? | – | İşaretlenirse kişisel rekor hesabında yarışma derecesi sayılır. |

**Derece biçimi** — üç yazım da kabul edilir:

```
1:35.12     → 1 dakika 35,12 saniye  (önerilen)
95.12       → 95,12 saniye
1.35.12     → 1 dakika 35,12 saniye
```

Virgül de nokta gibi kabul edilir (`1:35,12`). Derece saniyeye çevrilerek saklanır; ekranda yine `1:35.12` biçiminde gösterilir. 60 saniyenin altındaki dereceler `32.45` biçiminde görünür.

### 14.2 Split ve ek ölçümler

Bu alanlar isteğe bağlıdır; girildiğinde analiz ekranlarında ayrı grafiklerde gösterilir.

| Alan | Aralık | Açıklama |
|------|--------|----------|
| **Split süreleri** | – | Ara dereceler; her biri derece biçiminde, virgülle ayrılmış: `27.10, 29.40, 30.20` |
| Kulaç sayısı | 0–1000 | Toplam kulaç. |
| Kulaç frekansı (stroke rate) | 0–200 | Dakikadaki kulaç. |
| Çıkış reaksiyon süresi | 0–10 sn | |
| Dönüş süresi | 0–60 sn | |
| Ortalama nabız | 30–240 | |
| Algılanan zorluk | 1–10 | Sporcunun kendi değerlendirmesi. |
| Eğitmen / ders | – | Kaydın hangi antrenmanda alındığı. |
| Not | – | |

### 14.3 Kişisel rekor takibi

Yeni derece, aynı **stil + mesafe + kulvar tipi** kombinasyonundaki önceki en iyi dereceden hızlıysa sistem kaydı **otomatik olarak kişisel rekor** işaretler. Antrenman ve yarışma dereceleri ayrı değerlendirilir; antrenmanda kırılan bir derece yarışma rekorunun yerine geçmez.

Kişisel rekorlar öğrenci profilinin *Performans* sekmesinde ve performans ekranındaki **Kişisel Rekorlar** tablosunda listelenir.

### 14.4 Gelişim grafiğini okuma

Sporcu özeti ekranında her etkinlik (örn. "50 m Serbest, kısa kulvar") için şu sayılar **veritabanından hesaplanır** — tahmin veya yapay zekâ çıktısı değildir:

| Gösterge | Anlamı |
|----------|--------|
| En iyi / en kötü derece | Dönemdeki uç değerler. |
| Ortalama · medyan | Medyan uç değerlerden daha az etkilenir; ikisi çok farklıysa dağılım çarpıktır. |
| Standart sapma | Küçükse derece istikrarlı, büyükse dalgalı demektir. |
| %25 / %75 persentil | Derecelerin ortadaki yarısının hangi aralıkta kaldığı. |
| İlk → son derece | Dönemin başındaki ve sonundaki derece. |
| Gelişim (sn / %) | İlk ve son derece arasındaki fark. **Negatif süre = hızlanma = iyi.** |
| 30 / 90 günlük değişim | Kısa ve orta vadeli seyir. |
| **Eğilim** | `improving` (gelişiyor) · `stable` (sabit) · `declining` (geriliyor). |
| Hareketli ortalama | Grafikteki ikinci çizgi; tek seferlik iyi/kötü dereceleri yumuşatır. |

**Grafiği okuma kuralı:** yüzmede **aşağı inen çizgi iyidir** (derece küçülüyor = sporcu hızlanıyor). Kişisel rekorlar grafik üzerinde ayrı işaretle gösterilir.

Ekranda ayrıca:

- **En çok gelişenler** — belirlediğiniz dönemde derecesi en çok iyileşen sporcular,
- **Performansı düşenler** — son dönem ortalaması, önceki döneme göre kötüleşen sporcular,
- **En güçlü / en zayıf stil** — sporcunun stiller arası karşılaştırması,
- **Yarışma hazırlık göstergesi** — yarışma öncesi form durumu

listelenir.

---

## 15. Yarışma Yönetimi

### 15.1 Yarışma oluşturma

1. Sol menü → **Yarışmalar** → **Yeni Yarışma**.
2. Alanlar: ad, düzenleyen kurum, yer, **seviye** (Kulüp · İl · Bölge · Ulusal · Uluslararası), başlangıç–bitiş tarihi, **son kayıt tarihi**, açıklama.
3. **Kaydet**.

### 15.2 Etkinlik ekleme

Yarışma detayında **Etkinlik Ekle**: **stil + mesafe + kulvar tipi + cinsiyet/yaş kategorisi**. Örnek: "50 m Serbest – Kız – 11-12 yaş". Bir yarışmaya istediğiniz kadar etkinlik eklenebilir.

### 15.3 Sporcu kaydı

Etkinlik satırında **Sporcu Kaydet**: sporcu seçilir ve **seed (kayıt) derecesi** girilir. Seed derecesi seri dağıtımının temelidir; sporcunun o etkinlikteki en iyi derecesini kullanın. Sporcunun sistemde kişisel rekoru varsa öneri olarak gelir.

Son kayıt tarihi geçmiş yarışmalarda kayıt açmadan önce yöneticinize danışın.

### 15.4 Seri (heat) oluşturma

Etkinlik satırında **Seri Oluştur** düğmesi, kayıtlı sporcuları **seed derecelerine göre** otomatik olarak serilere ve kulvarlara dağıtır. Dağıtım standart yüzme kuralına uyar: en hızlı sporcular son seride ve merkez kulvarlarda yer alır.

Sonuç **seri çizelgesi** olarak ekranda görünür: seri numarası, kulvar numarası, sporcu adı ve seed derecesi. Çizelgeyi yazdırıp havuz kenarında kullanabilirsiniz.

### 15.5 Sonuç girme

Yarışma bittikten sonra her kayıt satırına:

| Alan | Açıklama |
|------|----------|
| Derece | `1:02.45` biçiminde. |
| Sıralama | Etkinlikteki final sırası. |
| Madalya | Altın / Gümüş / Bronz / yok. |
| Diskalifiye | İşaretlenirse **gerekçe zorunludur**. |

Girilen derece kulüp rekoru eşiğini geçerse **kulüp rekoru listesi otomatik güncellenir**.

### 15.6 Raporlar

- **Yarışma sonuç raporu** — tüm etkinliklerin sonuçları, sıralamalar ve madalyalar.
- **Madalya özeti** — seçilen yıl için altın/gümüş/bronz dağılımı ve sporcu bazlı kırılım.
- **Kulüp rekorları** — stil, mesafe ve kulvar tipine göre güncel rekorlar.

---

## 16. Rapor Oluşturma

**Raporlar** ekranı (`/reports`) yalnızca **yetkiniz olan** rapor tanımlarını listeler. Örneğin finans yetkiniz yoksa finans raporları listede görünmez.

### 16.1 Rapor kataloğu

| Rapor | Kategori | Filtreler | Gereken yetki |
|-------|----------|-----------|---------------|
| Günlük Yönetici Raporu | Yönetim | tarih | `report:read` |
| Haftalık Yönetim Raporu | Yönetim | dönem | `report:read` |
| Aylık Yönetim Raporu | Yönetim | dönem | `report:read` |
| Öğrenci Listesi | Öğrenci | grup, durum, seviye | `student:read` |
| Öğrenci Gelişim Raporu | Öğrenci | öğrenci, dönem | `performance:read` |
| Yoklama Raporu | Operasyon | dönem, grup, eğitmen | `attendance:read` |
| Eğitmen İş Yükü Raporu | Personel | dönem | `instructor:read` |
| Havuz Kullanım Raporu | Tesis | dönem, havuz | `pool:read` |
| Kulvar Doluluk Raporu | Tesis | dönem, havuz | `pool:read` |
| Finans Raporu | Finans | dönem | `finance:read` |
| Tahsilat Raporu | Finans | dönem | `finance:read` |
| Bekleyen Alacak Raporu | Finans | – | `finance:read` |
| Üyelik Raporu | Satış | durum | `membership:read` |
| Satış Raporu | Satış | dönem | `finance:read` |
| Performans Raporu | Spor | dönem, öğrenci | `performance:read` |
| Yarışma Raporu | Spor | dönem | `competition:read` |

### 16.2 Adımlar

1. Listeden rapor türünü seçin.
2. **Dönem** seçin: Bugün · Bu hafta · Bu ay · Bu çeyrek · Son 6 ay · Bu yıl · Geçen yıl · Özel aralık. Özel aralıkta başlangıç ve bitiş tarihi girilir.
3. Rapora özgü diğer filtreleri uygulayın (havuz, eğitmen, grup, öğrenci, üyelik durumu).
4. **Rapor dili** seçin (Türkçe / İngilizce) — arayüz diliniz Türkçe kalırken İngilizce rapor üretebilirsiniz.
5. **Önizle**'ye basın. Ekranda satır sayısı, sütunlar, ilk satırlar ve toplamlar görünür. Yanlış filtreyle büyük dosya üretmemek için önizleme adımını atlamayın.
6. Biçimi seçip **Dışa Aktar**'a basın.

### 16.3 Dışa aktarma biçimleri

| Biçim | Ne zaman kullanılır |
|-------|---------------------|
| **PDF** | Yazdırılacak veya paylaşılacak resmî çıktı. "Grafik ekle" seçeneği açıksa grafikler de basılır. |
| **XLSX** | Excel'de üzerinde çalışılacak veri. Sütun genişlikleri otomatik ayarlanır. |
| **CSV** | Başka bir sisteme aktarılacak ham veri. |
| **JSON** | Teknik entegrasyonlar. |

Türkçe karakterler (ç, ğ, ı, ö, ş, ü) tüm biçimlerde korunur. Dosya tarayıcınızın indirme klasörüne iner.

### 16.4 Şablon kaydetme

Sık kullandığınız filtre setini **Şablon Olarak Kaydet** ile adlandırıp saklayın. Bir sonraki sefer **Kayıtlı Şablonlar** listesinden tek tıkla çağırabilirsiniz. Örnek: "Aylık yoklama – Yıldızlar grubu – PDF".

---

## 17. Bildirimler

Bildirim merkezi (`/notifications`) sistemin size ve rolünüze gönderdiği uyarıları toplar. Üst çubuktaki zil ikonunda okunmamış bildirim varsa kırmızı nokta, sol menüde ise sayı rozeti görünür. Sayaç **dakikada bir** tazelenir.

### 17.1 Bildirim türleri

| Tür | Ne zaman üretilir |
|-----|-------------------|
| Üyelik bitiyor | Üyelik bitişine 14 gün veya daha az kaldığında. |
| Ödeme gecikti | Fatura vadesi geçtiğinde ve bakiye kapanmadığında. |
| Ders iptal edildi | Bir ders iptal edildiğinde. |
| Eğitmen izni | İzin kaydı ders programını etkilediğinde. |
| Havuz bakımı | Planlı bakım yaklaştığında; su kalitesi limit dışına çıktığında. |
| Performans düşüşü | Sporcunun son dönem derecesi belirgin biçimde kötüleştiğinde. |
| Yaklaşan yarışma | Yarışma tarihi yaklaştığında. |
| AI raporu hazır | Uzun süren bir AI analizi tamamlandığında. |
| Yedekleme sonucu | Zamanlanmış yedekleme tamamlandığında veya başarısız olduğunda. |
| Sistem | Seri ders üretiminde atlanan tarihler gibi genel bilgiler. |
| Deneme dersi | Yaklaşan deneme dersleri. |
| Yeni kayıt | Yeni öğrenci kaydı açıldığında. |

Her bildirimin bir **önem derecesi** vardır: Bilgi · Başarılı · **Uyarı** · **Hata**. Uyarı ve hata bildirimlerini biriktirmeyin.

### 17.2 Kullanım

- Bildirime tıklayınca ilgili kayda gidersiniz (üyelik, fatura, ders vb.).
- **Okundu işaretle** tek bildirimi, **Tümünü okundu işaretle** listenin tamamını kapatır.
- **Yalnızca okunmamışlar** filtresiyle listeyi daraltabilirsiniz.

Bildirim gönderme yetkisi olan kullanıcılar (`notification:send`) belirli kişilere veya rollere duyuru gönderebilir.

---

## 18. Dil Değiştirme ve Tema

### 18.1 Dil

Üst çubuktaki **TR / EN** düğmesi arayüz dilini anında değiştirir; sayfa yenilenmez.

Dil seçimi yalnızca metinleri değil biçimlendirmeyi de etkiler:

| | Türkçe | İngilizce |
|---|--------|-----------|
| Tarih | 18.08.2026 | farklı sıralama |
| Sayı | 1.234,56 | 1,234.56 |
| Para | 1.234,56 ₺ | para birimi ayarına göre |

Tercihiniz hesabınıza kaydedilir; başka bir bilgisayardan giriş yaptığınızda da aynı dille açılır.

**Rapor dili ayrıdır:** rapor dışa aktarma ekranındaki dil seçimi arayüz dilinden bağımsızdır.

### 18.2 Tema

Güneş/ay düğmesi üç durum arasında sırayla geçer:

`Açık → Koyu → Sistem → Açık …`

- **Açık** — parlak ortamlar, gündüz kullanımı.
- **Koyu** — düşük ışıklı ortam; havuz kenarı ve akşam vardiyaları için daha rahattır.
- **Sistem** — Windows'un tema ayarını takip eder.

Tercih hesabınıza kaydedilir.

---

## 19. Klavye Kısayolları

| Kısayol | İşlev | Nerede çalışır |
|---------|-------|----------------|
| `Ctrl+K` (veya `⌘+K`) | Komut paletini açar | Her ekranda |
| `/` | Global aramayı açar | Metin kutusu dışında herhangi bir yerde |
| `↑` `↓` | Komut paletinde gezinme | Komut paleti açıkken |
| `Enter` | Seçili komutu çalıştırır | Komut paleti açıkken |
| `Esc` | Paleti / arama panelini / açık pencereyi kapatır | Her yerde |
| `Tab` / `Shift+Tab` | Form alanları arasında geçiş | Formlarda |
| `Ctrl+P` | Sayfayı yazdır (tarayıcı) — menü ve üst çubuk çıktıya dâhil edilmez | Her ekranda |

> `/` tuşu, imleç bir metin kutusunun içindeyken arama açmaz; normal karakter olarak yazılır.

---

## 20. Sık Sorulan Sorular

**1. Ders kaydedilmiyor, kırmızı bir uyarı çıkıyor. Ne yapmalıyım?**
Çakışma denetimi devrede. Uyarıdaki satırlar hangi eğitmenin, kulvarın veya öğrencinin meşgul olduğunu ve çakışan dersin adını yazar. Saati, kulvarı veya eğitmeni değiştirip tekrar deneyin. Gerçekten üst üste ders yapılacaksa **Yine de oluştur**'u kullanın — bu tercih denetim kaydına yazılır.

**2. Yoklamayı kaydettim ama öğrencinin ders hakkı düşmedi.**
Üç olasılık var: (a) "Ders hakkını düş" kutusu kapalıydı, (b) öğrencinin aktif üyeliği yok, (c) üyelik süre bazlı (aylık/yıllık sınırsız) olduğu için hak sayısı tutulmuyor. Öğrenci profilindeki *Üyelik* sekmesinden kontrol edin.

**3. Aynı dersin yoklamasını iki kez kaydedersem hak iki kez düşer mi?**
Hayır. Ders hakkı kayıt başına yalnızca bir kez düşer; düzeltme yaptığınızda ikinci düşüm olmaz.

**4. Yanlış işaretlediğim yoklamayı nasıl düzeltirim?**
Aynı dersin yoklama ekranını açın, durumu değiştirin ve tekrar kaydedin. Düzeltme denetim kaydına yazılır, kim düzeltti geriye dönük görülür.

**5. Seri oluşturdum ama beklediğimden az ders üretildi.**
Tatil günleri atlanmış veya bazı tarihlerde çakışma çıkmış olabilir. Kaç ders üretildiği işlem sonundaki bildirimde yazar; atlanan tarihlerin listesi **Bildirimler** ekranındaki uyarı bildirimindedir. Atlanan tarihler için tekil ders açabilirsiniz.

**6. Bir öğrenciyi sildim, geri gelir mi?**
Standart silme işlemi öğrenciyi **pasife alır**, kaydı silmez. Öğrenciyi düzenleyip durumunu **Aktif** yapmanız yeterlidir. (Kalıcı silme ayrı bir yetki gerektirir ve geri alınamaz.)

**7. Dereceyi hangi biçimde yazmalıyım?**
`1:35.12` (önerilen), `95.12` veya `1.35.12`. Üçü de aynı süreyi ifade eder. Virgül de kabul edilir.

**8. Gelişim grafiğinde çizgi aşağı iniyor, bu kötü mü?**
Tam tersi. Yüzmede küçük derece iyidir; aşağı inen çizgi sporcunun **hızlandığını** gösterir.

**9. Bir ekran menüde hiç görünmüyor.**
Hesabınızın o modüle yetkisi yok. Adresi elle yazarsanız "erişim reddedildi" ekranı gelir. Yetki gerekiyorsa yöneticinize başvurun.

**10. Öğrencinin sağlık notu alanı "gizli" görünüyor.**
Sağlık notu ve özel ihtiyaç bilgileri ayrı bir yetkiyle (`student:read_sensitive`) korunur. Bu yetki genellikle sağlık personeli, baş antrenör ve adaptif yüzme eğitmenlerinde bulunur.

**11. Üyeliği dondurdum, bitiş tarihi değişmedi gibi görünüyor.**
Bitiş tarihi, dondurma **süresi kadar** ötelenir ve üyelik satırında güncellenir. Listeyi yenileyin; paketin azami dondurma günü aşıldıysa öteleme sınırlanmış olabilir.

**12. QR kodu okuttuk ama "zaten kaydedilmiş" hatası aldık.**
Aynı öğrenci o ders için ikinci kez okuttu. Yoklama zaten alınmış; listeden kontrol edin.

**13. QR kodu çalışmıyor, süresi doldu diyor.**
QR jetonu üretirken seçtiğiniz süre (30/60/90/120 dakika) doldu. Yoklama ekranından yeni bir QR üretin.

**14. Raporu Excel'e aktardım, Türkçe karakterler bozuk çıktı.**
XLSX ve PDF çıktılarında karakterler korunur. CSV'yi Excel ile açarken kodlama olarak **UTF-8** seçin; doğrudan çift tıklamak yerine Excel'de "Veri → Metinden/CSV'den" yolunu kullanın.

**15. Aynı veliye ikinci çocuğu nasıl eklerim?**
Yeni veli kaydı **açmayın**. İkinci öğrencinin profilinden **Veli bağla** ile mevcut veliyi seçin. Bir veli sınırsız sayıda öğrenciye bağlanabilir.

**16. Havuz bakımdayken ders açamıyorum.**
Bakım kaydı engelleyici bir çakışmadır. Bakım tarihini güncelleyin, dersi başka havuza alın veya farklı bir güne planlayın.

**17. Su kalitesi ölçümü girince uyarı bildirimi geldi. Ne anlama geliyor?**
pH 6.8–7.6 veya klor 0.5–3.0 ppm aralığının dışında bir değer girildi. Sistem otomatik olarak ilgili personele bildirim gönderdi; teknik personelle iletişime geçin.

**18. "Oturumunuz sona erdi" uyarısı alıyorum.**
Oturum süresi 120 dakikadır. Tekrar giriş yapın. Sık tekrarlıyorsa yöneticinize bildirin.

---

## 21. Sorun Giderme

### Liste boş geliyor

1. **Filtreleri temizle** bağlantısına basın — çoğu zaman tarih aralığı veya durum filtresi sonucu daraltmıştır.
2. Tarih aralığını genişletin (örn. "Bu ay" yerine "Bu yıl").
3. Arama kutusunda kalmış bir kelime olup olmadığını kontrol edin.

### Ekran açılmıyor / boş beyaz kalıyor

1. Sayfayı yenileyin (`F5`).
2. Konsol penceresinin hâlâ açık olduğundan emin olun; kapandıysa `START_SWIMMING_SCHOOL.bat` ile tekrar başlatın.
3. Sorun sürerse *Ayarlar → Hakkında* ekranındaki sürüm ve veritabanı bilgisiyle birlikte yöneticinize başvurun.

### "Erişim reddedildi" / "Yetkiniz yok"

Hesabınızda o işlem için gereken izin tanımlı değil. Hata mesajında hangi iznin eksik olduğu belirtilir. Yöneticiniz *Ayarlar → Kullanıcılar* ekranından rolünüzü güncelleyebilir.

### Giriş yapamıyorum

| Belirti | Olası neden | Çözüm |
|---------|-------------|-------|
| "Geçersiz kimlik bilgileri" | Yanlış e-posta/parola | Büyük-küçük harfe dikkat edin; Caps Lock kapalı olsun. |
| "Çok fazla deneme" | 8 hatalı denemeden sonra 15 dakikalık kilit veya dakikadaki deneme sınırı | 15 dakika bekleyin ya da yöneticinizden parolanızı sıfırlamasını isteyin. |
| "Hesap pasif" | Hesabınız devre dışı bırakılmış | Yöneticinize başvurun. |

### Ders / üyelik / ödeme kaydedilmiyor

Hata mesajını sonuna kadar okuyun; sistem hangi alanın hatalı olduğunu yazar. Sık görülenler:

- Bitiş saati başlangıçtan önce veya eşit.
- Ders süresi 8 saati aşıyor.
- Kapasite 1–100 aralığının dışında.
- Tutar sıfır veya negatif.
- İade gerekçesi 3 karakterden kısa.
- Dondurma bitiş tarihi başlangıçtan önce.

### Rapor/dışa aktarma çalışmıyor

1. Önce **Önizle**'ye basın; satır sayısı 0 ise filtreleriniz sonucu boşaltmıştır.
2. Çok geniş tarih aralıklarında üretim uzun sürebilir; dönemi daraltıp tekrar deneyin.
3. İndirme başlamıyorsa tarayıcı indirme izinlerini kontrol edin.

### Bildirimler gelmiyor

Bildirimler sistem tarafından tarama sırasında üretilir. Üretim yetkiniz varsa *Bildirimler* ekranındaki tarama işlemini çalıştırın; yoksa yöneticinize haber verin.

### Yapay zekâ analizi hata veriyor

*AI Merkezi* ekranından sağlayıcı **sağlık kontrolünü** çalıştırın. Yerel modelde servis kapalıysa veya seçili model kurulu değilse hata mesajı sebebi açıkça yazar. AI çalışmasa bile **hesaplanmış veri panelleri çalışmaya devam eder**; sayısal analizleriniz etkilenmez.

### Sorun sürüyorsa

Destek isterken şu üç bilgiyi birlikte iletin:

1. *Ayarlar → Hakkında* ekranındaki **sürüm** ve **veritabanı revizyonu**,
2. Hata mesajının **tam metni** (ekran görüntüsü),
3. Sorunun oluştuğu **saat** ve hangi ekranda çalıştığınız.

Yöneticiniz bu bilgilerle `logs/` klasöründeki kayıtlardan olayı bulabilir.

---

*Bu belge sistemin 0.9.0 sürümüne göre hazırlanmıştır. Program içi kılavuz (`/help`) ve Eğitim Merkezi (`/training`) aynı içeriği ekran ekran, adım adım sunar.*
