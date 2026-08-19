"""Tanıtım sunumu üreteci / Presentation builder.

Üretilen dosyalar (`sunum/` klasörü):

    Yuzme_Okulu_Tanitim.pptx          TR · koyu tema · ekran ve projeksiyon
    Yuzme_Okulu_Tanitim.pdf           TR · koyu tema · PDF
    Yuzme_Okulu_Tanitim.html          TR · kaydırmalı, tek dosya, çevrimdışı
    Yuzme_Okulu_Tanitim_Baski.pptx    TR · açık tema · yazıcı
    Yuzme_Okulu_Tanitim_Baski.pdf     TR · açık tema · PDF
    Yuzme_Okulu_Intro_EN.*            aynı set, İngilizce
    Yuzme_Okulu_Intro_EN_Print.*      aynı set, İngilizce, açık tema

PPTX üretimi saf Python'dur. PDF ve PNG dönüşümü Windows'ta kurulu
PowerPoint'i COM üzerinden kullanır; PowerPoint yoksa PPTX yine üretilir ve
eksik adımlar raporlanır.

Kullanım:
    python tools/build_presentation.py            # hepsi
    python tools/build_presentation.py --pptx     # yalnızca PPTX
"""

from __future__ import annotations

import argparse
import base64
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation  # noqa: E402
from pptx.util import Inches  # noqa: E402

from presentation_content import DECK, VERSION  # noqa: E402
from presentation_render import RENDERERS, header, new_slide  # noqa: E402
from presentation_shots import SHOTS  # noqa: E402
from presentation_theme import SLIDE_H, SLIDE_W, THEMES  # noqa: E402


def build_deck() -> list[dict]:
    """Anlatı slaytlarına ekran görüntüsü slaytlarını serpiştirir.

    Her ekran, kendisini anlatan özellik slaytının hemen ardına eklenir.
    Bir `after` başlığı destede bulunamazsa üretim durur — ekran sessizce
    yanlış yere ya da sona atılmaz.
    """
    titles = {item.get("title", {}).get("tr") for item in DECK}
    missing = sorted({shot["after"] for shot in SHOTS if shot["after"] not in titles})
    if missing:
        raise SystemExit("Ekran slaytlarinin baglanacagi baslik bulunamadi:\n  - " + "\n  - ".join(missing))

    by_anchor: dict[str, list[dict]] = {}
    for shot in SHOTS:
        by_anchor.setdefault(shot["after"], []).append(shot)

    merged: list[dict] = []
    for item in DECK:
        merged.append(item)
        for shot in by_anchor.get(item.get("title", {}).get("tr", ""), []):
            merged.append(shot)
    return merged


OUT_DIR = ROOT / "sunum"

# (dosya adı, dil, tema)
VARIANTS = [
    ("Yuzme_Okulu_Tanitim", "tr", "ekran"),
    ("Yuzme_Okulu_Tanitim_Baski", "tr", "baski"),
    ("Yuzme_Okulu_Intro_EN", "en", "ekran"),
    ("Yuzme_Okulu_Intro_EN_Print", "en", "baski"),
]

# HTML görüntüleyici yalnızca ekran (koyu) varyantları için üretilir
HTML_VARIANTS = {"Yuzme_Okulu_Tanitim", "Yuzme_Okulu_Intro_EN"}

TITLES = {
    "tr": "Akıllı Yüzme Okulu Yönetim Sistemi — Tanıtım",
    "en": "Smart Swimming School Management System — Introduction",
}

UI = {
    "tr": {
        "prev": "‹ Önceki",
        "next": "Sonraki ›",
        "hint": "Kaydırın veya ok tuşlarını kullanın",
        "close": "Kapat",
    },
    "en": {"prev": "‹ Previous", "next": "Next ›", "hint": "Swipe or use the arrow keys", "close": "Close"},
}


