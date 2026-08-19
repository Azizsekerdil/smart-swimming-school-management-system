"""Ders, seri, kayıt, çakışma ve takvim uçları / Lessons, series, calendar."""

from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import (
    AccessScope,
    client_ip,
    db_session,
    get_language,
    get_scope,
    pagination,
    require_org_wide_scope,
    require_permissions,
)
from app.core.exceptions import ConflictError, SchedulingConflictError, ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.enums import EnrollmentStatus, LessonStatus, MembershipStatus
from app.models.facility import Lane, Pool
from app.models.lesson import Lesson, LessonEnrollment, LessonSeries
from app.models.membership import Membership
from app.models.people import Instructor, Student
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.lesson import (
    CalendarEvent,
    CalendarResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
    EnrollmentOut,
    EnrollRequest,
    LessonCreate,
    LessonDetail,
    LessonMoveRequest,
    LessonOut,
    LessonSeriesCreate,
    LessonSeriesOut,
    LessonUpdate,
)
from app.services import audit
from app.services.crud import apply_sort, get_or_404, paginate
from app.services.scheduling import (
    ConflictChecker,
    build_lessons_from_series,
    generate_series_dates,
)

router = APIRouter(prefix="/lessons", tags=["Dersler"])


def _decorate(lesson: Lesson) -> LessonOut:
    out = LessonOut.model_validate(lesson)
    out.duration_minutes = lesson.duration_minutes
    out.enrolled_count = lesson.enrolled_count
    out.occupancy_rate = lesson.occupancy_rate
    out.pool_name = lesson.pool.name if lesson.pool else None
    out.lane_name = lesson.lane.display_name if lesson.lane else None
    out.instructor_name = lesson.instructor.full_name if lesson.instructor else None
    out.group_name = lesson.group.name if lesson.group else None
    return out


def _raise_conflicts(errors: list, warnings: list) -> None:
    raise SchedulingConflictError(
        message_key=errors[0].message_key,
        details={
            "conflicts": [e.model_dump(mode="json") for e in errors],
            "warnings": [w.model_dump(mode="json") for w in warnings],
        },
    )


def _scope_filter(scope: AccessScope, stmt):  # noqa: ANN001, ANN202
    """Eğitmen kendi derslerini, öğrenci/veli kendi kayıtlı derslerini görür."""
    if scope.is_instructor_scoped and scope.instructor_id:
        return stmt.where(Lesson.instructor_id == scope.instructor_id)
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        return stmt.where(
            Lesson.id.in_(
                select(LessonEnrollment.lesson_id).where(
                    LessonEnrollment.student_id.in_(allowed)
                )
            )
        )
    return stmt


