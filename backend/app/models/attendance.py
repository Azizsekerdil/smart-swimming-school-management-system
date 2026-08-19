"""Yoklama modeli / Attendance model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import AttendanceMethod, AttendanceStatus

if TYPE_CHECKING:
    from app.models.lesson import Lesson
    from app.models.people import Student


class Attendance(Base, IntPKMixin, TimestampMixin):
    """Bir öğrencinin bir dersteki devam kaydı."""

    __tablename__ = "attendances"
    __table_args__ = (
        Index("ix_attendance_unique", "lesson_id", "student_id", unique=True),
        Index("ix_attendance_student_status", "student_id", "status"),
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=AttendanceStatus.PRESENT, nullable=False, index=True
    )
    method: Mapped[str] = mapped_column(
        String(20), default=AttendanceMethod.MANUAL, nullable=False
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    late_minutes: Mapped[int | None] = mapped_column(Integer)
    excuse_reason: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)

    # Telafi dersi bağlantısı
    makeup_lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL")
    )
    counts_toward_credit: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lesson: Mapped["Lesson"] = relationship(
        back_populates="attendances", foreign_keys=[lesson_id]
    )
    student: Mapped["Student"] = relationship(back_populates="attendances")

    @property
    def is_present(self) -> bool:
        return self.status in (
            AttendanceStatus.PRESENT,
            AttendanceStatus.LATE,
            AttendanceStatus.MAKEUP,
        )


class AttendanceToken(Base, IntPKMixin):
    """QR / kart ile yoklama için tek kullanımlık token."""

    __tablename__ = "attendance_tokens"

    token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class StudentCard(Base, IntPKMixin, TimestampMixin):
    """Öğrenci kartı / RFID-NFC kimliği (ileride donanım entegrasyonu için)."""

    __tablename__ = "student_cards"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_code: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    card_type: Mapped[str] = mapped_column(String(20), default="qr", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
