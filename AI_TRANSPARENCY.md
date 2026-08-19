# Yapay Zekâ Şeffaflık Notu / AI Transparency Notice

Bu belge, üründeki yapay zekâ kullanımını, verinin nereye gittiğini ve neyin
**yapılmadığını** açıkça anlatır.

---

## 1. Yapay zekâ ne için kullanılır?

| Kullanım | Ne yapar | Ne yapmaz |
|---|---|---|
| **Analiz yorumu** | İstatistik motorunun **hesapladığı** metrikleri metne çevirir. | Sayı üretmez, tahmin etmez. Sayılar veritabanından gelir. |
| **Sohbet (AI Merkezi)** | Operatörün sorusunu yanıtlar. | Otomatik işlem yapmaz; hiçbir kaydı değiştirmez. |
| **CAIO ajanı** | Toplulaştırılmış sistem ölçümlerinden yönetici özeti ve öneri üretir. | Öneriyi uygulamaz; öneri statüsünde kaydeder. |
| **AI Developer Console** | Proje kaynak kodunda değişiklik **önerisi** (yama) üretir. | Onaysız uygulamaz. Varsayılan olarak hem kabuk hem yama uygulama **kapalıdır**. |

**Yapay zekâ hiçbir yerde otonom karar vermez.** Kayıt oluşturma, silme,
ödeme, ders planlama gibi işlemler yalnızca kullanıcı eylemiyle gerçekleşir.

---

## 2. Hangi sağlayıcılar desteklenir?

| Sağlayıcı | Tür | Varsayılan | Veri nereye gider |
|---|---|---|---|
| **LM Studio** | Yerel (loopback) | **Açık** | Hiçbir yere — model kendi bilgisayarınızda çalışır. |
| **NVIDIA Build** | Bulut | **Kapalı** | NVIDIA'nın altyapısına. Açıkça etkinleştirilmelidir. |
| Genel OpenAI-uyumlu uç | Yapılandırılabilir | **Kapalı** | Sizin belirlediğiniz uca. |

Anthropic, Gemini, Azure OpenAI, Ollama veya vLLM için bir bağdaştırıcı
**yoktur**.

**Varsayılan zincir `local,nvidia`'dır**: yerel model önce denenir. Politika
motoru bir çağrıyı `LOCAL_ONLY` olarak işaretlediğinde, bulut sağlayıcı
zincirden çıkarılır — sağlayıcı hatası bile bu kararı gevşetemez.

---

## 3. API anahtarı yoksa ne olur?

Anahtar tanımlı değilken ilgili sağlayıcı **NOT_CONFIGURED** durumundadır ve
**hiçbir ağ çağrısı yapmaz**. Uygulama çökmez:

* yerel yapay zekâ (LM Studio) kuruluysa çalışmaya devam eder,
* yapay zekâ ile ilgisi olmayan bütün özellikler (kayıt, ders, yoklama,
  üyelik, finans, performans, rapor, yedekleme) normal çalışır,
* AI özellikleri arayüzde "kullanılamıyor" olarak raporlanır.

Arayüz bir anahtarı asla tam olarak göstermez: yalnızca **sağlayıcı adı,
durum ve son 4 karakter** görünür. "Bağlantıyı test et" yalnızca kullanıcı
açıkça tıkladığında çalışır ve anahtar hiçbir koşulda loglanmaz.

---

## 4. Gizlilik geçidi — verinin izlediği yol

Bütün AI çağrıları tek bir geçitten geçer:
`backend/app/services/hsp/gateway.py`.

```
  istek
    │
    ▼
  [1] Sınıflandırma      hangi alanlar var? çocuk verisi mi? özel nitelikli mi?
    │                    (serbest metin ise: freetext.scan ile taranır)
    ▼
  [2] Sağlayıcı kanıtı   bölge, saklama, eğitimde kullanım, DPA, aktarım
    │                    (bulut için kanıt YOKSA politika bunu ALEYHTE okur)
    ▼
  [3] Politika kararı    ÇAĞRIDAN ÖNCE çalışır
    │
    ▼
  [4] Kararı uygula      gönder │ takma adlaştır │ maskele │ yerele zorla │ ENGELLE
    │
    ▼
  [5] Sağlayıcı çağrısı  yalnızca politikanın izin verdiği sağlayıcılarla
    │
    ▼
  [6] Geri eşleme        takma ad → gerçek ad, YALNIZCA uygulama içinde
    │
    ▼
  [7] Hak makbuzu        hash zincirine eklenen, kurcalanması belli olan kayıt
```

**Karar `BLOCK` ise çağrı yapılmaz.** Bu, sözleşmenin en sert maddesidir.

### Bu gerçekten bütün yollara uygulanıyor mu?

