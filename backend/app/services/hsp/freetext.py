"""Serbest metin yükleri için veri asgarileştirme tarayıcısı.

Free-text payload scanner for data minimisation.

Sohbet uçları (``/ai/chat``, ``/ai/chat/stream``) yapılandırılmış bir alan
listesi taşımaz: operatör ne yazarsa o gider. Bu modül gönderilecek metni
tarayarak kayıt defterindeki (``classification.FIELD_REGISTRY``) hangi kişisel
veri alanlarının metinde **fiilen** bulunduğunu tespit eder.

Böylece HSP geçidi serbest metni de aynı politikayla değerlendirebilir:
sınıflandırma → sağlayıcı kanıtı → karar (gönder / takma adlaştır / yerele
zorla / engelle) → hak makbuzu.

Tasarım notları:

* Tespit **muhafazakârdır**: şüpheli bir kalıp bulunduğunda alan bildirilir.
  Yanlış pozitif, veriyi gereksiz yere takma adlaştırır (zararsız); yanlış
  negatif ise kişisel veriyi yönetişimsiz gönderir (kabul edilemez).
* Ad eşleştirmesi veritabanındaki gerçek veri sahiplerine karşı yapılır, bu
  yüzden takma adlaştırma yalnızca gerçekten var olan kişiler için üretilir.
* Metin **hiçbir zaman** loglanmaz veya saklanmaz; yalnızca alan yolları döner.
"""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

# Bir taramada eşleştirilecek en fazla veri sahibi adı (performans sınırı)
MAX_SUBJECT_NAMES = 5000
# Ad eşleştirmesinde kabul edilen en kısa ad (çok kısa adlar gürültü üretir)
MIN_NAME_LENGTH = 4

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# Türkiye cep telefonu ve genel uluslararası biçimler
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+90[\s.\-]?)?0?5\d{2}[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}(?!\d)"
    r"|(?<!\d)\+\d{1,3}[\s.\-]?\d{3}[\s.\-]?\d{3}[\s.\-]?\d{2,4}(?!\d)"
)
# T.C. kimlik numarası biçimi: 11 hane, ilk hane 0 olamaz
_NATIONAL_ID_RE = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
_IBAN_RE = re.compile(r"(?<![A-Z0-9])TR\d{2}[\s]?(?:\d{4}[\s]?){5}\d{2}(?![A-Z0-9])")
_DATE_RE = re.compile(
    r"(?<!\d)(?:0?[1-9]|[12]\d|3[01])[./\-](?:0?[1-9]|1[0-2])[./\-](?:19|20)\d{2}(?!\d)"
)

# Anahtar kelimeler küçük harfe ve aksansız biçime indirgenerek aranır.
_HEALTH_WORDS = (
    "alerj",
    "astim",
    "epilep",
    "diyabet",
    "seker hastal",
    "kronik",
    "ilac kullan",
    "rahatsizlik",
    "saglik notu",
    "saglik durumu",
    "tani ",
    "teshis",
    "rapor sonucu",
    "allerg",
    "asthma",
    "epileps",
    "diabet",
    "chronic",
    "medication",
    "diagnos",
    "health note",
    "medical",
    "disabilit",
)
_SPECIAL_NEEDS_WORDS = (
    "ozel gereksinim",
    "ozel egitim",
    "otiz",
    "disleks",
    "engelli",
    "special need",
    "autis",
    "dyslex",
)
_FINANCE_WORDS = (
    "borc",
    "odenmemis",
    "fatura tutar",
    "tahsilat",
    "outstanding",
    "invoice amount",
    "unpaid",
)
_EMERGENCY_WORDS = ("acil durum", "acil iletisim", "emergency contact")


# Türkçeye özgü, NFKD ile çözülmeyen harfler (noktasız `ı` bir taban harftir).
_TR_FOLD = str.maketrans({"İ": "i", "I": "i", "ı": "i", "ﬁ": "fi"})


def _fold(text: str) -> str:
    """Küçük harfe indirger ve aksanları düşürür (Türkçe uyumlu arama).

    `Astım` -> `astim`, `ÖZEL` -> `ozel`, `ALİ` -> `ali`. Böylece anahtar
    kelime ve ad eşleştirmesi büyük/küçük harf ve aksandan bağımsız çalışır.
    """
    lowered = text.translate(_TR_FOLD).lower().translate(_TR_FOLD)
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _subject_names(db: Session) -> dict[str, str]:
    """Veritabanındaki veri sahiplerinin adları -> tür eşlemesi."""
    from app.models.people import Guardian, Instructor, Student

    names: dict[str, str] = {}
    for model, kind in (
        (Student, "student"),
        (Guardian, "guardian"),
        (Instructor, "instructor"),
    ):
        # `full_name` bir Python özelliğidir (sütun değil), bu yüzden nesneler
        # üzerinden okunur. Ad + soyad sütunları yalnızca ilgili modelde
        # bulunduğundan tek tip bir sorgu kullanılamaz.
        rows = db.scalars(select(model).limit(MAX_SUBJECT_NAMES)).all()
        for row in rows:
            value = getattr(row, "full_name", None)
            if value and len(value) >= MIN_NAME_LENGTH:
                names.setdefault(value, kind)
    return names


def scan(db: Session, text: str) -> tuple[list[str], dict[str, str]]:
    """Serbest metni tarar.

    Döner: ``(field_paths, subject_names)``

    * ``field_paths``  — HSP kayıt defteri yolları (geçide bildirilecek)
    * ``subject_names`` — {gerçek ad: veri sahibi türü}, takma adlaştırma için
    """
    if not text:
        return [], {}

    folded = _fold(text)
    paths: list[str] = []

    def add(path: str) -> None:
        if path not in paths:
            paths.append(path)

    if _EMAIL_RE.search(text):
        add("student.email")
    if _PHONE_RE.search(text):
        add("student.phone")
    if _NATIONAL_ID_RE.search(text):
        add("student.national_id")
    if _IBAN_RE.search(text):
        add("invoice.amount")
    if _DATE_RE.search(text):
        add("student.birth_date")
    if any(word in folded for word in _HEALTH_WORDS):
        add("student.health_notes")
    if any(word in folded for word in _SPECIAL_NEEDS_WORDS):
        add("student.special_needs")
    if any(word in folded for word in _FINANCE_WORDS):
        add("invoice.balance")
    if any(word in folded for word in _EMERGENCY_WORDS):
        add("student.emergency_contact")

    matched: dict[str, str] = {}
    for name, kind in _subject_names(db).items():
        if _fold(name) in folded:
            matched[name] = kind
            add(f"{kind}.full_name")

    return paths, matched
