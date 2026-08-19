"""Yarışma uçları / Competition endpoints."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import (
    AccessScope,
    db_session,
    get_language,
    pagination,
    require_org_wide_scope,
    require_permissions,
)
from app.core.exceptions import ConflictError, ValidationError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.competition import (
    ClubRecord,
    Competition,
    CompetitionEntry,
    CompetitionEvent,
)
from app.models.people import Student
from app.models.performance import PerformanceRecord, PersonalBest
from app.models.user import User
from app.schemas.common import Message, Page, PaginationParams
from app.schemas.performance import (
    ClubRecordOut,
    CompetitionCreate,
    CompetitionEntryCreate,
    CompetitionEntryOut,
    CompetitionEventCreate,
    CompetitionEventOut,
    CompetitionOut,
    CompetitionResultUpdate,
    CompetitionUpdate,
    HeatSheet,
    HeatSheetLane,
)
from app.services import audit
from app.services.crud import get_or_404, paginate
from app.services.formatting import format_swim_time

router = APIRouter(prefix="/competitions", tags=["Yarışmalar"])


def _entry_out(entry: CompetitionEntry) -> CompetitionEntryOut:
    out = CompetitionEntryOut.model_validate(entry)
    out.formatted_result = format_swim_time(entry.result_time_seconds)
    out.improvement_seconds = entry.improvement_seconds
    if entry.student:
        out.student_name = entry.student.full_name
    return out


def _event_out(
    event: CompetitionEvent, include_entries: bool = True
) -> CompetitionEventOut:
    out = CompetitionEventOut.model_validate(event)
    out.name = event.name
    out.entry_count = len(event.entries)
    out.entries = [_entry_out(e) for e in event.entries] if include_entries else []
    return out


def _competition_out(comp: Competition, include_events: bool = True) -> CompetitionOut:
    out = CompetitionOut.model_validate(comp)
    out.event_count = len(comp.events)
    entries = [entry for event in comp.events for entry in event.entries]
    out.entry_count = len(entries)
    out.medal_count = sum(1 for e in entries if e.medal)
    out.events = [_event_out(e) for e in comp.events] if include_events else []
    return out


@router.get("", response_model=Page[CompetitionOut], summary="Yarışmaları listele")
def list_competitions(
    upcoming_only: bool = False,
    year: int | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.COMPETITION_READ)),
) -> Page[CompetitionOut]:
    stmt = select(Competition).options(
        selectinload(Competition.events).selectinload(CompetitionEvent.entries)
    )
    if upcoming_only:
        stmt = stmt.where(Competition.start_date >= date.today())
    if year:
        stmt = stmt.where(
            Competition.start_date >= date(year, 1, 1),
            Competition.start_date <= date(year, 12, 31),
        )
    stmt = stmt.order_by(Competition.start_date.desc())
    rows, total = paginate(db, stmt, params)
    return Page[CompetitionOut](
        items=[_competition_out(c, include_events=False) for c in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "", response_model=CompetitionOut, status_code=201, summary="Yarışma oluştur"
)
def create_competition(
    payload: CompetitionCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
) -> CompetitionOut:
    if payload.end_date < payload.start_date:
        raise ValidationError(details={"reason": "end_before_start"})
    competition = Competition(**payload.model_dump())
    db.add(competition)
    audit.record(
        db,
        action="create",
        entity_type="competition",
        user=current,
        summary=f"Yarışma oluşturuldu: {competition.name}",
    )
    db.commit()
    db.refresh(competition)
    return _competition_out(competition)


@router.get("/records", response_model=list[ClubRecordOut], summary="Kulüp rekorları")
def club_records(
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.COMPETITION_READ)),
) -> list[ClubRecordOut]:
    rows = db.scalars(
        select(ClubRecord).order_by(ClubRecord.stroke, ClubRecord.distance_m)
    ).all()
    result = []
    for record in rows:
        item = ClubRecordOut.model_validate(record)
        item.formatted_time = format_swim_time(record.time_seconds)
        result.append(item)
    return result


@router.get("/medals/summary", summary="Madalya tablosu")
def medal_summary(
    year: int | None = None,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.COMPETITION_READ)),
) -> dict:
    stmt = (
        select(CompetitionEntry)
        .options(selectinload(CompetitionEntry.student))
        .where(CompetitionEntry.medal.is_not(None))
    )
    if year:
        stmt = (
            stmt.join(CompetitionEvent)
            .join(Competition)
            .where(
                Competition.start_date >= date(year, 1, 1),
                Competition.start_date <= date(year, 12, 31),
            )
        )
    entries = db.scalars(stmt).all()

    per_student: dict[int, dict] = defaultdict(
        lambda: {"gold": 0, "silver": 0, "bronze": 0, "total": 0, "name": ""}
    )
    totals = {"gold": 0, "silver": 0, "bronze": 0}
    for entry in entries:
        bucket = per_student[entry.student_id]
        bucket["name"] = (
            entry.student.full_name if entry.student else f"#{entry.student_id}"
        )
        medal = entry.medal
        if medal is not None and medal in totals:
            bucket[medal] += 1
            totals[medal] += 1
        bucket["total"] += 1

    rows = sorted(
        [{"student_id": sid, **data} for sid, data in per_student.items()],
        key=lambda r: (-r["gold"], -r["silver"], -r["bronze"]),
    )
    return {"totals": totals, "total_medals": sum(totals.values()), "athletes": rows}


@router.get(
    "/{competition_id}", response_model=CompetitionOut, summary="Yarışma detayı"
)
def get_competition(
    competition_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.COMPETITION_READ)),
) -> CompetitionOut:
    return _competition_out(get_or_404(db, Competition, competition_id))


@router.patch(
    "/{competition_id}", response_model=CompetitionOut, summary="Yarışma güncelle"
)
def update_competition(
    competition_id: int,
    payload: CompetitionUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
) -> CompetitionOut:
    competition = get_or_404(db, Competition, competition_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(competition, key, value)
    audit.record(
        db,
        action="update",
        entity_type="competition",
        entity_id=competition_id,
        user=current,
        summary=f"Yarışma güncellendi: {competition.name}",
    )
    db.commit()
    db.refresh(competition)
    return _competition_out(competition)


@router.delete("/{competition_id}", response_model=Message, summary="Yarışma sil")
def delete_competition(
    competition_id: int,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    competition = get_or_404(db, Competition, competition_id)
    name = competition.name
    db.delete(competition)
    audit.record(
        db,
        action="delete",
        entity_type="competition",
        entity_id=competition_id,
        user=current,
        summary=f"Yarışma silindi: {name}",
    )
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Etkinlikler
# ---------------------------------------------------------------------------
@router.post(
    "/events",
    response_model=CompetitionEventOut,
    status_code=201,
    summary="Etkinlik ekle",
)
def create_event(
    payload: CompetitionEventCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
) -> CompetitionEventOut:
    get_or_404(db, Competition, payload.competition_id)
    event = CompetitionEvent(**payload.model_dump())
    db.add(event)
    audit.record(
        db,
        action="create",
        entity_type="competition_event",
        user=current,
        summary=f"Etkinlik eklendi: {payload.distance_m} m {payload.stroke}",
    )
    db.commit()
    db.refresh(event)
    return _event_out(event)


@router.delete("/events/{event_id}", response_model=Message, summary="Etkinlik sil")
def delete_event(
    event_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    event = get_or_404(db, CompetitionEvent, event_id)
    db.delete(event)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


# ---------------------------------------------------------------------------
# Kayıtlar ve sonuçlar
# ---------------------------------------------------------------------------
@router.post(
    "/entries",
    response_model=CompetitionEntryOut,
    status_code=201,
    summary="Sporcu kaydet",
)
def create_entry(
    payload: CompetitionEntryCreate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
) -> CompetitionEntryOut:
    event = get_or_404(db, CompetitionEvent, payload.event_id)
    student = get_or_404(db, Student, payload.student_id, "student.not_found")

    if db.scalar(
        select(CompetitionEntry).where(
            CompetitionEntry.event_id == payload.event_id,
            CompetitionEntry.student_id == payload.student_id,
        )
    ):
        raise ConflictError()

    seed = payload.seed_time_seconds
    if seed is None:
        pb = db.scalar(
            select(PersonalBest).where(
                PersonalBest.student_id == payload.student_id,
                PersonalBest.stroke == event.stroke,
                PersonalBest.distance_m == event.distance_m,
            )
        )
        seed = float(pb.time_seconds) if pb else None

    entry = CompetitionEntry(
        event_id=payload.event_id,
        student_id=payload.student_id,
        seed_time_seconds=seed,
        heat_number=payload.heat_number,
        lane_number=payload.lane_number,
    )
    db.add(entry)
    audit.record(
        db,
        action="create",
        entity_type="competition_entry",
        user=current,
        summary=f"Yarışma kaydı: {student.full_name} - {event.name}",
    )
    db.commit()
    db.refresh(entry)
    return _entry_out(entry)


@router.patch(
    "/entries/{entry_id}/result",
    response_model=CompetitionEntryOut,
    summary="Sonuç gir",
)
def record_result(
    entry_id: int,
    payload: CompetitionResultUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
) -> CompetitionEntryOut:
    """Yarışma sonucunu kaydeder; kişisel ve kulüp rekorlarını otomatik günceller."""
    entry = get_or_404(db, CompetitionEntry, entry_id)
    event = entry.event
    competition = event.competition

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)

    if payload.result_time_seconds and not payload.is_disqualified:
        result_time = float(payload.result_time_seconds)

        # Performans kaydı olarak da işle
        record = PerformanceRecord(
            student_id=entry.student_id,
            stroke=event.stroke,
            distance_m=event.distance_m,
            course_type=competition.course_type,
            time_seconds=result_time,
            recorded_date=event.scheduled_date or competition.start_date,
            is_competition=True,
            notes=f"{competition.name} - {event.name}",
        )
        db.add(record)
        db.flush()

        # Kişisel rekor
        pb = db.scalar(
            select(PersonalBest).where(
                PersonalBest.student_id == entry.student_id,
                PersonalBest.stroke == event.stroke,
                PersonalBest.distance_m == event.distance_m,
                PersonalBest.course_type == competition.course_type,
            )
        )
        if pb is None or result_time < float(pb.time_seconds):
            entry.is_personal_best = True
            record.is_personal_best = True
            if pb is None:
                db.add(
                    PersonalBest(
                        student_id=entry.student_id,
                        stroke=event.stroke,
                        distance_m=event.distance_m,
                        course_type=competition.course_type,
                        time_seconds=result_time,
                        achieved_date=record.recorded_date,
                        performance_record_id=record.id,
                    )
                )
            else:
                pb.time_seconds = result_time
                pb.achieved_date = record.recorded_date
                pb.performance_record_id = record.id

        # Kulüp rekoru
        club = db.scalar(
            select(ClubRecord).where(
                ClubRecord.stroke == event.stroke,
                ClubRecord.distance_m == event.distance_m,
                ClubRecord.course_type == competition.course_type,
                ClubRecord.gender_category == event.gender_category,
                ClubRecord.age_category == (event.age_category or "open"),
            )
        )
        student = db.get(Student, entry.student_id)
        if club is None or result_time < float(club.time_seconds):
            entry.is_club_record = True
            if club is None:
                db.add(
                    ClubRecord(
                        stroke=event.stroke,
                        distance_m=event.distance_m,
                        course_type=competition.course_type,
                        gender_category=event.gender_category,
                        age_category=event.age_category or "open",
                        student_id=entry.student_id,
                        holder_name=student.full_name if student else "",
                        time_seconds=result_time,
                        achieved_date=record.recorded_date,
                        competition_name=competition.name,
                    )
                )
            else:
                club.student_id = entry.student_id
                club.holder_name = student.full_name if student else club.holder_name
                club.time_seconds = result_time
                club.achieved_date = record.recorded_date
                club.competition_name = competition.name

    audit.record(
        db,
        action="record_result",
        entity_type="competition_entry",
        entity_id=entry_id,
        user=current,
        summary=(
            f"Sonuç: {format_swim_time(payload.result_time_seconds)} "
            f"(sıra: {payload.rank}, madalya: {payload.medal or '-'})"
        ),
    )
    db.commit()
    db.refresh(entry)
    return _entry_out(entry)


@router.delete(
    "/entries/{entry_id}", response_model=Message, summary="Yarışma kaydını sil"
)
def delete_entry(
    entry_id: int,
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
    lang: str = Depends(get_language),
) -> Message:
    entry = get_or_404(db, CompetitionEntry, entry_id)
    db.delete(entry)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))


@router.post(
    "/events/{event_id}/seed-heats",
    response_model=list[HeatSheet],
    summary="Seri oluştur",
)
def seed_heats(
    event_id: int,
    lanes_per_heat: int = 6,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.COMPETITION_WRITE)),
) -> list[HeatSheet]:
    """Seed zamanlarına göre serileri ve kulvarları otomatik dağıtır.

    Standart yüzme kuralı: en hızlı sporcular son seride, her seride en hızlı
    sporcu orta kulvarda yer alır.
    """
    event = get_or_404(db, CompetitionEvent, event_id)
    entries = list(event.entries)
    if not entries:
        return []

    # Seed zamanı olmayanlar en yavaş kabul edilir
    entries.sort(key=lambda e: float(e.seed_time_seconds or 1e9))

    # Kulvar öncelik sırası: orta kulvardan dışa doğru (6 kulvar için 3,4,2,5,1,6)
    center = (lanes_per_heat + 1) // 2
    lane_order: list[int] = []
    offset = 0
    while len(lane_order) < lanes_per_heat:
        for candidate in (center - offset, center + offset):
            if 1 <= candidate <= lanes_per_heat and candidate not in lane_order:
                lane_order.append(candidate)
        offset += 1

    heat_count = -(-len(entries) // lanes_per_heat)
    # En hızlılar son seriye gelsin diye grupları ters çevir
    groups = [
        entries[i : i + lanes_per_heat] for i in range(0, len(entries), lanes_per_heat)
    ]
    groups.reverse()

    sheets: list[HeatSheet] = []
    for heat_index, group in enumerate(groups, start=1):
        lanes: list[HeatSheetLane] = []
        for position, entry in enumerate(group):
            lane_number = (
                lane_order[position] if position < len(lane_order) else position + 1
            )
            entry.heat_number = heat_index
            entry.lane_number = lane_number
            lanes.append(
                HeatSheetLane(
                    lane_number=lane_number,
                    student_id=entry.student_id,
                    student_name=entry.student.full_name if entry.student else None,
                    seed_time=(
                        float(entry.seed_time_seconds)
                        if entry.seed_time_seconds
                        else None
                    ),
                    formatted_seed=format_swim_time(entry.seed_time_seconds),
                )
            )
        lanes.sort(key=lambda lane: lane.lane_number)
        sheets.append(
            HeatSheet(
                event_id=event_id,
                event_name=event.name,
                heat_number=heat_index,
                lanes=lanes,
            )
        )

    audit.record(
        db,
        action="seed_heats",
        entity_type="competition_event",
        entity_id=event_id,
        user=current,
        summary=f"{heat_count} seri oluşturuldu ({len(entries)} sporcu)",
    )
    db.commit()
    return sheets


@router.get("/{competition_id}/results", summary="Yarışma sonuç raporu")
def competition_results(
    competition_id: int,
    db: Session = Depends(db_session),
    _scope: AccessScope = Depends(require_org_wide_scope),
    _: User = Depends(require_permissions(Perm.COMPETITION_READ)),
) -> dict:
    competition = get_or_404(db, Competition, competition_id)
    events = []
    total_pb = total_records = 0

    for event in competition.events:
        finished = [
            entry
            for entry in event.entries
            if entry.result_time_seconds and not entry.is_disqualified
        ]
        finished.sort(key=lambda e: float(e.result_time_seconds))
        total_pb += sum(1 for e in finished if e.is_personal_best)
        total_records += sum(1 for e in finished if e.is_club_record)

        events.append(
            {
                "event_id": event.id,
                "event_name": event.name,
                "gender_category": event.gender_category,
                "age_category": event.age_category,
                "results": [
                    {
                        "rank": entry.rank or index + 1,
                        "student_id": entry.student_id,
                        "student_name": (
                            entry.student.full_name if entry.student else None
                        ),
                        "time": format_swim_time(entry.result_time_seconds),
                        "time_seconds": float(entry.result_time_seconds),
                        "seed_time": format_swim_time(entry.seed_time_seconds),
                        "improvement": entry.improvement_seconds,
                        "medal": entry.medal,
                        "is_personal_best": entry.is_personal_best,
                        "is_club_record": entry.is_club_record,
                    }
                    for index, entry in enumerate(finished)
                ],
                "disqualified": [
                    {
                        "student_name": (
                            entry.student.full_name if entry.student else None
                        ),
                        "reason": entry.disqualification_reason,
                    }
                    for entry in event.entries
                    if entry.is_disqualified
                ],
            }
        )

    return {
        "competition": {
            "id": competition.id,
            "name": competition.name,
            "location": competition.location,
            "start_date": competition.start_date.isoformat(),
            "end_date": competition.end_date.isoformat(),
            "level": competition.level,
            "course_type": competition.course_type,
        },
        "summary": {
            "event_count": len(competition.events),
            "entry_count": sum(len(e.entries) for e in competition.events),
            "personal_bests": total_pb,
            "club_records": total_records,
        },
        "events": events,
    }
