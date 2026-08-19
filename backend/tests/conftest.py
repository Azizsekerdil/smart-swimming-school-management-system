"""Test yapılandırması ve paylaşılan fikstürler / Test configuration and fixtures.

Testler bellek içi (in-memory) SQLite kullanır; gerçek veritabanına dokunmaz.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import date, datetime, time, timedelta

# Ayarları test moduna al (uygulama import edilmeden ÖNCE)
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-not-used-in-production-0123456789"
# .env dosyasındaki değeri geçersiz kıl: testler sabit bir yönetici parolası bekler
os.environ["FIRST_ADMIN_EMAIL"] = "admin@yuzmeokulu.local"
os.environ["FIRST_ADMIN_PASSWORD"] = "Admin!2026"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["LOCAL_AI_ENABLED"] = "false"
os.environ["NVIDIA_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["BACKUP_SCHEDULE_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.deps import db_session  # noqa: E402
from app.core.permissions import RoleCode  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.init_db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Group,
    Guardian,
    Instructor,
    Lane,
    Lesson,
    Package,
    Pool,
    Role,
    Student,
    StudentGuardian,
    User,
)
from app.models.enums import LessonType, StudentStatus, SwimLevel  # noqa: E402

# Tüm testler tek bir bellek içi veritabanı paylaşır
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def _enable_foreign_keys(dbapi_connection, connection_record):  # noqa: ANN001, ARG001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Her test için temiz oturum; test sonunda tüm veriler silinir."""
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        # Tabloları temizle (bağımlılık sırasına göre ters)
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        session.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """Uygulamanın veritabanı bağımlılığını test oturumuyla değiştirir."""

    def _override() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[db_session] = _override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Veri fikstürleri
# ---------------------------------------------------------------------------
@pytest.fixture
def seeded(db: Session) -> dict:
    """Rolleri ve varsayılan ayarları yükler."""
    return init_db(db)


@pytest.fixture
def admin_user(db: Session, seeded: dict) -> User:  # noqa: ARG001
    user = db.query(User).filter(User.email == "admin@yuzmeokulu.local").first()
    assert user is not None, "init_db yönetici oluşturmalı"
    user.must_change_password = False
    db.commit()
    return user


