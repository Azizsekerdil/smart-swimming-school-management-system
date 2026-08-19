"""Yoklama uçları / Attendance endpoints."""

from __future__ import annotations

import secrets
from datetime import date, datetime, time, timedelta, timezone

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
    require_permissions,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.attendance import Attendance, AttendanceToken, StudentCard
from app.models.enums import (
    AttendanceMethod,
    AttendanceStatus,
    EnrollmentStatus,
    LessonStatus,
    MembershipStatus,
)
from app.models.lesson import Lesson, LessonEnrollment
from app.models.membership import Membership
from app.models.people import Student
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.operations import (
    AttendanceBulkCreate,
    AttendanceOut,
    AttendanceSheet,
    AttendanceSheetRow,
    AttendanceUpdate,
    QRCheckinRequest,
)
from app.services import audit
from app.services.crud import get_or_404, paginate

router = APIRouter(prefix="/attendance", tags=["Yoklama"])

PRESENT_STATUSES = (
    AttendanceStatus.PRESENT,
    AttendanceStatus.LATE,
    AttendanceStatus.MAKEUP,
)


def _decorate(attendance: Attendance) -> AttendanceOut:
    out = AttendanceOut.model_validate(attendance)
    if attendance.student:
        out.student_name = attendance.student.full_name
        out.student_number = attendance.student.student_number
    if attendance.lesson:
        out.lesson_title = attendance.lesson.title
        out.lesson_start = attendance.lesson.start_at
    return out


def _consume_credit(
    db: Session, student_id: int, enrollment: LessonEnrollment | None
) -> None:
    """Devam eden öğrenciden bir ders hakkı düşer (yalnızca bir kez)."""
    if enrollment and enrollment.credit_consumed:
        return
    membership = db.scalar(
        select(Membership)
        .where(
            Membership.student_id == student_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Membership.end_date.asc().nullslast())
        .limit(1)
    )
    if membership and membership.total_credits is not None:
        membership.used_credits = min(
            membership.total_credits, membership.used_credits + 1
        )
        if membership.remaining_credits == 0:
            membership.status = MembershipStatus.EXPIRED
    if enrollment:
        enrollment.credit_consumed = True
        if membership:
            enrollment.membership_id = membership.id


@router.get(
    "/sheet/{lesson_id}", response_model=AttendanceSheet, summary="Yoklama listesi"
)
def attendance_sheet(
    lesson_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.ATTENDANCE_READ)),
) -> AttendanceSheet:
    """Bir dersin yoklama ekranı verisi: kayıtlı öğrenciler + mevcut durum."""
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    # Nesne bazlı yetki + satır bazlı süzme.
    scope.assert_lesson_allowed(lesson_id)

    _enroll_stmt = (
        select(LessonEnrollment)
        .options(selectinload(LessonEnrollment.student))
        .where(
            LessonEnrollment.lesson_id == lesson_id,
            LessonEnrollment.status != EnrollmentStatus.CANCELLED,
        )
    )
    _enroll_stmt = scope.scope_students(_enroll_stmt, LessonEnrollment.student_id)
    enrollments = db.scalars(_enroll_stmt).all()

    existing = {
        a.student_id: a
        for a in db.scalars(
            select(Attendance).where(Attendance.lesson_id == lesson_id)
        ).all()
    }

    rows: list[AttendanceSheetRow] = []
    for enrollment in enrollments:
        student = enrollment.student
        attendance = existing.get(student.id)
        membership = db.scalar(
            select(Membership)
            .where(
                Membership.student_id == student.id,
                Membership.status == MembershipStatus.ACTIVE,
            )
            .limit(1)
        )
        rows.append(
            AttendanceSheetRow(
                student_id=student.id,
                student_number=student.student_number,
                full_name=student.full_name,
                photo_url=student.photo_url,
                enrollment_status=enrollment.status,
                attendance_id=attendance.id if attendance else None,
                status=attendance.status if attendance else None,
                late_minutes=attendance.late_minutes if attendance else None,
                notes=attendance.notes if attendance else None,
                membership_remaining=(
                    membership.remaining_credits if membership else None
                ),
            )
        )

    return AttendanceSheet(
        lesson_id=lesson.id,
        lesson_title=lesson.title,
        start_at=lesson.start_at,
        end_at=lesson.end_at,
        pool_name=lesson.pool.name if lesson.pool else None,
        lane_name=lesson.lane.display_name if lesson.lane else None,
        instructor_name=lesson.instructor.full_name if lesson.instructor else None,
        is_recorded=bool(existing),
        rows=sorted(rows, key=lambda r: r.full_name),
    )


