"""Öğrenci yönetimi uçları / Student management endpoints."""

from __future__ import annotations

from datetime import date, timedelta

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
from app.core.exceptions import ConflictError, PermissionDeniedError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus, MembershipStatus, StudentStatus
from app.models.finance import Invoice, Payment
from app.models.lesson import Lesson, LessonEnrollment
from app.models.membership import Membership
from app.models.people import Group, Guardian, Student, StudentGuardian
from app.models.performance import PersonalBest
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.people import (
    StudentCreate,
    StudentDetail,
    StudentOut,
    StudentUpdate,
)
from app.services import audit
from app.services.crud import (
    apply_search,
    apply_sort,
    get_or_404,
    next_sequence_number,
    paginate,
)

router = APIRouter(prefix="/students", tags=["Öğrenciler"])

SENSITIVE_FIELDS = ("health_notes", "special_needs")


def _to_out(student: Student, scope: AccessScope) -> StudentOut:
    """ORM -> şema. Hassas alanlar yetkisiz kullanıcıdan gizlenir."""
    data = StudentOut.model_validate(student)
    if not scope.can_read_sensitive():
        for field in SENSITIVE_FIELDS:
            setattr(data, field, None)
    return data


def _scoped_query(scope: AccessScope, stmt):  # noqa: ANN001, ANN202
    """Satır bazlı erişim kısıtını uygular."""
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        stmt = stmt.where(Student.id.in_(allowed))
    return stmt


@router.get("", response_model=Page[StudentOut], summary="Öğrencileri listele")
def list_students(
    q: str | None = None,
    status: StudentStatus | None = None,
    swim_level: str | None = None,
    group_id: int | None = None,
    instructor_id: int | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    include_demo: bool = True,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.STUDENT_READ)),
) -> Page[StudentOut]:
    stmt = select(Student).options(
        selectinload(Student.guardians).selectinload(StudentGuardian.guardian),
        selectinload(Student.group),
        selectinload(Student.primary_instructor),
    )
    stmt = _scoped_query(scope, stmt)
    stmt = apply_search(
        stmt,
        Student,
        q,
        ["first_name", "last_name", "student_number", "phone", "email"],
    )
    if status:
        stmt = stmt.where(Student.status == status)
    if swim_level:
        stmt = stmt.where(Student.swim_level == swim_level)
    if group_id:
        stmt = stmt.where(Student.group_id == group_id)
    if instructor_id:
        stmt = stmt.where(Student.primary_instructor_id == instructor_id)
    if not include_demo:
        stmt = stmt.where(Student.is_demo.is_(False))
    today = date.today()
    if min_age is not None:
        stmt = stmt.where(
            Student.birth_date <= today - timedelta(days=min_age * 365.25)
        )
    if max_age is not None:
        stmt = stmt.where(
            Student.birth_date >= today - timedelta(days=(max_age + 1) * 365.25)
        )

    stmt = apply_sort(stmt, Student, params, "last_name")
    rows, total = paginate(db, stmt, params)
    return Page[StudentOut](
        items=[_to_out(s, scope) for s in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=StudentOut, status_code=201, summary="Öğrenci oluştur")
def create_student(
    payload: StudentCreate,
    request: Request,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    current: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
) -> StudentOut:
    number = payload.student_number or next_sequence_number(
        db, Student, "student_number", "OGR"
    )
    if db.scalar(select(Student).where(Student.student_number == number)):
        raise ConflictError("student.number_exists", details={"student_number": number})

    data = payload.model_dump(
        exclude={"guardian_ids", "student_number", "registration_date"}
    )
    student = Student(
        **data,
        student_number=number,
        registration_date=payload.registration_date or date.today(),
        consent_date=date.today() if payload.consent_given else None,
    )
    db.add(student)
    db.flush()

    for guardian_id in payload.guardian_ids:
        if db.get(Guardian, guardian_id):
            db.add(
                StudentGuardian(
                    student_id=student.id,
                    guardian_id=guardian_id,
                    is_primary=guardian_id == payload.guardian_ids[0],
                )
            )

    audit.record(
        db,
        action="create",
        entity_type="student",
        entity_id=student.id,
        user=current,
        summary=f"Öğrenci kaydı: {student.full_name} ({number})",
        changes={"student_number": number, "full_name": student.full_name},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(student)
    return _to_out(student, scope)


@router.get("/stats/overview", summary="Öğrenci özet sayıları")
def student_overview(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STUDENT_READ)),
) -> dict:
    counts = dict(
        db.execute(
            select(Student.status, func.count(Student.id)).group_by(Student.status)
        ).all()
    )
    levels = dict(
        db.execute(
            select(Student.swim_level, func.count(Student.id)).group_by(
                Student.swim_level
            )
        ).all()
    )
    month_start = date.today().replace(day=1)
    new_this_month = db.scalar(
        select(func.count(Student.id)).where(Student.registration_date >= month_start)
    )
    return {
        "total": sum(counts.values()),
        "by_status": counts,
        "by_level": levels,
        "new_this_month": new_this_month or 0,
        "active": counts.get(StudentStatus.ACTIVE.value, 0),
    }


