"""Performans ve yarışma şemaları / Performance and competition schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.models.enums import CompetitionLevel, CourseType, Stroke
from app.schemas.common import ORMModel

# Standart yarışma mesafeleri (metre)
STANDARD_DISTANCES = [25, 50, 100, 200, 400, 800, 1500]


class PerformanceBase(BaseModel):
    student_id: int
    stroke: Stroke
    distance_m: int = Field(ge=10, le=10000)
    course_type: CourseType = CourseType.SHORT
    time_seconds: float = Field(gt=0, le=36000)
    splits: list[float] = Field(default_factory=list)
    stroke_rate: float | None = Field(default=None, ge=0, le=200)
    stroke_count: int | None = Field(default=None, ge=0, le=1000)
    reaction_time: float | None = Field(default=None, ge=0, le=10)
    turn_time: float | None = Field(default=None, ge=0, le=60)
    recorded_date: date
    is_competition: bool = False
    heart_rate_avg: int | None = Field(default=None, ge=30, le=240)
    perceived_effort: int | None = Field(default=None, ge=1, le=10)
    instructor_id: int | None = None
    lesson_id: int | None = None
    notes: str | None = None


class PerformanceCreate(PerformanceBase):
    pass


class PerformanceUpdate(BaseModel):
    stroke: Stroke | None = None
    distance_m: int | None = None
    course_type: CourseType | None = None
    time_seconds: float | None = None
    splits: list[float] | None = None
    stroke_rate: float | None = None
    stroke_count: int | None = None
    reaction_time: float | None = None
    turn_time: float | None = None
    recorded_date: date | None = None
    is_competition: bool | None = None
    heart_rate_avg: int | None = None
    perceived_effort: int | None = None
    notes: str | None = None


class PerformanceOut(ORMModel, PerformanceBase):
    id: int
    is_personal_best: bool = False
    student_name: str | None = None
    instructor_name: str | None = None
    event_name: str = ""
    pace_per_100m: float | None = None
    speed_ms: float | None = None
    formatted_time: str = ""


class PersonalBestOut(ORMModel):
    id: int
    student_id: int
    stroke: str
    distance_m: int
    course_type: str
    time_seconds: float
    formatted_time: str = ""
    achieved_date: date


class PerformanceTrendPoint(BaseModel):
    date: date
    time_seconds: float
    formatted_time: str
    is_personal_best: bool = False
    moving_average: float | None = None


class PerformanceEventAnalysis(BaseModel):
    """Tek bir etkinlik (ör. 50 m serbest) için istatistiksel analiz.

    Bu bölüm TAMAMEN hesaplanmış gerçek veridir; AI yorumu içermez.
    """

    stroke: str
    distance_m: int
    course_type: str
    record_count: int
    best_time: float
    worst_time: float
    mean_time: float
    median_time: float
    std_dev: float | None = None
    percentile_25: float | None = None
    percentile_75: float | None = None
    first_time: float
    last_time: float
    improvement_seconds: float
    improvement_percent: float
    change_30d: float | None = None
    change_90d: float | None = None
    trend: str = "stable"  # improving | stable | declining
    trend_slope: float | None = None
    points: list[PerformanceTrendPoint] = []


class StudentPerformanceSummary(BaseModel):
    student_id: int
    student_name: str
    total_records: int
    training_count: int
    competition_count: int
    personal_best_count: int
    first_record_date: date | None = None
    last_record_date: date | None = None
    events: list[PerformanceEventAnalysis] = []
    strongest_stroke: str | None = None
    weakest_stroke: str | None = None
    overall_improvement_percent: float | None = None


class PerformanceFilter(BaseModel):
    student_id: int | None = None
    stroke: Stroke | None = None
    distance_m: int | None = None
    course_type: CourseType | None = None
    date_from: date | None = None
    date_to: date | None = None
    is_competition: bool | None = None
    instructor_id: int | None = None


class TopImproverRow(BaseModel):
    student_id: int
    student_name: str
    stroke: str
    distance_m: int
    first_time: float
    last_time: float
    improvement_seconds: float
    improvement_percent: float
    record_count: int


class DecliningAthleteRow(BaseModel):
    student_id: int
    student_name: str
    stroke: str
    distance_m: int
    recent_mean: float
    baseline_mean: float
    decline_seconds: float
    decline_percent: float
    record_count: int
    last_record_date: date


# ---------------------------------------------------------------------------
# Antrenman planı
# ---------------------------------------------------------------------------
class TrainingPlanBase(BaseModel):
    student_id: int
    instructor_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    focus_areas: list[str] = Field(default_factory=list)
    weekly_sessions: list[dict] = Field(default_factory=list)
    goals: str | None = None
    notes: str | None = None


class TrainingPlanCreate(TrainingPlanBase):
    pass


class TrainingPlanOut(ORMModel, TrainingPlanBase):
    id: int
    ai_generated: bool = False
    ai_provider: str | None = None
    ai_model: str | None = None
    is_approved: bool = False
    student_name: str | None = None


# ---------------------------------------------------------------------------
# Yarışma
# ---------------------------------------------------------------------------
class CompetitionBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    location: str | None = None
    organizer: str | None = None
    level: CompetitionLevel = CompetitionLevel.CLUB
    course_type: CourseType = CourseType.SHORT
    start_date: date
    end_date: date
    registration_deadline: date | None = None
    description: str | None = None


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    organizer: str | None = None
    level: CompetitionLevel | None = None
    course_type: CourseType | None = None
    start_date: date | None = None
    end_date: date | None = None
    registration_deadline: date | None = None
    description: str | None = None
    is_completed: bool | None = None


class CompetitionEventBase(BaseModel):
    stroke: Stroke
    distance_m: int = Field(ge=10, le=10000)
    gender_category: str = "mixed"
    age_category: str | None = None
    event_order: int = 1
    scheduled_date: date | None = None


class CompetitionEventCreate(CompetitionEventBase):
    competition_id: int


class CompetitionEntryCreate(BaseModel):
    event_id: int
    student_id: int
    seed_time_seconds: float | None = Field(default=None, gt=0)
    heat_number: int | None = None
    lane_number: int | None = None


class CompetitionResultUpdate(BaseModel):
    result_time_seconds: float | None = Field(default=None, gt=0)
    rank: int | None = Field(default=None, ge=1)
    medal: str | None = None
    is_disqualified: bool = False
    disqualification_reason: str | None = None
    notes: str | None = None


class CompetitionEntryOut(ORMModel):
    id: int
    event_id: int
    student_id: int
    student_name: str | None = None
    seed_time_seconds: float | None = None
    heat_number: int | None = None
    lane_number: int | None = None
    result_time_seconds: float | None = None
    formatted_result: str | None = None
    rank: int | None = None
    medal: str | None = None
    is_personal_best: bool = False
    is_club_record: bool = False
    is_disqualified: bool = False
    improvement_seconds: float | None = None
    notes: str | None = None


class CompetitionEventOut(ORMModel, CompetitionEventBase):
    id: int
    competition_id: int
    name: str = ""
    entry_count: int = 0
    entries: list[CompetitionEntryOut] = []


class CompetitionOut(ORMModel, CompetitionBase):
    id: int
    is_completed: bool = False
    event_count: int = 0
    entry_count: int = 0
    medal_count: int = 0
    events: list[CompetitionEventOut] = []


class ClubRecordOut(ORMModel):
    id: int
    stroke: str
    distance_m: int
    course_type: str
    gender_category: str
    age_category: str
    student_id: int | None = None
    holder_name: str
    time_seconds: float
    formatted_time: str = ""
    achieved_date: date
    competition_name: str | None = None


class HeatSheetLane(BaseModel):
    lane_number: int
    student_id: int | None = None
    student_name: str | None = None
    seed_time: float | None = None
    formatted_seed: str | None = None


class HeatSheet(BaseModel):
    event_id: int
    event_name: str
    heat_number: int
    lanes: list[HeatSheetLane]


class CompetitionReadinessRow(BaseModel):
    """Yarışma öncesi hazırlık göstergesi - istatistiksel, AI değil."""

    student_id: int
    student_name: str
    event_name: str
    best_time: float
    recent_mean: float
    consistency_std: float | None = None
    trend: str
    records_last_30d: int
    attendance_rate_30d: float | None = None
    readiness_score: float
    readiness_basis: str
