"""Havuz, kulvar ve kulvar planlama uçları / Pool, lane and lane-planning."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import client_ip, db_session, get_language, require_permissions
from app.core.exceptions import ConflictError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.enums import LessonStatus, PoolStatus
from app.models.facility import Holiday, Lane, Pool, PoolMaintenance, WaterQualityLog
from app.models.lesson import Lesson
from app.models.user import User
from app.schemas.common import Message
from app.schemas.facility import (
    HolidayBase,
    HolidayOut,
    LaneCreate,
    LaneOut,
    LaneUpdate,
    LanePlanResponse,
    MaintenanceCreate,
    MaintenanceOut,
    PoolCreate,
    PoolOut,
    PoolSummary,
    PoolUpdate,
    WaterQualityCreate,
    WaterQualityOut,
)
from app.services import audit
from app.services.crud import get_or_404
from app.services.scheduling import find_free_lanes, lane_plan, suggest_slot

router = APIRouter(prefix="/pools", tags=["Havuzlar"])

# Su kalitesi kabul aralıkları (havuz işletme standartlarına göre)
PH_RANGE = (6.8, 7.6)
CHLORINE_RANGE = (0.5, 3.0)
TURBIDITY_MAX = 0.5


@router.get("", response_model=list[PoolOut], summary="Havuzları listele")
def list_pools(
    status: PoolStatus | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> list[PoolOut]:
    stmt = select(Pool).options(selectinload(Pool.lanes)).order_by(Pool.name)
    if status:
        stmt = stmt.where(Pool.status == status)
    pools = db.scalars(stmt).all()
    result = []
    for pool in pools:
        item = PoolOut.model_validate(pool)
        item.operating_hours = pool.operating_hours
        result.append(item)
    return result


@router.post("", response_model=PoolOut, status_code=201, summary="Havuz oluştur")
def create_pool(
    payload: PoolCreate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_WRITE)),
) -> PoolOut:
    if db.scalar(select(Pool).where(Pool.name == payload.name)):
        raise ConflictError(details={"field": "name"})

    pool = Pool(**payload.model_dump(exclude={"auto_create_lanes"}))
    db.add(pool)
    db.flush()

    if payload.auto_create_lanes:
        for number in range(1, pool.lane_count + 1):
            db.add(
                Lane(
                    pool_id=pool.id,
                    lane_number=number,
                    max_swimmers=8,
                    is_active=True,
                )
            )

    audit.record(
        db,
        action="create",
        entity_type="pool",
        entity_id=pool.id,
        user=current,
        summary=f"Havuz oluşturuldu: {pool.name} ({pool.lane_count} kulvar)",
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(pool)
    out = PoolOut.model_validate(pool)
    out.operating_hours = pool.operating_hours
    return out


@router.get("/summary", response_model=list[PoolSummary], summary="Havuz doluluk özeti")
def pools_summary(
    day: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> list[PoolSummary]:
    target = day or date.today()
    day_start = datetime.combine(target, time.min)
    day_end = day_start + timedelta(days=1)

    summaries: list[PoolSummary] = []
    for pool in db.scalars(select(Pool).options(selectinload(Pool.lanes))).all():
        lessons = db.scalars(
            select(Lesson).where(
                Lesson.pool_id == pool.id,
                Lesson.start_at >= day_start,
                Lesson.start_at < day_end,
                Lesson.status != LessonStatus.CANCELLED,
            )
        ).all()
        active_lanes = [lane for lane in pool.lanes if lane.is_active]
        open_minutes = (
            datetime.combine(target, pool.closing_time)
            - datetime.combine(target, pool.opening_time)
        ).total_seconds() / 60
        capacity_minutes = open_minutes * max(1, len(active_lanes))
        used_minutes = sum(
            lesson.duration_minutes for lesson in lessons if lesson.lane_id
        )

        summaries.append(
            PoolSummary(
                id=pool.id,
                name=pool.name,
                status=pool.status,
                lane_count=len(pool.lanes),
                active_lane_count=len(active_lanes),
                today_lesson_count=len(lessons),
                occupancy_rate=(
                    round(used_minutes / capacity_minutes * 100, 1)
                    if capacity_minutes
                    else 0.0
                ),
            )
        )
    return summaries


@router.get("/{pool_id}", response_model=PoolOut, summary="Havuz detayı")
def get_pool(
    pool_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> PoolOut:
    pool = get_or_404(db, Pool, pool_id, "pool.not_found")
    out = PoolOut.model_validate(pool)
    out.operating_hours = pool.operating_hours
    return out


@router.patch("/{pool_id}", response_model=PoolOut, summary="Havuz güncelle")
def update_pool(
    pool_id: int,
    payload: PoolUpdate,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_WRITE)),
) -> PoolOut:
    pool = get_or_404(db, Pool, pool_id, "pool.not_found")
    changes: dict = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        old = getattr(pool, key, None)
        if old != value:
            changes[key] = {"from": str(old), "to": str(value)}
            setattr(pool, key, value)
    audit.record(
        db,
        action="update",
        entity_type="pool",
        entity_id=pool.id,
        user=current,
        summary=f"Havuz güncellendi: {pool.name}",
        changes=changes,
        ip_address=client_ip(request),
    )
    db.commit()
    db.refresh(pool)
    out = PoolOut.model_validate(pool)
    out.operating_hours = pool.operating_hours
    return out


@router.delete("/{pool_id}", response_model=Message, summary="Havuz sil")
def delete_pool(
    pool_id: int,
    request: Request,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    pool = get_or_404(db, Pool, pool_id, "pool.not_found")
    lesson_count = (
        db.scalar(select(func.count(Lesson.id)).where(Lesson.pool_id == pool_id)) or 0
    )
    if lesson_count:
        raise ConflictError("common.in_use", details={"lesson_count": lesson_count})
    name = pool.name
    db.delete(pool)
    audit.record(
        db,
        action="delete",
        entity_type="pool",
        entity_id=pool_id,
        user=current,
        summary=f"Havuz silindi: {name}",
        ip_address=client_ip(request),
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Kulvarlar
# ---------------------------------------------------------------------------
@router.get(
    "/{pool_id}/lanes", response_model=list[LaneOut], summary="Kulvarları listele"
)
def list_lanes(
    pool_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> list[LaneOut]:
    get_or_404(db, Pool, pool_id, "pool.not_found")
    lanes = db.scalars(
        select(Lane).where(Lane.pool_id == pool_id).order_by(Lane.lane_number)
    ).all()
    result = []
    for lane in lanes:
        item = LaneOut.model_validate(lane)
        item.display_name = lane.display_name
        result.append(item)
    return result


@router.post("/lanes", response_model=LaneOut, status_code=201, summary="Kulvar ekle")
def create_lane(
    payload: LaneCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_WRITE)),
) -> LaneOut:
    get_or_404(db, Pool, payload.pool_id, "pool.not_found")
    if db.scalar(
        select(Lane).where(
            Lane.pool_id == payload.pool_id, Lane.lane_number == payload.lane_number
        )
    ):
        raise ConflictError(details={"field": "lane_number"})
    lane = Lane(**payload.model_dump())
    db.add(lane)
    audit.record(
        db,
        action="create",
        entity_type="lane",
        user=current,
        summary=f"Kulvar eklendi: havuz #{payload.pool_id} kulvar {payload.lane_number}",
    )
    db.commit()
    db.refresh(lane)
    out = LaneOut.model_validate(lane)
    out.display_name = lane.display_name
    return out


@router.patch("/lanes/{lane_id}", response_model=LaneOut, summary="Kulvar güncelle")
def update_lane(
    lane_id: int,
    payload: LaneUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_WRITE)),
) -> LaneOut:
    lane = get_or_404(db, Lane, lane_id, "lane.not_found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lane, key, value)
    audit.record(
        db,
        action="update",
        entity_type="lane",
        entity_id=lane_id,
        user=current,
        summary=f"Kulvar güncellendi: {lane.display_name}",
    )
    db.commit()
    db.refresh(lane)
    out = LaneOut.model_validate(lane)
    out.display_name = lane.display_name
    return out


@router.delete("/lanes/{lane_id}", response_model=Message, summary="Kulvar sil")
def delete_lane(
    lane_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_DELETE)),
    lang: str = Depends(get_language),
) -> Message:
    lane = get_or_404(db, Lane, lane_id, "lane.not_found")
    db.delete(lane)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Kulvar planlama
# ---------------------------------------------------------------------------
@router.get(
    "/{pool_id}/lane-plan",
    response_model=LanePlanResponse,
    summary="Günlük kulvar planı",
)
def get_lane_plan(
    pool_id: int,
    day: date | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> LanePlanResponse:
    get_or_404(db, Pool, pool_id, "pool.not_found")
    plan = lane_plan(db, pool_id=pool_id, day=day or date.today())
    return LanePlanResponse(**plan)


@router.get("/{pool_id}/free-lanes", summary="Boş kulvarları bul")
def free_lanes(
    pool_id: int,
    start_at: datetime,
    end_at: datetime,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> dict:
    get_or_404(db, Pool, pool_id, "pool.not_found")
    lanes = find_free_lanes(db, pool_id=pool_id, start_at=start_at, end_at=end_at)
    return {
        "pool_id": pool_id,
        "start_at": start_at,
        "end_at": end_at,
        "free_lane_count": len(lanes),
        "lanes": [
            {"id": lane.id, "lane_number": lane.lane_number, "name": lane.display_name}
            for lane in lanes
        ],
    }


@router.get("/{pool_id}/suggest-slots", summary="Uygun zaman dilimi öner")
def suggest_slots(
    pool_id: int,
    day: date,
    duration_minutes: int = 60,
    instructor_id: int | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.LESSON_SCHEDULE)),
) -> dict:
    """Çakışmasız ders yerleştirme önerileri üretir."""
    get_or_404(db, Pool, pool_id, "pool.not_found")
    slots = suggest_slot(
        db,
        pool_id=pool_id,
        duration_minutes=duration_minutes,
        target_date=day,
        instructor_id=instructor_id,
    )
    return {"pool_id": pool_id, "date": day, "count": len(slots), "suggestions": slots}


# ---------------------------------------------------------------------------
# Bakım ve su kalitesi
# ---------------------------------------------------------------------------
@router.get(
    "/{pool_id}/maintenance",
    response_model=list[MaintenanceOut],
    summary="Bakım kayıtları",
)
def list_maintenance(
    pool_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> list[MaintenanceOut]:
    rows = db.scalars(
        select(PoolMaintenance)
        .where(PoolMaintenance.pool_id == pool_id)
        .order_by(PoolMaintenance.start_at.desc())
    ).all()
    return [MaintenanceOut.model_validate(m) for m in rows]


@router.post(
    "/maintenance",
    response_model=MaintenanceOut,
    status_code=201,
    summary="Bakım planla",
)
def create_maintenance(
    payload: MaintenanceCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_MAINTENANCE)),
) -> MaintenanceOut:
    pool = get_or_404(db, Pool, payload.pool_id, "pool.not_found")
    maintenance = PoolMaintenance(**payload.model_dump())
    db.add(maintenance)

    affected = db.scalars(
        select(Lesson).where(
            Lesson.pool_id == payload.pool_id,
            Lesson.start_at < payload.end_at,
            payload.start_at < Lesson.end_at,
            Lesson.status == LessonStatus.SCHEDULED,
        )
    ).all()

    audit.record(
        db,
        action="create",
        entity_type="pool_maintenance",
        entity_id=payload.pool_id,
        user=current,
        summary=(
            f"Bakım planlandı: {pool.name} "
            f"({payload.start_at:%d.%m %H:%M}-{payload.end_at:%d.%m %H:%M}), "
            f"etkilenen ders: {len(affected)}"
        ),
    )
    db.commit()
    db.refresh(maintenance)
    return MaintenanceOut.model_validate(maintenance)


@router.patch(
    "/maintenance/{maintenance_id}",
    response_model=MaintenanceOut,
    summary="Bakım güncelle",
)
def update_maintenance(
    maintenance_id: int,
    is_completed: bool | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_MAINTENANCE)),
) -> MaintenanceOut:
    maintenance = get_or_404(db, PoolMaintenance, maintenance_id)
    if is_completed is not None:
        maintenance.is_completed = is_completed
    db.commit()
    db.refresh(maintenance)
    return MaintenanceOut.model_validate(maintenance)


@router.get(
    "/{pool_id}/water-quality",
    response_model=list[WaterQualityOut],
    summary="Su kalitesi",
)
def list_water_quality(
    pool_id: int,
    limit: int = 50,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> list[WaterQualityOut]:
    rows = db.scalars(
        select(WaterQualityLog)
        .where(WaterQualityLog.pool_id == pool_id)
        .order_by(WaterQualityLog.measured_at.desc())
        .limit(limit)
    ).all()
    return [WaterQualityOut.model_validate(r) for r in rows]


@router.post(
    "/water-quality",
    response_model=WaterQualityOut,
    status_code=201,
    summary="Su ölçümü kaydet",
)
def create_water_quality(
    payload: WaterQualityCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.POOL_MAINTENANCE)),
) -> WaterQualityOut:
    get_or_404(db, Pool, payload.pool_id, "pool.not_found")
    within = True
    if payload.ph is not None and not (PH_RANGE[0] <= payload.ph <= PH_RANGE[1]):
        within = False
    if payload.chlorine_ppm is not None and not (
        CHLORINE_RANGE[0] <= payload.chlorine_ppm <= CHLORINE_RANGE[1]
    ):
        within = False
    if payload.turbidity_ntu is not None and payload.turbidity_ntu > TURBIDITY_MAX:
        within = False

    log = WaterQualityLog(**payload.model_dump(), is_within_limits=within)
    db.add(log)
    if not within:
        from app.services.notifications import broadcast

        broadcast(
            db,
            notification_type="pool_maintenance",
            severity="warning",
            title_tr="Su kalitesi sınır dışı",
            title_en="Water quality out of range",
            body_tr=f"pH: {payload.ph}, Klor: {payload.chlorine_ppm} ppm",
            body_en=f"pH: {payload.ph}, Chlorine: {payload.chlorine_ppm} ppm",
            role_codes=["pool_technician", "operations_manager", "system_admin"],
            entity_type="pool",
            entity_id=payload.pool_id,
        )
    audit.record(
        db,
        action="create",
        entity_type="water_quality",
        entity_id=payload.pool_id,
        user=current,
        summary=f"Su ölçümü kaydedildi (limit içi: {within})",
    )
    db.commit()
    db.refresh(log)
    return WaterQualityOut.model_validate(log)


# ---------------------------------------------------------------------------
# Tatiller
# ---------------------------------------------------------------------------
@router.get(
    "/calendar/holidays", response_model=list[HolidayOut], summary="Tatilleri listele"
)
def list_holidays(
    year: int | None = None,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.POOL_READ)),
) -> list[HolidayOut]:
    stmt = select(Holiday).order_by(Holiday.date)
    if year:
        stmt = stmt.where(
            Holiday.date >= date(year, 1, 1), Holiday.date <= date(year, 12, 31)
        )
    return [HolidayOut.model_validate(h) for h in db.scalars(stmt).all()]


@router.post(
    "/calendar/holidays",
    response_model=HolidayOut,
    status_code=201,
    summary="Tatil ekle",
)
def create_holiday(
    payload: HolidayBase,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.LESSON_SCHEDULE)),
) -> HolidayOut:
    if db.scalar(select(Holiday).where(Holiday.date == payload.date)):
        raise ConflictError()
    holiday = Holiday(**payload.model_dump())
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    return HolidayOut.model_validate(holiday)


@router.delete(
    "/calendar/holidays/{holiday_id}", response_model=Message, summary="Tatil sil"
)
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.LESSON_SCHEDULE)),
    lang: str = Depends(get_language),
) -> Message:
    holiday = get_or_404(db, Holiday, holiday_id)
    db.delete(holiday)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))