@router.get("/{student_id}", response_model=StudentDetail, summary="Öğrenci detayı")
def get_student(
    student_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.STUDENT_READ)),
) -> StudentDetail:
    allowed = scope.allowed_student_ids()
    if allowed is not None and student_id not in allowed:
        raise PermissionDeniedError()

    student = get_or_404(db, Student, student_id, "student.not_found")
    base = _to_out(student, scope)
    detail = StudentDetail(**base.model_dump())

    membership = db.scalar(
        select(Membership)
        .where(
            Membership.student_id == student_id,
            Membership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Membership.end_date.desc().nullslast())
        .limit(1)
    )
    if membership:
        detail.active_membership = {
            "id": membership.id,
            "package_name": membership.package.name if membership.package else None,
            "start_date": membership.start_date.isoformat(),
            "end_date": (
                membership.end_date.isoformat() if membership.end_date else None
            ),
            "remaining_credits": membership.remaining_credits,
            "total_credits": membership.total_credits,
            "days_remaining": membership.days_remaining,
            "status": membership.status,
        }

    total_att = (
        db.scalar(
            select(func.count(Attendance.id)).where(Attendance.student_id == student_id)
        )
        or 0
    )
    present = (
        db.scalar(
            select(func.count(Attendance.id)).where(
                Attendance.student_id == student_id,
                Attendance.status.in_(
                    [
                        AttendanceStatus.PRESENT,
                        AttendanceStatus.LATE,
                        AttendanceStatus.MAKEUP,
                    ]
                ),
            )
        )
        or 0
    )
    detail.attendance_rate = round(present / total_att * 100, 1) if total_att else None
    detail.total_lessons = (
        db.scalar(
            select(func.count(LessonEnrollment.id)).where(
                LessonEnrollment.student_id == student_id
            )
        )
        or 0
    )
    detail.personal_best_count = (
        db.scalar(
            select(func.count(PersonalBest.id)).where(
                PersonalBest.student_id == student_id
            )
        )
        or 0
    )

    invoiced = (
        db.scalar(
            select(
                func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)
            ).where(Invoice.student_id == student_id)
        )
        or 0
    )
    detail.outstanding_balance = round(float(invoiced), 2)
    return detail


