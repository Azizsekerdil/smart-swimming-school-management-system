"""Akıllı ders planlama ve çakışma motoru / Smart scheduling & conflict engine.

Bu modül sistemin operasyonel kalbidir. Aynı zaman diliminde:
  * aynı eğitmen,
  * aynı kulvar,
  * aynı öğrenci
iki farklı derse atanamaz. Ayrıca havuz bakımı, havuz çalışma saatleri ve
tatil günleri denetlenir.

Zaman aralığı kesişimi kuralı: [a_start, a_end) ∩ [b_start, b_end) ≠ ∅
  <=>  a_start < b_end  AND  b_start < a_end
Bitişik dersler (14:00-15:00 ve 15:00-16:00) çakışma sayılmaz.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.core.i18n import t
from app.models.enums import EnrollmentStatus, LessonStatus
from app.models.facility import Holiday, Lane, Pool, PoolMaintenance
from app.models.lesson import Lesson, LessonEnrollment, LessonSeries
from app.models.people import Instructor, InstructorLeave, Student
from app.schemas.lesson import ConflictItem


def _overlap_clause(start_at: datetime, end_at: datetime):
    """SQL düzeyinde zaman kesişimi koşulu."""
    return and_(Lesson.start_at < end_at, start_at < Lesson.end_at)


def _active_lesson_clause():
    return Lesson.status.notin_([LessonStatus.CANCELLED, LessonStatus.POSTPONED])


def _naive(dt: datetime) -> datetime:
    """SQLite karşılaştırmaları için timezone bilgisini düşürür."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


