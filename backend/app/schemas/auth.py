"""Kimlik doğrulama ve kullanıcı şemaları / Auth and user schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

from app.schemas.common import EMAIL_PATTERN, Email, ORMModel


def _validate_login_identifier(value: str) -> str:
    """E-posta ya da belgelenmiş `admin` kurulum kullanıcı adı."""
    from app.core.bootstrap import BOOTSTRAP_USERNAME

    if value == BOOTSTRAP_USERNAME:
        return value
    if not re.match(EMAIL_PATTERN, value):
        raise ValueError("must be a valid e-mail address")
    return value


LoginIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=255),
    AfterValidator(_validate_login_identifier),
]


class LoginRequest(BaseModel):
    """Giriş isteği.

    `email` normalde bir e-posta adresidir. Tek istisna, ilk kurulumda
    kullanılan `admin` kullanıcı adıdır (bkz. `app/core/bootstrap.py`).
    """

    email: LoginIdentifier
    password: str = Field(min_length=1, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleOut(ORMModel):
    id: int
    code: str
    name_tr: str
    name_en: str
    description: str | None = None
    permissions: list[str] = []
    is_system: bool = False


class RoleSummary(ORMModel):
    id: int
    code: str
    name_tr: str
    name_en: str


class UserOut(ORMModel):
    id: int
    # Çıktıda esnek tip: mevcut kayıtlar okuma isteğini düşürmemeli.
    # Doğrulama giriş şemalarında (LoginRequest, UserCreate) yapılır.
    email: str
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None
    language: str = "tr"
    theme: str = "light"
    is_active: bool
    is_superuser: bool
    must_change_password: bool = False
    onboarding_completed: bool = False
    training_mode: bool = False
    last_login_at: datetime | None = None
    roles: list[RoleSummary] = []
    created_at: datetime | None = None


class UserMe(UserOut):
    """Oturum açan kullanıcının kendi profili - efektif izinleri de içerir."""

    permissions: list[str] = []
    student_id: int | None = None
    guardian_id: int | None = None
    instructor_id: int | None = None


class UserCreate(BaseModel):
    email: Email
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    language: str = "tr"
    role_codes: list[str] = Field(default_factory=list)
    is_active: bool = True
    must_change_password: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    language: str | None = None
    theme: str | None = None
    is_active: bool | None = None
    role_codes: list[str] | None = None
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class PasswordReset(BaseModel):
    """Yönetici tarafından parola sıfırlama."""

    user_id: int
    new_password: str = Field(min_length=8, max_length=200)
    must_change_password: bool = True


class PreferencesUpdate(BaseModel):
    language: str | None = Field(default=None, pattern="^(tr|en)$")
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
    training_mode: bool | None = None
    onboarding_completed: bool | None = None
