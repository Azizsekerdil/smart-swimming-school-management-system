"""Satır/nesne bazlı yetkilendirme regresyon testleri.

Kendi verisiyle sınırlı roller (veli / öğrenci / sporcu) yalnızca kendi
kayıtlarını görebilir. Bu dosya, tek ortak mekanizmanın (`AccessScope`,
`app/api/deps.py`) gerçekten uygulandığını **olumsuz** senaryolarla kanıtlar:
başka bir ailenin çocuğuna, borcuna, üyeliğine veya ders listesine erişim
denenir ve reddedilmesi beklenir.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import EnrollmentStatus, MembershipStatus
from app.models.finance import Invoice
from app.models.lesson import Lesson, LessonEnrollment
from app.models.membership import Membership, Package
from app.models.people import Student
from app.models.performance import TrainingPlan


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
@pytest.fixture
def linked_guardian(db: Session, guardian):  # noqa: ANN201
    """Veli-öğrenci bağını kurar ve oturum kimlik haritasını tazeler.

    Testler tek bir oturum paylaştığı için `User.guardian` ilişkisi daha önce
    `None` olarak önbelleğe alınmış olabilir. Gerçek uygulamada her istek yeni
    bir oturum açar; burada aynı davranışı elde etmek için önbellek boşaltılır.
    """
    db.expire_all()
    return guardian


@pytest.fixture
def other_lesson(db: Session, lesson: Lesson, second_student: Student) -> Lesson:
    """Yalnızca `second_student`'ın kayıtlı olduğu ders (velinin çocuğu değil)."""
    db.add(
        LessonEnrollment(
            lesson_id=lesson.id,
            student_id=second_student.id,
            status=EnrollmentStatus.ENROLLED,
        )
    )
    db.commit()
    return lesson


