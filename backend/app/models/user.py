"""Kullanıcı, rol ve oturum modelleri / User, role and session models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.people import Guardian, Instructor, Student

# Kullanıcı <-> Rol çoktan çoğa
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Role(Base, IntPKMixin, TimestampMixin):
    """Sistem rolü. İzinler JSON listesi olarak saklanır."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    name_tr: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(400))
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles, back_populates="roles", lazy="selectin"
    )

    def name(self, lang: str = "tr") -> str:
        return self.name_tr if lang == "tr" else self.name_en

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Role {self.code}>"


class User(Base, IntPKMixin, TimestampMixin):
    """Sisteme giriş yapabilen kullanıcı."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(5), default="tr", nullable=False)
    theme: Mapped[str] = mapped_column(String(10), default="light", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    training_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users", lazy="selectin"
    )

    # Kişi kayıtlarıyla isteğe bağlı bağlantı (portal erişimi için)
    student: Mapped["Student | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    guardian: Mapped["Guardian | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )
    instructor: Mapped["Instructor | None"] = relationship(
        back_populates="user", uselist=False, lazy="selectin"
    )

    @property
    def role_codes(self) -> list[str]:
        return [r.code for r in self.roles]

    @property
    def permissions(self) -> set[str]:
        """Rollerin birleşiminden efektif izin kümesi."""
        if self.is_superuser:
            from app.core.permissions import ALL_PERMISSIONS

            return set(ALL_PERMISSIONS)
        perms: set[str] = set()
        for role in self.roles:
            perms |= set(role.permissions or [])
        return perms

    def has_permission(self, permission: str) -> bool:
        return self.is_superuser or permission in self.permissions

    def has_any_role(self, codes: set[str] | list[str]) -> bool:
        return bool(set(self.role_codes) & set(codes))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"


class LoginAttempt(Base, IntPKMixin):
    """Giriş denemesi kaydı - rate limiting ve güvenlik denetimi için."""

    __tablename__ = "login_attempts"
    __table_args__ = (Index("ix_login_attempts_email_time", "email", "attempted_at"),)

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    successful: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
