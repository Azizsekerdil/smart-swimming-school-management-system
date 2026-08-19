"""Öğrenci, veli ve eğitmen modelleri / Student, guardian and instructor models.

KVKK / GDPR notu: Yalnızca operasyon için gerekli veriler tutulur. Sağlık notu
alanı serbest metindir ve `student:read_sensitive` izni olmadan API yanıtlarında
maskelenir.
"""

from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IntPKMixin, TimestampMixin
from app.models.enums import Gender, StudentStatus, SwimLevel

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.competition import CompetitionEntry
    from app.models.finance import Payment
    from app.models.lesson import Lesson, LessonEnrollment
    from app.models.membership import Membership
    from app.models.performance import PerformanceRecord
    from app.models.user import User


class Group(Base, IntPKMixin, TimestampMixin):
    """Öğrenci grubu (ör. 'Yıldızlar - Başlangıç Çocuk')."""

    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(400))
    level: Mapped[str] = mapped_column(
        String(30), default=SwimLevel.BEGINNER, nullable=False
    )
    min_age: Mapped[int | None] = mapped_column(Integer)
    max_age: Mapped[int | None] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(20), default="#0ea5e9", nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    default_instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL")
    )
    default_instructor: Mapped["Instructor | None"] = relationship(
        foreign_keys=[default_instructor_id]
    )
    students: Mapped[list["Student"]] = relationship(back_populates="group")


class Student(Base, IntPKMixin, TimestampMixin):
    """Öğrenci / sporcu."""

    __tablename__ = "students"
    __table_args__ = (
        Index("ix_students_name", "last_name", "first_name"),
        Index("ix_students_status_level", "status", "swim_level"),
    )

    student_number: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(
        String(20), default=Gender.UNSPECIFIED, nullable=False
    )
    photo_url: Mapped[str | None] = mapped_column(String(500))

    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    address: Mapped[str | None] = mapped_column(String(400))

    emergency_contact_name: Mapped[str | None] = mapped_column(String(160))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30))

    swim_level: Mapped[str] = mapped_column(
        String(30), default=SwimLevel.BEGINNER, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=StudentStatus.ACTIVE, nullable=False, index=True
    )
    registration_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    left_date: Mapped[date | None] = mapped_column(Date)

    group_id: Mapped[int | None] = mapped_column(
        ForeignKey("groups.id", ondelete="SET NULL")
    )
    primary_instructor_id: Mapped[int | None] = mapped_column(
        ForeignKey("instructors.id", ondelete="SET NULL")
    )

    # Operasyon için gerekli sağlık/özel ihtiyaç notları (hassas - RBAC korumalı)
    health_notes: Mapped[str | None] = mapped_column(Text)
    special_needs: Mapped[str | None] = mapped_column(Text)
    goals: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    # KVKK aydınlatma onayı
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_date: Mapped[date | None] = mapped_column(Date)

    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    user: Mapped["User | None"] = relationship(back_populates="student")

    group: Mapped[Group | None] = relationship(back_populates="students")
    primary_instructor: Mapped["Instructor | None"] = relationship(
        foreign_keys=[primary_instructor_id], back_populates="students"
    )
    guardians: Mapped[list["StudentGuardian"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["LessonEnrollment"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    attendances: Mapped[list["Attendance"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="student")
    performance_records: Mapped[list["PerformanceRecord"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    competition_entries: Mapped[list["CompetitionEntry"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def guardian_list(self) -> list["Guardian"]:
        """Bağlantı tablosunu atlayarak doğrudan veli nesnelerini döndürür."""
        return [link.guardian for link in self.guardians if link.guardian]

    @property
    def age(self) -> int | None:
        if not self.birth_date:
            return None
        today = date.today()
        return (
            today.year
            - self.birth_date.year
            - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Student {self.student_number} {self.full_name}>"


class Guardian(Base, IntPKMixin, TimestampMixin):
    """Veli. Bir velinin birden fazla öğrencisi olabilir."""

    __tablename__ = "guardians"

    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    relationship_type: Mapped[str] = mapped_column(
        String(40), default="parent", nullable=False
    )
    phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    secondary_phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    national_id_last4: Mapped[str | None] = mapped_column(
        String(4)
    )  # veri minimizasyonu
    address: Mapped[str | None] = mapped_column(String(400))
    occupation: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    user: Mapped["User | None"] = relationship(back_populates="guardian")

    students: Mapped[list["StudentGuardian"]] = relationship(
        back_populates="guardian", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def student_list(self) -> list[Student]:
        """Bağlantı tablosunu atlayarak doğrudan öğrenci nesnelerini döndürür."""
        return [link.student for link in self.students if link.student]


class StudentGuardian(Base, IntPKMixin):
    """Öğrenci-veli ilişkisi (çoktan çoğa + rol bilgisi)."""

    __tablename__ = "student_guardians"
    __table_args__ = (
        Index("ix_student_guardian_unique", "student_id", "guardian_id", unique=True),
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    guardian_id: Mapped[int] = mapped_column(
        ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    can_pickup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_billing_contact: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    student: Mapped[Student] = relationship(back_populates="guardians")
    guardian: Mapped[Guardian] = relationship(back_populates="students")


class Instructor(Base, IntPKMixin, TimestampMixin):
    """Eğitmen / antrenör."""

    __tablename__ = "instructors"

    employee_number: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(
        String(20), default=Gender.UNSPECIFIED, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500))

    title: Mapped[str | None] = mapped_column(String(120))  # ör. "Baş Antrenör"
    specialties: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    hire_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2))
    monthly_salary: Mapped[float | None] = mapped_column(Numeric(12, 2))
    max_weekly_hours: Mapped[int] = mapped_column(Integer, default=40, nullable=False)

    bio: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    user: Mapped["User | None"] = relationship(back_populates="instructor")

    students: Mapped[list[Student]] = relationship(
        foreign_keys=[Student.primary_instructor_id],
        back_populates="primary_instructor",
    )
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="instructor")
    certificates: Mapped[list["InstructorCertificate"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )
    availabilities: Mapped[list["InstructorAvailability"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )
    leaves: Mapped[list["InstructorLeave"]] = relationship(
        back_populates="instructor", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class InstructorCertificate(Base, IntPKMixin, TimestampMixin):
    """Eğitmen sertifikası (ör. TYF Antrenörlük, Cankurtaran, İlk Yardım)."""

    __tablename__ = "instructor_certificates"

    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructors.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(200))
    issued_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)
    document_url: Mapped[str | None] = mapped_column(String(500))

    instructor: Mapped[Instructor] = relationship(back_populates="certificates")

    @property
    def is_expired(self) -> bool:
        return bool(self.expiry_date and self.expiry_date < date.today())


class InstructorAvailability(Base, IntPKMixin):
    """Haftalık müsaitlik penceresi. weekday: 0=Pazartesi ... 6=Pazar."""

    __tablename__ = "instructor_availabilities"

    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructors.id", ondelete="CASCADE"), nullable=False
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    instructor: Mapped[Instructor] = relationship(back_populates="availabilities")


class InstructorLeave(Base, IntPKMixin, TimestampMixin):
    """Eğitmen izni / devamsızlığı."""

    __tablename__ = "instructor_leaves"

    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructors.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    leave_type: Mapped[str] = mapped_column(
        String(40), default="annual", nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(400))
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    instructor: Mapped[Instructor] = relationship(back_populates="leaves")
