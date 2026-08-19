"""İstatistik ve raporlama şemaları / Statistics and reporting schemas."""

from __future__ import annotations

from datetime import date, datetime
from datetime import date as DateType  # `date` alan adıyla çakışmayı önlemek için
from typing import Any, Literal

from pydantic import BaseModel, Field

PeriodKey = Literal[
    "today", "week", "month", "quarter", "half_year", "year", "last_year", "custom"
]


class PeriodFilter(BaseModel):
    period: PeriodKey = "month"
    date_from: date | None = None
    date_to: date | None = None
    pool_id: int | None = None
    instructor_id: int | None = None
    group_id: int | None = None
    student_id: int | None = None
    include_demo: bool = True


class SeriesPoint(BaseModel):
    label: str
    value: float
    secondary: float | None = None
    date: DateType | None = None


class Distribution(BaseModel):
    label: str
    value: float
    percent: float = 0.0
    color: str | None = None


class ComparisonMetric(BaseModel):
    key: str
    label_tr: str
    label_en: str
    current: float
    previous: float | None = None
    change_absolute: float | None = None
    change_percent: float | None = None
    unit: str = "count"
    direction: str = "neutral"  # up_good | up_bad | down_good | down_bad | neutral


# ---------------------------------------------------------------------------
# Öğrenci istatistikleri
# ---------------------------------------------------------------------------
class StudentStatistics(BaseModel):
    period_start: date
    period_end: date
    total_students: int = 0
    active_students: int = 0
    passive_students: int = 0
    trial_students: int = 0
    new_registrations: int = 0
    lost_students: int = 0
    growth_rate: float = 0.0
    retention_rate: float = 0.0
    churn_rate: float = 0.0
    average_membership_days: float = 0.0
    attendance_rate: float = 0.0
    age_distribution: list[Distribution] = Field(default_factory=list)
    level_distribution: list[Distribution] = Field(default_factory=list)
    group_distribution: list[Distribution] = Field(default_factory=list)
    gender_distribution: list[Distribution] = Field(default_factory=list)
    registration_trend: list[SeriesPoint] = Field(default_factory=list)
    comparisons: list[ComparisonMetric] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Eğitmen istatistikleri
# ---------------------------------------------------------------------------
class InstructorStatRow(BaseModel):
    instructor_id: int
    full_name: str
    student_count: int = 0
    lesson_count: int = 0
    total_hours: float = 0.0
    occupancy_rate: float = 0.0
    attendance_rate: float = 0.0
    cancellation_rate: float = 0.0
    private_lesson_count: int = 0
    group_lesson_count: int = 0
    private_ratio: float = 0.0
    student_improvement_percent: float | None = None


class InstructorStatistics(BaseModel):
    period_start: date
    period_end: date
    rows: list[InstructorStatRow] = Field(default_factory=list)
    total_hours: float = 0.0
    average_students_per_instructor: float = 0.0
    average_occupancy: float = 0.0
    disclaimer_tr: str = (
        "Bu göstergeler karar desteği içindir; tek başına bireysel performans "
        "değerlendirmesi olarak kullanılmamalıdır."
    )
    disclaimer_en: str = (
        "These indicators are for decision support only and should not be used "
        "alone as an individual performance evaluation."
    )


# ---------------------------------------------------------------------------
# Havuz / kulvar istatistikleri
# ---------------------------------------------------------------------------
class HeatmapCell(BaseModel):
    weekday: int
    hour: int
    value: float
    lesson_count: int = 0


class PoolStatistics(BaseModel):
    period_start: date
    period_end: date
    pool_usage: list[Distribution] = Field(default_factory=list)
    lane_usage: list[Distribution] = Field(default_factory=list)
    hourly_load: list[SeriesPoint] = Field(default_factory=list)
    daily_load: list[SeriesPoint] = Field(default_factory=list)
    weekly_load: list[SeriesPoint] = Field(default_factory=list)
    busiest_hour: str | None = None
    quietest_hour: str | None = None
    most_used_lane: str | None = None
    overall_occupancy: float = 0.0
    free_capacity_hours: float = 0.0
    average_lanes_per_lesson: float = 0.0
    heatmap: list[HeatmapCell] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Yoklama istatistikleri
