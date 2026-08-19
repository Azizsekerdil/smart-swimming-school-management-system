"""RBAC - Rol Bazlı Erişim Kontrolü / Role Based Access Control.

Tasarım: `kaynak:eylem` biçiminde ince taneli izinler tanımlanır, roller bu
izinlerin bir kümesine sahiptir. Kullanıcı birden fazla role sahip olabilir;
efektif izin kümesi rollerin birleşimidir.

Design: fine-grained `resource:action` permissions; roles hold a set of them.
A user may hold multiple roles - the effective set is the union.
"""

from __future__ import annotations

from enum import StrEnum


class RoleCode(StrEnum):
    """Sistemdeki tüm rol kodları."""

    # --- Yönetim / Management ---
    SYSTEM_ADMIN = "system_admin"
    SCHOOL_DIRECTOR = "school_director"
    OPERATIONS_MANAGER = "operations_manager"
    FINANCE = "finance"
    HR = "hr"
    RECEPTION = "reception"
    SALES_MARKETING = "sales_marketing"

    # --- Eğitim / Education ---
    HEAD_COACH = "head_coach"
    SWIM_COACH = "swim_coach"
    SWIM_INSTRUCTOR = "swim_instructor"
    KIDS_INSTRUCTOR = "kids_instructor"
    BABY_INSTRUCTOR = "baby_instructor"
    PRIVATE_INSTRUCTOR = "private_instructor"
    ADAPTIVE_INSTRUCTOR = "adaptive_instructor"
    CONDITIONING_COACH = "conditioning_coach"

    # --- Diğer / Other ---
    LIFEGUARD = "lifeguard"
    POOL_TECHNICIAN = "pool_technician"
    MEDICAL_STAFF = "medical_staff"
    ATHLETE = "athlete"
    STUDENT = "student"
    PARENT = "parent"


ROLE_LABELS: dict[str, dict[str, str]] = {
    RoleCode.SYSTEM_ADMIN: {"tr": "Sistem Yöneticisi", "en": "System Administrator"},
    RoleCode.SCHOOL_DIRECTOR: {"tr": "Yüzme Okulu Müdürü", "en": "School Director"},
    RoleCode.OPERATIONS_MANAGER: {"tr": "Operasyon Müdürü", "en": "Operations Manager"},
    RoleCode.FINANCE: {"tr": "Finans / Muhasebe", "en": "Finance / Accounting"},
    RoleCode.HR: {"tr": "İnsan Kaynakları", "en": "Human Resources"},
    RoleCode.RECEPTION: {"tr": "Resepsiyon", "en": "Reception"},
    RoleCode.SALES_MARKETING: {"tr": "Satış / Pazarlama", "en": "Sales / Marketing"},
    RoleCode.HEAD_COACH: {"tr": "Baş Antrenör", "en": "Head Coach"},
    RoleCode.SWIM_COACH: {"tr": "Yüzme Antrenörü", "en": "Swimming Coach"},
    RoleCode.SWIM_INSTRUCTOR: {"tr": "Yüzme Eğitmeni", "en": "Swimming Instructor"},
    RoleCode.KIDS_INSTRUCTOR: {
        "tr": "Çocuk Yüzme Eğitmeni",
        "en": "Kids Swimming Instructor",
    },
    RoleCode.BABY_INSTRUCTOR: {
        "tr": "Bebek Yüzme Eğitmeni",
        "en": "Baby Swimming Instructor",
    },
    RoleCode.PRIVATE_INSTRUCTOR: {
        "tr": "Özel Ders Eğitmeni",
        "en": "Private Lesson Instructor",
    },
    RoleCode.ADAPTIVE_INSTRUCTOR: {
        "tr": "Adaptif Yüzme Eğitmeni",
        "en": "Adaptive Swimming Instructor",
    },
    RoleCode.CONDITIONING_COACH: {
        "tr": "Kondisyon / Performans Antrenörü",
        "en": "Conditioning Coach",
    },
    RoleCode.LIFEGUARD: {"tr": "Cankurtaran", "en": "Lifeguard"},
    RoleCode.POOL_TECHNICIAN: {"tr": "Havuz Teknik Personeli", "en": "Pool Technician"},
    RoleCode.MEDICAL_STAFF: {
        "tr": "Sağlık / İlk Yardım Personeli",
        "en": "Medical Staff",
    },
    RoleCode.ATHLETE: {"tr": "Sporcu", "en": "Athlete"},
    RoleCode.STUDENT: {"tr": "Öğrenci", "en": "Student"},
    RoleCode.PARENT: {"tr": "Veli", "en": "Parent"},
}

