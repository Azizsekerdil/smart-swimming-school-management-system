# Tanıtım Sunumu / Introduction Deck

Akıllı Yüzme Okulu Yönetim Sistemi'nin **52 slaytlık** tanıtım sunumu, dört
varyantta üretilir. Slaytların 17'si programın **gerçek arayüz görüntülerini**
taşır.

| Dosya | Dil | Tema | Kullanım |
|---|---|---|---|
| `Yuzme_Okulu_Tanitim.pptx` | Türkçe | Koyu | Projeksiyon, ekran sunumu |
| `Yuzme_Okulu_Tanitim.pdf` | Türkçe | Koyu | E-posta, paylaşım |
| `Yuzme_Okulu_Tanitim.html` | Türkçe | Koyu | Telefon/tablet, çevrimdışı, tek dosya |
| `Yuzme_Okulu_Tanitim_Baski.pptx` | Türkçe | Açık | Yazıcı çıktısı |
| `Yuzme_Okulu_Tanitim_Baski.pdf` | Türkçe | Açık | Basılı dağıtım |
| `Yuzme_Okulu_Intro_EN.*` | İngilizce | Koyu | Aynı set |
| `Yuzme_Okulu_Intro_EN_Print.*` | İngilizce | Açık | Aynı set |

## Arayüz görüntüleri

Ekran görüntüleri **çalışan uygulamadan** alınır. Hiçbir ekran elle çizilmez,
taklit edilmez veya mockup ile değiştirilmez.

> **Veri uyarısı.** Slaytlarda görünen bütün kayıtlar **sentetik demo
> verisidir**. Adlar `backend/app/db/seed.py` içindeki sabit havuzlardan
> üretilir, e-posta adresleri yönlendirilemeyen `.local` alan adını kullanır ve
> telefon numaraları hiçbir numaralandırma planında tahsisli olmayan `0000`
> ön ekiyle üretildiği için **aranamaz**. Hiçbir gerçek öğrenci, veli, çocuk
> veya personel verisi bu sunumda yer almaz.

Deste ile arayüz aynı görsel dili konuşur: **koyu deste koyu arayüzü, baskı
destesi açık arayüzü** gösterir. Bu, ürünün iki temayı da desteklediğini
sunumun kendisiyle kanıtlar.

| Slayt türü | Adet | İçerik |
|---|---:|---|
| Tekil ekran (`shot`) | 15 | Büyük ekran görüntüsü + 4 açıklama maddesi |
| Galeri (`gallery`) | 2 | 3'lü ızgarada 9 ekran, altında başlık |
| **Toplam ekran** | **24** | 24 arayüz ekranının tamamı |

Ekran slaytları anlatıya serpiştirilmiştir: her ekran, kendisini anlatan
özellik slaytının hemen ardından gelir. Böylece "ne yapıyor" ile "nasıl
görünüyor" yan yana okunur.

## HTML görüntüleyici

Tek dosyadır, 52 slaytı gömülü PNG olarak taşır ve internet bağlantısı
gerektirmez. Dokunmatik ekranda kaydırarak, bilgisayarda ok tuşlarıyla
ilerler; slayta dokunulduğunda tam ekran açılır. Telefonda dikey tutulduğunda
slaytı otomatik olarak yatay çevirir.

## Yeniden üretme

**1. Ekran görüntülerini yakala** (uygulama çalışıyor olmalı):

```
python tools/capture_screens.py --theme both --lang both
```

`START_SWIMMING_SCHOOL.bat` ya da `uvicorn` ile backend ayakta olmalı ve
frontend derlenmiş olmalıdır (`BUILD_FRONTEND.bat`). 96 görüntü üretir
(24 ekran × 2 tema × 2 dil).

**2. Desteyi üret:**

```
python tools/build_presentation.py
```

PPTX üretimi saf Python'dur (`python-pptx`). PDF ve PNG dönüşümü Windows'ta
kurulu PowerPoint'i COM üzerinden kullanır (`pywin32`); PowerPoint yoksa PPTX
dosyaları yine üretilir, eksik adımlar raporlanır.

Yalnızca PPTX üretmek için `--pptx` ekleyin.

## İçerik nereden geliyor?

| Dosya | Sorumluluk |
|---|---|
| `tools/presentation_theme.py` | Renk rolleri (koyu/açık) ve yerleşim ızgarası |
| `tools/presentation_render.py` | Slayt çizim blokları — hiçbir renk sabit yazılmaz |
| `tools/presentation_content.py` | 35 anlatı slaytının TR ve EN metinleri |
| `tools/presentation_shots.py` | 17 ekran slaytı ve bunların bağlandığı başlıklar |
| `tools/capture_screens.py` | Çalışan uygulamadan ekran yakalama |
| `tools/build_presentation.py` | Üretim akışı: serpiştir → PPTX → PDF → PNG → HTML |

Koyu ve açık varyantlar **aynı içerik ve aynı yerleşimden** üretilir; yalnızca
tema nesnesi değişir. Bu yüzden ekran ve baskı sürümleri arasında içerik farkı
oluşmaz.

Ekran slaytları `after` alanıyla bir başlığa bağlanır. Başlık destede
bulunamazsa üretim **durur** — ekran sessizce yanlış yere ya da sona atılmaz.

## Sayılar hakkında

Slaytlardaki bütün rakamlar (240 API ucu, 55 tablo, 21 rol, 395 test
fonksiyonu, 16 rapor şablonu, 28 istatistik fonksiyonu vb.) yayımlanan kaynak
koddan ve veritabanı şemasından **mekanik olarak** ölçülmüştür; hiçbiri elle
yazılmamıştır. Henüz tamamlanmamış yetenekler — RFID/NFC donanım entegrasyonu ve
bulut yedekleme — slaytlarda açıkça "altyapı hazır / sonraki sürüm" olarak
işaretlenir.

## Sürüm kontrolü

`.pptx` ve `.pdf` dosyaları sürümlenir (yaklaşık 40 MB). Şunlar yoksayılır ve
yukarıdaki iki komutla yeniden üretilir:

- `.html` görüntüleyiciler (~9,4 MB × 2)
- `ekranlar/` altındaki 96 ham görüntü (~34 MB)
- `ekranlar/_olcekli/` ölçekli önbellek (~22 MB)

Ham görüntüler gömülmeden önce 1600 piksel genişliğe küçültülür; yakalama 2x
ölçekle yapıldığı için bu, dosya boyutunu yaklaşık yarıya indirir ve slayttaki
netliği etkilemez.
