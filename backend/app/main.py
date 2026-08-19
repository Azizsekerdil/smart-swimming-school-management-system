"""Akıllı Yüzme Okulu Yönetim Sistemi - FastAPI uygulaması.

Smart Swimming School Management System - FastAPI application entrypoint.
"""

from __future__ import annotations

import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import get_logger, setup_logging
from app.db.init_db import init_db
from app.db.session import SessionLocal

setup_logging()
logger = get_logger("application")

DESCRIPTION = """
**Akıllı Yüzme Okulu Yönetim Sistemi** — yüzme okulu operasyonları, sporcu
performans analizi ve yapay zekâ destekli karar desteği için REST API.

* Öğrenci, veli, eğitmen yönetimi
* Havuz, kulvar, ders planlama ve çakışma denetimi
* Yoklama, üyelik, finans
* Performans analizi ve yarışma yönetimi
* İstatistik motoru ve rapor üretici
* Yerel (LM Studio) ve bulut (NVIDIA) yapay zekâ entegrasyonu
* Yedekleme / geri yükleme

Tüm hata mesajları `Accept-Language` başlığına göre Türkçe veya İngilizce döner.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    """Uygulama yaşam döngüsü: başlangıçta veritabanını hazırla."""
    logger.info("=" * 60)
    logger.info(
        "%s v%s başlatılıyor (%s)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )

    try:
        with SessionLocal() as db:
            result = init_db(db)
            logger.info(
                "Veritabanı hazır | roller: %s, yönetici: %s",
                result["total_roles"],
                result["admin_email"],
            )
    except Exception:  # noqa: BLE001 - başlangıç hatası uygulamayı durdurmamalı
        logger.exception("Başlangıç verisi yüklenemedi - uygulama yine de başlıyor")

    # Zamanlanmış yedekleme (etkinse)
    try:
        from app.services.backup import start_backup_scheduler

        start_backup_scheduler()
    except Exception:  # noqa: BLE001
        logger.warning("Yedekleme zamanlayıcısı başlatılamadı", exc_info=True)

    logger.info("API hazır: http://%s:%s/docs", settings.app_host, settings.app_port)
    logger.info("=" * 60)
    yield

    try:
        from app.services.backup import stop_backup_scheduler

        stop_backup_scheduler()
    except Exception:  # noqa: BLE001
        pass
    logger.info("%s kapatılıyor", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={"name": "Swimming School Management System"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Process-Time"],
)

register_exception_handlers(app)


# --- Güvenlik başlıkları ve istek süresi ---
@app.middleware("http")
async def security_headers_middleware(
    request: Request, call_next
):  # noqa: ANN001, ANN201
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    response.headers["X-Process-Time"] = str(elapsed_ms)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.is_production:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    # API yanıtları için katı CSP; /app altındaki SPA kendi CSP'sini kullanır
    if request.url.path.startswith("/api"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'"
        )
    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/api/ping", tags=["Sistem"], summary="Basit canlılık kontrolü")
def ping() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}


# --- Yüklenen dosyalar ---
_uploads = settings.data_path / "uploads"
_uploads.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads)), name="uploads")

# --- Üretim derlemesinde SPA'yı da bu sunucudan servis et ---
_frontend_dist = settings.project_root / "frontend" / "dist"

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def resolve_spa_asset(full_path: str, root: Path) -> Path | None:
    """SPA statik dosya yolunu güvenli biçimde çözer.

    Yalnızca `root` dizini **altındaki** gerçek bir dosya döndürür. Kapsam
    dışına çıkan her istek `None` döner ve çağıran `index.html` sunar; hiçbir
    koşulda dizin dışından dosya okunmaz.

    Reddedilen girdiler:
      * POSIX mutlak yol (`/etc/passwd`)
      * Windows mutlak/sürücü yolu (`C:\\...`, `C:/...`, `C:dosya`)
      * UNC yolu (`//sunucu/pay`, `\\\\sunucu\\pay`)
      * `..` ile üst dizine çıkma (ters/düz eğik çizgi farkı gözetmeksizin)
      * Sunucuya çözülmeden ulaşan yüzde kodlaması (`%2e%2e%2f`, çift kodlama)
      * NUL bayt enjeksiyonu
      * `root` dışına çıkan sembolik bağ / kavşak (junction)
    """
    if not full_path or "\x00" in full_path:
        return None
    # ASGI sunucusu yüzde kodlamasını zaten çözer; hâlâ '%' varsa bu çift
    # kodlanmış bir kaçış denemesidir - dosya olarak sunulmaz.
    if "%" in full_path:
        return None

    normalised = full_path.replace("\\", "/")
    if normalised.startswith("/") or _DRIVE_PREFIX.match(normalised):
        return None

    parts = [segment for segment in normalised.split("/") if segment not in ("", ".")]
    if not parts or any(segment == ".." for segment in parts):
        return None

    try:
        root_resolved = root.resolve(strict=True)
        target = (root_resolved / Path(*parts)).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None

    if target == root_resolved or not target.is_relative_to(root_resolved):
        return None
    if not target.is_file():
        return None
    return target


if _frontend_dist.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_frontend_dist / "assets")),
        name="spa-assets",
    )

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str = ""):  # noqa: ANN201
        """SPA yönlendirmesi - bilinmeyen yollar index.html'e düşer."""
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "uploads/")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = resolve_spa_asset(full_path, _frontend_dist)
        if target is not None:
            return FileResponse(target)
        return FileResponse(_frontend_dist / "index.html")

else:

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "note": (
                "Arayüz derlenmemiş. Geliştirme için `npm run dev` (frontend), "
                "üretim için `npm run build` çalıştırın."
            ),
        }


def run() -> None:
    """`python -m app.main` ile doğrudan çalıştırma."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug and not settings.is_production,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    run()