@pytest.fixture
def other_invoice(db: Session, second_student: Student) -> Invoice:
    invoice = Invoice(
        invoice_number="FT-TEST-0001",
        student_id=second_student.id,
        issue_date=date.today(),
        due_date=date.today() - timedelta(days=10),
        total_amount=1000,
        paid_amount=0,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@pytest.fixture
def other_membership(
    db: Session, second_student: Student, package: Package
) -> Membership:
    membership = Membership(
        student_id=second_student.id,
        package_id=package.id,
        start_date=date.today() - timedelta(days=5),
        end_date=date.today() + timedelta(days=5),
        status=MembershipStatus.ACTIVE,
        total_credits=8,
        used_credits=7,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@pytest.fixture
def other_training_plan(db: Session, second_student: Student) -> TrainingPlan:
    plan = TrainingPlan(
        student_id=second_student.id,
        title="Başka öğrencinin planı",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        is_approved=True,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


# ---------------------------------------------------------------------------
# 1. Kurum geneli / kohort ötesi uçlar self-scoped role tamamen kapalı
# ---------------------------------------------------------------------------
ORG_WIDE_PATHS = [
    "/api/v1/finance/summary",
    "/api/v1/finance/expenses",
    "/api/v1/finance/discounts",
    "/api/v1/lessons/series",
    "/api/v1/performance/top-improvers",
    "/api/v1/performance/declining",
    "/api/v1/performance/readiness",
    "/api/v1/competitions/records",
    "/api/v1/competitions/medals/summary",
]


@pytest.mark.parametrize("path", ORG_WIDE_PATHS)
def test_parent_denied_on_org_wide_endpoints(
    client: TestClient, linked_guardian, parent_headers: dict, path: str
) -> None:
    response = client.get(path, headers=parent_headers)
    assert response.status_code == 403, f"{path} -> {response.status_code}"
    assert response.json()["error"]["details"]["reason"] == "scope.org_wide_only"


def test_parent_denied_on_conflict_check(
    client: TestClient, linked_guardian, parent_headers: dict, pool, lanes, tomorrow_at
) -> None:
    response = client.post(
        "/api/v1/lessons/check-conflicts",
        headers=parent_headers,
        json={
            "start_at": tomorrow_at(19, 0).isoformat(),
            "end_at": tomorrow_at(20, 0).isoformat(),
            "pool_id": pool.id,
            "lane_id": lanes[1].id,
        },
    )
    assert response.status_code == 403


def test_parent_denied_on_competition_results(
    client: TestClient, linked_guardian, parent_headers: dict, admin_headers: dict
) -> None:
    created = client.post(
        "/api/v1/competitions",
        headers=admin_headers,
        json={
            "name": "Test Yarışması",
            "start_date": date.today().isoformat(),
            "end_date": date.today().isoformat(),
            "level": "club",
        },
    )
    assert created.status_code == 201, created.text
    competition_id = created.json()["id"]
    response = client.get(
        f"/api/v1/competitions/{competition_id}/results", headers=parent_headers
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 2. Satır bazlı süzme: başka ailenin kaydı listede görünmez
# ---------------------------------------------------------------------------
def test_outstanding_balances_only_own_children(
    client: TestClient, linked_guardian, parent_headers: dict, other_invoice: Invoice
) -> None:
    response = client.get("/api/v1/finance/outstanding", headers=parent_headers)
    assert response.status_code == 200
    body = response.json()
    student_ids = {item["student_id"] for item in body["items"]}
    assert other_invoice.student_id not in student_ids
    assert body["count"] == 0


def test_expiring_memberships_only_own_children(
    client: TestClient,
    linked_guardian,
    parent_headers: dict,
    other_membership: Membership,
) -> None:
    response = client.get("/api/v1/memberships/expiring", headers=parent_headers)
    assert response.status_code == 200
    assert all(
        item["student_id"] != other_membership.student_id for item in response.json()
    )


def test_low_credit_memberships_only_own_children(
    client: TestClient,
    linked_guardian,
    parent_headers: dict,
    other_membership: Membership,
) -> None:
    response = client.get("/api/v1/memberships/low-credit", headers=parent_headers)
    assert response.status_code == 200
    assert all(
        item["student_id"] != other_membership.student_id for item in response.json()
    )


def test_training_plans_only_own_children(
    client: TestClient, linked_guardian, parent_headers: dict, other_training_plan
) -> None:
    response = client.get("/api/v1/performance/training-plans", headers=parent_headers)
    assert response.status_code == 200
    assert all(
        item["student_id"] != other_training_plan.student_id for item in response.json()
    )


# ---------------------------------------------------------------------------
# 3. Nesne bazlı (IDOR) reddi
# ---------------------------------------------------------------------------
def test_membership_detail_idor_denied(
    client: TestClient,
    linked_guardian,
    parent_headers: dict,
    other_membership: Membership,
) -> None:
    response = client.get(
        f"/api/v1/memberships/{other_membership.id}", headers=parent_headers
    )
    assert response.status_code == 403
    assert response.json()["error"]["details"]["reason"] == "scope.student_forbidden"


def test_training_plan_filter_by_other_student_denied(
    client: TestClient, linked_guardian, parent_headers: dict, second_student: Student
) -> None:
    response = client.get(
        f"/api/v1/performance/training-plans?student_id={second_student.id}",
        headers=parent_headers,
    )
    assert response.status_code == 403


def test_lesson_detail_denied_when_child_not_enrolled(
    client: TestClient, linked_guardian, parent_headers: dict, other_lesson: Lesson
) -> None:
    response = client.get(f"/api/v1/lessons/{other_lesson.id}", headers=parent_headers)
    assert response.status_code == 403
    assert response.json()["error"]["details"]["reason"] == "scope.lesson_forbidden"


def test_lesson_roster_denied_when_child_not_enrolled(
    client: TestClient, linked_guardian, parent_headers: dict, other_lesson: Lesson
) -> None:
    response = client.get(
        f"/api/v1/lessons/{other_lesson.id}/roster", headers=parent_headers
    )
    assert response.status_code == 403


def test_attendance_sheet_denied_when_child_not_enrolled(
    client: TestClient, linked_guardian, parent_headers: dict, other_lesson: Lesson
) -> None:
    response = client.get(
        f"/api/v1/attendance/sheet/{other_lesson.id}", headers=parent_headers
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 4. Kendi çocuğuna erişim çalışır ve SINIFTAKİ DİĞER çocuklar görünmez
# ---------------------------------------------------------------------------
@pytest.fixture
def shared_lesson(
    db: Session, lesson: Lesson, student: Student, second_student: Student
) -> Lesson:
    db.add(
        LessonEnrollment(
            lesson_id=lesson.id, student_id=student.id, status=EnrollmentStatus.ENROLLED
        )
    )
    db.add(
        LessonEnrollment(
            lesson_id=lesson.id,
            student_id=second_student.id,
            status=EnrollmentStatus.ENROLLED,
        )
    )
    db.commit()
    return lesson


def test_roster_shows_only_own_child(
    client: TestClient,
    linked_guardian,
    parent_headers: dict,
    shared_lesson: Lesson,
    student: Student,
    second_student: Student,
) -> None:
    response = client.get(
        f"/api/v1/lessons/{shared_lesson.id}/roster", headers=parent_headers
    )
    assert response.status_code == 200
    ids = {row["student_id"] for row in response.json()}
    assert ids == {student.id}
    assert second_student.id not in ids


def test_attendance_sheet_shows_only_own_child(
    client: TestClient,
    linked_guardian,
    parent_headers: dict,
    shared_lesson: Lesson,
    student: Student,
    second_student: Student,
) -> None:
    response = client.get(
        f"/api/v1/attendance/sheet/{shared_lesson.id}", headers=parent_headers
    )
    assert response.status_code == 200
    ids = {row["student_id"] for row in response.json()["rows"]}
    assert ids == {student.id}


def test_lesson_detail_shows_only_own_child_enrollments(
    client: TestClient,
    linked_guardian,
    parent_headers: dict,
    shared_lesson: Lesson,
    student: Student,
    second_student: Student,
) -> None:
    response = client.get(f"/api/v1/lessons/{shared_lesson.id}", headers=parent_headers)
    assert response.status_code == 200
    ids = {row["student_id"] for row in response.json()["enrollments"]}
    assert ids == {student.id}


# ---------------------------------------------------------------------------
# 5. Yönetici için hiçbir kısıt yok (regresyon: kapsam fazla daraltmasın)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", ORG_WIDE_PATHS)
def test_admin_still_reaches_org_wide_endpoints(
    client: TestClient, admin_headers: dict, path: str
) -> None:
    response = client.get(path, headers=admin_headers)
    assert response.status_code == 200, f"{path} -> {response.text}"


def test_admin_sees_full_roster(
    client: TestClient,
    admin_headers: dict,
    shared_lesson: Lesson,
    student: Student,
    second_student: Student,
) -> None:
    response = client.get(
        f"/api/v1/lessons/{shared_lesson.id}/roster", headers=admin_headers
    )
    assert response.status_code == 200
    ids = {row["student_id"] for row in response.json()}
    assert ids == {student.id, second_student.id}