# ---------------------------------------------------------------------------
class AttendanceStatistics(BaseModel):
    period_start: date
    period_end: date
    overall_rate: float = 0.0
    present_count: int = 0
    absent_count: int = 0
    late_count: int = 0
    excused_count: int = 0
    cancelled_count: int = 0
    makeup_count: int = 0
    no_show_rate: float = 0.0
    late_rate: float = 0.0
    excuse_rate: float = 0.0
    makeup_rate: float = 0.0
    by_group: list[Distribution] = Field(default_factory=list)
    by_instructor: list[Distribution] = Field(default_factory=list)
    lowest_students: list[dict[str, Any]] = Field(default_factory=list)
    trend: list[SeriesPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Gelişmiş analizler
# ---------------------------------------------------------------------------
class CohortRow(BaseModel):
    cohort: str
    size: int
    retention_by_month: list[float]


class CohortAnalysis(BaseModel):
    cohorts: list[CohortRow]
    months: int
    note_tr: str = "Cohort, öğrencinin kayıt olduğu aya göre gruplanır."
    note_en: str = "Cohorts are grouped by the month the student registered."


class TrendAnalysis(BaseModel):
    metric: str
    points: list[SeriesPoint]
    moving_average: list[SeriesPoint] = Field(default_factory=list)
    slope: float | None = None
    direction: str = "stable"
    seasonality_detected: bool = False
    seasonal_peaks: list[str] = Field(default_factory=list)


class CorrelationResult(BaseModel):
    variable_a: str
    variable_b: str
    coefficient: float
    sample_size: int
    strength: str
    disclaimer_tr: str = (
        "Korelasyon nedensellik anlamına gelmez. İki değişken birlikte hareket "
        "ediyor olabilir; biri diğerinin sebebi olmayabilir."
    )
    disclaimer_en: str = (
        "Correlation does not imply causation. Two variables may move together "
        "without one causing the other."
    )


class OutlierRow(BaseModel):
    entity_type: str
    entity_id: int
    label: str
    value: float
    z_score: float
    direction: str


class DistributionAnalysis(BaseModel):
    metric: str
    count: int
    mean: float
    median: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_25: float
    percentile_75: float
    percentile_90: float
    histogram: list[Distribution] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
class DashboardAlert(BaseModel):
    key: str
    severity: str
    title_tr: str
    title_en: str
    count: int = 0
    link: str | None = None


class DashboardTodayLesson(BaseModel):
    id: int
    title: str
    start_at: datetime
    end_at: datetime
    pool_name: str | None = None
    lane_name: str | None = None
    instructor_name: str | None = None
    enrolled_count: int = 0
    capacity: int = 0
    status: str
    attendance_recorded: bool = False


class DashboardSummary(BaseModel):
    generated_at: datetime
    # Sayaçlar
    active_students: int = 0
    total_students: int = 0
    lessons_today: int = 0
    lessons_completed_today: int = 0
    active_instructors: int = 0
    instructors_on_leave: int = 0
    pool_occupancy_rate: float = 0.0
    lanes_in_use: int = 0
    lanes_free: int = 0
    total_lanes: int = 0
    # Finans
    due_today: float = 0.0
    collected_today: float = 0.0
    overdue_amount: float = 0.0
    overdue_count: int = 0
    monthly_revenue: float = 0.0
    monthly_expense: float = 0.0
    # Operasyon
    attendance_today_rate: float | None = None
    attendance_pending_lessons: int = 0
    upcoming_trials: int = 0
    new_registrations_this_month: int = 0
    expiring_memberships: int = 0
    declining_athletes: int = 0
    upcoming_competitions: int = 0
    unread_notifications: int = 0
    # Listeler
    today_lessons: list[DashboardTodayLesson] = Field(default_factory=list)
    alerts: list[DashboardAlert] = Field(default_factory=list)
    revenue_trend: list[SeriesPoint] = Field(default_factory=list)
    attendance_trend: list[SeriesPoint] = Field(default_factory=list)
    level_distribution: list[Distribution] = Field(default_factory=list)
    pool_load: list[SeriesPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Rapor üretici
# ---------------------------------------------------------------------------
class ReportDefinition(BaseModel):
    key: str
    title_tr: str
    title_en: str
    description_tr: str
    description_en: str
    category: str
    supported_formats: list[str] = Field(default_factory=lambda: ["pdf", "xlsx", "csv"])
    filters: list[str] = Field(default_factory=list)
    required_permission: str


class ReportRequest(BaseModel):
    report_key: str
    format: Literal["pdf", "xlsx", "csv", "json"] = "pdf"
    period: PeriodKey = "month"
    date_from: date | None = None
    date_to: date | None = None
    pool_id: int | None = None
    instructor_id: int | None = None
    group_id: int | None = None
    student_id: int | None = None
    membership_status: str | None = None
    language: Literal["tr", "en"] = "tr"
    include_charts: bool = True


class ReportPreview(BaseModel):
    report_key: str
    title: str
    generated_at: datetime
    period_label: str
    columns: list[dict[str, str]]
    rows: list[dict[str, Any]]
    totals: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)
    row_count: int = 0


class ReportTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    report_key: str
    filters: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    is_shared: bool = False


class ReportTemplateOut(ReportTemplateIn):
    id: int
    owner_user_id: int | None = None
