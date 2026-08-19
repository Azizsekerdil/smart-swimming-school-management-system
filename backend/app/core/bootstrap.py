"""İlk kurulum (bootstrap) yönetici sözleşmesi / Bootstrap admin contract.

Ürün, ilk açılışta tek kullanımlık ve **belgelenmiş** bir kurulum kimliğiyle
gelir:

    kullanıcı adı : admin
    parola        : admin

Bu bir sır değildir; kurulumu yapan kişinin ilk girişini mümkün kılan geçici
bir kapıdır. Güvenli olmasını sağlayan şey parolanın gizliliği değil, bu
modülün uyguladığı kısıtlardır:

1. **Zorunlu parola değişimi.** Parola değiştirilmeden hiçbir korumalı uca
   (kontrol paneli, öğrenci/veli/personel verisi, finans, AI/API ayarları,
   dışa aktarma, yedekleme, yönetim işlemleri) erişilemez. Tek istisna
   `GET /auth/me`, `POST /auth/change-password` ve `POST /auth/logout`.
2. **Yalnızca yerel cihazdan.** Parola değişmeden önce giriş yalnızca
   döngüsel arabirimden (127.0.0.1 / ::1) kabul edilir. Ağ üzerinden veya bir
   ters vekil (proxy) arkasından gelen kurulum girişi reddedilir.
3. **Tek kullanımlık.** Parola bir kez değiştirildiğinde `admin/admin` kalıcı
   olarak geçersizdir. Yönetici parola sıfırlama **varsayılanı geri
   getiremez**: parola politikası `admin` değerini reddeder ve bu modül
   kurulum durumunu kalıcı olarak "tamamlandı" işaretler.
4. **Hash'li saklama.** Parola bcrypt (cost 12) ile saklanır; hiçbir zaman
   düz metin olarak veritabanına, loga, hataya, telemetriye, yedeğe, PDF'e
   veya ekran görüntüsüne yazılmaz.
5. **Kaba kuvvet koruması.** Hız sınırı, artan gecikme ve geçici hesap kilidi
   uygulanır; denetim kaydı tutulur ancak parola değeri asla kaydedilmez.

Kurtarma: veritabanında hiç etkin süper kullanıcı kalmazsa (ör. hesap yanlışlıkla
silindiyse) kurulum kapısı yeniden açılır. Bu, veritabanına yerel erişim
gerektirir ve `logs/security.log` içine uyarı olarak yazılır.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

# Kurulum kimliği - SIR DEĞİLDİR, belgelenmiş tek kullanımlık kapıdır.
BOOTSTRAP_USERNAME = "admin"
BOOTSTRAP_PASSWORD = "admin"

# Kurulum durumunun saklandığı ayar anahtarı
BOOTSTRAP_SETTING_KEY = "security_bootstrap"

# Parola değişmeden erişilebilen tek uçlar (yol sonuna göre eşleşir)
PASSWORD_CHANGE_ALLOWED_SUFFIXES = (
    "/auth/change-password",
    "/auth/me",
    "/auth/logout",
    "/auth/login",
    "/auth/refresh",
    "/auth/bootstrap-status",
)

# Döngüsel (yerel cihaz) adresleri
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1"})

# Ters vekil varlığını ele veren başlıklar. Bunlardan biri varsa istek yerel
# cihazdan gelmiş sayılmaz: kurulum girişi ağ üzerinden yapılamaz.
PROXY_HEADERS = (
    "x-forwarded-for",
    "x-real-ip",
    "forwarded",
    "x-forwarded-host",
)


def is_local_request(request) -> bool:  # noqa: ANN001 - starlette.Request
    """İsteğin fiziksel olarak yerel cihazdan gelip gelmediğini söyler.

    `X-Forwarded-For` gibi başlıklara **güvenilmez**; istemci tarafından
    uydurulabilir. Bu yüzden karar yalnızca soket düzeyindeki eş adrese
    dayanır ve herhangi bir vekil başlığı varlığı isteği "uzak" yapar.
    """
    if request is None:
        return False
    headers = getattr(request, "headers", None)
    if headers is not None:
        for name in PROXY_HEADERS:
            if headers.get(name):
                return False
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client else None
    if not host:
        return False
    return host.lower() in LOOPBACK_HOSTS


def path_allows_password_change_only(path: str) -> bool:
    """Zorunlu parola değişimi sırasında bu yola izin verilir mi?"""
    normalised = path.rstrip("/")
    return any(
        normalised.endswith(suffix) for suffix in PASSWORD_CHANGE_ALLOWED_SUFFIXES
    )


# ---------------------------------------------------------------------------
# Kalıcı kurulum durumu
# ---------------------------------------------------------------------------
def _setting(db: Session):  # noqa: ANN202
    from app.models.system import AppSetting

    return db.scalar(select(AppSetting).where(AppSetting.key == BOOTSTRAP_SETTING_KEY))


def read_state(db: Session) -> dict:
    row = _setting(db)
    if row is None or not isinstance(row.value, dict):
        return {"completed": False, "completed_at": None}
    return {
        "completed": bool(row.value.get("completed")),
        "completed_at": row.value.get("completed_at"),
    }


def is_completed(db: Session) -> bool:
    return read_state(db)["completed"]


def _write_state(db: Session, value: dict) -> None:
    from app.models.system import AppSetting

    row = _setting(db)
    if row is None:
        row = AppSetting(
            key=BOOTSTRAP_SETTING_KEY,
            category="security",
            description="İlk kurulum yönetici kapısının durumu",
            value=value,
        )
        db.add(row)
    else:
        row.value = value
    db.flush()


def mark_completed(db: Session) -> None:
    """Kurulum kapısını kalıcı olarak kapatır (geri alınamaz)."""
    if is_completed(db):
        return
    _write_state(
        db,
        {
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def reopen_for_recovery(db: Session) -> None:
    """Yalnızca hiç etkin süper kullanıcı kalmadığında çağrılır."""
    _write_state(db, {"completed": False, "completed_at": None})


def has_active_superuser(db: Session) -> bool:
    from app.models.user import User

    return (
        db.scalar(
            select(User.id)
            .where(User.is_superuser.is_(True), User.is_active.is_(True))
            .limit(1)
        )
        is not None
    )
