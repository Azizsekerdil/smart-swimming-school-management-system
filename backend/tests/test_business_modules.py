"""İş modülleri testleri: yoklama, üyelik, finans, performans, yedekleme.

Business module tests: attendance, membership, finance, performance, backup.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.enums import (
    AttendanceStatus,
    LessonType,
    MembershipStatus,
    PaymentStatus,
)
from app.models.facility import Lane, Pool
from app.models.finance import Invoice, Payment
from app.models.lesson import Lesson, LessonEnrollment
from app.models.membership import Membership, Package
from app.models.people import Student
from app.models.performance import PersonalBest


# ===========================================================================
# Yoklama
# ===========================================================================
class TestAttendance:
    def test_sheet_lists_enrolled_students(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        lesson: Lesson,
        student: Student,
        second_student: Student,
    ):
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=second_student.id))
        db.commit()

        response = client.get(
            f"/api/v1/attendance/sheet/{lesson.id}", headers=admin_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["rows"]) == 2
        assert body["is_recorded"] is False

    def test_record_attendance(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        lesson: Lesson,
        student: Student,
    ):
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
        db.commit()

        response = client.post(
            "/api/v1/attendance",
            headers=admin_headers,
            json={
                "lesson_id": lesson.id,
                "method": "manual",
                "entries": [{"student_id": student.id, "status": "present"}],
            },
        )
        assert response.status_code == 201
        assert response.json()[0]["status"] == "present"

    def test_attendance_consumes_membership_credit(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        lesson: Lesson,
        student: Student,
        package: Package,
    ):
        membership = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() + timedelta(days=80),
            status=MembershipStatus.ACTIVE,
            total_credits=8,
            used_credits=0,
        )
        db.add(membership)
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
        db.commit()

        client.post(
            "/api/v1/attendance",
            headers=admin_headers,
            json={
                "lesson_id": lesson.id,
                "entries": [{"student_id": student.id, "status": "present"}],
                "consume_credits": True,
            },
        )
        db.refresh(membership)
        assert membership.used_credits == 1

    def test_absent_does_not_consume_credit(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        lesson: Lesson,
        student: Student,
        package: Package,
    ):
        membership = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today(),
            status=MembershipStatus.ACTIVE,
            total_credits=8,
            used_credits=0,
        )
        db.add(membership)
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
        db.commit()

        client.post(
            "/api/v1/attendance",
            headers=admin_headers,
            json={
                "lesson_id": lesson.id,
                "entries": [{"student_id": student.id, "status": "absent"}],
                "consume_credits": True,
            },
        )
        db.refresh(membership)
        assert membership.used_credits == 0

    def test_recording_twice_does_not_double_consume(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        lesson: Lesson,
        student: Student,
        package: Package,
    ):
        membership = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today(),
            status=MembershipStatus.ACTIVE,
            total_credits=8,
            used_credits=0,
        )
        db.add(membership)
        db.add(LessonEnrollment(lesson_id=lesson.id, student_id=student.id))
        db.commit()

        payload = {
            "lesson_id": lesson.id,
            "entries": [{"student_id": student.id, "status": "present"}],
            "consume_credits": True,
        }
        client.post("/api/v1/attendance", headers=admin_headers, json=payload)
        client.post("/api/v1/attendance", headers=admin_headers, json=payload)

        db.refresh(membership)
        assert membership.used_credits == 1, "Aynı ders iki kez hak düşürmemeli"

    def test_student_summary(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        pool: Pool,
        lanes: list[Lane],
        student: Student,
    ):
        yesterday = datetime.combine(date.today() - timedelta(days=1), time(17, 0))
        lesson = Lesson(
            title="Geçmiş",
            lesson_type=LessonType.GROUP,
            start_at=yesterday,
            end_at=yesterday + timedelta(hours=1),
            pool_id=pool.id,
            lane_id=lanes[0].id,
        )
        db.add(lesson)
        db.flush()
        db.add(
            Attendance(
                lesson_id=lesson.id,
                student_id=student.id,
                status=AttendanceStatus.PRESENT,
            )
        )
        db.commit()

        response = client.get(
            f"/api/v1/attendance/student/{student.id}/summary", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["attendance_rate"] == 100.0


# ===========================================================================
# Üyelik
# ===========================================================================
class TestMembership:
    def test_create_membership_computes_end_date(
        self,
        client: TestClient,
        admin_headers: dict,
        student: Student,
        package: Package,
    ):
        response = client.post(
            "/api/v1/memberships",
            headers=admin_headers,
            json={"student_id": student.id, "package_id": package.id},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["total_credits"] == 8
        assert body["remaining_credits"] == 8
        expected_end = date.today() + timedelta(days=90)
        assert body["end_date"] == expected_end.isoformat()

    def test_create_with_payment(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        student: Student,
        package: Package,
    ):
        response = client.post(
            "/api/v1/memberships",
            headers=admin_headers,
            json={
                "student_id": student.id,
                "package_id": package.id,
                "create_payment": True,
                "payment_method": "cash",
            },
        )
        assert response.status_code == 201
        payments = db.query(Payment).filter(Payment.student_id == student.id).all()
        assert len(payments) == 1
        assert float(payments[0].amount) == 3000.0

    def test_discount_cannot_exceed_price(
        self,
        client: TestClient,
        admin_headers: dict,
        student: Student,
        package: Package,
    ):
        response = client.post(
            "/api/v1/memberships",
            headers=admin_headers,
            json={
                "student_id": student.id,
                "package_id": package.id,
                "discount_amount": 5000,
            },
        )
        assert response.status_code == 422

    def test_freeze_extends_end_date(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        student: Student,
        package: Package,
    ):
        membership = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status=MembershipStatus.ACTIVE,
            total_credits=8,
        )
        db.add(membership)
        db.commit()
        original_end = membership.end_date

        response = client.post(
            f"/api/v1/memberships/{membership.id}/freeze",
            headers=admin_headers,
            json={
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=9)).isoformat(),
                "reason": "Hastalık",
            },
        )
        assert response.status_code == 200
        db.refresh(membership)
        assert membership.end_date == original_end + timedelta(days=10)
        assert membership.status == MembershipStatus.FROZEN

    def test_freeze_limit_enforced(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        student: Student,
        package: Package,
    ):
        package.max_freeze_days = 5
        membership = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            status=MembershipStatus.ACTIVE,
        )
        db.add(membership)
        db.commit()

        response = client.post(
            f"/api/v1/memberships/{membership.id}/freeze",
            headers=admin_headers,
            json={
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=30)).isoformat(),
            },
        )
        assert response.status_code == 422

    def test_renew_creates_new_and_expires_old(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        student: Student,
        package: Package,
    ):
        old = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today() - timedelta(days=90),
            end_date=date.today(),
            status=MembershipStatus.ACTIVE,
            total_credits=8,
            used_credits=8,
        )
        db.add(old)
        db.commit()

        response = client.post(
            f"/api/v1/memberships/{old.id}/renew", headers=admin_headers, json={}
        )
        assert response.status_code == 200
        db.refresh(old)
        assert old.status == MembershipStatus.EXPIRED
        assert response.json()["used_credits"] == 0

    def test_refresh_statuses_expires_out_of_credit(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        student: Student,
        package: Package,
    ):
        membership = Membership(
            student_id=student.id,
            package_id=package.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            status=MembershipStatus.ACTIVE,
            total_credits=8,
            used_credits=8,
        )
        db.add(membership)
        db.commit()

        response = client.post(
            "/api/v1/memberships/refresh-statuses", headers=admin_headers
        )
        assert response.status_code == 200
        db.refresh(membership)
        assert membership.status == MembershipStatus.EXPIRED

    def test_expiring_endpoint(
        self,
        client: TestClient,
        admin_headers: dict,
        db: Session,
        student: Student,
        package: Package,
    ):
        db.add(
            Membership(
                student_id=student.id,
                package_id=package.id,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=7),
                status=MembershipStatus.ACTIVE,
            )
        )
        db.commit()
        response = client.get(
            "/api/v1/memberships/expiring", headers=admin_headers, params={"days": 14}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1


# ===========================================================================
# Finans
# ===========================================================================
class TestFinance:
    def test_create_payment(
        self, client: TestClient, finance_headers: dict, student: Student
    ):
        response = client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={"student_id": student.id, "amount": 1500, "method": "cash"},
        )
        assert response.status_code == 201
        assert response.json()["receipt_number"].startswith("FIS")

    def test_zero_amount_rejected(
        self, client: TestClient, finance_headers: dict, student: Student
    ):
        response = client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={"student_id": student.id, "amount": 0, "method": "cash"},
        )
        assert response.status_code == 422

    def test_payment_updates_invoice_balance(
        self, client: TestClient, finance_headers: dict, db: Session, student: Student
    ):
        invoice = Invoice(
            invoice_number="FT000001",
            student_id=student.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=1000,
            total_amount=1000,
            paid_amount=0,
            status=PaymentStatus.PENDING,
        )
        db.add(invoice)
        db.commit()

        client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={
                "student_id": student.id,
                "invoice_id": invoice.id,
                "amount": 1000,
                "method": "card",
            },
        )
        db.refresh(invoice)
        assert float(invoice.paid_amount) == 1000.0
        assert invoice.status == PaymentStatus.PAID

    def test_partial_payment_sets_partial_status(
        self, client: TestClient, finance_headers: dict, db: Session, student: Student
    ):
        invoice = Invoice(
            invoice_number="FT000002",
            student_id=student.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            subtotal=1000,
            total_amount=1000,
            paid_amount=0,
            status=PaymentStatus.PENDING,
        )
        db.add(invoice)
        db.commit()

        client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={
                "student_id": student.id,
                "invoice_id": invoice.id,
                "amount": 400,
                "method": "cash",
            },
        )
        db.refresh(invoice)
        assert invoice.status == PaymentStatus.PARTIAL
        assert invoice.balance == 600.0

    def test_overpayment_rejected(
        self, client: TestClient, finance_headers: dict, db: Session, student: Student
    ):
        invoice = Invoice(
            invoice_number="FT000003",
            student_id=student.id,
            issue_date=date.today(),
            due_date=date.today(),
            subtotal=500,
            total_amount=500,
            paid_amount=0,
            status=PaymentStatus.PENDING,
        )
        db.add(invoice)
        db.commit()

        response = client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={
                "student_id": student.id,
                "invoice_id": invoice.id,
                "amount": 900,
                "method": "cash",
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "payment.exceeds_balance"

    def test_refund_reduces_net(
        self, client: TestClient, finance_headers: dict, db: Session, student: Student
    ):
        created = client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={"student_id": student.id, "amount": 1000, "method": "cash"},
        ).json()

        response = client.post(
            f"/api/v1/finance/payments/{created['id']}/refund",
            headers=finance_headers,
            json={"amount": 300, "reason": "Kısmi iade"},
        )
        assert response.status_code == 200
        assert response.json()["net_amount"] == 700.0

    def test_refund_cannot_exceed_payment(
        self, client: TestClient, finance_headers: dict, student: Student
    ):
        created = client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={"student_id": student.id, "amount": 100, "method": "cash"},
        ).json()

        response = client.post(
            f"/api/v1/finance/payments/{created['id']}/refund",
            headers=finance_headers,
            json={"amount": 500, "reason": "Fazla"},
        )
        assert response.status_code == 422

    def test_outstanding_aging_buckets(
        self, client: TestClient, finance_headers: dict, db: Session, student: Student
    ):
        db.add(
            Invoice(
                invoice_number="FT000010",
                student_id=student.id,
                issue_date=date.today() - timedelta(days=50),
                due_date=date.today() - timedelta(days=45),
                subtotal=1000,
                total_amount=1000,
                paid_amount=0,
                status=PaymentStatus.PENDING,
            )
        )
        db.commit()

        response = client.get("/api/v1/finance/outstanding", headers=finance_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["aging"]["31_60"] == 1000.0
        assert body["total_outstanding"] == 1000.0

    def test_summary_computes_net(
        self, client: TestClient, finance_headers: dict, student: Student
    ):
        client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={"student_id": student.id, "amount": 5000, "method": "cash"},
        )
        client.post(
            "/api/v1/finance/expenses",
            headers=finance_headers,
            json={"title": "Kimyasal", "category": "chemicals", "amount": 1200},
        )

        response = client.get("/api/v1/finance/summary", headers=finance_headers)
        body = response.json()
        assert body["total_income"] == 5000.0
        assert body["total_expense"] == 1200.0
        assert body["net_income"] == 3800.0

    def test_reception_cannot_delete_payment(
        self,
        client: TestClient,
        reception_headers: dict,
        finance_headers: dict,
        student: Student,
    ):
        created = client.post(
            "/api/v1/finance/payments",
            headers=finance_headers,
            json={"student_id": student.id, "amount": 100, "method": "cash"},
        ).json()
        response = client.delete(
            f"/api/v1/finance/payments/{created['id']}",
            headers=reception_headers,
            params={"reason": "test"},
        )
        assert response.status_code == 403


# ===========================================================================
# Performans
# ===========================================================================
class TestPerformanceAPI:
    def test_create_record_sets_personal_best(
        self, client: TestClient, admin_headers: dict, db: Session, student: Student
    ):
        response = client.post(
            "/api/v1/performance",
            headers=admin_headers,
            json={
                "student_id": student.id,
                "stroke": "freestyle",
                "distance_m": 50,
                "time_seconds": 35.5,
                "recorded_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 201
        assert response.json()["is_personal_best"] is True
        assert db.query(PersonalBest).count() == 1

    def test_faster_time_updates_personal_best(
        self, client: TestClient, admin_headers: dict, db: Session, student: Student
    ):
        base = {
            "student_id": student.id,
            "stroke": "freestyle",
            "distance_m": 50,
            "recorded_date": date.today().isoformat(),
        }
        client.post(
            "/api/v1/performance",
            headers=admin_headers,
            json={**base, "time_seconds": 35.5},
        )
        response = client.post(
            "/api/v1/performance",
            headers=admin_headers,
            json={**base, "time_seconds": 34.0},
        )
        assert response.json()["is_personal_best"] is True

        best = db.query(PersonalBest).one()
        assert float(best.time_seconds) == 34.0
        assert db.query(PersonalBest).count() == 1

    def test_slower_time_not_personal_best(
        self, client: TestClient, admin_headers: dict, student: Student
    ):
        base = {
            "student_id": student.id,
            "stroke": "freestyle",
            "distance_m": 50,
            "recorded_date": date.today().isoformat(),
        }
        client.post(
            "/api/v1/performance",
            headers=admin_headers,
            json={**base, "time_seconds": 34.0},
        )
        response = client.post(
            "/api/v1/performance",
            headers=admin_headers,
            json={**base, "time_seconds": 36.0},
        )
        assert response.json()["is_personal_best"] is False

    def test_formatted_time_in_response(
        self, client: TestClient, admin_headers: dict, student: Student
    ):
        response = client.post(
            "/api/v1/performance",
            headers=admin_headers,
            json={
                "student_id": student.id,
                "stroke": "freestyle",
                "distance_m": 100,
                "time_seconds": 95.12,
                "recorded_date": date.today().isoformat(),
            },
        )
        assert response.json()["formatted_time"] == "1:35.12"

    def test_events_catalog(self, client: TestClient, admin_headers: dict):
        response = client.get(
            "/api/v1/performance/events/catalog", headers=admin_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["strokes"]) == 5
        assert 50 in body["distances"]

    def test_instructor_can_write_performance(
        self, client: TestClient, instructor_headers: dict, student: Student
    ):
        response = client.post(
            "/api/v1/performance",
            headers=instructor_headers,
            json={
                "student_id": student.id,
                "stroke": "backstroke",
                "distance_m": 50,
                "time_seconds": 40.0,
                "recorded_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 201


# ===========================================================================
# Yedekleme
# ===========================================================================
class TestBackup:
    def test_status_when_no_backups(self, client: TestClient, admin_headers: dict):
        response = client.get("/api/v1/backup/status", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total_backup_count"] == 0
        assert body["status"] == "never"

    def test_restore_requires_confirmation(
        self, client: TestClient, admin_headers: dict
    ):
        response = client.post(
            "/api/v1/backup/restore",
            headers=admin_headers,
            json={"backup_id": "bkp_test", "confirm": False},
        )
        assert response.status_code == 422
        assert "confirmation_required" in str(response.json())

    def test_restore_unknown_backup_404(self, client: TestClient, admin_headers: dict):
        response = client.post(
            "/api/v1/backup/restore",
            headers=admin_headers,
            json={"backup_id": "bkp_yok", "confirm": True},
        )
        assert response.status_code == 404

    def test_verify_unknown_backup_404(self, client: TestClient, admin_headers: dict):
        response = client.post("/api/v1/backup/bkp_yok/verify", headers=admin_headers)
        assert response.status_code == 404

    def test_reception_cannot_restore(
        self, client: TestClient, reception_headers: dict
    ):
        response = client.post(
            "/api/v1/backup/restore",
            headers=reception_headers,
            json={"backup_id": "bkp_x", "confirm": True},
        )
        assert response.status_code == 403

    def test_backup_location_endpoint(self, client: TestClient, admin_headers: dict):
        response = client.get("/api/v1/backup/location/open", headers=admin_headers)
        assert response.status_code == 200
        assert "path" in response.json()


# ===========================================================================
# Öğrenci / eğitmen CRUD
# ===========================================================================
class TestStudentCRUD:
    def test_auto_student_number(self, client: TestClient, admin_headers: dict):
        response = client.post(
            "/api/v1/students",
            headers=admin_headers,
            json={"first_name": "Yeni", "last_name": "Öğrenci"},
        )
        assert response.status_code == 201
        assert response.json()["student_number"].startswith("OGR")

    def test_duplicate_number_rejected(
        self, client: TestClient, admin_headers: dict, student: Student
    ):
        response = client.post(
            "/api/v1/students",
            headers=admin_headers,
            json={
                "first_name": "Kopya",
                "last_name": "Test",
                "student_number": student.student_number,
            },
        )
        assert response.status_code == 409

    def test_future_birth_date_rejected(self, client: TestClient, admin_headers: dict):
        response = client.post(
            "/api/v1/students",
            headers=admin_headers,
            json={
                "first_name": "Gelecek",
                "last_name": "Test",
                "birth_date": (date.today() + timedelta(days=1)).isoformat(),
            },
        )
        assert response.status_code == 422

    def test_soft_delete_sets_passive(
        self, client: TestClient, admin_headers: dict, db: Session, student: Student
    ):
        response = client.delete(
            f"/api/v1/students/{student.id}", headers=admin_headers
        )
        assert response.status_code == 200
        db.refresh(student)
        assert student.status == "passive"
        assert student.left_date is not None

    def test_hard_delete_removes(
        self, client: TestClient, admin_headers: dict, db: Session, student: Student
    ):
        student_id = student.id
        response = client.delete(
            f"/api/v1/students/{student_id}",
            headers=admin_headers,
            params={"hard": True},
        )
        assert response.status_code == 200
        assert db.get(Student, student_id) is None

    def test_search_by_name(
        self, client: TestClient, admin_headers: dict, student: Student
    ):
        response = client.get(
            "/api/v1/students", headers=admin_headers, params={"q": student.first_name}
        )
        assert response.json()["total"] >= 1

    def test_filter_by_status(
        self, client: TestClient, admin_headers: dict, student: Student  # noqa: ARG002
    ):
        response = client.get(
            "/api/v1/students", headers=admin_headers, params={"status": "left"}
        )
        assert response.json()["total"] == 0

    def test_pagination(
        self, client: TestClient, admin_headers: dict, student, second_student
    ):  # noqa: ARG002
        response = client.get(
            "/api/v1/students",
            headers=admin_headers,
            params={"page": 1, "page_size": 1},
        )
        body = response.json()
        assert len(body["items"]) == 1
        assert body["total"] == 2

    def test_detail_includes_computed_fields(
        self, client: TestClient, admin_headers: dict, student: Student
    ):
        response = client.get(f"/api/v1/students/{student.id}", headers=admin_headers)
        body = response.json()
        assert body["age"] is not None
        assert body["full_name"] == f"{student.first_name} {student.last_name}"
        assert "outstanding_balance" in body

    def test_not_found_returns_404(self, client: TestClient, admin_headers: dict):
        response = client.get("/api/v1/students/999999", headers=admin_headers)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "student.not_found"


class TestPoolCRUD:
    def test_create_pool_generates_lanes(
        self, client: TestClient, admin_headers: dict, db: Session
    ):
        response = client.post(
            "/api/v1/pools",
            headers=admin_headers,
            json={
                "name": "Yeni Havuz",
                "length_m": 50,
                "lane_count": 8,
                "auto_create_lanes": True,
            },
        )
        assert response.status_code == 201
        pool_id = response.json()["id"]
        assert db.query(Lane).filter(Lane.pool_id == pool_id).count() == 8

    def test_duplicate_pool_name_rejected(
        self, client: TestClient, admin_headers: dict, pool: Pool
    ):
        response = client.post(
            "/api/v1/pools",
            headers=admin_headers,
            json={"name": pool.name, "lane_count": 4},
        )
        assert response.status_code == 409

    def test_closing_before_opening_rejected(
        self, client: TestClient, admin_headers: dict
    ):
        response = client.post(
            "/api/v1/pools",
            headers=admin_headers,
            json={
                "name": "Hatalı Havuz",
                "opening_time": "22:00:00",
                "closing_time": "08:00:00",
            },
        )
        assert response.status_code == 422

    def test_cannot_delete_pool_with_lessons(
        self,
        client: TestClient,
        admin_headers: dict,
        pool: Pool,
        lesson: Lesson,  # noqa: ARG002
    ):
        response = client.delete(f"/api/v1/pools/{pool.id}", headers=admin_headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "common.in_use"

    def test_water_quality_out_of_range_flagged(
        self, client: TestClient, admin_headers: dict, pool: Pool
    ):
        response = client.post(
            "/api/v1/pools/water-quality",
            headers=admin_headers,
            json={
                "pool_id": pool.id,
                "measured_at": datetime.now().isoformat(),
                "ph": 9.5,
                "chlorine_ppm": 1.0,
            },
        )
        assert response.status_code == 201
        assert response.json()["is_within_limits"] is False


class TestReportsAPI:
    def test_definitions_filtered_by_permission(
        self, client: TestClient, instructor_headers: dict, admin_headers: dict
    ):
        admin_reports = client.get(
            "/api/v1/reports/definitions", headers=admin_headers
        ).json()
        instructor_reports = client.get(
            "/api/v1/reports/definitions", headers=instructor_headers
        ).json()
        assert len(admin_reports) > len(instructor_reports)

    def test_preview_student_list(
        self, client: TestClient, admin_headers: dict, student: Student  # noqa: ARG002
    ):
        response = client.post(
            "/api/v1/reports/preview",
            headers=admin_headers,
            json={"report_key": "student_list", "format": "json", "language": "tr"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["row_count"] >= 1
        assert len(body["columns"]) > 3

    def test_unknown_report_404(self, client: TestClient, admin_headers: dict):
        response = client.post(
            "/api/v1/reports/preview",
            headers=admin_headers,
            json={"report_key": "olmayan_rapor", "format": "json"},
        )
        assert response.status_code == 404

    @pytest.mark.parametrize("export_format", ["csv", "xlsx", "pdf"])
    def test_export_formats(
        self,
        client: TestClient,
        admin_headers: dict,
        student: Student,
        export_format: str,  # noqa: ARG002
    ):
        response = client.post(
            "/api/v1/reports/export",
            headers=admin_headers,
            json={
                "report_key": "student_list",
                "format": export_format,
                "language": "tr",
            },
        )
        assert response.status_code == 200
        assert len(response.content) > 100
        assert "attachment" in response.headers["content-disposition"]

    def test_csv_has_utf8_bom(
        self, client: TestClient, admin_headers: dict, student: Student  # noqa: ARG002
    ):
        """Excel'in Türkçe karakterleri doğru açması için BOM gerekir."""
        response = client.post(
            "/api/v1/reports/export",
            headers=admin_headers,
            json={"report_key": "student_list", "format": "csv", "language": "tr"},
        )
        assert response.content.startswith(b"\xef\xbb\xbf")

    def test_pdf_magic_bytes(
        self, client: TestClient, admin_headers: dict, student: Student  # noqa: ARG002
    ):
        response = client.post(
            "/api/v1/reports/export",
            headers=admin_headers,
            json={"report_key": "student_list", "format": "pdf", "language": "tr"},
        )
        assert response.content.startswith(b"%PDF")

    def test_export_requires_permission(
        self, client: TestClient, instructor_headers: dict
    ):
        response = client.post(
            "/api/v1/reports/export",
            headers=instructor_headers,
            json={"report_key": "finance", "format": "pdf"},
        )
        assert response.status_code == 403


class TestI18nCompleteness:
    def test_no_missing_backend_translations(
        self, client: TestClient, admin_headers: dict
    ):
        response = client.get("/api/v1/i18n/validate", headers=admin_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["is_complete"] is True, f"Eksik çeviriler: {body['missing']}"

    def test_health_endpoint_public(self, client: TestClient):
        assert client.get("/api/v1/health").status_code == 200

    def test_about_endpoint(self, client: TestClient, admin_headers: dict):
        response = client.get("/api/v1/about", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["license"] == "MIT"
