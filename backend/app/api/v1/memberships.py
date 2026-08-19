"""Paket ve üyelik uçları / Package and membership endpoints."""

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
from app.core.exceptions import ConflictError, ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.enums import MembershipStatus, PaymentStatus
from app.models.finance import Payment
from app.models.membership import Membership, MembershipFreeze, Package
from app.models.people import Student
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.operations import (
    MembershipCreate,
    MembershipFreezeCreate,
    MembershipFreezeOut,
    MembershipOut,
    MembershipRenewRequest,
    MembershipUpdate,
    PackageCreate,
    PackageOut,
    PackageUpdate,
)
from app.services import audit
from app.services.crud import get_or_404, next_sequence_number, paginate

router = APIRouter(prefix="/memberships", tags=["Üyelikler"])
packages_router = APIRouter(prefix="/packages", tags=["Paketler"])


def _decorate(membership: Membership) -> MembershipOut:
    out = MembershipOut.model_validate(membership)
    out.remaining_credits = membership.remaining_credits
    out.days_remaining = membership.days_remaining
    out.usage_rate = membership.usage_rate
    out.is_expiring_soon = membership.is_expiring_soon
    if membership.student:
        out.student_name = membership.student.full_name
        out.student_number = membership.student.student_number
    if membership.package:
        out.package_name = membership.package.name
        out.package_type = membership.package.package_type
    out.freezes = [MembershipFreezeOut.model_validate(f) for f in membership.freezes]
    for f in out.freezes:
        f.days = (f.end_date - f.start_date).days + 1
    return out


def _compute_end_date(package: Package, start: date) -> date | None:
    return (
        start + timedelta(days=package.duration_days) if package.duration_days else None
    )


# ---------------------------------------------------------------------------
# Paketler
# ---------------------------------------------------------------------------
@packages_router.get("", response_model=list[PackageOut], summary="Paketleri listele")
def list_packages(
    is_active: bool | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.MEMBERSHIP_READ)),
) -> list[PackageOut]:
    stmt = select(Package)
    if is_active is not None:
        stmt = stmt.where(Package.is_active.is_(is_active))
    packages = db.scalars(stmt.order_by(Package.price)).all()

    result = []
    for package in packages:
        item = PackageOut.model_validate(package)
        item.active_membership_count = (
            db.scalar(
                select(func.count(Membership.id)).where(
                    Membership.package_id == package.id,
                    Membership.status == MembershipStatus.ACTIVE,
                )
            )
            or 0
        )
        result.append(item)
    return result


