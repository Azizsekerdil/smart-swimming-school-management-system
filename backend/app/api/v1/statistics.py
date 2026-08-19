"""İstatistik ve analitik merkezi uçları / Statistics & analytics center."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_permissions
from app.core.permissions import Perm
from app.models.attendance import Attendance
from app.models.lesson import Lesson
from app.models.people import Student
from app.models.performance import PerformanceRecord
from app.models.system import KpiTarget
from app.models.user import User
from app.schemas.statistics import (
    AttendanceStatistics,
    CohortAnalysis,
    CorrelationResult,
    DashboardSummary,
    DistributionAnalysis,
    InstructorStatistics,
    OutlierRow,
    PeriodKey,
    PoolStatistics,
    StudentStatistics,
)
from app.schemas.system import KpiDashboard, KpiTargetIn, KpiTargetOut
from app.services import audit
from app.services.statistics_engine import (
    PRESENT_STATUSES,
    attendance_statistics,
    cohort_retention,
    compute_kpis,
    correlate,
    dashboard_summary,
    distribution_analysis,
    find_outliers_in_attendance,
    instructor_statistics,
    pool_statistics,
    resolve_period,
    student_statistics,
)

router = APIRouter(prefix="/statistics", tags=["İstatistikler"])


@router.get("/dashboard", response_model=DashboardSummary, summary="Ana kontrol paneli")
def dashboard(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> DashboardSummary:
    data = dashboard_summary(db)

    alerts = []
    if data["overdue_count"]:
        alerts.append(
            {
                "key": "overdue_payments",
                "severity": "error",
                "title_tr": f"{data['overdue_count']} geciken ödeme",
                "title_en": f"{data['overdue_count']} overdue payments",
                "count": data["overdue_count"],
                "link": "/finance?tab=outstanding",
            }
        )
    if data["expiring_memberships"]:
        alerts.append(
            {
                "key": "expiring_memberships",
                "severity": "warning",
                "title_tr": f"{data['expiring_memberships']} üyelik bitmek üzere",
                "title_en": f"{data['expiring_memberships']} memberships expiring",
                "count": data["expiring_memberships"],
                "link": "/memberships?expiring=14",
            }
        )
    if data["attendance_pending_lessons"]:
        alerts.append(
            {
                "key": "pending_attendance",
                "severity": "warning",
                "title_tr": f"{data['attendance_pending_lessons']} derste yoklama alınmadı",
                "title_en": f"Attendance missing for {data['attendance_pending_lessons']} lessons",
                "count": data["attendance_pending_lessons"],
                "link": "/attendance",
            }
        )
    if data["declining_athletes"]:
        alerts.append(
            {
                "key": "declining_athletes",
                "severity": "warning",
                "title_tr": f"{data['declining_athletes']} sporcuda performans düşüşü",
                "title_en": f"Performance decline in {data['declining_athletes']} athletes",
                "count": data["declining_athletes"],
                "link": "/performance?filter=declining",
            }
        )
    if data["upcoming_competitions"]:
        alerts.append(
            {
                "key": "upcoming_competitions",
                "severity": "info",
                "title_tr": f"{data['upcoming_competitions']} yaklaşan yarışma",
                "title_en": f"{data['upcoming_competitions']} upcoming competitions",
                "count": data["upcoming_competitions"],
                "link": "/competitions",
            }
        )

    data["alerts"] = alerts
    return DashboardSummary(**data)


@router.get(
    "/students", response_model=StudentStatistics, summary="Öğrenci istatistikleri"
)
def students_stats(
    period: PeriodKey = "month",
    date_from: date | None = None,
    date_to: date | None = None,
    group_id: int | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> StudentStatistics:
    start, end = resolve_period(period, date_from, date_to)
    return student_statistics(db, start, end, group_id)


@router.get(
    "/instructors",
    response_model=InstructorStatistics,
    summary="Eğitmen istatistikleri",
)
def instructors_stats(
    period: PeriodKey = "month",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> InstructorStatistics:
    start, end = resolve_period(period, date_from, date_to)
    return instructor_statistics(db, start, end)


@router.get(
    "/pools", response_model=PoolStatistics, summary="Havuz/kulvar istatistikleri"
)
def pools_stats(
    period: PeriodKey = "month",
    date_from: date | None = None,
    date_to: date | None = None,
    pool_id: int | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> PoolStatistics:
    start, end = resolve_period(period, date_from, date_to)
    return pool_statistics(db, start, end, pool_id)


@router.get(
    "/attendance", response_model=AttendanceStatistics, summary="Yoklama istatistikleri"
)
def attendance_stats(
    period: PeriodKey = "month",
    date_from: date | None = None,
    date_to: date | None = None,
    group_id: int | None = None,
    instructor_id: int | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> AttendanceStatistics:
    start, end = resolve_period(period, date_from, date_to)
    return attendance_statistics(db, start, end, group_id, instructor_id)


@router.get("/kpi", response_model=KpiDashboard, summary="KPI panosu")
def kpi_dashboard(
    period: PeriodKey = "month",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> KpiDashboard:
    start, end = resolve_period(period, date_from, date_to)
    return KpiDashboard(
        period_start=start, period_end=end, kpis=compute_kpis(db, start, end)
    )


@router.get("/kpi/targets", response_model=list[KpiTargetOut], summary="KPI hedefleri")
def list_kpi_targets(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> list[KpiTargetOut]:
    rows = db.scalars(select(KpiTarget).order_by(KpiTarget.kpi_key)).all()
    return [KpiTargetOut.model_validate(t) for t in rows]


@router.put("/kpi/targets", response_model=KpiTargetOut, summary="KPI hedefi belirle")
def set_kpi_target(
    payload: KpiTargetIn,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.KPI_WRITE)),
) -> KpiTargetOut:
    target = db.scalar(select(KpiTarget).where(KpiTarget.kpi_key == payload.kpi_key))
    if target is None:
        target = KpiTarget(**payload.model_dump())
        db.add(target)
    else:
        for key, value in payload.model_dump().items():
            setattr(target, key, value)
    audit.record(
        db,
        action="update",
        entity_type="kpi_target",
        entity_id=payload.kpi_key,
        user=current,
        summary=f"KPI hedefi: {payload.kpi_key} = {payload.target_value}",
    )
    db.commit()
    db.refresh(target)
    return KpiTargetOut.model_validate(target)


# ---------------------------------------------------------------------------
# Gelişmiş analizler
# ---------------------------------------------------------------------------
@router.get(
    "/cohort", response_model=CohortAnalysis, summary="Cohort tutundurma analizi"
)
def cohort(
    months: int = 12,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> CohortAnalysis:
    return cohort_retention(db, months=min(24, max(3, months)))


@router.get(
    "/outliers/attendance", response_model=list[OutlierRow], summary="Devam aykırıları"
)
def attendance_outliers(
    period: PeriodKey = "quarter",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> list[OutlierRow]:
    start, end = resolve_period(period, date_from, date_to)
    return find_outliers_in_attendance(db, start, end)


@router.get(
    "/correlation/attendance-performance",
    response_model=CorrelationResult | None,
    summary="Devam-performans korelasyonu",
)
def attendance_performance_correlation(
    days: int = 180,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> CorrelationResult | None:
    """Devam oranı ile performans gelişimi arasındaki ilişkiyi ölçer.

    ÖNEMLİ: Korelasyon nedensellik anlamına gelmez.
    """
    since = date.today() - timedelta(days=days)
    attendance_rates: list[float] = []
    improvements: list[float] = []

    for student in db.scalars(select(Student)).all():
        rows = db.execute(
            select(Attendance.status)
            .join(Lesson, Lesson.id == Attendance.lesson_id)
            .where(Attendance.student_id == student.id, Lesson.start_at >= since)
        ).all()
        if len(rows) < 5:
            continue
        present = sum(1 for (status,) in rows if status in PRESENT_STATUSES)
        rate = present / len(rows) * 100

        records = db.scalars(
            select(PerformanceRecord)
            .where(
                PerformanceRecord.student_id == student.id,
                PerformanceRecord.recorded_date >= since,
            )
            .order_by(PerformanceRecord.recorded_date)
        ).all()
        if len(records) < 3:
            continue
        first = float(records[0].time_seconds)
        last = float(records[-1].time_seconds)
        if first <= 0:
            continue
        attendance_rates.append(rate)
        improvements.append((first - last) / first * 100)

    return correlate(
        attendance_rates,
        improvements,
        "attendance_rate",
        "performance_improvement_percent",
    )


@router.get(
    "/distribution/{metric}",
    response_model=DistributionAnalysis,
    summary="Dağılım analizi",
)
def distribution(
    metric: str,
    days: int = 180,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> DistributionAnalysis:
    """Desteklenen metrikler: student_age, attendance_rate, lesson_occupancy."""
    since = date.today() - timedelta(days=days)
    values: list[float] = []

    if metric == "student_age":
        values = [
            float(s.age) for s in db.scalars(select(Student)).all() if s.age is not None
        ]
    elif metric == "attendance_rate":
        for student in db.scalars(select(Student)).all():
            rows = db.execute(
                select(Attendance.status)
                .join(Lesson, Lesson.id == Attendance.lesson_id)
                .where(Attendance.student_id == student.id, Lesson.start_at >= since)
            ).all()
            if len(rows) >= 3:
                present = sum(1 for (status,) in rows if status in PRESENT_STATUSES)
                values.append(present / len(rows) * 100)
    elif metric == "lesson_occupancy":
        lessons = db.scalars(select(Lesson)).all()
        values = [lesson.occupancy_rate for lesson in lessons if lesson.capacity]

    return distribution_analysis(values, metric)


@router.get("/overview", summary="Tüm istatistiklerin özeti")
def overview(
    period: PeriodKey = "month",
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STATISTICS_READ)),
) -> dict:
    """İstatistik Merkezi ana ekranı için birleşik özet."""
    start, end = resolve_period(period, date_from, date_to)
    return {
        "period": {"start": start.isoformat(), "end": end.isoformat(), "key": period},
        "students": student_statistics(db, start, end).model_dump(mode="json"),
        "instructors": instructor_statistics(db, start, end).model_dump(mode="json"),
        "pools": pool_statistics(db, start, end).model_dump(mode="json"),
        "attendance": attendance_statistics(db, start, end).model_dump(mode="json"),
        "kpis": [k.model_dump(mode="json") for k in compute_kpis(db, start, end)],
    }
