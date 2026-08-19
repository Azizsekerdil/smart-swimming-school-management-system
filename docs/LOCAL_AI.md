# Yerel Yapay Zekâ — LM Studio Kılavuzu

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'nin yapay zekâ özelliklerini
kendi bilgisayarınızda çalışan bir dil modeliyle kullanmayı anlatır. Kurulum,
yapılandırma, bağlantı testi, donanım gereksinimleri ve sorun giderme
adımlarının tamamı buradadır.

**Sürüm:** 0.9.0 · **Sağlayıcı adı:** `local` · **Varsayılan uç:**
`http://localhost:1234/v1` · **Varsayılan durum:** Etkin

---

## İçindekiler

1. [LM Studio nedir, neden yerel model](#1-lm-studio-nedir-neden-yerel-model)
2. [Kurulum](#2-kurulum)
3. [Sunucuyu başlatma](#3-sunucuyu-başlatma)
4. [Programı yapılandırma](#4-programı-yapılandırma)
5. [Bağlantı testi](#5-bağlantı-testi)
6. [Donanım gereksinimleri](#6-donanım-gereksinimleri)
7. [Performans ipuçları](#7-performans-i̇puçları)
8. [Sorun giderme](#8-sorun-giderme)
9. [Gizlilik avantajı](#9-gizlilik-avantajı)

---

## 1. LM Studio nedir, neden yerel model

**LM Studio**, açık ağırlıklı dil modellerini kendi bilgisayarınızda
indirip çalıştırmanızı sağlayan bir masaüstü uygulamasıdır. Modeli
yükledikten sonra OpenAI ile aynı şemayı konuşan yerel bir HTTP sunucusu
açar (`/v1/chat/completions`, `/v1/models`). Bu program da tam olarak bu
şemayı kullanır, bu yüzden ek bir bağlayıcı yazmaya gerek yoktur.

Kod tarafındaki karşılığı `LMStudioProvider` sınıfıdır
(`backend/app/services/ai/providers.py`) ve `OpenAICompatibleProvider`
tabanından türer.

### Neden yerel model?

| Konu | Yerel model (LM Studio) | Bulut model |
|------|-------------------------|-------------|
| Veri nereye gider | Bilgisayardan **çıkmaz** | Sağlayıcı sunucularına gider |
| İnternet | Gerekmez | Gerekir |
| Kişisel veri riski | Yok (veri yerelde kalır) | Değerlendirilmeli |
| Maliyet | Elektrik + tek seferlik donanım | Token başına ücret / kota |
| Kota sınırı | Yok | Var |
| Hız | Donanıma bağlı | Genelde daha hızlı |
| Model kalitesi | Donanımın kaldırdığı kadar | Çok büyük modeller erişilebilir |
| Kesinti riski | Kendi bilgisayarınız | Sağlayıcı kesintisi |

Yüzme okulu verisi öğrenci adı, yaş, sağlık notu, veli iletişim bilgisi ve
performans dereceleri içerir. Bu veri türü için varsayılan tercih yerel
modeldir; program da bu nedenle `LOCAL_AI_ENABLED=true` ve
`AI_FALLBACK_CHAIN=local,nvidia` varsayılanlarıyla gelir.

> **Not:** LM Studio kapalıyken program tamamen normal çalışır. Yalnızca
> AI yorumu üretilmez; istatistikler, raporlar ve tüm operasyonel modüller
> etkilenmez. Analiz uçları yine başarılı yanıt döner, sadece
> `ai_available: false` olur.

---

## 2. Kurulum

### 2.1 LM Studio'yu indirin

1. <https://lmstudio.ai> adresine gidin.
2. İşletim sisteminize uygun sürümü indirin (Windows için `.exe`).
3. Kurulumu tamamlayın ve uygulamayı açın.

> İndirme ve kurulum işlemini **kendiniz yapmalısınız**; bu program sizin
> adınıza dosya indirmez.

### 2.2 Model indirin

LM Studio içindeki arama (**Discover** / büyüteç) sekmesinden model
indirilir. Model seçerken üç şeye bakın: **boyut** (donanımınıza sığmalı),
**quantization** (Q4_K_M çoğu senaryoda iyi denge), **kullanım şartları**
(ticari kullanım serbest mi).

Programın model yönlendirme tablosu (`TASK_MODEL_HINTS`,
`backend/app/services/ai/providers.py`) şu ad ailelerini tanır. Model
adında bu parçalardan biri geçiyorsa ilgili görev için aday olarak
işaretlenir:

| Görev | Arayüzdeki etiket | Tanınan ad parçaları | Ne için kullanılır |
|-------|-------------------|----------------------|--------------------|
| `general` | Genel analiz | `gemma`, `llama`, `qwen3`, `mistral`, `phi` | Devam, finans, tutundurma, program analizleri |
| `reasoning` | Akıl yürütme | `gemma`, `qwen3`, `llama-3.3`, `deepseek` | Performans yorumu, antrenman planı, CAIO özeti |
| `vision` | Görsel analiz | `vl`, `vision`, `moondream`, `llava`, `pixtral` | Görsel girdi gerektiren senaryolar |
| `math` | Matematiksel analiz | `math`, `qwen2.5-math` | Sayısal ağırlıklı yorumlar |
| `code` | Kod üretimi | `coder`, `code`, `qwen2.5-coder`, `starcoder`, `codestral` | AI Developer Console yama üretimi |
| `embedding` | Vektör gömme | `embed`, `nomic-embed`, `bge` | İleride RAG katmanı için |
| `medical` | Sağlık metni | `biomistral`, `medical`, `med` | Sağlık notu metinleri |

### Öneri: hangi model ailesinden başlamalı

| İhtiyaç | Aranacak model ailesi | Neden |
|---------|----------------------|-------|
| **Genel amaçlı** (günlük analiz, sohbet, rapor yorumu) | `gemma`, `llama`, `qwen3`, `mistral`, `phi` ailelerinden 7B–12B bir *instruct* modeli | Türkçe talimat takibi ve biçimli çıktı (başlıklı yanıt, JSON) için yeterli; orta donanımda çalışır |
| **Görsel analiz** | Adında `vl`, `vision`, `llava`, `pixtral`, `moondream` geçen bir model | Görsel girdi kabul eden mimariler bu adlarla yayımlanır |
| **Matematik / sayısal** | Adında `math` geçen bir model (ör. `qwen2.5-math` ailesi) | Sayısal akıl yürütmeye özel ince ayar |
| **Kod üretimi** (AI Developer Console) | Adında `coder` / `code` geçen bir model | Ajanın istediği katı JSON şemasını daha güvenilir üretir |

> **Önemli:** Program, model adından yetenek **varsaymaz**. Yukarıdaki
> eşleşmeler yalnızca bir öneridir ve arayüzde `heuristic` (doğrulanmamış)
> olarak işaretlenir. LM Studio `/v1/models` yanıtında yetenek alanı
> bildirmediği için yerel modeller neredeyse her zaman "doğrulanmamış"
> görünür — bu beklenen davranıştır. Ayrıntı:
> [AI_ARCHITECTURE.md § 4](AI_ARCHITECTURE.md#4-model-yönlendirme).

### 2.3 Modeli yükleyin

İndirme bittikten sonra LM Studio'nun sohbet ekranından modeli seçip
yükleyin (**Load Model**). Model belleğe yüklenmeden sunucu istek
karşılayamaz.

---

## 3. Sunucuyu başlatma

1. LM Studio'da sol menüden **Developer** (bazı sürümlerde **Local Server**)
   sekmesine geçin.
2. Yüklü modeli seçin.
3. **Start Server** düğmesine basın.
4. Sunucu adresi görünür: varsayılan olarak `http://localhost:1234`.

Sunucu çalışırken uç noktalar şunlardır:

| Uç | Ne yapar | Program nerede kullanır |
|----|----------|-------------------------|
| `GET http://localhost:1234/v1/models` | Yüklü modelleri listeler | `health()`, `list_models()`, bağlantı testi 1 ve 2 |
| `POST http://localhost:1234/v1/chat/completions` | Yanıt üretir | `chat()` ve `stream()` |

Hızlı doğrulama (PowerShell):

```powershell
Invoke-RestMethod http://localhost:1234/v1/models | ConvertTo-Json -Depth 4
```

Aynı kontrol `curl` ile:

```bash
curl http://localhost:1234/v1/models
```

Yanıtta `"data": [...]` içinde model kimliğini görüyorsanız sunucu hazırdır.

> Sunucu portunu LM Studio'dan değiştirdiyseniz `.env` dosyasındaki
> `LOCAL_AI_BASE_URL` değerini de aynı porta güncelleyin.

---

## 4. Programı yapılandırma

İki yol vardır: `.env` dosyası (kalıcı, uygulama başlangıcında okunur) veya
arayüz (**AI Merkezi > Ayarlar**, değişiklik yine `.env`'e yazılır).

### 4.1 `.env` değişkenleri

Dosya: `C:\SwimmingSchool\.env` (şablon: `.env.example`)

| Değişken | Varsayılan (kod) | Tip | Açıklama |
|----------|------------------|-----|----------|
| `LOCAL_AI_ENABLED` | `true` | bool | Yerel sağlayıcıyı tamamen açar/kapatır. `false` iken zincirden çıkarılır. |
| `LOCAL_AI_BASE_URL` | `http://localhost:1234/v1` | metin | LM Studio sunucu adresi. **Sonundaki `/v1` gereklidir.** |
| `LOCAL_AI_API_KEY` | `lm-studio` | metin | LM Studio anahtar doğrulamaz; yer tutucu değerdir. Boş bırakılırsa `Authorization` başlığı hiç gönderilmez. |
| `LOCAL_AI_MODEL` | `""` (boş) | metin | Kullanılacak model kimliği. **Boş bırakılırsa sunucudaki ilk model otomatik seçilir.** |
| `LOCAL_AI_TIMEOUT` | `180` | saniye | İstek zaman aşımı. Yavaş donanımda artırın (arayüzden 5–900 arası). |
| `LOCAL_AI_MAX_TOKENS` | `2048` | tam sayı | Üretilecek azami token (arayüzden 1–32000 arası). |
| `LOCAL_AI_TEMPERATURE` | `0.3` | ondalık | Yaratıcılık. Analizde düşük tutun (0–2 arası; 0.2–0.4 önerilir). |

İlgili yönlendirme ayarları:

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `AI_DEFAULT_MODE` | `automatic` | `local` yaparsanız **yalnızca** yerel model kullanılır, buluta hiç düşülmez. |
| `AI_FALLBACK_CHAIN` | `local,nvidia` | Deneme sırası. Yerel her zaman başta olmalıdır. |
| `AI_RESPONSE_LANGUAGE` | `auto` | `tr`, `en` veya arayüz dilini izleyen `auto`. |
| `AI_LOG_PROMPTS` | `false` | Gizlilik: `true` iken istem metni veritabanına yazılır. |

Örnek — yalnızca yerel, kapalı devre yapılandırma:

```dotenv
# ---------- YEREL YAPAY ZEKA / LOCAL AI (LM Studio) ----------
LOCAL_AI_ENABLED=true
LOCAL_AI_BASE_URL=http://localhost:1234/v1
LOCAL_AI_API_KEY=lm-studio
LOCAL_AI_MODEL=google/gemma-4-12b-qat
LOCAL_AI_TIMEOUT=240
LOCAL_AI_MAX_TOKENS=2048
LOCAL_AI_TEMPERATURE=0.3

# ---------- AI YÖNLENDİRME / AI ROUTING ----------
AI_DEFAULT_MODE=local
AI_FALLBACK_CHAIN=local
AI_RESPONSE_LANGUAGE=auto
AI_LOG_PROMPTS=false

# Bulut sağlayıcı kapalı
NVIDIA_ENABLED=false
```

`.env` değişikliği sonrası ya programı yeniden başlatın
(`START_SWIMMING_SCHOOL.bat`) ya da sağlayıcıları yeniden yükleyin:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/reload
```

### 4.2 Arayüzden yapılandırma

**AI Merkezi > Ayarlar** sekmesi (`ai:configure` izni gerekir):

1. Sol menüden **AI Merkezi**'ne girin.
2. Üstteki **Ayarlar** sekmesine geçin.
3. "LM Studio (Yerel)" bölümündeki alanları doldurun — alan adları `.env`
   anahtarlarıyla birebir eşleşir (`LOCAL_AI_BASE_URL`, `LOCAL_AI_MODEL`,
   `LOCAL_AI_TIMEOUT`, `LOCAL_AI_MAX_TOKENS`, `LOCAL_AI_TEMPERATURE`).
4. Kaydedin.

Kaydetme işlemi `PUT /api/v1/ai/config` uçunu çağırır; değerler `.env`
dosyasına yazılır, sağlayıcılar otomatik yeniden yüklenir ve değişiklik
denetim kaydına (audit log) işlenir.

Mevcut yapılandırmayı görmek için: `GET /api/v1/ai/config`. Bu uç API
anahtarlarını **asla tam döndürmez**, yalnızca maskeli gösterir.

### 4.3 Model listesini görme

**AI Merkezi > Model Yönlendirme** sekmesi, her görev türü için her
sağlayıcının önerdiği modeli ve önerinin kaynağını
(`api` / `heuristic` / `fallback` / `unavailable`) gösterir.

Ham liste için:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/local/models
```

Bu uç önbelleği atlar (`use_cache=False`), yani LM Studio'da modeli
değiştirdikten sonra hemen güncel sonucu döner.

---

## 5. Bağlantı testi

### 5.1 Testi çalıştırma

**AI Merkezi > Kontrol Merkezi** sekmesinde LM Studio satırındaki
**Bağlantıyı Test Et** düğmesine basın. Karşılığı:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/local/test
```

Gereken izin: `ai:configure`. Her çalıştırma denetim kaydına yazılır.

### 5.2 Altı testin anlamı

| # | Test | Ne doğrular | FAIL ise ilk bakılacak yer |
|---|------|-------------|----------------------------|
| 1 | `connection` | `GET /v1/models` yanıt veriyor mu; gecikme ve model sayısı | LM Studio açık mı, **Start Server** basılı mı, port doğru mu |
| 2 | `model` | Sunucuda en az bir model listeleniyor mu (ilk 4'ü raporlanır) | Model yüklendi mi (**Load Model**) |
| 3 | `simple_prompt` | Model gerçekten üretim yapıyor mu ("Türkiye'nin başkenti nedir?") | Model bozuk/eksik indirilmiş olabilir; bellek yetersizliği |
| 4 | `json_output` | `{"status":"ok","value":42}` üretebiliyor mu | Küçük modeller katı JSON'da zorlanır — analiz ve Developer Console bu yeteneğe bağlıdır |
| 5 | `timeout` | Yapılandırılmış zaman aşımını raporlar (bilgilendirme) | Bilgi amaçlıdır, her zaman `PASS` |
| 6 | `streaming` | SSE akışı ilk 5 parçayı gönderiyor mu | Sohbet ekranındaki canlı yazım bu teste bağlıdır |

### 5.3 PASS / FAIL / SKIPPED yorumlama

| Sonuç | Anlamı | Ne yapmalı |
|-------|--------|------------|
| **PASS** | Test geçti. | — |
| **FAIL** | Test başarısız. Ayrıntı sütunu hata tipini söyler. | İlgili satırdaki çözüme bakın ([Bölüm 8](#8-sorun-giderme)). |
| **SKIPPED** | Test **çalıştırılmadı**. | İki nedeni olabilir (aşağıda). |

`SKIPPED` iki durumda görünür:

1. **Sağlayıcı devre dışı** — `LOCAL_AI_ENABLED=false`. Altı testin tamamı
   `SKIPPED` olur, genel sonuç da `SKIPPED`'tır. Bu bir hata değildir.
2. **Bağlantı kurulamadı** — 1. test `FAIL` verdiğinde kalan beş test
   `"Bağlantı kurulamadı"` açıklamasıyla `SKIPPED` olur ve genel sonuç
   `FAIL` olur.

**Genel sonuç kuralı:** Tüm testler `PASS` veya `SKIPPED` ise genel sonuç
`PASS`; en az bir `FAIL` varsa `FAIL`.

Sık görülen bir kombinasyon: 1–3 `PASS`, 4 (`json_output`) `FAIL`.
Bu, modelin çalıştığını ama katı JSON üretemediğini gösterir. Sohbet ve
metin analizi çalışır; AI Developer Console yama üretimi güvenilir olmaz.
Çözüm: daha büyük veya *instruct* ince ayarlı bir modele geçin.

---

## 6. Donanım gereksinimleri

Bellek ihtiyacı model parametre sayısına ve quantization seviyesine bağlıdır.
Aşağıdaki değerler yaygın **Q4_K_M** (4-bit) quantization içindir ve model
ağırlıkları + orta düzey bağlam (8K) için gereken toplamı gösterir.

| Model boyutu | Ağırlık (Q4_K_M, yaklaşık) | Yalnızca CPU — önerilen RAM | GPU hızlandırma — önerilen VRAM | Beklenen deneyim |
|--------------|---------------------------|------------------------------|----------------------------------|------------------|
| 1–3B | 1–2 GB | 8 GB | 4 GB | Çok hızlı; kısa özet ve sınıflandırma için yeterli, karmaşık analizde zayıf |
| 7–8B | 4–5 GB | 16 GB | 6–8 GB | **Günlük kullanım için tavsiye edilen alt sınır.** Devam/finans analizi ve Türkçe rapor yorumu iyi |
| 12–14B | 7–9 GB | 24 GB | 10–12 GB | Belirgin kalite artışı; performans yorumu ve antrenman planı için ideal |
| 20–24B | 12–15 GB | 32 GB | 16 GB | Güçlü akıl yürütme; CPU'da yavaş kalır |
| 30–34B | 18–21 GB | 48 GB | 24 GB | Kod üretimi ve karmaşık CAIO özetleri için uygun |
| 70B+ | 38–45 GB | 64 GB+ | 48 GB+ | Genellikle çok GPU'lu iş istasyonu gerektirir; tipik okul bilgisayarında pratik değil |

Ek notlar:

* **Bağlam uzunluğu belleğe eklenir.** 32K bağlam, 8K'ya göre birkaç GB daha
  fazla yer kaplar. `LOCAL_AI_MAX_TOKENS=2048` varsayılanı bu maliyeti
  düşük tutar.
* **Quantization seçimi:** Q8 ≈ ağırlığın iki katı bellek, en yüksek kalite;
  Q4_K_M denge noktası; Q3 ve altı bellek kazandırır ama Türkçe metinde
  kalite kaybı belirginleşir.
* **GPU şart değil.** CPU üzerinde de çalışır; sadece yanıt süresi uzar.
  Bu durumda `LOCAL_AI_TIMEOUT` değerini `300`–`600` aralığına çıkarın.
* **Program kendisi hafiftir:** FastAPI backend + SQLite + WebView2 tabanlı
  masaüstü başlatıcı. Bellek tüketiminin neredeyse tamamı modele aittir.

---

## 7. Performans ipuçları

### 7.1 Bağlam (context) uzunluğu

LM Studio'da model yüklenirken **Context Length** ayarlanır. Bağlam ne kadar
uzunsa bellek tüketimi ve ilk token gecikmesi o kadar artar.

Program modele **ham veri göndermez**; önce Statistics Engine metrikleri
hesaplar, sonra bunların JSON özeti **6000 karakterle sınırlanarak**
gönderilir (`analysis.py`). Buna göre:

* **4K–8K bağlam** analiz ve sohbet için yeterlidir.
* **16K+ bağlam** yalnızca AI Developer Console kullanıyorsanız gerekir;
  ajan dosya içeriklerini gönderir (`MAX_CONTEXT_CHARS = 60_000`,
  dosya başına `MAX_FILE_BYTES = 200_000` sınırı).

### 7.2 GPU offload

LM Studio'nun model yükleme panelinde **GPU Offload** kaydırıcısı, kaç
katmanın ekran kartına aktarılacağını belirler.

* Model VRAM'e tamamen sığıyorsa **tüm katmanları** GPU'ya verin — en yüksek
  hız budur.
* Sığmıyorsa kısmi offload da hızlandırır; kaydırıcıyı kademeli artırıp
  bellek taşana kadar deneyin.
* Taşma olursa LM Studio modeli yükleyemez veya sistem takılır; bir kademe
  geri alın.

### 7.3 Quantization

| Seviye | Bellek | Kalite | Ne zaman |
|--------|--------|--------|----------|
| Q8_0 | En yüksek | En yüksek | Bol VRAM varsa, JSON/kod üretimi kritikse |
| Q5_K_M | Yüksek | Çok iyi | Dengeyi kaliteye kaydırmak istediğinizde |
| **Q4_K_M** | Orta | İyi | **Varsayılan öneri** |
| Q3_K_M | Düşük | Orta | Bellek çok kısıtlıysa; Türkçe kalitesi düşer |

Aynı bellek bütçesinde **daha büyük modelin daha agresif quantize edilmiş
hali**, küçük modelin yüksek kalitesinden genellikle daha iyi sonuç verir
(örn. 12B-Q4, 7B-Q8'e tercih edilebilir).

### 7.4 Uygulama tarafı ayarlar

| Ayar | Öneri | Neden |
|------|-------|-------|
| `LOCAL_AI_TEMPERATURE` | `0.2`–`0.4` | Analiz yorumlarında tutarlılık; yüksek değer uydurma riskini artırır |
| `LOCAL_AI_MAX_TOKENS` | `1024`–`2048` | Yanıtlar zaten kısa istenir; yüksek değer bekleme süresini uzatır |
| `LOCAL_AI_TIMEOUT` | CPU'da `300`+ | Yavaş donanımda erken kesilmeyi önler |
| `AI_DEFAULT_MODE` | `local` | Buluta hiç düşmez; hem gizlilik hem öngörülebilir gecikme |

### 7.5 Diğer

* **Modeli yüklü bırakın.** Her istekte yeniden yükleme, ilk yanıtı
  onlarca saniye geciktirir.
* **Sağlık kontrolü 30 saniye önbelleklenir** (`_HEALTH_CACHE_TTL`), bu
  yüzden sayfa yenilemek LM Studio'ya sürekli istek göndermez.
* **Model listesi de önbelleklenir.** LM Studio'da modeli değiştirdikten
  sonra `POST /api/v1/ai/reload` çağırın veya AI Merkezi'nde yenileyin.

---

## 8. Sorun giderme

### 8.1 Bağlantı reddedildi

**Belirti:** Bağlantı testi 1. adımda `FAIL`; ayrıntıda `ConnectError`.
Kontrol Merkezi'nde LM Studio satırı "kullanılamıyor" görünür.

| Olası sebep | Çözüm |
|-------------|-------|
| LM Studio kapalı | Uygulamayı açın |
| Sunucu başlatılmamış | **Developer > Start Server** |
| Port farklı | LM Studio'daki portu okuyun, `LOCAL_AI_BASE_URL` değerini eşitleyin |
| `/v1` eksik | Adres `http://localhost:1234/v1` olmalı, `http://localhost:1234` değil |
| `LOCAL_AI_ENABLED=false` | `true` yapın (bu durumda testler `FAIL` değil `SKIPPED` görünür) |
| Güvenlik duvarı yerel portu engelliyor | Windows Güvenlik Duvarı'nda LM Studio'ya izin verin |
| `localhost` çözümlenmiyor | `http://127.0.0.1:1234/v1` deneyin |

Hızlı doğrulama:

```powershell
Invoke-RestMethod http://localhost:1234/v1/models
```

Bu komut da hata veriyorsa sorun LM Studio tarafındadır, programda değil.

### 8.2 Zaman aşımı

**Belirti:** Hata metni `[local] Zaman aşımı (180s)`. Görev geçmişinde
(`AI Merkezi > Görev Geçmişi`) durum `failed`.

| Olası sebep | Çözüm |
|-------------|-------|
| Model donanıma göre çok büyük | Daha küçük model veya daha agresif quantization |
| GPU offload kapalı, tümü CPU'da | LM Studio'da GPU Offload'u artırın |
| `LOCAL_AI_TIMEOUT` düşük | `300`–`600` yapın |
| `LOCAL_AI_MAX_TOKENS` çok yüksek | `2048` veya altına indirin |
| İlk istek soğuk başlangıç | Modeli LM Studio sohbetinde bir kez çalıştırıp ısıtın |
| Bağlam çok uzun | LM Studio'da Context Length'i düşürün |

### 8.3 Boş yanıt

**Belirti:** `[local] Yanıt boş döndü (choices yok)` veya 3. testte
"Boş yanıt".

| Olası sebep | Çözüm |
|-------------|-------|
| Model yüklenmemiş, sunucu ayakta | LM Studio'da **Load Model** |
| `max_tokens` çok düşük | `LOCAL_AI_MAX_TOKENS` değerini artırın |
| Akıl yürütme modeli içeriği `reasoning` alanında döndürüyor | Program bunu zaten ele alır; yine boşsa standart bir *instruct* modele geçin |
| Model bozuk indirilmiş | LM Studio'dan silip yeniden indirin |
| İstem şablonu uyumsuz | LM Studio'da modelin doğru prompt template'ini seçin |

### 8.4 Yavaş yanıt

**Belirti:** Yanıtlar geliyor ama 60 saniyeden uzun sürüyor.
Kontrol Merkezi'ndeki gecikme (latency) sütunu yüksek.

| Olası sebep | Çözüm |
|-------------|-------|
| CPU üzerinde çalışıyor | GPU Offload'u açın |
| Model çok büyük | Bir kademe küçük modele geçin (24B → 12B → 8B) |
| Yüksek quantization (Q8) | Q4_K_M'ye geçin |
| Uzun bağlam yüklü | Context Length'i 8K'ya düşürün |
| Arka planda başka ağır süreç | Diğer uygulamaları kapatın |
| RAM yetersiz, disk takası (swap) başlamış | [Bölüm 6](#6-donanım-gereksinimleri) tablosuna göre model boyutunu düşürün |

Ölçüm için: **AI Merkezi > Görev Geçmişi** sekmesinde her görevin
`duration_ms` ve token sayıları listelenir; hangi görev türünün yavaş
olduğunu buradan görebilirsiniz.

### 8.5 JSON testi başarısız (4. test)

**Belirti:** 1–3 `PASS`, `json_output` `FAIL`.

Model serbest metin üretebiliyor ama katı JSON üretemiyor. Sonuçları:

* AI Analizi ve Sohbet **çalışır** (bunlar serbest metin bekler).
* AI Developer Console yama üretimi **güvenilmez olur** (ajan katı JSON şeması ister).

Çözüm: daha büyük bir model, *instruct* ince ayarlı bir sürüm veya kod
odaklı bir model (`coder` ailesi) kullanın.

### 8.6 Model listesi boş

**Belirti:** 2. test `FAIL`, "0 model".

LM Studio sunucusu açık ama hiçbir model yüklü değil. Modeli seçip
yükledikten sonra `POST /api/v1/ai/reload` çağırın veya AI Merkezi'ni
yenileyin.

### 8.7 Loglara bakma

Sorun devam ederse `logs/` klasöründeki dosyalara bakın:

| Dosya | İçerik |
|-------|--------|
| `logs/ai.log` | Sağlayıcı çağrıları, model adı, token, süre, fallback geçişleri |
| `logs/application.log` | Genel uygulama akışı ve başlangıç hataları |

Log kayıtları `RedactingFilter`'dan geçer; API anahtarları ve parolalar
maskelenmiş olarak yazılır.

CAIO ajanı da bu logları tarar ve hata sayısı eşiği aşarsa
`reliability` kategorisinde bulgu üretir
(`AI Merkezi` değil, **CAIO** ekranı).

---

## 9. Gizlilik avantajı

### 9.1 Veri neden bilgisayardan çıkmamalı

Bu sistemde işlenen veri türleri:

* Öğrenci ad-soyad, doğum tarihi, seviye, grup
* Veli iletişim bilgileri
* **Sağlık notu ve özel ihtiyaç bilgisi** (`student:read_sensitive` izniyle korunur)
* Yoklama geçmişi, ödeme ve borç durumu
* Performans dereceleri ve antrenman kayıtları

Bunların önemli bir bölümü kişisel veri, bir bölümü **özel nitelikli**
kişisel veridir (sağlık). Yerel model kullanıldığında bu veriler hiçbir
ağ bağlantısı üzerinden dışarı çıkmaz; istek `localhost` üzerinde başlar
ve biter.

Kod tarafındaki karşılığı `LMStudioProvider` sınıfının belgesidir:

> "Gizlilik notu: İstekler bilgisayardan çıkmaz. Hassas öğrenci verisi için
> tercih edilmesi gereken sağlayıcıdır."

Bu not API üzerinden arayüze de taşınır (`privacy_note_tr` /
`privacy_note_en`) ve AI Merkezi'nde sağlayıcı satırında gösterilir.

### 9.2 Modele ne gönderiliyor?

Program modele ham veritabanı satırı göndermez. `analysis.py` içinde
gönderilen içerik şudur:

* Kullanıcının sorusu
* Statistics Engine'in **hesapladığı** metrikler (oranlar, ortalamalar, dereceler)
* İlgili öğrencinin **adı** (kapsam öğrenci bazlıysa)
* Bu metriklerin ilk 6000 karakterlik JSON özeti

Gönderilmeyenler: TC kimlik/iletişim bilgileri, parolalar, API anahtarları,
tam tablo dökümleri, ham sağlık notu metni.

### 9.3 Kapalı devre yapılandırma

Hiçbir verinin dışarı çıkmadığından emin olmak için:

```dotenv
AI_DEFAULT_MODE=local
AI_FALLBACK_CHAIN=local
LOCAL_AI_ENABLED=true
NVIDIA_ENABLED=false
OPENAI_COMPAT_ENABLED=false
AI_LOG_PROMPTS=false
```

Bu yapılandırmada:

* `resolve_chain()` her zaman `["local"]` döndürür — buluta **hiç düşülmez**.
* `NvidiaProvider.enabled` zaten `False` olur (hem bayrak hem anahtar yok).
* İstem metinleri veritabanına yazılmaz.
* Kontrol Merkezi'nde `local_only_mode: true` görünür.

Doğrulamak için:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/control-center
```

Yanıttaki `"mode": "local"`, `"fallback_chain": ["local"]` ve
`"local_only_mode": true` alanları yapılandırmayı teyit eder.

### 9.4 Ek koruma katmanları

Yerel model kullansanız bile şu korumalar açık kalır:

| Koruma | Nerede |
|--------|--------|
| RBAC — AI özelliklerine erişim `ai:use` iznine bağlı | `backend/app/core/permissions.py` |
| Yapılandırma değişikliği `ai:configure` iznine bağlı | `backend/app/api/v1/ai.py` |
| Her AI çağrısı `ai_tasks` tablosuna kaydedilir (kim, ne zaman, hangi model) | `backend/app/models/system.py` |
| Yapılandırma değişiklikleri denetim kaydına yazılır | `app/services/audit.py` |
| İstem metni varsayılan olarak saklanmaz | `AI_LOG_PROMPTS=false` |
| Loglarda anahtar maskeleme | `RedactingFilter` |

### 9.5 Bulut gerekiyorsa

Yerel donanım yetersizse hibrit çalışabilirsiniz: rutin ve kişisel veri
içeren analizleri yerelde, yalnızca kişisel veri içermeyen genel soruları
bulutta. Bunun için `AI_DEFAULT_MODE=automatic` ve
`AI_FALLBACK_CHAIN=local,nvidia` bırakın; buluta yalnızca yerel başarısız
olduğunda düşülür.

CAIO ajanı bulut kullanımını izler: yerel oran %50'nin altına düşer ve
buluta 50.000'den fazla token gönderilirse `cost` kategorisinde `low`
önemde bir bulgu üretir ve rutin analizleri yerele almanızı önerir.

Bulut tarafının ayrıntıları: [NVIDIA_AI.md](NVIDIA_AI.md)

---

## İlgili belgeler

* [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) — Yapay zekâ mimarisi ve sağlayıcı soyutlaması
* [NVIDIA_AI.md](NVIDIA_AI.md) — NVIDIA Build bulut entegrasyonu
* [DEVELOPER_AGENT.md](DEVELOPER_AGENT.md) — AI Developer Console ve CAIO
* [../.env.example](../.env.example) — Tüm ortam değişkenlerinin şablonu