# Personel sayılan roller (eğitmen kaydı açılabilir)
STAFF_ROLES = {
    RoleCode.HEAD_COACH,
    RoleCode.SWIM_COACH,
    RoleCode.SWIM_INSTRUCTOR,
    RoleCode.KIDS_INSTRUCTOR,
    RoleCode.BABY_INSTRUCTOR,
    RoleCode.PRIVATE_INSTRUCTOR,
    RoleCode.ADAPTIVE_INSTRUCTOR,
    RoleCode.CONDITIONING_COACH,
    RoleCode.LIFEGUARD,
    RoleCode.POOL_TECHNICIAN,
    RoleCode.MEDICAL_STAFF,
}


class Perm(StrEnum):
    """İzin kodları - `kaynak:eylem` biçiminde."""

    # Öğrenci
    STUDENT_READ = "student:read"
    STUDENT_WRITE = "student:write"
    STUDENT_DELETE = "student:delete"
    STUDENT_READ_SENSITIVE = "student:read_sensitive"  # sağlık notu vb.

    # Veli
    GUARDIAN_READ = "guardian:read"
    GUARDIAN_WRITE = "guardian:write"
    GUARDIAN_DELETE = "guardian:delete"

    # Eğitmen
    INSTRUCTOR_READ = "instructor:read"
    INSTRUCTOR_WRITE = "instructor:write"
    INSTRUCTOR_DELETE = "instructor:delete"

    # Havuz / kulvar
    POOL_READ = "pool:read"
    POOL_WRITE = "pool:write"
    POOL_DELETE = "pool:delete"
    POOL_MAINTENANCE = "pool:maintenance"

    # Ders / takvim
    LESSON_READ = "lesson:read"
    LESSON_WRITE = "lesson:write"
    LESSON_DELETE = "lesson:delete"
    LESSON_SCHEDULE = "lesson:schedule"

    # Yoklama
    ATTENDANCE_READ = "attendance:read"
    ATTENDANCE_WRITE = "attendance:write"

    # Üyelik
    MEMBERSHIP_READ = "membership:read"
    MEMBERSHIP_WRITE = "membership:write"
    MEMBERSHIP_DELETE = "membership:delete"

    # Finans
    FINANCE_READ = "finance:read"
    FINANCE_WRITE = "finance:write"
    FINANCE_DELETE = "finance:delete"

    # Performans
    PERFORMANCE_READ = "performance:read"
    PERFORMANCE_WRITE = "performance:write"

    # Yarışma
    COMPETITION_READ = "competition:read"
    COMPETITION_WRITE = "competition:write"

    # Rapor / istatistik
    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"
    STATISTICS_READ = "statistics:read"
    KPI_WRITE = "kpi:write"

    # AI
    AI_USE = "ai:use"
    AI_CONFIGURE = "ai:configure"
    AI_DEVELOPER = "ai:developer"
    AI_CAIO = "ai:caio"

    # Sistem
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    ROLE_MANAGE = "role:manage"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    AUDIT_READ = "audit:read"
    BACKUP_READ = "backup:read"
    BACKUP_CREATE = "backup:create"
    BACKUP_RESTORE = "backup:restore"
    NOTIFICATION_READ = "notification:read"
    NOTIFICATION_SEND = "notification:send"
    SYSTEM_HEALTH = "system:health"

    # Portal (kendi verisi)
    SELF_PORTAL = "self:portal"


