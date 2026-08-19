"""İstatistik motoru testleri / Statistics engine tests.

Saf matematiksel fonksiyonlar birim testlerle, toplu analizler veri fikstürleriyle
doğrulanır.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus, CourseType, LessonType, Stroke
from app.models.facility import Lane, Pool
from app.models.lesson import Lesson
from app.models.people import Instructor, Student
from app.models.performance import PerformanceRecord
from app.services.formatting import (
    format_currency,
    format_date,
    format_number,
    format_percent,
    format_swim_time,
    parse_swim_time,
)
from app.services.statistics_engine import (
    analyze_event,
    attendance_statistics,
    correlation_strength,
    detect_outliers,
    distribution_analysis,
    find_declining_athletes,
    find_top_improvers,
    linear_slope,
    mean,
    median,
    moving_average,
    pearson_correlation,
    percentile,
    pool_statistics,
    previous_period,
    resolve_period,
    std_dev,
    student_statistics,
    trend_direction,
)


# ===========================================================================
# Saf istatistik fonksiyonları
# ===========================================================================
class TestBasicStatistics:
    def test_mean(self):
        assert mean([1, 2, 3, 4, 5]) == 3.0
        assert mean([]) == 0.0

    def test_median_odd_and_even(self):
        assert median([1, 3, 2]) == 2.0
        assert median([1, 2, 3, 4]) == 2.5

    def test_std_dev(self):
        # Örneklem standart sapması (ddof=1)
        assert std_dev([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(2.138, abs=0.01)

    def test_std_dev_needs_two_points(self):
        assert std_dev([5]) is None
        assert std_dev([]) is None

    def test_percentile(self):
        values = list(range(1, 101))
        assert percentile(values, 50) == pytest.approx(50.5, abs=0.1)
        assert percentile(values, 25) == pytest.approx(25.75, abs=0.1)

    def test_moving_average_expanding_window(self):
        result = moving_average([10, 20, 30, 40], window=2)
        assert result[0] == 10.0  # ilk nokta kendisi
        assert result[1] == 15.0
        assert result[3] == 35.0

    def test_moving_average_empty(self):
        assert moving_average([]) == []

    def test_linear_slope_positive(self):
        assert linear_slope([0, 1, 2, 3], [0, 2, 4, 6]) == pytest.approx(2.0)

    def test_linear_slope_negative(self):
        assert linear_slope([0, 1, 2], [10, 8, 6]) == pytest.approx(-2.0)

    def test_linear_slope_insufficient_data(self):
        assert linear_slope([1], [5]) is None
        assert linear_slope([1, 1, 1], [1, 2, 3]) is None  # x'te varyans yok


class TestCorrelation:
    def test_perfect_positive_correlation(self):
        assert pearson_correlation([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)

    def test_perfect_negative_correlation(self):
        assert pearson_correlation([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)

    def test_no_correlation_with_constant(self):
        assert pearson_correlation([1, 2, 3, 4], [5, 5, 5, 5]) is None

    def test_insufficient_sample(self):
        assert pearson_correlation([1, 2], [3, 4]) is None

    @pytest.mark.parametrize(
        ("coefficient", "expected"),
        [
            (0.95, "very_strong"),
            (0.7, "strong"),
            (0.5, "moderate"),
            (0.3, "weak"),
            (0.1, "negligible"),
            (-0.85, "very_strong"),
        ],
    )
    def test_strength_labels(self, coefficient: float, expected: str):
        assert correlation_strength(coefficient) == expected


class TestOutliers:
    def test_detects_extreme_value(self):
        values = [10, 10, 11, 10, 10, 10, 50]
        outliers = detect_outliers(values, threshold=2.0)
        assert len(outliers) == 1
        assert outliers[0][1] == 50

    def test_no_outliers_in_uniform_data(self):
        assert detect_outliers([10, 10, 10, 10, 10]) == []

    def test_requires_minimum_sample(self):
        assert detect_outliers([1, 100]) == []


class TestTrendDirection:
    def test_lower_is_better_negative_slope_improving(self):
        """Yüzme derecelerinde düşen eğim gelişme demektir."""
        assert trend_direction(-0.5, lower_is_better=True) == "improving"

    def test_lower_is_better_positive_slope_declining(self):
        assert trend_direction(0.5, lower_is_better=True) == "declining"

    def test_higher_is_better(self):
        assert trend_direction(0.5, lower_is_better=False) == "improving"

    def test_flat_is_stable(self):
        assert trend_direction(0.0) == "stable"
        assert trend_direction(None) == "stable"


class TestDistributionAnalysis:
    def test_computes_summary(self):
        result = distribution_analysis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], "test", bins=5)
        assert result.count == 10
        assert result.mean == 5.5
        assert result.median == 5.5
        assert result.min_value == 1
        assert result.max_value == 10
        assert len(result.histogram) == 5
        assert sum(item.value for item in result.histogram) == 10

    def test_empty_input(self):
        result = distribution_analysis([], "test")
        assert result.count == 0
        assert result.histogram == []


# ===========================================================================
# Dönem çözümleme
# ===========================================================================
class TestPeriodResolution:
    def test_today(self):
        start, end = resolve_period("today")
        assert start == end == date.today()

    def test_month_starts_first_day(self):
        start, end = resolve_period("month")
        assert start.day == 1
        assert end == date.today()

    def test_year(self):
        start, _ = resolve_period("year")
        assert start.month == 1 and start.day == 1

    def test_custom(self):
        start, end = resolve_period("custom", date(2026, 1, 5), date(2026, 3, 10))
        assert start == date(2026, 1, 5)
        assert end == date(2026, 3, 10)

    def test_previous_period_same_length(self):
        start, end = date(2026, 8, 1), date(2026, 8, 31)
        prev_start, prev_end = previous_period(start, end)
        assert prev_end == date(2026, 7, 31)
        assert (end - start).days == (prev_end - prev_start).days


# ===========================================================================
# Yüzme derecesi biçimlendirme
# ===========================================================================
class TestSwimTimeFormatting:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (32.45, "32.45"),
            (95.12, "1:35.12"),
            (60.0, "1:00.00"),
            (125.5, "2:05.50"),
            (5.0, "5.00"),
        ],
    )
    def test_format(self, seconds: float, expected: str):
        assert format_swim_time(seconds) == expected

    def test_format_none(self):
        assert format_swim_time(None) == "-"

    @pytest.mark.parametrize(
        ("text", "expected"),
        [("32.45", 32.45), ("1:35.12", 95.12), ("1.35.12", 95.12), ("32,45", 32.45)],
    )
    def test_parse(self, text: str, expected: float):
        assert parse_swim_time(text) == pytest.approx(expected)

    def test_parse_invalid(self):
        assert parse_swim_time("abc") is None
        assert parse_swim_time("") is None

    def test_roundtrip(self):
        for seconds in (32.45, 95.12, 125.5):
            assert parse_swim_time(format_swim_time(seconds)) == pytest.approx(seconds)


class TestLocaleFormatting:
    def test_turkish_number(self):
        assert format_number(1250.5, "tr", 2) == "1.250,50"

    def test_english_number(self):
        assert format_number(1250.5, "en", 2) == "1,250.50"

    def test_turkish_currency(self):
        assert format_currency(1250.5, "TRY", "tr") == "1.250,50 ₺"

    def test_turkish_percent(self):
        assert format_percent(85.4, "tr") == "%85,4"

    def test_english_percent(self):
        assert format_percent(85.4, "en") == "85.4%"

    def test_turkish_date(self):
        assert format_date(date(2026, 8, 15), "tr") == "15.08.2026"

    def test_english_date(self):
        assert format_date(date(2026, 8, 15), "en") == "08/15/2026"


# ===========================================================================
# Performans analizi
# ===========================================================================
def _add_performance(
    db: Session,
    student: Student,
    times: list[float],
    *,
    stroke=Stroke.FREESTYLE,
    distance=50,
    start_days_ago=90,
) -> None:
    step = start_days_ago // max(1, len(times))
    for index, seconds in enumerate(times):
        db.add(
            PerformanceRecord(
                student_id=student.id,
                stroke=stroke,
                distance_m=distance,
                course_type=CourseType.SHORT,
                time_seconds=seconds,
                splits=[],
                recorded_date=date.today()
                - timedelta(days=start_days_ago - index * step),
            )
        )
    db.commit()


class TestEventAnalysis:
    def test_improving_athlete(self, db: Session, student: Student):
        _add_performance(db, student, [35.0, 34.5, 34.0, 33.5, 33.0])
        records = db.query(PerformanceRecord).all()
        analysis = analyze_event(records)

        assert analysis is not None
        assert analysis.record_count == 5
        assert analysis.best_time == 33.0
        assert analysis.first_time == 35.0
        assert analysis.last_time == 33.0
        assert analysis.improvement_seconds == 2.0
        assert analysis.improvement_percent == pytest.approx(5.71, abs=0.01)
        assert analysis.trend == "improving"

    def test_declining_athlete(self, db: Session, student: Student):
        _add_performance(db, student, [33.0, 33.5, 34.0, 34.5, 35.0])
        analysis = analyze_event(db.query(PerformanceRecord).all())
        assert analysis is not None
        assert analysis.trend == "declining"
        assert analysis.improvement_seconds == -2.0

    def test_moving_average_present(self, db: Session, student: Student):
        _add_performance(db, student, [35.0, 34.0, 33.0, 32.0])
        analysis = analyze_event(db.query(PerformanceRecord).all())
        assert analysis is not None
        assert all(point.moving_average is not None for point in analysis.points)

    def test_personal_best_marked_in_points(self, db: Session, student: Student):
        _add_performance(db, student, [35.0, 32.0, 34.0])
        analysis = analyze_event(db.query(PerformanceRecord).all())
        assert analysis is not None
        best_points = [point for point in analysis.points if point.is_personal_best]
        assert len(best_points) == 1
        assert best_points[0].time_seconds == 32.0

    def test_empty_returns_none(self):
        assert analyze_event([]) is None


class TestAthleteRankings:
    def test_finds_top_improver(
        self, db: Session, student: Student, second_student: Student
    ):
        _add_performance(db, student, [40.0, 38.0, 36.0, 34.0])  # %15 gelişim
        _add_performance(db, second_student, [40.0, 39.8, 39.6, 39.5])  # %1.25 gelişim

        improvers = find_top_improvers(db, lookback_days=120, min_records=3)
        assert len(improvers) == 2
        assert improvers[0].student_id == student.id
        assert improvers[0].improvement_percent > improvers[1].improvement_percent

    def test_finds_declining_athlete(self, db: Session, student: Student):
        # İlk 2/3 hızlı, son 1/3 belirgin yavaş
        _add_performance(db, student, [30.0, 30.1, 30.0, 30.2, 33.0, 33.5])
        declining = find_declining_athletes(db, lookback_days=120, min_records=4)
        assert len(declining) == 1
        assert declining[0].student_id == student.id
        assert declining[0].decline_percent > 1.0

    def test_stable_athlete_not_flagged(self, db: Session, student: Student):
        _add_performance(db, student, [30.0, 30.05, 30.0, 29.95, 30.0, 30.02])
        assert find_declining_athletes(db, lookback_days=120, min_records=4) == []

    def test_min_records_filter(self, db: Session, student: Student):
        _add_performance(db, student, [40.0, 35.0])
        assert find_top_improvers(db, lookback_days=120, min_records=5) == []


# ===========================================================================
# Toplu istatistikler
# ===========================================================================
class TestStudentStatistics:
    def test_counts_active_students(
        self, db: Session, student: Student, second_student: Student
    ):
        stats = student_statistics(db, date.today() - timedelta(days=365), date.today())
        assert stats.total_students == 2
        assert stats.active_students == 2

    def test_new_registrations_in_period(
        self, db: Session, student: Student, second_student: Student
    ):
        # student 120 gün önce, second_student 60 gün önce kaydolmuş
        stats = student_statistics(db, date.today() - timedelta(days=90), date.today())
        assert stats.new_registrations == 1

    def test_level_distribution_sums_to_total(
        self, db: Session, student: Student, second_student: Student
    ):
        stats = student_statistics(db, date.today() - timedelta(days=365), date.today())
        assert sum(item.value for item in stats.level_distribution) == 2

    def test_empty_database(self, db: Session):
        stats = student_statistics(db, date.today() - timedelta(days=30), date.today())
        assert stats.total_students == 0
        assert stats.retention_rate == 100.0


class TestAttendanceStatistics:
    def test_computes_rate(
        self,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        student: Student,
        second_student: Student,
    ):
        yesterday = datetime.combine(date.today() - timedelta(days=1), time(17, 0))
        lesson = Lesson(
            title="Geçmiş Ders",
            lesson_type=LessonType.GROUP,
            start_at=yesterday,
            end_at=yesterday + timedelta(hours=1),
            pool_id=pool.id,
            lane_id=lanes[0].id,
            capacity=8,
        )
        db.add(lesson)
        db.flush()
        db.add(
            Attendance(
                lesson_id=lesson.id,
                student_id=student.id,
                status=AttendanceStatus.PRESENT,
            )
        )
        db.add(
            Attendance(
                lesson_id=lesson.id,
                student_id=second_student.id,
                status=AttendanceStatus.ABSENT,
            )
        )
        db.commit()

        stats = attendance_statistics(
            db, date.today() - timedelta(days=7), date.today()
        )
        assert stats.present_count == 1
        assert stats.absent_count == 1
        assert stats.overall_rate == 50.0
        assert stats.no_show_rate == 50.0

    def test_empty_period(self, db: Session):
        stats = attendance_statistics(
            db, date.today() - timedelta(days=7), date.today()
        )
        assert stats.overall_rate == 0.0


class TestPoolStatistics:
    def test_computes_occupancy(
        self, db: Session, pool: Pool, lanes: list[Lane], instructor: Instructor
    ):
        today = date.today()
        db.add(
            Lesson(
                title="Bugünkü Ders",
                lesson_type=LessonType.GROUP,
                start_at=datetime.combine(today, time(17, 0)),
                end_at=datetime.combine(today, time(18, 0)),
                pool_id=pool.id,
                lane_id=lanes[0].id,
                instructor_id=instructor.id,
                capacity=8,
            )
        )
        db.commit()

        stats = pool_statistics(db, today, today)
        assert stats.overall_occupancy > 0
        assert stats.busiest_hour == "17:00"
        assert len(stats.heatmap) == 1
        assert stats.heatmap[0].hour == 17

    def test_empty_pool_zero_occupancy(self, db: Session, pool: Pool):  # noqa: ARG002
        stats = pool_statistics(db, date.today(), date.today())
        assert stats.overall_occupancy == 0.0
        assert stats.heatmap == []
