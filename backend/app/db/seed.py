"""Demo verisi üreticisi / Demo data seeder.

YALNIZCA GELİŞTİRME ORTAMI İÇİNDİR. Üretilen tüm kayıtlar `is_demo=True` ile
işaretlenir ve arayüzde "DEMO" rozetiyle gösterilir; gerçek veri gibi sunulmaz.

Çalıştırma:
    python -m app.db.seed
    python -m app.db.seed --reset
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging
from app.core.security import hash_password
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.attendance import Attendance
from app.models.competition import Competition, CompetitionEntry, CompetitionEvent
from app.models.enums import (
    AttendanceStatus,
    CompetitionLevel,
    CourseType,
    ExpenseCategory,
    Gender,
    LessonStatus,
    LessonType,
    MembershipStatus,
    PaymentMethod,
    PaymentStatus,
    PoolStatus,
    Stroke,
    StudentStatus,
    SwimLevel,
)
from app.models.facility import Lane, Pool, WaterQualityLog
from app.models.finance import Expense, Invoice, Payment
from app.models.lesson import Lesson, LessonEnrollment
from app.models.membership import Membership, Package
from app.models.people import (
    Group,
    Guardian,
    Instructor,
    InstructorAvailability,
    InstructorCertificate,
    Student,
    StudentGuardian,
)
from app.models.performance import PerformanceRecord, PersonalBest
from app.models.user import Role, User

logger = get_logger("application")
random.seed(20260815)  # Tekrarlanabilir demo verisi

# ---------------------------------------------------------------------------
# Türkçe isim havuzları
# ---------------------------------------------------------------------------
FIRST_NAMES_M = [
    "Ahmet",
    "Mehmet",
    "Mustafa",
    "Ali",
    "Emre",
    "Burak",
    "Can",
    "Deniz",
    "Efe",
    "Kerem",
    "Mert",
    "Ozan",
    "Selim",
    "Yusuf",
    "Arda",
    "Barış",
    "Cem",
    "Eren",
    "Kaan",
    "Onur",
    "Tolga",
    "Umut",
    "Yiğit",
    "Berk",
    "Doruk",
]
FIRST_NAMES_F = [
    "Ayşe",
    "Fatma",
    "Zeynep",
    "Elif",
    "Merve",
    "Selin",
    "Ece",
    "Defne",
    "İrem",
    "Melis",
    "Nehir",
    "Pınar",
    "Sude",
    "Yaren",
    "Aslı",
    "Buse",
    "Ceren",
    "Dilara",
    "Esra",
    "Gizem",
    "Hazal",
    "İpek",
    "Lara",
    "Nazlı",
    "Öykü",
]
LAST_NAMES = [
    "Yılmaz",
    "Kaya",
    "Demir",
    "Şahin",
    "Çelik",
    "Yıldız",
    "Yıldırım",
    "Öztürk",
    "Aydın",
    "Özdemir",
    "Arslan",
    "Doğan",
    "Kılıç",
    "Aslan",
    "Çetin",
    "Kara",
    "Koç",
    "Kurt",
    "Özkan",
    "Şimşek",
    "Polat",
    "Erdoğan",
    "Aksoy",
    "Bulut",
    "Güneş",
]

INSTRUCTOR_TITLES = [
    ("Baş Antrenör", ["yarışma", "teknik analiz", "performans"]),
    ("Yüzme Antrenörü", ["yarışma", "kondisyon"]),
    ("Yüzme Eğitmeni", ["başlangıç", "yetişkin"]),
    ("Çocuk Yüzme Eğitmeni", ["çocuk", "başlangıç", "oyun temelli"]),
    ("Bebek Yüzme Eğitmeni", ["bebek", "su alışkanlığı"]),
    ("Özel Ders Eğitmeni", ["özel ders", "teknik düzeltme"]),
    ("Adaptif Yüzme Eğitmeni", ["adaptif", "özel gereksinim"]),
    ("Kondisyon Antrenörü", ["kondisyon", "kuru antrenman"]),
]

CERTIFICATES = [
    ("TYF 1. Kademe Antrenörlük", "Türkiye Yüzme Federasyonu"),
    ("Cankurtaran Belgesi", "Türkiye Sualtı Sporları Federasyonu"),
    ("İlk Yardım Sertifikası", "Sağlık Bakanlığı"),
    ("Bebek Yüzme Eğitmenliği", "Uluslararası Yüzme Akademisi"),
    ("Adaptif Yüzme Sertifikası", "Özel Sporcular Federasyonu"),
]

GROUP_SPECS = [
    ("Yavru Balıklar", SwimLevel.BEGINNER, 4, 6, "#38bdf8"),
    ("Deniz Yıldızları", SwimLevel.BEGINNER, 7, 9, "#0ea5e9"),
    ("Yunuslar", SwimLevel.ELEMENTARY, 8, 11, "#0284c7"),
    ("Köpekbalıkları", SwimLevel.INTERMEDIATE, 10, 14, "#6366f1"),
    ("Şampiyonlar", SwimLevel.ADVANCED, 12, 17, "#8b5cf6"),
    ("Yarışma Takımı", SwimLevel.COMPETITIVE, 13, 18, "#d946ef"),
    ("Yetişkin Başlangıç", SwimLevel.BEGINNER, 18, 65, "#f59e0b"),
    ("Yetişkin İleri", SwimLevel.INTERMEDIATE, 18, 65, "#f97316"),
]

# Gider tutarları ~50 öğrencilik bir okulun aylık cirosuyla (~120-140 bin TL)
# orantılı seçilmiştir; böylece demo panosunda net kâr gerçekçi görünür.
EXPENSE_SPECS = [
    ("Personel Maaşları", ExpenseCategory.SALARY, 52000, 61000),
    ("Havuz Kirası", ExpenseCategory.RENT, 22000, 22000),
    ("Elektrik Faturası", ExpenseCategory.UTILITIES, 6500, 11000),
    ("Doğalgaz (Isıtma)", ExpenseCategory.UTILITIES, 4500, 9500),
    ("Su Faturası", ExpenseCategory.UTILITIES, 2200, 3800),
    ("Havuz Kimyasalları", ExpenseCategory.CHEMICALS, 3000, 5200),
    ("Filtre Bakımı", ExpenseCategory.MAINTENANCE, 1200, 3500),
    ("Ekipman Alımı", ExpenseCategory.EQUIPMENT, 800, 4500),
    ("Sosyal Medya Reklamı", ExpenseCategory.MARKETING, 1500, 3500),
    ("Sigorta Primi", ExpenseCategory.INSURANCE, 1800, 1800),
]


#: Türkçe -> ASCII eşlemesi.
#: Dikkat: "İ".lower() Python'da "i̇" (i + birleşik nokta U+0307) üretir; bu da
#: e-posta doğrulamasını bozar. Bu yüzden küçültmeden ÖNCE eşleme yapılır.
_TR_ASCII = str.maketrans(
    {
        "ı": "i",
        "İ": "I",
        "ş": "s",
        "Ş": "S",
        "ğ": "g",
        "Ğ": "G",
        "ü": "u",
        "Ü": "U",
        "ö": "o",
        "Ö": "O",
        "ç": "c",
        "Ç": "C",
        "â": "a",
        "î": "i",
        "û": "u",
    }
)


def _slug(text: str) -> str:
    """Türkçe metni e-posta/kullanıcı adı için güvenli ASCII'ye çevirir."""
    ascii_text = text.translate(_TR_ASCII).lower()
    return "".join(
        ch for ch in ascii_text if ch.isascii() and (ch.isalnum() or ch in "._-")
    )


