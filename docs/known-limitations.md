# Bilinen Sınırlar / Known Limitations

Bu dosya, ürünün **yapmadığı** ve **henüz yapmadığı** şeyleri listeler.
README'deki özellik listesini dengelemek için vardır: bir eksiği burada
görmüyorsanız da var olabilir; ama burada yazan her madde doğrulanmıştır.

Ölçüm tarihi: 2026-08-19 · Sürüm: `1.0.0-public`

---

## 1. Mimari sınırlar (tasarım gereği)

| # | Sınır | Ayrıntı |
|---|---|---|
| A-1 | **Çok kiracılı (multi-tenant) değildir** | Hiçbir modelde kurum/şube ayırıcı sütun yoktur ve hiçbir sorguda kiracı süzgeci yoktur. Ürün **tek kurumluk tek kurulum** için tasarlanmıştır. Birden çok kurumun verisini aynı kuruluma koymayın. |
| A-2 | **Tek kullanıcılı masaüstü kurulum varsayılır** | Varsayılan yapılandırma `127.0.0.1` üzerinde SQLite ile çalışır. Ağa açık kurulum için ters vekil, TLS ve gözden geçirilmiş CORS listesi gerekir; bunlar ürünle birlikte gelmez. |
| A-3 | **Yedekler şifrelenmez** | Yedek arşivi düz ZIP'tir. `.env` yedeğe dâhil edilmez, ancak veritabanı dâhildir. Diskin şifrelenmesi kurumun sorumluluğundadır. |
| A-4 | **Yedekleme/geri yükleme yalnızca SQLite** | PostgreSQL'e taşındığında `pg_dump`/`pg_restore` kullanılmalıdır. |
| A-5 | **Oturum iptali (token revocation) yoktur** | JWT süresi dolana kadar geçerlidir; "çıkış" yalnızca istemci tarafındaki belirteci atar ve denetim kaydı üretir. Kısa `ACCESS_TOKEN_EXPIRE_MINUTES` kullanın. |
| A-6 | **Saklama süresi (retention) motoru yoktur** | Süre dolan kişisel veriyi otomatik silen bir bileşen yoktur. Saklama süresi elle yönetilir. |
| A-7 | **Maliyet/token tavanı yoktur** | Bulut sağlayıcı etkinleştirildiğinde harcamayı sınırlayan bir mekanizma yoktur; sınır sağlayıcı hesabından yönetilmelidir. |
| A-8 | **RFID/NFC donanım entegrasyonu yoktur** | Kart/QR ile giriş uçları vardır; fiziksel okuyucu entegrasyonu yoktur. |
| A-9 | **Bulut yedekleme yoktur** | Yedek yalnızca yerel dizine yazılır. |
| A-10 | **Mobil uygulama yoktur** | Arayüz duyarlıdır (responsive) ama yerel bir mobil uygulama yoktur. |
| A-11 | **E-posta/SMS gönderimi yoktur** | Bildirimler uygulama içidir; harici bir gönderim sağlayıcısı bağlı değildir. |

---

## 2. Yapay zekâ ile ilgili sınırlar

| # | Sınır | Ayrıntı |
|---|---|---|
| AI-1 | **Yalnızca 3 sağlayıcı** | LM Studio (yerel), NVIDIA Build (bulut), genel OpenAI-uyumlu uç. Anthropic / Gemini / Azure / Ollama / vLLM bağdaştırıcısı yoktur. |
| AI-2 | **Doğal dilden SQL üretimi yoktur** | CAIO yalnızca ORM toplulaştırmaları kullanır. Bu bilinçli bir tercihtir. |
| AI-3 | **Takma ad alanı 16 bittir** | Takma ad belirteci 4 onaltılık karakterdir; doğum günü sınırına göre ~300 veri sahibinden sonra çakışma olasılığı belirginleşir. Ayrıca takma adların kararlılığı `SECRET_KEY`'in kalıcı olmasına bağlıdır. |
| AI-4 | **Serbest metin taraması sezgiseldir** | `freetext.scan` desen ve sözlük tabanlıdır. Muhafazakâr ayarlanmıştır (şüpheli durumda alanı bildirir) ama sıfır yanlış negatif garantisi vermez. |
| AI-5 | **Sağlayıcı kanıtı elle bakımlıdır** | Bölge/saklama/eğitim bilgileri `hsp/providers.py` içinde kayıtlıdır ve sağlayıcı koşullarını değiştirdiğinde elle güncellenmelidir. |

