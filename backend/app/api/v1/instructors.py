"""Eğitmen ve grup yönetimi uçları / Instructor and group management."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

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
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.attendance import Attendance
from app.models.enums import AttendanceStatus, LessonStatus, LessonType
from app.models.lesson import Lesson
from app.models.people import (
    Group,
    Instructor,
    InstructorAvailability,
    InstructorCertificate,
    InstructorLeave,
    Student,
)
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.people import (
    AvailabilityBase,
    CertificateCreate,
    CertificateOut,
    GroupCreate,
    GroupOut,
    GroupUpdate,
    InstructorCreate,
    InstructorDetail,
    InstructorOut,
    InstructorUpdate,
    InstructorWorkload,
    LeaveBase,
    LeaveOut,
)
from app.services import audit
from app.services.crud import (
    apply_search,
    apply_sort,
    get_or_404,
    next_sequence_number,
    paginate,
)

router = APIRouter(prefix="/instructors", tags=["Eğitmenler"])
groups_router = APIRouter(prefix="/groups", tags=["Gruplar"])


def _to_out(instructor: Instructor, scope: AccessScope) -> InstructorOut:
    data = InstructorOut.model_validate(instructor)
    if not scope.can_read_salary():
        data.hourly_rate = None
        data.monthly_salary = None
    return data


@router.get("", response_model=Page[InstructorOut], summary="Eğitmenleri listele")
def list_instructors(
    q: str | None = None,
    is_active: bool | None = None,
    specialty: str | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.INSTRUCTOR_READ)),
) -> Page[InstructorOut]:
    stmt = select(Instructor).options(
        selectinload(Instructor.certificates), selectinload(Instructor.availabilities)
    )
    stmt = apply_search(
        stmt,
        Instructor,
        q,
        ["first_name", "last_name", "employee_number", "email", "phone"],
    )
    if is_active is not None:
        stmt = stmt.where(Instructor.is_active.is_(is_active))
    stmt = apply_sort(stmt, Instructor, params, "last_name")
    rows, total = paginate(db, stmt, params)

    items = [_to_out(i, scope) for i in rows]
    if specialty:
        items = [i for i in items if specialty in (i.specialties or [])]
    return Page[InstructorOut](
        items=items, total=total, page=params.page, page_size=params.page_size
    )


@router.post(
    "", response_model=InstructorOut, status_code=201, summary="Eğitmen oluştur"
)
def create_instructor(
    payload: InstructorCreate,
    request: Request,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    current: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
) -> InstructorOut:
    number = payload.employee_number or next_sequence_number(
        db, Instructor, "employee_number", "EGT", width=4
    )
    instructor = Instructor(
        **payload.model_dump(
            exclude={
                "employee_number",
                "availabilities",
                "create_portal_user",
                "portal_role_code",
            }
        ),
        employee_number=number,
    )
    db.add(instructor)
    db.flush()

    for slot in payload.availabilities:
        db.add(
            InstructorAvailability(
                instructor_id=instructor.id,
                weekday=slot.weekday,
                start_time=slot.start_time,
                end_time=slot.end_time,
            )
        )

    audit.record(
        db,
        action="create",
        entity_type="instructor",
        entity_id=instructor.id,
        user=current,
        summary=f"Eğitmen kaydı: {instructor.full_name} ({number})",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(instructor)
    return _to_out(instructor, scope)


@router.get(
    "/workload", response_model=list[InstructorWorkload], summary="Eğitmen iş yükü"
)
def instructor_workload(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.INSTRUCTOR_READ)),
) -> list[InstructorWorkload]:
    """Eğitmen ders yükü dağılımı - yük dengeleme için."""
    end = date_to or date.today()
    start = date_from or (end - timedelta(days=30))
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)

    rows: list[InstructorWorkload] = []
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
        total_hours = sum(lesson.duration_minutes for lesson in active) / 60
        enrolled = sum(lesson.enrolled_count for lesson in active)
        capacity = sum(lesson.capacity for lesson in active)
        private = sum(
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
            InstructorWorkload(
                instructor_id=instructor.id,
                full_name=instructor.full_name,
                lesson_count=len(active),
                total_hours=round(total_hours, 1),
                student_count=student_count,
                occupancy_rate=round(enrolled / capacity * 100, 1) if capacity else 0.0,
                cancellation_rate=(
                    round(cancelled / len(lessons) * 100, 1) if lessons else 0.0
                ),
                private_ratio=round(private / len(active) * 100, 1) if active else 0.0,
            )
        )
    rows.sort(key=lambda r: r.total_hours, reverse=True)
    return rows


@router.get(
    "/{instructor_id}", response_model=InstructorDetail, summary="Eğitmen detayı"
)
def get_instructor(
    instructor_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.INSTRUCTOR_READ)),
) -> InstructorDetail:
    instructor = get_or_404(db, Instructor, instructor_id, "instructor.not_found")
    base = _to_out(instructor, scope)
    detail = InstructorDetail(**base.model_dump())

    detail.student_count = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.primary_instructor_id == instructor_id
            )
        )
        or 0
    )

    week_start = datetime.combine(
        date.today() - timedelta(days=date.today().weekday()), time.min
    )
    week_end = week_start + timedelta(days=7)
    week_lessons = db.scalars(
        select(Lesson).where(
            Lesson.instructor_id == instructor_id,
            Lesson.start_at >= week_start,
            Lesson.start_at < week_end,
            Lesson.status != LessonStatus.CANCELLED,
        )
    ).all()
    detail.weekly_lesson_count = len(week_lessons)
    detail.weekly_hours = round(
        sum(lesson.duration_minutes for lesson in week_lessons) / 60, 1
    )

    detail.upcoming_lessons = (
        db.scalar(
            select(func.count(Lesson.id)).where(
                Lesson.instructor_id == instructor_id,
                Lesson.start_at >= datetime.now(),
                Lesson.status == LessonStatus.SCHEDULED,
            )
        )
        or 0
    )

    total = (
        db.scalar(
            select(func.count(Attendance.id))
            .join(Lesson, Lesson.id == Attendance.lesson_id)
            .where(Lesson.instructor_id == instructor_id)
        )
        or 0
    )
    present = (
        db.scalar(
            select(func.count(Attendance.id))
            .join(Lesson, Lesson.id == Attendance.lesson_id)
            .where(
                Lesson.instructor_id == instructor_id,
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
    detail.attendance_rate = round(present / total * 100, 1) if total else None
    detail.leaves = [LeaveOut.model_validate(leave) for leave in instructor.leaves]
    return detail


@router.patch(
    "/{instructor_id}", response_model=InstructorOut, summary="Eğitmen güncelle"
)
def update_instructor(
    instructor_id: int,
    payload: InstructorUpdate,
    request: Request,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    current: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
) -> InstructorOut:
    instructor = get_or_404(db, Instructor, instructor_id, "instructor.not_found")
    data = payload.model_dump(exclude_unset=True)
    if not scope.can_read_salary():
        data.pop("hourly_rate", None)
        data.pop("monthly_salary", None)

    changes: dict = {}
    for key, value in data.items():
        if getattr(instructor, key, None) != value:
            key_is_salary = key in ("hourly_rate", "monthly_salary")
            changes[key] = {
                "from": "***" if key_is_salary else getattr(instructor, key, None),
                "to": "***" if key_is_salary else value,
            }
            setattr(instructor, key, value)

    audit.record(
        db,
        action="update",
        entity_type="instructor",
        entity_id=instructor.id,
        user=current,
        summary=f"Eğitmen güncellendi: {instructor.full_name}",
        changes=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(instructor)
    return _to_out(instructor, scope)


@router.delete("/{instructor_id}", response_model=Message, summary="Eğitmeni pasife al")
def deactivate_instructor(
    instructor_id: int,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.INSTRUCTOR_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    instructor = get_or_404(db, Instructor, instructor_id, "instructor.not_found")
    instructor.is_active = False
    audit.record(
        db,
        action="deactivate",
        entity_type="instructor",
        entity_id=instructor_id,
        user=current,
        summary=f"Eğitmen pasife alındı: {instructor.full_name}",
        ip_address=client_ip(request),
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


# ---------------------------------------------------------------------------
# Sertifikalar / müsaitlik / izinler
# ---------------------------------------------------------------------------
@router.post(
    "/{instructor_id}/certificates",
    response_model=CertificateOut,
    status_code=201,
    summary="Sertifika ekle",
)
def add_certificate(
    instructor_id: int,
    payload: CertificateCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
) -> CertificateOut:
    get_or_404(db, Instructor, instructor_id, "instructor.not_found")
    cert = InstructorCertificate(instructor_id=instructor_id, **payload.model_dump())
    db.add(cert)
    audit.record(
        db,
        action="create",
        entity_type="instructor_certificate",
        entity_id=instructor_id,
        user=current,
        summary=f"Sertifika eklendi: {payload.name}",
    )
    db.commit()
    db.refresh(cert)
    return CertificateOut.model_validate(cert)


@router.delete(
    "/{instructor_id}/certificates/{cert_id}",
    response_model=Message,
    summary="Sertifika sil",
)
def delete_certificate(
    instructor_id: int,
    cert_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    cert = get_or_404(db, InstructorCertificate, cert_id)
    db.delete(cert)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


@router.put(
    "/{instructor_id}/availability",
    response_model=Message,
    summary="Müsaitlik takvimini ayarla",
)
def set_availability(
    instructor_id: int,
    slots: list[AvailabilityBase],
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    get_or_404(db, Instructor, instructor_id, "instructor.not_found")
    for old in db.scalars(
        select(InstructorAvailability).where(
            InstructorAvailability.instructor_id == instructor_id
        )
    ).all():
        db.delete(old)
    for slot in slots:
        db.add(InstructorAvailability(instructor_id=instructor_id, **slot.model_dump()))
    audit.record(
        db,
        action="update",
        entity_type="instructor_availability",
        entity_id=instructor_id,
        user=current,
        summary=f"Müsaitlik güncellendi ({len(slots)} dilim)",
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.post(
    "/{instructor_id}/leaves",
    response_model=LeaveOut,
    status_code=201,
    summary="İzin ekle",
)
def add_leave(
    instructor_id: int,
    payload: LeaveBase,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
) -> LeaveOut:
    get_or_404(db, Instructor, instructor_id, "instructor.not_found")
    leave = InstructorLeave(instructor_id=instructor_id, **payload.model_dump())
    db.add(leave)
    audit.record(
        db,
        action="create",
        entity_type="instructor_leave",
        entity_id=instructor_id,
        user=current,
        summary=f"İzin kaydı: {payload.start_date} - {payload.end_date}",
    )
    db.commit()
    db.refresh(leave)
    return LeaveOut.model_validate(leave)


@router.delete("/leaves/{leave_id}", response_model=Message, summary="İzin sil")
def delete_leave(
    leave_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.INSTRUCTOR_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    leave = get_or_404(db, InstructorLeave, leave_id)
    db.delete(leave)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Gruplar
# ---------------------------------------------------------------------------
@groups_router.get("", response_model=list[GroupOut], summary="Grupları listele")
def list_groups(
    is_active: bool | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STUDENT_READ)),
) -> list[GroupOut]:
    stmt = select(Group, func.count(Student.id)).outerjoin(
        Student, Student.group_id == Group.id
    )
    if is_active is not None:
        stmt = stmt.where(Group.is_active.is_(is_active))
    rows = db.execute(stmt.group_by(Group.id).order_by(Group.name)).all()
    result = []
    for group, count in rows:
        item = GroupOut.model_validate(group)
        item.student_count = count
        result.append(item)
    return result


@groups_router.post(
    "", response_model=GroupOut, status_code=201, summary="Grup oluştur"
)
def create_group(
    payload: GroupCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
) -> GroupOut:
    group = Group(**payload.model_dump())
    db.add(group)
    audit.record(
        db,
        action="create",
        entity_type="group",
        user=current,
        summary=f"Grup oluşturuldu: {group.name}",
    )
    db.commit()
    db.refresh(group)
    return GroupOut.model_validate(group)


@groups_router.patch("/{group_id}", response_model=GroupOut, summary="Grup güncelle")
def update_group(
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
) -> GroupOut:
    group = get_or_404(db, Group, group_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, key, value)
    audit.record(
        db,
        action="update",
        entity_type="group",
        entity_id=group_id,
        user=current,
        summary=f"Grup güncellendi: {group.name}",
    )
    db.commit()
    db.refresh(group)
    return GroupOut.model_validate(group)


@groups_router.delete("/{group_id}", response_model=Message, summary="Grup sil")
def delete_group(
    group_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.STUDENT_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    group = get_or_404(db, Group, group_id)
    db.delete(group)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))