# Demo telefon numaraları KASITLI OLARAK aranamaz biçimdedir.
#
# Önceki sürüm `05XX` biçiminde numara üretiyordu; 0530-0559 aralığı Türkiye'de
# gerçek, tahsis edilmiş mobil bandıdır. Sentetik olarak üretilmiş olsa bile
# böyle bir numara ekran görüntülerinde ya da sunumlarda yayımlandığında gerçek
# bir aboneye trafik yönlendirme riski taşır. `0000` hiçbir ülke/operatör
# planında tahsisli değildir: numara okunabilir kalır ama aranamaz.
DEMO_PHONE_PREFIX = "0000"


def _phone(index: int | None = None) -> str:
    """Aranamayan, açıkça kurgusal demo telefon numarası üretir."""
    suffix = random.randint(0, 9999) if index is None else index % 10000
    return f"{DEMO_PHONE_PREFIX} 000 {suffix // 100:02d} {suffix % 100:02d}"


def _name(gender: str) -> tuple[str, str]:
    first = random.choice(FIRST_NAMES_F if gender == Gender.FEMALE else FIRST_NAMES_M)
    return first, random.choice(LAST_NAMES)


# ---------------------------------------------------------------------------
# Temizlik
# ---------------------------------------------------------------------------
DEMO_MODELS_IN_ORDER = [
    Attendance,
    LessonEnrollment,
    CompetitionEntry,
    CompetitionEvent,
    Competition,
    PerformanceRecord,
    PersonalBest,
    Payment,
    Invoice,
    Expense,
    Membership,
    Lesson,
    WaterQualityLog,
    Lane,
    Pool,
    StudentGuardian,
    Student,
    Guardian,
    InstructorCertificate,
    InstructorAvailability,
    Instructor,
    Group,
]


def clear_demo_data(db: Session) -> None:
    """Yalnızca demo işaretli kayıtları siler; gerçek verilere dokunmaz."""
    logger.info("Demo verileri temizleniyor...")
    for model in DEMO_MODELS_IN_ORDER:
        if hasattr(model, "is_demo"):
            db.execute(delete(model).where(model.is_demo.is_(True)))
        elif model in (
            Attendance,
            LessonEnrollment,
            CompetitionEntry,
            CompetitionEvent,
            PersonalBest,
            InstructorCertificate,
            InstructorAvailability,
            StudentGuardian,
            WaterQualityLog,
            Lane,
        ):
            # Bağlı kayıtlar cascade ile silinir; kalanları temizle
            db.execute(delete(model))
    db.commit()