---

## 3. Kod kalitesi ve araç sınırları

| # | Sınır | Ayrıntı |
|---|---|---|
| Q-1 | **mypy temiz değildir** | `mypy app --ignore-missing-imports` **60 hata** raporlar (17 dosya, 2026-08-19). Bunlar çalışma zamanı hatası değildir ama tip borcudur. CI'da bu adım bilinçli olarak **bloklayıcı değildir** ve adı da bunu söyler. |
| Q-2 | **Semgrep 3 dosyayı tam ayrıştıramıyor** | `.github/workflows/ci.yml` (gömülü `node -e` bloğu), `frontend/src/lib/types.ts` (kısmi ayrıştırma) ve `tools/presentation_content.py` (zaman aşımı). Bu bir kod kusuru değil, tarayıcı sınırıdır; ilgili dosyalar elle gözden geçirilmiştir. |
| Q-3 | **Bandit gürültüsü** | 104 bulgu; 1'i MEDIUM (döngüsel adrese `urlopen`, yanlış pozitif), kalanı LOW. Bunların ~90'ı demo tohumlayıcısındaki `random` kullanımıdır (B311) — sentetik veri için doğru araçtır, kriptografik kullanım yoktur. |
| Q-4 | **Test kapsamı ölçülmemiş eşik yoktur** | 395 test fonksiyonu (parametreleştirme sonrası 533 çalıştırma) geçer; ancak asgari bir kapsam yüzdesi zorlanmaz. |
| Q-5 | **Yük/performans testi yoktur** | Ölçek davranışı hakkında hiçbir iddia yoktur. |
| Q-6 | **Erişilebilirlik denetimi yapılmamıştır** | WCAG uyumu iddia edilmez. |

---

## 4. Sunum ve varlıklar

| # | Sınır | Ayrıntı |
|---|---|---|
| P-1 | **Yayımlanan PDF'ler Calibri ile üretilmiştir** | Calibri tescilli bir Microsoft yazı tipidir. `tools/presentation_theme.py`, kurulu ise önce özgür bir yazı tipini (Inter, Source Sans 3, DejaVu Sans, Noto Sans) seçer; derleme makinesinde bunların hiçbiri kurulu olmadığı için son çareye düşülmüştür. `SWS_PRESENTATION_FONT` ile geçersiz kılınabilir. Bkz. `THIRD_PARTY_NOTICES.md`. |
| P-2 | **PDF/PPTX üretimi Windows + PowerPoint gerektirir** | PPTX üretimi saf Python'dur; PDF/PNG dışa aktarımı COM üzerinden kurulu PowerPoint kullanır. PowerPoint yoksa PPTX üretilir, PDF üretilmez. |
| P-3 | **Ekran yakalama çalışan bir kurulum gerektirir** | `tools/capture_screens.py` derlenmiş arayüz, çalışan backend, Playwright ve **ilk kurulum parolası değiştirilmiş** bir hesap ister. |
| P-4 | **Sunumdaki kişiler kurgusaldır** | Bütün kayıtlar sentetiktir; adlar sabit havuzlardan, telefonlar aranamayan `0000` ön ekiyle üretilir. |

---

## 5. Dürüstlük notu: neyin doğrulanmadığı

* **Üçüncü taraf proje incelemesi.** `THIRD_PARTY_NOTICES.md`, bazı kopyaleft
  ve lisanssız projelerin yalnızca kavramsal olarak incelendiğini, kod düzeyinde
  kullanılmadığını beyan eder. Bu beyan depo içinden **doğrulanamaz**; bir
  beyandır, kanıt değildir. Depoda satır içi (vendored) üçüncü taraf kaynak
  dizini bulunmadığı doğrulanmıştır.
* **"Tamamı geçiyor" ifadesi**, bu depodaki test paketinin bu depodaki kodla,
  CPython 3.11 üzerinde, 2026-08-19 tarihinde çalıştırılmasına dayanır.
  Başka bir ortamda aynı sonucun çıkacağı garanti edilmez.
* **Üretimde çalıştığı iddiası yoktur.** Ürün hiçbir gerçek kurumda üretim
  yükü altında çalıştırılmamıştır.