class ConflictChecker:
    """Ders planlama çakışmalarını tespit eder."""

    def __init__(self, db: Session, lang: str = "tr") -> None:
        self.db = db
        self.lang = lang

    # ------------------------------------------------------------------
    # Ana giriş noktası
    # ------------------------------------------------------------------
    def check(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        pool_id: int,
        lane_id: int | None = None,
        instructor_id: int | None = None,
        student_ids: Iterable[int] = (),
        exclude_lesson_id: int | None = None,
    ) -> tuple[list[ConflictItem], list[ConflictItem]]:
        """(hatalar, uyarılar) döndürür. Hata varsa ders kaydedilemez."""
        errors: list[ConflictItem] = []
        warnings: list[ConflictItem] = []

        start_at = _naive(start_at)
        end_at = _naive(end_at)

        if end_at <= start_at:
            errors.append(
                ConflictItem(
                    kind="time_range",
                    message_key="lesson.invalid_time_range",
                    message=t("lesson.invalid_time_range", self.lang),
                )
            )
            return errors, warnings

        if instructor_id:
            errors.extend(
                self._instructor_conflicts(
                    start_at, end_at, instructor_id, exclude_lesson_id
                )
            )
            warnings.extend(
                self._instructor_leave_warnings(start_at, end_at, instructor_id)
            )

        if lane_id:
            errors.extend(
                self._lane_conflicts(start_at, end_at, lane_id, exclude_lesson_id)
            )

        student_id_list = [s for s in student_ids if s]
        if student_id_list:
            errors.extend(
                self._student_conflicts(
                    start_at, end_at, student_id_list, exclude_lesson_id
                )
            )

        errors.extend(self._maintenance_conflicts(start_at, end_at, pool_id))
        warnings.extend(self._pool_hours_warnings(start_at, end_at, pool_id))
        warnings.extend(self._holiday_warnings(start_at))

        return errors, warnings

    # ------------------------------------------------------------------
    # Eğitmen
    # ------------------------------------------------------------------
    def _instructor_conflicts(
        self,
        start_at: datetime,
        end_at: datetime,
        instructor_id: int,
        exclude_id: int | None,
    ) -> list[ConflictItem]:
        stmt = select(Lesson).where(
            Lesson.instructor_id == instructor_id,
            _overlap_clause(start_at, end_at),
            _active_lesson_clause(),
        )
        if exclude_id:
            stmt = stmt.where(Lesson.id != exclude_id)

        instructor = self.db.get(Instructor, instructor_id)
        name = instructor.full_name if instructor else str(instructor_id)

        return [
            ConflictItem(
                kind="instructor",
                message_key="lesson.conflict_instructor",
                message=(
                    f"{t('lesson.conflict_instructor', self.lang)} "
                    f"({name}: {clash.title} · {clash.start_at:%H:%M}-{clash.end_at:%H:%M})"
                ),
                lesson_id=clash.id,
                lesson_title=clash.title,
                entity_id=instructor_id,
                entity_name=name,
                start_at=clash.start_at,
                end_at=clash.end_at,
            )
            for clash in self.db.scalars(stmt).all()
        ]

    def _instructor_leave_warnings(
        self, start_at: datetime, end_at: datetime, instructor_id: int
    ) -> list[ConflictItem]:
        day = start_at.date()
        stmt = select(InstructorLeave).where(
            InstructorLeave.instructor_id == instructor_id,
            InstructorLeave.start_date <= day,
            InstructorLeave.end_date >= day,
        )
        leaves = self.db.scalars(stmt).all()
        if not leaves:
            return []
        instructor = self.db.get(Instructor, instructor_id)
        name = instructor.full_name if instructor else str(instructor_id)
        return [
            ConflictItem(
                kind="instructor_leave",
                message_key="instructor.unavailable",
                message=(
                    f"{name} {leave.start_date:%d.%m.%Y}-{leave.end_date:%d.%m.%Y} "
                    f"tarihleri arasında izinli."
                ),
                entity_id=instructor_id,
                entity_name=name,
                severity="warning",
            )
            for leave in leaves
        ]

    # ------------------------------------------------------------------
    # Kulvar
    # ------------------------------------------------------------------
    def _lane_conflicts(
        self, start_at: datetime, end_at: datetime, lane_id: int, exclude_id: int | None
    ) -> list[ConflictItem]:
        stmt = select(Lesson).where(
            Lesson.lane_id == lane_id,
            _overlap_clause(start_at, end_at),
            _active_lesson_clause(),
        )
        if exclude_id:
            stmt = stmt.where(Lesson.id != exclude_id)

        lane = self.db.get(Lane, lane_id)
        name = lane.display_name if lane else str(lane_id)

        return [
            ConflictItem(
                kind="lane",
                message_key="lesson.conflict_lane",
                message=(
                    f"{t('lesson.conflict_lane', self.lang)} "
                    f"({name}: {clash.title} · {clash.start_at:%H:%M}-{clash.end_at:%H:%M})"
                ),
                lesson_id=clash.id,
                lesson_title=clash.title,
                entity_id=lane_id,
                entity_name=name,
                start_at=clash.start_at,
                end_at=clash.end_at,
            )
            for clash in self.db.scalars(stmt).all()
        ]

    # ------------------------------------------------------------------
    # Öğrenci
    # ------------------------------------------------------------------
    def _student_conflicts(
        self,
        start_at: datetime,
        end_at: datetime,
        student_ids: list[int],
        exclude_id: int | None,
    ) -> list[ConflictItem]:
        stmt = (
            select(Lesson, LessonEnrollment.student_id)
            .join(LessonEnrollment, LessonEnrollment.lesson_id == Lesson.id)
            .where(
                LessonEnrollment.student_id.in_(student_ids),
                LessonEnrollment.status == EnrollmentStatus.ENROLLED,
                _overlap_clause(start_at, end_at),
                _active_lesson_clause(),
            )
        )
        if exclude_id:
            stmt = stmt.where(Lesson.id != exclude_id)

        conflicts: list[ConflictItem] = []
        for lesson, student_id in self.db.execute(stmt).all():
            student = self.db.get(Student, student_id)
            name = student.full_name if student else str(student_id)
            conflicts.append(
                ConflictItem(
                    kind="student",
                    message_key="lesson.conflict_student",
                    message=(
                        f"{t('lesson.conflict_student', self.lang)} "
                        f"({name}: {lesson.title} · {lesson.start_at:%H:%M}-{lesson.end_at:%H:%M})"
                    ),
                    lesson_id=lesson.id,
                    lesson_title=lesson.title,
                    entity_id=student_id,
                    entity_name=name,
                    start_at=lesson.start_at,
                    end_at=lesson.end_at,
                )
            )
        return conflicts

    # ------------------------------------------------------------------
    # Havuz
    # ------------------------------------------------------------------
    def _maintenance_conflicts(
        self, start_at: datetime, end_at: datetime, pool_id: int
    ) -> list[ConflictItem]:
        stmt = select(PoolMaintenance).where(
            PoolMaintenance.pool_id == pool_id,
            PoolMaintenance.start_at < end_at,
            start_at < PoolMaintenance.end_at,
            PoolMaintenance.is_completed.is_(False),
        )
        pool = self.db.get(Pool, pool_id)
        name = pool.name if pool else str(pool_id)
        return [
            ConflictItem(
                kind="pool_maintenance",
                message_key="pool.under_maintenance",
                message=(
                    f"{t('pool.under_maintenance', self.lang)} "
                    f"({name}: {m.start_at:%d.%m %H:%M}-{m.end_at:%d.%m %H:%M})"
                ),
                entity_id=pool_id,
                entity_name=name,
                start_at=m.start_at,
                end_at=m.end_at,
            )
            for m in self.db.scalars(stmt).all()
        ]

    def _pool_hours_warnings(
        self, start_at: datetime, end_at: datetime, pool_id: int
    ) -> list[ConflictItem]:
        pool = self.db.get(Pool, pool_id)
        if not pool:
            return []
        if start_at.time() >= pool.opening_time and end_at.time() <= pool.closing_time:
            return []
        return [
            ConflictItem(
                kind="pool_hours",
                message_key="pool.outside_hours",
                message=(
                    f"{t('pool.outside_hours', self.lang)} "
                    f"({pool.name}: {pool.opening_time:%H:%M}-{pool.closing_time:%H:%M})"
                ),
                entity_id=pool_id,
                entity_name=pool.name,
                severity="warning",
            )
        ]

    def _holiday_warnings(self, start_at: datetime) -> list[ConflictItem]:
        holiday = self.db.scalar(
            select(Holiday).where(
                Holiday.date == start_at.date(), Holiday.is_closed.is_(True)
            )
        )
        if not holiday:
            return []
        return [
            ConflictItem(
                kind="holiday",
                message_key="common.validation_error",
                message=f"{holiday.date:%d.%m.%Y} tatil günü: {holiday.name}",
                severity="warning",
            )
        ]


