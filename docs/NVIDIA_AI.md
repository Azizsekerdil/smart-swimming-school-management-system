# Bulut Yapay Zekâ — NVIDIA Build Entegrasyonu

Bu belge, Akıllı Yüzme Okulu Yönetim Sistemi'ni NVIDIA Build (build.nvidia.com)
üzerinden bulut dil modelleriyle çalıştırmayı anlatır. API anahtarının güvenli
yönetimi, model seçimi, maliyet kontrolü ve gizlilik değerlendirmesi bu
belgenin merkezindedir.

**Sürüm:** 0.9.0 · **Sağlayıcı adı:** `nvidia` · **Varsayılan uç:**
`https://integrate.api.nvidia.com/v1` · **Varsayılan durum:** Kapalı

---

## İçindekiler

1. [NVIDIA Build nedir, ne zaman kullanılır](#1-nvidia-build-nedir-ne-zaman-kullanılır)
2. [API anahtarı alma](#2-api-anahtarı-alma)
3. [Güvenlik uyarısı](#3-güvenlik-uyarısı)
4. [Yapılandırma](#4-yapılandırma)
5. [Model seçimi](#5-model-seçimi)
6. [Bağlantı testi ve doğrulama](#6-bağlantı-testi-ve-doğrulama)
7. [Maliyet kontrolü](#7-maliyet-kontrolü)
8. [Gizlilik](#8-gizlilik)
9. [Sorun giderme](#9-sorun-giderme)

---

## 1. NVIDIA Build nedir, ne zaman kullanılır

**NVIDIA Build**, NVIDIA'nın barındırdığı dil modellerine OpenAI uyumlu bir
REST API üzerinden erişim sunan bulut hizmetidir. Bu program, aynı
`/v1/chat/completions` ve `/v1/models` şemasını konuştuğu için ek bir
bağlayıcı olmadan bağlanır.

Kod tarafındaki karşılığı `NvidiaProvider` sınıfıdır
(`backend/app/services/ai/providers.py`) ve `OpenAICompatibleProvider`
tabanından türer. Sağlayıcının bir özel kuralı vardır:

```python
@property
def enabled(self) -> bool:
    # API anahtarı olmadan bulut sağlayıcı etkin sayılmaz
    return super().enabled and bool(self.api_key)
```

Yani `NVIDIA_ENABLED=true` yapmak yetmez; anahtar tanımlı değilse sağlayıcı
devre dışı kabul edilir ve fallback zincirinden sessizce çıkarılır.

### Ne zaman kullanılır

| Durum | Bulut uygun mu | Gerekçe |
|-------|----------------|---------|
| Yerel donanım 7B modeli bile kaldırmıyor | **Evet** | Bulut modeli donanımdan bağımsızdır |
| LM Studio kapalı / bakımda, kesinti istenmiyor | **Evet** | Fallback zinciri buluta düşer |
| Çok büyük modele ihtiyaç var (karmaşık akıl yürütme, kod üretimi) | **Evet** | 70B+ modeller yerelde pratik değildir |
| Toplu/geçici yük (dönem sonu raporlama haftası) | **Evet** | Kalıcı donanım yatırımı gerekmez |
| Öğrenci sağlık notu içeren analiz | **Hayır** | Özel nitelikli kişisel veri buluta gönderilmemelidir |
| Rutin günlük analiz (devam, doluluk) | Tercihen hayır | Yerel model yeterli; maliyet ve gizlilik açısından daha iyi |
| Kurumsal politika verinin yurt dışına çıkmasını yasaklıyor | **Hayır** | Yalnızca yerel mod kullanın |

Önerilen varsayılan yapılandırma **hibrittir**: yerel önce, bulut yedek.

```dotenv
AI_DEFAULT_MODE=automatic
AI_FALLBACK_CHAIN=local,nvidia
```

Bu sırada bulut yalnızca yerel sağlayıcı başarısız olduğunda devreye girer.

---

## 2. API Anahtarı Alma

> ### ⚠ Bu adımları KULLANICININ KENDİSİ yapmalıdır
>
> API anahtarı **kişisel bir kimlik bilgisidir**. Hesap oluşturma, giriş
> yapma ve anahtar üretme adımlarını **siz kendiniz** gerçekleştirmelisiniz.
> Bu program, bu yazılımın geliştiricisi veya herhangi bir yapay zekâ
> asistanı sizin adınıza hesap açamaz, oturum bilgisi giremez veya anahtar
> oluşturamaz. Anahtarınızı hiç kimseyle paylaşmayın — destek talebinde
> bile paylaşmanız gerekmez.

### Adımlar

1. Tarayıcınızdan <https://build.nvidia.com> adresine gidin.
2. **Kendi** NVIDIA hesabınızla oturum açın; hesabınız yoksa kayıt olun.
3. Kullanmak istediğiniz modelin sayfasına gidin.
4. Sayfadaki **Get API Key** / **Generate API Key** düğmesini kullanarak
   anahtar üretin.
5. Anahtar yalnızca **bir kez** tam olarak gösterilir. Pencereyi kapatmadan
   önce kopyalayın.
6. Anahtarı bir parola yöneticisinde saklayın. Not defterine, e-postaya,
   sohbet uygulamasına veya ekran görüntüsüne kaydetmeyin.
7. Anahtarı yalnızca `.env` dosyasına veya program arayüzündeki
   **AI Merkezi > Ayarlar** alanına girin.

### Hesap türü ve kota

NVIDIA Build'in ücretsiz ve ücretli katmanlarının kredi/kota koşulları
zaman içinde değişir. Güncel limitleri, ücretlendirmeyi ve kullanım
şartlarını **kendi hesabınızın panelinden** doğrulayın. Bu belge fiyat veya
kota taahhüdü içermez.

---

## 3. GÜVENLİK UYARISI

> ### API anahtarınız bir paroladır. Ona göre davranın.

### 3.1 Asla yapmayın

| ❌ Yapmayın | Neden |
|------------|-------|
| Anahtarı kaynak koda yazmak | Kod paylaşıldığı anda anahtar da paylaşılır |
| `README.md`, `docs/` veya herhangi bir belgeye yazmak | Belgeler genellikle herkese açıktır |
| Ekran görüntüsü almak / paylaşmak | Görüntü kalıcıdır, geri alınamaz |
| Hata raporuna, forum gönderisine, destek biletine yapıştırmak | Arşivlenir ve indekslenir |
| E-posta veya mesajlaşma uygulamasıyla göndermek | Sunucularda düz metin kalır |
| `.env.example` dosyasına gerçek değeri yazmak | Bu dosya **depoya dahildir**; boş kalmalıdır |
| Anahtarı `git commit` etmek | Geçmişten silmek zordur; anahtarı iptal etmek gerekir |
| Log dosyasına yazdırmak / `print()` ile ekrana basmak | Loglar paylaşılır ve yedeklenir |

### 3.2 Her zaman yapın

| ✅ Yapın | Nasıl |
|---------|-------|
| Anahtarı yalnızca `.env` dosyasına koyun | `NVIDIA_API_KEY=nvapi-...` |
| `.env` dosyasının `.gitignore` içinde olduğunu **doğrulayın** | Aşağıdaki komut |
| Anahtarı parola yöneticisinde saklayın | Yedeğiniz orada olsun |
| Kullanmadığınız dönemde `NVIDIA_ENABLED=false` yapın | Yanlışlıkla kullanımı engeller |
| Sızıntı şüphesinde **hemen iptal edin** | build.nvidia.com panelinden |
| Anahtarı periyodik olarak yenileyin | Kurumsal iyi uygulama |

### 3.3 `.gitignore` doğrulaması

```powershell
# .env gerçekten yok sayılıyor mu? (çıktı boşsa ignore ediliyor demektir)
git check-ignore -v .env

# .env yanlışlıkla takip ediliyor mu? (çıktı varsa SORUN var)
git ls-files --error-unmatch .env
```

`.env` takip ediliyorsa hemen çıkarın ve anahtarı iptal edin:

```powershell
git rm --cached .env
# .gitignore dosyasına ".env" satırını ekleyin, sonra commit edin
```

Program bu kontrolü sizin için de yapar: **CAIO ajanı** her çalıştığında
`.env` dosyasının varlığını ve `.gitignore` durumunu gözlemler
(`_observe_security`). `.env` var ama yok sayılmıyorsa **`critical`**
önemde bir bulgu üretir:

> **.env dosyası Git tarafından yok sayılmıyor** — Ortam dosyası sürüm
> kontrolüne girebilir; API anahtarları ve gizli anahtar sızabilir.

### 3.4 Anahtar sızarsa ne yapmalı

1. **Hemen iptal edin.** build.nvidia.com panelinden anahtarı silin/geçersiz kılın.
2. **Yeni anahtar üretin** ve yalnızca `.env` dosyasına girin.
3. **Kullanım geçmişini inceleyin.** Beklenmeyen tüketim var mı bakın.
4. **Sızıntı kaynağını kapatın.** Git geçmişindeyse commit'i temizleyin;
   ekran görüntüsündeyse görüntüyü kaldırın.
5. **Programı yeniden yükleyin:** `POST /api/v1/ai/reload`.

> Anahtar bir kez sızdıysa, kaynağı temizlemek yeterli değildir —
> **anahtarın kendisi iptal edilmelidir.** Git geçmişinden silinen bir
> commit'in kopyası başka birinde olabilir.

### 3.5 Programın sağladığı korumalar

| Katman | Mekanizma | Dosya |
|--------|-----------|-------|
| Yapılandırma | Anahtar yalnızca ortam değişkeninden okunur, koda gömülmez | `core/config.py` |
| API yanıtı | `GET /api/v1/ai/config` anahtarı **maskeli** döner (`nva************1234`) | `mask_secret()` |
| Hata gövdesi | Sağlayıcı hatası istemciye gitmeden `redact()` filtresinden geçer | `services/ai/base.py` |
| Loglar | `RedactingFilter` `nvapi-`, `sk-`, `Bearer`, `api_key=` kalıplarını `***REDACTED***` yapar | `core/logging_config.py` |
| Denetim kaydı | Anahtar değişince audit'e yalnızca `"nvidia_api_key (gizli)"` yazılır | `api/v1/ai.py` |
| Yedekleme | API anahtarları ve parolalar yedeğe **dahil edilmez** | `services/backup.py` |
| Developer ajanı | `.env` yolu `FORBIDDEN_PATH_PARTS` içinde; ajan okuyamaz da yazamaz da | `services/ai/policy.py` |
| CI | GitHub Actions gizli anahtar taraması çalıştırır | `.github/workflows` |

---

## 4. Yapılandırma

### 4.1 `.env` değişkenleri

Dosya: `C:\SwimmingSchool\.env` (şablon: `.env.example`)

| Değişken | Varsayılan (kod) | Tip | Açıklama |
|----------|------------------|-----|----------|
| `NVIDIA_ENABLED` | `false` | bool | Bulut sağlayıcıyı açar. **Tek başına yetmez — anahtar da gerekir.** |
| `NVIDIA_API_KEY` | `""` (boş) | metin | API anahtarınız. Boşsa sağlayıcı `enabled=False` sayılır. |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1` | metin | API kök adresi. Sonundaki `/v1` gereklidir. |
| `NVIDIA_MODEL` | `meta/llama-3.3-70b-instruct` | metin | Varsayılan model kimliği. Boş bırakılırsa API'nin listelediği ilk model kullanılır. |
| `NVIDIA_TIMEOUT` | `120` | saniye | İstek zaman aşımı (arayüzden 5–900 arası). |
| `NVIDIA_MAX_TOKENS` | `2048` | tam sayı | Üretilecek azami token (arayüzden 1–32000 arası). |
| `NVIDIA_TEMPERATURE` | `0.3` | ondalık | Yaratıcılık (0–2). Analizde düşük tutun. |

İlgili yönlendirme ayarları:

| Değişken | Varsayılan | Etkisi |
|----------|-----------|--------|
| `AI_DEFAULT_MODE` | `automatic` | `nvidia` yaparsanız **her istek buluta gider** (yerel hiç denenmez) |
| `AI_FALLBACK_CHAIN` | `local,nvidia` | Deneme sırası; yerel başta kalmalıdır |
| `AI_LOG_PROMPTS` | `false` | `true` iken buluta gönderilen istem veritabanına da yazılır |

Örnek — hibrit yapılandırma (önerilen):

```dotenv
# ---------- NVIDIA BUILD API ----------
# API anahtarını https://build.nvidia.com adresinden alın.
# ANAHTARI ASLA KAYNAK KODA VEYA GIT'E YAZMAYIN.
NVIDIA_ENABLED=true
NVIDIA_API_KEY=<panelden-aldiginiz-anahtari-buraya-yapistirin>
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=meta/llama-3.3-70b-instruct
NVIDIA_TIMEOUT=120
NVIDIA_MAX_TOKENS=2048
NVIDIA_TEMPERATURE=0.3

# ---------- AI YÖNLENDİRME ----------
AI_DEFAULT_MODE=automatic
AI_FALLBACK_CHAIN=local,nvidia
AI_LOG_PROMPTS=false
```

Değişiklik sonrası programı yeniden başlatın (`START_SWIMMING_SCHOOL.bat`)
veya sağlayıcıları yeniden yükleyin:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/reload
```

### 4.2 Arayüzden girme

**AI Merkezi > Ayarlar** sekmesi (`ai:configure` izni gerekir):

1. Sol menüden **AI Merkezi**'ne girin.
2. **Ayarlar** sekmesine geçin.
3. "NVIDIA Build (Bulut)" bölümünü doldurun: etkinlik, adres, model,
   **API anahtarı**, zaman aşımı, azami token, sıcaklık.
4. Kaydedin.

Kaydetme `PUT /api/v1/ai/config` uçunu çağırır ve şunları yapar:

* Değerleri `.env` dosyasına yazar (yoksa `.env.example`'dan oluşturur).
* Sağlayıcıları yeniden yükler (`reload_providers()`).
* Denetim kaydına yazar — ancak **anahtarın değeri audit'e yazılmaz**,
  yalnızca `"nvidia_api_key (gizli)"` etiketi geçer.

#### Anahtar maskeli gösterilir

Anahtar bir kez kaydedildikten sonra arayüze **asla tam olarak dönmez**.
`GET /api/v1/ai/config` yanıtı şöyledir:

```json
{
  "nvidia": {
    "enabled": true,
    "base_url": "https://integrate.api.nvidia.com/v1",
    "model": "meta/llama-3.3-70b-instruct",
    "api_key_set": true,
    "api_key_masked": "nva************a1b2",
    "timeout": 120,
    "max_tokens": 2048,
    "temperature": 0.3
  }
}
```

Maskeleme kuralı (`mask_secret`): 8 karakterden kısa değerler tamamen
yıldızlanır; uzun değerlerde ilk 3 ve son 4 karakter görünür, arası 12
yıldızla doldurulur. `api_key_set` alanı anahtarın **tanımlı olup
olmadığını** söyler; değerini vermez.

Anahtarı değiştirmek için alana yeni değeri yazıp kaydetmeniz yeterlidir;
mevcut anahtarı okumak mümkün değildir (bu kasıtlıdır).

---

## 5. Model Seçimi

### 5.1 Model listesi API'den dinamik gelir

Bu belge **sabit bir model listesi vermez.** NVIDIA Build kataloğu sık
değişir; bu programda model listesi her zaman API'den canlı çekilir:

* **Arayüz:** AI Merkezi > **Model Yönlendirme** sekmesi — her görev türü
  için her sağlayıcının önerdiği model ve önerinin kaynağı gösterilir.
* **API:**

  ```bash
  curl -H "Authorization: Bearer $TOKEN" \
       http://127.0.0.1:8000/api/v1/ai/providers/nvidia/models
  ```

  Bu uç önbelleği atlar (`use_cache=False`) ve her model için `id`,
  `owned_by`, `capabilities`, `capability_source`, `context_length` döner.

Listede gördüğünüz `id` değerini `NVIDIA_MODEL` olarak yazın veya
arayüzdeki model alanına girin.

### 5.2 Hangi kritere göre seçilir

| Kriter | Ne sorulmalı | Bu programda neden önemli |
|--------|--------------|---------------------------|
| **Talimat takibi** (instruction following) | Model verilen başlık şablonuna uyuyor mu? | Analiz yanıtı `## Yorum` / `## Olası Nedenler` / `## Öneriler` başlıklarıyla ayrıştırılır. Uymuyorsa tüm metin tek bloğa düşer. |
| **Akıl yürütme** (reasoning) | Çok adımlı çıkarım yapabiliyor mu? | Performans yorumu, antrenman planı ve CAIO özeti `task="reasoning"` ile çağrılır. |
| **Kod üretimi** (coding) | Katı JSON ve çalışır kod üretebiliyor mu? | AI Developer Console `task="code"` ve `json_mode=True` kullanır; şema dışına çıkan yanıt reddedilir. |
| **Görsel** (vision) | Görsel girdi kabul ediyor mu? | Yalnızca görsel senaryolar için gerekir; metin analizinde gerekmez. |
| **Bağlam uzunluğu** (context) | Kaç token'lık girdi alabiliyor? | Analiz için 8K yeterlidir (metrik özeti 6000 karakterle sınırlıdır). Developer ajanı dosya içeriği gönderir — 32K+ tercih edilir. |
| **Hız** | Yanıt gecikmesi kabul edilebilir mi? | Kontrol Merkezi'ndeki gecikme sütunu ve görev geçmişindeki `duration_ms` ile ölçün. |
| **Maliyet / kota** | Token başına tüketim ve limit ne? | Büyük modeller aynı işi daha çok kaynakla yapar; rutin işler için küçük model yeterli olabilir. |
| **Türkçe kalitesi** | Türkçe çıktı doğal ve doğru mu? | Arayüz ve raporlar Türkçe; zayıf Türkçe destekli model kullanılabilir yorum üretmez. |
| **Kullanım şartları** | Ticari kullanım, veri saklama ve eğitim politikası ne? | Kurumsal/KVKK değerlendirmesi için zorunludur. Modelin lisansını ve sağlayıcı şartlarını **kendiniz okuyun.** |

### 5.3 Seçimi doğrulama yöntemi

Adaya karar vermeden önce ölçün:

1. `NVIDIA_MODEL` değerini adayla değiştirin, `POST /api/v1/ai/reload` çağırın.
2. Altı aşamalı bağlantı testini çalıştırın —
   özellikle **4. test (`json_output`)** sonucuna bakın.
3. AI Merkezi > AI Analizi sekmesinden gerçek bir soru sorun ve yanıtın
   başlık şablonuna uyup uymadığını kontrol edin.
4. **Görev Geçmişi** sekmesinde `duration_ms` ve `total_tokens`
   değerlerini karşılaştırın.

### 5.4 Yetenek bilgisi ne kadar güvenilir?

Program model adından yetenek **varsaymaz**. `capability_source` alanı
öneri kaynağını açıkça bildirir:

| Değer | Anlamı |
|-------|--------|
| `api` | Sağlayıcı API'si yeteneği **açıkça bildirmiştir** — doğrulanmış |
| `heuristic` | Yalnızca model adında anahtar kelime eşleşmiştir — doğrulanmamış tahmin |
| `fallback` | Eşleşme yok; listedeki ilk model önerilmiştir |
| `unavailable` | Sağlayıcıda hiç model yok |

Ayrıntı: [AI_ARCHITECTURE.md § 4](AI_ARCHITECTURE.md#4-model-yönlendirme).

---

## 6. Bağlantı Testi ve Doğrulama

### 6.1 Testi çalıştırma

**AI Merkezi > Kontrol Merkezi** sekmesinde NVIDIA satırındaki
**Bağlantıyı Test Et** düğmesi. API karşılığı:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/nvidia/test
```

Gereken izin: `ai:configure`. Her çalıştırma denetim kaydına
`ai_test` eylemiyle yazılır. **API anahtarı hiçbir test çıktısında görünmez.**

### 6.2 Altı test aşaması

| # | Test | Ne doğrular | Bulutta tipik hata nedeni |
|---|------|-------------|---------------------------|
| 1 | `connection` | `GET /v1/models` yanıt veriyor mu, gecikme ne kadar | İnternet yok, anahtar geçersiz (401), adres yanlış |
| 2 | `model` | Hesabınızın erişebildiği modeller listeleniyor mu | Anahtar yetkisiz veya hesap kısıtlı |
| 3 | `simple_prompt` | Model gerçekten üretim yapıyor mu | Kota aşımı (429), model kimliği yanlış |
| 4 | `json_output` | Katı JSON üretebiliyor mu | Model *instruct* değil; Developer Console bu yeteneğe bağlıdır |
| 5 | `timeout` | Yapılandırılmış zaman aşımını raporlar | Bilgilendirmedir, her zaman `PASS` |
| 6 | `streaming` | SSE akışı çalışıyor mu | Ağ/proxy akışı kesiyor olabilir |

**Sonuç yorumlama:**

* **PASS** — geçti.
* **FAIL** — başarısız; ayrıntı sütunu hata tipini söyler.
* **SKIPPED** — çalıştırılmadı. Ya sağlayıcı devre dışı/anahtarsız (altı test
  birden `SKIPPED`, genel sonuç `SKIPPED`) ya da 1. test `FAIL` verdiği için
  kalanlar atlandı (genel sonuç `FAIL`).

Genel sonuç kuralı: tüm testler `PASS` veya `SKIPPED` ise `PASS`, en az bir
`FAIL` varsa `FAIL`.

> Altı test birden `SKIPPED` görüyorsanız neredeyse her zaman sebep şudur:
> `NVIDIA_ENABLED=false` veya `NVIDIA_API_KEY` boş. Bu bir bağlantı hatası
> **değildir** — sağlayıcı hiç denenmemiştir.

### 6.3 Hafif sağlık kontrolü

Tam test yerine yalnızca erişilebilirlik ve gecikme ölçmek için:

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/nvidia/health
```

Sonuç `ai_provider_health` tablosuna yazılır ve Kontrol Merkezi'nde
"son kontrol" bilgisi olarak görünür. Rutin sağlık sorguları 30 saniye
önbelleklenir; bu uç önbelleği atlar.

### 6.4 Uçtan uca doğrulama

```bash
# 1) Yapılandırma doğru mu (anahtar maskeli döner)
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/config

# 2) Modeller geliyor mu
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/providers/nvidia/models

# 3) Gerçek bir sohbet isteği — açıkça nvidia seçilerek
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"messages":[{"role":"user","content":"Tek kelimeyle: test"}],"provider":"nvidia"}' \
     http://127.0.0.1:8000/api/v1/ai/chat
```

Üçüncü isteğin yanıtındaki `provider`, `model`, `usage` ve
`attempted_providers` alanları hangi sağlayıcının gerçekten yanıtladığını
gösterir. `provider="nvidia"` gönderildiğinde fallback **devre dışıdır** —
bu bilinçli seçimin denendiğini garanti eder.

---

## 7. Maliyet Kontrolü

Bulut kullanımı token başına tüketilir. Program tüketimi ölçer, sınırlar ve
raporlar.

### 7.1 Token takibi

Her AI çağrısı `ai_tasks` tablosuna kaydedilir:
`provider`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`,
`duration_ms`, `fallback_used`, `attempted_providers`.

Görüntüleme:

* **AI Merkezi > Kontrol Merkezi** — bugünkü ve toplam token kullanımı,
  görev sayıları, son 24 saatteki hata sayısı.
* **AI Merkezi > Görev Geçmişi** — görev bazında sağlayıcı, model, token, süre.
  Filtre: `GET /api/v1/ai/tasks?provider=nvidia&status=success`.

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/control-center
```

Yanıttaki `usage_today` ve `usage_total` blokları prompt/completion/total
ayrımıyla gelir.

### 7.2 Yerel / bulut dağılımı

CAIO ajanının `ai_usage` gözlemi bu dağılımı hesaplar
(`_observe_ai_usage`):

| Alan | Anlamı |
|------|--------|
| `total_tasks` / `successful` / `failed` | Görev sayıları |
| `success_rate` | Başarı yüzdesi |
| **`local_ratio`** | Başarılı görevlerin yüzde kaçı yerel sağlayıcıyla yapıldı |
| `cloud_task_count` | Bulut sağlayıcıyla yapılan görev sayısı |
| **`cloud_tokens`** | Buluta gönderilen toplam token |
| `fallback_count` | Kaç görevde fallback devreye girdi |
| `avg_duration_ms` | Ortalama süre |
| `by_kind` | Görev türüne göre dağılım |

Yalnızca ölçüm almak için (AI çağrısı yapmaz):

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/caio/observe
```

### 7.3 CAIO maliyet uyarısı

CAIO kural motoru şu koşulda `cost` kategorisinde `low` önemde bir bulgu
üretir:

> **Koşul:** `local_ratio < 50` **ve** `cloud_tokens > 50.000`
>
> **Başlık:** "Bulut AI kullanımı yüksek (yerel oran %X)"
>
> **Öneri:** "Rutin analizler için AI modunu 'local' yapın; yalnızca karmaşık
> görevlerde buluta düşün."

Bulgu **CAIO** ekranında görünür ve `open` → `acknowledged` → `in_progress`
→ `resolved` / `dismissed` akışıyla yönetilir.

### 7.4 Fallback zinciriyle bulut kullanımını sınırlama

| Amaç | Yapılandırma | Sonuç |
|------|--------------|-------|
| Bulut hiç kullanılmasın | `AI_DEFAULT_MODE=local` | `resolve_chain()` her zaman `["local"]` döner |
| Bulut yalnızca yedek olsun | `AI_DEFAULT_MODE=automatic` + `AI_FALLBACK_CHAIN=local,nvidia` | Yerel çalışırken buluta hiç gidilmez |
| Yalnızca bulut | `AI_DEFAULT_MODE=nvidia` | Her istek buluta gider — maliyet en yüksek |
| Geçici olarak kapat | `NVIDIA_ENABLED=false` | Sağlayıcı zincirden çıkarılır |

### 7.5 İstek başına tüketimi azaltma

| Ayar | Etki |
|------|------|
| `NVIDIA_MAX_TOKENS` düşürmek (ör. `1024`) | Üretilen token sayısını, dolayısıyla completion maliyetini sınırlar |
| `NVIDIA_TEMPERATURE` düşük tutmak (`0.2`–`0.3`) | Daha kısa, daha odaklı yanıtlar |
| Daha küçük model seçmek | Rutin analizler için genellikle yeterli |
| Analizi gereksiz tekrarlamamak | `data_points < 3` ise program zaten AI'yı hiç çağırmaz |
| CAIO'yu `include_ai=false` ile çalıştırmak | Kural motoru bulguları AI'sız üretilir, token harcanmaz |

Son madde önemlidir: CAIO'nun asıl değeri kural motorundan gelir ve o
tamamen ücretsizdir.

```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"include_ai": false}' \
     http://127.0.0.1:8000/api/v1/ai/caio/run
```

### 7.6 İstem uzunluğu zaten sınırlı

Program modele ham veri göndermez; Statistics Engine'in hesapladığı metrik
özeti **6000 karakterle** kesilir (`analysis.py`). Bu, hem maliyeti hem de
gizlilik yüzeyini yapısal olarak sınırlar. AI Developer Console'da da
bağlam sınırı vardır: `MAX_CONTEXT_CHARS = 60_000`, dosya başına
`MAX_FILE_BYTES = 200_000`.

---

## 8. Gizlilik

### 8.1 Bulut modele ne gönderiliyor?

`analysis.run_analysis()` içinde modele giden içerik açıkça kurulur:

* Kullanıcının **sorusu**
* Statistics Engine'in **hesapladığı metrikler** (dereceler, oranlar, tutarlar,
  doluluk, devam yüzdeleri)
* Kapsam öğrenci bazlıysa öğrencinin **adı-soyadı**
* Bu metriklerin ilk 6000 karakterlik JSON özeti

**Gönderilmeyenler:** ham veritabanı satırları, kimlik numarası, iletişim
bilgileri, parolalar, API anahtarları, tam tablo dökümleri.

Buna rağmen dikkat: **öğrenci adı ve performans/finans verileri
gönderilebilir.** Örneğin `payment_risk` kapsamında geciken faturaların
öğrenci adı ve borç tutarı, `student_performance` kapsamında sporcunun adı
ve tüm dereceleri metrik özetine girer.

### 8.2 KVKK açısından değerlendirme

Aşağıdakiler bir hukuki görüş değil, kontrol listesidir. Kurumunuzun veri
sorumlusu ve hukuk danışmanıyla birlikte değerlendirin.

| Kontrol | Soru | Bu programdaki karşılık |
|---------|------|-------------------------|
| **Hukuki dayanak** | Kişisel veriyi bir bulut hizmet sağlayıcısına aktarmanın dayanağı ne? | Öğrenci kayıtlarında açık rıza alanı vardır; CAIO rızasız aktif öğrencileri `compliance` bulgusu olarak raporlar |
| **Yurt dışına aktarım** | Bulut sağlayıcı sunucuları nerede? Aktarım koşulları sağlanıyor mu? | NVIDIA Build bulut hizmetidir; koşulları sağlayıcının şartlarından **kendiniz** doğrulamalısınız |
| **Veri minimizasyonu** | Gereğinden fazla veri gönderiliyor mu? | Ham veri gönderilmez; yalnızca hesaplanmış metrik özeti (≤6000 karakter) gider |
| **Özel nitelikli veri** | Sağlık verisi buluta gidiyor mu? | Sağlık notu alanı analiz metriklerine dahil edilmez; yine de **sağlık içerikli serbest metin soruları buluta göndermeyin** |
| **Saklama** | İstem metni saklanıyor mu? | `AI_LOG_PROMPTS=false` (varsayılan) iken saklanmaz |
| **Aydınlatma** | Veli/öğrenci bulut AI kullanımından haberdar mı? | Aydınlatma metninize bu maddeyi ekleyin |
| **Erişim kontrolü** | Kim AI kullanabiliyor? | `ai:use` izni; yapılandırma için `ai:configure` |
| **İzlenebilirlik** | Kim ne zaman hangi modele ne sordu? | `ai_tasks` tablosu + denetim kaydı |
| **Sağlayıcı politikası** | Gönderilen veri model eğitiminde kullanılıyor mu? | Sağlayıcının güncel şartlarından **kendiniz** doğrulayın |

### 8.3 Hassas veri için yerel model önerisi

Aşağıdaki durumlarda **bulut yerine yerel model** kullanın:

* Sağlık notu, engel/özel ihtiyaç bilgisi içeren analizler
* Bireysel öğrenci adı geçen ayrıntılı performans/finans yorumları
* Veli iletişim bilgisi içeren tahsilat senaryoları
* Kurumsal politikanın veri çıkışını yasakladığı her durum

Kapalı devre yapılandırma:

```dotenv
AI_DEFAULT_MODE=local
AI_FALLBACK_CHAIN=local
NVIDIA_ENABLED=false
OPENAI_COMPAT_ENABLED=false
AI_LOG_PROMPTS=false
```

Doğrulama: `GET /api/v1/ai/control-center` yanıtında
`"mode": "local"`, `"fallback_chain": ["local"]`, `"local_only_mode": true`.

Yerel kurulum: [LOCAL_AI.md](LOCAL_AI.md)

### 8.4 Arayüzdeki gizlilik uyarısı

`NvidiaProvider.public_info()` her sağlayıcı satırına bir uyarı ekler ve bu
uyarı AI Merkezi > Kontrol Merkezi'nde gösterilir:

> "Bulut model: gönderilen veriler NVIDIA sunucularında işlenir. Kişisel veri
> gönderirken dikkatli olun."

Yerel sağlayıcı için karşılığı:

> "Yerel model: veriler bilgisayarınızdan dışarı çıkmaz. Hassas öğrenci
> verileri için önerilir."

---

## 9. Sorun Giderme

### 9.1 HTTP 401 — Yetkisiz (anahtar sorunu)

**Belirti:** Hata metni `[nvidia] HTTP 401: ...`. Bağlantı testi 1. adımda
`FAIL`, kalan beş test `SKIPPED`.

| Olası sebep | Çözüm |
|-------------|-------|
| `NVIDIA_API_KEY` boş | Anahtarı `.env`'e girin veya AI Merkezi > Ayarlar'dan kaydedin |
| Anahtar yanlış kopyalanmış | Baştaki/sondaki boşluk, tırnak veya satır sonu olmamalı |
| Anahtar iptal edilmiş / süresi dolmuş | build.nvidia.com'dan yeni anahtar üretin |
| `.env` değişti ama uygulama okumadı | `POST /api/v1/ai/reload` veya programı yeniden başlatın |
| `.env` dosyası yanlış yerde | Proje kökünde olmalı: `C:\SwimmingSchool\.env` |

Doğrulama — anahtarın tanımlı olup olmadığını (değerini görmeden) kontrol edin:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://127.0.0.1:8000/api/v1/ai/config
```

`nvidia.api_key_set` alanı `false` ise anahtar hiç okunmamıştır.

> **Not:** Anahtarı `.env` dosyasında tırnak içine almayın:
> `NVIDIA_API_KEY=nvapi-xxx` doğru, `NVIDIA_API_KEY="nvapi-xxx"` değeri
> tırnakla birlikte okutabilir.

### 9.2 HTTP 429 — Kota / hız sınırı

**Belirti:** `[nvidia] HTTP 429: ...`. Genelde 1. ve 2. test geçer,
3. test (`simple_prompt`) başarısız olur.

| Olası sebep | Çözüm |
|-------------|-------|
| Dakikalık/saatlik istek limiti aşıldı | Bekleyin, ardından tekrar deneyin |
| Hesap kredisi/kotası bitti | build.nvidia.com panelinden kullanımınızı kontrol edin |
| Çok sayıda eşzamanlı analiz | Toplu analizleri sıraya yayın |
| Gereksiz bulut kullanımı | `AI_FALLBACK_CHAIN=local,nvidia` ile yerel önceliklendirin |

Kalıcı çözüm: rutin analizleri yerele alın
(`AI_DEFAULT_MODE=local` veya yerel öncelikli zincir).

### 9.3 Zaman aşımı

**Belirti:** `[nvidia] Zaman aşımı (120s)`. Görev geçmişinde durum `failed`.

| Olası sebep | Çözüm |
|-------------|-------|
| Büyük model + uzun yanıt | `NVIDIA_MAX_TOKENS` değerini düşürün |
| `NVIDIA_TIMEOUT` düşük | `180`–`300` yapın (arayüzden en fazla 900) |
| Ağ yavaş veya kararsız | Bağlantınızı test edin |
| Kurumsal proxy/güvenlik duvarı isteği yavaşlatıyor | Ağ yöneticinizle `integrate.api.nvidia.com` erişimini doğrulayın |
| Sağlayıcı tarafında yoğunluk | Daha sonra deneyin; fallback zinciri yerele düşmeli |

Fallback devredeyse yerel sağlayıcı yanıtı üretir ve yanıtta
`fallback_used: true` görünür — kullanıcı kesinti yaşamaz.

### 9.4 Model bulunamadı

**Belirti:** `HTTP 404` ya da `[nvidia] Kullanılabilir model bulunamadı`.

| Olası sebep | Çözüm |
|-------------|-------|
| `NVIDIA_MODEL` kimliği yanlış yazılmış | `GET /api/v1/ai/providers/nvidia/models` ile doğru `id` değerini alın |
| Model katalogdan kaldırılmış / adı değişmiş | Güncel listeden yeni bir model seçin |
| Hesabınız o modele erişemiyor | Panelden erişim durumunuzu kontrol edin |
| `NVIDIA_MODEL` boş ve API hiç model döndürmüyor | Anahtar veya hesap yetkisi sorunudur (bkz. 401) |

`NVIDIA_MODEL` boş bırakılırsa program listedeki **ilk** modeli kullanır;
bu davranış öngörülebilir değildir, üretimde model kimliğini açıkça yazın.

### 9.5 Bağlantı hatası (ağ)

**Belirti:** `[nvidia] Bağlantı hatası: ConnectError`.

| Olası sebep | Çözüm |
|-------------|-------|
| İnternet yok | Bağlantıyı kontrol edin |
| `NVIDIA_BASE_URL` yanlış | `https://integrate.api.nvidia.com/v1` (sonda `/v1` olmalı) |
| Güvenlik duvarı/proxy engelliyor | Ağ yöneticinizle konuşun |
| DNS sorunu | Adresi tarayıcıdan test edin |

### 9.6 Sağlayıcı hiç denenmiyor

**Belirti:** Görev geçmişinde `attempted_providers` içinde `nvidia` hiç yok;
bağlantı testinde altı test birden `SKIPPED`.

`NvidiaProvider.enabled` iki koşula birden bağlıdır:

```python
return super().enabled and bool(self.api_key)
#      ↑ _enabled (NVIDIA_ENABLED) ve base_url dolu   ↑ anahtar tanımlı
```

Kontrol listesi:

1. `NVIDIA_ENABLED=true` mi?
2. `NVIDIA_API_KEY` dolu mu? (`api_key_set: true`)
3. `NVIDIA_BASE_URL` boş değil mi?
4. `AI_FALLBACK_CHAIN` içinde `nvidia` var mı?
5. `AI_DEFAULT_MODE=local` olarak ayarlanmamış mı? (bu ayar buluta düşmeyi kapatır)
6. `.env` değişikliği sonrası `POST /api/v1/ai/reload` çağrıldı mı?

### 9.7 JSON testi başarısız

**Belirti:** 1–3 `PASS`, `json_output` `FAIL`.

Model serbest metin üretiyor ama katı JSON üretemiyor. AI Analizi ve Sohbet
çalışır; **AI Developer Console yama üretimi güvenilmez olur** (ajan katı
şema ister ve şema dışına çıkan yanıtı reddeder). Çözüm: talimat takibi
güçlü, *instruct* ince ayarlı bir modele geçin.

### 9.8 Loglara bakma

| Dosya | İçerik |
|-------|--------|
| `logs/ai.log` | Sağlayıcı çağrıları, model, token, süre, fallback geçişleri |
| `logs/application.log` | Genel uygulama akışı |

Loglar `RedactingFilter`'dan geçer: `nvapi-...` biçimli anahtarlar
`nvapi-***REDACTED***` olarak yazılır. Log dosyalarını paylaşmadan önce yine
de gözden geçirin.

---

## İlgili belgeler

* [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) — Sağlayıcı soyutlaması, yönlendirme, fallback
* [LOCAL_AI.md](LOCAL_AI.md) — LM Studio ile yerel model kullanımı
* [DEVELOPER_AGENT.md](DEVELOPER_AGENT.md) — AI Developer Console ve CAIO güvenlik kılavuzu
* [../.env.example](../.env.example) — Tüm ortam değişkenlerinin şablonu