ALL_PERMISSIONS: list[str] = [p.value for p in Perm]

# --- Yeniden kullanılabilir izin demetleri ---
_READ_ONLY_OPERATIONS = {
    Perm.STUDENT_READ,
    Perm.GUARDIAN_READ,
    Perm.INSTRUCTOR_READ,
    Perm.POOL_READ,
    Perm.LESSON_READ,
    Perm.ATTENDANCE_READ,
}

_INSTRUCTOR_BASE = {
    Perm.STUDENT_READ,
    Perm.GUARDIAN_READ,
    Perm.INSTRUCTOR_READ,
    Perm.POOL_READ,
    Perm.LESSON_READ,
    Perm.ATTENDANCE_READ,
    Perm.ATTENDANCE_WRITE,
    Perm.PERFORMANCE_READ,
    Perm.PERFORMANCE_WRITE,
    Perm.COMPETITION_READ,
    Perm.REPORT_READ,
    Perm.STATISTICS_READ,
    Perm.AI_USE,
    Perm.NOTIFICATION_READ,
    Perm.SELF_PORTAL,
}

_MANAGER_FULL = set(Perm) - {
    Perm.AI_DEVELOPER,
    Perm.ROLE_MANAGE,
    Perm.USER_DELETE,
    Perm.BACKUP_RESTORE,
}