# ---------------------------------------------------------------------------
# Tekrarlanan ders üretimi
# ---------------------------------------------------------------------------
def generate_series_dates(
    start_date: date,
    end_date: date,
    weekdays: list[int],
    skip_holidays: bool = True,
    db: Session | None = None,
) -> list[date]:
    """Seri için ders tarihlerini üretir. weekday: 0=Pazartesi ... 6=Pazar."""
    holidays: set[date] = set()
    if skip_holidays and db is not None:
        holidays = {
            h.date
            for h in db.scalars(
                select(Holiday).where(
                    Holiday.date >= start_date,
                    Holiday.date <= end_date,
                    Holiday.is_closed.is_(True),
                )
            ).all()
        }

    dates: list[date] = []
    current = start_date
    while current <= end_date:
        if current.weekday() in weekdays and current not in holidays:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def build_lessons_from_series(series: LessonSeries, dates: list[date]) -> list[Lesson]:
    """Seriden Lesson nesneleri üretir (henüz DB'ye eklenmez)."""
    lessons: list[Lesson] = []
    for d in dates:
        start_at = datetime.combine(d, series.start_time)
        end_at = datetime.combine(d, series.end_time)
        lessons.append(
            Lesson(
                title=series.title,
                lesson_type=series.lesson_type,
                status=LessonStatus.SCHEDULED,
                start_at=start_at,
                end_at=end_at,
                pool_id=series.pool_id,
                lane_id=series.lane_id,
                instructor_id=series.instructor_id,
                group_id=series.group_id,
                series_id=series.id,
                capacity=series.capacity,
                color=series.color,
                notes=series.notes,
            )
        )
    return lessons


# ---------------------------------------------------------------------------
# Boş kulvar bulma / kulvar planlama
# ---------------------------------------------------------------------------
def find_free_lanes(
    db: Session,
    *,
    pool_id: int,
    start_at: datetime,
    end_at: datetime,
    exclude_lesson_id: int | None = None,
) -> list[Lane]:
    """Verilen zaman aralığında boş olan kulvarları döndürür."""
    start_at, end_at = _naive(start_at), _naive(end_at)
    busy_stmt = select(Lesson.lane_id).where(
        Lesson.pool_id == pool_id,
        Lesson.lane_id.is_not(None),
        _overlap_clause(start_at, end_at),
        _active_lesson_clause(),
    )
    if exclude_lesson_id:
        busy_stmt = busy_stmt.where(Lesson.id != exclude_lesson_id)
    busy_ids = {lane_id for lane_id in db.scalars(busy_stmt).all() if lane_id}

    lanes = db.scalars(
        select(Lane)
        .where(Lane.pool_id == pool_id, Lane.is_active.is_(True))
        .order_by(Lane.lane_number)
    ).all()
    return [lane for lane in lanes if lane.id not in busy_ids]


def suggest_slot(
    db: Session,
    *,
    pool_id: int,
    duration_minutes: int,
    target_date: date,
    instructor_id: int | None = None,
    earliest: time | None = None,
    latest: time | None = None,
    step_minutes: int = 30,
) -> list[dict]:
    """Belirtilen gün için çakışmasız zaman/kulvar önerileri üretir."""
    pool = db.get(Pool, pool_id)
    if not pool:
        return []

    start_bound = earliest or pool.opening_time
    end_bound = latest or pool.closing_time
    checker = ConflictChecker(db)
    suggestions: list[dict] = []

    cursor = datetime.combine(target_date, start_bound)
    day_end = datetime.combine(target_date, end_bound)

    while cursor + timedelta(minutes=duration_minutes) <= day_end:
        slot_end = cursor + timedelta(minutes=duration_minutes)
        free_lanes = find_free_lanes(
            db, pool_id=pool_id, start_at=cursor, end_at=slot_end
        )
        if free_lanes:
            instructor_ok = True
            if instructor_id:
                errors, _ = checker.check(
                    start_at=cursor,
                    end_at=slot_end,
                    pool_id=pool_id,
                    instructor_id=instructor_id,
                )
                instructor_ok = not any(e.kind == "instructor" for e in errors)
            if instructor_ok:
                suggestions.append(
                    {
                        "start_at": cursor,
                        "end_at": slot_end,
                        "free_lane_count": len(free_lanes),
                        "lane_ids": [lane.id for lane in free_lanes],
                        "lane_names": [lane.display_name for lane in free_lanes],
                    }
                )
        cursor += timedelta(minutes=step_minutes)

    return suggestions


