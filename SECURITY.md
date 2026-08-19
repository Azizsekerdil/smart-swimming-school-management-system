# Güvenlik Politikası / Security Policy

> Ürünün güvenlik **mimarisi** `docs/SECURITY.md` içinde ayrıntılı olarak
> anlatılır. Bu dosya, açık bildirimi ve destek kapsamını tanımlar.
>
> The security **architecture** is documented in `docs/SECURITY.md`. This file
> defines vulnerability reporting and the support scope.

---

## Desteklenen sürümler / Supported versions

| Sürüm | Destek |
|---|---|
| `1.0.0-public` (bu depo / this repository) | Güvenlik düzeltmeleri en iyi çaba ile / security fixes on a best-effort basis |
| `< 1.0.0` (özel sürümler / private builds) | Desteklenmiyor / not supported |

Bu proje **tek kişilik, en iyi çaba (best-effort)** ile sürdürülür. Bir hizmet
düzeyi taahhüdü (SLA) verilmez.

This project is maintained by one person on a **best-effort** basis. No service
level agreement (SLA) is offered.

---

## Açık bildirimi / Reporting a vulnerability

**Lütfen güvenlik açıklarını herkese açık bir issue olarak açmayın.**
**Please do not open a public issue for security vulnerabilities.**

1. GitHub'da **Security > Report a vulnerability** (özel güvenlik danışması /
   private security advisory) yolunu kullanın. Bu yol tercih edilir.
2. Bu yol kullanılamıyorsa, deponun sahibine GitHub üzerinden özel bir kanalla
   ulaşın ve konuya `SECURITY` yazın.

Bildiriminizde şunlar yardımcı olur:

* etkilenen sürüm / commit,
* yeniden üretim adımları (mümkünse en küçük örnek),
* etkinin sizce ne olduğu (veri okuma, yetki yükseltme, hizmet reddi …),
* varsa önerdiğiniz düzeltme.

**Yanıt hedefi (taahhüt değil):** ilk yanıt 7 gün, üçlü değerlendirme 14 gün.

Sorumlu açıklama beklenir: düzeltme yayımlanana veya 90 gün geçene kadar
(hangisi önce olursa) ayrıntıları yayımlamamanızı rica ederiz. Bu bir ödül
(bug bounty) programı **değildir**; parasal ödeme yapılmaz.

---

## Kapsam / Scope

**Kapsam içi:** bu depodaki kaynak kod, varsayılan yapılandırma, ilk kurulum
akışı, kimlik doğrulama ve yetkilendirme, veri sınırları, AI geçidi, yedekleme.

**Kapsam dışı:**

* Sizin kurulumunuzdaki yanlış yapılandırma (ör. `SECRET_KEY` boş bırakmak,
  uygulamayı TLS'siz olarak İnternet'e açmak);
* Üçüncü taraf sağlayıcıların (NVIDIA Build, LM Studio) kendi altyapısı;
* Çok kiracılı (multi-tenant) dağıtım — ürün bunu **desteklemez**, bkz.
  `docs/known-limitations.md`;
* Sosyal mühendislik, fiziksel erişim, kullanıcı cihazının ele geçirilmesi.

---

## İlk kurulum kimliği: `admin` / `admin`

Ürün, ilk açılışta **belgelenmiş, tek kullanımlık** bir kurulum kimliğiyle
gelir. Bu bir sır değildir; güvenliği parolanın gizliliğine değil, aşağıdaki
kısıtlara dayanır (uygulaması: `backend/app/core/bootstrap.py`, regresyon
testleri: `backend/tests/test_bootstrap_admin.py`):