# ---------------------------------------------------------------------------
# PPTX
# ---------------------------------------------------------------------------
def build_pptx(name: str, lang: str, theme_key: str) -> Path:
    theme = THEMES[theme_key]
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)

    for spec in build_deck():
        slide = new_slide(prs, theme)
        kind = spec["kind"]
        if kind not in ("cover", "closing"):
            header(slide, theme, spec["icon"], spec["title"][lang], spec.get("subtitle", {}).get(lang))
        RENDERERS[kind](slide, theme, spec, lang)

        # Konuşmacı notu: slaytın alt başlığı, sunum sırasında hatırlatıcı olarak.
        note = spec.get("subtitle", {}).get(lang) or spec.get("tagline", {}).get(lang, "")
        if note:
            slide.notes_slide.notes_text_frame.text = note

    prs.core_properties.title = TITLES[lang]
    prs.core_properties.subject = TITLES[lang]
    prs.core_properties.comments = f"{VERSION} — {theme_key}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.pptx"
    prs.save(str(path))
    return path


# ---------------------------------------------------------------------------
# PowerPoint COM: PDF ve PNG dışa aktarım
# ---------------------------------------------------------------------------
def _open_powerpoint():
    """PowerPoint COM oturumu açar.

    Not: PowerPoint tamamen gizli bir oturumda otomasyona izin vermez;
    `Visible` ayarlanmadan `Presentations.Open` çağrısı COM sunucusunu
    düşürür. Bu yüzden uygulama görünür açılır, pencereler ise
    `WithWindow=0` ile bastırılır.
    """
    import pythoncom  # type: ignore[import-untyped]
    import win32com.client  # type: ignore[import-untyped]

    pythoncom.CoInitialize()
    app = win32com.client.Dispatch("PowerPoint.Application")
    app.Visible = 1
    return app


def _ordered_frames(png_dir: Path) -> list[Path]:
    """PowerPoint'in dışa aktardığı kareleri slayt sırasına dizer.

    İki tuzak vardır:
      1. Windows dosya sistemi harf duyarsızdır; `*.PNG` ve `*.png` aynı
         dosyaları döndürür, ikisini toplamak kareleri ikiye katlar.
      2. Dosya adları `Slayt1`, `Slayt2` … `Slayt10` biçimindedir; alfabetik
         sıralama `Slayt10`'u `Slayt2`'den önce koyar. Bu yüzden addaki sayıya
         göre sıralanır.
    """
    unique = {path.name.lower(): path for path in png_dir.iterdir() if path.suffix.lower() == ".png"}

    def slide_number(path: Path) -> int:
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return int(digits) if digits else 0

    return sorted(unique.values(), key=slide_number)


def export_pdf_and_png(
    pptx_paths: dict[str, Path], want_png: set[str]
) -> tuple[dict[str, Path], dict[str, list[Path]]]:
    """Tek PowerPoint oturumunda tüm dosyaları dönüştürür."""
    pdfs: dict[str, Path] = {}
    pngs: dict[str, list[Path]] = {}

    app = _open_powerpoint()
    try:
        for name, pptx in pptx_paths.items():
            deck = app.Presentations.Open(str(pptx), ReadOnly=0, Untitled=0, WithWindow=0)
            try:
                pdf = pptx.with_suffix(".pdf")
                deck.SaveAs(str(pdf), 32)  # ppSaveAsPDF
                pdfs[name] = pdf

                if name in want_png:
                    png_dir = OUT_DIR / "_kareler" / name
                    if png_dir.exists():
                        shutil.rmtree(png_dir)
                    png_dir.mkdir(parents=True, exist_ok=True)
                    # 1920x1080 — HTML görüntüleyici için yeterli, dosya boyutu makul
                    deck.Export(str(png_dir), "png", 1920, 1080)
                    pngs[name] = _ordered_frames(png_dir)
            finally:
                deck.Close()
    finally:
        # Son sunum kapandığında PowerPoint kendini sonlandırmış olabilir;
        # bu durumda Quit hata verir ve göz ardı edilmelidir.
        try:
            app.Quit()
        except Exception:
            pass
    return pdfs, pngs


