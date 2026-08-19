"""Masaüstü başlatıcı / Desktop launcher.

Programı gerçek bir Windows uygulaması gibi başlatır:
  * Backend'i arka planda çalıştırır
  * Hazır olmasını bekler (sağlık kontrolü)
  * Yerleşik WebView penceresinde açar (Edge WebView2 - Electron'a göre çok daha
    az RAM kullanır)
  * pywebview yoksa varsayılan tarayıcıda açar (zarif geri düşüş)
  * Pencere kapatıldığında backend'i temiz biçimde durdurur

Çalıştırma:
    python desktop/launcher.py
    START_SWIMMING_SCHOOL.bat  (çift tıklama)
"""

from __future__ import annotations

import atexit
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Windows konsolunda Türkçe karakterlerin bozulmaması için çıktıyı UTF-8'e sabitle
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # pragma: no cover - eski konsollar
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist" / "index.html"

APP_TITLE = "Akıllı Yüzme Okulu Yönetim Sistemi"
DEFAULT_PORT = 8000
STARTUP_TIMEOUT = 90

_backend_process: subprocess.Popen | None = None


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def log(message: str, level: str = "*") -> None:
    print(f"  [{level}] {message}", flush=True)


def banner() -> None:
    print()
    print("=" * 62)
    print(f"   {APP_TITLE}")
    print("   Smart Swimming School Management System")
    print("=" * 62)
    print()


def find_free_port(preferred: int = DEFAULT_PORT) -> int:
    """Tercih edilen port doluysa boş bir port bulur."""
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def python_executable() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    log("Sanal ortam bulunamadı, sistem Python'u kullanılıyor.", "!")
    return sys.executable


def wait_for_backend(port: int, timeout: int = STARTUP_TIMEOUT) -> bool:
    """Backend hazır olana kadar bekler."""
    url = f"http://127.0.0.1:{port}/api/ping"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _backend_process and _backend_process.poll() is not None:
            log("Backend süreci beklenmedik şekilde sonlandı.", "X")
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as response:  # noqa: S310
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
def start_backend(port: int) -> subprocess.Popen:
    global _backend_process

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env["APP_PORT"] = str(port)

    command = [
        python_executable(),
        "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--log-level", "warning",
    ]

    creation_flags = 0
    if sys.platform == "win32":
        # Konsol penceresi açılmasın
        creation_flags = subprocess.CREATE_NO_WINDOW

    _backend_process = subprocess.Popen(  # noqa: S603
        command,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    return _backend_process


def stop_backend() -> None:
    global _backend_process
    if _backend_process is None:
        return
    if _backend_process.poll() is None:
        log("Backend durduruluyor…")
        _backend_process.terminate()
        try:
            _backend_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _backend_process.kill()
    _backend_process = None


atexit.register(stop_backend)


# ---------------------------------------------------------------------------
# Pencere
# ---------------------------------------------------------------------------
def open_window(url: str) -> None:
    """WebView penceresi açar; yoksa tarayıcıya düşer."""
    try:
        import webview  # type: ignore[import-not-found]
    except ImportError:
        log("pywebview kurulu değil; varsayılan tarayıcı kullanılacak.", "!")
        log("Masaüstü penceresi için:  pip install pywebview", "!")
        webbrowser.open(url)
        print()
        log(f"Uygulama açık: {url}")
        log("Kapatmak için bu pencerede Ctrl+C tuşlarına basın.")
        try:
            while True:
                time.sleep(1)
                if _backend_process and _backend_process.poll() is not None:
                    break
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


# ---------------------------------------------------------------------------
# Ana akış
# ---------------------------------------------------------------------------
def main() -> int:
    banner()

    if not BACKEND_DIR.exists():
        log(f"Backend dizini bulunamadı: {BACKEND_DIR}", "X")
        return 1

    if not FRONTEND_DIST.exists():
        log("Arayüz derlemesi bulunamadı (frontend/dist).", "!")
        log("Derlemek için:  cd frontend && npm install && npm run build", "!")
        log("Şimdilik yalnızca API dokümantasyonu açılacak.", "!")

    port = DEFAULT_PORT
    if port_in_use(port):
        log(f"Port {port} kullanımda, alternatif aranıyor…", "!")
        port = find_free_port(port + 1)

    log(f"Backend başlatılıyor (port {port})…")
    start_backend(port)

    if not wait_for_backend(port):
        log("Backend belirtilen sürede yanıt vermedi.", "X")
        log("Ayrıntı için logs/application.log dosyasına bakın.", "X")
        stop_backend()
        input("\n  Kapatmak için Enter'a basın…")
        return 1

    log("Backend hazır.", "+")

    base_url = f"http://127.0.0.1:{port}"
    target_url = base_url if FRONTEND_DIST.exists() else f"{base_url}/docs"

    print()
    log(f"Adres  : {target_url}")
    log(f"API    : {base_url}/docs")
    print()

    try:
        open_window(target_url)
    finally:
        stop_backend()
        log("Uygulama kapatıldı.", "+")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        stop_backend()
        print("\n  Kapatıldı.")
        sys.exit(0)