| Kısıt | Uygulanışı |
|---|---|
| **Zorunlu parola değişimi** | Parola değişmeden hiçbir korumalı uca erişilemez. Tek istisna `GET /auth/me`, `POST /auth/change-password`, `POST /auth/logout`. Kapı, kimlik doğrulaması gerektiren her ucun ortak noktası olan `get_current_user` içinde uygulanır. |
| **Yalnızca yerel cihaz** | Parola değişene kadar giriş yalnızca döngüsel arabirimden (`127.0.0.1` / `::1`) kabul edilir. `X-Forwarded-For` gibi başlıklara **güvenilmez**; böyle bir başlığın varlığı isteği "uzak" yapar ve reddedilir. |
| **Tek kullanımlık** | Parola bir kez değiştiğinde `admin/admin` kalıcı olarak geçersizdir. Kurulum durumu veritabanında "tamamlandı" olarak işaretlenir; hesap silinse bile varsayılan kimlik geri gelmez. |
| **Sıfırlama varsayılanı geri getiremez** | Parola politikası `admin` değerini reddeder (`FORBIDDEN_PASSWORDS`), ayrıca hem kullanıcı parola değişiminde hem yönetici sıfırlamasında açıkça engellenir. |
| **Hash'li saklama** | bcrypt (cost 12), 72 baytın üzerinde SHA-256 ön özet. Parola değeri hiçbir zaman düz metin olarak veritabanına, loga, hataya, telemetriye, yedeğe, PDF'e veya ekran görüntüsüne yazılmaz. |
| **Kaba kuvvet koruması** | Dakikalık hız sınırı, ardışık hatada **artan gecikme** (2s → 4s → 8s … en çok 60s) ve 8 hatada 15 dakikalık geçici kilit. Denetim kaydı tutulur; parola değeri kaydedilmez. |
| **Uyarı** | README, `.env.example`, giriş ekranı ve zorunlu değişim ekranı aynı uyarıyı gösterir: *"admin / admin — ilk girişte değiştirilmelidir."* |

**Kurtarma:** veritabanında hiç etkin süper kullanıcı kalmazsa kurulum kapısı
yeniden açılır. Bu, veritabanına yerel erişim gerektirir ve `logs/security.log`
dosyasına uyarı olarak yazılır.

---

## API anahtarları / API keys

* Depoda **hiçbir gerçek anahtar yoktur**: kaynakta, testlerde, `.env.example`
  içinde, belgelerde, PDF'lerde, ekran görüntülerinde, loglarda veya SBOM'da.
* `.env.example` yalnızca boş değer ya da `YOUR_PROVIDER_API_KEY_HERE` yer
  tutucusunu içerir.
* Anahtarlar kurulumdan **sonra** kullanıcı tarafından girilir: yerel `.env`,
  bir sır yöneticisi ya da arayüzdeki Ayarlar > Yapay Zekâ ekranı.
* Anahtar tanımlı değilken sağlayıcı **NOT_CONFIGURED** durumundadır ve
  **hiçbir çağrı yapmaz**; yerel yapay zekâ ve AI dışı bütün özellikler
  çalışmaya devam eder.
* Arayüzde yalnızca sağlayıcı adı, durum ve anahtarın **son 4 karakteri**
  gösterilir. "Bağlantıyı test et" yalnızca kullanıcı açıkça tıkladığında
  çalışır; anahtar hiçbir koşulda loglanmaz.
* Loglarda `nvapi-`, `sk-`, `gh*_`, `Bearer …` ve `key/secret/password/token=`
  desenleri bir redaksiyon süzgeciyle maskelenir
  (`backend/app/core/logging_config.py`).

---

## Yayımlama öncesi denetim / Pre-publication review

Sürekli tümleştirmedeki gizli anahtar taraması **yalnızca metin dosyalarını**
tarar. PDF, PPTX ve PNG gibi ikili dosyalar bu taramanın dışındadır ve
ayrıca denetlenmelidir: sunum varlıklarındaki hassas içerik yalnızca raster
katmanda bulunabilir ve metin tabanlı hiçbir tarayıcı onu göremez.

Bu depodaki sunum PDF'leri, kaynağından (demo tohumu → yakalama betiği → PNG →
PPTX → PDF) yeniden üretilmiş, metin katmanı, meta veri, gömülü dosya/JavaScript
ve **OCR ile raster katmanı** ayrı ayrı denetlenmiştir.

---

## Bilinen sınırlar / Known limits

Ürünün kasıtlı olarak **yapmadığı** şeyler ve açık eksikler
`docs/known-limitations.md` içinde tek tek listelenir. Bir güvenlik
değerlendirmesi yapmadan önce lütfen o dosyayı okuyun.
