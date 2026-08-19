"""Kimlik doğrulama ve RBAC testleri / Authentication and RBAC tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.permissions import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    Perm,
    RoleCode,
    permissions_for_roles,
    role_label,
)
from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    password_strength_issues,
    verify_password,
)
from app.models.user import User


# ---------------------------------------------------------------------------
# Parola ve token birim testleri
# ---------------------------------------------------------------------------
class TestPasswordSecurity:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("Gizli!2026")
        assert hashed != "Gizli!2026"
        assert hashed.startswith("$2b$")

    def test_verify_correct_password(self):
        hashed = hash_password("Gizli!2026")
        assert verify_password("Gizli!2026", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("Gizli!2026")
        assert verify_password("YanlisParola", hashed) is False

    def test_same_password_different_hashes(self):
        """Tuz (salt) sayesinde aynı parola farklı hash üretir."""
        assert hash_password("Ayni!2026") != hash_password("Ayni!2026")

    def test_long_password_over_bcrypt_limit(self):
        """bcrypt 72 bayt sınırını aşan parolalar da doğru çalışmalı."""
        long_password = "A" * 200 + "!2026"
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True
        assert verify_password("A" * 199 + "!2026", hashed) is False

    def test_verify_against_garbage_hash_returns_false(self):
        assert verify_password("herhangi", "gecersiz-hash") is False

    @pytest.mark.parametrize(
        ("password", "expected_issue"),
        [
            ("kisa1", "min_length"),
            ("sadeceharfler", "needs_digit"),
            ("12345678", "needs_letter"),
            ("password", "too_common"),
        ],
    )
    def test_weak_passwords_detected(self, password: str, expected_issue: str):
        assert expected_issue in password_strength_issues(password)

    def test_strong_password_accepted(self):
        assert password_strength_issues("Guclu2026Parola") == []


class TestTokens:
    def test_access_token_roundtrip(self):
        token = create_access_token(42, extra={"email": "a@b.local"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert payload["email"] == "a@b.local"

    def test_tampered_token_rejected(self):
        token = create_access_token(1)
        assert decode_token(token[:-3] + "xyz") is None

    def test_garbage_token_rejected(self):
        assert decode_token("bu.bir.token.degil") is None


# ---------------------------------------------------------------------------
# İzin haritası birim testleri
# ---------------------------------------------------------------------------
class TestPermissionMap:
    def test_every_role_has_permissions(self):
        for code in RoleCode:
            assert code in ROLE_PERMISSIONS, f"{code} için izin tanımı yok"

    def test_system_admin_has_all_permissions(self):
        assert {str(p) for p in ROLE_PERMISSIONS[RoleCode.SYSTEM_ADMIN]} == set(
            ALL_PERMISSIONS
        )

    def test_parent_cannot_write_students(self):
        parent = permissions_for_roles([RoleCode.PARENT])
        assert Perm.STUDENT_WRITE not in parent
        assert Perm.FINANCE_WRITE not in parent
        assert Perm.AI_DEVELOPER not in parent

    def test_instructor_can_record_attendance_but_not_finance(self):
        perms = permissions_for_roles([RoleCode.SWIM_INSTRUCTOR])
        assert Perm.ATTENDANCE_WRITE in perms
        assert Perm.PERFORMANCE_WRITE in perms
        assert Perm.FINANCE_WRITE not in perms
        assert Perm.USER_WRITE not in perms

    def test_only_system_admin_has_developer_permission(self):
        holders = [
            code
            for code, perms in ROLE_PERMISSIONS.items()
            if Perm.AI_DEVELOPER in perms
        ]
        assert holders == [RoleCode.SYSTEM_ADMIN]

    def test_reception_cannot_delete_students(self):
        perms = permissions_for_roles([RoleCode.RECEPTION])
        assert Perm.STUDENT_WRITE in perms
        assert Perm.STUDENT_DELETE not in perms

    def test_multiple_roles_union(self):
        combined = permissions_for_roles([RoleCode.RECEPTION, RoleCode.FINANCE])
        assert Perm.STUDENT_WRITE in combined  # resepsiyondan
        assert Perm.FINANCE_DELETE in combined  # finanstan

    def test_role_labels_exist_in_both_languages(self):
        for code in RoleCode:
            assert role_label(code, "tr") != code
            assert role_label(code, "en") != code

    def test_sensitive_data_permission_is_restricted(self):
        holders = {
            code
            for code, perms in ROLE_PERMISSIONS.items()
            if Perm.STUDENT_READ_SENSITIVE in perms
        }
        # Sağlık verisi yalnızca ilgili rollerde olmalı
        assert holders <= {
            RoleCode.SYSTEM_ADMIN,
            RoleCode.SCHOOL_DIRECTOR,
            RoleCode.HEAD_COACH,
            RoleCode.ADAPTIVE_INSTRUCTOR,
            RoleCode.MEDICAL_STAFF,
        }


# ---------------------------------------------------------------------------
# API testleri
# ---------------------------------------------------------------------------
class TestLoginEndpoint:
    def test_login_success(self, client: TestClient, admin_user: User):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "Admin!2026"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, admin_user: User):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "YanlisParola"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "auth.invalid_credentials"

    def test_login_unknown_user(self, client: TestClient, seeded: dict):  # noqa: ARG002
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "yok@yuzmeokulu.local", "password": "Herhangi1"},
        )
        assert response.status_code == 401
        # Kullanıcının var olup olmadığı sızdırılmamalı
        assert response.json()["error"]["code"] == "auth.invalid_credentials"

    def test_login_inactive_user(
        self, client: TestClient, db: Session, reception_user: User
    ):
        reception_user.is_active = False
        db.commit()
        response = client.post(
            "/api/v1/auth/login",
            json={"email": reception_user.email, "password": "Test!2026"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "auth.inactive_user"

    def test_error_message_language_tr(self, client: TestClient, admin_user: User):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "yanlis"},
            headers={"Accept-Language": "tr"},
        )
        assert "hatalı" in response.json()["error"]["message"].lower()

    def test_error_message_language_en(self, client: TestClient, admin_user: User):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "yanlis"},
            headers={"Accept-Language": "en"},
        )
        assert "invalid" in response.json()["error"]["message"].lower()


class TestProtectedEndpoints:
    def test_no_token_rejected(self, client: TestClient):
        assert client.get("/api/v1/students").status_code == 401

    def test_invalid_token_rejected(self, client: TestClient):
        response = client.get(
            "/api/v1/students", headers={"Authorization": "Bearer gecersiz.token.abc"}
        )
        assert response.status_code == 401

    def test_refresh_token_cannot_be_used_as_access(
        self, client: TestClient, admin_user: User
    ):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "Admin!2026"},
        ).json()
        response = client.get(
            "/api/v1/students",
            headers={"Authorization": f"Bearer {login['refresh_token']}"},
        )
        assert response.status_code == 401

    def test_me_returns_permissions(self, client: TestClient, admin_headers: dict):
        response = client.get("/api/v1/auth/me", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["is_superuser"] is True
        assert len(body["permissions"]) == len(ALL_PERMISSIONS)

    def test_refresh_flow(self, client: TestClient, admin_user: User):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": admin_user.email, "password": "Admin!2026"},
        ).json()
        response = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestRoleBasedAccess:
    def test_parent_cannot_list_all_students(
        self, client: TestClient, parent_headers: dict, student  # noqa: ARG002
    ):
        """Veli öğrenci listesine erişemez (student:read izni yok)."""
        response = client.get("/api/v1/students", headers=parent_headers)
        assert response.status_code == 403

    def test_instructor_can_read_students(
        self, client: TestClient, instructor_headers: dict, student  # noqa: ARG002
    ):
        response = client.get("/api/v1/students", headers=instructor_headers)
        assert response.status_code == 200

    def test_instructor_cannot_create_student(
        self, client: TestClient, instructor_headers: dict
    ):
        response = client.post(
            "/api/v1/students",
            headers=instructor_headers,
            json={"first_name": "Yeni", "last_name": "Ogrenci"},
        )
        assert response.status_code == 403

    def test_reception_can_create_student(
        self, client: TestClient, reception_headers: dict
    ):
        response = client.post(
            "/api/v1/students",
            headers=reception_headers,
            json={
                "first_name": "Yeni",
                "last_name": "Ogrenci",
                "swim_level": "beginner",
            },
        )
        assert response.status_code == 201

    def test_reception_cannot_access_ai_developer(
        self, client: TestClient, reception_headers: dict
    ):
        response = client.get("/api/v1/ai/developer/policy", headers=reception_headers)
        assert response.status_code == 403

    def test_reception_cannot_read_audit_log(
        self, client: TestClient, reception_headers: dict
    ):
        assert client.get("/api/v1/audit", headers=reception_headers).status_code == 403

    def test_forbidden_response_lists_required_permission(
        self, client: TestClient, instructor_headers: dict
    ):
        response = client.post(
            "/api/v1/students",
            headers=instructor_headers,
            json={"first_name": "A", "last_name": "B"},
        )
        details = response.json()["error"].get("details", {})
        assert "student:write" in details.get("required", [])


class TestSensitiveFieldMasking:
    def test_privileged_user_sees_health_notes(
        self, client: TestClient, admin_headers: dict, student
    ):
        response = client.get(f"/api/v1/students/{student.id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["health_notes"] == "Test sağlık notu"

    def test_unprivileged_user_cannot_see_health_notes(
        self, client: TestClient, reception_headers: dict, student
    ):
        """Resepsiyonun student:read_sensitive izni yoktur."""
        response = client.get(
            f"/api/v1/students/{student.id}", headers=reception_headers
        )
        assert response.status_code == 200
        assert response.json()["health_notes"] is None

    def test_unprivileged_user_cannot_write_health_notes(
        self, client: TestClient, reception_headers: dict, student
    ):
        response = client.patch(
            f"/api/v1/students/{student.id}",
            headers=reception_headers,
            json={"health_notes": "Yetkisiz değişiklik"},
        )
        assert response.status_code == 403


class TestPasswordChange:
    def test_change_password_success(self, client: TestClient, reception_headers: dict):
        response = client.post(
            "/api/v1/auth/change-password",
            headers=reception_headers,
            json={"current_password": "Test!2026", "new_password": "YeniGuclu2026"},
        )
        assert response.status_code == 200

    def test_change_password_wrong_current(
        self, client: TestClient, reception_headers: dict
    ):
        response = client.post(
            "/api/v1/auth/change-password",
            headers=reception_headers,
            json={"current_password": "Yanlis", "new_password": "YeniGuclu2026"},
        )
        assert response.status_code == 400

    def test_change_password_weak_rejected(
        self, client: TestClient, reception_headers: dict
    ):
        response = client.post(
            "/api/v1/auth/change-password",
            headers=reception_headers,
            json={"current_password": "Test!2026", "new_password": "12345678"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "auth.password_weak"


class TestAuditTrail:
    def test_login_creates_audit_entry(self, client: TestClient, admin_headers: dict):
        response = client.get(
            "/api/v1/audit", headers=admin_headers, params={"action": "login"}
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_audit_never_stores_passwords(
        self, client: TestClient, admin_headers: dict, reception_headers: dict
    ):
        client.post(
            "/api/v1/auth/change-password",
            headers=reception_headers,
            json={"current_password": "Test!2026", "new_password": "YeniGuclu2026"},
        )
        response = client.get("/api/v1/audit", headers=admin_headers)
        serialized = response.text
        assert "YeniGuclu2026" not in serialized
        assert "Test!2026" not in serialized
