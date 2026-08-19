"""Sporcu performans uçları / Athlete performance endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import (
    AccessScope,
    db_session,
    get_language,
    get_scope,
    pagination,
    require_org_wide_scope,
    require_permissions,
)
from app.core.exceptions import PermissionDeniedError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.enums import CourseType, Stroke
from app.models.people import Student
from app.models.performance import PerformanceRecord, PersonalBest, TrainingPlan
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.performance import (
    STANDARD_DISTANCES,
    DecliningAthleteRow,
    PerformanceCreate,
    PerformanceEventAnalysis,
    PerformanceOut,
    PerformanceUpdate,
    PersonalBestOut,
    StudentPerformanceSummary,
    TopImproverRow,
    TrainingPlanCreate,
    TrainingPlanOut,
)
from app.services import audit
from app.services.crud import get_or_404, paginate
from app.services.formatting import format_swim_time
from app.services.statistics_engine import (
    analyze_event,
    competition_readiness,
    find_declining_athletes,
    find_top_improvers,
    student_performance_summary,
)

router = APIRouter(prefix="/performance", tags=["Performans"])


def _decorate(record: PerformanceRecord) -> PerformanceOut:
    out = PerformanceOut.model_validate(record)
    out.event_name = f"{record.distance_m} m {record.stroke}"
    out.pace_per_100m = record.pace_per_100m
    out.speed_ms = record.speed_ms
    out.formatted_time = format_swim_time(record.time_seconds)
    if record.student:
        out.student_name = record.student.full_name
    if record.instructor:
        out.instructor_name = record.instructor.full_name
    return out


def _refresh_personal_best(db: Session, record: PerformanceRecord) -> bool:
    """Kişisel rekoru günceller. Yeni rekorsa True döner."""
    existing = db.scalar(
        select(PersonalBest).where(
            PersonalBest.student_id == record.student_id,
            PersonalBest.stroke == record.stroke,
            PersonalBest.distance_m == record.distance_m,
            PersonalBest.course_type == record.course_type,
        )
    )
    new_time = float(record.time_seconds)

    if existing is None:
        db.add(
            PersonalBest(
                student_id=record.student_id,
                stroke=record.stroke,
                distance_m=record.distance_m,
                course_type=record.course_type,
                time_seconds=new_time,
                achieved_date=record.recorded_date,
                performance_record_id=record.id,
            )
        )
        record.is_personal_best = True
        return True

    if new_time < float(existing.time_seconds):
        existing.time_seconds = new_time
        existing.achieved_date = record.recorded_date
        existing.performance_record_id = record.id
        record.is_personal_best = True
        # Önceki rekor kaydının işaretini kaldır
        for old in db.scalars(
            select(PerformanceRecord).where(
                PerformanceRecord.student_id == record.student_id,
                PerformanceRecord.stroke == record.stroke,
                PerformanceRecord.distance_m == record.distance_m,
                PerformanceRecord.course_type == record.course_type,
                PerformanceRecord.id != record.id,
                PerformanceRecord.is_personal_best.is_(True),
            )
        ).all():
            old.is_personal_best = False
        return True

    record.is_personal_best = False
    return False


@router.get("", response_model=Page[PerformanceOut], summary="Performans kayıtları")
def list_records(
    student_id: int | None = None,
    stroke: Stroke | None = None,
    distance_m: int | None = None,
    course_type: CourseType | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    is_competition: bool | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> Page[PerformanceOut]:
    stmt = select(PerformanceRecord).options(
        selectinload(PerformanceRecord.student),
        selectinload(PerformanceRecord.instructor),
    )
    allowed = scope.allowed_student_ids()
    if allowed is not None:
        stmt = stmt.where(PerformanceRecord.student_id.in_(allowed))
    if student_id:
        stmt = stmt.where(PerformanceRecord.student_id == student_id)
    if stroke:
        stmt = stmt.where(PerformanceRecord.stroke == stroke)
    if distance_m:
        stmt = stmt.where(PerformanceRecord.distance_m == distance_m)
    if course_type:
        stmt = stmt.where(PerformanceRecord.course_type == course_type)
    if date_from:
        stmt = stmt.where(PerformanceRecord.recorded_date >= date_from)
    if date_to:
        stmt = stmt.where(PerformanceRecord.recorded_date <= date_to)
    if is_competition is not None:
        stmt = stmt.where(PerformanceRecord.is_competition.is_(is_competition))

    stmt = stmt.order_by(
        PerformanceRecord.recorded_date.desc(), PerformanceRecord.id.desc()
    )
    rows, total = paginate(db, stmt, params)
    return Page[PerformanceOut](
        items=[_decorate(r) for r in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "", response_model=PerformanceOut, status_code=201, summary="Performans kaydet"
)
def create_record(
    payload: PerformanceCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.PERFORMANCE_WRITE)),
) -> PerformanceOut:
    student = get_or_404(db, Student, payload.student_id, "student.not_found")
    record = PerformanceRecord(**payload.model_dump())
    db.add(record)
    db.flush()

    is_pb = _refresh_personal_best(db, record)
    audit.record(
        db,
        action="create",
        entity_type="performance_record",
        entity_id=record.id,
        user=current,
        summary=(
            f"Performans: {student.full_name} {record.distance_m}m {record.stroke} "
            f"{format_swim_time(record.time_seconds)}" + (" (KR!)" if is_pb else "")
        ),
    )
    db.commit()
    db.refresh(record)
    return _decorate(record)


@router.get("/events/catalog", summary="Standart etkinlik kataloğu")
def events_catalog(lang: str = Depends(get_language)) -> dict:
    """Sistemin desteklediği stil/mesafe kombinasyonları."""
    from app.models.enums import label

    return {
        "strokes": [
            {"value": s.value, "label": label("stroke", s.value, lang)} for s in Stroke
        ],
        "distances": STANDARD_DISTANCES,
        "course_types": [
            {
                "value": "short",
                "label": (
                    "25 m (Kısa Kulvar)" if lang == "tr" else "25 m (Short Course)"
                ),
            },
            {
                "value": "long",
                "label": "50 m (Uzun Kulvar)" if lang == "tr" else "50 m (Long Course)",
            },
        ],
        "common_events": [
            f"{distance} m {label('stroke', stroke.value, lang)}"
            for stroke in (
                Stroke.FREESTYLE,
                Stroke.BACKSTROKE,
                Stroke.BREASTSTROKE,
                Stroke.BUTTERFLY,
            )
            for distance in (25, 50, 100)
        ],
    }


@router.get(
    "/student/{student_id}/summary",
    response_model=StudentPerformanceSummary,
    summary="Sporcu performans özeti",
)
def performance_summary(
    student_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> StudentPerformanceSummary:
    """Tamamen hesaplanmış istatistiksel özet (AI yorumu içermez)."""
    allowed = scope.allowed_student_ids()
    if allowed is not None and student_id not in allowed:
        raise PermissionDeniedError()
    get_or_404(db, Student, student_id, "student.not_found")
    return student_performance_summary(db, student_id, date_from, date_to)


@router.get(
    "/student/{student_id}/event",
    response_model=PerformanceEventAnalysis | None,
    summary="Tek etkinlik analizi",
)
def event_analysis(
    student_id: int,
    stroke: Stroke,
    distance_m: int,
    course_type: CourseType = CourseType.SHORT,
    date_from: date | None = None,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> PerformanceEventAnalysis | None:
    allowed = scope.allowed_student_ids()
    if allowed is not None and student_id not in allowed:
        raise PermissionDeniedError()

    stmt = select(PerformanceRecord).where(
        PerformanceRecord.student_id == student_id,
        PerformanceRecord.stroke == stroke,
        PerformanceRecord.distance_m == distance_m,
        PerformanceRecord.course_type == course_type,
    )
    if date_from:
        stmt = stmt.where(PerformanceRecord.recorded_date >= date_from)
    records = db.scalars(stmt.order_by(PerformanceRecord.recorded_date)).all()
    return analyze_event(list(records))


@router.get(
    "/student/{student_id}/personal-bests",
    response_model=list[PersonalBestOut],
    summary="Kişisel rekorlar",
)
def personal_bests(
    student_id: int,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> list[PersonalBestOut]:
    allowed = scope.allowed_student_ids()
    if allowed is not None and student_id not in allowed:
        raise PermissionDeniedError()

    rows = db.scalars(
        select(PersonalBest)
        .where(PersonalBest.student_id == student_id)
        .order_by(PersonalBest.stroke, PersonalBest.distance_m)
    ).all()
    result = []
    for pb in rows:
        item = PersonalBestOut.model_validate(pb)
        item.formatted_time = format_swim_time(pb.time_seconds)
        result.append(item)
    return result


@router.get(
    "/top-improvers", response_model=list[TopImproverRow], summary="En çok gelişenler"
)
def top_improvers(
    days: int = 90,
    min_records: int = 3,
    limit: int = 20,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> list[TopImproverRow]:
    return find_top_improvers(
        db, lookback_days=days, min_records=min_records, limit=limit
    )


@router.get(
    "/declining",
    response_model=list[DecliningAthleteRow],
    summary="Performansı düşenler",
)
def declining_athletes(
    days: int = 90,
    min_records: int = 4,
    limit: int = 20,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> list[DecliningAthleteRow]:
    return find_declining_athletes(
        db, lookback_days=days, min_records=min_records, limit=limit
    )


@router.get("/readiness", summary="Yarışma hazırlık göstergesi")
def readiness(
    days: int = 60,
    limit: int = 50,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> dict:
    rows = competition_readiness(db, lookback_days=days)
    return {
        "period_days": days,
        "count": len(rows),
        "rows": rows[:limit],
        "note_tr": (
            "Bu skor tamamen istatistikseldir (tutarlılık, forma yakınlık, gelişim "
            "eğilimi, antrenman hacmi). Yapay zekâ tahmini değildir."
        ),
        "note_en": (
            "This score is purely statistical (consistency, proximity to best form, "
            "improvement trend, training volume). It is not an AI prediction."
        ),
    }


@router.patch(
    "/{record_id}", response_model=PerformanceOut, summary="Performans güncelle"
)
def update_record(
    record_id: int,
    payload: PerformanceUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.PERFORMANCE_WRITE)),
) -> PerformanceOut:
    record = get_or_404(db, PerformanceRecord, record_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.flush()
    _refresh_personal_best(db, record)
    audit.record(
        db,
        action="update",
        entity_type="performance_record",
        entity_id=record_id,
        user=current,
        summary="Performans kaydı güncellendi",
    )
    db.commit()
    db.refresh(record)
    return _decorate(record)


@router.delete("/{record_id}", response_model=Message, summary="Performans kaydı sil")
def delete_record(
    record_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.PERFORMANCE_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    record = get_or_404(db, PerformanceRecord, record_id)
    db.delete(record)
    audit.record(
        db,
        action="delete",
        entity_type="performance_record",
        entity_id=record_id,
        user=current,
        summary="Performans kaydı silindi",
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Antrenman planları
# ---------------------------------------------------------------------------
@router.get(
    "/training-plans",
    response_model=list[TrainingPlanOut],
    summary="Antrenman planları",
)
def list_training_plans(
    student_id: int | None = None,
    db: Session = Depends(db_session),
    scope: AccessScope = Depends(get_scope),
    _: User = Depends(require_permissions(Perm.PERFORMANCE_READ)),
) -> list[TrainingPlanOut]:
    stmt = select(TrainingPlan)
    if student_id:
        # Nesne bazlı yetki: başka bir öğrencinin planı istenirse reddedilir.
        scope.assert_student_allowed(student_id)
        stmt = stmt.where(TrainingPlan.student_id == student_id)
    stmt = scope.scope_students(stmt, TrainingPlan.student_id)
    rows = db.scalars(stmt.order_by(TrainingPlan.start_date.desc())).all()
    result = []
    for plan in rows:
        item = TrainingPlanOut.model_validate(plan)
        student = db.get(Student, plan.student_id)
        item.student_name = student.full_name if student else None
        result.append(item)
    return result


@router.post(
    "/training-plans",
    response_model=TrainingPlanOut,
    status_code=201,
    summary="Antrenman planı oluştur",
)
def create_training_plan(
    payload: TrainingPlanCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.PERFORMANCE_WRITE)),
) -> TrainingPlanOut:
    student = get_or_404(db, Student, payload.student_id, "student.not_found")
    plan = TrainingPlan(
        **payload.model_dump(), is_approved=True, approved_by_user_id=current.id
    )
    db.add(plan)
    audit.record(
        db,
        action="create",
        entity_type="training_plan",
        user=current,
        summary=f"Antrenman planı: {student.full_name} - {payload.title}",
    )
    db.commit()
    db.refresh(plan)
    out = TrainingPlanOut.model_validate(plan)
    out.student_name = student.full_name
    return out


@router.post(
    "/training-plans/{plan_id}/approve",
    response_model=Message,
    summary="AI planını onayla",
)
def approve_plan(
    plan_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.PERFORMANCE_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    """AI tarafından üretilen antrenman planı ancak eğitmen onayıyla yürürlüğe girer."""
    plan = get_or_404(db, TrainingPlan, plan_id)
    plan.is_approved = True
    plan.approved_by_user_id = current.id
    audit.record(
        db,
        action="approve",
        entity_type="training_plan",
        entity_id=plan_id,
        user=current,
        summary=f"Antrenman planı onaylandı (AI üretimi: {plan.ai_generated})",
    )
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))
