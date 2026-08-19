"""Güvenlik yardımcıları: parola hashleme ve JWT / Security helpers."""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# passlib 1.7.4, bcrypt 4.1+ sürümünü okumak için kaldırılmış bir özniteliğe
# (`bcrypt.__about__`) bakar ve başlangıçta zararsız ama kafa karıştırıcı bir
# yığın izi basar. Hash'leme etkilenmez; yalnızca bu sürüm okuma uyarısını
# susturuyoruz.
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

# bcrypt: endüstri standardı, yavaş ve tuzlu (salted) hash
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

ALGORITHM = settings.jwt_algorithm


# ---------------------------------------------------------------------------
# Parola / Password
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    """Parolayı bcrypt ile hashler."""
    # bcrypt 72 bayt sınırı - uzun parolaları önce SHA-256 ile özetleriz
    if len(plain_password.encode("utf-8")) > 72:
        plain_password = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolayı doğrular. Hata durumunda sessizce False döner (bilgi sızdırmaz)."""
    try:
        if len(plain_password.encode("utf-8")) > 72:
            plain_password = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:  # noqa: BLE001 - doğrulama hatası asla detay sızdırmamalı
        return False


# Hiçbir koşulda kabul edilmeyen parolalar. `admin` burada olduğu için
# kurulum parolası bir daha ASLA geri getirilemez - ne kullanıcı parola
# değişikliğiyle ne de yönetici parola sıfırlamasıyla.
FORBIDDEN_PASSWORDS = frozenset(
    {
        "admin",
        "admin1",
        "admin12",
        "admin123",
        "administrator",
        "password",
        "parola",
        "parola123",
        "123456789",
        "12345678",
        "qwerty123",
        "yonetici",
    }
)


def password_strength_issues(password: str) -> list[str]:
    """Parola politikası ihlallerini döndürür (boş liste = uygun)."""
    issues: list[str] = []
    if len(password) < 8:
        issues.append("min_length")
    if not any(c.isdigit() for c in password):
        issues.append("needs_digit")
    if not any(c.isalpha() for c in password):
        issues.append("needs_letter")
    if password.strip().lower() in FORBIDDEN_PASSWORDS:
        issues.append("too_common")
    return issues


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def _create_token(
    subject: str | int,
    token_type: str,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": secrets.token_hex(8),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        extra,
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        subject, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str) -> dict[str, Any] | None:
    """Token'ı çözer. Geçersiz/süresi dolmuşsa None döner."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# Çeşitli / Misc
# ---------------------------------------------------------------------------
def generate_api_token(prefix: str = "sws") -> str:
    """Sistem içi entegrasyonlar için token üretir."""
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def constant_time_compare(a: str, b: str) -> bool:
    """Zamanlama saldırılarına karşı güvenli karşılaştırma."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def file_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    """Dosyanın SHA-256 özetini hesaplar (yedek doğrulama için)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()