# ---------------------------------------------------------------------------
# Üretim
# ---------------------------------------------------------------------------
def seed_pools(db: Session) -> list[Pool]:
    specs = [
        (
            "Ana Havuz",
            25.0,
            12.5,
            1.2,
            2.0,
            8,
            80,
            CourseType.SHORT,
            time(7, 0),
            time(22, 0),
        ),
        (
            "Çocuk Havuzu",
            12.5,
            8.0,
            0.6,
            1.0,
            4,
            30,
            CourseType.SHORT,
            time(9, 0),
            time(20, 0),
        ),
    ]
    pools: list[Pool] = []
    for (
        name,
        length,
        width,
        dmin,
        dmax,
        lanes,
        capacity,
        course,
        opening,
        closing,
    ) in specs:
        pool = Pool(
            name=name,
            length_m=length,
            width_m=width,
            depth_min_m=dmin,
            depth_max_m=dmax,
            lane_count=lanes,
            capacity=capacity,
            course_type=course,
            opening_time=opening,
            closing_time=closing,
            status=PoolStatus.OPERATIONAL,
            water_temperature_c=28.5 if "Çocuk" in name else 27.0,
            air_temperature_c=29.0,
            is_indoor=True,
            is_heated=True,
            is_demo=True,
            location="Zemin Kat" if "Ana" in name else "1. Kat",
        )
        db.add(pool)
        db.flush()
        purposes = ["Eğitim", "Eğitim", "Yarışma", "Serbest"]
        for number in range(1, lanes + 1):
            db.add(
                Lane(
                    pool_id=pool.id,
                    lane_number=number,
                    width_m=round(width / lanes, 2),
                    depth_m=dmax,
                    max_swimmers=8 if "Ana" in name else 6,
                    is_active=True,
                    purpose=purposes[(number - 1) % len(purposes)],
                )
            )
        # Su kalitesi geçmişi
        for offset in range(14):
            measured = datetime.now() - timedelta(days=offset)
            ph = round(random.uniform(7.0, 7.5), 2)
            chlorine = round(random.uniform(0.8, 2.2), 2)
            db.add(
                WaterQualityLog(
                    pool_id=pool.id,
                    measured_at=measured,
                    ph=ph,
                    chlorine_ppm=chlorine,
                    temperature_c=pool.water_temperature_c,
                    turbidity_ntu=round(random.uniform(0.05, 0.35), 2),
                    measured_by="Havuz Teknik Ekibi",
                    is_within_limits=True,
                )
            )
        pools.append(pool)
    db.commit()
    logger.info(
        "%s havuz, %s kulvar oluşturuldu", len(pools), sum(p.lane_count for p in pools)
    )
    return pools


def seed_groups(db: Session) -> list[Group]:
    groups = []
    for name, level, min_age, max_age, color in GROUP_SPECS:
        group = Group(
            name=name,
            level=level,
            min_age=min_age,
            max_age=max_age,
            color=color,
            capacity=12,
            is_active=True,
            description=f"{min_age}-{max_age} yaş {level} seviye grubu",
        )
        db.add(group)
        groups.append(group)
    db.commit()
    return groups


def seed_instructors(db: Session, count: int = 10) -> list[Instructor]:
    instructors: list[Instructor] = []
    for index in range(count):
        gender = Gender.FEMALE if index % 2 else Gender.MALE
        first, last = _name(gender)
        title, specialties = INSTRUCTOR_TITLES[index % len(INSTRUCTOR_TITLES)]
        hire = date.today() - timedelta(days=random.randint(120, 2200))

        instructor = Instructor(
            employee_number=f"EGT{index + 1:04d}",
            first_name=first,
            last_name=last,
            gender=gender,
            birth_date=date.today() - timedelta(days=random.randint(24, 48) * 365),
            phone=_phone(),
            email=f"{_slug(first)}.{_slug(last)}{index + 1}@yuzmeokulu.local",
            title=title,
            specialties=specialties,
            hire_date=hire,
            is_active=index < count - 1,
            hourly_rate=round(random.uniform(450, 900), 2),
            monthly_salary=round(random.uniform(38000, 72000), 2),
            max_weekly_hours=random.choice([30, 35, 40]),
            bio=f"{title} olarak {(date.today() - hire).days // 365} yıldır görev yapıyor.",
            is_demo=True,
        )
        db.add(instructor)
        db.flush()

        for cert_name, issuer in random.sample(CERTIFICATES, k=random.randint(1, 3)):
            issued = hire - timedelta(days=random.randint(30, 900))
            db.add(
                InstructorCertificate(
                    instructor_id=instructor.id,
                    name=cert_name,
                    issuer=issuer,
                    issued_date=issued,
                    expiry_date=issued
                    + timedelta(days=random.choice([730, 1095, 1825])),
                )
            )
        for weekday in range(0, 6):
            db.add(
                InstructorAvailability(
                    instructor_id=instructor.id,
                    weekday=weekday,
                    start_time=time(random.choice([8, 9, 10])),
                    end_time=time(random.choice([20, 21, 22])),
                )
            )
        instructors.append(instructor)
    db.commit()
    logger.info("%s eğitmen oluşturuldu", len(instructors))
    return instructors


