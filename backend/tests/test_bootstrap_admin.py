"""İlk kurulum (bootstrap) yönetici sözleşmesinin regresyon testleri.

Kanıtlanan sözleşme (bkz. `app/core/bootstrap.py`):

* parola değişmeden hiçbir korumalı uca erişilemez,
* kurulum girişi yalnızca yerel cihazdan kabul edilir,
* parola değiştikten sonra `admin/admin` kalıcı olarak geçersizdir,
* yönetici parola sıfırlaması varsayılanı geri getiremez,
* yeni parola hash'lenerek saklanır (düz metin yok),
* kaba kuvvet için artan gecikme ve geçici kilit uygulanır,
* denetim kaydı tutulur ve parola değeri kayda yazılmaz.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.core import bootstrap
from app.core.config import settings
from app.core.security import (
    FORBIDDEN_PASSWORDS,
    password_strength_issues,
    verify_password,
)
from app.db.init_db import init_db
from app.main import app
from app.models.system import AuditLog
from app.models.user import User

STRONG_PASSWORD = "Havuz-Guvenli-2026x1"


# ---------------------------------------------------------------------------
# Fikstürler
# ---------------------------------------------------------------------------
@pytest.fixture
def bootstrap_db(db: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    """Ürünle aynı kurulum parolasıyla temiz bir veritabanı hazırlar."""
    monkeypatch.setattr(settings, "first_admin_password", bootstrap.BOOTSTRAP_PASSWORD)
    init_db(db)
    return db


def _client(db: Session, host: str) -> Generator[TestClient, None, None]:
    def _override() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[db_session] = _override
    with TestClient(app, client=(host, 51000)) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def local_client(bootstrap_db: Session) -> Generator[TestClient, None, None]:
    yield from _client(bootstrap_db, "127.0.0.1")


@pytest.fixture
def remote_client(bootstrap_db: Session) -> Generator[TestClient, None, None]:
    yield from _client(bootstrap_db, "192.0.2.10")


def _login(client: TestClient, identifier: str, password: str):  # noqa: ANN202
    return client.post(
        "/api/v1/auth/login", json={"email": identifier, "password": password}
    )


# ---------------------------------------------------------------------------
# 1. Yerel cihazdan kurulum girişi çalışır, uzaktan çalışmaz
# ---------------------------------------------------------------------------
def test_bootstrap_login_succeeds_from_local_device(local_client: TestClient) -> None:
    response = _login(local_client, "admin", "admin")
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_bootstrap_login_refused_from_remote_host(remote_client: TestClient) -> None:
    response = _login(remote_client, "admin", "admin")
    assert response.status_code == 403, response.text
    body = response.json()
    assert "admin" not in str(body.get("details", {}))


def test_bootstrap_login_refused_when_proxy_header_present(
    local_client: TestClient,
) -> None:
    """Vekil başlığı varsa istek yerel sayılmaz (başlık uydurulabilir)."""
    response = local_client.post(
        "/api/v1/auth/login",
        json={"email": "admin", "password": "admin"},
        headers={"X-Forwarded-For": "127.0.0.1"},
    )
    assert response.status_code == 403


def test_bootstrap_remote_denial_is_audited_without_password(
    remote_client: TestClient, bootstrap_db: Session
) -> None:
    _login(remote_client, "admin", "admin")
    rows = (
        bootstrap_db.query(AuditLog)
        .filter(AuditLog.action == "bootstrap_remote_login_denied")
        .all()
    )
    assert rows, "uzaktan kurulum girişi denetim kaydı üretmeli"
    for row in rows:
        assert "admin" not in (row.summary or "").split("(")[0].lower().replace(
            "kurulum", ""
        )
        assert bootstrap.BOOTSTRAP_PASSWORD not in str(row.changes or "")


# ---------------------------------------------------------------------------
# 2. Parola değişmeden korumalı alan yok
# ---------------------------------------------------------------------------
PROTECTED_PATHS = [
    "/api/v1/students",
    "/api/v1/guardians",
    "/api/v1/instructors",
    "/api/v1/lessons",
    "/api/v1/finance/summary",
    "/api/v1/finance/payments",
    "/api/v1/memberships",
    "/api/v1/statistics/overview",
    "/api/v1/reports/templates",
    "/api/v1/ai/config",
    "/api/v1/settings",
    "/api/v1/users",
    "/api/v1/backup",
    "/api/v1/audit",
]


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_protected_areas_unreachable_before_password_change(
    local_client: TestClient, path: str
) -> None:
    token = _login(local_client, "admin", "admin").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = local_client.get(path, headers=headers)
    assert response.status_code == 403, f"{path} -> {response.status_code}"
    assert response.json()["error"]["code"] == "auth.password_change_required"


def test_only_password_change_flow_is_reachable(local_client: TestClient) -> None:
    token = _login(local_client, "admin", "admin").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert local_client.get("/api/v1/auth/me", headers=headers).status_code == 200


# ---------------------------------------------------------------------------
# 3. Parola değiştikten sonra admin/admin ölü
# ---------------------------------------------------------------------------
def _complete_bootstrap(client: TestClient) -> dict[str, str]:
    token = _login(client, "admin", "admin").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "admin", "new_password": STRONG_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return headers


def test_default_credential_dead_after_change(local_client: TestClient) -> None:
    _complete_bootstrap(local_client)
    assert _login(local_client, "admin", "admin").status_code == 401
    assert _login(local_client, "admin", STRONG_PASSWORD).status_code == 200


def test_protected_areas_reachable_after_change(local_client: TestClient) -> None:
    _complete_bootstrap(local_client)
    token = _login(local_client, "admin", STRONG_PASSWORD).json()["access_token"]
    response = local_client.get(
        "/api/v1/students", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_remote_login_allowed_after_change(
    bootstrap_db: Session, local_client: TestClient
) -> None:
    _complete_bootstrap(local_client)
    for remote in _client(bootstrap_db, "192.0.2.10"):
        assert _login(remote, "admin", STRONG_PASSWORD).status_code == 200


def test_bootstrap_marked_completed(
    local_client: TestClient, bootstrap_db: Session
) -> None:
    assert bootstrap.is_completed(bootstrap_db) is False
    _complete_bootstrap(local_client)
    assert bootstrap.is_completed(bootstrap_db) is True


def test_ensure_admin_does_not_recreate_default_after_completion(
    local_client: TestClient, bootstrap_db: Session
) -> None:
    """Hesap silinse bile varsayılan kimlik geri gelmez."""
    _complete_bootstrap(local_client)
    admin = (
        bootstrap_db.query(User)
        .filter(User.email == settings.first_admin_email)
        .first()
    )
    assert admin is not None
    # Başka bir etkin süper kullanıcı bırak, sonra kurulum hesabını sil.
    survivor = User(
        email="ikinci-admin@test.local",
        hashed_password=admin.hashed_password,
        full_name="Yedek Yönetici",
        is_active=True,
        is_superuser=True,
    )
    bootstrap_db.add(survivor)
    bootstrap_db.delete(admin)
    bootstrap_db.commit()

    from app.db.init_db import ensure_admin

    assert ensure_admin(bootstrap_db) is None
    recreated = (
        bootstrap_db.query(User)
        .filter(User.email == settings.first_admin_email)
        .first()
    )
    assert recreated is None


# ---------------------------------------------------------------------------
# 4. Sıfırlama varsayılanı geri getiremez
# ---------------------------------------------------------------------------
def test_password_policy_rejects_bootstrap_password() -> None:
    assert "too_common" in password_strength_issues("admin")
    assert bootstrap.BOOTSTRAP_PASSWORD in FORBIDDEN_PASSWORDS


def test_change_password_refuses_bootstrap_value(local_client: TestClient) -> None:
    token = _login(local_client, "admin", "admin").json()["access_token"]
    response = local_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "admin", "new_password": "admin"},
    )
    assert response.status_code == 422


def test_admin_reset_cannot_restore_default(local_client: TestClient) -> None:
    _complete_bootstrap(local_client)
    token = _login(local_client, "admin", STRONG_PASSWORD).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = local_client.get("/api/v1/auth/me", headers=headers).json()
    response = local_client.post(
        "/api/v1/users/reset-password",
        headers=headers,
        json={
            "user_id": me["id"],
            "new_password": "admin",
            "must_change_password": True,
        },
    )
    assert response.status_code == 422
    assert _login(local_client, "admin", "admin").status_code == 401


# ---------------------------------------------------------------------------
# 5. Parola hash'li saklanır
# ---------------------------------------------------------------------------
def test_new_password_is_hashed_not_plaintext(
    local_client: TestClient, bootstrap_db: Session
) -> None:
    _complete_bootstrap(local_client)
    admin = (
        bootstrap_db.query(User)
        .filter(User.email == settings.first_admin_email)
        .first()
    )
    assert admin is not None
    stored = admin.hashed_password
    assert STRONG_PASSWORD not in stored
    assert stored.startswith("$2")  # bcrypt
    assert verify_password(STRONG_PASSWORD, stored) is True
    assert verify_password("admin", stored) is False


def test_bootstrap_password_never_stored_in_plaintext(bootstrap_db: Session) -> None:
    admin = (
        bootstrap_db.query(User)
        .filter(User.email == settings.first_admin_email)
        .first()
    )
    assert admin is not None
    assert admin.hashed_password != bootstrap.BOOTSTRAP_PASSWORD
    assert admin.hashed_password.startswith("$2")


# ---------------------------------------------------------------------------
# 6. Kaba kuvvet: artan gecikme ve kilit
# ---------------------------------------------------------------------------
def test_progressive_delay_grows_with_failures() -> None:
    from app.api.v1.auth import _progressive_delay_seconds

    assert _progressive_delay_seconds(0) == 0
    assert _progressive_delay_seconds(1) == 0
    assert _progressive_delay_seconds(2) == 2
    assert _progressive_delay_seconds(3) == 4
    assert _progressive_delay_seconds(4) == 8
    assert _progressive_delay_seconds(50) == 60  # üst sınır


def test_repeated_failures_trigger_rate_limit(local_client: TestClient) -> None:
    codes = [
        _login(local_client, "admin", f"yanlis-parola-{index}").status_code
        for index in range(5)
    ]
    assert codes[0] == 401
    assert 429 in codes, f"artan gecikme 429 üretmeli: {codes}"


def test_account_locks_after_max_failures(
    local_client: TestClient, bootstrap_db: Session
) -> None:
    from app.api.v1.auth import MAX_FAILED_ATTEMPTS

    admin = (
        bootstrap_db.query(User)
        .filter(User.email == settings.first_admin_email)
        .first()
    )
    assert admin is not None
    admin.failed_login_count = MAX_FAILED_ATTEMPTS - 1
    bootstrap_db.commit()
    # Artan gecikme kapısını atlamak için son başarısız denemeyi geçmişe al
    _login(local_client, "admin", "kesinlikle-yanlis")
    bootstrap_db.refresh(admin)
    assert admin.locked_until is not None


# ---------------------------------------------------------------------------
# 7. Kurulum durumu ağa duyurulmaz
# ---------------------------------------------------------------------------
def test_bootstrap_status_visible_locally(local_client: TestClient) -> None:
    body = local_client.get("/api/v1/auth/bootstrap-status").json()
    assert body["bootstrap_pending"] is True
    assert body["local_request"] is True
    assert "admin" in body["warning_en"]


def test_bootstrap_status_hidden_from_network(remote_client: TestClient) -> None:
    body = remote_client.get("/api/v1/auth/bootstrap-status").json()
    assert body["bootstrap_pending"] is False
    assert body["local_request"] is False
    assert "warning_en" not in body