def _make_user(
    db: Session, email: str, role_code: str, password: str = "Test!2026"
) -> User:
    role = db.query(Role).filter(Role.code == role_code).first()
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=f"Test {role_code}",
        is_active=True,
    )
    if role:
        user.roles.append(role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def reception_user(db: Session, seeded: dict) -> User:  # noqa: ARG001
    return _make_user(db, "resepsiyon@test.local", RoleCode.RECEPTION)


@pytest.fixture
def instructor_user(db: Session, seeded: dict) -> User:  # noqa: ARG001
    return _make_user(db, "egitmen@test.local", RoleCode.SWIM_INSTRUCTOR)


@pytest.fixture
def parent_user(db: Session, seeded: dict) -> User:  # noqa: ARG001
    return _make_user(db, "veli@test.local", RoleCode.PARENT)


@pytest.fixture
def finance_user(db: Session, seeded: dict) -> User:  # noqa: ARG001
    return _make_user(db, "finans@test.local", RoleCode.FINANCE)


def auth_headers(
    client: TestClient, email: str, password: str = "Test!2026"
) -> dict[str, str]:
    """Giriş yapıp Authorization başlığı üretir."""
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, f"Giriş başarısız: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient, admin_user: User) -> dict[str, str]:
    return auth_headers(client, admin_user.email, "Admin!2026")


@pytest.fixture
def reception_headers(client: TestClient, reception_user: User) -> dict[str, str]:
    return auth_headers(client, reception_user.email)


@pytest.fixture
def instructor_headers(client: TestClient, instructor_user: User) -> dict[str, str]:
    return auth_headers(client, instructor_user.email)


@pytest.fixture
def parent_headers(client: TestClient, parent_user: User) -> dict[str, str]:
    return auth_headers(client, parent_user.email)


@pytest.fixture
def finance_headers(client: TestClient, finance_user: User) -> dict[str, str]:
    return auth_headers(client, finance_user.email)


@pytest.fixture
def pool(db: Session) -> Pool:
    pool = Pool(
        name="Test Havuzu",
        length_m=25,
        lane_count=4,
        capacity=40,
        opening_time=time(8, 0),
        closing_time=time(22, 0),
    )
    db.add(pool)
    db.flush()
    for number in range(1, 5):
        db.add(Lane(pool_id=pool.id, lane_number=number, max_swimmers=8))
    db.commit()
    db.refresh(pool)
    return pool


@pytest.fixture
def lanes(db: Session, pool: Pool) -> list[Lane]:
    return (
        db.query(Lane).filter(Lane.pool_id == pool.id).order_by(Lane.lane_number).all()
    )


@pytest.fixture
def instructor(db: Session) -> Instructor:
    instructor = Instructor(
        employee_number="EGT0001",
        first_name="Ayşe",
        last_name="Yılmaz",
        title="Yüzme Eğitmeni",
        specialties=["çocuk", "başlangıç"],
        is_active=True,
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return instructor


@pytest.fixture
def second_instructor(db: Session) -> Instructor:
    instructor = Instructor(
        employee_number="EGT0002",
        first_name="Mehmet",
        last_name="Demir",
        title="Baş Antrenör",
        is_active=True,
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return instructor


@pytest.fixture
def group(db: Session) -> Group:
    group = Group(
        name="Yunuslar", level=SwimLevel.ELEMENTARY, min_age=8, max_age=11, capacity=10
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@pytest.fixture
def student(db: Session, group: Group, instructor: Instructor) -> Student:
    student = Student(
        student_number="OGR00001",
        first_name="Ali",
        last_name="Kaya",
        birth_date=date.today() - timedelta(days=10 * 365),
        swim_level=SwimLevel.ELEMENTARY,
        status=StudentStatus.ACTIVE,
        registration_date=date.today() - timedelta(days=120),
        group_id=group.id,
        primary_instructor_id=instructor.id,
        consent_given=True,
        health_notes="Test sağlık notu",
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@pytest.fixture
def second_student(db: Session, group: Group) -> Student:
    student = Student(
        student_number="OGR00002",
        first_name="Zeynep",
        last_name="Şahin",
        birth_date=date.today() - timedelta(days=9 * 365),
        swim_level=SwimLevel.BEGINNER,
        status=StudentStatus.ACTIVE,
        registration_date=date.today() - timedelta(days=60),
        group_id=group.id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@pytest.fixture
def guardian(db: Session, student: Student, parent_user: User) -> Guardian:
    guardian = Guardian(
        first_name="Fatma",
        last_name="Kaya",
        relationship_type="mother",
        phone="0000 000 11 22",  # aranamaz demo numarasi (bkz. seed._phone)
        user_id=parent_user.id,
    )
    db.add(guardian)
    db.flush()
    db.add(
        StudentGuardian(student_id=student.id, guardian_id=guardian.id, is_primary=True)
    )
    db.commit()
    db.refresh(guardian)
    return guardian


@pytest.fixture
def package(db: Session) -> Package:
    package = Package(
        name="Test 8 Ders",
        package_type="lesson_pack",
        lesson_count=8,
        duration_days=90,
        price=3000,
        currency="TRY",
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@pytest.fixture
def lesson(
    db: Session, pool: Pool, lanes: list[Lane], instructor: Instructor
) -> Lesson:
    """Yarın 17:00-18:00 arası bir ders."""
    tomorrow = date.today() + timedelta(days=1)
    lesson = Lesson(
        title="Test Dersi",
        lesson_type=LessonType.GROUP,
        start_at=datetime.combine(tomorrow, time(17, 0)),
        end_at=datetime.combine(tomorrow, time(18, 0)),
        pool_id=pool.id,
        lane_id=lanes[0].id,
        instructor_id=instructor.id,
        capacity=8,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@pytest.fixture
def tomorrow_at():
    """Yarının belirli saatini üretir: tomorrow_at(17, 0) -> datetime"""

    def _factory(hour: int, minute: int = 0) -> datetime:
        return datetime.combine(date.today() + timedelta(days=1), time(hour, minute))

    return _factory