def seed_guardians_and_students(
    db: Session, groups: list[Group], instructors: list[Instructor], count: int = 50
) -> tuple[list[Student], list[Guardian]]:
    students: list[Student] = []
    guardians: list[Guardian] = []
    active_instructors = [i for i in instructors if i.is_active]

    for index in range(count):
        gender = random.choice([Gender.MALE, Gender.FEMALE])
        first, last = _name(gender)
        age = random.choices(
            [
                random.randint(4, 6),
                random.randint(7, 11),
                random.randint(12, 17),
                random.randint(18, 55),
            ],
            weights=[25, 40, 25, 10],
        )[0]
        birth = date.today() - timedelta(days=age * 365 + random.randint(0, 364))
        registration = date.today() - timedelta(days=random.randint(15, 900))

        suitable = [g for g in groups if (g.min_age or 0) <= age <= (g.max_age or 99)]
        group = random.choice(suitable) if suitable else random.choice(groups)

        level = group.level
        if random.random() < 0.2:
            level = random.choice(list(SwimLevel))

        status = random.choices(
            [
                StudentStatus.ACTIVE,
                StudentStatus.PASSIVE,
                StudentStatus.TRIAL,
                StudentStatus.LEFT,
            ],
            weights=[76, 10, 8, 6],
        )[0]

        student = Student(
            student_number=f"OGR{index + 1:05d}",
            first_name=first,
            last_name=last,
            birth_date=birth,
            gender=gender,
            phone=_phone() if age >= 15 else None,
            email=None,
            address=f"{random.choice(['Atatürk', 'Cumhuriyet', 'İnönü', 'Barbaros'])} Mah. No:{random.randint(1, 120)}",
            emergency_contact_name=None,
            emergency_contact_phone=_phone(),
            swim_level=level,
            status=status,
            registration_date=registration,
            left_date=(
                (registration + timedelta(days=random.randint(60, 400)))
                if status == StudentStatus.LEFT
                else None
            ),
            group_id=group.id,
            primary_instructor_id=(
                random.choice(active_instructors).id if active_instructors else None
            ),
            health_notes=random.choice(
                [
                    None,
                    None,
                    None,
                    "Hafif astım - inhaler yanında bulunmalı",
                    "Kulak tüpü var, kulak tıkacı kullanmalı",
                    "Alerjik rinit",
                ]
            ),
            special_needs=random.choice(
                [None, None, None, None, "Otizm spektrum - birebir ilgi gerekiyor"]
            ),
            goals=random.choice(
                [
                    "Su korkusunu yenmek",
                    "Serbest stili öğrenmek",
                    "Yarışmalara hazırlanmak",
                    "Kondisyon geliştirmek",
                    "4 stili tamamlamak",
                    None,
                ]
            ),
            consent_given=random.random() > 0.08,
            consent_date=registration,
            is_demo=True,
        )
        db.add(student)
        db.flush()
        students.append(student)

        # 18 yaş altı için veli
        if age < 18:
            guardian_gender = random.choice([Gender.MALE, Gender.FEMALE])
            guardian_first = random.choice(
                FIRST_NAMES_F if guardian_gender == Gender.FEMALE else FIRST_NAMES_M
            )
            guardian = Guardian(
                first_name=guardian_first,
                last_name=last,
                relationship_type=(
                    "mother" if guardian_gender == Gender.FEMALE else "father"
                ),
                phone=_phone(),
                secondary_phone=_phone() if random.random() > 0.6 else None,
                email=f"veli{index + 1}@ornek.local",
                occupation=random.choice(
                    [
                        "Öğretmen",
                        "Mühendis",
                        "Doktor",
                        "Esnaf",
                        "Memur",
                        "Serbest Meslek",
                        None,
                    ]
                ),
                is_demo=True,
            )
            db.add(guardian)
            db.flush()
            db.add(
                StudentGuardian(
                    student_id=student.id,
                    guardian_id=guardian.id,
                    is_primary=True,
                    can_pickup=True,
                    is_billing_contact=True,
                )
            )
            student.emergency_contact_name = guardian.full_name
            student.emergency_contact_phone = guardian.phone
            guardians.append(guardian)

    db.commit()
    logger.info("%s öğrenci, %s veli oluşturuldu", len(students), len(guardians))
    return students, guardians


