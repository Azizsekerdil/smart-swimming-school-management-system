"""Üyelik ve paket modelleri / Membership and package models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import MembershipStatus, PackageType

if TYPE_CHECKING:
    from app.models.finance import Payment
    from app.models.people import Student


class Package(Base, IntPKMixin, TimestampMixin):
    """Satılabilir paket tanımı (4 Ders, Aylık, Yıllık, Özel Ders Paketi ...)."""

    __tablename__ = "packages"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name_en: Mapped[str | None] = mapped_column(String(120))
    package_type: Mapped[str] = mapped_column(
        String(30), default=PackageType.LESSON_PACK, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)

    lesson_count: Mapped[int | None] = mapped_column(
        Integer
    )  # None => süresiz/sınırsız
    duration_days: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)

    max_freeze_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6366f1", nullable=False)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="package")


class Membership(Base, IntPKMixin, TimestampMixin):
    """Bir öğrencinin satın aldığı paket örneği."""

    __tablename__ = "memberships"
    __table_args__ = (
        Index("ix_membership_student_status", "student_id", "status"),
        Index("ix_membership_end_date", "end_date"),
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("packages.id", ondelete="RESTRICT"), nullable=False
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default=MembershipStatus.ACTIVE, nullable=False, index=True
    )

    total_credits: Mapped[int | None] = mapped_column(Integer)
    used_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    price_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    discount_reason: Mapped[str | None] = mapped_column(String(200))

    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled_at: Mapped[date | None] = mapped_column(Date)
    cancellation_reason: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["Student"] = relationship(back_populates="memberships")
    package: Mapped[Package] = relationship(back_populates="memberships")
    freezes: Mapped[list["MembershipFreeze"]] = relationship(
        back_populates="membership", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="membership")

    @property
    def remaining_credits(self) -> int | None:
        if self.total_credits is None:
            return None
        return max(0, self.total_credits - self.used_credits)

    @property
    def days_remaining(self) -> int | None:
        if not self.end_date:
            return None
        return (self.end_date - date.today()).days

    def expiring_within(self, threshold_days: int = 14) -> bool:
        d = self.days_remaining
        return d is not None and 0 <= d <= threshold_days

    @property
    def is_expiring_soon(self) -> bool:
        return self.expiring_within(14)

    @property
    def usage_rate(self) -> float:
        if not self.total_credits:
            return 0.0
        return round(self.used_credits / self.total_credits * 100, 1)


class MembershipFreeze(Base, IntPKMixin, TimestampMixin):
    """Üyelik dondurma kaydı."""

    __tablename__ = "membership_freezes"

    membership_id: Mapped[int] = mapped_column(
        ForeignKey("memberships.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(300))
    approved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    membership: Mapped[Membership] = relationship(back_populates="freezes")

    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days + 1
