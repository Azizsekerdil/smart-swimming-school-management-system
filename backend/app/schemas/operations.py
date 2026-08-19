"""Yoklama, üyelik ve finans şemaları / Attendance, membership and finance schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (
    AttendanceMethod,
    AttendanceStatus,
    ExpenseCategory,
    MembershipStatus,
    PackageType,
    PaymentMethod,
    PaymentStatus,
)
from app.schemas.common import ORMModel


# ---------------------------------------------------------------------------
# Yoklama
# ---------------------------------------------------------------------------
class AttendanceEntry(BaseModel):
    student_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT
    late_minutes: int | None = Field(default=None, ge=0, le=240)
    excuse_reason: str | None = None
    notes: str | None = None


class AttendanceBulkCreate(BaseModel):
    """Bir dersin yoklamasını toplu kaydeder."""

    lesson_id: int
    method: AttendanceMethod = AttendanceMethod.MANUAL
    entries: list[AttendanceEntry] = Field(min_length=1)
    consume_credits: bool = True


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus | None = None
    late_minutes: int | None = None
    excuse_reason: str | None = None
    notes: str | None = None
    makeup_lesson_id: int | None = None


class AttendanceOut(ORMModel):
    id: int
    lesson_id: int
    student_id: int
    student_name: str | None = None
    student_number: str | None = None
    lesson_title: str | None = None
    lesson_start: datetime | None = None
    status: AttendanceStatus
    method: AttendanceMethod
    checked_in_at: datetime | None = None
    late_minutes: int | None = None
    excuse_reason: str | None = None
    notes: str | None = None
    makeup_lesson_id: int | None = None


class AttendanceSheetRow(BaseModel):
    """Yoklama ekranındaki tek satır."""

    student_id: int
    student_number: str
    full_name: str
    photo_url: str | None = None
    enrollment_status: str
    attendance_id: int | None = None
    status: AttendanceStatus | None = None
    late_minutes: int | None = None
    notes: str | None = None
    membership_remaining: int | None = None


class AttendanceSheet(BaseModel):
    lesson_id: int
    lesson_title: str
    start_at: datetime
    end_at: datetime
    pool_name: str | None = None
    lane_name: str | None = None
    instructor_name: str | None = None
    is_recorded: bool
    rows: list[AttendanceSheetRow]


class QRCheckinRequest(BaseModel):
    token: str
    card_code: str


# ---------------------------------------------------------------------------
# Paket / üyelik
# ---------------------------------------------------------------------------
class PackageBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    name_en: str | None = None
    package_type: PackageType = PackageType.LESSON_PACK
    description: str | None = None
    lesson_count: int | None = Field(default=None, ge=1, le=1000)
    duration_days: int | None = Field(default=None, ge=1, le=3650)
    price: float = Field(ge=0)
    currency: str = "TRY"
    max_freeze_days: int = Field(default=30, ge=0, le=365)
    is_active: bool = True
    color: str = "#6366f1"


class PackageCreate(PackageBase):
    pass


class PackageUpdate(BaseModel):
    name: str | None = None
    name_en: str | None = None
    package_type: PackageType | None = None
    description: str | None = None
    lesson_count: int | None = None
    duration_days: int | None = None
    price: float | None = None
    max_freeze_days: int | None = None
    is_active: bool | None = None
    color: str | None = None


class PackageOut(ORMModel, PackageBase):
    id: int
    active_membership_count: int = 0


class MembershipCreate(BaseModel):
    student_id: int
    package_id: int
    start_date: date | None = None
    discount_amount: float = Field(default=0, ge=0)
    discount_reason: str | None = None
    auto_renew: bool = False
    notes: str | None = None
    # İlk ödemeyi birlikte kaydet
    create_payment: bool = False
    payment_amount: float | None = None
    payment_method: PaymentMethod = PaymentMethod.CASH


class MembershipUpdate(BaseModel):
    status: MembershipStatus | None = None
    end_date: date | None = None
    auto_renew: bool | None = None
    notes: str | None = None
    total_credits: int | None = None


class MembershipFreezeCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = None

    @model_validator(mode="after")
    def _valid(self):  # noqa: ANN201
        if self.end_date < self.start_date:
            raise ValueError("Dondurma bitiş tarihi başlangıçtan önce olamaz.")
        return self


class MembershipFreezeOut(ORMModel):
    id: int
    membership_id: int
    start_date: date
    end_date: date
    reason: str | None = None
    days: int = 0


class MembershipOut(ORMModel):
    id: int
    student_id: int
    student_name: str | None = None
    student_number: str | None = None
    package_id: int
    package_name: str | None = None
    package_type: str | None = None
    start_date: date
    end_date: date | None = None
    status: MembershipStatus
    total_credits: int | None = None
    used_credits: int = 0
    remaining_credits: int | None = None
    days_remaining: int | None = None
    usage_rate: float = 0.0
    price_paid: float = 0.0
    discount_amount: float = 0.0
    auto_renew: bool = False
    is_expiring_soon: bool = False
    notes: str | None = None
    freezes: list[MembershipFreezeOut] = []


class MembershipRenewRequest(BaseModel):
    package_id: int | None = None
    start_date: date | None = None
    discount_amount: float = Field(default=0, ge=0)
    create_payment: bool = False
    payment_method: PaymentMethod = PaymentMethod.CASH


# ---------------------------------------------------------------------------
# Finans
# ---------------------------------------------------------------------------
class PaymentCreate(BaseModel):
    student_id: int | None = None
    membership_id: int | None = None
    invoice_id: int | None = None
    amount: float = Field(gt=0)
    currency: str = "TRY"
    method: PaymentMethod = PaymentMethod.CASH
    payment_date: date | None = None
    reference: str | None = None
    description: str | None = None


class PaymentUpdate(BaseModel):
    amount: float | None = None
    method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    payment_date: date | None = None
    reference: str | None = None
    description: str | None = None


class PaymentRefund(BaseModel):
    amount: float = Field(gt=0)
    reason: str = Field(min_length=3, max_length=300)


class PaymentOut(ORMModel):
    id: int
    receipt_number: str
    student_id: int | None = None
    student_name: str | None = None
    membership_id: int | None = None
    invoice_id: int | None = None
    amount: float
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    payment_date: date
    reference: str | None = None
    description: str | None = None
    refunded_amount: float = 0.0
    net_amount: float = 0.0
    created_at: datetime | None = None


class InvoiceCreate(BaseModel):
    student_id: int | None = None
    membership_id: int | None = None
    issue_date: date | None = None
    due_date: date
    subtotal: float = Field(ge=0)
    discount_amount: float = Field(default=0, ge=0)
    tax_amount: float = Field(default=0, ge=0)
    description: str | None = None


class InvoiceOut(ORMModel):
    id: int
    invoice_number: str
    student_id: int | None = None
    student_name: str | None = None
    membership_id: int | None = None
    issue_date: date
    due_date: date
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    paid_amount: float
    balance: float = 0.0
    currency: str
    status: PaymentStatus
    is_overdue: bool = False
    days_overdue: int = 0
    description: str | None = None


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: ExpenseCategory = ExpenseCategory.OTHER
    amount: float = Field(gt=0)
    currency: str = "TRY"
    expense_date: date | None = None
    method: PaymentMethod = PaymentMethod.TRANSFER
    vendor: str | None = None
    invoice_reference: str | None = None
    description: str | None = None
    is_recurring: bool = False


class ExpenseUpdate(BaseModel):
    title: str | None = None
    category: ExpenseCategory | None = None
    amount: float | None = None
    expense_date: date | None = None
    method: PaymentMethod | None = None
    vendor: str | None = None
    invoice_reference: str | None = None
    description: str | None = None
    is_recurring: bool | None = None


class ExpenseOut(ORMModel, ExpenseCreate):
    id: int
    expense_date: date


class DiscountBase(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    percentage: float | None = Field(default=None, ge=0, le=100)
    fixed_amount: float | None = Field(default=None, ge=0)
    valid_from: date
    valid_until: date
    max_uses: int | None = Field(default=None, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def _one_of(self):  # noqa: ANN201
        if self.percentage is None and self.fixed_amount is None:
            raise ValueError("Yüzde veya sabit tutar indiriminden biri girilmelidir.")
        return self


class DiscountOut(ORMModel, DiscountBase):
    id: int
    used_count: int = 0
    is_valid_now: bool = False


class FinanceSummary(BaseModel):
    """Finans panosu özeti."""

    period_start: date
    period_end: date
    currency: str = "TRY"
    total_income: float = 0.0
    total_expense: float = 0.0
    net_income: float = 0.0
    outstanding_total: float = 0.0
    overdue_total: float = 0.0
    overdue_count: int = 0
    collection_rate: float = 0.0
    revenue_per_student: float = 0.0
    active_student_count: int = 0
    income_by_method: dict[str, float] = Field(default_factory=dict)
    expense_by_category: dict[str, float] = Field(default_factory=dict)
    income_by_package: dict[str, float] = Field(default_factory=dict)
    monthly_series: list[dict] = Field(default_factory=list)
