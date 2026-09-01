#!/usr/bin/env bash
# macOS .app paketi — Akıllı Yüzme Okulu Yönetim Sistemi
#
# GitHub Actions (macos-latest) üzerinde .github/workflows/build-macos.yml
# tarafından çalıştırılır; bir Mac'te elle de çalıştırılabilir.
#
# Çıktı: dist/YuzmeOkulu.app  ve  dist/YuzmeOkulu-macOS.zip
#
# Not: "set -u" BİLEREK yok — macOS'un bash 3.2'si boş dizi açılımını
# ("${DIZI[@]}") unbound sayar ve derlemeyi kırar.
set -eo pipefail

cd "$(dirname "$0")"
PROJECT_ROOT="$(pwd)"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "HATA: macOS .app paketi bir Mac üzerinde oluşturulmalıdır."
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r backend/requirements.txt
# Paketleyici + pencere kitaplığı (requirements.txt'te yoklar; ps1 betiği de
# Windows'ta bunları ayrıca kurar).
"$PYTHON_BIN" -m pip install pyinstaller pywebview

# ---------------------------------------------------------------- arayüz
# frontend/dist git'e girmez (.gitignore); CI'da burada derlenir.
if [[ ! -f frontend/dist/index.html ]]; then
  echo "Arayüz derleniyor (frontend/dist yok)…"
  cd frontend
  if [[ -f package-lock.json ]]; then
    npm ci --no-audit --no-fund
  else
    npm install --no-audit --no-fund
  fi
  npm run build
  cd "$PROJECT_ROOT"
fi

# ------------------------------------------------------------------ ikon
# Projede henüz logo png'si yok; desktop/yuzme_okulu.png eklenirse buradan
# .icns üretilir ve spec (desktop/yuzme_okulu.icns) otomatik kullanır.
if command -v sips >/dev/null && command -v iconutil >/dev/null && [[ -f desktop/yuzme_okulu.png ]]; then
  ICONSET="build/macos/YuzmeOkulu.iconset"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  for size in 16 32 128 256 512; do
    sips -z "$size" "$size" desktop/yuzme_okulu.png --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" desktop/yuzme_okulu.png --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o desktop/yuzme_okulu.icns
fi

# ------------------------------------------------------------- paketleme
rm -rf dist/YuzmeOkulu dist/YuzmeOkulu.app dist/YuzmeOkulu-macOS.zip

# Spec SPECPATH-göreli ve platform dallı (Windows sürüm kaynağı/ikonunu
# atlar, darwin'de BUNDLE ile .app üretir); --add-data/--icon yolları spec
# içinde mutlaklaştırıldığı için CLI bayrağı gerekmez.
PYTHONPATH="$PROJECT_ROOT/backend" "$PYTHON_BIN" -m PyInstaller \
  desktop/yuzme_okulu.spec --noconfirm --clean

APP_PATH="dist/YuzmeOkulu.app"
[[ -d "$APP_PATH" ]] || { echo "HATA: $APP_PATH oluşturulamadı."; exit 1; }

ditto -c -k --keepParent "$APP_PATH" "dist/YuzmeOkulu-macOS.zip"
echo "Tamamlandı: $APP_PATH"
echo "Dağıtım ZIP'i: dist/YuzmeOkulu-macOS.zip"
