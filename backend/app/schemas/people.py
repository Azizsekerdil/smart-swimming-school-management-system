"""Öğrenci, veli, eğitmen ve grup şemaları / People schemas."""

from __future__ import annotations

from datetime import date, time

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Gender, StudentStatus, SwimLevel
from app.schemas.common import Email, ORMModel


# ---------------------------------------------------------------------------
# Grup
# ---------------------------------------------------------------------------
class GroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    level: SwimLevel = SwimLevel.BEGINNER
    min_age: int | None = Field(default=None, ge=0, le=120)
    max_age: int | None = Field(default=None, ge=0, le=120)
    color: str = "#0ea5e9"
    capacity: int = Field(default=12, ge=1, le=100)
    is_active: bool = True
    default_instructor_id: int | None = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    level: SwimLevel | None = None
    min_age: int | None = None
    max_age: int | None = None
    color: str | None = None
    capacity: int | None = None
    is_active: bool | None = None
    default_instructor_id: int | None = None


class GroupOut(ORMModel, GroupBase):
    id: int
    student_count: int = 0


# ---------------------------------------------------------------------------
# Veli
# ---------------------------------------------------------------------------
class GuardianBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    relationship_type: str = Field(default="parent", max_length=40)
    phone: str = Field(min_length=5, max_length=30)
    secondary_phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    address: str | None = Field(default=None, max_length=400)
    occupation: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class GuardianCreate(GuardianBase):
    student_ids: list[int] = Field(default_factory=list)
    create_portal_user: bool = False


class GuardianUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    relationship_type: str | None = None
    phone: str | None = None
    secondary_phone: str | None = None
    email: Email | None = None
    address: str | None = None
    occupation: str | None = None
    notes: str | None = None


class GuardianLink(BaseModel):
    student_id: int
    is_primary: bool = True
    can_pickup: bool = True
    is_billing_contact: bool = True


class StudentBrief(ORMModel):
    id: int
    student_number: str
    first_name: str
    last_name: str
    full_name: str
    swim_level: str
    status: str
    age: int | None = None
    photo_url: str | None = None


class GuardianOut(ORMModel, GuardianBase):
    id: int
    full_name: str
    user_id: int | None = None
    is_demo: bool = False
    # ORM'de `students` bağlantı tablosu nesneleridir; şemaya modeldeki
    # `student_list` özelliği üzerinden doğrudan Student nesneleri gelir.
    students: list[StudentBrief] = Field(
        default_factory=list, validation_alias="student_list"
    )
    # Çıktıda esnek tip: veritabanındaki eski/dış kaynaklı kayıtlar okuma
    # isteğini düşürmemeli. Doğrulama giriş şemalarında yapılır.
    email: str | None = None


class GuardianBrief(ORMModel):
    id: int
    full_name: str
    phone: str
    relationship_type: str
    email: str | None = None


# ---------------------------------------------------------------------------
# Öğrenci
# ---------------------------------------------------------------------------
class StudentBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    gender: Gender = Gender.UNSPECIFIED
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    address: str | None = Field(default=None, max_length=400)
    emergency_contact_name: str | None = Field(default=None, max_length=160)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    swim_level: SwimLevel = SwimLevel.BEGINNER
    status: StudentStatus = StudentStatus.ACTIVE
    group_id: int | None = None
    primary_instructor_id: int | None = None
    goals: str | None = None
    notes: str | None = None
    consent_given: bool = False

    @field_validator("birth_date")
    @classmethod
    def _birth_not_future(cls, v: date | None) -> date | None:
        if v and v > date.today():
            raise ValueError("Doğum tarihi gelecekte olamaz.")
        return v


class StudentCreate(StudentBase):
    student_number: str | None = Field(default=None, max_length=30)
    registration_date: date | None = None
    health_notes: str | None = None
    special_needs: str | None = None
    guardian_ids: list[int] = Field(default_factory=list)


class StudentUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    gender: Gender | None = None
    phone: str | None = None
    email: Email | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    swim_level: SwimLevel | None = None
    status: StudentStatus | None = None
    group_id: int | None = None
    primary_instructor_id: int | None = None
    goals: str | None = None
    notes: str | None = None
    health_notes: str | None = None
    special_needs: str | None = None
    consent_given: bool | None = None
    photo_url: str | None = None


class InstructorBrief(ORMModel):
    id: int
    employee_number: str
    full_name: str
    title: str | None = None
    photo_url: str | None = None


