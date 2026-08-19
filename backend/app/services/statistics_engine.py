"""İstatistik motoru / Statistics engine.

Bu modül GERÇEK, HESAPLANMIŞ verileri üretir. Yapay zekâ yorumu içermez;
AI katmanı bu modülün çıktısını girdi olarak kullanır (bkz. services/ai/analysis.py).

Her metrik test edilebilir saf bir fonksiyona ayrılmıştır.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.competition import Competition
from app.models.enums import (
    AttendanceStatus,
    LessonStatus,
    LessonType,
    MembershipStatus,
    PaymentStatus,
    StudentStatus,
)
from app.models.facility import Lane, Pool
from app.models.finance import Expense, Invoice, Payment
from app.models.lesson import Lesson
from app.models.membership import Membership
from app.models.people import Group, Instructor, Student
from app.models.performance import PerformanceRecord
from app.models.system import KpiTarget
from app.schemas.performance import (
    DecliningAthleteRow,
    PerformanceEventAnalysis,
    PerformanceTrendPoint,
    StudentPerformanceSummary,
    TopImproverRow,
)
from app.schemas.statistics import (
    AttendanceStatistics,
    CohortAnalysis,
    CohortRow,
    ComparisonMetric,
    CorrelationResult,
    Distribution,
    DistributionAnalysis,
    HeatmapCell,
    InstructorStatistics,
    InstructorStatRow,
    OutlierRow,
    PoolStatistics,
    SeriesPoint,
    StudentStatistics,
    TrendAnalysis,
)
from app.schemas.system import KpiValue
from app.services.formatting import format_swim_time, weekday_name

PRESENT_STATUSES = [
    AttendanceStatus.PRESENT.value,
    AttendanceStatus.LATE.value,
    AttendanceStatus.MAKEUP.value,
]


# ===========================================================================
# Dönem çözümleme
# ===========================================================================
def resolve_period(
    period: str = "month", date_from: date | None = None, date_to: date | None = None
) -> tuple[date, date]:
    """Dönem anahtarını (start, end) tarih çiftine çevirir."""
    today = date.today()
    if period == "custom" and date_from and date_to:
        return date_from, date_to
    if period == "today":
        return today, today
    if period == "week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        return today.replace(day=1), today
    if period == "quarter":
        quarter_start_month = 3 * ((today.month - 1) // 3) + 1
        return today.replace(month=quarter_start_month, day=1), today
    if period == "half_year":
        return today - timedelta(days=182), today
    if period == "year":
        return today.replace(month=1, day=1), today
    if period == "last_year":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    return today.replace(day=1), today


def previous_period(start: date, end: date) -> tuple[date, date]:
    """Karşılaştırma için bir önceki eş uzunlukta dönem."""
    span = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    return prev_end - timedelta(days=span - 1), prev_end


def _dt_range(start: date, end: date) -> tuple[datetime, datetime]:
    return datetime.combine(start, time.min), datetime.combine(end, time.max)


def _pct_change(current: float, previous: float | None) -> float | None:
    if previous is None or previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def _distribution(
    counts: dict[str, int], colors: dict[str, str] | None = None
) -> list[Distribution]:
    total = sum(counts.values()) or 1
    return [
        Distribution(
            label=str(label),
            value=float(value),
            percent=round(value / total * 100, 1),
            color=(colors or {}).get(str(label)),
        )
        for label, value in sorted(counts.items(), key=lambda kv: -kv[1])
    ]


# ===========================================================================
# Temel istatistik yardımcıları (saf fonksiyonlar - test edilebilir)
# ===========================================================================
def mean(values: list[float]) -> float:
    return round(float(np.mean(values)), 3) if values else 0.0


def median(values: list[float]) -> float:
    return round(float(np.median(values)), 3) if values else 0.0


def std_dev(values: list[float]) -> float | None:
    return round(float(np.std(values, ddof=1)), 3) if len(values) > 1 else None


def percentile(values: list[float], q: float) -> float | None:
    return round(float(np.percentile(values, q)), 3) if values else None


def moving_average(values: list[float], window: int = 3) -> list[float]:
    """Basit hareketli ortalama; ilk noktalar için genişleyen pencere kullanır."""
    if not values:
        return []
    series = pd.Series(values)
    return [
        round(float(v), 3)
        for v in series.rolling(window=window, min_periods=1).mean().tolist()
    ]


def linear_slope(x: list[float], y: list[float]) -> float | None:
    """En küçük kareler eğimi. y birim / x birim."""
    if len(x) < 2 or len(set(x)) < 2:
        return None
    slope, _ = np.polyfit(np.array(x, dtype=float), np.array(y, dtype=float), 1)
    return round(float(slope), 6)


def pearson_correlation(x: list[float], y: list[float]) -> float | None:
    """Pearson korelasyon katsayısı. NEDENSELLİK ANLAMINA GELMEZ."""
    if len(x) < 3 or len(x) != len(y):
        return None
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    coefficient = float(np.corrcoef(np.array(x), np.array(y))[0, 1])
    return None if math.isnan(coefficient) else round(coefficient, 4)


def correlation_strength(coefficient: float) -> str:
    magnitude = abs(coefficient)
    if magnitude >= 0.8:
        return "very_strong"
    if magnitude >= 0.6:
        return "strong"
    if magnitude >= 0.4:
        return "moderate"
    if magnitude >= 0.2:
        return "weak"
    return "negligible"


def detect_outliers(
    values: list[float], threshold: float = 2.0
) -> list[tuple[int, float, float]]:
    """(index, value, z_score) listesi döndürür."""
    if len(values) < 4:
        return []
    array = np.array(values, dtype=float)
    sigma = float(np.std(array, ddof=1))
    if sigma == 0:
        return []
    mu = float(np.mean(array))
    result = []
    for index, value in enumerate(array):
        z = (value - mu) / sigma
        if abs(z) >= threshold:
            result.append((index, float(value), round(float(z), 2)))
    return result


def trend_direction(slope: float | None, lower_is_better: bool = False) -> str:
    """Eğimden yön etiketi üretir. Yüzme derecelerinde düşük değer iyidir."""
    if slope is None or abs(slope) < 1e-6:
        return "stable"
    improving = slope < 0 if lower_is_better else slope > 0
    return "improving" if improving else "declining"


# ===========================================================================
# Öğrenci istatistikleri
# ===========================================================================
def student_statistics(
    db: Session, start: date, end: date, group_id: int | None = None
) -> StudentStatistics:
    base = select(Student)
    if group_id:
        base = base.where(Student.group_id == group_id)
    students = db.scalars(base).all()

    total = len(students)
    by_status: dict[str, int] = defaultdict(int)
    for s in students:
        by_status[s.status] += 1

    new_registrations = sum(1 for s in students if start <= s.registration_date <= end)
    lost = sum(1 for s in students if s.left_date and start <= s.left_date <= end)

    active_at_start = sum(
        1
        for s in students
        if s.registration_date < start and (not s.left_date or s.left_date >= start)
    )
    retention = (
        round((active_at_start - lost) / active_at_start * 100, 1)
        if active_at_start
        else 100.0
    )
    churn = round(100 - retention, 1)
    growth = (
        round((new_registrations - lost) / active_at_start * 100, 1)
        if active_at_start
        else 0.0
    )

    # Yaş dağılımı
    age_buckets = {
        "0-5": 0,
        "6-9": 0,
        "10-13": 0,
        "14-17": 0,
        "18-29": 0,
        "30-49": 0,
        "50+": 0,
    }
    for s in students:
        age = s.age
        if age is None:
            continue
        if age <= 5:
            age_buckets["0-5"] += 1
        elif age <= 9:
            age_buckets["6-9"] += 1
        elif age <= 13:
            age_buckets["10-13"] += 1
        elif age <= 17:
            age_buckets["14-17"] += 1
        elif age <= 29:
            age_buckets["18-29"] += 1
        elif age <= 49:
            age_buckets["30-49"] += 1
        else:
            age_buckets["50+"] += 1

    level_counts: dict[str, int] = defaultdict(int)
    gender_counts: dict[str, int] = defaultdict(int)
    for s in students:
        level_counts[s.swim_level] += 1
        gender_counts[s.gender] += 1

    group_rows = db.execute(
        select(Group.name, func.count(Student.id))
        .outerjoin(Student, Student.group_id == Group.id)
        .group_by(Group.name)
    ).all()
    group_counts = {name: count for name, count in group_rows if count}

    # Ortalama üyelik süresi (gün)
    durations = [
        ((s.left_date or date.today()) - s.registration_date).days for s in students
    ]
    avg_duration = mean([float(d) for d in durations]) if durations else 0.0

    # Devam oranı
    start_dt, end_dt = _dt_range(start, end)
    attendance_rows = db.execute(
        select(Attendance.status, func.count(Attendance.id))
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Lesson.start_at >= start_dt, Lesson.start_at <= end_dt)
        .group_by(Attendance.status)
    ).all()
    attendance_counts = dict(attendance_rows)
    attendance_total = sum(attendance_counts.values())
    present = sum(attendance_counts.get(s, 0) for s in PRESENT_STATUSES)
    attendance_rate = (
        round(present / attendance_total * 100, 1) if attendance_total else 0.0
    )

    # Kayıt trendi (aylık)
    trend: list[SeriesPoint] = []
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        count = sum(1 for s in students if cursor <= s.registration_date < next_month)
        trend.append(
            SeriesPoint(label=f"{cursor:%Y-%m}", value=float(count), date=cursor)
        )
        cursor = next_month

    # Önceki dönem karşılaştırması
    prev_start, prev_end = previous_period(start, end)
    prev_new = sum(1 for s in students if prev_start <= s.registration_date <= prev_end)
    prev_lost = sum(
        1 for s in students if s.left_date and prev_start <= s.left_date <= prev_end
    )

    comparisons = [
        ComparisonMetric(
            key="new_registrations",
            label_tr="Yeni Kayıt",
            label_en="New Registrations",
            current=float(new_registrations),
            previous=float(prev_new),
            change_absolute=float(new_registrations - prev_new),
            change_percent=_pct_change(new_registrations, prev_new),
            direction="up_good",
        ),
        ComparisonMetric(
            key="lost_students",
            label_tr="Kayıp Öğrenci",
            label_en="Lost Students",
            current=float(lost),
            previous=float(prev_lost),
            change_absolute=float(lost - prev_lost),
            change_percent=_pct_change(lost, prev_lost),
            direction="down_good",
        ),
    ]

    return StudentStatistics(
        period_start=start,
        period_end=end,
        total_students=total,
        active_students=by_status.get(StudentStatus.ACTIVE.value, 0),
        passive_students=by_status.get(StudentStatus.PASSIVE.value, 0),
        trial_students=by_status.get(StudentStatus.TRIAL.value, 0),
        new_registrations=new_registrations,
        lost_students=lost,
        growth_rate=growth,
        retention_rate=retention,
        churn_rate=churn,
        average_membership_days=round(avg_duration, 1),
        attendance_rate=attendance_rate,
        age_distribution=_distribution(age_buckets),
        level_distribution=_distribution(dict(level_counts)),
        group_distribution=_distribution(group_counts),
        gender_distribution=_distribution(dict(gender_counts)),
        registration_trend=trend,
        comparisons=comparisons,
    )


# ===========================================================================
# Eğitmen istatistikleri
# ===========================================================================
def instructor_statistics(db: Session, start: date, end: date) -> InstructorStatistics:
    start_dt, end_dt = _dt_range(start, end)
    rows: list[InstructorStatRow] = []

    for instructor in db.scalars(
        select(Instructor).where(Instructor.is_active.is_(True))
    ).all():
        lessons = db.scalars(
            select(Lesson).where(
                Lesson.instructor_id == instructor.id,
                Lesson.start_at >= start_dt,
                Lesson.start_at <= end_dt,
            )
        ).all()
        active = [
            lesson for lesson in lessons if lesson.status != LessonStatus.CANCELLED
        ]
        cancelled = len(lessons) - len(active)

        enrolled = sum(lesson.enrolled_count for lesson in active)
        capacity = sum(lesson.capacity for lesson in active)
        total_hours = sum(lesson.duration_minutes for lesson in active) / 60

        attendance_rows = db.execute(
            select(Attendance.status, func.count(Attendance.id))
            .join(Lesson, Lesson.id == Attendance.lesson_id)
            .where(
                Lesson.instructor_id == instructor.id,
                Lesson.start_at >= start_dt,
                Lesson.start_at <= end_dt,
            )
            .group_by(Attendance.status)
        ).all()
        counts = dict(attendance_rows)
        att_total = sum(counts.values())
        att_present = sum(counts.get(s, 0) for s in PRESENT_STATUSES)

        private_count = sum(
            1 for lesson in active if lesson.lesson_type == LessonType.PRIVATE
        )
        student_count = (
            db.scalar(
                select(func.count(Student.id)).where(
                    Student.primary_instructor_id == instructor.id
                )
            )
            or 0
        )

        rows.append(
            InstructorStatRow(
                instructor_id=instructor.id,
                full_name=instructor.full_name,
                student_count=student_count,
                lesson_count=len(active),
                total_hours=round(total_hours, 1),
                occupancy_rate=round(enrolled / capacity * 100, 1) if capacity else 0.0,
                attendance_rate=(
                    round(att_present / att_total * 100, 1) if att_total else 0.0
                ),
                cancellation_rate=(
                    round(cancelled / len(lessons) * 100, 1) if lessons else 0.0
                ),
                private_lesson_count=private_count,
                group_lesson_count=len(active) - private_count,
                private_ratio=(
                    round(private_count / len(active) * 100, 1) if active else 0.0
                ),
            )
        )

    rows.sort(key=lambda r: r.total_hours, reverse=True)
    return InstructorStatistics(
        period_start=start,
        period_end=end,
        rows=rows,
        total_hours=round(sum(r.total_hours for r in rows), 1),
        average_students_per_instructor=round(
            mean([float(r.student_count) for r in rows]), 1
        ),
        average_occupancy=round(mean([r.occupancy_rate for r in rows]), 1),
    )


# ===========================================================================
# Havuz / kulvar istatistikleri
# ===========================================================================
def pool_statistics(
    db: Session, start: date, end: date, pool_id: int | None = None
) -> PoolStatistics:
    start_dt, end_dt = _dt_range(start, end)
    stmt = select(Lesson).where(
        Lesson.start_at >= start_dt,
        Lesson.start_at <= end_dt,
        Lesson.status != LessonStatus.CANCELLED,
    )
    if pool_id:
        stmt = stmt.where(Lesson.pool_id == pool_id)
    lessons = db.scalars(stmt).all()

    pools = {p.id: p for p in db.scalars(select(Pool)).all()}
    lanes = {lane.id: lane for lane in db.scalars(select(Lane)).all()}

    pool_minutes: dict[str, float] = defaultdict(float)
    lane_minutes: dict[str, float] = defaultdict(float)
    hourly: dict[int, float] = defaultdict(float)
    daily: dict[int, float] = defaultdict(float)
    weekly: dict[str, float] = defaultdict(float)
    heat: dict[tuple[int, int], list[float]] = defaultdict(list)
    lane_usage_per_lesson: list[int] = []

    for lesson in lessons:
        minutes = lesson.duration_minutes
        pool = pools.get(lesson.pool_id)
        pool_minutes[pool.name if pool else f"#{lesson.pool_id}"] += minutes
        if lesson.lane_id:
            lane = lanes.get(lesson.lane_id)
            label = (
                f"{pool.name if pool else ''} - {lane.display_name}"
                if lane
                else f"#{lesson.lane_id}"
            )
            lane_minutes[label] += minutes
            lane_usage_per_lesson.append(1)
        hourly[lesson.start_at.hour] += minutes
        daily[lesson.start_at.weekday()] += minutes
        weekly[
            f"{lesson.start_at.isocalendar().year}-W{lesson.start_at.isocalendar().week:02d}"
        ] += minutes
        heat[(lesson.start_at.weekday(), lesson.start_at.hour)].append(minutes)

    # Toplam kapasite dakikası
    days = (end - start).days + 1
    target_pools = (
        [pools[pool_id]] if pool_id and pool_id in pools else list(pools.values())
    )
    capacity_minutes = 0.0
    for pool in target_pools:
        active_lanes = sum(1 for lane in pool.lanes if lane.is_active) or 1
        open_minutes = (
            datetime.combine(date.today(), pool.closing_time)
            - datetime.combine(date.today(), pool.opening_time)
        ).total_seconds() / 60
        capacity_minutes += open_minutes * active_lanes * days

    used_minutes = sum(lane_minutes.values())
    overall = (
        round(used_minutes / capacity_minutes * 100, 1) if capacity_minutes else 0.0
    )

    busiest = max(hourly.items(), key=lambda kv: kv[1])[0] if hourly else None
    quietest = min(hourly.items(), key=lambda kv: kv[1])[0] if hourly else None
    most_used_lane = (
        max(lane_minutes.items(), key=lambda kv: kv[1])[0] if lane_minutes else None
    )

    heatmap = [
        HeatmapCell(
            weekday=weekday,
            hour=hour,
            value=round(sum(values), 1),
            lesson_count=len(values),
        )
        for (weekday, hour), values in sorted(heat.items())
    ]

    return PoolStatistics(
        period_start=start,
        period_end=end,
        pool_usage=_distribution({k: int(v) for k, v in pool_minutes.items()}),
        lane_usage=_distribution({k: int(v) for k, v in lane_minutes.items()}),
        hourly_load=[
            SeriesPoint(label=f"{hour:02d}:00", value=round(hourly.get(hour, 0), 1))
            for hour in range(6, 24)
        ],
        daily_load=[
            SeriesPoint(label=weekday_name(day), value=round(daily.get(day, 0), 1))
            for day in range(7)
        ],
        weekly_load=[
            SeriesPoint(label=label, value=round(value, 1))
            for label, value in sorted(weekly.items())
        ],
        busiest_hour=f"{busiest:02d}:00" if busiest is not None else None,
        quietest_hour=f"{quietest:02d}:00" if quietest is not None else None,
        most_used_lane=most_used_lane,
        overall_occupancy=overall,
        free_capacity_hours=round(max(0.0, capacity_minutes - used_minutes) / 60, 1),
        average_lanes_per_lesson=(
            round(len(lane_usage_per_lesson) / len(lessons), 2) if lessons else 0.0
        ),
        heatmap=heatmap,
    )


# ===========================================================================
# Yoklama istatistikleri
# ===========================================================================
def attendance_statistics(
    db: Session,
    start: date,
    end: date,
    group_id: int | None = None,
    instructor_id: int | None = None,
) -> AttendanceStatistics:
    start_dt, end_dt = _dt_range(start, end)
    stmt = (
        select(Attendance, Lesson)
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Lesson.start_at >= start_dt, Lesson.start_at <= end_dt)
    )
    if instructor_id:
        stmt = stmt.where(Lesson.instructor_id == instructor_id)
    if group_id:
        stmt = stmt.where(Lesson.group_id == group_id)

    rows = db.execute(stmt).all()
    counts: dict[str, int] = defaultdict(int)
    by_group_total: dict[str, int] = defaultdict(int)
    by_group_present: dict[str, int] = defaultdict(int)
    by_instructor_total: dict[str, int] = defaultdict(int)
    by_instructor_present: dict[str, int] = defaultdict(int)
    per_student: dict[int, list[int]] = defaultdict(list)
    daily: dict[date, list[int]] = defaultdict(list)

    for attendance, lesson in rows:
        counts[attendance.status] += 1
        present = 1 if attendance.status in PRESENT_STATUSES else 0
        group_label = lesson.group.name if lesson.group else "—"
        by_group_total[group_label] += 1
        by_group_present[group_label] += present
        instructor_label = lesson.instructor.full_name if lesson.instructor else "—"
        by_instructor_total[instructor_label] += 1
        by_instructor_present[instructor_label] += present
        per_student[attendance.student_id].append(present)
        daily[lesson.start_at.date()].append(present)

    total = sum(counts.values())
    present_total = sum(counts.get(s, 0) for s in PRESENT_STATUSES)

    def _rate_dist(
        totals: dict[str, int], presents: dict[str, int]
    ) -> list[Distribution]:
        return sorted(
            [
                Distribution(
                    label=label,
                    value=round(presents[label] / count * 100, 1),
                    percent=round(presents[label] / count * 100, 1),
                )
                for label, count in totals.items()
                if count
            ],
            key=lambda d: d.value,
            reverse=True,
        )

    lowest: list[dict] = []
    for student_id, values in per_student.items():
        if len(values) < 3:
            continue
        rate = round(sum(values) / len(values) * 100, 1)
        if rate < 75:
            student = db.get(Student, student_id)
            lowest.append(
                {
                    "student_id": student_id,
                    "student_name": student.full_name if student else f"#{student_id}",
                    "attendance_rate": rate,
                    "records": len(values),
                }
            )
    lowest.sort(key=lambda item: item["attendance_rate"])

    trend = [
        SeriesPoint(
            label=f"{day:%d.%m}",
            value=round(sum(values) / len(values) * 100, 1),
            date=day,
        )
        for day, values in sorted(daily.items())
        if values
    ]

    return AttendanceStatistics(
        period_start=start,
        period_end=end,
        overall_rate=round(present_total / total * 100, 1) if total else 0.0,
        present_count=counts.get(AttendanceStatus.PRESENT.value, 0),
        absent_count=counts.get(AttendanceStatus.ABSENT.value, 0),
        late_count=counts.get(AttendanceStatus.LATE.value, 0),
        excused_count=counts.get(AttendanceStatus.EXCUSED.value, 0),
        cancelled_count=counts.get(AttendanceStatus.CANCELLED.value, 0),
        makeup_count=counts.get(AttendanceStatus.MAKEUP.value, 0),
        no_show_rate=(
            round(counts.get(AttendanceStatus.ABSENT.value, 0) / total * 100, 1)
            if total
            else 0.0
        ),
        late_rate=(
            round(counts.get(AttendanceStatus.LATE.value, 0) / total * 100, 1)
            if total
            else 0.0
        ),
        excuse_rate=(
            round(counts.get(AttendanceStatus.EXCUSED.value, 0) / total * 100, 1)
            if total
            else 0.0
        ),
        makeup_rate=(
            round(counts.get(AttendanceStatus.MAKEUP.value, 0) / total * 100, 1)
            if total
            else 0.0
        ),
        by_group=_rate_dist(by_group_total, by_group_present),
        by_instructor=_rate_dist(by_instructor_total, by_instructor_present),
        lowest_students=lowest[:20],
        trend=trend,
    )


# ===========================================================================
# Performans analizi
# ===========================================================================
def analyze_event(
    records: list[PerformanceRecord], window: int = 3
) -> PerformanceEventAnalysis | None:
    """Tek bir etkinlik için tam istatistiksel analiz (kronolojik sıralı kayıtlar)."""
    if not records:
        return None

    ordered = sorted(records, key=lambda r: r.recorded_date)
    times = [float(r.time_seconds) for r in ordered]
    dates = [r.recorded_date for r in ordered]

    ma = moving_average(times, window)
    x = [(d - dates[0]).days for d in dates]
    slope = linear_slope([float(v) for v in x], times)

    today = date.today()
    recent_30 = [
        float(r.time_seconds) for r in ordered if (today - r.recorded_date).days <= 30
    ]
    recent_90 = [
        float(r.time_seconds) for r in ordered if (today - r.recorded_date).days <= 90
    ]
    older_90 = [
        float(r.time_seconds) for r in ordered if (today - r.recorded_date).days > 90
    ]

    change_30 = (
        round(mean(recent_30) - mean(older_90), 2) if recent_30 and older_90 else None
    )
    change_90 = (
        round(mean(recent_90) - mean(older_90), 2) if recent_90 and older_90 else None
    )

    improvement = round(times[0] - times[-1], 2)  # pozitif = hızlandı
    improvement_pct = round(improvement / times[0] * 100, 2) if times[0] else 0.0
    best = min(times)

    points = [
        PerformanceTrendPoint(
            date=record.recorded_date,
            time_seconds=float(record.time_seconds),
            formatted_time=format_swim_time(record.time_seconds),
            is_personal_best=abs(float(record.time_seconds) - best) < 0.001,
            moving_average=ma[index],
        )
        for index, record in enumerate(ordered)
    ]

    first = ordered[0]
    return PerformanceEventAnalysis(
        stroke=first.stroke,
        distance_m=first.distance_m,
        course_type=first.course_type,
        record_count=len(ordered),
        best_time=round(best, 2),
        worst_time=round(max(times), 2),
        mean_time=mean(times),
        median_time=median(times),
        std_dev=std_dev(times),
        percentile_25=percentile(times, 25),
        percentile_75=percentile(times, 75),
        first_time=round(times[0], 2),
        last_time=round(times[-1], 2),
        improvement_seconds=improvement,
        improvement_percent=improvement_pct,
        change_30d=change_30,
        change_90d=change_90,
        trend=trend_direction(slope, lower_is_better=True),
        trend_slope=slope,
        points=points,
    )


def student_performance_summary(
    db: Session,
    student_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> StudentPerformanceSummary:
    """Bir sporcunun tüm etkinliklerdeki performans özeti."""
    student = db.get(Student, student_id)
    stmt = select(PerformanceRecord).where(PerformanceRecord.student_id == student_id)
    if date_from:
        stmt = stmt.where(PerformanceRecord.recorded_date >= date_from)
    if date_to:
        stmt = stmt.where(PerformanceRecord.recorded_date <= date_to)
    records = db.scalars(stmt.order_by(PerformanceRecord.recorded_date)).all()

    grouped: dict[tuple, list[PerformanceRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.stroke, record.distance_m, record.course_type)].append(record)

    events = [
        analysis for group in grouped.values() if (analysis := analyze_event(group))
    ]
    events.sort(key=lambda e: (e.stroke, e.distance_m))

    # En güçlü/zayıf stil: stil bazında ortalama gelişim yüzdesine göre
    by_stroke: dict[str, list[float]] = defaultdict(list)
    for event in events:
        by_stroke[event.stroke].append(event.improvement_percent)

    strongest = weakest = None
    if by_stroke:
        averages = {stroke: mean(values) for stroke, values in by_stroke.items()}
        strongest = max(averages.items(), key=lambda kv: kv[1])[0]
        weakest = min(averages.items(), key=lambda kv: kv[1])[0]

    overall = mean([e.improvement_percent for e in events]) if events else None

    return StudentPerformanceSummary(
        student_id=student_id,
        student_name=student.full_name if student else f"#{student_id}",
        total_records=len(records),
        training_count=sum(1 for r in records if not r.is_competition),
        competition_count=sum(1 for r in records if r.is_competition),
        personal_best_count=sum(1 for r in records if r.is_personal_best),
        first_record_date=records[0].recorded_date if records else None,
        last_record_date=records[-1].recorded_date if records else None,
        events=events,
        strongest_stroke=strongest,
        weakest_stroke=weakest,
        overall_improvement_percent=round(overall, 2) if overall is not None else None,
    )


def find_top_improvers(
    db: Session, lookback_days: int = 90, min_records: int = 3, limit: int = 20
) -> list[TopImproverRow]:
    """Belirtilen dönemde en çok gelişen sporcular."""
    since = date.today() - timedelta(days=lookback_days)
    records = db.scalars(
        select(PerformanceRecord)
        .where(PerformanceRecord.recorded_date >= since)
        .order_by(PerformanceRecord.recorded_date)
    ).all()

    grouped: dict[tuple, list[PerformanceRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.student_id, record.stroke, record.distance_m)].append(record)

    rows: list[TopImproverRow] = []
    for (student_id, stroke, distance), group in grouped.items():
        if len(group) < min_records:
            continue
        ordered = sorted(group, key=lambda r: r.recorded_date)
        first_time = float(ordered[0].time_seconds)
        last_time = float(ordered[-1].time_seconds)
        improvement = round(first_time - last_time, 2)
        if improvement <= 0:
            continue
        student = db.get(Student, student_id)
        rows.append(
            TopImproverRow(
                student_id=student_id,
                student_name=student.full_name if student else f"#{student_id}",
                stroke=stroke,
                distance_m=distance,
                first_time=round(first_time, 2),
                last_time=round(last_time, 2),
                improvement_seconds=improvement,
                improvement_percent=round(improvement / first_time * 100, 2),
                record_count=len(ordered),
            )
        )

    rows.sort(key=lambda r: r.improvement_percent, reverse=True)
    return rows[:limit]


def find_declining_athletes(
    db: Session, lookback_days: int = 90, min_records: int = 4, limit: int = 20
) -> list[DecliningAthleteRow]:
    """Performansı gerileyen sporcular: son 1/3 ortalaması ilk 2/3'ten kötü."""
    since = date.today() - timedelta(days=lookback_days)
    records = db.scalars(
        select(PerformanceRecord)
        .where(PerformanceRecord.recorded_date >= since)
        .order_by(PerformanceRecord.recorded_date)
    ).all()

    grouped: dict[tuple, list[PerformanceRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.student_id, record.stroke, record.distance_m)].append(record)

    rows: list[DecliningAthleteRow] = []
    for (student_id, stroke, distance), group in grouped.items():
        if len(group) < min_records:
            continue
        ordered = sorted(group, key=lambda r: r.recorded_date)
        split = max(1, len(ordered) * 2 // 3)
        baseline = [float(r.time_seconds) for r in ordered[:split]]
        recent = [float(r.time_seconds) for r in ordered[split:]]
        if not recent or not baseline:
            continue
        baseline_mean = mean(baseline)
        recent_mean = mean(recent)
        decline = round(recent_mean - baseline_mean, 2)  # pozitif = yavaşladı
        if decline <= 0:
            continue
        decline_pct = round(decline / baseline_mean * 100, 2) if baseline_mean else 0.0
        if decline_pct < 1.0:  # gürültüyü ele
            continue
        student = db.get(Student, student_id)
        rows.append(
            DecliningAthleteRow(
                student_id=student_id,
                student_name=student.full_name if student else f"#{student_id}",
                stroke=stroke,
                distance_m=distance,
                recent_mean=recent_mean,
                baseline_mean=baseline_mean,
                decline_seconds=decline,
                decline_percent=decline_pct,
                record_count=len(ordered),
                last_record_date=ordered[-1].recorded_date,
            )
        )

    rows.sort(key=lambda r: r.decline_percent, reverse=True)
    return rows[:limit]


def competition_readiness(
    db: Session, competition_id: int | None = None, lookback_days: int = 60
) -> list[dict]:
    """Yarışma öncesi hazırlık göstergesi.

    Skor tamamen istatistikseldir: son dönem tutarlılığı, gelişim eğilimi ve
    antrenman yoğunluğu birleştirilir. AI tahmini DEĞİLDİR.
    """
    since = date.today() - timedelta(days=lookback_days)
    records = db.scalars(
        select(PerformanceRecord).where(PerformanceRecord.recorded_date >= since)
    ).all()

    grouped: dict[tuple, list[PerformanceRecord]] = defaultdict(list)
    for record in records:
        grouped[(record.student_id, record.stroke, record.distance_m)].append(record)

    rows: list[dict] = []
    for (student_id, stroke, distance), group in grouped.items():
        if len(group) < 3:
            continue
        ordered = sorted(group, key=lambda r: r.recorded_date)
        times = [float(r.time_seconds) for r in ordered]
        best = min(times)
        recent_mean = mean(times[-3:])
        sigma = std_dev(times)
        x = [float((r.recorded_date - ordered[0].recorded_date).days) for r in ordered]
        slope = linear_slope(x, times)

        # Bileşenler (0-100)
        consistency = 100.0
        if sigma is not None and recent_mean:
            consistency = max(0.0, 100.0 - (sigma / recent_mean * 100) * 10)
        form = 50.0
        if best and recent_mean:
            form = max(0.0, 100.0 - (recent_mean - best) / best * 100 * 5)
        trend_score = 50.0
        if slope is not None:
            trend_score = 50.0 - slope * 500  # negatif eğim (hızlanma) skoru artırır
            trend_score = max(0.0, min(100.0, trend_score))
        volume = min(100.0, len(ordered) / 12 * 100)

        score = round(
            consistency * 0.25 + form * 0.35 + trend_score * 0.25 + volume * 0.15, 1
        )
        student = db.get(Student, student_id)

        rows.append(
            {
                "student_id": student_id,
                "student_name": student.full_name if student else f"#{student_id}",
                "event_name": f"{distance} m {stroke}",
                "stroke": stroke,
                "distance_m": distance,
                "best_time": round(best, 2),
                "best_time_formatted": format_swim_time(best),
                "recent_mean": recent_mean,
                "recent_mean_formatted": format_swim_time(recent_mean),
                "consistency_std": sigma,
                "trend": trend_direction(slope, lower_is_better=True),
                "records_last_period": len(ordered),
                "readiness_score": score,
                "readiness_basis": (
                    "tutarlılık %25 + forma yakınlık %35 + gelişim eğilimi %25 + "
                    "antrenman hacmi %15 (istatistiksel, AI değil)"
                ),
            }
        )

    rows.sort(key=lambda r: r["readiness_score"], reverse=True)
    return rows


# ===========================================================================
# Gelişmiş analizler
# ===========================================================================
def cohort_retention(db: Session, months: int = 12) -> CohortAnalysis:
    """Kayıt ayına göre cohort tutundurma analizi."""
    students = db.scalars(select(Student)).all()
    today = date.today()
    start_month = (today.replace(day=1) - timedelta(days=30 * months)).replace(day=1)

    cohorts: dict[str, list[Student]] = defaultdict(list)
    for student in students:
        if student.registration_date >= start_month:
            cohorts[f"{student.registration_date:%Y-%m}"].append(student)

    rows: list[CohortRow] = []
    for label in sorted(cohorts):
        members = cohorts[label]
        cohort_start = datetime.strptime(label, "%Y-%m").date()
        retention: list[float] = []
        for offset in range(months):
            check_date = (cohort_start + timedelta(days=31 * offset)).replace(day=1)
            if check_date > today:
                break
            still_active = sum(
                1 for s in members if not s.left_date or s.left_date >= check_date
            )
            retention.append(round(still_active / len(members) * 100, 1))
        rows.append(
            CohortRow(cohort=label, size=len(members), retention_by_month=retention)
        )

    return CohortAnalysis(cohorts=rows, months=months)


def trend_analysis(
    points: list[tuple[date, float]], metric: str, window: int = 3
) -> TrendAnalysis:
    """Genel amaçlı trend analizi + hareketli ortalama + mevsimsellik sezgisi."""
    ordered = sorted(points, key=lambda p: p[0])
    values = [value for _, value in ordered]
    labels = [f"{d:%Y-%m-%d}" for d, _ in ordered]

    ma = moving_average(values, window)
    x = [float((d - ordered[0][0]).days) for d, _ in ordered] if ordered else []
    slope = linear_slope(x, values) if values else None

    # Basit mevsimsellik: aylık ortalamalar genel ortalamadan %25+ sapıyorsa
    monthly: dict[int, list[float]] = defaultdict(list)
    for d, value in ordered:
        monthly[d.month].append(value)
    overall_mean = mean(values)
    peaks = [
        str(month)
        for month, month_values in monthly.items()
        if overall_mean and mean(month_values) > overall_mean * 1.25
    ]

    return TrendAnalysis(
        metric=metric,
        points=[
            SeriesPoint(label=label, value=value, date=ordered[index][0])
            for index, (label, value) in enumerate(zip(labels, values, strict=False))
        ],
        moving_average=[
            SeriesPoint(label=labels[index], value=value)
            for index, value in enumerate(ma)
        ],
        slope=slope,
        direction=trend_direction(slope),
        seasonality_detected=bool(peaks),
        seasonal_peaks=peaks,
    )


def correlate(
    x: list[float], y: list[float], name_a: str, name_b: str
) -> CorrelationResult | None:
    coefficient = pearson_correlation(x, y)
    if coefficient is None:
        return None
    return CorrelationResult(
        variable_a=name_a,
        variable_b=name_b,
        coefficient=coefficient,
        sample_size=len(x),
        strength=correlation_strength(coefficient),
    )


def distribution_analysis(
    values: list[float], metric: str, bins: int = 10
) -> DistributionAnalysis:
    if not values:
        return DistributionAnalysis(
            metric=metric,
            count=0,
            mean=0,
            median=0,
            std_dev=0,
            min_value=0,
            max_value=0,
            percentile_25=0,
            percentile_75=0,
            percentile_90=0,
        )
    counts, edges = np.histogram(np.array(values, dtype=float), bins=bins)
    total = len(values)
    histogram = [
        Distribution(
            label=f"{edges[i]:.1f}-{edges[i + 1]:.1f}",
            value=float(counts[i]),
            percent=round(float(counts[i]) / total * 100, 1),
        )
        for i in range(len(counts))
    ]
    return DistributionAnalysis(
        metric=metric,
        count=total,
        mean=mean(values),
        median=median(values),
        std_dev=std_dev(values) or 0.0,
        min_value=round(min(values), 3),
        max_value=round(max(values), 3),
        percentile_25=percentile(values, 25) or 0.0,
        percentile_75=percentile(values, 75) or 0.0,
        percentile_90=percentile(values, 90) or 0.0,
        histogram=histogram,
    )


def find_outliers_in_attendance(
    db: Session, start: date, end: date
) -> list[OutlierRow]:
    """Devam oranında istatistiksel aykırı öğrencileri bulur."""
    start_dt, end_dt = _dt_range(start, end)
    rows = db.execute(
        select(Attendance.student_id, Attendance.status)
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Lesson.start_at >= start_dt, Lesson.start_at <= end_dt)
    ).all()

    per_student: dict[int, list[int]] = defaultdict(list)
    for student_id, status in rows:
        per_student[student_id].append(1 if status in PRESENT_STATUSES else 0)

    eligible = {
        student_id: sum(values) / len(values) * 100
        for student_id, values in per_student.items()
        if len(values) >= 4
    }
    if len(eligible) < 4:
        return []

    ids = list(eligible.keys())
    values = [eligible[i] for i in ids]
    outliers = []
    for index, value, z in detect_outliers(values):
        student = db.get(Student, ids[index])
        outliers.append(
            OutlierRow(
                entity_type="student",
                entity_id=ids[index],
                label=student.full_name if student else f"#{ids[index]}",
                value=round(value, 1),
                z_score=z,
                direction="below" if z < 0 else "above",
            )
        )
    return outliers