@router.get("", response_model=Page[LessonOut], summary="Dersleri listele")
def list_lessons(
    date_from: date | None = None,
    date_to: date | None = None,
    pool_id: int | None = None,
    lane_id: int | None = None,
    instructor_id: int | None = None,
    group_id: int | None = None,
    lesson_type: str | None = None,
    status: LessonStatus | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
) -> Page[LessonOut]:
    stmt = select(Lesson).options(
        selectinload(Lesson.pool),
        selectinload(Lesson.lane),
        selectinload(Lesson.instructor),
        selectinload(Lesson.group),
        selectinload(Lesson.enrollments),
    )
    stmt = _scope_filter(scope, stmt)
    if date_from:
        stmt = stmt.where(Lesson.start_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Lesson.start_at <= datetime.combine(date_to, time.max))
    if pool_id:
        stmt = stmt.where(Lesson.pool_id == pool_id)
    if lane_id:
        stmt = stmt.where(Lesson.lane_id == lane_id)
    if instructor_id:
        stmt = stmt.where(Lesson.instructor_id == instructor_id)
    if group_id:
        stmt = stmt.where(Lesson.group_id == group_id)
    if lesson_type:
        stmt = stmt.where(Lesson.lesson_type == lesson_type)
    if status:
        stmt = stmt.where(Lesson.status == status)

    stmt = apply_sort(stmt, Lesson, params, "start_at")
    rows, total = paginate(db, stmt, params)
    return Page[LessonOut](
        items=[_decorate(lesson) for lesson in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=LessonDetail, status_code=201, summary="Ders oluştur")
def create_lesson(
    payload: LessonCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_WRITE)),
    lang: str = Depends(get_language),
) -> LessonDetail:
    get_or_404(db, Pool, payload.pool_id, "pool.not_found")
    if payload.lane_id:
        get_or_404(db, Lane, payload.lane_id, "lane.not_found")
    if payload.instructor_id:
        get_or_404(db, Instructor, payload.instructor_id, "instructor.not_found")

    checker = ConflictChecker(db, lang)
    errors, warnings = checker.check(
        start_at=payload.start_at,
        end_at=payload.end_at,
        pool_id=payload.pool_id,
        lane_id=payload.lane_id,
        instructor_id=payload.instructor_id,
        student_ids=payload.student_ids,
    )
    if errors and not payload.force:
        _raise_conflicts(errors, warnings)

    lesson = Lesson(**payload.model_dump(exclude={"student_ids", "force"}))
    db.add(lesson)
    db.flush()

    for student_id in payload.student_ids:
        if db.get(Student, student_id):
            db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student_id))

    audit.record(
        db,
        action="create",
        entity_type="lesson",
        entity_id=lesson.id,
        user=current,
        summary=f"Ders oluşturuldu: {lesson.title} @ {lesson.start_at:%d.%m.%Y %H:%M}",
        changes={"forced": payload.force, "conflict_count": len(errors)},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(lesson)
    detail = LessonDetail(**_decorate(lesson).model_dump())
    detail.enrollments = [_enrollment_out(e) for e in lesson.enrollments]
    return detail


def _enrollment_out(enrollment: LessonEnrollment) -> EnrollmentOut:
    out = EnrollmentOut.model_validate(enrollment)
    if enrollment.student:
        out.student_name = enrollment.student.full_name
        out.student_number = enrollment.student.student_number
    return out


@router.post(
    "/check-conflicts", response_model=ConflictCheckResponse, summary="Çakışma denetimi"
)
def check_conflicts(
    payload: ConflictCheckRequest,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
    lang: str = Depends(get_language),
) -> ConflictCheckResponse:
    """Ders kaydetmeden önce çakışmaları önizler."""
    checker = ConflictChecker(db, lang)
    errors, warnings = checker.check(
        start_at=payload.start_at,
        end_at=payload.end_at,
        pool_id=payload.pool_id,
        lane_id=payload.lane_id,
        instructor_id=payload.instructor_id,
        student_ids=payload.student_ids,
        exclude_lesson_id=payload.exclude_lesson_id,
    )
    return ConflictCheckResponse(
        has_conflict=bool(errors), conflicts=errors, warnings=warnings
    )


@router.get("/calendar", response_model=CalendarResponse, summary="Takvim görünümü")
def calendar(
    start: date,
    end: date,
    pool_id: int | None = None,
    instructor_id: int | None = None,
    group_id: int | None = None,
    lesson_type: str | None = None,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
) -> CalendarResponse:
    if (end - start).days > 120:
        raise ValidationError(details={"reason": "range_too_large", "max_days": 120})

    stmt = (
        select(Lesson)
        .options(
            selectinload(Lesson.pool),
            selectinload(Lesson.lane),
            selectinload(Lesson.instructor),
            selectinload(Lesson.group),
            selectinload(Lesson.enrollments),
        )
        .where(
            Lesson.start_at >= datetime.combine(start, time.min),
            Lesson.start_at <= datetime.combine(end, time.max),
        )
    )
    stmt = _scope_filter(scope, stmt)
    if pool_id:
        stmt = stmt.where(Lesson.pool_id == pool_id)
    if instructor_id:
        stmt = stmt.where(Lesson.instructor_id == instructor_id)
    if group_id:
        stmt = stmt.where(Lesson.group_id == group_id)
    if lesson_type:
        stmt = stmt.where(Lesson.lesson_type == lesson_type)

    lessons = db.scalars(stmt.order_by(Lesson.start_at)).unique().all()
    events = [
        CalendarEvent(
            id=lesson.id,
            title=lesson.title,
            start=lesson.start_at,
            end=lesson.end_at,
            lesson_type=lesson.lesson_type,
            status=lesson.status,
            color=lesson.color,
            pool_id=lesson.pool_id,
            pool_name=lesson.pool.name if lesson.pool else "",
            lane_id=lesson.lane_id,
            lane_name=lesson.lane.display_name if lesson.lane else None,
            instructor_id=lesson.instructor_id,
            instructor_name=lesson.instructor.full_name if lesson.instructor else None,
            group_name=lesson.group.name if lesson.group else None,
            enrolled_count=lesson.enrolled_count,
            capacity=lesson.capacity,
        )
        for lesson in lessons
    ]
    return CalendarResponse(start=start, end=end, events=events, total=len(events))


# ---------------------------------------------------------------------------
# Seriler
# ---------------------------------------------------------------------------
@router.post(
    "/series",
    response_model=LessonSeriesOut,
    status_code=201,
    summary="Tekrarlanan ders",
)
def create_series(
    payload: LessonSeriesCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_SCHEDULE)),
    lang: str = Depends(get_language),
) -> LessonSeriesOut:
    """Haftalık tekrarlanan ders serisi oluşturur ve ders örneklerini üretir."""
    get_or_404(db, Pool, payload.pool_id, "pool.not_found")

    series = LessonSeries(
        **payload.model_dump(exclude={"student_ids", "skip_holidays", "force"})
    )
    db.add(series)
    db.flush()

    dates = generate_series_dates(
        payload.start_date,
        payload.end_date,
        payload.weekdays,
        payload.skip_holidays,
        db,
    )
    if not dates:
        raise ValidationError(details={"reason": "no_dates_generated"})

    lessons = build_lessons_from_series(series, dates)
    checker = ConflictChecker(db, lang)
    conflicted: list[dict] = []
    created = 0

    for lesson in lessons:
        errors, _ = checker.check(
            start_at=lesson.start_at,
            end_at=lesson.end_at,
            pool_id=lesson.pool_id,
            lane_id=lesson.lane_id,
            instructor_id=lesson.instructor_id,
            student_ids=payload.student_ids,
        )
        if errors and not payload.force:
            conflicted.append(
                {
                    "date": lesson.start_at.date().isoformat(),
                    "conflicts": [e.message for e in errors],
                }
            )
            continue
        db.add(lesson)
        db.flush()
        for student_id in payload.student_ids:
            if db.get(Student, student_id):
                db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student_id))
        created += 1

    audit.record(
        db,
        action="create",
        entity_type="lesson_series",
        entity_id=series.id,
        user=current,
        summary=(
            f"Ders serisi: {series.title} · {created}/{len(dates)} ders oluşturuldu, "
            f"{len(conflicted)} çakışma atlandı"
        ),
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(series)

    out = LessonSeriesOut.model_validate(series)
    out.generated_lesson_count = created
    if conflicted:
        # Çakışan tarihler kullanıcıya bildirim olarak iletilir
        from app.services.notifications import create as notify

        notify(
            db,
            notification_type="system",
            severity="warning",
            title_tr=f"{len(conflicted)} ders çakışma nedeniyle oluşturulmadı",
            title_en=f"{len(conflicted)} lessons skipped due to conflicts",
            body_tr="; ".join(c["date"] for c in conflicted[:10]),
            user_id=current.id,
            entity_type="lesson_series",
            entity_id=series.id,
        )
        db.commit()
    return out


@router.get("/series", response_model=list[LessonSeriesOut], summary="Serileri listele")
def list_series(
    is_active: bool | None = None,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
) -> list[LessonSeriesOut]:
    stmt = select(LessonSeries).options(selectinload(LessonSeries.lessons))
    if is_active is not None:
        stmt = stmt.where(LessonSeries.is_active.is_(is_active))
    result = []
    for series in (
        db.scalars(stmt.order_by(LessonSeries.start_date.desc())).unique().all()
    ):
        out = LessonSeriesOut.model_validate(series)
        out.generated_lesson_count = len(series.lessons)
        result.append(out)
    return result


@router.delete("/series/{series_id}", response_model=Message, summary="Seriyi sil")
def delete_series(
    series_id: int,
    future_only: bool = True,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    """`future_only=true` yalnızca gelecekteki dersleri siler, geçmiş kayıtları korur."""
    series = get_or_404(db, LessonSeries, series_id)
    now = datetime.now()
    removed = 0
    for lesson in list(series.lessons):
        if future_only and lesson.start_at < now:
            continue
        db.delete(lesson)
        removed += 1
    if not future_only:
        db.delete(series)
    else:
        series.is_active = False

    audit.record(
        db,
        action="delete",
        entity_type="lesson_series",
        entity_id=series_id,
        user=current,
        summary=f"Seri silindi: {removed} ders kaldırıldı (future_only={future_only})",
    )
    db.commit()
    return Message(
        code="common.deleted",
        message=t("common.deleted", lang),
        data={"removed": removed},
    )


# ---------------------------------------------------------------------------
# Tekil ders işlemleri
# ---------------------------------------------------------------------------
@router.get("/{lesson_id}", response_model=LessonDetail, summary="Ders detayı")
def get_lesson(
    lesson_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
) -> LessonDetail:
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    # Nesne bazlı yetki: self-scoped rol yalnızca kayıtlı olduğu dersi görür.
    scope.assert_lesson_allowed(lesson_id)
    _allowed = scope.allowed_student_ids()
    _enrollments = lesson.enrollments
    if _allowed is not None:
        _allowed_set = set(_allowed)
        _enrollments = [e for e in _enrollments if e.student_id in _allowed_set]
    detail = LessonDetail(**_decorate(lesson).model_dump())
    detail.enrollments = [_enrollment_out(e) for e in _enrollments]
    detail.attendance_recorded = bool(lesson.attendances)
    return detail


@router.patch("/{lesson_id}", response_model=LessonDetail, summary="Ders güncelle")
def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_WRITE)),
    lang: str = Depends(get_language),
) -> LessonDetail:
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    data = payload.model_dump(exclude_unset=True, exclude={"force"})

    new_start = data.get("start_at", lesson.start_at)
    new_end = data.get("end_at", lesson.end_at)
    if new_end <= new_start:
        raise ValidationError("lesson.invalid_time_range")

    time_or_resource_changed = any(
        k in data for k in ("start_at", "end_at", "lane_id", "instructor_id", "pool_id")
    )
    if time_or_resource_changed:
        checker = ConflictChecker(db, lang)
        errors, warnings = checker.check(
            start_at=new_start,
            end_at=new_end,
            pool_id=data.get("pool_id", lesson.pool_id),
            lane_id=data.get("lane_id", lesson.lane_id),
            instructor_id=data.get("instructor_id", lesson.instructor_id),
            student_ids=[e.student_id for e in lesson.enrollments],
            exclude_lesson_id=lesson.id,
        )
        if errors and not payload.force:
            _raise_conflicts(errors, warnings)

    changes: dict = {}
    for key, value in data.items():
        old = getattr(lesson, key, None)
        if old != value:
            changes[key] = {"from": str(old), "to": str(value)}
            setattr(lesson, key, value)

    audit.record(
        db,
        action="update",
        entity_type="lesson",
        entity_id=lesson.id,
        user=current,
        summary=f"Ders güncellendi: {lesson.title}",
        changes=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(lesson)
    detail = LessonDetail(**_decorate(lesson).model_dump())
    detail.enrollments = [_enrollment_out(e) for e in lesson.enrollments]
    return detail


@router.post(
    "/{lesson_id}/move",
    response_model=LessonDetail,
    summary="Dersi taşı (sürükle-bırak)",
)
def move_lesson(
    lesson_id: int,
    payload: LessonMoveRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_SCHEDULE)),
    lang: str = Depends(get_language),
) -> LessonDetail:
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    checker = ConflictChecker(db, lang)
    errors, warnings = checker.check(
        start_at=payload.start_at,
        end_at=payload.end_at,
        pool_id=lesson.pool_id,
        lane_id=payload.lane_id if payload.lane_id is not None else lesson.lane_id,
        instructor_id=(
            payload.instructor_id
            if payload.instructor_id is not None
            else lesson.instructor_id
        ),
        student_ids=[e.student_id for e in lesson.enrollments],
        exclude_lesson_id=lesson.id,
    )
    if errors and not payload.force:
        _raise_conflicts(errors, warnings)

    old_start = lesson.start_at
    lesson.start_at = payload.start_at
    lesson.end_at = payload.end_at
    if payload.lane_id is not None:
        lesson.lane_id = payload.lane_id
    if payload.instructor_id is not None:
        lesson.instructor_id = payload.instructor_id

    audit.record(
        db,
        action="move",
        entity_type="lesson",
        entity_id=lesson.id,
        user=current,
        summary=f"Ders taşındı: {old_start:%d.%m %H:%M} -> {lesson.start_at:%d.%m %H:%M}",
    )
    db.commit()
    db.refresh(lesson)
    detail = LessonDetail(**_decorate(lesson).model_dump())
    detail.enrollments = [_enrollment_out(e) for e in lesson.enrollments]
    return detail