# ---------------------------------------------------------------------------
# Rol -> izin haritası
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, set[str]] = {
    # Sistem yöneticisi: her şey
    RoleCode.SYSTEM_ADMIN: set(Perm),
    # Okul müdürü: operasyonel her şey (yamayı uygulayan AI geliştirici hariç)
    RoleCode.SCHOOL_DIRECTOR: _MANAGER_FULL | {Perm.BACKUP_RESTORE, Perm.AI_CAIO},
    # Operasyon müdürü: eğitim/operasyon tam, finans salt okunur
    RoleCode.OPERATIONS_MANAGER: {
        Perm.STUDENT_READ,
        Perm.STUDENT_WRITE,
        Perm.GUARDIAN_READ,
        Perm.GUARDIAN_WRITE,
        Perm.INSTRUCTOR_READ,
        Perm.INSTRUCTOR_WRITE,
        Perm.POOL_READ,
        Perm.POOL_WRITE,
        Perm.POOL_MAINTENANCE,
        Perm.LESSON_READ,
        Perm.LESSON_WRITE,
        Perm.LESSON_SCHEDULE,
        Perm.LESSON_DELETE,
        Perm.ATTENDANCE_READ,
        Perm.ATTENDANCE_WRITE,
        Perm.MEMBERSHIP_READ,
        Perm.MEMBERSHIP_WRITE,
        Perm.FINANCE_READ,
        Perm.PERFORMANCE_READ,
        Perm.PERFORMANCE_WRITE,
        Perm.COMPETITION_READ,
        Perm.COMPETITION_WRITE,
        Perm.REPORT_READ,
        Perm.REPORT_EXPORT,
        Perm.STATISTICS_READ,
        Perm.KPI_WRITE,
        Perm.AI_USE,
        Perm.NOTIFICATION_READ,
        Perm.NOTIFICATION_SEND,
        Perm.SETTINGS_READ,
        Perm.BACKUP_READ,
        Perm.BACKUP_CREATE,
        Perm.SYSTEM_HEALTH,
        Perm.SELF_PORTAL,
    },
    # Finans / muhasebe
    RoleCode.FINANCE: {
        Perm.STUDENT_READ,
        Perm.GUARDIAN_READ,
        Perm.INSTRUCTOR_READ,
        Perm.MEMBERSHIP_READ,
        Perm.MEMBERSHIP_WRITE,
        Perm.FINANCE_READ,
        Perm.FINANCE_WRITE,
        Perm.FINANCE_DELETE,
        Perm.REPORT_READ,
        Perm.REPORT_EXPORT,
        Perm.STATISTICS_READ,
        Perm.AI_USE,
        Perm.NOTIFICATION_READ,
        Perm.SELF_PORTAL,
    },
    # İnsan kaynakları
    RoleCode.HR: {
        Perm.INSTRUCTOR_READ,
        Perm.INSTRUCTOR_WRITE,
        Perm.INSTRUCTOR_DELETE,
        Perm.USER_READ,
        Perm.USER_WRITE,
        Perm.LESSON_READ,
        Perm.ATTENDANCE_READ,
        Perm.REPORT_READ,
        Perm.REPORT_EXPORT,
        Perm.STATISTICS_READ,
        Perm.AI_USE,
        Perm.NOTIFICATION_READ,
        Perm.SELF_PORTAL,
    },
    # Resepsiyon: günlük operasyon
    RoleCode.RECEPTION: {
        Perm.STUDENT_READ,
        Perm.STUDENT_WRITE,
        Perm.GUARDIAN_READ,
        Perm.GUARDIAN_WRITE,
        Perm.INSTRUCTOR_READ,
        Perm.POOL_READ,
        Perm.LESSON_READ,
        Perm.LESSON_WRITE,
        Perm.LESSON_SCHEDULE,
        Perm.ATTENDANCE_READ,
        Perm.ATTENDANCE_WRITE,
        Perm.MEMBERSHIP_READ,
        Perm.MEMBERSHIP_WRITE,
        Perm.FINANCE_READ,
        Perm.FINANCE_WRITE,
        Perm.REPORT_READ,
        Perm.NOTIFICATION_READ,
        Perm.AI_USE,
        Perm.SELF_PORTAL,
    },
    # Satış / pazarlama
    RoleCode.SALES_MARKETING: {
        Perm.STUDENT_READ,
        Perm.STUDENT_WRITE,
        Perm.GUARDIAN_READ,
        Perm.GUARDIAN_WRITE,
        Perm.MEMBERSHIP_READ,
        Perm.MEMBERSHIP_WRITE,
        Perm.FINANCE_READ,
        Perm.REPORT_READ,
        Perm.REPORT_EXPORT,
        Perm.STATISTICS_READ,
        Perm.NOTIFICATION_READ,
        Perm.NOTIFICATION_SEND,
        Perm.AI_USE,
        Perm.SELF_PORTAL,
    },
    # Baş antrenör: eğitim tarafının yöneticisi
    RoleCode.HEAD_COACH: _INSTRUCTOR_BASE
    | {
        Perm.INSTRUCTOR_WRITE,
        Perm.LESSON_WRITE,
        Perm.LESSON_SCHEDULE,
        Perm.LESSON_DELETE,
        Perm.COMPETITION_WRITE,
        Perm.REPORT_EXPORT,
        Perm.KPI_WRITE,
        Perm.STUDENT_WRITE,
        Perm.STUDENT_READ_SENSITIVE,
        Perm.NOTIFICATION_SEND,
    },
    RoleCode.SWIM_COACH: _INSTRUCTOR_BASE | {Perm.COMPETITION_WRITE, Perm.LESSON_WRITE},
    RoleCode.SWIM_INSTRUCTOR: set(_INSTRUCTOR_BASE),
    RoleCode.KIDS_INSTRUCTOR: set(_INSTRUCTOR_BASE),
    RoleCode.BABY_INSTRUCTOR: set(_INSTRUCTOR_BASE),
    RoleCode.PRIVATE_INSTRUCTOR: set(_INSTRUCTOR_BASE),
    RoleCode.ADAPTIVE_INSTRUCTOR: _INSTRUCTOR_BASE | {Perm.STUDENT_READ_SENSITIVE},
    RoleCode.CONDITIONING_COACH: set(_INSTRUCTOR_BASE),
    # Cankurtaran: havuz durumu + o anki dersler
    RoleCode.LIFEGUARD: _READ_ONLY_OPERATIONS
    | {
        Perm.ATTENDANCE_READ,
        Perm.NOTIFICATION_READ,
        Perm.SELF_PORTAL,
    },
    # Havuz teknik personeli
    RoleCode.POOL_TECHNICIAN: {
        Perm.POOL_READ,
        Perm.POOL_WRITE,
        Perm.POOL_MAINTENANCE,
        Perm.LESSON_READ,
        Perm.NOTIFICATION_READ,
        Perm.SYSTEM_HEALTH,
        Perm.SELF_PORTAL,
    },
    # Sağlık personeli: yalnızca operasyonel sağlık notları
    RoleCode.MEDICAL_STAFF: {
        Perm.STUDENT_READ,
        Perm.STUDENT_READ_SENSITIVE,
        Perm.GUARDIAN_READ,
        Perm.LESSON_READ,
        Perm.ATTENDANCE_READ,
        Perm.NOTIFICATION_READ,
        Perm.NOTIFICATION_SEND,
        Perm.SELF_PORTAL,
    },
    # Sporcu / öğrenci: yalnızca kendi verisi (satır bazlı filtre ayrıca uygulanır)
    RoleCode.ATHLETE: {
        Perm.SELF_PORTAL,
        Perm.LESSON_READ,
        Perm.ATTENDANCE_READ,
        Perm.PERFORMANCE_READ,
        Perm.COMPETITION_READ,
        Perm.NOTIFICATION_READ,
    },
    RoleCode.STUDENT: {
        Perm.SELF_PORTAL,
        Perm.LESSON_READ,
        Perm.ATTENDANCE_READ,
        Perm.PERFORMANCE_READ,
        Perm.NOTIFICATION_READ,
    },
    # Veli: çocuklarının verisi (satır bazlı filtre ayrıca uygulanır)
    RoleCode.PARENT: {
        Perm.SELF_PORTAL,
        Perm.LESSON_READ,
        Perm.ATTENDANCE_READ,
        Perm.PERFORMANCE_READ,
        Perm.MEMBERSHIP_READ,
        Perm.FINANCE_READ,
        Perm.NOTIFICATION_READ,
    },
}

