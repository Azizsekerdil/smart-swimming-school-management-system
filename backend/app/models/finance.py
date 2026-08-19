"""Finans modelleri / Finance models: fatura, ödeme, gider, indirim."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import (
    ExpenseCategory,
    PaymentMethod,
    PaymentStatus,
    TransactionDirection,
)

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.people import Student


class Invoice(Base, IntPKMixin, TimestampMixin):
    """Fatura / borç kaydı."""

    __tablename__ = "invoices"
    __table_args__ = (Index("ix_invoice_student_status", "student_id", "status"),)

    invoice_number: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )
    membership_id: Mapped[int | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="SET NULL")
    )

    issue_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    discount_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    total_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    paid_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default=PaymentStatus.PENDING, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["Student | None"] = relationship()
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice")

    @property
    def balance(self) -> float:
        return float(self.total_amount) - float(self.paid_amount)

    @property
    def is_overdue(self) -> bool:
        return self.balance > 0.005 and self.due_date < date.today()

    @property
    def days_overdue(self) -> int:
        return max(0, (date.today() - self.due_date).days) if self.is_overdue else 0


class Payment(Base, IntPKMixin, TimestampMixin):
    """Tahsilat kaydı."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payment_date_method", "payment_date", "method"),
        Index("ix_payment_student_date", "student_id", "payment_date"),
    )

    receipt_number: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.id", ondelete="SET NULL"), index=True
    )
    membership_id: Mapped[int | None] = mapped_column(
        ForeignKey("memberships.id", ondelete="SET NULL")
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"), index=True
    )

    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.CASH, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PaymentStatus.PAID, nullable=False, index=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    reference: Mapped[str | None] = mapped_column(String(120))  # POS/dekont no
    description: Mapped[str | None] = mapped_column(String(400))
    refunded_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0, nullable=False
    )
    refund_reason: Mapped[str | None] = mapped_column(String(300))

    received_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student: Mapped["Student | None"] = relationship(back_populates="payments")
    membership: Mapped["Membership | None"] = relationship(back_populates="payments")
    invoice: Mapped[Invoice | None] = relationship(back_populates="payments")

    @property
    def net_amount(self) -> float:
        return float(self.amount) - float(self.refunded_amount)


class Expense(Base, IntPKMixin, TimestampMixin):
    """Gider kaydı."""

    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expense_date_category", "expense_date", "category"),)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(
        String(30), default=ExpenseCategory.OTHER, nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.TRANSFER, nullable=False
    )
    vendor: Mapped[str | None] = mapped_column(String(200))
    invoice_reference: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Discount(Base, IntPKMixin, TimestampMixin):
    """İndirim / kampanya tanımı."""

    __tablename__ = "discounts"

    code: Mapped[str] = mapped_column(
        String(40), unique=True, index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    percentage: Mapped[float | None] = mapped_column(Numeric(5, 2))
    fixed_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def is_valid_now(self) -> bool:
        today = date.today()
        if not self.is_active or not (self.valid_from <= today <= self.valid_until):
            return False
        return self.max_uses is None or self.used_count < self.max_uses


class CashTransaction(Base, IntPKMixin):
    """Kasa hareketi - nakit/banka/POS bakiyesi izlemek için birleşik defter."""

    __tablename__ = "cash_transactions"

    direction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.CASH, nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(400))
    payment_id: Mapped[int | None] = mapped_column(
        ForeignKey("payments.id", ondelete="SET NULL")
    )
    expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("expenses.id", ondelete="SET NULL")
    )

    @staticmethod
    def direction_options() -> list[str]:
        return [d.value for d in TransactionDirection]