def seed_memberships_and_finance(
    db: Session, students: list[Student], packages: list[Package]
) -> None:
    active_packages = [p for p in packages if p.is_active and float(p.price) > 0]
    invoice_counter = payment_counter = 1

    for student in students:
        if student.status in (StudentStatus.LEFT,):
            continue
        history_count = random.randint(1, 3)
        cursor_date = student.registration_date

        for order in range(history_count):
            package = random.choice(active_packages)
            start = cursor_date
            end = start + timedelta(days=package.duration_days or 30)
            is_last = order == history_count - 1

            if is_last and student.status == StudentStatus.ACTIVE:
                status = MembershipStatus.ACTIVE
                # Aktif üyeliğin bugünü kapsamasını sağla
                if end < date.today():
                    start = date.today() - timedelta(days=random.randint(5, 40))
                    end = start + timedelta(days=package.duration_days or 30)
            else:
                status = MembershipStatus.EXPIRED

            total_credits = package.lesson_count
            used = (
                random.randint(0, total_credits)
                if total_credits and status == MembershipStatus.EXPIRED
                else (
                    random.randint(0, max(0, (total_credits or 8) // 2))
                    if total_credits
                    else 0
                )
            )
            discount = random.choice([0, 0, 0, 250, 500])
            price = max(0.0, float(package.price) - discount)

            membership = Membership(
                student_id=student.id,
                package_id=package.id,
                start_date=start,
                end_date=end,
                status=status,
                total_credits=total_credits,
                used_credits=used,
                price_paid=price,
                discount_amount=discount,
                discount_reason="Kardeş indirimi" if discount else None,
                auto_renew=random.random() > 0.7,
                is_demo=True,
            )
            db.add(membership)
            db.flush()

            # Fatura
            due = start + timedelta(days=random.choice([0, 7, 15]))
            fully_paid = random.random() > 0.18
            paid_amount = (
                price if fully_paid else round(price * random.uniform(0, 0.6), 2)
            )
            invoice = Invoice(
                invoice_number=f"FT{invoice_counter:06d}",
                student_id=student.id,
                membership_id=membership.id,
                issue_date=start,
                due_date=due,
                subtotal=float(package.price),
                discount_amount=discount,
                tax_amount=0,
                total_amount=price,
                paid_amount=paid_amount,
                status=(
                    PaymentStatus.PAID
                    if fully_paid
                    else (
                        PaymentStatus.PARTIAL
                        if paid_amount > 0
                        else PaymentStatus.PENDING
                    )
                ),
                description=f"{package.name} paketi",
                is_demo=True,
            )
            db.add(invoice)
            db.flush()
            invoice_counter += 1

            if paid_amount > 0:
                db.add(
                    Payment(
                        receipt_number=f"FIS{payment_counter:06d}",
                        student_id=student.id,
                        membership_id=membership.id,
                        invoice_id=invoice.id,
                        amount=paid_amount,
                        currency=package.currency,
                        method=random.choice(
                            [
                                PaymentMethod.CASH,
                                PaymentMethod.CARD,
                                PaymentMethod.TRANSFER,
                            ]
                        ),
                        status=PaymentStatus.PAID,
                        payment_date=due if due <= date.today() else start,
                        description=f"{package.name} ödemesi",
                        is_demo=True,
                    )
                )
                payment_counter += 1

            cursor_date = end + timedelta(days=random.randint(0, 20))
            if cursor_date > date.today():
                break

    # Giderler (son 12 ay)
    for month_offset in range(12):
        month_start = (
            date.today().replace(day=1) - timedelta(days=31 * month_offset)
        ).replace(day=1)
        for title, category, low, high in EXPENSE_SPECS:
            db.add(
                Expense(
                    title=f"{title} - {month_start:%m/%Y}",
                    category=category,
                    amount=round(random.uniform(low, high), 2),
                    expense_date=month_start + timedelta(days=random.randint(0, 27)),
                    method=PaymentMethod.TRANSFER,
                    vendor=random.choice(["ABC Ltd.", "XYZ A.Ş.", "Belediye", "-"]),
                    is_recurring=category
                    in (ExpenseCategory.SALARY, ExpenseCategory.RENT),
                    is_demo=True,
                )
            )
    db.commit()
    logger.info("Üyelik, fatura, ödeme ve gider kayıtları oluşturuldu")


def seed_lessons_and_attendance(
    db: Session,
    pools: list[Pool],
    groups: list[Group],
    instructors: list[Instructor],
    students: list[Student],
) -> None:
    active_instructors = [i for i in instructors if i.is_active]
    active_students = [
        s for s in students if s.status in (StudentStatus.ACTIVE, StudentStatus.TRIAL)
    ]
    main_pool = pools[0]
    kids_pool = pools[1] if len(pools) > 1 else pools[0]

    lane_map = {
        pool.id: db.scalars(
            select(Lane).where(Lane.pool_id == pool.id).order_by(Lane.lane_number)
        ).all()
        for pool in pools
    }

    # Grup -> ders türü ve saat şablonu
    schedule_templates = [
        (groups[0], kids_pool, LessonType.KIDS, [0, 2], time(16, 0), time(16, 45)),
        (groups[1], kids_pool, LessonType.KIDS, [1, 3], time(17, 0), time(17, 45)),
        (groups[2], main_pool, LessonType.GROUP, [0, 2, 4], time(17, 0), time(18, 0)),
        (
            groups[3],
            main_pool,
            LessonType.INTERMEDIATE,
            [1, 3],
            time(18, 0),
            time(19, 0),
        ),
        (
            groups[4],
            main_pool,
            LessonType.ADVANCED,
            [0, 2, 4],
            time(19, 0),
            time(20, 0),
        ),
        (
            groups[5],
            main_pool,
            LessonType.COMPETITION_TEAM,
            [1, 3, 5],
            time(19, 0),
            time(20, 30),
        ),
        (groups[6], main_pool, LessonType.ADULT, [1, 3], time(20, 30), time(21, 30)),
        (groups[7], main_pool, LessonType.ADULT, [0, 4], time(20, 30), time(21, 30)),
    ]

    start_date = date.today() - timedelta(days=60)
    end_date = date.today() + timedelta(days=30)
    lesson_count = attendance_count = 0

    # Kulvar tahsisini takip et: (pool_id, tarih, saat) -> kullanılan kulvarlar
    lane_usage: dict[tuple[int, date, time], set[int]] = {}

    for group, pool, lesson_type, weekdays, start_time, end_time in schedule_templates:
        instructor = random.choice(active_instructors)
        group_students = [s for s in active_students if s.group_id == group.id]
        lanes = lane_map[pool.id]

        cursor = start_date
        while cursor <= end_date:
            if cursor.weekday() not in weekdays:
                cursor += timedelta(days=1)
                continue

            key = (pool.id, cursor, start_time)
            used = lane_usage.setdefault(key, set())
            available = [lane for lane in lanes if lane.id not in used]
            if not available:
                cursor += timedelta(days=1)
                continue
            lane = available[0]
            used.add(lane.id)

            start_at = datetime.combine(cursor, start_time)
            end_at = datetime.combine(cursor, end_time)
            is_past = end_at < datetime.now()

            lesson = Lesson(
                title=f"{group.name} - {lesson_type}",
                lesson_type=lesson_type,
                status=LessonStatus.COMPLETED if is_past else LessonStatus.SCHEDULED,
                start_at=start_at,
                end_at=end_at,
                pool_id=pool.id,
                lane_id=lane.id,
                instructor_id=instructor.id,
                group_id=group.id,
                capacity=min(group.capacity, lane.max_swimmers),
                color=group.color,
                is_demo=True,
            )
            db.add(lesson)
            db.flush()
            lesson_count += 1

            enrolled = group_students[: lesson.capacity]
            for student in enrolled:
                db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
                if is_past:
                    status = random.choices(
                        [
                            AttendanceStatus.PRESENT,
                            AttendanceStatus.PRESENT,
                            AttendanceStatus.PRESENT,
                            AttendanceStatus.LATE,
                            AttendanceStatus.ABSENT,
                            AttendanceStatus.EXCUSED,
                        ],
                        weights=[55, 15, 10, 8, 7, 5],
                    )[0]
                    db.add(
                        Attendance(
                            lesson_id=lesson.id,
                            student_id=student.id,
                            status=status,
                            checked_in_at=(
                                start_at + timedelta(minutes=random.randint(-5, 12))
                                if status
                                in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)
                                else None
                            ),
                            late_minutes=(
                                random.randint(5, 20)
                                if status == AttendanceStatus.LATE
                                else None
                            ),
                            excuse_reason=(
                                "Hastalık"
                                if status == AttendanceStatus.EXCUSED
                                else None
                            ),
                            is_demo=True,
                        )
                    )
                    attendance_count += 1
            cursor += timedelta(days=1)

    # Özel dersler
    for _ in range(30):
        day = date.today() - timedelta(days=random.randint(-20, 50))
        hour = random.choice([10, 11, 14, 15, 16])
        start_at = datetime.combine(day, time(hour, 0))
        end_at = start_at + timedelta(minutes=45)
        key = (main_pool.id, day, time(hour, 0))
        used = lane_usage.setdefault(key, set())
        available = [lane for lane in lane_map[main_pool.id] if lane.id not in used]
        if not available or not active_students:
            continue
        lane = available[0]
        used.add(lane.id)
        student = random.choice(active_students)
        lesson = Lesson(
            title=f"Özel Ders - {student.full_name}",
            lesson_type=LessonType.PRIVATE,
            status=(
                LessonStatus.COMPLETED
                if end_at < datetime.now()
                else LessonStatus.SCHEDULED
            ),
            start_at=start_at,
            end_at=end_at,
            pool_id=main_pool.id,
            lane_id=lane.id,
            instructor_id=random.choice(active_instructors).id,
            capacity=1,
            price=1200,
            color="#f59e0b",
            is_demo=True,
        )
        db.add(lesson)
        db.flush()
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
        lesson_count += 1
        if end_at < datetime.now():
            db.add(
                Attendance(
                    lesson_id=lesson.id,
                    student_id=student.id,
                    status=AttendanceStatus.PRESENT,
                    checked_in_at=start_at,
                    is_demo=True,
                )
            )
            attendance_count += 1

    db.commit()
    logger.info("%s ders, %s yoklama kaydı oluşturuldu", lesson_count, attendance_count)


def seed_performance(
    db: Session, students: list[Student], instructors: list[Instructor]
) -> None:
    """Gerçekçi gelişim eğrileri üretir (zamanla iyileşen dereceler)."""
    athletes = [
        s
        for s in students
        if s.swim_level
        in (
            SwimLevel.INTERMEDIATE,
            SwimLevel.ADVANCED,
            SwimLevel.COMPETITIVE,
            SwimLevel.ELITE,
        )
        and s.status == StudentStatus.ACTIVE
    ]
    if not athletes:
        athletes = [s for s in students if s.status == StudentStatus.ACTIVE][:15]

    # Yaş ve stile göre gerçekçi başlangıç dereceleri (25 m, saniye)
    base_times = {
        Stroke.FREESTYLE: 20.0,
        Stroke.BACKSTROKE: 24.0,
        Stroke.BREASTSTROKE: 26.0,
        Stroke.BUTTERFLY: 23.0,
    }
    record_count = 0
    active_instructors = [i for i in instructors if i.is_active]

    for student in athletes:
        age = student.age or 12
        # Yaş faktörü: küçükler daha yavaş
        age_factor = max(1.0, 2.0 - (age - 6) * 0.06)
        level_factor = {
            SwimLevel.BEGINNER: 1.5,
            SwimLevel.ELEMENTARY: 1.3,
            SwimLevel.INTERMEDIATE: 1.15,
            SwimLevel.ADVANCED: 1.05,
            SwimLevel.COMPETITIVE: 0.98,
            SwimLevel.ELITE: 0.92,
        }.get(student.swim_level, 1.2)

        strokes = random.sample(list(base_times.keys()), k=random.randint(2, 4))
        for stroke in strokes:
            for distance in random.sample([25, 50, 100], k=random.randint(1, 2)):
                base = (
                    base_times[stroke]
                    * age_factor
                    * level_factor
                    * (distance / 25)
                    * (1.0 + 0.04 * (distance // 25 - 1))
                )
                session_count = random.randint(6, 14)
                # Genel iyileşme oranı: %3-12
                total_improvement = random.uniform(0.03, 0.12)
                declining = random.random() < 0.15  # bazı sporcularda gerileme

                for session in range(session_count):
                    progress = session / max(1, session_count - 1)
                    if declining and progress > 0.6:
                        factor = 1 - total_improvement * 0.6 + (progress - 0.6) * 0.09
                    else:
                        factor = 1 - total_improvement * progress
                    noise = random.uniform(-0.012, 0.012)
                    time_seconds = round(base * (factor + noise), 2)

                    days_ago = int((1 - progress) * random.randint(100, 170))
                    recorded = date.today() - timedelta(days=days_ago)
                    if recorded < student.registration_date:
                        recorded = student.registration_date + timedelta(
                            days=session * 7
                        )
                    if recorded > date.today():
                        continue

                    splits = []
                    if distance >= 50:
                        segments = distance // 25
                        per_segment = time_seconds / segments
                        splits = [
                            round(
                                per_segment
                                * (1 + (index * 0.03) + random.uniform(-0.02, 0.02)),
                                2,
                            )
                            for index in range(segments)
                        ]

                    db.add(
                        PerformanceRecord(
                            student_id=student.id,
                            instructor_id=(
                                random.choice(active_instructors).id
                                if active_instructors
                                else None
                            ),
                            stroke=stroke,
                            distance_m=distance,
                            course_type=CourseType.SHORT,
                            time_seconds=time_seconds,
                            splits=splits,
                            stroke_rate=round(random.uniform(32, 52), 1),
                            stroke_count=random.randint(
                                distance // 25 * 12, distance // 25 * 22
                            ),
                            reaction_time=round(random.uniform(0.62, 0.92), 3),
                            turn_time=(
                                round(random.uniform(0.9, 1.8), 2)
                                if distance > 25
                                else None
                            ),
                            recorded_date=recorded,
                            is_competition=random.random() < 0.15,
                            heart_rate_avg=random.randint(150, 190),
                            perceived_effort=random.randint(5, 9),
                            is_demo=True,
                        )
                    )
                    record_count += 1

    db.commit()

    # Kişisel rekorları hesapla
    rows = db.execute(
        select(
            PerformanceRecord.student_id,
            PerformanceRecord.stroke,
            PerformanceRecord.distance_m,
            PerformanceRecord.course_type,
            func.min(PerformanceRecord.time_seconds),
        ).group_by(
            PerformanceRecord.student_id,
            PerformanceRecord.stroke,
            PerformanceRecord.distance_m,
            PerformanceRecord.course_type,
        )
    ).all()

    for student_id, stroke, distance, course, best_time in rows:
        record = db.scalar(
            select(PerformanceRecord)
            .where(
                PerformanceRecord.student_id == student_id,
                PerformanceRecord.stroke == stroke,
                PerformanceRecord.distance_m == distance,
                PerformanceRecord.time_seconds == best_time,
            )
            .limit(1)
        )
        if record:
            record.is_personal_best = True
            db.add(
                PersonalBest(
                    student_id=student_id,
                    stroke=stroke,
                    distance_m=distance,
                    course_type=course,
                    time_seconds=float(best_time),
                    achieved_date=record.recorded_date,
                    performance_record_id=record.id,
                )
            )
    db.commit()
    logger.info(
        "%s performans kaydı, %s kişisel rekor oluşturuldu", record_count, len(rows)
    )


def seed_competitions(db: Session, students: list[Student]) -> None:
    athletes = [
        s
        for s in students
        if s.swim_level in (SwimLevel.COMPETITIVE, SwimLevel.ADVANCED, SwimLevel.ELITE)
        and s.status == StudentStatus.ACTIVE
    ]
    if not athletes:
        return

    specs = [
        ("Kulüp İçi Zaman Denemesi", CompetitionLevel.CLUB, -45, "Kendi Havuzumuz"),
        ("İl Yaz Kupası", CompetitionLevel.LOCAL, -20, "Merkez Olimpik Havuz"),
        ("Bölge Şampiyonası", CompetitionLevel.REGIONAL, 25, "Bölge Spor Kompleksi"),
    ]

    for name, level, day_offset, location in specs:
        start = date.today() + timedelta(days=day_offset)
        competition = Competition(
            name=name,
            location=location,
            organizer="Türkiye Yüzme Federasyonu",
            level=level,
            course_type=CourseType.SHORT,
            start_date=start,
            end_date=start + timedelta(days=1),
            registration_deadline=start - timedelta(days=10),
            is_completed=day_offset < 0,
            is_demo=True,
            description=f"{name} - {location}",
        )
        db.add(competition)
        db.flush()

        for order, (stroke, distance) in enumerate(
            [
                (Stroke.FREESTYLE, 50),
                (Stroke.FREESTYLE, 100),
                (Stroke.BACKSTROKE, 50),
                (Stroke.BREASTSTROKE, 50),
            ],
            start=1,
        ):
            event = CompetitionEvent(
                competition_id=competition.id,
                stroke=stroke,
                distance_m=distance,
                gender_category="mixed",
                age_category="11-14 yaş",
                event_order=order,
                scheduled_date=start,
            )
            db.add(event)
            db.flush()

            participants = random.sample(
                athletes, k=min(len(athletes), random.randint(4, 8))
            )
            results = []
            for entry_index, athlete in enumerate(participants):
                pb = db.scalar(
                    select(PersonalBest).where(
                        PersonalBest.student_id == athlete.id,
                        PersonalBest.stroke == stroke,
                        PersonalBest.distance_m == distance,
                    )
                )
                seed_time = (
                    float(pb.time_seconds)
                    if pb
                    else round(random.uniform(28, 45) * (distance / 50), 2)
                )
                entry = CompetitionEntry(
                    event_id=event.id,
                    student_id=athlete.id,
                    seed_time_seconds=seed_time,
                    heat_number=1,
                    lane_number=entry_index + 1,
                )
                if competition.is_completed:
                    result_time = round(seed_time * random.uniform(0.97, 1.04), 2)
                    entry.result_time_seconds = result_time
                    entry.is_personal_best = result_time < seed_time
                    results.append((entry, result_time))
                db.add(entry)

            if results:
                results.sort(key=lambda item: item[1])
                medals = ["gold", "silver", "bronze"]
                for rank, (entry, _) in enumerate(results, start=1):
                    entry.rank = rank
                    if rank <= 3:
                        entry.medal = medals[rank - 1]

    db.commit()
    logger.info("%s yarışma oluşturuldu", len(specs))


def seed_demo_users(
    db: Session, instructors: list[Instructor], guardians: list[Guardian]
) -> None:
    """Her rol için demo giriş hesabı oluşturur (geliştirme kolaylığı)."""
    role_specs = [
        ("mudur@yuzmeokulu.local", "Demo Müdür", "school_director"),
        ("resepsiyon@yuzmeokulu.local", "Demo Resepsiyon", "reception"),
        ("finans@yuzmeokulu.local", "Demo Finans", "finance"),
        ("basantrenor@yuzmeokulu.local", "Demo Baş Antrenör", "head_coach"),
        ("egitmen@yuzmeokulu.local", "Demo Eğitmen", "swim_instructor"),
        ("veli@yuzmeokulu.local", "Demo Veli", "parent"),
    ]
    password = hash_password("Demo!2026")

    for email, full_name, role_code in role_specs:
        if db.scalar(select(User).where(User.email == email)):
            continue
        role = db.scalar(select(Role).where(Role.code == role_code))
        user = User(
            email=email,
            hashed_password=password,
            full_name=full_name,
            language="tr",
            is_active=True,
            must_change_password=False,
        )
        if role:
            user.roles.append(role)
        db.add(user)
        db.flush()

        if role_code in ("head_coach", "swim_instructor") and instructors:
            instructor = next(
                (i for i in instructors if i.user_id is None and i.is_active), None
            )
            if instructor:
                instructor.user_id = user.id
        if role_code == "parent" and guardians:
            guardian = next((g for g in guardians if g.user_id is None), None)
            if guardian:
                guardian.user_id = user.id

    db.commit()
    logger.info("Demo kullanıcı hesapları oluşturuldu (parola: Demo!2026)")


def seed_all(db: Session, student_count: int = 50, instructor_count: int = 10) -> dict:
    """Tüm demo verisini üretir."""
    if settings.is_production:
        raise RuntimeError("Demo verisi üretim ortamında oluşturulamaz.")

    init_db(db)
    packages = db.scalars(select(Package)).all()

    pools = seed_pools(db)
    groups = seed_groups(db)
    instructors = seed_instructors(db, instructor_count)
    students, guardians = seed_guardians_and_students(
        db, groups, instructors, student_count
    )
    seed_memberships_and_finance(db, students, packages)
    seed_lessons_and_attendance(db, pools, groups, instructors, students)
    seed_performance(db, students, instructors)
    seed_competitions(db, students)
    seed_demo_users(db, instructors, guardians)

    summary = {
        "pools": len(pools),
        "lanes": db.scalar(select(func.count(Lane.id))) or 0,
        "groups": len(groups),
        "instructors": len(instructors),
        "students": len(students),
        "guardians": len(guardians),
        "lessons": db.scalar(select(func.count(Lesson.id))) or 0,
        "attendances": db.scalar(select(func.count(Attendance.id))) or 0,
        "memberships": db.scalar(select(func.count(Membership.id))) or 0,
        "payments": db.scalar(select(func.count(Payment.id))) or 0,
        "invoices": db.scalar(select(func.count(Invoice.id))) or 0,
        "expenses": db.scalar(select(func.count(Expense.id))) or 0,
        "performance_records": db.scalar(select(func.count(PerformanceRecord.id))) or 0,
        "personal_bests": db.scalar(select(func.count(PersonalBest.id))) or 0,
        "competitions": db.scalar(select(func.count(Competition.id))) or 0,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo verisi üretici")
    parser.add_argument(
        "--reset", action="store_true", help="Mevcut demo verilerini sil"
    )
    parser.add_argument("--students", type=int, default=50)
    parser.add_argument("--instructors", type=int, default=10)
    args = parser.parse_args()

    setup_logging()
    if settings.is_production:
        print("HATA: Üretim ortamında demo verisi oluşturulamaz.")
        return 1

    with SessionLocal() as db:
        if args.reset:
            clear_demo_data(db)
        existing = db.scalar(select(func.count(Student.id))) or 0
        if existing and not args.reset:
            print(
                f"Veritabanında zaten {existing} öğrenci var. Yeniden üretmek için --reset kullanın."
            )
            return 0

        summary = seed_all(db, args.students, args.instructors)

    print("\n" + "=" * 58)
    print("  DEMO VERİSİ OLUŞTURULDU (yalnızca geliştirme ortamı)")
    print("=" * 58)
    for key, value in summary.items():
        print(f"  {key:.<32} {value:>6}")
    print("=" * 58)
    print("  Tüm demo kayıtlar `is_demo=True` ile işaretlenmiştir.")
    print(f"  Yönetici: {settings.first_admin_email}")
    print("  Demo hesaplar: mudur@ / resepsiyon@ / finans@ / basantrenor@")
    print("                 egitmen@ / veli@yuzmeokulu.local  (parola: Demo!2026)")
    print("=" * 58 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
