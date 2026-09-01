"""Masaüstü başlatıcı / Desktop launcher.

Programı gerçek bir Windows uygulaması gibi başlatır:

  1. Veritabanı şemasını günceller (Alembic migration, etkileşimsiz)
  2. Uvicorn'u AYNI SÜREÇTE, arka plan iş parçacığında başlatır
     (alt süreç DEĞİL — PyInstaller paketinde alt süreç başlatmak,
     exe'nin kendisini yeniden çalıştırmak anlamına gelirdi)
  3. Sağlık ucu (/api/ping) yanıt verene kadar bekler
  4. PyWebView penceresinde açar; pywebview yoksa varsayılan tarayıcıya düşer

Arayüz ve API aynı kökenden sunulur (bkz. `app.main`), bu yüzden CORS ya da
ayrı bir web sunucusu gerekmez.

Çalıştırma (geliştirme):
    python desktop/launcher.py

Paketleme:
    powershell -ExecutionPolicy Bypass -File scripts\\masaustu_paketle.ps1

Ortam değişkenleri:
    YUZME_OKULU_PORT        Sabit port (verilmezse boş bir port seçilir)
    YUZME_OKULU_PENCERESIZ  "1" ise pencere/tarayıcı açılmaz; yalnızca sunucu
                            çalışır (duman testi / CI için)
    YUZME_OKULU_VERI_DIZINI Paketli sürümde yazılabilir veri dizini
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

IS_FROZEN = bool(getattr(sys, "frozen", False))

# Paketlenmemiş çalıştırmada `app` paketini (backend/) görünür kıl.
if not IS_FROZEN:
    _BACKEND = Path(__file__).resolve().parents[1] / "backend"
    if _BACKEND.is_dir() and str(_BACKEND) not in sys.path:
        sys.path.insert(0, str(_BACKEND))

APP_TITLE = "Akıllı Yüzme Okulu Yönetim Sistemi"
STARTUP_TIMEOUT = 90.0

# Windows konsolunda Türkçe karakterler uygulamayı düşürmesin
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError, OSError):
        pass


def log(message: str, level: str = "*") -> None:
    print(f"  [{level}] {message}", flush=True)


def hata_goster(baslik: str, mesaj: str) -> None:
    """Kullanıcıya hata kutusu gösterir.

    Pencereli (console=False) pakette `print` hiçbir yere gitmez; mesaj
    kutusu açılamazsa en azından stderr'e yazılır.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            # MB_ICONERROR (0x10) | MB_SETFOREGROUND (0x10000)
            ctypes.windll.user32.MessageBoxW(None, mesaj, baslik, 0x10 | 0x10000)
            return
        except Exception:  # noqa: BLE001
            pass
    print(f"{baslik}: {mesaj}", file=sys.stderr)


def kaynak_koku() -> Path:
    """Salt okunur kaynakların kökü (alembic.ini, migration'lar, arayüz)."""
    if IS_FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1] / "backend"


def bos_port_bul() -> int:
    """İşletim sisteminden kullanılabilir bir port ister."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def ornek_env_kopyala() -> None:
    """Paketli sürümde .env.example'ı veri dizinine kopyalar (yoksa).

    Kullanıcı ayarları değiştirmek isterse bu dosyayı `.env` adıyla
    kopyalayıp düzenleyebilir; program bir sonraki açılışta okur.
    """
    if not IS_FROZEN:
        return
    try:
        from app.core.config import PROJECT_ROOT

        kaynak = kaynak_koku() / ".env.example"
        hedef = PROJECT_ROOT / ".env.example"
        if kaynak.is_file() and not hedef.exists():
            shutil.copyfile(kaynak, hedef)
    except OSError:
        pass


def migrasyonlari_uygula() -> None:
    """Veritabanı şemasını en son sürüme yükseltir (etkileşimsiz)."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    kok = kaynak_koku()
    cfg = AlembicConfig(str(kok / "alembic.ini"))
    cfg.set_main_option("script_location", str(kok / "alembic"))
    command.upgrade(cfg, "head")


# Sunucu iş parçacığında oluşan hata buraya yazılır; ana iş parçacığı bunu
# kullanıcıya gösterir. Aksi hâlde hata sessizce kaybolurdu.
_sunucu_hatasi: list[BaseException] = []


def sunucuyu_baslat(port: int) -> threading.Thread:
    """Uvicorn'u AYNI süreçte, daemon iş parçacığında başlatır.

    Daemon olduğu için pencere kapanınca süreçle birlikte biter.
    """
    import uvicorn

    from app.main import app

    yapilandirma = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    sunucu = uvicorn.Server(yapilandirma)

    def calistir() -> None:
        try:
            sunucu.run()
        except BaseException as exc:  # noqa: BLE001
            _sunucu_hatasi.append(exc)

    iplik = threading.Thread(target=calistir, name="uvicorn", daemon=True)
    iplik.start()
    return iplik


