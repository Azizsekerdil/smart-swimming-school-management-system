# Gizlilik Notu / Privacy Notice

Bu belge, **yazılımın kendisinin** kişisel veriyi nasıl işlediğini anlatır.
Bir kuruma özel gizlilik politikası değildir; kurumun kendi aydınlatma metnini
ve veri işleme envanterini hazırlaması gerekir.

This document describes how **the software itself** handles personal data. It
is not an organisation-specific privacy policy; each deploying organisation must
produce its own notice and processing record.

---

## 1. Kim veri sorumlusudur?

**Yazılımı kuran kurum** (yüzme okulu) veri sorumlusudur. Bu depo bir hizmet
sunmaz, veri toplamaz ve hiçbir sunucuya veri göndermez. Yazılım kurumun kendi
donanımında çalışır; veritabanı kurumun diskindedir.

Proje sahibi **hiçbir kullanıcı verisine erişemez** ve hiçbir telemetri
toplamaz. Ürün içinde analitik, çökme raporlama veya kullanım ölçümü
gönderen bir bileşen **yoktur**.

---

## 2. Hangi kişisel veriler işlenir?

Şema, kişisel veri alanlarını açıkça kayıt altına alır
(`backend/app/services/hsp/classification.py` — 31 sınıflandırılmış alan).
Özet:

| Veri sahibi | Alanlar | Sınıf |
|---|---|---|
| Öğrenci (**çoğunlukla çocuk**) | ad, soyad, doğum tarihi, T.C. kimlik no, telefon, e-posta, adres, acil durum iletişimi, yüzme seviyesi, hedefler, notlar | Gizli |
| Öğrenci — özel nitelikli | **sağlık notları**, **özel gereksinim** | Kısıtlı / özel nitelikli |
| Veli | ad, soyad, telefon, e-posta, T.C. kimlik no, yakınlık derecesi | Gizli |
| Eğitmen / personel | ad, soyad, telefon, e-posta, sertifikalar, **maaş** | Gizli / kısıtlı |
| İşlem verisi | yoklama, ders kaydı, üyelik, ödeme, fatura, performans ölçümü | Gizli |
| Sistem | kullanıcı e-postası, parola **özeti** (hash), giriş denemeleri, denetim kaydı | Gizli |

**Çocuk verisi** ayrı olarak işaretlenir (`may_concern_child`) ve politika
motoru bunu daha katı bir kural kümesine tabi tutar.

---

## 3. Erişim sınırları

* **Rol tabanlı yetki:** 21 rol, 52 ayrı izin.
* **Özel nitelikli veri maskeleme:** `student:read_sensitive` izni olmayan bir
  kullanıcı sağlık notu ve özel gereksinim alanlarını **göremez**; alan
  maskelenerek döner ve yazma da reddedilir.
* **Satır/nesne bazlı kapsam:** veli, öğrenci ve sporcu rolleri yalnızca kendi
  (ya da çocuklarının) kaydını görür. Tek ortak mekanizma
  `AccessScope` (`backend/app/api/deps.py`) üzerinden uygulanır:
  * liste uçları öğrenci kimliğine göre süzülür,
  * tekil nesne uçları erişim öncesi doğrulanır (IDOR koruması),
  * kurum geneli/kohort ötesi toplulaştırmalar bu roller için tamamen
    reddedilir.
  * Ders listesi ve yoklama ekranı da süzülür: bir veli sınıftaki **diğer**
    çocukları görmez.
  * Regresyon testleri: `backend/tests/test_row_level_authorisation.py`.
* **Denetim kaydı:** oluşturma, güncelleme, silme, giriş, parola değişimi ve
  yedekleme işlemleri kaydedilir. Denetim kaydına parola, anahtar veya özel
  nitelikli değer **yazılmaz**.

---

## 4. Yapay zekâ ve veri asgarileştirme

Ayrıntı: [`AI_TRANSPARENCY.md`](AI_TRANSPARENCY.md).

Özet:

* **Bütün** AI çağrıları tek bir geçitten geçer
  (`backend/app/services/hsp/gateway.py`): sohbet, akışlı sohbet, geliştirici
  ajanı ve CAIO dâhil. Bu, testle de doğrulanır
  (`backend/tests/test_ai_privacy_gateway.py`).
* Geçit sırayla: yükü sınıflandırır → hedef sağlayıcının kanıtını çözer →
  politikayı **çağrıdan önce** çalıştırır → kararı uygular (gönder /
  takma adlaştır / yerele zorla / **engelle**) → hak makbuzu üretir.
* **Serbest metin de taranır.** Sohbet uçları yapılandırılmış alan listesi
  taşımadığı için giden metin, kayıt defterine karşı taranır
  (`backend/app/services/hsp/freetext.py`): telefon, e-posta, kimlik numarası,
  sağlık/özel gereksinim anahtar kelimeleri ve veritabanındaki gerçek kişi
  adları tespit edilir.
* **Takma adlaştırma:** gerçek adlar, `SECRET_KEY` ile anahtarlanmış
  HMAC-SHA-256 türevi kararlı takma adlarla değiştirilir ve yanıt yalnızca
  uygulama içinde geri eşlenir.
* **Sağlık notları** bulut sağlayıcıya gönderilen yüke dâhil edilmez.
* **Yerel öncelik:** varsayılan zincir `local,nvidia`'dır ve NVIDIA varsayılan
  olarak **kapalıdır**. Yerel model kullanıldığında hiçbir veri kurumdan çıkmaz.
* **İstem metni saklanmaz:** `AI_LOG_PROMPTS=false` (varsayılan) iken görev
  başlığı dâhil hiçbir alanda istem metni saklanmaz.

---

## 5. Demo verisi

`SEED_DEMO_DATA` ile üretilen bütün kayıtlar **sentetiktir**:

* adlar sabit havuzlardan üretilir (`backend/app/db/seed.py`),
* e-posta adresleri RFC 6762 ile ayrılmış, yönlendirilemeyen `.local` alan
  adını kullanır,
* telefon numaraları hiçbir numaralandırma planında tahsisli olmayan `0000`
  ön ekiyle üretilir; **aranamazlar**,
* her satır `is_demo = true` ile işaretlenir,
* üretim ortamında (`APP_ENV=production`) tohumlama çalışmayı **reddeder**.

Depodaki sunum PDF'lerinde görünen bütün kayıtlar bu sentetik veridir. Gerçek
hiçbir öğrenci, veli, çocuk veya personel verisi yayımlanmamıştır.

---

## 6. Saklama, silme ve dışa aktarma

| Konu | Durum |
|---|---|
| Kayıt silme | Uygulama içinden yapılabilir (yetkiye bağlı). |
| Dışa aktarma | Rapor motoru XLSX/PDF üretir. |
| **Otomatik saklama süresi (retention) motoru** | **YOK.** Süre dolan kayıtları otomatik silen bir bileşen yoktur; saklama süresi kurumun elle yönetmesi gereken bir konudur. Bkz. `docs/known-limitations.md`. |
| Yedekler | Şifrelenmez (düz ZIP). Yedeklerin bulunduğu diskin şifrelenmesi kurumun sorumluluğundadır. |
| `.env` | Yedeklere **dâhil edilmez**. |

---

## 7. Yasal not

Bu belge hukuki danışmanlık değildir. KVKK, GDPR ya da başka bir mevzuata
uyum, yazılımın tek başına sağlayabileceği bir sonuç değildir: aydınlatma
metni, açık rıza yönetimi, veri işleme envanteri, saklama süreleri ve veri
sahibi başvuru süreçleri kurumun sorumluluğundadır.

Yazılım bu süreçleri **destekleyen** teknik yapılar sunar (rıza/bildirim
tabloları, hak makbuzları, veri haritası, sınıflandırma kayıt defteri) ancak
uyumu **garanti etmez** ve öyle bir iddiada bulunmaz.
