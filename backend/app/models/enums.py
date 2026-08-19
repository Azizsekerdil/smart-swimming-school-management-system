"""Alan sabitleri / Domain enumerations.

Tümü StrEnum: veritabanında okunabilir metin olarak saklanır, JSON'a doğrudan
serileştirilebilir ve i18n etiketleri ayrı tutulur.
"""

from __future__ import annotations

from enum import StrEnum


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"
    UNSPECIFIED = "unspecified"


class SwimLevel(StrEnum):
    """Yüzme seviyeleri."""

    BEGINNER = "beginner"  # Başlangıç
    ELEMENTARY = "elementary"  # Temel
    INTERMEDIATE = "intermediate"  # Orta
    ADVANCED = "advanced"  # İleri
    COMPETITIVE = "competitive"  # Yarışma
    ELITE = "elite"  # Elit


class StudentStatus(StrEnum):
    ACTIVE = "active"
    PASSIVE = "passive"
    TRIAL = "trial"
    FROZEN = "frozen"
    LEFT = "left"


class LessonType(StrEnum):
    GROUP = "group"  # Grup dersi
    PRIVATE = "private"  # Özel ders
    KIDS = "kids"  # Çocuk yüzme
    BABY = "baby"  # Bebek yüzme
    ADULT = "adult"  # Yetişkin yüzme
    BEGINNER = "beginner"  # Başlangıç
    INTERMEDIATE = "intermediate"  # Orta
    ADVANCED = "advanced"  # İleri
    COMPETITION_TEAM = "competition_team"  # Yarışma takımı
    ADAPTIVE = "adaptive"  # Adaptif yüzme
    CONDITIONING = "conditioning"  # Kondisyon
    TRIAL = "trial"  # Deneme dersi
    MAKEUP = "makeup"  # Telafi dersi


class LessonStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class EnrollmentStatus(StrEnum):
    ENROLLED = "enrolled"
    WAITLIST = "waitlist"
    CANCELLED = "cancelled"


class AttendanceStatus(StrEnum):
    PRESENT = "present"  # Geldi
    ABSENT = "absent"  # Gelmedi
    LATE = "late"  # Geç Geldi
    EXCUSED = "excused"  # Mazeretli
    CANCELLED = "cancelled"  # İptal
    MAKEUP = "makeup"  # Telafi


class AttendanceMethod(StrEnum):
    MANUAL = "manual"
    QR = "qr"
    CARD = "card"
    RFID = "rfid"
    NFC = "nfc"


class PackageType(StrEnum):
    LESSON_PACK = "lesson_pack"  # N ders
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"  # 3 aylık
    BIANNUAL = "biannual"  # 6 aylık
    ANNUAL = "annual"
    PRIVATE_PACK = "private_pack"
    TRIAL = "trial"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    FROZEN = "frozen"
    CANCELLED = "cancelled"
    PENDING = "pending"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"  # POS
    TRANSFER = "transfer"  # Havale/EFT
    ONLINE = "online"
    OTHER = "other"


