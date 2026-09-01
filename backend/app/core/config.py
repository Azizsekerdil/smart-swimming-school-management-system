"""Uygulama yapılandırması / Application configuration.

Tüm ayarlar ortam değişkenlerinden (.env) okunur. Hiçbir sır kaynak koda gömülmez.
All settings are read from environment variables (.env). No secret is hardcoded.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: PyInstaller ile paketlenmiş sürümde mi çalışıyoruz?
#: Paketli çalışmada kaynaklar (kod, derlenmiş arayüz, migration'lar) her
#: açılışta GEÇİCİ bir dizine açılır ve salt okunur kabul edilmelidir;
#: yazılabilir veri (veritabanı, log, yedek) exe'nin yanında tutulur.
IS_FROZEN = bool(getattr(sys, "frozen", False))


def _yazilabilir_mi(dizin: Path) -> bool:
    """Dizine GERÇEKTEN yazılabildiğini dener.

    Windows'ta izin bayraklarına bakmak yeterli değildir: ACL'ler ve UAC
    yönlendirmesi ancak yazma denendiğinde ortaya çıkar.
    """
    if not dizin.is_dir():
        return False
    deneme = dizin / f".yazma_denemesi_{os.getpid()}"
    try:
        deneme.touch()
        deneme.unlink()
    except OSError:
        return False
    return True


if IS_FROZEN:
    #: Salt okunur kaynakların (derlenmiş arayüz, migration'lar) kökü.
    RESOURCE_ROOT = Path(
        getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)
    )
    # Yazılabilir kök sırasıyla:
    #   1. YUZME_OKULU_VERI_DIZINI ortam değişkeni — her şeyi ezer
    #   2. exe'nin yanındaki dizin (taşınabilir kullanım; veri exe ile taşınır)
    #   3. %LOCALAPPDATA%\YuzmeOkulu (Program Files gibi yazılamayan kurulumlar)
    _ozel_veri = os.environ.get("YUZME_OKULU_VERI_DIZINI", "").strip()
    if _ozel_veri:
        PROJECT_ROOT = Path(_ozel_veri).expanduser().resolve()
    else:
        _exe_dizini = Path(sys.executable).resolve().parent
        if _yazilabilir_mi(_exe_dizini):
            PROJECT_ROOT = _exe_dizini
        else:
            _yerel = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            PROJECT_ROOT = (
                (Path(_yerel) if _yerel else Path.home()) / "YuzmeOkulu"
            ).resolve()
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    BACKEND_ROOT = RESOURCE_ROOT
else:
    # Proje kök dizini: backend/app/core/config.py -> backend/app/core -> backend/app -> backend -> ROOT
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    BACKEND_ROOT = Path(__file__).resolve().parents[2]
    RESOURCE_ROOT = PROJECT_ROOT


class Settings(BaseSettings):
    """Merkezi ayar nesnesi."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- Uygulama ----------
    app_name: str = "Akıllı Yüzme Okulu Yönetim Sistemi"
    app_env: Literal["development", "production", "test"] = "development"
    app_debug: bool = True
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_default_language: Literal["tr", "en"] = "tr"
    app_timezone: str = "Europe/Istanbul"
    app_currency: str = "TRY"
    app_version: str = "0.9.0"

    # ---------- Güvenlik ----------
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(64))
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 14
    jwt_algorithm: str = "HS256"
    first_admin_email: str = "admin@yuzmeokulu.local"
    # Belgelenmiş, tek kullanımlık kurulum parolası (SIR DEĞİLDİR).
    # İlk girişte değiştirilmesi zorunludur; değişmeden hiçbir korumalı uca
    # erişilemez ve yalnızca yerel cihazdan giriş kabul edilir.
    # Ayrıntılar: app/core/bootstrap.py
    first_admin_password: str = "admin"
    rate_limit_enabled: bool = True
    rate_limit_login_per_minute: int = 10
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---------- Veritabanı ----------
    database_url: str = "sqlite:///./data/swimming_school.db"
    database_echo: bool = False

    # ---------- Yerel AI (LM Studio) ----------
    local_ai_enabled: bool = True
    local_ai_base_url: str = "http://localhost:1234/v1"
    local_ai_api_key: str = "lm-studio"
    local_ai_model: str = ""
    local_ai_timeout: int = 180
    local_ai_max_tokens: int = 2048
    local_ai_temperature: float = 0.3

    # ---------- NVIDIA ----------
    nvidia_enabled: bool = False
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_timeout: int = 120
    nvidia_max_tokens: int = 2048
    nvidia_temperature: float = 0.3

    # ---------- Genel OpenAI uyumlu ----------
    openai_compat_enabled: bool = False
    openai_compat_base_url: str = ""
    openai_compat_api_key: str = ""
    openai_compat_model: str = ""

    # ---------- AI yönlendirme ----------
    ai_fallback_chain: str = "local,nvidia"
    ai_default_mode: Literal["local", "nvidia", "automatic"] = "automatic"
    ai_response_language: Literal["tr", "en", "auto"] = "auto"
    ai_log_prompts: bool = False

    # ---------- AI Developer Console ----------
    ai_developer_enabled: bool = True
    ai_developer_allow_apply: bool = False
    ai_developer_allow_shell: bool = False
    ai_developer_auto_test: bool = True
    ai_developer_root: str = "."

    # ---------- Yedekleme ----------
    backup_dir: str = "./backups"
    backup_schedule_enabled: bool = False
    backup_schedule_cron: str = "0 23 * * *"
    backup_retention_daily: int = 7
    backup_retention_weekly: int = 4
    backup_retention_monthly: int = 12

    # ---------- Loglama ----------
    log_dir: str = "./logs"
    log_level: str = "INFO"
    log_json: bool = False

    # ---------- Demo verisi ----------
    seed_demo_data: bool = True

    # ------------------------------------------------------------------
    # Doğrulayıcılar / Validators
    # ------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    # ------------------------------------------------------------------
    # Türetilmiş özellikler / Derived properties
    # ------------------------------------------------------------------
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def fallback_chain_list(self) -> list[str]:
        return [p.strip() for p in self.ai_fallback_chain.split(",") if p.strip()]

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def backup_path(self) -> Path:
        p = Path(self.backup_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def log_path(self) -> Path:
        p = Path(self.log_dir)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def data_path(self) -> Path:
        p = PROJECT_ROOT / "data"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def developer_root_path(self) -> Path:
        """AI geliştirici ajanının yazma izni olan kök dizin."""
        p = Path(self.ai_developer_root)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p.resolve()

    @property
    def frontend_dist_path(self) -> Path:
        """Derlenmiş arayüzün bulunduğu dizin.

        Paketli sürümde (PyInstaller) arayüz paket içine `arayuz` adıyla
        gömülür ve geçici açılma dizininden okunur; geliştirmede
        `frontend/dist` kullanılır.
        """
        if IS_FROZEN:
            return RESOURCE_ROOT / "arayuz"
        return PROJECT_ROOT / "frontend" / "dist"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def resolved_database_url(self) -> str:
        """SQLite göreli yollarını proje köküne göre mutlaklaştırır.

        `:memory:` ve `file:` biçimleri dosya yolu değildir; olduğu gibi bırakılır
        (testler bellek içi veritabanı kullanır).
        """
        url = self.database_url
        prefix = "sqlite:///"
        if url.startswith(prefix):
            raw = url[len(prefix) :]
            if raw in (":memory:", "") or raw.startswith("file:"):
                return url
            if raw.startswith("./") or not Path(raw).is_absolute():
                abs_path = (PROJECT_ROOT / raw.lstrip("./")).resolve()
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                return f"{prefix}{abs_path.as_posix()}"
        return url

    def public_ai_config(self) -> dict:
        """Sırları maskeleyerek AI yapılandırmasını döndürür (UI için güvenli)."""
        return {
            "local": {
                "enabled": self.local_ai_enabled,
                "base_url": self.local_ai_base_url,
                "model": self.local_ai_model or "(otomatik)",
                "api_key_set": bool(self.local_ai_api_key),
                "api_key_masked": mask_secret(self.local_ai_api_key),
                "timeout": self.local_ai_timeout,
                "max_tokens": self.local_ai_max_tokens,
                "temperature": self.local_ai_temperature,
            },
            "nvidia": {
                "enabled": self.nvidia_enabled,
                "base_url": self.nvidia_base_url,
                "model": self.nvidia_model,
                "api_key_set": bool(self.nvidia_api_key),
                "api_key_masked": mask_secret(self.nvidia_api_key),
                "timeout": self.nvidia_timeout,
                "max_tokens": self.nvidia_max_tokens,
                "temperature": self.nvidia_temperature,
            },
            "openai_compat": {
                "enabled": self.openai_compat_enabled,
                "base_url": self.openai_compat_base_url,
                "model": self.openai_compat_model,
                "api_key_set": bool(self.openai_compat_api_key),
                "api_key_masked": mask_secret(self.openai_compat_api_key),
            },
            "routing": {
                "mode": self.ai_default_mode,
                "fallback_chain": self.fallback_chain_list,
                "response_language": self.ai_response_language,
            },
        }


def mask_secret(value: str | None) -> str:
    """API anahtarlarını güvenli biçimde maskeler. Tam değer ASLA gösterilmez."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}{'*' * 12}{value[-4:]}"


def _kalici_gizli_anahtar(ad: str) -> str:
    """Verilmeyen gizli anahtarı üretir; SONRAKİ açılışlarda aynı değeri döner.

    Paketli sürümde `secret_key` her süreçte yeniden üretilseydi, kullanıcı
    programı her açtığında tüm oturumlar (JWT) geçersiz kalırdı. Bu yüzden
    üretilen anahtar veri kökünde saklanır. `.env` veya ortam değişkeniyle
    açıkça anahtar verilmişse bu dosyaya hiç bakılmaz.
    """
    dosya = PROJECT_ROOT / "data" / "gizli-anahtarlar.json"
    try:
        if dosya.is_file():
            mevcut = json.loads(dosya.read_text(encoding="utf-8"))
            deger = mevcut.get(ad)
            if isinstance(deger, str) and deger:
                return deger
        else:
            mevcut = {}
    except (OSError, ValueError):
        return secrets.token_urlsafe(64)

    yeni = secrets.token_urlsafe(64)
    mevcut[ad] = yeni
    try:
        dosya.parent.mkdir(parents=True, exist_ok=True)
        dosya.write_text(json.dumps(mevcut, indent=2), encoding="utf-8")
    except OSError:
        pass
    return yeni


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Paketli sürümde .env/ortam değişkeniyle verilmemiş secret_key kalıcılaştırılır.
    if IS_FROZEN and "secret_key" not in s.model_fields_set:
        s.secret_key = _kalici_gizli_anahtar("secret_key")
    return s


settings = get_settings()
