"""Havuz, kulvar ve tesis modelleri / Pool, lane and facility models."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
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
from app.models.enums import CourseType, PoolStatus

if TYPE_CHECKING:
    from app.models.lesson import Lesson


class Pool(Base, IntPKMixin, TimestampMixin):
    """Havuz. Sistem birden fazla havuzu destekler."""

    __tablename__ = "pools"

    name: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True, index=True
    )
    code: Mapped[str | None] = mapped_column(String(20))
    location: Mapped[str | None] = mapped_column(String(200))

    length_m: Mapped[float] = mapped_column(Numeric(6, 2), default=25, nullable=False)
    width_m: Mapped[float | None] = mapped_column(Numeric(6, 2))
    depth_min_m: Mapped[float | None] = mapped_column(Numeric(4, 2))
    depth_max_m: Mapped[float | None] = mapped_column(Numeric(4, 2))
    lane_count: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    course_type: Mapped[str] = mapped_column(
        String(10), default=CourseType.SHORT, nullable=False
    )

    opening_time: Mapped[time] = mapped_column(Time, default=time(7, 0), nullable=False)
    closing_time: Mapped[time] = mapped_column(
        Time, default=time(22, 0), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), default=PoolStatus.OPERATIONAL, nullable=False, index=True
    )
    water_temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    air_temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    is_indoor: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_heated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    lanes: Mapped[list["Lane"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan", order_by="Lane.lane_number"
    )
    maintenances: Mapped[list["PoolMaintenance"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )
    water_logs: Mapped[list["WaterQualityLog"]] = relationship(
        back_populates="pool", cascade="all, delete-orphan"
    )
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="pool")

    @property
    def operating_hours(self) -> str:
        return f"{self.opening_time:%H:%M}-{self.closing_time:%H:%M}"


class Lane(Base, IntPKMixin, TimestampMixin):
    """Havuz kulvarı."""

    __tablename__ = "lanes"
    __table_args__ = (
        Index("ix_lane_pool_number", "pool_id", "lane_number", unique=True),
    )

    pool_id: Mapped[int] = mapped_column(
        ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lane_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(80))
    width_m: Mapped[float | None] = mapped_column(Numeric(4, 2))
    depth_m: Mapped[float | None] = mapped_column(Numeric(4, 2))
    max_swimmers: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(80))  # ör. "Eğitim", "Serbest"
    notes: Mapped[str | None] = mapped_column(String(300))

    pool: Mapped[Pool] = relationship(back_populates="lanes")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="lane")

    @property
    def display_name(self) -> str:
        return self.name or f"Kulvar {self.lane_number}"


class PoolMaintenance(Base, IntPKMixin, TimestampMixin):
    """Havuz bakım kaydı - bakım süresince ders planlanamaz."""

    __tablename__ = "pool_maintenances"

    pool_id: Mapped[int] = mapped_column(
        ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    maintenance_type: Mapped[str] = mapped_column(
        String(60), default="routine", nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    cost: Mapped[float | None] = mapped_column(Numeric(12, 2))
    performed_by: Mapped[str | None] = mapped_column(String(160))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    pool: Mapped[Pool] = relationship(back_populates="maintenances")


class WaterQualityLog(Base, IntPKMixin):
    """Su kalitesi ölçüm kaydı."""

    __tablename__ = "water_quality_logs"

    pool_id: Mapped[int] = mapped_column(
        ForeignKey("pools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ph: Mapped[float | None] = mapped_column(Numeric(4, 2))
    chlorine_ppm: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    turbidity_ntu: Mapped[float | None] = mapped_column(Numeric(5, 2))
    measured_by: Mapped[str | None] = mapped_column(String(160))
    is_within_limits: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(String(400))

    pool: Mapped[Pool] = relationship(back_populates="water_logs")


class Holiday(Base, IntPKMixin):
    """Tatil / kapalı gün - takvimde ders planlanmasını engeller."""

    __tablename__ = "holidays"

    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
