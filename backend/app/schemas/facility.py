"""Havuz, kulvar ve tesis şemaları / Facility schemas."""

from __future__ import annotations

from datetime import date, datetime, time
from datetime import date as DateType  # `date` alan adıyla çakışmayı önlemek için

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CourseType, PoolStatus
from app.schemas.common import ORMModel


class LaneBase(BaseModel):
    lane_number: int = Field(ge=1, le=20)
    name: str | None = Field(default=None, max_length=80)
    width_m: float | None = Field(default=None, ge=0)
    depth_m: float | None = Field(default=None, ge=0)
    max_swimmers: int = Field(default=8, ge=1, le=30)
    is_active: bool = True
    purpose: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class LaneCreate(LaneBase):
    pool_id: int


class LaneUpdate(BaseModel):
    lane_number: int | None = None
    name: str | None = None
    width_m: float | None = None
    depth_m: float | None = None
    max_swimmers: int | None = None
    is_active: bool | None = None
    purpose: str | None = None
    notes: str | None = None


class LaneOut(ORMModel, LaneBase):
    id: int
    pool_id: int
    display_name: str


class PoolBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = Field(default=None, max_length=20)
    location: str | None = Field(default=None, max_length=200)
    length_m: float = Field(default=25, gt=0, le=100)
    width_m: float | None = Field(default=None, gt=0)
    depth_min_m: float | None = Field(default=None, ge=0)
    depth_max_m: float | None = Field(default=None, ge=0)
    lane_count: int = Field(default=6, ge=1, le=20)
    capacity: int = Field(default=60, ge=1)
    course_type: CourseType = CourseType.SHORT
    opening_time: time = time(7, 0)
    closing_time: time = time(22, 0)
    status: PoolStatus = PoolStatus.OPERATIONAL
    water_temperature_c: float | None = None
    air_temperature_c: float | None = None
    is_indoor: bool = True
    is_heated: bool = True
    notes: str | None = None

    @field_validator("closing_time")
    @classmethod
    def _closing_after_opening(cls, v: time, info):  # noqa: ANN001
        opening = info.data.get("opening_time")
        if opening and v <= opening:
            raise ValueError("Kapanış saati açılış saatinden sonra olmalıdır.")
        return v


class PoolCreate(PoolBase):
    auto_create_lanes: bool = True


class PoolUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    location: str | None = None
    length_m: float | None = None
    width_m: float | None = None
    depth_min_m: float | None = None
    depth_max_m: float | None = None
    lane_count: int | None = None
    capacity: int | None = None
    course_type: CourseType | None = None
    opening_time: time | None = None
    closing_time: time | None = None
    status: PoolStatus | None = None
    water_temperature_c: float | None = None
    air_temperature_c: float | None = None
    is_indoor: bool | None = None
    is_heated: bool | None = None
    notes: str | None = None


class PoolOut(ORMModel, PoolBase):
    id: int
    is_demo: bool = False
    lanes: list[LaneOut] = []
    operating_hours: str = ""


class PoolSummary(ORMModel):
    id: int
    name: str
    status: str
    lane_count: int
    active_lane_count: int = 0
    today_lesson_count: int = 0
    occupancy_rate: float = 0.0


class MaintenanceBase(BaseModel):
    start_at: datetime
    end_at: datetime
    maintenance_type: str = "routine"
    description: str | None = None
    cost: float | None = Field(default=None, ge=0)
    performed_by: str | None = None
    is_completed: bool = False


class MaintenanceCreate(MaintenanceBase):
    pool_id: int


class MaintenanceOut(ORMModel, MaintenanceBase):
    id: int
    pool_id: int


class WaterQualityBase(BaseModel):
    measured_at: datetime
    ph: float | None = Field(default=None, ge=0, le=14)
    chlorine_ppm: float | None = Field(default=None, ge=0)
    temperature_c: float | None = None
    turbidity_ntu: float | None = Field(default=None, ge=0)
    measured_by: str | None = None
    notes: str | None = None


class WaterQualityCreate(WaterQualityBase):
    pool_id: int


class WaterQualityOut(ORMModel, WaterQualityBase):
    id: int
    pool_id: int
    is_within_limits: bool


class HolidayBase(BaseModel):
    date: DateType
    name: str = Field(min_length=1, max_length=160)
    is_closed: bool = True


class HolidayOut(ORMModel, HolidayBase):
    id: int


class LaneOccupancySlot(BaseModel):
    """Kulvar planlama ekranı için tek bir zaman dilimi."""

    lane_id: int
    lane_number: int
    lane_name: str
    start_at: datetime
    end_at: datetime
    lesson_id: int | None = None
    lesson_title: str | None = None
    lesson_type: str | None = None
    instructor_name: str | None = None
    enrolled: int = 0
    capacity: int = 0
    color: str = "#94a3b8"
    is_free: bool = True


class LanePlanResponse(BaseModel):
    pool_id: int
    pool_name: str
    date: date
    slots: list[LaneOccupancySlot]
    free_lane_count: int
    used_lane_count: int
    occupancy_rate: float
