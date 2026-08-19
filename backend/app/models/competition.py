"""Yarışma modelleri / Competition models."""

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
from app.models.enums import CompetitionLevel, CourseType

if TYPE_CHECKING:
    from app.models.people import Student


class Competition(Base, IntPKMixin, TimestampMixin):
    """Yarışma / etkinlik."""

    __tablename__ = "competitions"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    location: Mapped[str | None] = mapped_column(String(200))
    organizer: Mapped[str | None] = mapped_column(String(200))
    level: Mapped[str] = mapped_column(
        String(20), default=CompetitionLevel.CLUB, nullable=False
    )
    course_type: Mapped[str] = mapped_column(
        String(10), default=CourseType.SHORT, nullable=False
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    registration_deadline: Mapped[date | None] = mapped_column(Date)

    description: Mapped[str | None] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    events: Mapped[list["CompetitionEvent"]] = relationship(
        back_populates="competition", cascade="all, delete-orphan"
    )


class CompetitionEvent(Base, IntPKMixin, TimestampMixin):
    """Yarışma içindeki bir etkinlik (ör. 50 m Serbest - Erkekler 12-13 yaş)."""

    __tablename__ = "competition_events"

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stroke: Mapped[str] = mapped_column(String(20), nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    gender_category: Mapped[str] = mapped_column(
        String(20), default="mixed", nullable=False
    )
    age_category: Mapped[str | None] = mapped_column(String(60))
    event_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    scheduled_date: Mapped[date | None] = mapped_column(Date)

    competition: Mapped[Competition] = relationship(back_populates="events")
    entries: Mapped[list["CompetitionEntry"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )

    @property
    def name(self) -> str:
        return f"{self.distance_m} m {self.stroke}"


class CompetitionEntry(Base, IntPKMixin, TimestampMixin):
    """Sporcunun bir etkinliğe kaydı ve sonucu."""

    __tablename__ = "competition_entries"
    __table_args__ = (Index("ix_entry_unique", "event_id", "student_id", unique=True),)

    event_id: Mapped[int] = mapped_column(
        ForeignKey("competition_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )

    seed_time_seconds: Mapped[float | None] = mapped_column(Numeric(8, 2))
    heat_number: Mapped[int | None] = mapped_column(Integer)
    lane_number: Mapped[int | None] = mapped_column(Integer)

    result_time_seconds: Mapped[float | None] = mapped_column(Numeric(8, 2))
    rank: Mapped[int | None] = mapped_column(Integer)
    medal: Mapped[str | None] = mapped_column(String(20))  # gold | silver | bronze
    is_personal_best: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_club_record: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_disqualified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    disqualification_reason: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)

    event: Mapped[CompetitionEvent] = relationship(back_populates="entries")
    student: Mapped["Student"] = relationship(back_populates="competition_entries")

    @property
    def improvement_seconds(self) -> float | None:
        """Seed time'a göre gelişim (negatif = daha hızlı)."""
        if self.seed_time_seconds is None or self.result_time_seconds is None:
            return None
        return round(float(self.result_time_seconds) - float(self.seed_time_seconds), 2)


class ClubRecord(Base, IntPKMixin, TimestampMixin):
    """Kulüp rekoru."""

    __tablename__ = "club_records"
    __table_args__ = (
        Index(
            "ix_club_record_unique",
            "stroke",
            "distance_m",
            "course_type",
            "gender_category",
            "age_category",
            unique=True,
        ),
    )

    stroke: Mapped[str] = mapped_column(String(20), nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    course_type: Mapped[str] = mapped_column(
        String(10), default=CourseType.SHORT, nullable=False
    )
    gender_category: Mapped[str] = mapped_column(
        String(20), default="mixed", nullable=False
    )
    age_category: Mapped[str] = mapped_column(
        String(60), default="open", nullable=False
    )

    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL")
    )
    holder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    time_seconds: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    achieved_date: Mapped[date] = mapped_column(Date, nullable=False)
    competition_name: Mapped[str | None] = mapped_column(String(200))