def lane_plan(db: Session, *, pool_id: int, day: date) -> dict:
    """Bir günün kulvar planını (saat x kulvar matrisi) üretir."""
    pool = db.get(Pool, pool_id)
    if not pool:
        return {}

    day_start = datetime.combine(day, time.min)
    day_end = day_start + timedelta(days=1)

    lessons = db.scalars(
        select(Lesson)
        .where(
            Lesson.pool_id == pool_id,
            Lesson.start_at >= day_start,
            Lesson.start_at < day_end,
            _active_lesson_clause(),
        )
        .order_by(Lesson.start_at)
    ).all()

    lanes = db.scalars(
        select(Lane).where(Lane.pool_id == pool_id).order_by(Lane.lane_number)
    ).all()

    slots = []
    used_lane_ids: set[int] = set()
    for lesson in lessons:
        if not lesson.lane_id:
            continue
        used_lane_ids.add(lesson.lane_id)
        lane = next((lane for lane in lanes if lane.id == lesson.lane_id), None)
        slots.append(
            {
                "lane_id": lesson.lane_id,
                "lane_number": lane.lane_number if lane else 0,
                "lane_name": lane.display_name if lane else "",
                "start_at": lesson.start_at,
                "end_at": lesson.end_at,
                "lesson_id": lesson.id,
                "lesson_title": lesson.title,
                "lesson_type": lesson.lesson_type,
                "instructor_name": (
                    lesson.instructor.full_name if lesson.instructor else None
                ),
                "enrolled": lesson.enrolled_count,
                "capacity": lesson.capacity,
                "color": lesson.color,
                "is_free": False,
            }
        )

    active_lanes = [lane for lane in lanes if lane.is_active]
    open_minutes = (
        datetime.combine(day, pool.closing_time)
        - datetime.combine(day, pool.opening_time)
    ).total_seconds() / 60
    total_capacity_minutes = open_minutes * max(1, len(active_lanes))
    # Kullanılan dakika, ders nesnelerinden doğrudan hesaplanır; heterojen slot
    # sözlüğünden türetmek tip güvenliğini kaybettiriyordu.
    used_minutes = sum(lesson.duration_minutes for lesson in lessons if lesson.lane_id)

    return {
        "pool_id": pool.id,
        "pool_name": pool.name,
        "date": day,
        "slots": slots,
        "free_lane_count": len(active_lanes) - len(used_lane_ids),
        "used_lane_count": len(used_lane_ids),
        "occupancy_rate": (
            round(used_minutes / total_capacity_minutes * 100, 1)
            if total_capacity_minutes
            else 0.0
        ),
    }


def detect_all_conflicts(db: Session, *, date_from: date, date_to: date) -> list[dict]:
    """Mevcut takvimdeki tüm çakışmaları tarar (sağlık kontrolü / CAIO için)."""
    start = datetime.combine(date_from, time.min)
    end = datetime.combine(date_to, time.max)

    lessons = db.scalars(
        select(Lesson)
        .where(
            Lesson.start_at >= start, Lesson.start_at <= end, _active_lesson_clause()
        )
        .order_by(Lesson.start_at)
    ).all()

    found: list[dict] = []
    for i, a in enumerate(lessons):
        for b in lessons[i + 1 :]:
            if b.start_at >= a.end_at:
                break  # sıralı olduğundan sonrası da kesişmez
            if not (a.start_at < b.end_at and b.start_at < a.end_at):
                continue
            if a.instructor_id and a.instructor_id == b.instructor_id:
                found.append(
                    {
                        "kind": "instructor",
                        "lesson_a": a.id,
                        "lesson_b": b.id,
                        "detail": f"{a.title} / {b.title}",
                        "at": a.start_at.isoformat(),
                    }
                )
            if a.lane_id and a.lane_id == b.lane_id:
                found.append(
                    {
                        "kind": "lane",
                        "lesson_a": a.id,
                        "lesson_b": b.id,
                        "detail": f"{a.title} / {b.title}",
                        "at": a.start_at.isoformat(),
                    }
                )
    return found