# Satır bazlı (row-level) kısıtlama uygulanan roller:
# Bu roller yalnızca kendileriyle ilişkili kayıtları görebilir.
SELF_SCOPED_ROLES = {RoleCode.ATHLETE, RoleCode.STUDENT, RoleCode.PARENT}
INSTRUCTOR_SCOPED_ROLES = {
    RoleCode.SWIM_INSTRUCTOR,
    RoleCode.KIDS_INSTRUCTOR,
    RoleCode.BABY_INSTRUCTOR,
    RoleCode.PRIVATE_INSTRUCTOR,
    RoleCode.ADAPTIVE_INSTRUCTOR,
    RoleCode.CONDITIONING_COACH,
    RoleCode.SWIM_COACH,
}


def permissions_for_roles(role_codes: list[str] | set[str]) -> set[str]:
    """Verilen rollerin efektif izin kümesini (birleşim) döndürür."""
    effective: set[str] = set()
    for code in role_codes:
        effective |= {str(p) for p in ROLE_PERMISSIONS.get(code, set())}
    return effective


def role_label(code: str, lang: str = "tr") -> str:
    return ROLE_LABELS.get(code, {}).get(lang, code)


def default_role_seed() -> list[dict]:
    """Veritabanına yazılacak varsayılan rol tanımlarını üretir."""
    return [
        {
            "code": str(code),
            "name_tr": ROLE_LABELS[code]["tr"],
            "name_en": ROLE_LABELS[code]["en"],
            "permissions": sorted(str(p) for p in ROLE_PERMISSIONS.get(code, set())),
            "is_system": True,
        }
        for code in RoleCode
    ]
