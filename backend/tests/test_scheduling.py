"""Ders planlama ve çakışma motoru testleri / Scheduling and conflict engine tests.

Bu modül sistemin en kritik iş kuralını doğrular: aynı anda aynı eğitmen,
aynı kulvar veya aynı öğrenci iki farklı derse atanamaz.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import EnrollmentStatus, LessonStatus, LessonType
from app.models.facility import Holiday, Lane, Pool, PoolMaintenance
from app.models.lesson import Lesson, LessonEnrollment, LessonSeries
from app.models.people import Instructor, InstructorLeave, Student
from app.services.scheduling import (
    ConflictChecker,
    build_lessons_from_series,
    detect_all_conflicts,
    find_free_lanes,
    generate_series_dates,
    lane_plan,
    suggest_slot,
)


def _lesson(
    db: Session,
    pool: Pool,
    *,
    lane_id=None,
    instructor_id=None,
    start: datetime,
    end: datetime,
    title="Ders",
    status=LessonStatus.SCHEDULED,
) -> Lesson:
    lesson = Lesson(
        title=title,
        lesson_type=LessonType.GROUP,
        status=status,
        start_at=start,
        end_at=end,
        pool_id=pool.id,
        lane_id=lane_id,
        instructor_id=instructor_id,
        capacity=8,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# ===========================================================================
# Zaman kesişimi kuralı
# ===========================================================================
class TestOverlapRule:
    """[a_start, a_end) ∩ [b_start, b_end) ≠ ∅  <=>  a_start < b_end AND b_start < a_end"""

    def test_identical_slot_conflicts(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        assert any(e.kind == "lane" for e in errors)

    def test_partial_overlap_start_conflicts(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17, 30),
            end_at=tomorrow_at(18, 30),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        assert any(e.kind == "lane" for e in errors)

    def test_partial_overlap_end_conflicts(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(16, 30),
            end_at=tomorrow_at(17, 30),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        assert any(e.kind == "lane" for e in errors)

    def test_fully_contained_conflicts(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(16), end=tomorrow_at(19)
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        assert any(e.kind == "lane" for e in errors)

    def test_adjacent_lessons_do_not_conflict(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        """14:00-15:00 ve 15:00-16:00 bitişiktir, çakışma DEĞİLDİR."""
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(14), end=tomorrow_at(15)
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(15),
            end_at=tomorrow_at(16),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        assert not any(e.kind == "lane" for e in errors)

    def test_separate_times_do_not_conflict(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(10), end=tomorrow_at(11)
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(15),
            end_at=tomorrow_at(16),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        assert errors == []


# ===========================================================================
# Kaynak bazlı çakışmalar
# ===========================================================================
class TestResourceConflicts:
    def test_instructor_conflict_detected(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        """Aynı eğitmen aynı saatte iki derste olamaz - farklı kulvar olsa bile."""
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[1].id,
            instructor_id=instructor.id,
        )
        assert any(e.kind == "instructor" for e in errors)

    def test_different_instructors_no_conflict(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        second_instructor: Instructor,
        tomorrow_at,
    ):
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[1].id,
            instructor_id=second_instructor.id,
        )
        assert errors == []

    def test_different_lanes_no_conflict(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[1].id,
        )
        assert errors == []

    def test_student_conflict_detected(
        self, db: Session, pool: Pool, lanes: list[Lane], student: Student, tomorrow_at
    ):
        """Aynı öğrenci aynı saatte iki derse kayıtlı olamaz."""
        existing = _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        db.add(LessonEnrollment(lesson_id=existing.id, student_id=student.id))
        db.commit()

        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[2].id,
            student_ids=[student.id],
        )
        assert any(e.kind == "student" for e in errors)

    def test_cancelled_enrollment_does_not_conflict(
        self, db: Session, pool: Pool, lanes: list[Lane], student: Student, tomorrow_at
    ):
        existing = _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        db.add(
            LessonEnrollment(
                lesson_id=existing.id,
                student_id=student.id,
                status=EnrollmentStatus.CANCELLED,
            )
        )
        db.commit()
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[2].id,
            student_ids=[student.id],
        )
        assert errors == []

    def test_cancelled_lesson_does_not_conflict(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
            status=LessonStatus.CANCELLED,
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
        )
        assert errors == []

    def test_exclude_lesson_id_ignores_self(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        """Ders güncellenirken kendisiyle çakıştığı raporlanmamalı."""
        existing = _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
        )
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            exclude_lesson_id=existing.id,
        )
        assert errors == []

    def test_invalid_time_range_rejected(self, db: Session, pool: Pool, tomorrow_at):
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(18), end_at=tomorrow_at(17), pool_id=pool.id
        )
        assert any(e.kind == "time_range" for e in errors)


# ===========================================================================
# Havuz kısıtları
# ===========================================================================
class TestPoolConstraints:
    def test_maintenance_blocks_lesson(self, db: Session, pool: Pool, tomorrow_at):
        db.add(
            PoolMaintenance(
                pool_id=pool.id,
                start_at=tomorrow_at(16),
                end_at=tomorrow_at(20),
                maintenance_type="filter",
            )
        )
        db.commit()
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17), end_at=tomorrow_at(18), pool_id=pool.id
        )
        assert any(e.kind == "pool_maintenance" for e in errors)

    def test_completed_maintenance_does_not_block(
        self, db: Session, pool: Pool, tomorrow_at
    ):
        db.add(
            PoolMaintenance(
                pool_id=pool.id,
                start_at=tomorrow_at(16),
                end_at=tomorrow_at(20),
                maintenance_type="filter",
                is_completed=True,
            )
        )
        db.commit()
        errors, _ = ConflictChecker(db).check(
            start_at=tomorrow_at(17), end_at=tomorrow_at(18), pool_id=pool.id
        )
        assert errors == []

    def test_outside_hours_is_warning_not_error(
        self, db: Session, pool: Pool, tomorrow_at
    ):
        """Havuz 08:00-22:00 açık; 06:00 dersi uyarı üretir ama engellemez."""
        errors, warnings = ConflictChecker(db).check(
            start_at=tomorrow_at(6), end_at=tomorrow_at(7), pool_id=pool.id
        )
        assert errors == []
        assert any(w.kind == "pool_hours" for w in warnings)

    def test_holiday_is_warning(self, db: Session, pool: Pool, tomorrow_at):
        db.add(Holiday(date=(date.today() + timedelta(days=1)), name="Test Tatili"))
        db.commit()
        _, warnings = ConflictChecker(db).check(
            start_at=tomorrow_at(17), end_at=tomorrow_at(18), pool_id=pool.id
        )
        assert any(w.kind == "holiday" for w in warnings)

    def test_instructor_leave_is_warning(
        self, db: Session, pool: Pool, instructor: Instructor, tomorrow_at
    ):
        tomorrow = date.today() + timedelta(days=1)
        db.add(
            InstructorLeave(
                instructor_id=instructor.id,
                start_date=tomorrow,
                end_date=tomorrow,
                leave_type="annual",
                approved=True,
            )
        )
        db.commit()
        _, warnings = ConflictChecker(db).check(
            start_at=tomorrow_at(17),
            end_at=tomorrow_at(18),
            pool_id=pool.id,
            instructor_id=instructor.id,
        )
        assert any(w.kind == "instructor_leave" for w in warnings)


# ===========================================================================
# Boş kulvar / öneri
# ===========================================================================
class TestFreeLanes:
    def test_all_lanes_free_when_empty(self, db: Session, pool: Pool, tomorrow_at):
        free = find_free_lanes(
            db, pool_id=pool.id, start_at=tomorrow_at(17), end_at=tomorrow_at(18)
        )
        assert len(free) == 4

    def test_occupied_lane_excluded(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        free = find_free_lanes(
            db, pool_id=pool.id, start_at=tomorrow_at(17), end_at=tomorrow_at(18)
        )
        assert lanes[0].id not in [lane.id for lane in free]
        assert len(free) == 3

    def test_inactive_lane_excluded(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        lanes[1].is_active = False
        db.commit()
        free = find_free_lanes(
            db, pool_id=pool.id, start_at=tomorrow_at(17), end_at=tomorrow_at(18)
        )
        assert lanes[1].id not in [lane.id for lane in free]

    def test_suggest_slot_returns_options(self, db: Session, pool: Pool):
        suggestions = suggest_slot(
            db,
            pool_id=pool.id,
            duration_minutes=60,
            target_date=date.today() + timedelta(days=1),
            earliest=time(9, 0),
            latest=time(12, 0),
        )
        assert len(suggestions) > 0
        assert all(s["free_lane_count"] > 0 for s in suggestions)

    def test_suggest_slot_avoids_busy_instructor(
        self, db: Session, pool: Pool, lanes: list[Lane], instructor: Instructor
    ):
        tomorrow = date.today() + timedelta(days=1)
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=datetime.combine(tomorrow, time(9, 0)),
            end=datetime.combine(tomorrow, time(12, 0)),
        )
        suggestions = suggest_slot(
            db,
            pool_id=pool.id,
            duration_minutes=60,
            target_date=tomorrow,
            instructor_id=instructor.id,
            earliest=time(9, 0),
            latest=time(12, 0),
        )
        # Eğitmen 09:00-12:00 dolu olduğundan bu aralıkta öneri olmamalı
        assert suggestions == []


class TestLanePlan:
    def test_lane_plan_lists_lessons(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
            title="Yunuslar",
        )
        plan = lane_plan(db, pool_id=pool.id, day=date.today() + timedelta(days=1))
        assert plan["used_lane_count"] == 1
        assert plan["free_lane_count"] == 3
        assert plan["slots"][0]["lesson_title"] == "Yunuslar"
        assert plan["occupancy_rate"] > 0

    def test_empty_day_plan(self, db: Session, pool: Pool):
        plan = lane_plan(db, pool_id=pool.id, day=date.today() + timedelta(days=5))
        assert plan["slots"] == []
        assert plan["used_lane_count"] == 0
        assert plan["occupancy_rate"] == 0.0


# ===========================================================================
# Tekrarlanan ders serisi
# ===========================================================================
class TestSeriesGeneration:
    def test_generates_correct_weekdays(self, db: Session):
        # 2026-08-17 Pazartesi
        start = date(2026, 8, 17)
        end = date(2026, 8, 30)
        dates = generate_series_dates(start, end, [0, 2], skip_holidays=False, db=db)
        assert all(d.weekday() in (0, 2) for d in dates)
        assert len(dates) == 4  # 2 hafta x 2 gün

    def test_skips_holidays(self, db: Session):
        start = date(2026, 8, 17)
        end = date(2026, 8, 30)
        db.add(Holiday(date=date(2026, 8, 19), name="Test Tatili"))
        db.commit()
        dates = generate_series_dates(start, end, [0, 2], skip_holidays=True, db=db)
        assert date(2026, 8, 19) not in dates
        assert len(dates) == 3

    def test_build_lessons_from_series(
        self, db: Session, pool: Pool, instructor: Instructor
    ):
        series = LessonSeries(
            title="Haftalık Ders",
            lesson_type=LessonType.GROUP,
            pool_id=pool.id,
            instructor_id=instructor.id,
            weekdays=[0, 2],
            start_time=time(17, 0),
            end_time=time(18, 0),
            start_date=date(2026, 8, 17),
            end_date=date(2026, 8, 30),
            capacity=10,
        )
        db.add(series)
        db.commit()

        dates = generate_series_dates(
            series.start_date, series.end_date, series.weekdays, False, db
        )
        lessons = build_lessons_from_series(series, dates)
        assert len(lessons) == 4
        assert all(lesson.start_at.time() == time(17, 0) for lesson in lessons)
        assert all(lesson.series_id == series.id for lesson in lessons)


class TestConflictScanner:
    def test_detects_existing_double_booking(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        """Doğrudan veritabanına yazılmış çakışmaları tarayabilmeli (CAIO için)."""
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17),
            end=tomorrow_at(18),
            title="A",
        )
        _lesson(
            db,
            pool,
            lane_id=lanes[0].id,
            instructor_id=instructor.id,
            start=tomorrow_at(17, 30),
            end=tomorrow_at(18, 30),
            title="B",
        )

        found = detect_all_conflicts(
            db, date_from=date.today(), date_to=date.today() + timedelta(days=7)
        )
        kinds = {item["kind"] for item in found}
        assert "lane" in kinds
        assert "instructor" in kinds

    def test_clean_schedule_has_no_conflicts(
        self, db: Session, pool: Pool, lanes: list[Lane], tomorrow_at
    ):
        _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        _lesson(
            db, pool, lane_id=lanes[1].id, start=tomorrow_at(17), end=tomorrow_at(18)
        )
        found = detect_all_conflicts(
            db, date_from=date.today(), date_to=date.today() + timedelta(days=7)
        )
        assert found == []


# ===========================================================================
# API düzeyinde
# ===========================================================================
class TestSchedulingAPI:
    def test_create_lesson_success(
        self,
        client: TestClient,
        admin_headers: dict,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        tomorrow_at,
    ):
        response = client.post(
            "/api/v1/lessons",
            headers=admin_headers,
            json={
                "title": "Yeni Ders",
                "lesson_type": "group",
                "start_at": tomorrow_at(17).isoformat(),
                "end_at": tomorrow_at(18).isoformat(),
                "pool_id": pool.id,
                "lane_id": lanes[0].id,
                "instructor_id": instructor.id,
                "capacity": 8,
            },
        )
        assert response.status_code == 201
        assert response.json()["duration_minutes"] == 60

    def test_create_conflicting_lesson_returns_409(
        self,
        client: TestClient,
        admin_headers: dict,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        lesson: Lesson,
        tomorrow_at,  # noqa: ARG002
    ):
        response = client.post(
            "/api/v1/lessons",
            headers=admin_headers,
            json={
                "title": "Çakışan Ders",
                "lesson_type": "group",
                "start_at": tomorrow_at(17).isoformat(),
                "end_at": tomorrow_at(18).isoformat(),
                "pool_id": pool.id,
                "lane_id": lanes[0].id,
                "instructor_id": instructor.id,
            },
        )
        assert response.status_code == 409
        conflicts = response.json()["error"]["details"]["conflicts"]
        assert len(conflicts) > 0

    def test_force_creates_despite_conflict(
        self,
        client: TestClient,
        admin_headers: dict,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        lesson: Lesson,
        tomorrow_at,  # noqa: ARG002
    ):
        response = client.post(
            "/api/v1/lessons",
            headers=admin_headers,
            json={
                "title": "Zorlanan Ders",
                "lesson_type": "group",
                "start_at": tomorrow_at(17).isoformat(),
                "end_at": tomorrow_at(18).isoformat(),
                "pool_id": pool.id,
                "lane_id": lanes[0].id,
                "instructor_id": instructor.id,
                "force": True,
            },
        )
        assert response.status_code == 201

    def test_check_conflicts_endpoint(
        self,
        client: TestClient,
        admin_headers: dict,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        lesson: Lesson,
        tomorrow_at,  # noqa: ARG002
    ):
        response = client.post(
            "/api/v1/lessons/check-conflicts",
            headers=admin_headers,
            json={
                "start_at": tomorrow_at(17).isoformat(),
                "end_at": tomorrow_at(18).isoformat(),
                "pool_id": pool.id,
                "lane_id": lanes[0].id,
                "instructor_id": instructor.id,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["has_conflict"] is True
        assert len(body["conflicts"]) >= 2  # kulvar + eğitmen

    def test_end_before_start_rejected(
        self, client: TestClient, admin_headers: dict, pool: Pool, tomorrow_at
    ):
        response = client.post(
            "/api/v1/lessons",
            headers=admin_headers,
            json={
                "title": "Hatalı",
                "start_at": tomorrow_at(18).isoformat(),
                "end_at": tomorrow_at(17).isoformat(),
                "pool_id": pool.id,
            },
        )
        assert response.status_code == 422

    def test_capacity_enforced_on_enroll(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        student: Student,
        second_student: Student,
        tomorrow_at,
    ):
        lesson = _lesson(
            db, pool, lane_id=lanes[0].id, start=tomorrow_at(19), end=tomorrow_at(20)
        )
        lesson.capacity = 1
        db.commit()

        first = client.post(
            f"/api/v1/lessons/{lesson.id}/enroll",
            headers=admin_headers,
            json={"student_ids": [student.id]},
        )
        assert first.status_code == 200

        second = client.post(
            f"/api/v1/lessons/{lesson.id}/enroll",
            headers=admin_headers,
            json={"student_ids": [second_student.id]},
        )
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "lesson.capacity_full"

    def test_duplicate_enrollment_rejected(
        self, client: TestClient, admin_headers: dict, lesson: Lesson, student: Student
    ):
        client.post(
            f"/api/v1/lessons/{lesson.id}/enroll",
            headers=admin_headers,
            json={"student_ids": [student.id]},
        )
        response = client.post(
            f"/api/v1/lessons/{lesson.id}/enroll",
            headers=admin_headers,
            json={"student_ids": [student.id]},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "lesson.already_enrolled"

    def test_move_lesson_checks_conflicts(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
        lesson: Lesson,
        tomorrow_at,
    ):
        blocker = _lesson(
            db,
            pool,
            lane_id=lanes[1].id,
            instructor_id=instructor.id,
            start=tomorrow_at(19),
            end=tomorrow_at(20),
        )
        response = client.post(
            f"/api/v1/lessons/{lesson.id}/move",
            headers=admin_headers,
            json={
                "start_at": tomorrow_at(19).isoformat(),
                "end_at": tomorrow_at(20).isoformat(),
                "lane_id": blocker.lane_id,
            },
        )
        assert response.status_code == 409

    def test_calendar_returns_events(
        self, client: TestClient, admin_headers: dict, lesson: Lesson  # noqa: ARG002
    ):
        start = date.today()
        end = date.today() + timedelta(days=7)
        response = client.get(
            "/api/v1/lessons/calendar",
            headers=admin_headers,
            params={"start": start.isoformat(), "end": end.isoformat()},
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    def test_calendar_range_limit(self, client: TestClient, admin_headers: dict):
        response = client.get(
            "/api/v1/lessons/calendar",
            headers=admin_headers,
            params={"start": "2026-01-01", "end": "2027-01-01"},
        )
        assert response.status_code == 422

    def test_series_creation_generates_lessons(
        self,
        client: TestClient,
        admin_headers: dict,
        pool: Pool,
        lanes: list[Lane],
        instructor: Instructor,
    ):
        start = date.today() + timedelta(days=1)
        end = start + timedelta(days=13)
        response = client.post(
            "/api/v1/lessons/series",
            headers=admin_headers,
            json={
                "title": "Haftalık Grup",
                "lesson_type": "group",
                "pool_id": pool.id,
                "lane_id": lanes[2].id,
                "instructor_id": instructor.id,
                "weekdays": [start.weekday()],
                "start_time": "19:00:00",
                "end_time": "20:00:00",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "capacity": 10,
            },
        )
        assert response.status_code == 201
        assert response.json()["generated_lesson_count"] >= 2