class StudentOut(ORMModel, StudentBase):
    id: int
    student_number: str
    full_name: str
    email: str | None = None  # çıktıda esnek (bkz. GuardianOut notu)
    age: int | None = None
    registration_date: date
    left_date: date | None = None
    photo_url: str | None = None
    is_demo: bool = False
    user_id: int | None = None
    # Hassas alanlar: yalnızca student:read_sensitive izniyle doldurulur
    health_notes: str | None = None
    special_needs: str | None = None
    # bkz. GuardianOut.students - bağlantı tablosu yerine çözümlenmiş liste
    guardians: list[GuardianBrief] = Field(
        default_factory=list, validation_alias="guardian_list"
    )
    group: GroupOut | None = None
    primary_instructor: InstructorBrief | None = None


class StudentDetail(StudentOut):
    """Detay ekranı için ek özet bilgiler."""

    active_membership: dict | None = None
    attendance_rate: float | None = None
    total_lessons: int = 0
    outstanding_balance: float = 0.0
    personal_best_count: int = 0


class StudentFilter(BaseModel):
    q: str | None = None
    status: StudentStatus | None = None
    swim_level: SwimLevel | None = None
    group_id: int | None = None
    instructor_id: int | None = None
    min_age: int | None = None
    max_age: int | None = None
    registered_after: date | None = None
    registered_before: date | None = None
    include_demo: bool = True


# ---------------------------------------------------------------------------
# Eğitmen
# ---------------------------------------------------------------------------
class CertificateBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    issued_date: date | None = None
    expiry_date: date | None = None
    document_url: str | None = None


class CertificateCreate(CertificateBase):
    pass


class CertificateOut(ORMModel, CertificateBase):
    id: int
    instructor_id: int
    is_expired: bool = False


class AvailabilityBase(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v: time, info):  # noqa: ANN001
        start = info.data.get("start_time")
        if start and v <= start:
            raise ValueError("Bitiş saati başlangıçtan sonra olmalıdır.")
        return v


class AvailabilityOut(ORMModel, AvailabilityBase):
    id: int
    instructor_id: int


class LeaveBase(BaseModel):
    start_date: date
    end_date: date
    leave_type: str = "annual"
    reason: str | None = None
    approved: bool = False


class LeaveOut(ORMModel, LeaveBase):
    id: int
    instructor_id: int


class InstructorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    gender: Gender = Gender.UNSPECIFIED
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    title: str | None = Field(default=None, max_length=120)
    specialties: list[str] = Field(default_factory=list)
    hire_date: date | None = None
    is_active: bool = True
    max_weekly_hours: int = Field(default=40, ge=1, le=80)
    bio: str | None = None
    notes: str | None = None


class InstructorCreate(InstructorBase):
    employee_number: str | None = Field(default=None, max_length=30)
    hourly_rate: float | None = Field(default=None, ge=0)
    monthly_salary: float | None = Field(default=None, ge=0)
    availabilities: list[AvailabilityBase] = Field(default_factory=list)
    create_portal_user: bool = False
    portal_role_code: str | None = None


class InstructorUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    gender: Gender | None = None
    phone: str | None = None
    email: Email | None = None
    title: str | None = None
    specialties: list[str] | None = None
    hire_date: date | None = None
    is_active: bool | None = None
    max_weekly_hours: int | None = None
    hourly_rate: float | None = None
    monthly_salary: float | None = None
    bio: str | None = None
    notes: str | None = None
    photo_url: str | None = None


class InstructorOut(ORMModel, InstructorBase):
    id: int
    employee_number: str
    full_name: str
    email: str | None = None  # çıktıda esnek (bkz. GuardianOut notu)
    photo_url: str | None = None
    is_demo: bool = False
    user_id: int | None = None
    # Ücret bilgisi yalnızca finance/hr izniyle doldurulur
    hourly_rate: float | None = None
    monthly_salary: float | None = None
    certificates: list[CertificateOut] = []
    availabilities: list[AvailabilityOut] = []


class InstructorDetail(InstructorOut):
    student_count: int = 0
    weekly_lesson_count: int = 0
    weekly_hours: float = 0.0
    upcoming_lessons: int = 0
    attendance_rate: float | None = None
    leaves: list[LeaveOut] = []


class InstructorWorkload(BaseModel):
    instructor_id: int
    full_name: str
    lesson_count: int
    total_hours: float
    student_count: int
    occupancy_rate: float
    cancellation_rate: float
    private_ratio: float