@router.post(
    "", response_model=list[AttendanceOut], status_code=201, summary="Yoklama kaydet"
)
def record_attendance(
    payload: AttendanceBulkCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.ATTENDANCE_WRITE)),
) -> list[AttendanceOut]:
    """Bir dersin yoklamasını toplu kaydeder/günceller ve ders haklarını düşer."""
    lesson = get_or_404(db, Lesson, payload.lesson_id, "lesson.not_found")
    now = datetime.now(timezone.utc)
    results: list[AttendanceOut] = []

    for entry in payload.entries:
        student = get_or_404(db, Student, entry.student_id, "student.not_found")
        enrollment = db.scalar(
            select(LessonEnrollment).where(
                LessonEnrollment.lesson_id == lesson.id,
                LessonEnrollment.student_id == entry.student_id,
            )
        )

        attendance = db.scalar(
            select(Attendance).where(
                Attendance.lesson_id == lesson.id,
                Attendance.student_id == entry.student_id,
            )
        )
        is_new = attendance is None
        if attendance is None:
            attendance = Attendance(
                lesson_id=lesson.id,
                student_id=entry.student_id,
                recorded_by_user_id=current.id,
            )
            db.add(attendance)

        attendance.status = entry.status
        attendance.method = payload.method
        attendance.late_minutes = entry.late_minutes
        attendance.excuse_reason = entry.excuse_reason
        attendance.notes = entry.notes
        if entry.status in PRESENT_STATUSES:
            attendance.checked_in_at = attendance.checked_in_at or now

        if (
            payload.consume_credits
            and is_new
            and entry.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
        ):
            _consume_credit(db, entry.student_id, enrollment)

        db.flush()
        out = AttendanceOut.model_validate(attendance)
        out.student_name = student.full_name
        out.student_number = student.student_number
        out.lesson_title = lesson.title
        out.lesson_start = lesson.start_at
        results.append(out)

    if lesson.status == LessonStatus.SCHEDULED and lesson.end_at < datetime.now():
        lesson.status = LessonStatus.COMPLETED

    audit.record(
        db,
        action="record_attendance",
        entity_type="lesson",
        entity_id=lesson.id,
        user=current,
        summary=f"Yoklama alındı: {lesson.title} ({len(results)} öğrenci)",
        ip_address=client_ip(request),
    )
    db.commit()
    return results


@router.get("", response_model=Page[AttendanceOut], summary="Yoklama kayıtları")
def list_attendance(
    student_id: int | None = None,
    lesson_id: int | None = None,
    instructor_id: int | None = None,
    status: AttendanceStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.ATTENDANCE_READ)),
) -> Page[AttendanceOut]:
    stmt = (
        select(Attendance)
        .options(selectinload(Attendance.student), selectinload(Attendance.lesson))
        .join(Lesson, Lesson.id == Attendance.lesson_id)
    )
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        stmt = stmt.where(Attendance.student_id.in_(allowed))
    if student_id:
        stmt = stmt.where(Attendance.student_id == student_id)
    if lesson_id:
        stmt = stmt.where(Attendance.lesson_id == lesson_id)
    if instructor_id:
        stmt = stmt.where(Lesson.instructor_id == instructor_id)
    if status:
        stmt = stmt.where(Attendance.status == status)
    if date_from:
        stmt = stmt.where(Lesson.start_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Lesson.start_at <= datetime.combine(date_to, time.max))

    stmt = stmt.order_by(Lesson.start_at.desc())
    rows, total = paginate(db, stmt, params)
    return Page[AttendanceOut](
        items=[_decorate(a) for a in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.patch(
    "/{attendance_id}", response_model=AttendanceOut, summary="Yoklama düzelt"
)
def update_attendance(
    attendance_id: int,
    payload: AttendanceUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.ATTENDANCE_WRITE)),
) -> AttendanceOut:
    attendance = get_or_404(db, Attendance, attendance_id)
    changes: dict = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        old = getattr(attendance, key, None)
        if old != value:
            changes[key] = {"from": old, "to": value}
            setattr(attendance, key, value)
    audit.record(
        db,
        action="update",
        entity_type="attendance",
        entity_id=attendance_id,
        user=current,
        summary="Yoklama düzeltildi",
        changes=changes,
    )
    db.commit()
    db.refresh(attendance)
    return _decorate(attendance)


@router.get("/student/{student_id}/summary", summary="Öğrenci devam özeti")
def student_attendance_summary(
    student_id: int,
    days: int = 90,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.ATTENDANCE_READ)),
) -> dict:
    allowed = scope.allowed_student_ids()
    if allowed is not None and student_id not in allowed:
        from app.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError()
    get_or_404(db, Student, student_id, "student.not_found")

    since = datetime.combine(date.today() - timedelta(days=days), time.min)
    rows = db.execute(
        select(Attendance.status, func.count(Attendance.id))
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Attendance.student_id == student_id, Lesson.start_at >= since)
        .group_by(Attendance.status)
    ).all()

    counts = dict(rows)
    total = sum(counts.values())
    present = sum(counts.get(s.value, 0) for s in PRESENT_STATUSES)
    return {
        "student_id": student_id,
        "period_days": days,
        "total": total,
        "by_status": counts,
        "attendance_rate": round(present / total * 100, 1) if total else None,
        "absent_count": counts.get(AttendanceStatus.ABSENT.value, 0),
        "late_count": counts.get(AttendanceStatus.LATE.value, 0),
        "excused_count": counts.get(AttendanceStatus.EXCUSED.value, 0),
    }