@packages_router.post(
    "", response_model=PackageOut, status_code=201, summary="Paket oluştur"
)
def create_package(
    payload: PackageCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> PackageOut:
    if db.scalar(select(Package).where(Package.name == payload.name)):
        raise ConflictError(details={"field": "name"})
    package = Package(**payload.model_dump())
    db.add(package)
    audit.record(
        db,
        action="create",
        entity_type="package",
        user=current,
        summary=f"Paket oluşturuldu: {package.name} ({package.price} {package.currency})",
    )
    db.commit()
    db.refresh(package)
    return PackageOut.model_validate(package)


@packages_router.patch(
    "/{package_id}", response_model=PackageOut, summary="Paket güncelle"
)
def update_package(
    package_id: int,
    payload: PackageUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> PackageOut:
    package = get_or_404(db, Package, package_id)
    changes: dict = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        old = getattr(package, key, None)
        if old != value:
            changes[key] = {"from": str(old), "to": str(value)}
            setattr(package, key, value)
    audit.record(
        db,
        action="update",
        entity_type="package",
        entity_id=package_id,
        user=current,
        summary=f"Paket güncellendi: {package.name}",
        changes=changes,
    )
    db.commit()
    db.refresh(package)
    return PackageOut.model_validate(package)


@packages_router.delete(
    "/{package_id}", response_model=Message, summary="Paketi pasife al"
)
def deactivate_package(
    package_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    package = get_or_404(db, Package, package_id)
    package.is_active = False
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


# ---------------------------------------------------------------------------
# Üyelikler
# ---------------------------------------------------------------------------
@router.get("", response_model=Page[MembershipOut], summary="Üyelikleri listele")
def list_memberships(
    student_id: int | None = None,
    status: MembershipStatus | None = None,
    package_id: int | None = None,
    expiring_days: int | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.MEMBERSHIP_READ)),
) -> Page[MembershipOut]:
    stmt = select(Membership).options(
        selectinload(Membership.student),
        selectinload(Membership.package),
        selectinload(Membership.freezes),
    )
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        stmt = stmt.where(Membership.student_id.in_(allowed))
    if student_id:
        stmt = stmt.where(Membership.student_id == student_id)
    if status:
        stmt = stmt.where(Membership.status == status)
    if package_id:
        stmt = stmt.where(Membership.package_id == package_id)
    if expiring_days is not None:
        stmt = stmt.where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date.is_not(None),
            Membership.end_date >= date.today(),
            Membership.end_date <= date.today() + timedelta(days=expiring_days),
        )

    stmt = stmt.order_by(Membership.start_date.desc())
    rows, total = paginate(db, stmt, params)
    return Page[MembershipOut](
        items=[_decorate(m) for m in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "", response_model=MembershipOut, status_code=201, summary="Üyelik oluştur"
)
def create_membership(
    payload: MembershipCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> MembershipOut:
    student = get_or_404(db, Student, payload.student_id, "student.not_found")
    package = get_or_404(db, Package, payload.package_id)

    start = payload.start_date or date.today()
    price = float(package.price) - float(payload.discount_amount)
    if price < 0:
        raise ValidationError(details={"reason": "discount_exceeds_price"})

    membership = Membership(
        student_id=payload.student_id,
        package_id=payload.package_id,
        start_date=start,
        end_date=_compute_end_date(package, start),
        total_credits=package.lesson_count,
        used_credits=0,
        price_paid=0,
        discount_amount=payload.discount_amount,
        discount_reason=payload.discount_reason,
        auto_renew=payload.auto_renew,
        notes=payload.notes,
        status=MembershipStatus.ACTIVE,
    )
    db.add(membership)
    db.flush()

    if payload.create_payment:
        amount = payload.payment_amount if payload.payment_amount is not None else price
        if amount > 0:
            payment = Payment(
                receipt_number=next_sequence_number(
                    db, Payment, "receipt_number", "FIS", 6
                ),
                student_id=payload.student_id,
                membership_id=membership.id,
                amount=amount,
                currency=package.currency,
                method=payload.payment_method,
                status=PaymentStatus.PAID,
                payment_date=date.today(),
                description=f"{package.name} paket ödemesi",
                received_by_user_id=current.id,
            )
            db.add(payment)
            membership.price_paid = amount

    audit.record(
        db,
        action="create",
        entity_type="membership",
        entity_id=membership.id,
        user=current,
        summary=f"Üyelik oluşturuldu: {student.full_name} - {package.name}",
        changes={"package": package.name, "price": price},
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(membership)
    return _decorate(membership)


@router.get(
    "/expiring", response_model=list[MembershipOut], summary="Süresi dolacak üyelikler"
)
def expiring_memberships(
    days: int = 14,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.MEMBERSHIP_READ)),
) -> list[MembershipOut]:
    rows = db.scalars(
        scope.scope_students(select(Membership), Membership.student_id)
        .options(selectinload(Membership.student), selectinload(Membership.package))
        .where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date.is_not(None),
            Membership.end_date >= date.today(),
            Membership.end_date <= date.today() + timedelta(days=days),
        )
        .order_by(Membership.end_date)
    ).all()
    return [_decorate(m) for m in rows]


@router.get(
    "/low-credit", response_model=list[MembershipOut], summary="Ders hakkı azalanlar"
)
def low_credit_memberships(
    threshold: int = 2,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.MEMBERSHIP_READ)),
) -> list[MembershipOut]:
    rows = db.scalars(
        scope.scope_students(select(Membership), Membership.student_id)
        .options(selectinload(Membership.student), selectinload(Membership.package))
        .where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.total_credits.is_not(None),
            (Membership.total_credits - Membership.used_credits) <= threshold,
        )
        .order_by(Membership.total_credits - Membership.used_credits)
    ).all()
    return [_decorate(m) for m in rows]


@router.get("/{membership_id}", response_model=MembershipOut, summary="Üyelik detayı")
def get_membership(
    membership_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.MEMBERSHIP_READ)),
) -> MembershipOut:
    membership = get_or_404(db, Membership, membership_id, "membership.not_found")
    # Nesne bazlı yetki (IDOR): başka ailenin üyeliği okunamaz.
    scope.assert_student_allowed(membership.student_id)
    return _decorate(membership)


