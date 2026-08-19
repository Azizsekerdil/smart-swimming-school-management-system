"""Takma adlaştırma ve maskeleme / Pseudonymisation and redaction.

Politika motoru "bu alan takma adlaştırılsın" dediğinde uygulamayı bu modül
yapar.

Önemli ayrım (§11, §35): **takma adlaştırma anonimleştirme değildir.**
Buradaki takma adlar kurumun anahtarıyla üretilir ve aynı kişi için kararlıdır;
bu, analizi mümkün kılar ama kişiyi hâlâ ayırt edilebilir tutar. Bu yüzden
takma adlaştırılmış veri de kişisel veridir ve öyle etiketlenir.

Takma ad neden kararlı? Model "Öğrenci-A7F3'ün derecesi geriliyor" diyebilsin
ve kullanıcı bunu gerçek öğrenciye geri eşleyebilsin diye. Eşleme yalnızca
uygulama içinde, anahtara sahip olan tarafta yapılır; modele gerçek ad hiç
gitmez.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata

from app.core.config import settings
from app.services.hsp.classification import Handling

REDACTED_TR = "[gizlendi]"
REDACTED_EN = "[redacted]"

# Takma ad öneki — veri sahibi kategorisine göre
_PREFIX = {
    "student": "Öğrenci",
    "guardian": "Veli",
    "instructor": "Eğitmen",
    "staff": "Personel",
}


def _key() -> bytes:
    """Takma ad anahtarı.

    Uygulamanın gizli anahtarından türetilir; ayrı bir sır yönetimi
    gerektirmez ama anahtar değişirse takma adlar da değişir. Bu bilinçlidir:
    anahtar rotasyonu, eski takma adların yeniden eşlenmesini imkânsız kılar.
    """
    secret = settings.secret_key or "hsp-fallback-key"
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _fold(value: str) -> str:
    """Takma ad üretimi için adı kararlı biçime indirger.

    Python'un `str.lower()` metodu Türkçe noktasız I'yı yanlış eşler:
    `"YILMAZ".lower()` → `"yilmaz"` iken `"Yılmaz".lower()` → `"yılmaz"`.
    Kayıtlarda ad sık sık büyük harfle tutulduğundan, düz `lower()` aynı kişiye
    iki farklı takma ad verirdi ve takma adın kararlılık garantisi çökerdi.

    Bu yüzden Türkçeye özgü harfler `lower()` çağrılmadan önce elle eşlenir.
    Ayrıca birleşik (combining) aksan biçimleri NFC ile tek koda indirgenir.
    """
    normalized = unicodedata.normalize("NFC", value.strip())
    return normalized.translate(_TR_FOLD).lower()


# "İ" → "i" ve "I" → "ı": lower() öncesi Türkçe eşleme
_TR_FOLD = str.maketrans({"İ": "i", "I": "ı"})


def pseudonym(value: str, subject: str = "student") -> str:
    """Bir kişi adı için kararlı, geri döndürülemez takma ad üretir.

    Aynı ad her zaman aynı takma adı verir; farklı kurulumlar farklı takma ad
    üretir çünkü anahtar farklıdır.
    """
    if not value:
        return REDACTED_TR
    digest = hmac.new(_key(), _fold(value).encode("utf-8"), hashlib.sha256)
    token = digest.hexdigest()[:4].upper()
    return f"{_PREFIX.get(subject, 'Kişi')}-{token}"


def apply_handling(
    value: object, handling: Handling, subject: str = "student"
) -> object:
    """Tek bir değere işleme kuralını uygular."""
    if handling is Handling.PASS:
        return value
    if handling is Handling.NEVER:
        return None
    if value is None:
        return None
    if handling is Handling.PSEUDONYMIZE:
        return pseudonym(str(value), subject)
    return REDACTED_TR


def scrub_mapping(
    payload: dict,
    field_handling: dict[str, Handling],
    *,
    subject_of: dict[str, str] | None = None,
) -> tuple[dict, list[str]]:
    """Bir sözlüğü politika planına göre temizler.

    Dönüş: (temizlenmiş sözlük, dokunulan alanların listesi).
    `NEVER` işaretli alanlar sözlükten tamamen çıkarılır — boş anahtar bile
    bırakılmaz, çünkü anahtarın varlığı da bilgi sızdırır.
    """
    subject_of = subject_of or {}
    cleaned: dict = {}
    touched: list[str] = []

    # Alan adından işleme kuralını bulmak için kısa ad dizini
    by_name = {
        path.split(".", 1)[-1]: handling for path, handling in field_handling.items()
    }

    for key, value in payload.items():
        handling = by_name.get(key, Handling.PASS)
        if handling is Handling.NEVER:
            touched.append(key)
            continue
        if handling is Handling.PASS:
            cleaned[key] = value
            continue
        cleaned[key] = apply_handling(value, handling, subject_of.get(key, "student"))
        touched.append(key)

    return cleaned, touched


# ---------------------------------------------------------------------------
# Serbest metin içindeki adları takma adla değiştirme
# ---------------------------------------------------------------------------
def replace_names(text: str, names: dict[str, str]) -> str:
    """Metindeki gerçek adları takma adlarla değiştirir.

    `names`: {gerçek ad: takma ad}. Uzun adlar önce değiştirilir ki "Ali Veli"
    içindeki "Ali" kısmi eşleşme yapıp bozuk çıktı üretmesin.
    """
    if not text or not names:
        return text
    for real in sorted(names, key=len, reverse=True):
        if not real:
            continue
        text = re.sub(re.escape(real), names[real], text, flags=re.IGNORECASE)
    return text


def build_name_map(values: list[str], subject: str = "student") -> dict[str, str]:
    """Ad listesinden {gerçek ad: takma ad} eşlemesi kurar."""
    return {name: pseudonym(name, subject) for name in values if name}
