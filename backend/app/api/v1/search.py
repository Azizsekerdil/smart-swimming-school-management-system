"""Global arama ve komut paleti / Global search and command palette."""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import AccessScope, db_session, get_language, get_scope
from app.core.permissions import Perm
from app.models.competition import Competition
from app.models.facility import Pool
from app.models.finance import Invoice, Payment
from app.models.lesson import Lesson
from app.models.membership import Package
from app.models.people import Group, Guardian, Instructor, Student
from app.schemas.system import SearchHit, SearchResponse

router = APIRouter(prefix="/search", tags=["Arama"])


def _like(term: str) -> str:
    return f"%{term.lower()}%"


@router.get("", response_model=SearchResponse, summary="Global arama")
def global_search(
    q: str,
    limit: int = 8,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
) -> SearchResponse:
    """Öğrenci, veli, eğitmen, ders, ödeme ve daha fazlasında arama yapar.

    Sonuçlar kullanıcının izinlerine göre filtrelenir.
    """
    started = time.perf_counter()
    groups: dict[str, list[SearchHit]] = {}
    user = scope.user
    term = q.strip()

    if len(term) < 2:
        return SearchResponse(query=q, total=0, groups={}, took_ms=0)

    pattern = _like(term)
    allowed_students = scope.allowed_student_ids()

    # --- Öğrenciler ---
    if user.has_permission(Perm.STUDENT_READ):
        stmt = select(Student).where(
            or_(
                func.lower(Student.first_name).like(pattern),
                func.lower(Student.last_name).like(pattern),
                func.lower(Student.student_number).like(pattern),
                func.lower(func.coalesce(Student.phone, "")).like(pattern),
                func.lower(func.coalesce(Student.email, "")).like(pattern),
            )
        )
        if allowed_students is not None:
            stmt = stmt.where(Student.id.in_(allowed_students))
        hits = [
            SearchHit(
                entity_type="student",
                id=s.id,
                title=s.full_name,
                subtitle=f"{s.student_number} · {s.swim_level}"
                + (f" · {s.age} yaş" if s.age else ""),
                route=f"/students/{s.id}",
                badge=s.status,
                score=2.0 if term.lower() in s.full_name.lower() else 1.0,
            )
            for s in db.scalars(stmt.limit(limit)).all()
        ]
        if hits:
            groups["students"] = hits

    # --- Veliler ---
    if user.has_permission(Perm.GUARDIAN_READ):
        hits = [
            SearchHit(
                entity_type="guardian",
                id=g.id,
                title=g.full_name,
                subtitle=f"{g.phone} · {len(g.students)} öğrenci",
                route=f"/guardians/{g.id}",
                badge=g.relationship_type,
                score=1.5,
            )
            for g in db.scalars(
                select(Guardian)
                .where(
                    or_(
                        func.lower(Guardian.first_name).like(pattern),
                        func.lower(Guardian.last_name).like(pattern),
                        func.lower(Guardian.phone).like(pattern),
                        func.lower(func.coalesce(Guardian.email, "")).like(pattern),
                    )
                )
                .limit(limit)
            ).all()
        ]
        if hits:
            groups["guardians"] = hits

    # --- Eğitmenler ---
    if user.has_permission(Perm.INSTRUCTOR_READ):
        hits = [
            SearchHit(
                entity_type="instructor",
                id=i.id,
                title=i.full_name,
                subtitle=f"{i.employee_number}" + (f" · {i.title}" if i.title else ""),
                route=f"/instructors/{i.id}",
                badge="aktif" if i.is_active else "pasif",
                score=1.5,
            )
            for i in db.scalars(
                select(Instructor)
                .where(
                    or_(
                        func.lower(Instructor.first_name).like(pattern),
                        func.lower(Instructor.last_name).like(pattern),
                        func.lower(Instructor.employee_number).like(pattern),
                        func.lower(func.coalesce(Instructor.email, "")).like(pattern),
                    )
                )
                .limit(limit)
            ).all()
        ]
        if hits:
            groups["instructors"] = hits

    # --- Dersler (yakın tarihli) ---
    if user.has_permission(Perm.LESSON_READ):
        window_start = datetime.now() - timedelta(days=30)
        hits = [
            SearchHit(
                entity_type="lesson",
                id=lesson.id,
                title=lesson.title,
                subtitle=(
                    f"{lesson.start_at:%d.%m.%Y %H:%M}"
                    + (f" · {lesson.pool.name}" if lesson.pool else "")
                    + (f" · {lesson.instructor.full_name}" if lesson.instructor else "")
                ),
                route=f"/calendar?lesson={lesson.id}",
                badge=lesson.status,
                score=1.0,
            )
            for lesson in db.scalars(
                select(Lesson)
                .where(
                    func.lower(Lesson.title).like(pattern),
                    Lesson.start_at >= window_start,
                )
                .order_by(Lesson.start_at.desc())
                .limit(limit)
            ).all()
        ]
        if hits:
            groups["lessons"] = hits

    # --- Ödemeler ---
    if user.has_permission(Perm.FINANCE_READ):
        stmt = (
            select(Payment)
            .join(Student, Student.id == Payment.student_id, isouter=True)
            .where(
                or_(
                    func.lower(Payment.receipt_number).like(pattern),
                    func.lower(func.coalesce(Payment.description, "")).like(pattern),
                    func.lower(Student.first_name).like(pattern),
                    func.lower(Student.last_name).like(pattern),
                )
            )
        )
        if allowed_students is not None:
            stmt = stmt.where(Payment.student_id.in_(allowed_students))
        hits = [
            SearchHit(
                entity_type="payment",
                id=p.id,
                title=f"{float(p.amount):,.2f} {p.currency} · {p.receipt_number}",
                subtitle=(
                    f"{p.payment_date:%d.%m.%Y} · {p.method}"
                    + (f" · {p.student.full_name}" if p.student else "")
                ),
                route=f"/finance/payments/{p.id}",
                badge=p.status,
                score=1.0,
            )
            for p in db.scalars(
                stmt.order_by(Payment.payment_date.desc()).limit(limit)
            ).all()
        ]
        if hits:
            groups["payments"] = hits

    # --- Üyelik / paket ---
    if user.has_permission(Perm.MEMBERSHIP_READ):
        hits = [
            SearchHit(
                entity_type="package",
                id=p.id,
                title=p.name,
                subtitle=f"{float(p.price):,.2f} {p.currency}"
                + (f" · {p.lesson_count} ders" if p.lesson_count else ""),
                route="/memberships?tab=packages",
                badge="aktif" if p.is_active else "pasif",
                score=0.8,
            )
            for p in db.scalars(
                select(Package)
                .where(func.lower(Package.name).like(pattern))
                .limit(limit)
            ).all()
        ]
        if hits:
            groups["packages"] = hits

    # --- Havuz / grup / yarışma ---
    if user.has_permission(Perm.POOL_READ):
        hits = [
            SearchHit(
                entity_type="pool",
                id=p.id,
                title=p.name,
                subtitle=f"{p.lane_count} kulvar · {p.length_m} m",
                route=f"/pools/{p.id}",
                badge=p.status,
                score=0.8,
            )
            for p in db.scalars(
                select(Pool).where(func.lower(Pool.name).like(pattern)).limit(limit)
            ).all()
        ]
        if hits:
            groups["pools"] = hits

    if user.has_permission(Perm.STUDENT_READ):
        hits = [
            SearchHit(
                entity_type="group",
                id=g.id,
                title=g.name,
                subtitle=f"{g.level} · kapasite {g.capacity}",
                route=f"/students?group={g.id}",
                score=0.7,
            )
            for g in db.scalars(
                select(Group).where(func.lower(Group.name).like(pattern)).limit(limit)
            ).all()
        ]
        if hits:
            groups["groups"] = hits

    if user.has_permission(Perm.COMPETITION_READ):
        hits = [
            SearchHit(
                entity_type="competition",
                id=c.id,
                title=c.name,
                subtitle=f"{c.start_date:%d.%m.%Y}"
                + (f" · {c.location}" if c.location else ""),
                route=f"/competitions/{c.id}",
                badge=c.level,
                score=0.7,
            )
            for c in db.scalars(
                select(Competition)
                .where(func.lower(Competition.name).like(pattern))
                .order_by(Competition.start_date.desc())
                .limit(limit)
            ).all()
        ]
        if hits:
            groups["competitions"] = hits

    total = sum(len(hits) for hits in groups.values())
    return SearchResponse(
        query=q,
        total=total,
        groups=groups,
        took_ms=int((time.perf_counter() - started) * 1000),
    )