@router.patch(
    "/{membership_id}", response_model=MembershipOut, summary="Üyelik güncelle"
)
def update_membership(
    membership_id: int,
    payload: MembershipUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> MembershipOut:
    membership = get_or_404(db, Membership, membership_id, "membership.not_found")
    changes: dict = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        old = getattr(membership, key, None)
        if old != value:
            changes[key] = {"from": str(old), "to": str(value)}
            setattr(membership, key, value)
    audit.record(
        db,
        action="update",
        entity_type="membership",
        entity_id=membership_id,
        user=current,
        summary="Üyelik güncellendi",
        changes=changes,
    )
    db.commit()
    db.refresh(membership)
    return _decorate(membership)


@router.post(
    "/{membership_id}/freeze", response_model=MembershipOut, summary="Üyeliği dondur"
)
def freeze_membership(
    membership_id: int,
    payload: MembershipFreezeCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> MembershipOut:
    """Dondurma süresi kadar bitiş tarihi ötelenir."""
    membership = get_or_404(db, Membership, membership_id, "membership.not_found")
    package = membership.package
    days = (payload.end_date - payload.start_date).days + 1

    used_days = sum(f.days for f in membership.freezes)
    if package and used_days + days > package.max_freeze_days:
        raise ValidationError(
            details={
                "reason": "freeze_limit_exceeded",
                "max_days": package.max_freeze_days,
                "used_days": used_days,
                "requested": days,
            }
        )

    db.add(
        MembershipFreeze(
            membership_id=membership_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            reason=payload.reason,
            approved_by_user_id=current.id,
        )
    )
    if membership.end_date:
        membership.end_date = membership.end_date + timedelta(days=days)
    membership.status = MembershipStatus.FROZEN

    audit.record(
        db,
        action="freeze",
        entity_type="membership",
        entity_id=membership_id,
        user=current,
        summary=f"Üyelik donduruldu: {days} gün ({payload.start_date} - {payload.end_date})",
    )
    db.commit()
    db.refresh(membership)
    return _decorate(membership)


@router.post(
    "/{membership_id}/unfreeze",
    response_model=MembershipOut,
    summary="Dondurmayı kaldır",
)
def unfreeze_membership(
    membership_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> MembershipOut:
    membership = get_or_404(db, Membership, membership_id, "membership.not_found")
    membership.status = MembershipStatus.ACTIVE
    audit.record(
        db,
        action="unfreeze",
        entity_type="membership",
        entity_id=membership_id,
        user=current,
        summary="Üyelik dondurması kaldırıldı",
    )
    db.commit()
    db.refresh(membership)
    return _decorate(membership)


@router.post(
    "/{membership_id}/renew", response_model=MembershipOut, summary="Üyeliği yenile"
)
def renew_membership(
    membership_id: int,
    payload: MembershipRenewRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
) -> MembershipOut:
    """Mevcut üyeliği kapatır ve aynı/yeni paketle yeni üyelik açar."""
    old = get_or_404(db, Membership, membership_id, "membership.not_found")
    package = get_or_404(db, Package, payload.package_id or old.package_id)

    start = payload.start_date or (
        max(date.today(), old.end_date + timedelta(days=1))
        if old.end_date
        else date.today()
    )
    price = float(package.price) - float(payload.discount_amount)

    new_membership = Membership(
        student_id=old.student_id,
        package_id=package.id,
        start_date=start,
        end_date=_compute_end_date(package, start),
        total_credits=package.lesson_count,
        used_credits=0,
        price_paid=0,
        discount_amount=payload.discount_amount,
        auto_renew=old.auto_renew,
        status=MembershipStatus.ACTIVE,
    )
    db.add(new_membership)
    db.flush()

    if old.status == MembershipStatus.ACTIVE:
        old.status = MembershipStatus.EXPIRED

    if payload.create_payment and price > 0:
        payment = Payment(
            receipt_number=next_sequence_number(
                db, Payment, "receipt_number", "FIS", 6
            ),
            student_id=old.student_id,
            membership_id=new_membership.id,
            amount=price,
            currency=package.currency,
            method=payload.payment_method,
            status=PaymentStatus.PAID,
            payment_date=date.today(),
            description=f"{package.name} yenileme",
            received_by_user_id=current.id,
        )
        db.add(payment)
        new_membership.price_paid = price

    audit.record(
        db,
        action="renew",
        entity_type="membership",
        entity_id=new_membership.id,
        user=current,
        summary=f"Üyelik yenilendi (eski #{membership_id}) - {package.name}",
    )
    db.commit()
    db.refresh(new_membership)
    return _decorate(new_membership)


@router.post(
    "/{membership_id}/cancel", response_model=Message, summary="Üyeliği iptal et"
)
def cancel_membership(
    membership_id: int,
    reason: str,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    membership = get_or_404(db, Membership, membership_id, "membership.not_found")
    membership.status = MembershipStatus.CANCELLED
    membership.cancelled_at = date.today()
    membership.cancellation_reason = reason
    audit.record(
        db,
        action="cancel",
        entity_type="membership",
        entity_id=membership_id,
        user=current,
        summary=f"Üyelik iptal edildi: {reason}",
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.post(
    "/refresh-statuses", response_model=Message, summary="Üyelik durumlarını güncelle"
)
def refresh_statuses(
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.MEMBERSHIP_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    """Süresi geçmiş veya kredisi biten üyelikleri EXPIRED yapar."""
    today = date.today()
    expired = 0
    for membership in db.scalars(
        select(Membership).where(Membership.status == MembershipStatus.ACTIVE)
    ).all():
        out_of_time = membership.end_date is not None and membership.end_date < today
        out_of_credit = (
            membership.total_credits is not None
            and membership.used_credits >= membership.total_credits
        )
        if out_of_time or out_of_credit:
            membership.status = MembershipStatus.EXPIRED
            expired += 1
    db.commit()
    return Message(
        code="common.updated",
        message=t("common.updated", lang),
        data={"expired": expired},
    )