class PaymentStatus(StrEnum):
    PAID = "paid"
    PENDING = "pending"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class TransactionDirection(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"


class ExpenseCategory(StrEnum):
    SALARY = "salary"
    RENT = "rent"
    UTILITIES = "utilities"  # Elektrik/su/doğalgaz
    CHEMICALS = "chemicals"  # Havuz kimyasalları
    MAINTENANCE = "maintenance"
    EQUIPMENT = "equipment"
    MARKETING = "marketing"
    TAX = "tax"
    INSURANCE = "insurance"
    OTHER = "other"


class Stroke(StrEnum):
    """Yüzme stilleri."""

    FREESTYLE = "freestyle"  # Serbest
    BACKSTROKE = "backstroke"  # Sırtüstü
    BREASTSTROKE = "breaststroke"  # Kurbağalama
    BUTTERFLY = "butterfly"  # Kelebek
    MEDLEY = "medley"  # Karışık


class CourseType(StrEnum):
    SHORT = "short"  # 25 m havuz
    LONG = "long"  # 50 m havuz


class PoolStatus(StrEnum):
    OPERATIONAL = "operational"
    MAINTENANCE = "maintenance"
    CLOSED = "closed"


class CompetitionLevel(StrEnum):
    CLUB = "club"
    LOCAL = "local"
    REGIONAL = "regional"
    NATIONAL = "national"
    INTERNATIONAL = "international"


class NotificationType(StrEnum):
    MEMBERSHIP_EXPIRING = "membership_expiring"
    PAYMENT_OVERDUE = "payment_overdue"
    LESSON_CANCELLED = "lesson_cancelled"
    INSTRUCTOR_LEAVE = "instructor_leave"
    POOL_MAINTENANCE = "pool_maintenance"
    PERFORMANCE_DROP = "performance_drop"
    COMPETITION_UPCOMING = "competition_upcoming"
    AI_REPORT_READY = "ai_report_ready"
    BACKUP_RESULT = "backup_result"
    SYSTEM = "system"
    TRIAL_LESSON = "trial_lesson"
    NEW_REGISTRATION = "new_registration"


class NotificationSeverity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class AITaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AITaskKind(StrEnum):
    ANALYSIS = "analysis"
    CHAT = "chat"
    DEVELOPER = "developer"
    CAIO = "caio"
    REPORT = "report"
    HEALTH_CHECK = "health_check"


class BackupType(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    PRE_UPDATE = "pre_update"
    PRE_MIGRATION = "pre_migration"
    SAFETY = "safety"  # Restore öncesi güvenlik yedeği


class BackupStatus(StrEnum):
    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class TrainingStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Etiketler (TR/EN) - UI ve raporlar için
# ---------------------------------------------------------------------------
ENUM_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "gender": {
        "female": {"tr": "Kadın", "en": "Female"},
        "male": {"tr": "Erkek", "en": "Male"},
        "unspecified": {"tr": "Belirtilmemiş", "en": "Unspecified"},
    },
    "swim_level": {
        "beginner": {"tr": "Başlangıç", "en": "Beginner"},
        "elementary": {"tr": "Temel", "en": "Elementary"},
        "intermediate": {"tr": "Orta", "en": "Intermediate"},
        "advanced": {"tr": "İleri", "en": "Advanced"},
        "competitive": {"tr": "Yarışma", "en": "Competitive"},
        "elite": {"tr": "Elit", "en": "Elite"},
    },
    "student_status": {
        "active": {"tr": "Aktif", "en": "Active"},
        "passive": {"tr": "Pasif", "en": "Passive"},
        "trial": {"tr": "Deneme", "en": "Trial"},
        "frozen": {"tr": "Donduruldu", "en": "Frozen"},
        "left": {"tr": "Ayrıldı", "en": "Left"},
    },
    "lesson_type": {
        "group": {"tr": "Grup Dersi", "en": "Group Lesson"},
        "private": {"tr": "Özel Ders", "en": "Private Lesson"},
        "kids": {"tr": "Çocuk Yüzme", "en": "Kids Swimming"},
        "baby": {"tr": "Bebek Yüzme", "en": "Baby Swimming"},
        "adult": {"tr": "Yetişkin Yüzme", "en": "Adult Swimming"},
        "beginner": {"tr": "Başlangıç", "en": "Beginner"},
        "intermediate": {"tr": "Orta Seviye", "en": "Intermediate"},
        "advanced": {"tr": "İleri Seviye", "en": "Advanced"},
        "competition_team": {"tr": "Yarışma Takımı", "en": "Competition Team"},
        "adaptive": {"tr": "Adaptif Yüzme", "en": "Adaptive Swimming"},
        "conditioning": {"tr": "Kondisyon", "en": "Conditioning"},
        "trial": {"tr": "Deneme Dersi", "en": "Trial Lesson"},
        "makeup": {"tr": "Telafi Dersi", "en": "Make-up Lesson"},
    },
    "attendance_status": {
        "present": {"tr": "Geldi", "en": "Present"},
        "absent": {"tr": "Gelmedi", "en": "Absent"},
        "late": {"tr": "Geç Geldi", "en": "Late"},
        "excused": {"tr": "Mazeretli", "en": "Excused"},
        "cancelled": {"tr": "İptal", "en": "Cancelled"},
        "makeup": {"tr": "Telafi", "en": "Make-up"},
    },
    "stroke": {
        "freestyle": {"tr": "Serbest", "en": "Freestyle"},
        "backstroke": {"tr": "Sırtüstü", "en": "Backstroke"},
        "breaststroke": {"tr": "Kurbağalama", "en": "Breaststroke"},
        "butterfly": {"tr": "Kelebek", "en": "Butterfly"},
        "medley": {"tr": "Karışık", "en": "Medley"},
    },
    "payment_method": {
        "cash": {"tr": "Nakit", "en": "Cash"},
        "card": {"tr": "Kredi Kartı (POS)", "en": "Card (POS)"},
        "transfer": {"tr": "Havale / EFT", "en": "Bank Transfer"},
        "online": {"tr": "Online Ödeme", "en": "Online Payment"},
        "other": {"tr": "Diğer", "en": "Other"},
    },
    "payment_status": {
        "paid": {"tr": "Ödendi", "en": "Paid"},
        "pending": {"tr": "Bekliyor", "en": "Pending"},
        "partial": {"tr": "Kısmi Ödendi", "en": "Partially Paid"},
        "overdue": {"tr": "Gecikmiş", "en": "Overdue"},
        "refunded": {"tr": "İade Edildi", "en": "Refunded"},
        "cancelled": {"tr": "İptal", "en": "Cancelled"},
    },
    "membership_status": {
        "active": {"tr": "Aktif", "en": "Active"},
        "expired": {"tr": "Süresi Doldu", "en": "Expired"},
        "frozen": {"tr": "Dondurulmuş", "en": "Frozen"},
        "cancelled": {"tr": "İptal", "en": "Cancelled"},
        "pending": {"tr": "Beklemede", "en": "Pending"},
    },
    "pool_status": {
        "operational": {"tr": "Faal", "en": "Operational"},
        "maintenance": {"tr": "Bakımda", "en": "Under Maintenance"},
        "closed": {"tr": "Kapalı", "en": "Closed"},
    },
}


def label(group: str, value: str, lang: str = "tr") -> str:
    """Enum değerinin yerelleştirilmiş etiketini döndürür."""
    return ENUM_LABELS.get(group, {}).get(value, {}).get(lang, value)