# ===========================================================================
# KPI
# ===========================================================================
KPI_DEFINITIONS = {
    "active_students": ("Aktif Öğrenci", "Active Students", "count", "up_good"),
    "new_students_monthly": (
        "Aylık Yeni Öğrenci",
        "Monthly New Students",
        "count",
        "up_good",
    ),
    "student_retention": (
        "Öğrenci Tutundurma",
        "Student Retention",
        "percent",
        "up_good",
    ),
    "attendance_rate": ("Devam Oranı", "Attendance Rate", "percent", "up_good"),
    "pool_occupancy": ("Havuz Doluluk", "Pool Occupancy", "percent", "up_good"),
    "lane_occupancy": ("Kulvar Doluluk", "Lane Occupancy", "percent", "up_good"),
    "monthly_revenue": ("Aylık Gelir", "Monthly Revenue", "currency", "up_good"),
    "revenue_per_student": (
        "Öğrenci Başına Gelir",
        "Revenue per Student",
        "currency",
        "up_good",
    ),
    "outstanding_payments": (
        "Bekleyen Tahsilat",
        "Outstanding Payments",
        "currency",
        "down_good",
    ),
    "collection_rate": ("Tahsilat Oranı", "Collection Rate", "percent", "up_good"),
    "average_performance_improvement": (
        "Ortalama Performans Gelişimi",
        "Avg. Performance Improvement",
        "percent",
        "up_good",
    ),
}


