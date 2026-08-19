"""Ders, seri ve kayıt modelleri / Lesson, series and enrollment models.

Tasarım kararı: `Lesson` somut bir zaman dilimidir (tarih + saat + havuz + kulvar
+ eğitmen). Tekrarlanan dersler `LessonSeries` üzerinden üretilir; bu sayede
çakışma denetimi tek ve basit bir sorguya indirgenir.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import EnrollmentStatus, LessonStatus, LessonType

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.facility import Lane, Pool
    from app.models.people import Group, Instructor, Student


class LessonSeries(Base, IntPKMixin, TimestampMixin):
    """Tekrarlanan ders tanımı (ör. her Salı & Perşembe 17:00-18:00)."""

    __tablename__ = "lesson_series"

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    lesson_type: Mapped[str] = mapped_column(
        String(30), default=LessonType.GROUP, nullable=False
    )
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL")
    )
    instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL")
    )
    pool_id: Mapped[int] = mapped_column(
        ForeignKey("pools.id", ondelete="CASCADE"), nullable=False
    )
    lane_id: Mapped[int | None] = mapped_column(
        ForeignKey("lanes.id", ondelete="SET NULL")
    )

    # Haftanın günleri: [0,2] => Pazartesi ve Çarşamba
    weekdays: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    capacity: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#0ea5e9", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="series", cascade="all, delete-orphan"
    )


class Lesson(Base, IntPKMixin, TimestampMixin):
    """Somut bir ders oturumu."""

    __tablename__ = "lessons"
    __table_args__ = (
        Index("ix_lessons_start_end", "start_at", "end_at"),
        Index("ix_lessons_instructor_time", "instructor_id", "start_at"),
        Index("ix_lessons_lane_time", "lane_id", "start_at"),
        Index("ix_lessons_pool_time", "pool_id", "start_at"),
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    lesson_type: Mapped[str] = mapped_column(
        String(30), default=LessonType.GROUP, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=LessonStatus.SCHEDULED, nullable=False, index=True
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    pool_id: Mapped[int] = mapped_column(
        ForeignKey("pools.id", ondelete="CASCADE"), nullable=False
    )
    lane_id: Mapped[int | None] = mapped_column(
        ForeignKey("lanes.id", ondelete="SET NULL")
    )
    instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL")
    )
    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL")
    )
    series_id: Mapped[int | None] = mapped_column(
        ForeignKey("lesson_series.id", ondelete="CASCADE"), index=True
    )

    capacity: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    color: Mapped[str] = mapped_column(String(20), default="#0ea5e9", nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(String(300))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    pool: Mapped["Pool"] = relationship(back_populates="lessons")
    lane: Mapped["Lane | None"] = relationship(back_populates="lessons")
    instructor: Mapped["Instructor | None"] = relationship(back_populates="lessons")
    group: Mapped["Group | None"] = relationship()
    series: Mapped[LessonSeries | None] = relationship(back_populates="lessons")

    enrollments: Mapped[list["LessonEnrollment"]] = relationship(
        back_populates="lesson", cascade="all, delete-orphan"
    )
    # Attendance'ta iki yabancı anahtar var (lesson_id ve makeup_lesson_id);
    # bu ilişki yalnızca asıl ders bağlantısını kullanır.
    attendances: Mapped[list["Attendance"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        foreign_keys="Attendance.lesson_id",
    )

    @property
    def duration_minutes(self) -> int:
        return int((self.end_at - self.start_at).total_seconds() // 60)

    @property
    def enrolled_count(self) -> int:
        return sum(1 for e in self.enrollments if e.status == EnrollmentStatus.ENROLLED)

    @property
    def occupancy_rate(self) -> float:
        return (
            round(self.enrolled_count / self.capacity * 100, 1)
            if self.capacity
            else 0.0
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Lesson {self.title} @ {self.start_at:%Y-%m-%d %H:%M}>"


class LessonEnrollment(Base, IntPKMixin, TimestampMixin):
    """Öğrencinin bir derse kaydı."""

    __tablename__ = "lesson_enrollments"
    __table_args__ = (
        Index("ix_enrollment_unique", "lesson_id", "student_id", unique=True),
    )

    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=EnrollmentStatus.ENROLLED, nullable=False
    )
    membership_id: Mapped[int | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="SET NULL")
    )
    credit_consumed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(400))

    lesson: Mapped[Lesson] = relationship(back_populates="enrollments")
    student: Mapped["Student"] = relationship(back_populates="enrollments")
