"""Veli yönetimi ve veli portalı uçları / Guardian management and portal."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import (
    AccessScope,
    client_ip,
    db_session,
    get_current_user,
    get_language,
    get_scope,
    pagination,
    require_permissions,
)
from app.core.exceptions import PermissionDeniedError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.attendance import Attendance
from app.models.enums import MembershipStatus
from app.models.finance import Invoice
from app.models.lesson import Lesson, LessonEnrollment
from app.models.membership import Membership
from app.models.people import Guardian, Student, StudentGuardian
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.people import (
    GuardianCreate,
    GuardianOut,
    GuardianUpdate,
    StudentBrief,
)
from app.services import audit
from app.services.crud import apply_search, apply_sort, get_or_404, paginate

router = APIRouter(prefix="/guardians", tags=["Veliler"])


def _to_out(guardian: Guardian) -> GuardianOut:
    # `students` alanı şemadaki validation_alias sayesinde modeldeki
    # `student_list` özelliğinden otomatik doldurulur.
    return GuardianOut.model_validate(guardian)


@router.get("", response_model=Page[GuardianOut], summary="Velileri listele")
def list_guardians(
    q: str | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.GUARDIAN_READ)),
) -> Page[GuardianOut]:
    stmt = select(Guardian).options(
        selectinload(Guardian.students).selectinload(StudentGuardian.student)
    )
    stmt = apply_search(
        stmt, Guardian, q, ["first_name", "last_name", "phone", "email"]
    )
    stmt = apply_sort(stmt, Guardian, params, "last_name")
    rows, total = paginate(db, stmt, params)
    return Page[GuardianOut](
        items=[_to_out(g) for g in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post("", response_model=GuardianOut, status_code=201, summary="Veli oluştur")
def create_guardian(
    payload: GuardianCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.GUARDIAN_WRITE)),
) -> GuardianOut:
    guardian = Guardian(
        **payload.model_dump(exclude={"student_ids", "create_portal_user"})
    )
    db.add(guardian)
    db.flush()

    for index, student_id in enumerate(payload.student_ids):
        if db.get(Student, student_id):
            db.add(
                StudentGuardian(
                    student_id=student_id,
                    guardian_id=guardian.id,
                    is_primary=index == 0,
                )
            )

    audit.record(
        db,
        action="create",
        entity_type="guardian",
        entity_id=guardian.id,
        user=current,
        summary=f"Veli kaydı: {guardian.full_name}",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(guardian)
    return _to_out(guardian)


@router.get("/portal/my-children", summary="Veli portalı: çocuklarım")
def my_children(
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    scope: AccessScope = Depends(get_scope),
) -> dict:
    """Giriş yapan velinin çocuklarının özeti: takvim, yoklama, ödeme, paket."""
    if not user.guardian:
        raise PermissionDeniedError(details={"reason": "no_guardian_profile"})

    today = date.today()
    week_end = today + timedelta(days=7)
    children: list[dict] = []

    for link in user.guardian.students:
        student = link.student
        upcoming = db.scalars(
            select(Lesson)
            .join(LessonEnrollment, LessonEnrollment.lesson_id == Lesson.id)
            .where(
                LessonEnrollment.student_id == student.id,
                Lesson.start_at >= datetime.combine(today, time.min),
                Lesson.start_at <= datetime.combine(week_end, time.max),
            )
            .order_by(Lesson.start_at)
            .limit(20)
        ).all()

        attendances = db.scalars(
            select(Attendance)
            .join(Lesson, Lesson.id == Attendance.lesson_id)
            .where(Attendance.student_id == student.id)
            .order_by(Lesson.start_at.desc())
            .limit(10)
        ).all()

        membership = db.scalar(
            select(Membership)
            .where(
                Membership.student_id == student.id,
                Membership.status == MembershipStatus.ACTIVE,
            )
            .order_by(Membership.end_date.desc().nullslast())
            .limit(1)
        )

        balance = sum(
            float(inv.total_amount) - float(inv.paid_amount)
            for inv in db.scalars(
                select(Invoice).where(Invoice.student_id == student.id)
            ).all()
        )

        children.append(
            {
                "student": StudentBrief.model_validate(student).model_dump(),
                "upcoming_lessons": [
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "start_at": lesson.start_at.isoformat(),
                        "end_at": lesson.end_at.isoformat(),
                        "pool": lesson.pool.name if lesson.pool else None,
                        "lane": lesson.lane.display_name if lesson.lane else None,
                        "instructor": (
                            lesson.instructor.full_name if lesson.instructor else None
                        ),
                        "status": lesson.status,
                    }
                    for lesson in upcoming
                ],
                "recent_attendance": [
                    {
                        "lesson_title": a.lesson.title if a.lesson else None,
                        "date": (
                            a.lesson.start_at.date().isoformat() if a.lesson else None
                        ),
                        "status": a.status,
                    }
                    for a in attendances
                ],
                "membership": (
                    {
                        "package_name": (
                            membership.package.name
                            if membership and membership.package
                            else None
                        ),
                        "remaining_credits": (
                            membership.remaining_credits if membership else None
                        ),
                        "end_date": (
                            membership.end_date.isoformat()
                            if membership and membership.end_date
                            else None
                        ),
                        "days_remaining": (
                            membership.days_remaining if membership else None
                        ),
                        "status": membership.status if membership else None,
                    }
                    if membership
                    else None
                ),
                "outstanding_balance": round(balance, 2),
                "notes": student.notes,
            }
        )

    return {"guardian": user.guardian.full_name, "children": children}


@router.get("/{guardian_id}", response_model=GuardianOut, summary="Veli detayı")
def get_guardian(
    guardian_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.GUARDIAN_READ)),
) -> GuardianOut:
    return _to_out(get_or_404(db, Guardian, guardian_id))


@router.patch("/{guardian_id}", response_model=GuardianOut, summary="Veli güncelle")
def update_guardian(
    guardian_id: int,
    payload: GuardianUpdate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.GUARDIAN_WRITE)),
) -> GuardianOut:
    guardian = get_or_404(db, Guardian, guardian_id)
    changes: dict = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        if getattr(guardian, key, None) != value:
            changes[key] = {"from": getattr(guardian, key, None), "to": value}
            setattr(guardian, key, value)
    audit.record(
        db,
        action="update",
        entity_type="guardian",
        entity_id=guardian.id,
        user=current,
        summary=f"Veli güncellendi: {guardian.full_name}",
        changes=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(guardian)
    return _to_out(guardian)


@router.delete("/{guardian_id}", response_model=Message, summary="Veli sil")
def delete_guardian(
    guardian_id: int,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.GUARDIAN_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    guardian = get_or_404(db, Guardian, guardian_id)
    name = guardian.full_name
    db.delete(guardian)
    audit.record(
        db,
        action="delete",
        entity_type="guardian",
        entity_id=guardian_id,
        user=current,
        summary=f"Veli silindi: {name}",
        ip_address=client_ip(request),
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))