@router.post("/{lesson_id}/cancel", response_model=Message, summary="Dersi iptal et")
def cancel_lesson(
    lesson_id: int,
    reason: str,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    lesson.status = LessonStatus.CANCELLED
    lesson.cancellation_reason = reason

    from app.services.notifications import broadcast

    broadcast(
        db,
        notification_type="lesson_cancelled",
        severity="warning",
        title_tr=f"Ders iptal edildi: {lesson.title}",
        title_en=f"Lesson cancelled: {lesson.title}",
        body_tr=f"{lesson.start_at:%d.%m.%Y %H:%M} · {reason}",
        body_en=f"{lesson.start_at:%Y-%m-%d %H:%M} · {reason}",
        role_codes=["reception", "operations_manager"],
        entity_type="lesson",
        entity_id=lesson.id,
    )
    audit.record(
        db,
        action="cancel",
        entity_type="lesson",
        entity_id=lesson.id,
        user=current,
        summary=f"Ders iptal edildi: {lesson.title} · {reason}",
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.delete("/{lesson_id}", response_model=Message, summary="Dersi sil")
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    title = lesson.title
    db.delete(lesson)
    audit.record(
        db,
        action="delete",
        entity_type="lesson",
        entity_id=lesson_id,
        user=current,
        summary=f"Ders silindi: {title}",
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Kayıt (enrollment)
# ---------------------------------------------------------------------------
@router.post(
    "/{lesson_id}/enroll", response_model=list[EnrollmentOut], summary="Öğrenci kaydet"
)
def enroll_students(
    lesson_id: int,
    payload: EnrollRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_WRITE)),
    lang: str = Depends(get_language),
) -> list[EnrollmentOut]:
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    checker = ConflictChecker(db, lang)
    created: list[EnrollmentOut] = []

    # Kontenjan sayımı yüklenmiş ilişkiye değil doğrudan sorguya dayanır; böylece
    # tek çağrıda birden fazla öğrenci eklenirken de doğru sınır uygulanır.
    enrolled_count = (
        db.scalar(
            select(func.count(LessonEnrollment.id)).where(
                LessonEnrollment.lesson_id == lesson_id,
                LessonEnrollment.status == EnrollmentStatus.ENROLLED,
            )
        )
        or 0
    )

    for student_id in payload.student_ids:
        student = get_or_404(db, Student, student_id, "student.not_found")

        if db.scalar(
            select(LessonEnrollment).where(
                LessonEnrollment.lesson_id == lesson_id,
                LessonEnrollment.student_id == student_id,
            )
        ):
            raise ConflictError(
                "lesson.already_enrolled", details={"student_id": student_id}
            )

        if enrolled_count >= lesson.capacity and not payload.force:
            raise ConflictError(
                "lesson.capacity_full",
                details={"capacity": lesson.capacity, "enrolled": enrolled_count},
            )

        errors, _ = checker.check(
            start_at=lesson.start_at,
            end_at=lesson.end_at,
            pool_id=lesson.pool_id,
            student_ids=[student_id],
            exclude_lesson_id=lesson.id,
        )
        student_conflicts = [e for e in errors if e.kind == "student"]
        if student_conflicts and not payload.force:
            raise SchedulingConflictError(
                message_key="lesson.conflict_student",
                details={
                    "conflicts": [e.model_dump(mode="json") for e in student_conflicts]
                },
            )

        membership_id = None
        if payload.use_membership:
            membership = db.scalar(
                select(Membership)
                .where(
                    Membership.student_id == student_id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
                .order_by(Membership.end_date.asc().nullslast())
                .limit(1)
            )
            if membership:
                membership_id = membership.id

        enrollment = LessonEnrollment(
            lesson_id=lesson_id, student_id=student_id, membership_id=membership_id
        )
        db.add(enrollment)
        db.flush()
        enrolled_count += 1
        out = EnrollmentOut.model_validate(enrollment)
        out.student_name = student.full_name
        out.student_number = student.student_number
        created.append(out)

    audit.record(
        db,
        action="enroll",
        entity_type="lesson",
        entity_id=lesson_id,
        user=current,
        summary=f"{len(created)} öğrenci derse kaydedildi: {lesson.title}",
    )
    db.commit()
    return created


@router.delete(
    "/{lesson_id}/enroll/{student_id}",
    response_model=Message,
    summary="Ders kaydını kaldır",
)
def unenroll_student(
    lesson_id: int,
    student_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.LESSON_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    enrollment = db.scalar(
        select(LessonEnrollment).where(
            LessonEnrollment.lesson_id == lesson_id,
            LessonEnrollment.student_id == student_id,
        )
    )
    if enrollment:
        # Kredi tüketilmişse iade et
        if enrollment.credit_consumed and enrollment.membership_id:
            membership = db.get(Membership, enrollment.membership_id)
            if membership and membership.used_credits > 0:
                membership.used_credits -= 1
        db.delete(enrollment)
        audit.record(
            db,
            action="unenroll",
            entity_type="lesson",
            entity_id=lesson_id,
            user=current,
            summary=f"Öğrenci #{student_id} ders kaydından çıkarıldı",
        )
        db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


@router.get(
    "/{lesson_id}/roster", response_model=list[EnrollmentOut], summary="Ders listesi"
)
def lesson_roster(
    lesson_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
) -> list[EnrollmentOut]:
    get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    # Nesne bazlı yetki + satır bazlı süzme: veli sınıftaki diğer çocukları görmez.
    scope.assert_lesson_allowed(lesson_id)
    stmt = (
        select(LessonEnrollment)
        .options(selectinload(LessonEnrollment.student))
        .where(LessonEnrollment.lesson_id == lesson_id)
    )
    stmt = scope.scope_students(stmt, LessonEnrollment.student_id)
    rows = db.scalars(stmt).all()
    return [_enrollment_out(e) for e in rows]


@router.get("/today/list", response_model=list[LessonOut], summary="Bugünün dersleri")
def todays_lessons(
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.LESSON_READ)),
) -> list[LessonOut]:
    today = date.today()
    stmt = (
        select(Lesson)
        .options(
            selectinload(Lesson.pool),
            selectinload(Lesson.lane),
            selectinload(Lesson.instructor),
            selectinload(Lesson.enrollments),
        )
        .where(
            Lesson.start_at >= datetime.combine(today, time.min),
            Lesson.start_at <= datetime.combine(today, time.max),
        )
    )
    stmt = _scope_filter(scope, stmt)
    lessons = db.scalars(stmt.order_by(Lesson.start_at)).unique().all()
    return [_decorate(lesson) for lesson in lessons]
