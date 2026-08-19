"""Finans uçları: ödeme, fatura, gider, indirim / Finance endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

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
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.enums import PaymentStatus, StudentStatus, TransactionDirection
from app.models.finance import CashTransaction, Discount, Expense, Invoice, Payment
from app.models.membership import Membership
from app.models.people import Student
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.operations import (
    DiscountBase,
    DiscountOut,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
    FinanceSummary,
    InvoiceCreate,
    InvoiceOut,
    PaymentCreate,
    PaymentOut,
    PaymentRefund,
    PaymentUpdate,
)
from app.services import audit
from app.services.crud import get_or_404, next_sequence_number, paginate

router = APIRouter(prefix="/finance", tags=["Finans"])


def _payment_out(payment: Payment) -> PaymentOut:
    out = PaymentOut.model_validate(payment)
    out.net_amount = payment.net_amount
    if payment.student:
        out.student_name = payment.student.full_name
    return out


def _invoice_out(invoice: Invoice) -> InvoiceOut:
    out = InvoiceOut.model_validate(invoice)
    out.balance = invoice.balance
    out.is_overdue = invoice.is_overdue
    out.days_overdue = invoice.days_overdue
    if invoice.student:
        out.student_name = invoice.student.full_name
    return out


def _ledger(
    db: Session,
    direction: str,
    amount: float,
    method: str,
    description: str,
    payment_id: int | None = None,
    expense_id: int | None = None,
) -> None:
    db.add(
        CashTransaction(
            direction=direction,
            amount=amount,
            method=method,
            occurred_at=datetime.now(timezone.utc),
            description=description[:400],
            payment_id=payment_id,
            expense_id=expense_id,
        )
    )


# ---------------------------------------------------------------------------
# Ödemeler
# ---------------------------------------------------------------------------
@router.get("/payments", response_model=Page[PaymentOut], summary="Ödemeleri listele")
def list_payments(
    student_id: int | None = None,
    method: str | None = None,
    status: PaymentStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.FINANCE_READ)),
) -> Page[PaymentOut]:
    stmt = select(Payment).options(selectinload(Payment.student))
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        stmt = stmt.where(Payment.student_id.in_(allowed))
    if student_id:
        stmt = stmt.where(Payment.student_id == student_id)
    if method:
        stmt = stmt.where(Payment.method == method)
    if status:
        stmt = stmt.where(Payment.status == status)
    if date_from:
        stmt = stmt.where(Payment.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(Payment.payment_date <= date_to)

    stmt = stmt.order_by(Payment.payment_date.desc(), Payment.id.desc())
    rows, total = paginate(db, stmt, params)
    return Page[PaymentOut](
        items=[_payment_out(p) for p in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "/payments", response_model=PaymentOut, status_code=201, summary="Ödeme al"
)
def create_payment(
    payload: PaymentCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> PaymentOut:
    if payload.amount <= 0:
        raise ValidationError("payment.amount_invalid")

    if payload.student_id:
        get_or_404(db, Student, payload.student_id, "student.not_found")

    invoice = None
    if payload.invoice_id:
        invoice = get_or_404(db, Invoice, payload.invoice_id)
        if payload.amount > invoice.balance + 0.01:
            raise ValidationError(
                "payment.exceeds_balance", details={"balance": invoice.balance}
            )

    payment = Payment(
        receipt_number=next_sequence_number(db, Payment, "receipt_number", "FIS", 6),
        student_id=payload.student_id,
        membership_id=payload.membership_id,
        invoice_id=payload.invoice_id,
        amount=payload.amount,
        currency=payload.currency,
        method=payload.method,
        status=PaymentStatus.PAID,
        payment_date=payload.payment_date or date.today(),
        reference=payload.reference,
        description=payload.description,
        received_by_user_id=current.id,
    )
    db.add(payment)
    db.flush()

    if invoice:
        invoice.paid_amount = float(invoice.paid_amount) + payload.amount
        if invoice.balance <= 0.01:
            invoice.status = PaymentStatus.PAID
        elif invoice.paid_amount > 0:
            invoice.status = PaymentStatus.PARTIAL

    if payload.membership_id:
        membership = db.get(Membership, payload.membership_id)
        if membership:
            membership.price_paid = float(membership.price_paid) + payload.amount

    _ledger(
        db,
        TransactionDirection.INCOME,
        payload.amount,
        payload.method,
        payload.description or f"Ödeme {payment.receipt_number}",
        payment_id=payment.id,
    )
    audit.record(
        db,
        action="create",
        entity_type="payment",
        entity_id=payment.id,
        user=current,
        summary=f"Tahsilat: {payload.amount:,.2f} {payload.currency} ({payment.receipt_number})",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(payment)
    return _payment_out(payment)


@router.patch(
    "/payments/{payment_id}", response_model=PaymentOut, summary="Ödeme güncelle"
)
def update_payment(
    payment_id: int,
    payload: PaymentUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> PaymentOut:
    payment = get_or_404(db, Payment, payment_id, "payment.not_found")
    changes: dict = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        old = getattr(payment, key, None)
        if old != value:
            changes[key] = {"from": str(old), "to": str(value)}
            setattr(payment, key, value)
    audit.record(
        db,
        action="update",
        entity_type="payment",
        entity_id=payment_id,
        user=current,
        summary=f"Ödeme güncellendi: {payment.receipt_number}",
        changes=changes,
    )
    db.commit()
    db.refresh(payment)
    return _payment_out(payment)


@router.post(
    "/payments/{payment_id}/refund", response_model=PaymentOut, summary="İade işle"
)
def refund_payment(
    payment_id: int,
    payload: PaymentRefund,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> PaymentOut:
    payment = get_or_404(db, Payment, payment_id, "payment.not_found")
    remaining = float(payment.amount) - float(payment.refunded_amount)
    if payload.amount > remaining + 0.01:
        raise ValidationError(
            "payment.exceeds_balance", details={"refundable": round(remaining, 2)}
        )

    payment.refunded_amount = float(payment.refunded_amount) + payload.amount
    payment.refund_reason = payload.reason
    if abs(float(payment.refunded_amount) - float(payment.amount)) < 0.01:
        payment.status = PaymentStatus.REFUNDED

    if payment.invoice_id:
        invoice = db.get(Invoice, payment.invoice_id)
        if invoice:
            invoice.paid_amount = max(0.0, float(invoice.paid_amount) - payload.amount)
            invoice.status = (
                PaymentStatus.PAID if invoice.balance <= 0.01 else PaymentStatus.PARTIAL
            )

    _ledger(
        db,
        TransactionDirection.EXPENSE,
        payload.amount,
        payment.method,
        f"İade: {payment.receipt_number} · {payload.reason}",
        payment_id=payment.id,
    )
    audit.record(
        db,
        action="refund",
        entity_type="payment",
        entity_id=payment_id,
        user=current,
        summary=f"İade: {payload.amount:,.2f} · {payload.reason}",
    )
    db.commit()
    db.refresh(payment)
    return _payment_out(payment)


@router.delete("/payments/{payment_id}", response_model=Message, summary="Ödeme iptal")
def cancel_payment(
    payment_id: int,
    reason: str,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    payment = get_or_404(db, Payment, payment_id, "payment.not_found")
    payment.status = PaymentStatus.CANCELLED
    payment.description = f"{payment.description or ''} | İPTAL: {reason}".strip(" |")
    if payment.invoice_id:
        invoice = db.get(Invoice, payment.invoice_id)
        if invoice:
            invoice.paid_amount = max(
                0.0, float(invoice.paid_amount) - float(payment.amount)
            )
            invoice.status = (
                PaymentStatus.PAID if invoice.balance <= 0.01 else PaymentStatus.PENDING
            )
    audit.record(
        db,
        action="cancel",
        entity_type="payment",
        entity_id=payment_id,
        user=current,
        summary=f"Ödeme iptal edildi: {payment.receipt_number} · {reason}",
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


# ---------------------------------------------------------------------------
# Faturalar / borçlar
# ---------------------------------------------------------------------------
@router.get("/invoices", response_model=Page[InvoiceOut], summary="Faturaları listele")
def list_invoices(
    student_id: int | None = None,
    status: PaymentStatus | None = None,
    overdue_only: bool = False,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.FINANCE_READ)),
) -> Page[InvoiceOut]:
    stmt = select(Invoice).options(selectinload(Invoice.student))
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        stmt = stmt.where(Invoice.student_id.in_(allowed))
    if student_id:
        stmt = stmt.where(Invoice.student_id == student_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if overdue_only:
        stmt = stmt.where(
            Invoice.due_date < date.today(), Invoice.total_amount > Invoice.paid_amount
        )
    stmt = stmt.order_by(Invoice.due_date.desc())
    rows, total = paginate(db, stmt, params)
    return Page[InvoiceOut](
        items=[_invoice_out(i) for i in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "/invoices", response_model=InvoiceOut, status_code=201, summary="Fatura oluştur"
)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> InvoiceOut:
    total = payload.subtotal - payload.discount_amount + payload.tax_amount
    if total < 0:
        raise ValidationError(details={"reason": "negative_total"})

    invoice = Invoice(
        invoice_number=next_sequence_number(db, Invoice, "invoice_number", "FT", 6),
        student_id=payload.student_id,
        membership_id=payload.membership_id,
        issue_date=payload.issue_date or date.today(),
        due_date=payload.due_date,
        subtotal=payload.subtotal,
        discount_amount=payload.discount_amount,
        tax_amount=payload.tax_amount,
        total_amount=total,
        paid_amount=0,
        currency=settings.app_currency,
        status=PaymentStatus.PENDING,
        description=payload.description,
    )
    db.add(invoice)
    audit.record(
        db,
        action="create",
        entity_type="invoice",
        user=current,
        summary=f"Fatura oluşturuldu: {invoice.invoice_number} ({total:,.2f})",
    )
    db.commit()
    db.refresh(invoice)
    return _invoice_out(invoice)


@router.get("/outstanding", summary="Bekleyen borçlar")
def outstanding_balances(
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.FINANCE_READ)),
) -> dict:
    stmt = (
        select(Invoice)
        .options(selectinload(Invoice.student))
        .where(Invoice.total_amount > Invoice.paid_amount)
        .order_by(Invoice.due_date)
    )
    # Satır bazlı kapsam: veli/öğrenci yalnızca kendi borcunu görür.
    stmt = scope.scope_students(stmt, Invoice.student_id)
    rows = db.scalars(stmt).all()

    today = date.today()
    buckets = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "60_plus": 0.0}
    items = []
    for invoice in rows:
        balance = invoice.balance
        days = (today - invoice.due_date).days
        if days <= 0:
            buckets["current"] += balance
        elif days <= 30:
            buckets["1_30"] += balance
        elif days <= 60:
            buckets["31_60"] += balance
        else:
            buckets["60_plus"] += balance
        items.append(
            {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "student_id": invoice.student_id,
                "student_name": invoice.student.full_name if invoice.student else None,
                "due_date": invoice.due_date.isoformat(),
                "balance": round(balance, 2),
                "days_overdue": max(0, days),
            }
        )

    return {
        "total_outstanding": round(sum(buckets.values()), 2),
        "aging": {k: round(v, 2) for k, v in buckets.items()},
        "count": len(items),
        "items": items[:200],
    }


# ---------------------------------------------------------------------------
# Giderler
# ---------------------------------------------------------------------------
@router.get("/expenses", response_model=Page[ExpenseOut], summary="Giderleri listele")
def list_expenses(
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.FINANCE_READ)),
) -> Page[ExpenseOut]:
    stmt = select(Expense)
    if category:
        stmt = stmt.where(Expense.category == category)
    if date_from:
        stmt = stmt.where(Expense.expense_date >= date_from)
    if date_to:
        stmt = stmt.where(Expense.expense_date <= date_to)
    stmt = stmt.order_by(Expense.expense_date.desc())
    rows, total = paginate(db, stmt, params)
    return Page[ExpenseOut](
        items=[ExpenseOut.model_validate(e) for e in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "/expenses", response_model=ExpenseOut, status_code=201, summary="Gider ekle"
)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> ExpenseOut:
    expense = Expense(
        **payload.model_dump(exclude={"expense_date"}),
        expense_date=payload.expense_date or date.today(),
        created_by_user_id=current.id,
    )
    db.add(expense)
    db.flush()
    _ledger(
        db,
        TransactionDirection.EXPENSE,
        payload.amount,
        payload.method,
        payload.title,
        expense_id=expense.id,
    )
    audit.record(
        db,
        action="create",
        entity_type="expense",
        entity_id=expense.id,
        user=current,
        summary=f"Gider: {payload.title} ({payload.amount:,.2f})",
    )
    db.commit()
    db.refresh(expense)
    return ExpenseOut.model_validate(expense)


@router.patch(
    "/expenses/{expense_id}", response_model=ExpenseOut, summary="Gider güncelle"
)
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> ExpenseOut:
    expense = get_or_404(db, Expense, expense_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(expense, key, value)
    audit.record(
        db,
        action="update",
        entity_type="expense",
        entity_id=expense_id,
        user=current,
        summary=f"Gider güncellendi: {expense.title}",
    )
    db.commit()
    db.refresh(expense)
    return ExpenseOut.model_validate(expense)


@router.delete("/expenses/{expense_id}", response_model=Message, summary="Gider sil")
def delete_expense(
    expense_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    expense = get_or_404(db, Expense, expense_id)
    title = expense.title
    db.delete(expense)
    audit.record(
        db,
        action="delete",
        entity_type="expense",
        entity_id=expense_id,
        user=current,
        summary=f"Gider silindi: {title}",
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# İndirimler
# ---------------------------------------------------------------------------
@router.get(
    "/discounts", response_model=list[DiscountOut], summary="İndirimleri listele"
)
def list_discounts(
    active_only: bool = False,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.FINANCE_READ)),
) -> list[DiscountOut]:
    stmt = select(Discount).order_by(Discount.valid_until.desc())
    rows = db.scalars(stmt).all()
    result = []
    for discount in rows:
        if active_only and not discount.is_valid_now:
            continue
        item = DiscountOut.model_validate(discount)
        item.is_valid_now = discount.is_valid_now
        result.append(item)
    return result


@router.post(
    "/discounts", response_model=DiscountOut, status_code=201, summary="İndirim tanımla"
)
def create_discount(
    payload: DiscountBase,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.FINANCE_WRITE)),
) -> DiscountOut:
    discount = Discount(**payload.model_dump())
    db.add(discount)
    audit.record(
        db,
        action="create",
        entity_type="discount",
        user=current,
        summary=f"İndirim tanımlandı: {payload.code}",
    )
    db.commit()
    db.refresh(discount)
    out = DiscountOut.model_validate(discount)
    out.is_valid_now = discount.is_valid_now
    return out


# ---------------------------------------------------------------------------
# Finans özeti
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=FinanceSummary, summary="Finans panosu")
def finance_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.FINANCE_READ)),
) -> FinanceSummary:
    end = date_to or date.today()
    start = date_from or end.replace(day=1)

    payments = db.scalars(
        select(Payment).where(
            Payment.payment_date >= start,
            Payment.payment_date <= end,
            Payment.status.notin_([PaymentStatus.CANCELLED]),
        )
    ).all()
    expenses = db.scalars(
        select(Expense).where(
            Expense.expense_date >= start, Expense.expense_date <= end
        )
    ).all()

    total_income = sum(p.net_amount for p in payments)
    total_expense = sum(float(e.amount) for e in expenses)

    income_by_method: dict[str, float] = defaultdict(float)
    for p in payments:
        income_by_method[p.method] += p.net_amount

    expense_by_category: dict[str, float] = defaultdict(float)
    for e in expenses:
        expense_by_category[e.category] += float(e.amount)

    income_by_package: dict[str, float] = defaultdict(float)
    for p in payments:
        if p.membership and p.membership.package:
            income_by_package[p.membership.package.name] += p.net_amount

    invoices = db.scalars(
        select(Invoice).where(Invoice.total_amount > Invoice.paid_amount)
    ).all()
    outstanding = sum(i.balance for i in invoices)
    overdue_list = [i for i in invoices if i.is_overdue]
    overdue_total = sum(i.balance for i in overdue_list)

    invoiced_period = (
        db.scalar(
            select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
                Invoice.issue_date >= start, Invoice.issue_date <= end
            )
        )
        or 0
    )
    collected_period = (
        db.scalar(
            select(func.coalesce(func.sum(Invoice.paid_amount), 0)).where(
                Invoice.issue_date >= start, Invoice.issue_date <= end
            )
        )
        or 0
    )
    collection_rate = (
        round(float(collected_period) / float(invoiced_period) * 100, 1)
        if float(invoiced_period) > 0
        else 100.0
    )

    active_students = (
        db.scalar(
            select(func.count(Student.id)).where(Student.status == StudentStatus.ACTIVE)
        )
        or 0
    )

    # Son 12 ay gelir/gider serisi
    monthly: list[dict] = []
    cursor = (end.replace(day=1) - timedelta(days=334)).replace(day=1)
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        month_income = (
            db.scalar(
                select(
                    func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
                ).where(
                    Payment.payment_date >= cursor,
                    Payment.payment_date < next_month,
                    Payment.status.notin_([PaymentStatus.CANCELLED]),
                )
            )
            or 0
        )
        month_expense = (
            db.scalar(
                select(func.coalesce(func.sum(Expense.amount), 0)).where(
                    Expense.expense_date >= cursor, Expense.expense_date < next_month
                )
            )
            or 0
        )
        monthly.append(
            {
                "label": f"{cursor:%Y-%m}",
                "income": round(float(month_income), 2),
                "expense": round(float(month_expense), 2),
                "net": round(float(month_income) - float(month_expense), 2),
            }
        )
        cursor = next_month

    return FinanceSummary(
        period_start=start,
        period_end=end,
        currency=settings.app_currency,
        total_income=round(total_income, 2),
        total_expense=round(total_expense, 2),
        net_income=round(total_income - total_expense, 2),
        outstanding_total=round(outstanding, 2),
        overdue_total=round(overdue_total, 2),
        overdue_count=len(overdue_list),
        collection_rate=collection_rate,
        revenue_per_student=(
            round(total_income / active_students, 2) if active_students else 0.0
        ),
        active_student_count=active_students,
        income_by_method={k: round(v, 2) for k, v in income_by_method.items()},
        expense_by_category={k: round(v, 2) for k, v in expense_by_category.items()},
        income_by_package={k: round(v, 2) for k, v in income_by_package.items()},
        monthly_series=monthly,
    )