def compute_kpis(db: Session, start: date, end: date) -> list[KpiValue]:
    """Tüm KPI'ları hesaplar ve hedeflerle karşılaştırır."""
    targets = {
        target.kpi_key: target
        for target in db.scalars(
            select(KpiTarget).where(KpiTarget.is_active.is_(True))
        ).all()
    }
    prev_start, prev_end = previous_period(start, end)

    student_stats = student_statistics(db, start, end)
    pool_stats = pool_statistics(db, start, end)
    attendance_stats = attendance_statistics(db, start, end)

    payments_sum = (
        db.scalar(
            select(
                func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
            ).where(
                Payment.payment_date >= start,
                Payment.payment_date <= end,
                Payment.status != PaymentStatus.CANCELLED,
            )
        )
        or 0
    )
    prev_payments = (
        db.scalar(
            select(
                func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
            ).where(
                Payment.payment_date >= prev_start,
                Payment.payment_date <= prev_end,
                Payment.status != PaymentStatus.CANCELLED,
            )
        )
        or 0
    )

    outstanding = (
        db.scalar(
            select(
                func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)
            ).where(Invoice.total_amount > Invoice.paid_amount)
        )
        or 0
    )
    invoiced = (
        db.scalar(
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                Invoice.issue_date >= start, Invoice.issue_date <= end
            )
        )
        or 0
    )
    collected = (
        db.scalar(
            select(func.coalesce(func.sum(Invoice.paid_amount), 0)).where(
                Invoice.issue_date >= start, Invoice.issue_date <= end
            )
        )
        or 0
    )

    improvers = find_top_improvers(
        db, lookback_days=(end - start).days + 30, min_records=2, limit=500
    )
    avg_improvement = (
        mean([r.improvement_percent for r in improvers]) if improvers else 0.0
    )

    raw: dict[str, tuple[float, float | None]] = {
        "active_students": (float(student_stats.active_students), None),
        "new_students_monthly": (
            float(student_stats.new_registrations),
            float(student_stats.comparisons[0].previous or 0),
        ),
        "student_retention": (student_stats.retention_rate, None),
        "attendance_rate": (attendance_stats.overall_rate, None),
        "pool_occupancy": (pool_stats.overall_occupancy, None),
        "lane_occupancy": (pool_stats.overall_occupancy, None),
        "monthly_revenue": (
            round(float(payments_sum), 2),
            round(float(prev_payments), 2),
        ),
        "revenue_per_student": (
            (
                round(float(payments_sum) / student_stats.active_students, 2)
                if student_stats.active_students
                else 0.0
            ),
            None,
        ),
        "outstanding_payments": (round(float(outstanding), 2), None),
        "collection_rate": (
            (
                round(float(collected) / float(invoiced) * 100, 1)
                if float(invoiced)
                else 100.0
            ),
            None,
        ),
        "average_performance_improvement": (round(avg_improvement, 2), None),
    }

    result: list[KpiValue] = []
    for key, (value, previous) in raw.items():
        label_tr, label_en, unit, direction = KPI_DEFINITIONS[key]
        target = targets.get(key)
        target_value = target.target_value if target else None
        achievement = None
        status = "neutral"
        if target_value:
            if direction == "down_good":
                achievement = round(target_value / value * 100, 1) if value else 100.0
            else:
                achievement = round(value / target_value * 100, 1)
            status = (
                "good"
                if achievement >= 100
                else "warning" if achievement >= 85 else "bad"
            )

        result.append(
            KpiValue(
                key=key,
                label_tr=label_tr,
                label_en=label_en,
                value=value,
                unit=unit,
                target=target_value,
                achievement_percent=achievement,
                status=status,
                previous_value=previous,
                change_percent=_pct_change(value, previous),
            )
        )
    return result