# ---------------------------------------------------------------------------
# HTML görüntüleyici — tek dosya, çevrimdışı, dokunmatik uyumlu
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0B0F14">
<title>{title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{height:100%;background:#0B0F14;color:#E6EDF3;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Calibri,sans-serif;
    overscroll-behavior:none;-webkit-text-size-adjust:100%}}
  body{{display:flex;flex-direction:column;height:100dvh}}
  header{{flex:0 0 auto;display:flex;align-items:center;gap:.6rem;
    padding:calc(.5rem + env(safe-area-inset-top)) .9rem .5rem;
    border-bottom:1px solid #1c2430;background:#0B0F14}}
  .brand{{font-size:.86rem;font-weight:600;letter-spacing:.02em;white-space:nowrap;
    overflow:hidden;text-overflow:ellipsis}}
  .ver{{flex:0 0 auto;font-size:.7rem;font-weight:700;color:#0B0F14;background:#2DD4BF;
    border-radius:99px;padding:.15rem .5rem}}
  .count{{margin-left:auto;flex:0 0 auto;font-size:.8rem;color:#8B98A9;font-variant-numeric:tabular-nums}}
  .bar{{flex:0 0 auto;height:2px;background:#1c2430}}
  .bar > i{{display:block;height:100%;width:0;background:#2DD4BF;transition:width .18s ease}}
  main{{flex:1 1 auto;display:flex;overflow-x:auto;overflow-y:hidden;
    scroll-snap-type:x mandatory;scroll-behavior:smooth;
    -webkit-overflow-scrolling:touch;scrollbar-width:none}}
  main::-webkit-scrollbar{{display:none}}
  .slide{{flex:0 0 100%;scroll-snap-align:center;scroll-snap-stop:always;
    display:flex;align-items:center;justify-content:center;padding:.5rem}}
  .slide img{{max-width:100%;max-height:100%;width:auto;height:auto;
    border-radius:10px;border:1px solid #1c2430;display:block;cursor:zoom-in}}
  #zoom{{position:fixed;inset:0;z-index:50;background:#0B0F14;display:none;
    align-items:center;justify-content:center;cursor:zoom-out;
    padding-bottom:calc(3.4rem + env(safe-area-inset-bottom))}}
  #zoom.on{{display:flex}}
  #zoom img{{display:block;max-width:100%;max-height:100%}}
  @media (orientation:portrait){{
    #zoom img{{width:min(100dvh, calc(100dvw * 16 / 9));height:auto;
      max-width:none;max-height:none;transform:rotate(90deg)}}
  }}
  #zoom .close{{position:absolute;top:calc(.6rem + env(safe-area-inset-top));
    right:.8rem;z-index:2;font-size:.8rem;color:#8B98A9;background:#141920;
    border:1px solid #2B3442;border-radius:9px;padding:.4rem .7rem}}
  footer{{flex:0 0 auto;display:flex;align-items:center;gap:.5rem;
    padding:.5rem .8rem calc(.5rem + env(safe-area-inset-bottom));
    border-top:1px solid #1c2430;background:#0B0F14}}
  button{{font:inherit;font-size:.82rem;color:#E6EDF3;background:#141920;
    border:1px solid #2B3442;border-radius:9px;padding:.5rem .9rem;cursor:pointer}}
  button:disabled{{opacity:.38;cursor:default}}
  .hint{{margin:0 auto;font-size:.74rem;color:#8B98A9}}
  @media (max-width:520px){{ .hint{{display:none}} }}
</style>
</head>
<body>
<header>
  <span class="brand">{brand}</span>
  <span class="ver">{version}</span>
  <span class="count" id="count">1 / {n}</span>
</header>
<div class="bar"><i id="bar"></i></div>
<main id="deck">
{slides}
</main>
<footer>
  <button id="prev">{prev}</button>
  <span class="hint">{hint}</span>
  <button id="next">{next}</button>
</footer>
<div id="zoom"><button class="close" id="zclose">{close}</button><img id="zimg" alt=""></div>
<script>
(function () {{
  var deck = document.getElementById('deck'),
      slides = deck.querySelectorAll('.slide'),
      n = slides.length,
      count = document.getElementById('count'),
      bar = document.getElementById('bar'),
      prev = document.getElementById('prev'),
      next = document.getElementById('next'),
      zoom = document.getElementById('zoom'),
      zimg = document.getElementById('zimg'),
      cur = 0;

  function render() {{
    count.textContent = (cur + 1) + ' / ' + n;
    bar.style.width = ((cur + 1) / n * 100) + '%';
    prev.disabled = cur === 0;
    next.disabled = cur === n - 1;
  }}
  function go(i) {{
    cur = Math.max(0, Math.min(n - 1, i));
    slides[cur].scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
    render();
  }}
  prev.onclick = function () {{ go(cur - 1); }};
  next.onclick = function () {{ go(cur + 1); }};

  var t;
  deck.addEventListener('scroll', function () {{
    clearTimeout(t);
    t = setTimeout(function () {{
      cur = Math.round(deck.scrollLeft / deck.clientWidth);
      render();
    }}, 90);
  }});

  document.addEventListener('keydown', function (e) {{
    if (zoom.classList.contains('on')) {{
      if (e.key === 'Escape') closeZoom();
      else if (e.key === 'ArrowRight') {{ go(cur + 1); zimg.src = slides[cur].querySelector('img').src; }}
      else if (e.key === 'ArrowLeft') {{ go(cur - 1); zimg.src = slides[cur].querySelector('img').src; }}
      return;
    }}
    if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {{ e.preventDefault(); go(cur + 1); }}
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{ e.preventDefault(); go(cur - 1); }}
    else if (e.key === 'Home') go(0);
    else if (e.key === 'End') go(n - 1);
  }});

  function closeZoom() {{ zoom.classList.remove('on'); zimg.src = ''; }}
  document.getElementById('zclose').onclick = function (e) {{ e.stopPropagation(); closeZoom(); }};
  zoom.onclick = closeZoom;
  slides.forEach(function (s) {{
    s.querySelector('img').onclick = function () {{
      zimg.src = this.src;
      zoom.classList.add('on');
    }};
  }});

  render();
}})();
</script>
</body>
</html>
"""


def build_html(name: str, lang: str, pngs: list[Path]) -> Path:
    parts = []
    for index, png in enumerate(pngs, 1):
        data = base64.b64encode(png.read_bytes()).decode("ascii")
        parts.append(
            f'  <figure class="slide" id="s{index}">'
            f'<img src="data:image/png;base64,{data}" alt="{index}"></figure>'
        )

    ui = UI[lang]
    html = HTML_TEMPLATE.format(
        lang="tr" if lang == "tr" else "en",
        title=TITLES[lang],
        brand=TITLES[lang].split(" — ")[0],
        version=VERSION,
        n=len(pngs),
        slides="\n".join(parts),
        prev=ui["prev"],
        next=ui["next"],
        hint=ui["hint"],
        close=ui["close"],
    )
    path = OUT_DIR / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Tanıtım sunumu üretir")
    parser.add_argument("--pptx", action="store_true", help="yalnızca PPTX üret")
    args = parser.parse_args()

    deck = build_deck()
    screens = sum(1 for item in deck if item["kind"] in ("shot", "gallery"))
    print(f"\n  Akilli Yuzme Okulu — sunum uretimi  " f"({len(deck)} slayt, {screens}'i ekran goruntusu)\n")

    pptx_paths: dict[str, Path] = {}
    for name, lang, theme_key in VARIANTS:
        path = build_pptx(name, lang, theme_key)
        pptx_paths[name] = path
        print(f"  [+] {path.name:<38} {path.stat().st_size / 1024:>7.0f} KB")

    if args.pptx:
        print("\n  Yalnizca PPTX istendi; PDF ve HTML atlandi.\n")
        return 0

    print()
    try:
        pdfs, pngs = export_pdf_and_png(pptx_paths, HTML_VARIANTS)
    except Exception as exc:  # PowerPoint yoksa ya da COM hata verirse
        print(f"  [!] PDF/PNG donusumu yapilamadi: {exc}")
        print("      PPTX dosyalari uretildi; PDF icin PowerPoint gerekir.\n")
        return 1

    for name, pdf in pdfs.items():
        print(f"  [+] {pdf.name:<38} {pdf.stat().st_size / 1024:>7.0f} KB")

    print()
    for name in HTML_VARIANTS:
        frames = pngs.get(name, [])
        if not frames:
            print(f"  [!] {name}: kare bulunamadi, HTML uretilmedi")
            continue
        lang = next(lang for n, lang, _ in VARIANTS if n == name)
        html = build_html(name, lang, frames)
        print(f"  [+] {html.name:<38} {html.stat().st_size / 1024:>7.0f} KB  ({len(frames)} kare)")

    shutil.rmtree(OUT_DIR / "_kareler", ignore_errors=True)
    print(f"\n  Tamamlandi -> {OUT_DIR}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
