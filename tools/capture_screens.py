"""Uygulama ekranlarını yakalar / Capture application screens.

Sunum destesinde kullanılmak üzere çalışan uygulamanın gerçek ekranlarını PNG
olarak kaydeder. Ekran görüntüleri **canlı uygulamadan** alınır; hiçbir görsel
elle çizilmez veya taklit edilmez.

Kullanım:
    python tools/capture_screens.py            # koyu + açık tema, TR
    python tools/capture_screens.py --lang en  # İngilizce arayüz

Ön koşul: backend çalışıyor olmalı (START_SWIMMING_SCHOOL.bat ya da uvicorn) ve
frontend derlenmiş olmalı (BUILD_FRONTEND.bat).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "sunum" / "ekranlar"

BASE_URL = os.environ.get("SWS_BASE_URL", "http://127.0.0.1:8000")
VIEWPORT = {"width": 1600, "height": 1000}

# (dosya adı, rota, TR başlık, EN başlık, sayfanın oturması için ek bekleme sn)
SCREENS: list[tuple[str, str, str, str, float]] = [
    ("login", "/login", "Giriş", "Sign in", 0.6),
    ("dashboard", "/", "Kontrol Paneli", "Dashboard", 1.4),
    ("students", "/students", "Öğrenci Listesi", "Student List", 1.2),
    ("student_detail", "/students/1", "Öğrenci Detayı", "Student Detail", 1.6),
    ("guardians", "/guardians", "Veliler", "Guardians", 1.0),
    ("instructors", "/instructors", "Eğitmenler", "Instructors", 1.0),
    ("pools", "/pools", "Havuzlar", "Pools", 1.0),
    ("lane_plan", "/lane-plan", "Kulvar Planı", "Lane Plan", 1.4),
    ("calendar", "/calendar", "Takvim", "Calendar", 1.6),
    ("lessons", "/lessons", "Dersler", "Lessons", 1.2),
    ("attendance", "/attendance", "Yoklama", "Attendance", 1.2),
    ("memberships", "/memberships", "Üyelikler", "Memberships", 1.0),
    ("finance", "/finance", "Finans", "Finance", 1.4),
    ("performance", "/performance", "Performans", "Performance", 1.4),
    ("competitions", "/competitions", "Yarışmalar", "Competitions", 1.0),
    ("statistics", "/statistics", "İstatistik Merkezi", "Statistics Centre", 1.8),
    ("reports", "/reports", "Raporlar", "Reports", 1.0),
    ("ai_center", "/ai", "Yapay Zekâ Merkezi", "AI Centre", 1.6),
    ("ai_developer", "/ai-developer", "AI Geliştirici Konsolu", "AI Developer Console", 1.2),
    ("caio", "/caio", "CAIO Ajanı", "CAIO Agent", 1.2),
    ("notifications", "/notifications", "Bildirimler", "Notifications", 1.0),
    ("training", "/training", "Eğitim Merkezi", "Training Centre", 1.0),
    ("help", "/help", "Kullanım Kılavuzu", "User Guide", 1.0),
    ("settings", "/settings", "Ayarlar", "Settings", 1.0),
]

ADMIN_EMAIL = "admin@yuzmeokulu.local"


def _login(page: Page, password: str) -> bool:
    """Oturum açar.

    Ön koşul: hesabın **ilk kurulum parola değişimi tamamlanmış** olmalıdır.
    Değilse uygulama zorunlu parola değiştirme ekranını gösterir ve yakalama
    anlamlı ekran üretemez (bkz. `backend/app/core/bootstrap.py`).
    """
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.wait_for_timeout(700)
    try:
        # Kimlik alanı e-posta ya da kullanıcı adı kabul eder; bu yüzden
        # tip yerine kimlik (id) ile seçilir.
        page.fill("#email", ADMIN_EMAIL)
        page.fill('input[type="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_url(f"{BASE_URL}/**", timeout=15000)
        page.wait_for_timeout(2200)
    except Exception as exc:
        print(f"  [!] Giris basarisiz: {exc}")
        return False
    # Uygulama tek sayfa (SPA) oldugu icin URL degismeyebilir; oturumun
    # gercekten acildigini giris formunun kaybolmasindan anlariz.
    if page.locator("#email").count():
        return False
    # Zorunlu parola değişimi ekranı açıldıysa yakalamayı sürdürmek anlamsız.
    if page.locator("text=admin / admin").count():
        print(
            "  [!] Hesap ilk kurulum parolasini hala kullaniyor. "
            "Once parolayi degistirin."
        )
        return False
    return True


# Uygulamanın gerçek localStorage anahtarları (frontend/src/lib/*.ts)
THEME_KEY = "sws-theme"
LANGUAGE_KEY = "sws-language"


def _set_theme(page: Page, theme: str) -> None:
    """Temayı uygulamanın kendi anahtarıyla ayarlar.

    Anahtar adı tahmin edilmez; `frontend/src/lib/store.ts` içindeki
    `THEME_KEY` ile birebir aynıdır. Yanlış anahtar sessizce yok sayılır ve
    ekran görüntüleri istenmeyen temada çıkar.
    """
    page.evaluate(
        """([key, t]) => {
            localStorage.setItem(key, t);
            document.documentElement.classList.toggle('dark', t === 'dark');
        }""",
        [THEME_KEY, theme],
    )


def _set_language(page: Page, lang: str) -> None:
    page.evaluate(
        "([key, l]) => localStorage.setItem(key, l)",
        [LANGUAGE_KEY, lang],
    )


def capture(theme: str, lang: str, password: str) -> int:
    target = OUT_DIR / f"{theme}_{lang}"
    target.mkdir(parents=True, exist_ok=True)

    taken = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=2,  # keskin görüntü için 2x
            locale="tr-TR" if lang == "tr" else "en-GB",
            # Uygulama "system" temasında bunu izler; açık tercih zaten
            # localStorage ile veriliyor, bu ikinci güvence.
            color_scheme=theme,
        )
        page = context.new_page()

        # Konsol gürültüsünü bastır ama gerçek hataları göster
        page.on(
            "pageerror",
            lambda exc: print(f"      [sayfa hatasi] {str(exc)[:110]}"),
        )

        page.goto(BASE_URL, wait_until="domcontentloaded")
        _set_theme(page, theme)
        _set_language(page, lang)

        if not _login(page, password):
            print("  [X] Oturum acilamadi; yakalama iptal.")
            browser.close()
            return 0

        _set_theme(page, theme)
        _set_language(page, lang)
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1500)

        for name, route, title_tr, title_en, settle in SCREENS:
            label = title_tr if lang == "tr" else title_en
            try:
                if name == "login":
                    # Giriş ekranı için oturumu geçici olarak kapat
                    continue
                page.goto(f"{BASE_URL}{route}", wait_until="networkidle", timeout=25000)
                page.wait_for_timeout(int(settle * 1000))
                # Yükleniyor göstergesi kaldıysa biraz daha bekle
                if page.locator("text=Yükleniyor").count() or page.locator("text=Loading").count():
                    page.wait_for_timeout(1500)
                path = target / f"{name}.png"
                page.screenshot(path=str(path), full_page=False)
                size = path.stat().st_size / 1024
                print(f"  [+] {label:<26} {name}.png  {size:>6.0f} KB")
                taken += 1
            except Exception as exc:
                print(f"  [!] {label:<26} atlandi: {str(exc)[:80]}")

        # Giriş ekranı en sona: oturumu kapatıp yakala
        try:
            page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
            page.goto(f"{BASE_URL}/login", wait_until="networkidle")
            _set_theme(page, theme)
            _set_language(page, lang)
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1200)
            path = target / "login.png"
            page.screenshot(path=str(path))
            print(
                f"  [+] {'Giris' if lang == 'tr' else 'Sign in':<26} login.png  "
                f"{path.stat().st_size / 1024:>6.0f} KB"
            )
            taken += 1
        except Exception as exc:
            print(f"  [!] Giris ekrani atlandi: {str(exc)[:80]}")

        browser.close()
    return taken


def main() -> int:
    global BASE_URL
    parser = argparse.ArgumentParser(description="Uygulama ekranlarini yakalar")
    parser.add_argument("--theme", default="dark", choices=["dark", "light", "both"])
    parser.add_argument(
        "--base-url",
        default=None,
        help="Calisan uygulamanin adresi (ya da SWS_BASE_URL)",
    )
    parser.add_argument("--lang", default="tr", choices=["tr", "en", "both"])
    # Parola koda gömülmez: önce --password, sonra ortam değişkeni okunur.
    # Gerçek bir parolayı varsayılan olarak yazmak, depo public'e açıldığında
    # doğrudan kimlik bilgisi sızıntısı olurdu.
    parser.add_argument(
        "--password",
        default=os.environ.get("SWS_ADMIN_PASSWORD", ""),
        help="Yönetici parolası (ya da SWS_ADMIN_PASSWORD ortam değişkeni)",
    )
    args = parser.parse_args()

    if args.base_url:
        BASE_URL = args.base_url.rstrip("/")

    if not args.password:
        print(
            "\n  Parola gerekli: --password ile verin ya da SWS_ADMIN_PASSWORD"
            "\n  ortam degiskenini ayarlayin.\n"
        )
        return 2

    themes = ["dark", "light"] if args.theme == "both" else [args.theme]
    langs = ["tr", "en"] if args.lang == "both" else [args.lang]

    print(f"\n  Ekran yakalama — {BASE_URL}\n")
    total = 0
    for theme in themes:
        for lang in langs:
            print(f"  --- {theme} / {lang} ---")
            started = time.time()
            count = capture(theme, lang, args.password)
            total += count
            print(f"      {count} ekran, {time.time() - started:.0f} sn\n")

    print(f"  Toplam {total} ekran -> {OUT_DIR}\n")
    return 0 if total else 1


if __name__ == "__main__":
    sys.exit(main())