Evet — ve bu bir iddia değil, **testle zorlanan** bir kısıttır.
`backend/tests/test_ai_privacy_gateway.py`, sohbet ucunun, akışlı sohbet
ucunun, geliştirici ajanının ve CAIO'nun kaynak kodunu AST ile ayrıştırır ve
geçidi atlayan doğrudan bir sağlayıcı çağrısı kalmadığını doğrular. Bu test
kırılmadan geçidin etrafından dolaşan yeni bir çağrı yolu eklenemez.

### Serbest metin nasıl ele alınır?

Sohbet uçları yapılandırılmış bir alan listesi taşımaz — operatör ne yazarsa o
gider. Bu yüzden giden metin, kayıt defterine karşı taranır
(`backend/app/services/hsp/freetext.py`):

* e-posta, telefon, T.C. kimlik numarası biçimi, IBAN, doğum tarihi kalıbı,
* sağlık / özel gereksinim / finansal borç / acil durum anahtar kelimeleri
  (Türkçe ve İngilizce, büyük-küçük harf ve aksandan bağımsız),
* veritabanındaki **gerçek** öğrenci, veli ve eğitmen adları.

Tespit **muhafazakârdır**: şüpheli bir kalıp bulunduğunda alan bildirilir.
Yanlış pozitif veriyi gereksiz yere takma adlaştırır (zararsız); yanlış negatif
kişisel veriyi yönetişimsiz gönderir (kabul edilemez).

Taranan metin **hiçbir yerde saklanmaz veya loglanmaz**; taramadan yalnızca
alan yolları çıkar.

---

## 5. İnsan onayı

| İşlem | Onay |
|---|---|
| Kod değişikliği uygulama (AI Developer) | **Zorunlu.** `confirm=true` gerekir, ayrıca `AI_DEVELOPER_ALLOW_APPLY` varsayılan olarak kapalıdır. Otomatik checkpoint alınır; testler başarısızsa değişiklik **otomatik geri alınır**. |
| Kabuk komutu çalıştırma | `AI_DEVELOPER_ALLOW_SHELL` varsayılan olarak **kapalı**. Açıksa bile komut beyaz listesi, alt komut beyaz listesi ve 30+ yasak desen uygulanır; yorumlayıcı bayrakları (`python -c`) **kabul edilmez**. |
| Analiz / sohbet | Ayrıca onay istenmez — çağrı zaten kullanıcı eylemiyle başlar ve politika kapısından geçer. |
| Bulut sağlayıcıyı etkinleştirme | Kurulumu yapan kişinin açık eylemi gerekir (varsayılan kapalı). |

---

## 6. Ne iddia edilmez

* **Tıbbi, sağlık veya beslenme tavsiyesi verilmez.** Sağlık notu alanları
  yalnızca operasyonel bir not alanıdır; yapay zekâ bunları yorumlamaz ve
  buluta gönderilen yüke dâhil edilmez.
* **Finansal veya yatırım tavsiyesi verilmez.** Finans modülü tahsilat ve gider
  takibidir; yapay zekâ çıktısı bir muhasebe ya da vergi görüşü değildir.
* **Hukuki uyum garantisi verilmez.** Bkz. `PRIVACY.md`.
* **Performans skorları bir tahmin değildir.** "Yarışma hazırlık göstergesi"
  tamamen istatistikseldir (tutarlılık, forma yakınlık, gelişim eğilimi,
  antrenman hacmi) ve arayüzde bu açıkça yazılıdır.
* **Yapay zekâ çıktısı doğrulanmamıştır.** Dil modelleri hatalı ifade
  üretebilir. Arayüz, gerçek (hesaplanmış) veriyi ve AI yorumunu **ayrı
  panellerde** gösterir; ikisi karıştırılmaz.

---

## 7. Maliyet ve kota

Ürün, sağlayıcı tarafında **maliyet tavanı veya token bütçesi uygulamaz**.
Bulut sağlayıcıyı etkinleştirirseniz oluşacak kullanım ücretleri size aittir;
sınırı sağlayıcı hesabınızdan yönetin. Bu bilinen bir eksiktir, bkz.
`docs/known-limitations.md`.

---

## 8. Yönetişim özelliği hakkında dürüst bir not

Bu depodaki gizlilik geçidi, sınıflandırma kayıt defteri, sağlayıcı kanıt
kaydı ve hak makbuzu zinciri bir **kurumsal yönetişim özelliğidir**: kurumun
kendi yapay zekâ kullanımını denetlenebilir kılmayı amaçlar.

Bu bileşenler için **"patentli", "benzersiz" veya "dünyada bir ilk" gibi bir
iddiada bulunulmaz.** Benzer fikirler yayımlanmış literatürde ve başka
ürünlerde mevcuttur. Buradaki katkı, bunların tek bir çalışan üründe uçtan
uca bağlanmış ve testlerle zorlanmış olmasıdır — daha fazlası değil.
