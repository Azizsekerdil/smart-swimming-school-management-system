"""Kimlik doğrulama uçları / Authentication endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import client_ip, db_session, get_current_user, get_language
from app.core import bootstrap
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    BootstrapRemoteLoginError,
    RateLimitError,
    ValidationError,
)
from app.core.i18n import t
from app.core.logging_config import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_strength_issues,
    verify_password,
)
from app.models.user import LoginAttempt, User
from app.schemas.auth import (
    LoginRequest,
    PasswordChange,
    PreferencesUpdate,
    RefreshRequest,
    TokenPair,
    UserMe,
)
from app.schemas.common import Message
from app.services import audit

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])
security_logger = get_logger("security")

MAX_FAILED_ATTEMPTS = 8
LOCKOUT_MINUTES = 15

# Kullanıcı bulunamadığında da parola doğrulama maliyeti ödenir; böylece
# "kullanıcı var mı?" bilgisi yanıt süresinden çıkarılamaz (zamanlama saldırısı).
# Sabit yerine gerçek bir hash üretilir; uydurma hash passlib uyarısı verir.
_DUMMY_PASSWORD_HASH = hash_password("zamanlama-saldirisi-onlemi")


def _rate_limited(db: Session, email: str) -> bool:
    """Son 1 dakikadaki başarısız deneme sayısını kontrol eder."""
    if not settings.rate_limit_enabled:
        return False
    since = datetime.now(timezone.utc) - timedelta(minutes=1)
    count = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.email == email,
            LoginAttempt.attempted_at >= since.replace(tzinfo=None),
            LoginAttempt.successful.is_(False),
        )
    )
    return bool(count and count >= settings.rate_limit_login_per_minute)


# Artan gecikme: ardışık başarısız denemeden sonra hesap için zorunlu
# bekleme süresi katlanarak büyür (2s, 4s, 8s ... en fazla 60s). Sunucu iş
# parçacığını uyutmaz; bekleme dolmadan gelen istek 429 ile reddedilir.
PROGRESSIVE_DELAY_AFTER = 2
PROGRESSIVE_DELAY_MAX_SECONDS = 60


def _progressive_delay_seconds(failed_count: int) -> int:
    """Ardışık hata sayısına göre zorunlu bekleme (saniye)."""
    if failed_count < PROGRESSIVE_DELAY_AFTER:
        return 0
    return min(
        2 ** (failed_count - PROGRESSIVE_DELAY_AFTER + 1), PROGRESSIVE_DELAY_MAX_SECONDS
    )


def _enforce_progressive_delay(db: Session, user: User, identifier: str) -> None:
    """Son başarısız denemeden bu yana yeterli süre geçti mi?

    `identifier` gönderilen giriş kimliğidir (`admin` kullanıcı adı ya da
    e-posta); ikisi de aynı hesabı hedeflediği için birlikte sayılır.
    """
    wait = _progressive_delay_seconds(user.failed_login_count)
    if wait <= 0:
        return
    since = datetime.now(timezone.utc) - timedelta(seconds=wait)
    recent = db.scalar(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.email.in_({identifier, user.email.lower()}),
            LoginAttempt.successful.is_(False),
            LoginAttempt.attempted_at >= since.replace(tzinfo=None),
        )
    )
    if recent:
        raise RateLimitError("auth.rate_limited", details={"retry_after": wait})


def _resolve_login_user(db: Session, identifier: str) -> User | None:
    """Giriş kimliğini kullanıcıya çözer.

    `admin` kullanıcı adı yalnızca kurulum hesabına eşlenir; başka hiçbir
    hesap bu adla giriş yapamaz.
    """
    if identifier == bootstrap.BOOTSTRAP_USERNAME:
        return db.scalar(
            select(User).where(
                func.lower(User.email) == settings.first_admin_email.lower()
            )
        )
    return db.scalar(select(User).where(func.lower(User.email) == identifier))


def _log_attempt(
    db: Session, email: str, ip: str | None, ua: str | None, ok: bool
) -> None:
    db.add(
        LoginAttempt(
            email=email,
            ip_address=ip,
            user_agent=(ua or "")[:300] or None,
            successful=ok,
            attempted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    )
    db.commit()


def _build_me(user: User) -> UserMe:
    payload = UserMe.model_validate(user)
    payload.permissions = sorted(user.permissions)
    payload.student_id = user.student.id if user.student else None
    payload.guardian_id = user.guardian.id if user.guardian else None
    payload.instructor_id = user.instructor.id if user.instructor else None
    return payload


@router.post("/login", response_model=TokenPair, summary="Giriş yap")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(db_session),
    lang: str = Depends(get_language),
) -> TokenPair:
    email = payload.email.lower().strip()
    ip = client_ip(request)
    ua = request.headers.get("user-agent")

    if _rate_limited(db, email):
        security_logger.warning("Rate limit: %s (%s)", email, ip)
        raise RateLimitError("auth.rate_limited")

    user = _resolve_login_user(db, email)

    # Kullanıcı yoksa da parola doğrulama maliyetini ödeyerek zamanlama sızıntısını azalt
    if user is None:
        verify_password(payload.password, _DUMMY_PASSWORD_HASH)
        _log_attempt(db, email, ip, ua, False)
        security_logger.warning(
            "Başarısız giriş (bilinmeyen kullanıcı): %s (%s)", email, ip
        )
        raise AuthenticationError("auth.invalid_credentials")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until.replace(tzinfo=None) > now:
        _log_attempt(db, email, ip, ua, False)
        raise RateLimitError("auth.rate_limited")

    # Artan gecikme (kaba kuvvet yavaşlatma)
    _enforce_progressive_delay(db, user, email)

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            security_logger.warning("Hesap kilitlendi: %s (%s)", email, ip)
        db.commit()
        _log_attempt(db, email, ip, ua, False)
        security_logger.warning("Başarısız giriş: %s (%s)", email, ip)
        raise AuthenticationError("auth.invalid_credentials")

    if not user.is_active:
        _log_attempt(db, email, ip, ua, False)
        raise AuthenticationError("auth.inactive_user")

    # --- Kurulum kapısı: parola değişene kadar YALNIZCA yerel cihazdan ---
    # Parola doğru olsa bile ağ üzerinden kurulum girişi kabul edilmez.
    if user.must_change_password and not bootstrap.is_local_request(request):
        _log_attempt(db, email, ip, ua, False)
        audit.record(
            db,
            action="bootstrap_remote_login_denied",
            entity_type="user",
            entity_id=user.id,
            user=None,
            summary=(
                "Kurulum parolasıyla uzaktan giriş reddedildi "
                f"({user.email}) - parola değiştirilmelidir"
            ),
            ip_address=ip,
            commit=True,
        )
        security_logger.warning(
            "Kurulum parolasıyla uzaktan giriş reddedildi: %s (%s)", user.email, ip
        )
        raise BootstrapRemoteLoginError()

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    audit.record(
        db,
        action="login",
        entity_type="user",
        entity_id=user.id,
        user=user,
        summary=f"{user.email} giriş yaptı",
        ip_address=ip,
    )
    db.commit()
    _log_attempt(db, email, ip, ua, True)
    security_logger.info("Başarılı giriş: %s (%s)", email, ip)

    return TokenPair(
        access_token=create_access_token(
            user.id, extra={"email": user.email, "roles": user.role_codes}
        ),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/bootstrap-status", summary="İlk kurulum durumu")
def bootstrap_status(request: Request, db: Session = Depends(db_session)) -> dict:
    """İlk kurulum kapısının açık olup olmadığını bildirir.

    Yalnızca **yerel cihazdan** gerçek durum döner. Ağ üzerinden sorulduğunda
    daima `false` döner: kurulum kapısının açık olduğu bilgisi ağa duyurulmaz.
    """
    if not bootstrap.is_local_request(request):
        return {"bootstrap_pending": False, "local_request": False}
    pending = db.scalar(
        select(func.count(User.id)).where(
            User.must_change_password.is_(True), User.is_superuser.is_(True)
        )
    )
    return {
        "bootstrap_pending": bool(pending) and not bootstrap.is_completed(db),
        "local_request": True,
        "username": bootstrap.BOOTSTRAP_USERNAME,
        "warning_tr": (
            "İlk kurulum kimliği etkin: kullanıcı adı 'admin', parola 'admin'. "
            "İlk girişte MUTLAKA değiştirilmelidir."
        ),
        "warning_en": (
            "Initial setup credential is active: username 'admin', password "
            "'admin'. It MUST be changed on first login."
        ),
    }


@router.post("/refresh", response_model=TokenPair, summary="Token yenile")
def refresh(payload: RefreshRequest, db: Session = Depends(db_session)) -> TokenPair:
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise AuthenticationError("auth.invalid_token")

    user = db.get(User, int(data.get("sub", 0)))
    if user is None or not user.is_active:
        raise AuthenticationError("auth.invalid_token")

    return TokenPair(
        access_token=create_access_token(
            user.id, extra={"email": user.email, "roles": user.role_codes}
        ),
        refresh_token=create_refresh_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserMe, summary="Oturum bilgisi")
def me(user: User = Depends(get_current_user)) -> UserMe:
    return _build_me(user)


@router.post("/change-password", response_model=Message, summary="Parola değiştir")
def change_password(
    payload: PasswordChange,
    request: Request,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    if not verify_password(payload.current_password, user.hashed_password):
        raise AuthenticationError("auth.current_password_wrong", status_code=400)

    issues = password_strength_issues(payload.new_password)
    if issues:
        raise ValidationError("auth.password_weak", details={"issues": issues})

    # Yeni parola kurulum parolasıyla aynı olamaz (politika zaten reddeder,
    # burada açıkça da doğrulanır: "sıfırlama varsayılanı geri getiremez").
    if payload.new_password.strip().lower() == bootstrap.BOOTSTRAP_PASSWORD:
        raise ValidationError("auth.password_weak", details={"issues": ["too_common"]})

    was_bootstrap = user.must_change_password
    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    if was_bootstrap and user.is_superuser:
        # Kurulum kapısı kalıcı olarak kapanır.
        bootstrap.mark_completed(db)
    audit.record(
        db,
        action="change_password",
        entity_type="user",
        entity_id=user.id,
        user=user,
        summary="Parola değiştirildi",
        ip_address=client_ip(request),
    )
    db.commit()
    security_logger.info("Parola değiştirildi: %s", user.email)
    return Message(code="common.updated", message=t("common.updated", lang))


@router.patch("/preferences", response_model=UserMe, summary="Tercihleri güncelle")
def update_preferences(
    payload: PreferencesUpdate,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
) -> UserMe:
    if payload.language is not None:
        user.language = payload.language
    if payload.theme is not None:
        user.theme = payload.theme
    if payload.training_mode is not None:
        user.training_mode = payload.training_mode
    if payload.onboarding_completed is not None:
        user.onboarding_completed = payload.onboarding_completed
    db.commit()
    db.refresh(user)
    return _build_me(user)


@router.post("/logout", response_model=Message, summary="Çıkış yap")
def logout(
    request: Request,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    audit.record(
        db,
        action="logout",
        entity_type="user",
        entity_id=user.id,
        user=user,
        summary=f"{user.email} çıkış yaptı",
        ip_address=client_ip(request),
        commit=True,
    )
    return Message(code="common.updated", message=t("common.updated", lang))
