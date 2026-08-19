"""Biçimlendirme yardımcıları / Formatting helpers (TR & EN locale aware)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal


def format_swim_time(seconds: float | Decimal | None) -> str:
    """Yüzme derecesini `MM:SS.ss` veya `SS.ss` biçiminde gösterir.

    32.45  -> "32.45"
    95.12  -> "1:35.12"
    """
    if seconds is None:
        return "-"
    total = float(seconds)
    if total < 0:
        return "-"
    minutes = int(total // 60)
    remainder = total - minutes * 60
    if minutes:
        return f"{minutes}:{remainder:05.2f}"
    return f"{remainder:.2f}"


def parse_swim_time(text: str) -> float | None:
    """`1:35.12`, `95.12` veya `1.35.12` biçimlerini saniyeye çevirir."""
    if not text:
        return None
    cleaned = text.strip().replace(",", ".")
    try:
        if ":" in cleaned:
            minutes, seconds = cleaned.split(":", 1)
            return int(minutes) * 60 + float(seconds)
        parts = cleaned.split(".")
        if len(parts) == 3:  # 1.35.12 -> 1 dk 35.12 sn
            return int(parts[0]) * 60 + float(f"{parts[1]}.{parts[2]}")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def format_number(
    value: float | int | None, lang: str = "tr", decimals: int = 2
) -> str:
    """Türkçe: 1.250,50 · İngilizce: 1,250.50"""
    if value is None:
        return "-"
    formatted = f"{float(value):,.{decimals}f}"
    if lang == "tr":
        # Önce geçici işaretleyici kullanarak ayraçları takas et
        formatted = (
            formatted.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
        )
    return formatted


def format_currency(
    value: float | int | None, currency: str = "TRY", lang: str = "tr"
) -> str:
    symbols = {"TRY": "₺", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    number = format_number(value, lang, 2)
    return f"{number} {symbol}" if lang == "tr" else f"{symbol}{number}"


def format_date(value: date | datetime | None, lang: str = "tr") -> str:
    """Türkçe: 15.08.2026 · İngilizce: 08/15/2026"""
    if value is None:
        return "-"
    return f"{value:%d.%m.%Y}" if lang == "tr" else f"{value:%m/%d/%Y}"


def format_datetime(value: datetime | None, lang: str = "tr") -> str:
    if value is None:
        return "-"
    return f"{value:%d.%m.%Y %H:%M}" if lang == "tr" else f"{value:%m/%d/%Y %I:%M %p}"


def format_percent(value: float | None, lang: str = "tr", decimals: int = 1) -> str:
    if value is None:
        return "-"
    number = format_number(value, lang, decimals)
    return f"%{number}" if lang == "tr" else f"{number}%"


def format_duration_minutes(minutes: int | float | None, lang: str = "tr") -> str:
    if minutes is None:
        return "-"
    hours, mins = divmod(int(minutes), 60)
    if lang == "tr":
        return f"{hours} sa {mins} dk" if hours else f"{mins} dk"
    return f"{hours}h {mins}m" if hours else f"{mins}m"


WEEKDAY_NAMES = {
    "tr": ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"],
    "en": [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
}

MONTH_NAMES = {
    "tr": [
        "Ocak",
        "Şubat",
        "Mart",
        "Nisan",
        "Mayıs",
        "Haziran",
        "Temmuz",
        "Ağustos",
        "Eylül",
        "Ekim",
        "Kasım",
        "Aralık",
    ],
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
}


def weekday_name(index: int, lang: str = "tr") -> str:
    return WEEKDAY_NAMES.get(lang, WEEKDAY_NAMES["tr"])[index % 7]


def month_name(index: int, lang: str = "tr") -> str:
    """index: 1-12"""
    return MONTH_NAMES.get(lang, MONTH_NAMES["tr"])[(index - 1) % 12]
