"""Tüm ORM modellerini tek noktadan dışa aktarır.

Alembic'in `Base.metadata` üzerinden tüm tabloları görebilmesi için bu modülün
import edilmesi yeterlidir.
"""

from app.db.base import Base
from app.models.attendance import Attendance, AttendanceToken, StudentCard
from app.models.competition import (
    ClubRecord,
    Competition,
    CompetitionEntry,
    CompetitionEvent,
)
from app.models.enums import (
    AITaskKind,
    AITaskStatus,
    AttendanceMethod,
    AttendanceStatus,
    BackupStatus,
    BackupType,
    CompetitionLevel,
    CourseType,
    EnrollmentStatus,
    ExpenseCategory,
    Gender,
    LessonStatus,
    LessonType,
    MembershipStatus,
    NotificationSeverity,
    NotificationType,
    PackageType,
    PaymentMethod,
    PaymentStatus,
    PoolStatus,
    Stroke,
    StudentStatus,
    SwimLevel,
    TrainingStatus,
    TransactionDirection,
)
from app.models.facility import Holiday, Lane, Pool, PoolMaintenance, WaterQualityLog
from app.models.finance import (
    CashTransaction,
    Discount,
    Expense,
    Invoice,
    Payment,
)
from app.models.lesson import Lesson, LessonEnrollment, LessonSeries
from app.models.membership import Membership, MembershipFreeze, Package
from app.models.people import (
    Group,
    Guardian,
    Instructor,
    InstructorAvailability,
    InstructorCertificate,
    InstructorLeave,
    Student,
    StudentGuardian,
)
from app.models.performance import PerformanceRecord, PersonalBest, TrainingPlan
from app.models.hsp import (
    ConsentRecord,
    ConsentWithdrawal,
    NoticeVersion,
    ProviderEvidenceRecord,
    RightsReceipt,
)
from app.models.system import (
    AIProviderHealth,
    AITask,
    AppSetting,
    AuditLog,
    BackupRecord,
    CAIOFinding,
    KpiTarget,
    Notification,
    ReportTemplate,
    RestoreRecord,
    SystemEvent,
    TrainingProgress,
)
from app.models.user import LoginAttempt, Role, User, user_roles

__all__ = [
    "Base",
    # user
    "User",
    "Role",
    "user_roles",
    "LoginAttempt",
    # people
    "Student",
    "Guardian",
    "StudentGuardian",
    "Instructor",
    "Group",
    "InstructorCertificate",
    "InstructorAvailability",
    "InstructorLeave",
    # facility
    "Pool",
    "Lane",
    "PoolMaintenance",
    "WaterQualityLog",
    "Holiday",
    # lesson
    "Lesson",
    "LessonSeries",
    "LessonEnrollment",
    # attendance
    "Attendance",
    "AttendanceToken",
    "StudentCard",
    # membership
    "Package",
    "Membership",
    "MembershipFreeze",
    # finance
    "Invoice",
    "Payment",
    "Expense",
    "Discount",
    "CashTransaction",
    # performance
    "PerformanceRecord",
    "PersonalBest",
    "TrainingPlan",
    # competition
    "Competition",
    "CompetitionEvent",
    "CompetitionEntry",
    "ClubRecord",
    # system
    "AuditLog",
    "Notification",
    "AppSetting",
    "BackupRecord",
    "RestoreRecord",
    "AITask",
    "AIProviderHealth",
    "CAIOFinding",
    "KpiTarget",
    "TrainingProgress",
    "ReportTemplate",
    "SystemEvent",
    # enums
    "Gender",
    "SwimLevel",
    "StudentStatus",
    "LessonType",
    "LessonStatus",
    "EnrollmentStatus",
    "AttendanceStatus",
    "AttendanceMethod",
    "PackageType",
    "MembershipStatus",
    "PaymentMethod",
    "PaymentStatus",
    "TransactionDirection",
    "ExpenseCategory",
    "Stroke",
    "CourseType",
    "PoolStatus",
    "CompetitionLevel",
    "NotificationType",
    "NotificationSeverity",
    "AITaskStatus",
    "AITaskKind",
    "BackupType",
    "BackupStatus",
    "TrainingStatus",
    # --- HSP ---
    "RightsReceipt",
    "NoticeVersion",
    "ConsentRecord",
    "ConsentWithdrawal",
    "ProviderEvidenceRecord",
]
