"""Sunum tema ve yerleşim ızgarası / Presentation theme and layout grid.

Tek bir anlamsal renk rolü kümesi iki varyanta çözümlenir:

    ekran (dark)  -> projeksiyon ve ekran sunumu
    baski (light) -> yazıcı ve PDF dağıtımı

Slaytların yapısı iki varyantta birebir aynıdır; yalnızca renkler değişir.
Bu sayede "Tanitim" ve "Tanitim_Baski" dosyaları içerik olarak ayrışmaz.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Yerleşim ızgarası (inç) — 16:9, 13.333 x 7.5
# ---------------------------------------------------------------------------
SLIDE_W = 13.333
SLIDE_H = 7.5

MARGIN = 0.60
CONTENT_W = SLIDE_W - 2 * MARGIN  # 12.13

# Başlık bloğu
TITLE_Y = 0.32
TITLE_H = 0.75
SUB_Y = 1.02
SUB_H = 0.44

# Gövde bloğu
BODY_Y = 1.70
BODY_H = 5.20

# 2x2 kart ızgarası
CARD_W = 5.95
CARD_H = 2.35
CARD_GAP_X = 0.25
CARD_GAP_Y = 0.25

# 4 sütunlu istatistik kutusu
TILE_W = 2.90
TILE_H = 1.55
TILE_GAP = 0.15

# ---------------------------------------------------------------------------
# Yazı tipi seçimi
#
# Sunum, ÖZGÜR (libre) bir yazı tipi tercih eder; böylece deste, tescilli bir
# yazı tipi lisansı olmayan bir makinede de aynı görünümle yeniden üretilebilir.
# Sıradaki ilk KURULU yazı tipi kullanılır. Hiçbiri kurulu değilse, derlemenin
# yapıldığı makinedeki sistem yazı tipine düşülür ve bu durum
# `THIRD_PARTY_NOTICES.md` içinde açıkça kaydedilir.
#
# Ortam değişkeniyle geçersiz kılınabilir:  SWS_PRESENTATION_FONT="Inter"
# ---------------------------------------------------------------------------
PREFERRED_FONTS: tuple[str, ...] = (
    "Inter",  # SIL OFL 1.1
    "Source Sans 3",  # SIL OFL 1.1
    "DejaVu Sans",  # Bitstream Vera / public-domain benzeri izin
    "Noto Sans",  # SIL OFL 1.1
)
# Özgür bir yazı tipi bulunamazsa kullanılacak son çare (tescilli olabilir).
FALLBACK_FONT = "Calibri"

_FONT_FILE_HINTS: dict[str, tuple[str, ...]] = {
    "Inter": ("inter",),
    "Source Sans 3": ("sourcesans3", "sourcesanspro", "source-sans"),
    "DejaVu Sans": ("dejavusans",),
    "Noto Sans": ("notosans",),
}


def _installed_font_files() -> set[str]:
    """Makinede kurulu yazı tipi dosya adları (küçük harf, uzantısız)."""
    roots = [
        Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
        Path("/usr/share/fonts"),
        Path.home() / ".local/share/fonts",
        Path("/Library/Fonts"),
    ]
    found: set[str] = set()
    for root in roots:
        try:
            if not root.is_dir():
                continue
            for path in root.rglob("*"):
                if path.suffix.lower() in {".ttf", ".otf", ".ttc"}:
                    found.add(path.stem.lower().replace(" ", "").replace("-", ""))
        except OSError:
            continue
    return found


def resolve_font() -> str:
    """Kullanılacak yazı tipi adını belirler."""
    override = os.environ.get("SWS_PRESENTATION_FONT")
    if override:
        return override
    installed = _installed_font_files()
    for name in PREFERRED_FONTS:
        hints = _FONT_FILE_HINTS.get(name, (name.lower().replace(" ", ""),))
        if any(any(h in f for f in installed) for h in hints):
            return name
    return FALLBACK_FONT


FONT = resolve_font()
FONT_IS_LIBRE = FONT in PREFERRED_FONTS


@dataclass(frozen=True)
class Theme:
    """Anlamsal renk rolleri. Değerler RGB hex (# olmadan)."""

    key: str
    bg: str  # slayt zemini
    card: str  # kart / panel zemini
    tile: str  # istatistik kutusu zemini
    ink: str  # birincil metin
    muted: str  # ikincil metin
    line: str  # ayırıcı / kenarlık
    teal: str  # vurgu 1
    blue: str  # vurgu 2
    gold: str  # vurgu 3
    green: str  # vurgu 4
    purple: str  # vurgu 5
    rose: str  # vurgu 6 (uyarı / risk)
    # Simge rozetlerinin zemini: koyu temada doygun, açık temada tonlanmış
    chip_teal: str
    chip_blue: str
    chip_gold: str
    chip_green: str
    chip_purple: str
    chip_rose: str

    def accent(self, name: str) -> str:
        return getattr(self, name)

    def chip(self, name: str) -> str:
        return getattr(self, f"chip_{name}")


# Ekran / projeksiyon — koyu
DARK = Theme(
    key="ekran",
    bg="0B0F14",
    card="141920",
    tile="1A2030",
    ink="E6EDF3",
    muted="8B98A9",
    line="2B3442",
    teal="2DD4BF",
    blue="38BDF8",
    gold="F6D365",
    green="22C55E",
    purple="A78BFA",
    rose="FB7185",
    chip_teal="0F8F8A",
    chip_blue="1E5F86",
    chip_gold="7A5B12",
    chip_green="14663A",
    chip_purple="5A3D7A",
    chip_rose="7C2D3C",
)

# Baskı / PDF — açık
LIGHT = Theme(
    key="baski",
    bg="FFFFFF",
    card="F5F7F9",
    tile="EDF1F4",
    ink="10171F",
    muted="4B5563",
    line="DDE3E9",
    teal="0D7A72",
    blue="1B6E9C",
    gold="8A6410",
    green="15803D",
    purple="6D28D9",
    rose="BE123C",
    chip_teal="E3EFEE",
    chip_blue="E3F0FA",
    chip_gold="FAF0DA",
    chip_green="E4F5E9",
    chip_purple="EDE7F3",
    chip_rose="FBE8EC",
)

THEMES = {"ekran": DARK, "baski": LIGHT}

# Vurgu renklerinin sıralı dönüşümü — kartlar arasında renk çeşitliliği için
ACCENT_CYCLE = ("teal", "purple", "blue", "gold", "green", "rose")
