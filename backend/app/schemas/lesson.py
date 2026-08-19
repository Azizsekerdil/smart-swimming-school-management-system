"""Ders, seri, kayıt ve takvim şemaları / Lesson, series, enrollment schemas."""

from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.enums import EnrollmentStatus, LessonStatus, LessonType
from app.schemas.common import ORMModel


class LessonBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    lesson_type: LessonType = LessonType.GROUP
    start_at: datetime
    end_at: datetime
    pool_id: int
    lane_id: int | None = None
    instructor_id: int | None = None
    group_id: int | None = None
    capacity: int = Field(default=10, ge=1, le=100)
    price: float | None = Field(default=None, ge=0)
    color: str = "#0ea5e9"
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_range(self):  # noqa: ANN201
        if self.end_at <= self.start_at:
            raise ValueError("Bitiş saati başlangıç saatinden sonra olmalıdır.")
        if (self.end_at - self.start_at).total_seconds() > 8 * 3600:
            raise ValueError("Bir ders 8 saatten uzun olamaz.")
        return self


class LessonCreate(LessonBase):
    student_ids: list[int] = Field(default_factory=list)
    force: bool = False  # çakışma uyarılarını yok say (yalnızca yetkili roller)


class LessonUpdate(BaseModel):
    title: str | None = None
    lesson_type: LessonType | None = None
    status: LessonStatus | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    pool_id: int | None = None
    lane_id: int | None = None
    instructor_id: int | None = None
    group_id: int | None = None
    capacity: int | None = None
    price: float | None = None
    color: str | None = None
    notes: str | None = None
    cancellation_reason: str | None = None
    force: bool = False


class EnrollmentOut(ORMModel):
    id: int
    lesson_id: int
    student_id: int
    student_name: str | None = None
    student_number: str | None = None
    status: EnrollmentStatus
    membership_id: int | None = None
    credit_consumed: bool = False
    notes: str | None = None


class LessonOut(ORMModel, LessonBase):
    id: int
    status: LessonStatus
    series_id: int | None = None
    cancellation_reason: str | None = None
    duration_minutes: int = 0
    enrolled_count: int = 0
    occupancy_rate: float = 0.0
    is_demo: bool = False
    pool_name: str | None = None
    lane_name: str | None = None
    instructor_name: str | None = None
    group_name: str | None = None


class LessonDetail(LessonOut):
    enrollments: list[EnrollmentOut] = []
    attendance_recorded: bool = False


class LessonSeriesBase(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    lesson_type: LessonType = LessonType.GROUP
    group_id: int | None = None
    instructor_id: int | None = None
    pool_id: int
    lane_id: int | None = None
    weekdays: list[int] = Field(min_length=1)
    start_time: time
    end_time: time
    start_date: date
    end_date: date
    capacity: int = Field(default=10, ge=1, le=100)
    color: str = "#0ea5e9"
    notes: str | None = None

    @field_validator("weekdays")
    @classmethod
    def _valid_weekdays(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError(
                "Haftanın günü 0 (Pazartesi) ile 6 (Pazar) arasında olmalıdır."
            )
        return sorted(set(v))

    @model_validator(mode="after")
    def _validate(self):  # noqa: ANN201
        if self.end_time <= self.start_time:
            raise ValueError("Bitiş saati başlangıç saatinden sonra olmalıdır.")
        if self.end_date < self.start_date:
            raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")
        if (self.end_date - self.start_date).days > 400:
            raise ValueError("Seri en fazla 400 gün sürebilir.")
        return self


class LessonSeriesCreate(LessonSeriesBase):
    student_ids: list[int] = Field(default_factory=list)
    skip_holidays: bool = True
    force: bool = False


class LessonSeriesOut(ORMModel, LessonSeriesBase):
    id: int
    is_active: bool = True
    generated_lesson_count: int = 0


class EnrollRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)
    use_membership: bool = True
    force: bool = False


class ConflictItem(BaseModel):
    """Tespit edilen tek bir çakışma."""

    kind: str  # instructor | lane | student | pool_maintenance | pool_hours | holiday
    message_key: str
    message: str
    lesson_id: int | None = None
    lesson_title: str | None = None
    entity_id: int | None = None
    entity_name: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    severity: str = "error"  # error | warning


class ConflictCheckRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    pool_id: int
    lane_id: int | None = None
    instructor_id: int | None = None
    student_ids: list[int] = Field(default_factory=list)
    exclude_lesson_id: int | None = None


class ConflictCheckResponse(BaseModel):
    has_conflict: bool
    conflicts: list[ConflictItem] = []
    warnings: list[ConflictItem] = []


class CalendarEvent(BaseModel):
    """Takvim görünümü için hafif olay nesnesi."""

    id: int
    title: str
    start: datetime
    end: datetime
    lesson_type: str
    status: str
    color: str
    pool_id: int
    pool_name: str
    lane_id: int | None = None
    lane_name: str | None = None
    instructor_id: int | None = None
    instructor_name: str | None = None
    group_name: str | None = None
    enrolled_count: int = 0
    capacity: int = 0


class CalendarResponse(BaseModel):
    start: date
    end: date
    events: list[CalendarEvent]
    total: int


class LessonMoveRequest(BaseModel):
    """Takvimde sürükle-bırak ile taşıma."""

    start_at: datetime
    end_at: datetime
    lane_id: int | None = None
    instructor_id: int | None = None
    force: bool = False
