"""Sporcu performans modelleri / Athlete performance models."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
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
from app.models.enums import CourseType, Stroke

if TYPE_CHECKING:
    from app.models.people import Instructor, Student


class PerformanceRecord(Base, IntPKMixin, TimestampMixin):
    """Bir yüzme denemesinin ölçüm kaydı.

    `time_seconds` saniye cinsinden ondalıklı derecedir (ör. 32.45).
    `splits` her 25/50 m için ara dereceleri tutan JSON listesidir.
    """

    __tablename__ = "performance_records"
    __table_args__ = (
        Index("ix_perf_student_stroke_distance", "student_id", "stroke", "distance_m"),
        Index("ix_perf_student_date", "student_id", "recorded_date"),
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL")
    )
    lesson_id: Mapped[int | None] = mapped_column(
        ForeignKey("lessons.id", ondelete="SET NULL")
    )

    stroke: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    course_type: Mapped[str] = mapped_column(
        String(10), default=CourseType.SHORT, nullable=False
    )

    time_seconds: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    splits: Mapped[list[float]] = mapped_column(JSON, default=list, nullable=False)

    stroke_rate: Mapped[float | None] = mapped_column(Numeric(6, 2))  # vuruş/dakika
    stroke_count: Mapped[int | None] = mapped_column(Integer)  # toplam kulaç
    reaction_time: Mapped[float | None] = mapped_column(
        Numeric(5, 3)
    )  # çıkış reaksiyonu (sn)
    turn_time: Mapped[float | None] = mapped_column(Numeric(5, 2))  # dönüş süresi (sn)

    recorded_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_personal_best: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_competition: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    heart_rate_avg: Mapped[int | None] = mapped_column(Integer)
    perceived_effort: Mapped[int | None] = mapped_column(Integer)  # 1-10 RPE
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["Student"] = relationship(back_populates="performance_records")
    instructor: Mapped["Instructor | None"] = relationship()

    @property
    def event_name(self) -> str:
        return f"{self.distance_m} m {self.stroke}"

    @property
    def pace_per_100m(self) -> float | None:
        """100 m başına tempo (saniye)."""
        if not self.distance_m:
            return None
        return round(float(self.time_seconds) * 100 / self.distance_m, 2)

    @property
    def speed_ms(self) -> float | None:
        """Ortalama hız (m/sn)."""
        t = float(self.time_seconds)
        return round(self.distance_m / t, 3) if t > 0 else None

    @staticmethod
    def stroke_options() -> list[str]:
        return [s.value for s in Stroke]


class PersonalBest(Base, IntPKMixin, TimestampMixin):
    """Öğrencinin bir etkinlikteki en iyi derecesi (hızlı erişim için materyalize)."""

    __tablename__ = "personal_bests"
    __table_args__ = (
        Index(
            "ix_pb_unique",
            "student_id",
            "stroke",
            "distance_m",
            "course_type",
            unique=True,
        ),
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stroke: Mapped[str] = mapped_column(String(20), nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    course_type: Mapped[str] = mapped_column(
        String(10), default=CourseType.SHORT, nullable=False
    )
    time_seconds: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    achieved_date: Mapped[date] = mapped_column(Date, nullable=False)
    performance_record_id: Mapped[int | None] = mapped_column(
        ForeignKey("performance_records.id", ondelete="SET NULL")
    )


class TrainingPlan(Base, IntPKMixin, TimestampMixin):
    """Öğrenci için antrenman planı (AI önerileri buraya kaydedilebilir)."""

    __tablename__ = "training_plans"

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    focus_areas: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    weekly_sessions: Mapped[list[dict]] = mapped_column(
        JSON, default=list, nullable=False
    )
    goals: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # AI tarafından üretildiyse şeffaflık için işaretlenir
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_provider: Mapped[str | None] = mapped_column(String(40))
    ai_model: Mapped[str | None] = mapped_column(String(120))
    approved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