@router.patch("/{student_id}", response_model=StudentOut, summary="Öğrenci güncelle")
def update_student(
    student_id: int,
    payload: StudentUpdate,
    request: Request,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    current: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
) -> StudentOut:
    student = get_or_404(db, Student, student_id, "student.not_found")
    data = payload.model_dump(exclude_unset=True)

    # Hassas alanları yalnızca yetkili kullanıcı değiştirebilir
    if any(f in data for f in SENSITIVE_FIELDS) and not scope.can_read_sensitive():
        raise PermissionDeniedError(
            details={"required": [Perm.STUDENT_READ_SENSITIVE.value]}
        )

    changes: dict = {}
    for key, value in data.items():
        old = getattr(student, key, None)
        if old != value:
            changes[key] = {
                "from": "***" if key in SENSITIVE_FIELDS else old,
                "to": "***" if key in SENSITIVE_FIELDS else value,
            }
            setattr(student, key, value)

    if data.get("status") == StudentStatus.LEFT and not student.left_date:
        student.left_date = date.today()

    audit.record(
        db,
        action="update",
        entity_type="student",
        entity_id=student.id,
        user=current,
        summary=f"Öğrenci güncellendi: {student.full_name}",
        changes=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(student)
    return _to_out(student, scope)


@router.delete("/{student_id}", response_model=Message, summary="Öğrenciyi sil")
def delete_student(
    student_id: int,
    request: Request,
    hard: bool = False,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.STUDENT_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    """Varsayılan davranış: pasife çekme. `hard=true` kalıcı siler (geri alınamaz)."""
    student = get_or_404(db, Student, student_id, "student.not_found")
    name = student.full_name

    if hard:
        db.delete(student)
        action, summary = "delete", f"Öğrenci kalıcı olarak silindi: {name}"
    else:
        student.status = StudentStatus.PASSIVE
        student.left_date = date.today()
        action, summary = "soft_delete", f"Öğrenci pasife alındı: {name}"

    audit.record(
        db,
        action=action,
        entity_type="student",
        entity_id=student_id,
        user=current,
        summary=summary,
        ip_address=client_ip(request),
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


@router.post(
    "/{student_id}/guardians/{guardian_id}",
    response_model=Message,
    summary="Veli bağla",
)
def link_guardian(
    student_id: int,
    guardian_id: int,
    is_primary: bool = False,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    get_or_404(db, Student, student_id, "student.not_found")
    get_or_404(db, Guardian, guardian_id)
    existing = db.scalar(
        select(StudentGuardian).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.guardian_id == guardian_id,
        )
    )
    if existing:
        raise ConflictError()
    db.add(
        StudentGuardian(
            student_id=student_id, guardian_id=guardian_id, is_primary=is_primary
        )
    )
    audit.record(
        db,
        action="link_guardian",
        entity_type="student",
        entity_id=student_id,
        user=current,
        summary=f"Veli bağlandı (veli #{guardian_id})",
    )
    db.commit()
    return Message(code="common.created", message=t("common.created", lang))


@router.delete(
    "/{student_id}/guardians/{guardian_id}",
    response_model=Message,
    summary="Veli bağını kaldır",
)
def unlink_guardian(
    student_id: int,
    guardian_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    link = db.scalar(
        select(StudentGuardian).where(
            StudentGuardian.student_id == student_id,
            StudentGuardian.guardian_id == guardian_id,
        )
    )
    if link:
        db.delete(link)
        audit.record(
            db,
            action="unlink_guardian",
            entity_type="student",
            entity_id=student_id,
            user=current,
            summary=f"Veli bağı kaldırıldı (veli #{guardian_id})",
        )
        db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


@router.get("/{student_id}/timeline", summary="Öğrenci zaman çizelgesi")
def student_timeline(
    student_id: int,
    limit: int = 50,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.STUDENT_READ)),
) -> dict:
    """Dersler, yoklamalar ve ödemelerden birleşik geçmiş üretir."""
    allowed = scope.allowed_student_ids()
    if allowed is not None and student_id not in allowed:
        raise PermissionDeniedError()
    get_or_404(db, Student, student_id, "student.not_found")

    events: list[dict] = []

    rows = db.execute(
        select(Attendance, Lesson)
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Attendance.student_id == student_id)
        .order_by(Lesson.start_at.desc())
        .limit(limit)
    ).all()
    for att, lesson in rows:
        events.append(
            {
                "type": "attendance",
                "at": lesson.start_at.isoformat(),
                "title": lesson.title,
                "status": att.status,
                "detail": lesson.lesson_type,
            }
        )

    payments = db.scalars(
        select(Payment)
        .where(Payment.student_id == student_id)
        .order_by(Payment.payment_date.desc())
        .limit(limit)
    ).all()
    for p in payments:
        events.append(
            {
                "type": "payment",
                "at": p.payment_date.isoformat(),
                "title": f"{float(p.amount):,.2f} {p.currency}",
                "status": p.status,
                "detail": p.method,
            }
        )

    memberships = db.scalars(
        select(Membership)
        .where(Membership.student_id == student_id)
        .order_by(Membership.start_date.desc())
        .limit(20)
    ).all()
    for m in memberships:
        events.append(
            {
                "type": "membership",
                "at": m.start_date.isoformat(),
                "title": m.package.name if m.package else "Üyelik",
                "status": m.status,
                "detail": f"{m.used_credits}/{m.total_credits or '∞'}",
            }
        )

    events.sort(key=lambda e: e["at"], reverse=True)
    return {"student_id": student_id, "events": events[:limit], "total": len(events)}


@router.get("/groups/list", summary="Grupları listele")
def list_groups(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STUDENT_READ)),
) -> list[dict]:
    rows = db.execute(
        select(Group, func.count(Student.id))
        .outerjoin(Student, Student.group_id == Group.id)
        .group_by(Group.id)
        .order_by(Group.name)
    ).all()
    return [
        {
            "id": g.id,
            "name": g.name,
            "level": g.level,
            "color": g.color,
            "capacity": g.capacity,
            "is_active": g.is_active,
            "min_age": g.min_age,
            "max_age": g.max_age,
            "student_count": count,
            "default_instructor_id": g.default_instructor_id,
        }
        for g, count in rows
    ]