@router.get("/commands", summary="Komut paleti komutları")
def command_palette(
    scope: AccessScope = Depends(get_scope),
    lang: str = Depends(get_language),
) -> dict:
    """Ctrl+K komut paleti için kullanıcının yetkili olduğu komutlar."""
    user = scope.user
    catalog = [
        (
            "new_student",
            Perm.STUDENT_WRITE,
            "Yeni öğrenci",
            "New student",
            "/students?action=new",
            "user-plus",
        ),
        (
            "new_guardian",
            Perm.GUARDIAN_WRITE,
            "Yeni veli",
            "New guardian",
            "/guardians?action=new",
            "users",
        ),
        (
            "new_instructor",
            Perm.INSTRUCTOR_WRITE,
            "Yeni eğitmen",
            "New instructor",
            "/instructors?action=new",
            "award",
        ),
        (
            "new_lesson",
            Perm.LESSON_WRITE,
            "Yeni ders",
            "New lesson",
            "/calendar?action=new",
            "calendar-plus",
        ),
        (
            "new_series",
            Perm.LESSON_SCHEDULE,
            "Tekrarlanan ders",
            "Recurring lesson",
            "/calendar?action=series",
            "repeat",
        ),
        (
            "take_attendance",
            Perm.ATTENDANCE_WRITE,
            "Yoklama al",
            "Take attendance",
            "/attendance",
            "check-square",
        ),
        (
            "new_payment",
            Perm.FINANCE_WRITE,
            "Yeni ödeme",
            "New payment",
            "/finance?action=new-payment",
            "credit-card",
        ),
        (
            "new_membership",
            Perm.MEMBERSHIP_WRITE,
            "Yeni üyelik",
            "New membership",
            "/memberships?action=new",
            "id-card",
        ),
        (
            "new_performance",
            Perm.PERFORMANCE_WRITE,
            "Performans kaydı",
            "Performance record",
            "/performance?action=new",
            "timer",
        ),
        (
            "new_competition",
            Perm.COMPETITION_WRITE,
            "Yeni yarışma",
            "New competition",
            "/competitions?action=new",
            "trophy",
        ),
        (
            "lane_plan",
            Perm.POOL_READ,
            "Kulvar planı",
            "Lane plan",
            "/pools?tab=lane-plan",
            "grid",
        ),
        (
            "ai_analysis",
            Perm.AI_USE,
            "AI analizi",
            "AI analysis",
            "/ai?tab=analysis",
            "sparkles",
        ),
        (
            "ai_developer",
            Perm.AI_DEVELOPER,
            "AI Developer Console",
            "AI Developer Console",
            "/ai-developer",
            "terminal",
        ),
        ("caio", Perm.AI_CAIO, "CAIO raporu", "CAIO report", "/caio", "brain"),
        (
            "create_report",
            Perm.REPORT_READ,
            "Rapor oluştur",
            "Create report",
            "/reports",
            "file-text",
        ),
        (
            "statistics",
            Perm.STATISTICS_READ,
            "İstatistik merkezi",
            "Statistics center",
            "/statistics",
            "bar-chart",
        ),
        (
            "backup_now",
            Perm.BACKUP_CREATE,
            "Şimdi yedekle",
            "Backup now",
            "/settings?tab=backup",
            "hard-drive",
        ),
        (
            "open_settings",
            Perm.SETTINGS_READ,
            "Ayarları aç",
            "Open settings",
            "/settings",
            "settings",
        ),
        (
            "audit_log",
            Perm.AUDIT_READ,
            "Denetim kaydı",
            "Audit log",
            "/settings?tab=audit",
            "shield",
        ),
        (
            "training_center",
            Perm.SELF_PORTAL,
            "Eğitim merkezi",
            "Training center",
            "/training",
            "graduation-cap",
        ),
        (
            "user_guide",
            Perm.SELF_PORTAL,
            "Kullanım kılavuzu",
            "User guide",
            "/help",
            "book-open",
        ),
    ]

    commands = [
        {
            "id": key,
            "label": label_tr if lang == "tr" else label_en,
            "route": route,
            "icon": icon,
        }
        for key, permission, label_tr, label_en, route, icon in catalog
        if user.has_permission(permission)
    ]
    return {"commands": commands, "count": len(commands)}


@router.get("/quick-stats", summary="Arama kutusu hızlı sayaçları")
def quick_stats(
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
) -> dict:
    """Arama açıldığında gösterilecek hızlı bağlam bilgisi."""
    from app.models.enums import StudentStatus

    today = date.today()
    result: dict = {}
    if scope.user.has_permission(Perm.STUDENT_READ):
        result["active_students"] = (
            db.scalar(
                select(func.count(Student.id)).where(
                    Student.status == StudentStatus.ACTIVE
                )
            )
            or 0
        )
    if scope.user.has_permission(Perm.LESSON_READ):
        result["lessons_today"] = (
            db.scalar(
                select(func.count(Lesson.id)).where(
                    Lesson.start_at >= datetime.combine(today, datetime.min.time()),
                    Lesson.start_at <= datetime.combine(today, datetime.max.time()),
                )
            )
            or 0
        )
    if scope.user.has_permission(Perm.FINANCE_READ):
        result["overdue_invoices"] = (
            db.scalar(
                select(func.count(Invoice.id)).where(
                    Invoice.due_date < today, Invoice.total_amount > Invoice.paid_amount
                )
            )
            or 0
        )
    return result
