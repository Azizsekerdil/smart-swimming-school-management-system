# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller yapılandırması — Akıllı Yüzme Okulu Yönetim Sistemi masaüstü paketi.

Çalıştırma:
    powershell -ExecutionPolicy Bypass -File scripts\masaustu_paketle.ps1
    (veya doğrudan)  .venv\Scripts\python.exe -m PyInstaller desktop\yuzme_okulu.spec --noconfirm

Çıktı:
    dist\YuzmeOkulu\YuzmeOkulu.exe

Notlar:
  * `--onedir` (tek klasör) kullanılır, `--onefile` değil: tek dosya paketi her
    açılışta yüzlerce MB'ı geçici dizine açar; açılış uzar ve antivirüs
    yazılımları bu davranışı sık sık karantinaya alır. Tek klasör paketinde
    veri dizini (`data\`, `logs\`) exe'nin yanında kalır.
  * Bu spec makineden bağımsızdır (SPECPATH'e göreli yollar) ve macOS CI'da da
    çalışır: Windows'a özgü sürüm kaynağı ve ikon `sys.platform` ile dallanır.
  * Yazılabilir veri exe'nin YANINA yazılır — bkz. backend/app/core/config.py
    (IS_FROZEN dalları). Bu olmadan SQLite veritabanı geçici açılma dizinine
    yazılır ve her kapanışta kaybolurdu.
"""

import re
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

KOK = Path(SPECPATH).parent  # desktop/ -> proje kökü
BACKEND = KOK / "backend"
ARAYUZ = KOK / "frontend" / "dist"

# `app` paketi backend/ altındadır; collect_submodules'un bulabilmesi için
sys.path.insert(0, str(BACKEND))

# Sürüm, uygulamanın tek doğruluk kaynağından okunur.
_cfg_metni = (BACKEND / "app" / "core" / "config.py").read_text(encoding="utf-8")
SURUM = re.search(r'app_version:\s*str\s*=\s*"([^"]+)"', _cfg_metni).group(1)
SURUM_DORTLU = tuple(int(p) for p in (SURUM.split(".") + ["0", "0", "0"])[:4])

if not (ARAYUZ / "index.html").is_file():
    raise SystemExit(
        "Arayüz derlenmemiş. Önce çalıştırın:  cd frontend; npm install; npm run build"
    )

# ------------------------------------------------------------------ veriler
# Derlenmiş arayüz paket içine `arayuz` adıyla gömülür;
# `settings.frontend_dist_path` çalışma anında `sys._MEIPASS/arayuz` okur.
veriler = [(str(ARAYUZ), "arayuz")]

# Alembic migration'ları ve yapılandırması: açılışta şema yükseltmesi için.
veriler.append((str(BACKEND / "alembic"), "alembic"))
veriler.append((str(BACKEND / "alembic.ini"), "."))

# Kullanıcının ayarları görebilmesi için örnek yapılandırma.
if (KOK / ".env.example").is_file():
    veriler.append((str(KOK / ".env.example"), "."))

# ------------------------------------------------------- gizli içe aktarmalar
# Dinamik olarak yüklenen modüller statik analizde görünmez.
gizli = [
    *collect_submodules("uvicorn"),
    *collect_submodules("app"),
    *collect_submodules("alembic"),
    *collect_submodules("apscheduler"),
    "passlib.handlers.bcrypt",
    "bcrypt",
    "email_validator",
    "reportlab.pdfbase._fontdata",
    "openpyxl",
]

# pywebview kuruluysa pencere için paketlenir; yoksa launcher tarayıcıya düşer.
try:
    veriler += collect_data_files("webview")
    gizli.append("webview")
except Exception:  # noqa: BLE001 - pywebview kurulu değil
    pass

gizli = sorted(set(gizli))

# --------------------------------------------------- Windows sürüm kaynağı
# Dosya özelliklerinde ve SmartScreen iletişim kutularında görünen bilgi.
_surum_dosyasi = None
if sys.platform == "win32":
    _surum_kaynagi = f"""
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={SURUM_DORTLU}, prodvers={SURUM_DORTLU},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('041F04B0', [
        StringStruct('CompanyName', 'Yüzme Okulu'),
        StringStruct('FileDescription', 'Akıllı Yüzme Okulu Yönetim Sistemi'),
        StringStruct('FileVersion', '{SURUM}'),
        StringStruct('InternalName', 'YuzmeOkulu'),
        StringStruct('LegalCopyright', 'MIT Lisansı'),
        StringStruct('OriginalFilename', 'YuzmeOkulu.exe'),
        StringStruct('ProductName', 'Akıllı Yüzme Okulu Yönetim Sistemi'),
        StringStruct('ProductVersion', '{SURUM}'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x041F, 1200])])
  ]
)
"""
    _surum_dosyasi = KOK / "build" / "surum_bilgisi.txt"
    _surum_dosyasi.parent.mkdir(parents=True, exist_ok=True)
    _surum_dosyasi.write_text(_surum_kaynagi, encoding="utf-8")

# İkon: varsa kullanılır, yoksa ikonsuz paketlenir (platforma göre uzantı).
if sys.platform == "win32":
    _ikon_yolu = KOK / "desktop" / "yuzme_okulu.ico"
elif sys.platform == "darwin":
    _ikon_yolu = KOK / "desktop" / "yuzme_okulu.icns"
else:
    _ikon_yolu = None
IKON = str(_ikon_yolu) if (_ikon_yolu and _ikon_yolu.is_file()) else None

a = Analysis(
    [str(KOK / "desktop" / "launcher.py")],
    pathex=[str(BACKEND)],
    binaries=[],
    datas=veriler,
    hiddenimports=gizli,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Geliştirme araçları pakete girmemeli: boyutu büyütürler ve son
    # kullanıcıda hiçbir işlevleri yoktur.
    excludes=[
        "pytest",
        "_pytest",
        "mypy",
        "ruff",
        "IPython",
        "jupyter",
        "tkinter",
        "matplotlib",
        "playwright",
        "pip",
        "setuptools._distutils",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YuzmeOkulu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX bazı virüs tarayıcılarında yanlış alarm üretir
    console=False,  # pencereli uygulama; konsol açılmaz
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=IKON,
    version=str(_surum_dosyasi) if _surum_dosyasi else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="YuzmeOkulu",
)