# ===========================================================================
# Dashboard
# ===========================================================================
def dashboard_summary(db: Session) -> dict:
    """Ana kontrol paneli için tüm sayaç ve listeleri tek seferde üretir."""
    today = date.today()
    month_start = today.replace(day=1)
    day_start, day_end = _dt_range(today, today)

    active_students = (
        db.scalar(
            select(func.count(Student.id)).where(Student.status == StudentStatus.ACTIVE)
        )
        or 0
    )
    total_students = db.scalar(select(func.count(Student.id))) or 0

    today_lessons = db.scalars(
        select(Lesson)
        .where(Lesson.start_at >= day_start, Lesson.start_at <= day_end)
        .order_by(Lesson.start_at)
    ).all()
    completed_today = sum(
        1 for lesson in today_lessons if lesson.status == LessonStatus.COMPLETED
    )

    active_instructors = (
        db.scalar(
            select(func.count(Instructor.id)).where(Instructor.is_active.is_(True))
        )
        or 0
    )

    lanes = db.scalars(select(Lane).where(Lane.is_active.is_(True))).all()
    now = datetime.now()
    in_use = {
        lesson.lane_id
        for lesson in today_lessons
        if lesson.lane_id
        and lesson.start_at <= now <= lesson.end_at
        and lesson.status != LessonStatus.CANCELLED
    }

    pool_stats = pool_statistics(db, today, today)

    collected_today = (
        db.scalar(
            select(
                func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
            ).where(
                Payment.payment_date == today, Payment.status != PaymentStatus.CANCELLED
            )
        )
        or 0
    )
    due_today = (
        db.scalar(
            select(
                func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)
            ).where(
                Invoice.due_date == today, Invoice.total_amount > Invoice.paid_amount
            )
        )
        or 0
    )
    overdue_invoices = db.scalars(
        select(Invoice).where(
            Invoice.due_date < today, Invoice.total_amount > Invoice.paid_amount
        )
    ).all()

    monthly_revenue = (
        db.scalar(
            select(
                func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
            ).where(
                Payment.payment_date >= month_start,
                Payment.payment_date <= today,
                Payment.status != PaymentStatus.CANCELLED,
            )
        )
        or 0
    )
    monthly_expense = (
        db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.expense_date >= month_start, Expense.expense_date <= today
            )
        )
        or 0
    )

    attendance_today = db.execute(
        select(Attendance.status, func.count(Attendance.id))
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Lesson.start_at >= day_start, Lesson.start_at <= day_end)
        .group_by(Attendance.status)
    ).all()
    att_counts = dict(attendance_today)
    att_total = sum(att_counts.values())
    att_present = sum(att_counts.get(s, 0) for s in PRESENT_STATUSES)

    lessons_with_attendance = {
        row[0]
        for row in db.execute(
            select(Attendance.lesson_id)
            .join(Lesson, Lesson.id == Attendance.lesson_id)
            .where(Lesson.start_at >= day_start, Lesson.start_at <= day_end)
            .distinct()
        ).all()
    }
    pending_attendance = sum(
        1
        for lesson in today_lessons
        if lesson.id not in lessons_with_attendance
        and lesson.end_at < now
        and lesson.status != LessonStatus.CANCELLED
    )

    expiring = (
        db.scalar(
            select(func.count(Membership.id)).where(
                Membership.status == MembershipStatus.ACTIVE,
                Membership.end_date.is_not(None),
                Membership.end_date >= today,
                Membership.end_date <= today + timedelta(days=14),
            )
        )
        or 0
    )

    upcoming_trials = (
        db.scalar(
            select(func.count(Lesson.id)).where(
                Lesson.lesson_type == LessonType.TRIAL,
                Lesson.start_at >= now,
                Lesson.start_at
                <= datetime.combine(today + timedelta(days=7), time.max),
            )
        )
        or 0
    )

    new_this_month = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.registration_date >= month_start
            )
        )
        or 0
    )

    upcoming_competitions = (
        db.scalar(
            select(func.count(Competition.id)).where(
                Competition.start_date >= today,
                Competition.start_date <= today + timedelta(days=30),
            )
        )
        or 0
    )

    declining = find_declining_athletes(db, lookback_days=90, min_records=4, limit=100)

    # Gelir trendi (son 30 gün)
    revenue_trend: list[SeriesPoint] = []
    for offset in range(29, -1, -1):
        day = today - timedelta(days=offset)
        amount = (
            db.scalar(
                select(
                    func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
                ).where(
                    Payment.payment_date == day,
                    Payment.status != PaymentStatus.CANCELLED,
                )
            )
            or 0
        )
        revenue_trend.append(
            SeriesPoint(label=f"{day:%d.%m}", value=round(float(amount), 2), date=day)
        )

    attendance_stats = attendance_statistics(db, today - timedelta(days=29), today)
    student_stats = student_statistics(db, month_start, today)

    return {
        "generated_at": datetime.now(),
        "active_students": active_students,
        "total_students": total_students,
        "lessons_today": len(today_lessons),
        "lessons_completed_today": completed_today,
        "active_instructors": active_instructors,
        "instructors_on_leave": 0,
        "pool_occupancy_rate": pool_stats.overall_occupancy,
        "lanes_in_use": len(in_use),
        "lanes_free": max(0, len(lanes) - len(in_use)),
        "total_lanes": len(lanes),
        "due_today": round(float(due_today), 2),
        "collected_today": round(float(collected_today), 2),
        "overdue_amount": round(sum(i.balance for i in overdue_invoices), 2),
        "overdue_count": len(overdue_invoices),
        "monthly_revenue": round(float(monthly_revenue), 2),
        "monthly_expense": round(float(monthly_expense), 2),
        "attendance_today_rate": (
            round(att_present / att_total * 100, 1) if att_total else None
        ),
        "attendance_pending_lessons": pending_attendance,
        "upcoming_trials": upcoming_trials,
        "new_registrations_this_month": new_this_month,
        "expiring_memberships": expiring,
        "declining_athletes": len(declining),
        "upcoming_competitions": upcoming_competitions,
        "today_lessons": [
            {
                "id": lesson.id,
                "title": lesson.title,
                "start_at": lesson.start_at,
                "end_at": lesson.end_at,
                "pool_name": lesson.pool.name if lesson.pool else None,
                "lane_name": lesson.lane.display_name if lesson.lane else None,
                "instructor_name": (
                    lesson.instructor.full_name if lesson.instructor else None
                ),
                "enrolled_count": lesson.enrolled_count,
                "capacity": lesson.capacity,
                "status": lesson.status,
                "attendance_recorded": lesson.id in lessons_with_attendance,
            }
            for lesson in today_lessons
        ],
        "revenue_trend": revenue_trend,
        "attendance_trend": attendance_stats.trend,
        "level_distribution": student_stats.level_distribution,
        "pool_load": pool_stats.hourly_load,
    }