def sunucuyu_bekle(port: int, zaman_asimi: float = STARTUP_TIMEOUT) -> bool:
    """Sağlık ucu yanıt verene kadar bekler."""
    adres = f"http://127.0.0.1:{port}/api/ping"
    bitis = time.monotonic() + zaman_asimi
    while time.monotonic() < bitis:
        if _sunucu_hatasi:
            return False
        try:
            with urllib.request.urlopen(adres, timeout=2) as yanit:  # noqa: S310
                if yanit.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(0.3)
    return False


def pencere_ac(url: str) -> None:
    """WebView penceresi açar; pywebview yoksa tarayıcıya düşer."""
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError:
        log("pywebview kurulu değil; varsayılan tarayıcı kullanılacak.", "!")
        webbrowser.open(url)
        log(f"Uygulama açık: {url}")
        log("Kapatmak için bu pencerede Ctrl+C tuşlarına basın.")
        try:
            while not _sunucu_hatasi:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return

    log("Masaüstü penceresi açılıyor…")
    webview.create_window(
        APP_TITLE,
        url,
        width=1440,
        height=900,
        min_size=(1024, 680),
        resizable=True,
        text_select=True,
        confirm_close=False,
    )
    # gui=None -> Windows'ta EdgeChromium (WebView2) otomatik seçilir
    webview.start()


def main() -> int:
    print()
    print("=" * 62)
    print(f"   {APP_TITLE}")
    print("   Smart Swimming School Management System")
    print("=" * 62)
    print()

    # Ayarların yüklenmesi veri dizinini oluşturur; yazma izni yoksa BURADA
    # patlar. Yakalanmazsa kullanıcı ham bir traceback görür (ya da hiçbir şey).
    try:
        from app.core.config import PROJECT_ROOT, settings
    except Exception as exc:  # noqa: BLE001
        hata_goster(
            f"{APP_TITLE} — başlatılamadı",
            "Uygulama ayarları yüklenemedi; büyük olasılıkla veri dizinine "
            "yazma izni yok.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            "Çözüm: YUZME_OKULU_VERI_DIZINI ortam değişkeniyle yazılabilir "
            "bir klasör gösterin.",
        )
        return 1

    log(f"Veri dizini: {PROJECT_ROOT}")
    ornek_env_kopyala()

    if not settings.frontend_dist_path.joinpath("index.html").is_file():
        if IS_FROZEN:
            hata_goster(
                f"{APP_TITLE} — arayüz bulunamadı",
                "Paket bozuk görünüyor: derlenmiş arayüz (arayuz/index.html) "
                "paket içinde yok. Programı yeniden indirin/kurun.",
            )
            return 1
        log("Arayüz derlemesi yok (frontend/dist); yalnızca /docs açılacak.", "!")

    # ---------- veritabanı ----------
    log("Veritabanı şeması güncelleniyor…")
    try:
        migrasyonlari_uygula()
        log("Veritabanı güncel.", "+")
    except Exception as exc:  # noqa: BLE001
        hata_goster(
            f"{APP_TITLE} — veritabanı hatası",
            "Veritabanı şeması güncellenemedi.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Veri dizini: {PROJECT_ROOT}\n"
            "Ayrıntı için logs\\application.log dosyasına bakın.",
        )
        return 1

    # ---------- port ----------
    port_metni = os.environ.get("YUZME_OKULU_PORT", "").strip()
    if port_metni.isdigit():
        port = int(port_metni)
    else:
        port = bos_port_bul()

    log(f"Sunucu başlatılıyor (127.0.0.1:{port})…")
    sunucuyu_baslat(port)

    if not sunucuyu_bekle(port):
        if _sunucu_hatasi:
            ayrinti = f"{type(_sunucu_hatasi[0]).__name__}: {_sunucu_hatasi[0]}"
        else:
            ayrinti = f"Sunucu {STARTUP_TIMEOUT:.0f} saniye içinde yanıt vermedi."
        hata_goster(
            f"{APP_TITLE} — başlatılamadı",
            f"Uygulama başlatılamadı.\n\n{ayrinti}\n\n"
            f"Veri dizini: {PROJECT_ROOT}\n"
            "Ayrıntı için logs\\application.log dosyasına bakın.",
        )
        return 1

    url = f"http://127.0.0.1:{port}"
    if not settings.frontend_dist_path.joinpath("index.html").is_file():
        url = f"{url}/docs"

    log("Backend hazır.", "+")
    log(f"Adres: {url}")
    print()

    # Duman testi / CI: pencere açmadan sunucu olarak çalış
    if os.environ.get("YUZME_OKULU_PENCERESIZ", "").strip() == "1":
        log("Penceresiz kip: sunucu çalışıyor, kapatmak için süreci sonlandırın.")
        try:
            while not _sunucu_hatasi:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        return 0

    pencere_ac(url)
    log("Uygulama kapatıldı.", "+")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  Kapatıldı.")
        sys.exit(0)