# ---------------------------------------------------------------------------
# QR / kart ile yoklama
# ---------------------------------------------------------------------------
@router.post("/qr/generate/{lesson_id}", summary="Ders için QR token üret")
def generate_qr_token(
    lesson_id: int,
    valid_minutes: int = 90,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.ATTENDANCE_WRITE)),
) -> dict:
    """Ders girişinde okutulacak QR kodunun içeriğini üretir."""
    lesson = get_or_404(db, Lesson, lesson_id, "lesson.not_found")
    now = datetime.now(timezone.utc)
    token = AttendanceToken(
        token=secrets.token_urlsafe(24),
        lesson_id=lesson_id,
        expires_at=now + timedelta(minutes=valid_minutes),
        created_at=now,
    )
    db.add(token)
    db.commit()
    return {
        "token": token.token,
        "lesson_id": lesson_id,
        "lesson_title": lesson.title,
        "expires_at": token.expires_at.isoformat(),
        "qr_payload": f"SWS:ATT:{token.token}",
    }


@router.post("/qr/checkin", response_model=AttendanceOut, summary="QR/kart ile giriş")
def qr_checkin(
    payload: QRCheckinRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.ATTENDANCE_WRITE)),
) -> AttendanceOut:
    """Öğrenci kartı/QR ile hızlı yoklama girişi."""
    token = db.scalar(
        select(AttendanceToken).where(AttendanceToken.token == payload.token)
    )
    if token is None:
        raise NotFoundError(details={"field": "token"})
    if token.expires_at.replace(tzinfo=None) < datetime.now():
        raise ValidationError(details={"reason": "token_expired"})

    card = db.scalar(
        select(StudentCard).where(
            StudentCard.card_code == payload.card_code, StudentCard.is_active.is_(True)
        )
    )
    if card is None:
        raise NotFoundError(details={"field": "card_code"})

    lesson = get_or_404(db, Lesson, token.lesson_id, "lesson.not_found")
    student = get_or_404(db, Student, card.student_id, "student.not_found")

    existing = db.scalar(
        select(Attendance).where(
            Attendance.lesson_id == lesson.id, Attendance.student_id == student.id
        )
    )
    if existing:
        raise ConflictError("attendance.already_recorded")

    now = datetime.now(timezone.utc)
    late_minutes = max(
        0, int((now.replace(tzinfo=None) - lesson.start_at).total_seconds() // 60)
    )
    attendance = Attendance(
        lesson_id=lesson.id,
        student_id=student.id,
        status=AttendanceStatus.LATE if late_minutes > 10 else AttendanceStatus.PRESENT,
        method=AttendanceMethod.QR if card.card_type == "qr" else AttendanceMethod.CARD,
        checked_in_at=now,
        late_minutes=late_minutes if late_minutes > 10 else None,
        recorded_by_user_id=current.id,
    )
    db.add(attendance)
    token.used_count += 1

    enrollment = db.scalar(
        select(LessonEnrollment).where(
            LessonEnrollment.lesson_id == lesson.id,
            LessonEnrollment.student_id == student.id,
        )
    )
    _consume_credit(db, student.id, enrollment)
    db.commit()
    db.refresh(attendance)
    return _decorate(attendance)


@router.post("/cards/{student_id}", summary="Öğrenci kartı oluştur")
def create_student_card(
    student_id: int,
    card_type: str = "qr",
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
) -> dict:
    student = get_or_404(db, Student, student_id, "student.not_found")
    for old in db.scalars(
        select(StudentCard).where(StudentCard.student_id == student_id)
    ).all():
        old.is_active = False

    card = StudentCard(
        student_id=student_id,
        card_code=f"SWS{student.student_number}{secrets.token_hex(4).upper()}",
        card_type=card_type,
        issued_at=datetime.now(timezone.utc),
    )
    db.add(card)
    db.commit()
    return {
        "student_id": student_id,
        "student_name": student.full_name,
        "card_code": card.card_code,
        "card_type": card.card_type,
        "qr_payload": f"SWS:CARD:{card.card_code}",
    }


@router.post(
    "/{attendance_id}/makeup", response_model=Message, summary="Telafi dersi ata"
)
def assign_makeup(
    attendance_id: int,
    makeup_lesson_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.ATTENDANCE_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    attendance = get_or_404(db, Attendance, attendance_id)
    makeup = get_or_404(db, Lesson, makeup_lesson_id, "lesson.not_found")

    if attendance.status not in (AttendanceStatus.EXCUSED, AttendanceStatus.ABSENT):
        raise ValidationError(
            details={"reason": "only_absent_or_excused_can_have_makeup"}
        )

    attendance.makeup_lesson_id = makeup_lesson_id

    already = db.scalar(
        select(LessonEnrollment).where(
            LessonEnrollment.lesson_id == makeup_lesson_id,
            LessonEnrollment.student_id == attendance.student_id,
        )
    )
    if not already:
        db.add(
            LessonEnrollment(
                lesson_id=makeup_lesson_id,
                student_id=attendance.student_id,
                notes="Telafi dersi",
            )
        )

    audit.record(
        db,
        action="assign_makeup",
        entity_type="attendance",
        entity_id=attendance_id,
        user=current,
        summary=f"Telafi dersi atandı: {makeup.title}",
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))
