"""Eğitim Merkezi ve onboarding uçları / Training Center and onboarding."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, get_language
from app.core.i18n import t
from app.models.enums import TrainingStatus
from app.models.people import Instructor, Student
from app.models.facility import Pool
from app.models.system import AppSetting, TrainingProgress
from app.models.user import User
from app.schemas.common import Message
from app.schemas.system import (
    OnboardingState,
    TrainingOverview,
    TutorialOut,
    TutorialProgressUpdate,
)
from app.services.tutorials import (
    ONBOARDING_STEPS,
    TRACKS,
    TUTORIAL_INDEX,
    TUTORIALS,
    tutorials_for_roles,
)

router = APIRouter(prefix="/training", tags=["Eğitim Merkezi"])


def _progress_map(db: Session, user_id: int) -> dict[str, TrainingProgress]:
    rows = db.scalars(
        select(TrainingProgress).where(TrainingProgress.user_id == user_id)
    ).all()
    return {row.tutorial_id: row for row in rows}


def _decorate(tutorial: TutorialOut, progress: TrainingProgress | None) -> TutorialOut:
    item = tutorial.model_copy(deep=True)
    item.total_steps = len(tutorial.steps)
    if progress:
        item.status = progress.status
        item.current_step = progress.current_step
        item.progress_percent = (
            round(progress.current_step / item.total_steps * 100, 1)
            if item.total_steps
            else 0.0
        )
    else:
        item.status = TrainingStatus.NOT_STARTED
        item.current_step = 0
        item.progress_percent = 0.0
    return item


@router.get(
    "/tutorials", response_model=list[TutorialOut], summary="Eğitimleri listele"
)
def list_tutorials(
    category: str | None = None,
    recommended_only: bool = False,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
) -> list[TutorialOut]:
    progress = _progress_map(db, user.id)
    recommended = set(tutorials_for_roles(user.role_codes))

    items = []
    for tutorial in TUTORIALS:
        if category and tutorial.category != category:
            continue
        if recommended_only and tutorial.id not in recommended:
            continue
        items.append(_decorate(tutorial, progress.get(tutorial.id)))
    return items


@router.get(
    "/tutorials/{tutorial_id}", response_model=TutorialOut, summary="Eğitim detayı"
)
def get_tutorial(
    tutorial_id: str,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
) -> TutorialOut:
    tutorial = TUTORIAL_INDEX.get(tutorial_id)
    if tutorial is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(details={"tutorial_id": tutorial_id})
    progress = _progress_map(db, user.id).get(tutorial_id)
    return _decorate(tutorial, progress)


@router.post(
    "/progress", response_model=TutorialOut, summary="Eğitim ilerlemesini kaydet"
)
def update_progress(
    payload: TutorialProgressUpdate,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
) -> TutorialOut:
    tutorial = TUTORIAL_INDEX.get(payload.tutorial_id)
    if tutorial is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(details={"tutorial_id": payload.tutorial_id})

    total = len(tutorial.steps)
    progress = db.scalar(
        select(TrainingProgress).where(
            TrainingProgress.user_id == user.id,
            TrainingProgress.tutorial_id == payload.tutorial_id,
        )
    )
    if progress is None:
        progress = TrainingProgress(
            user_id=user.id, tutorial_id=payload.tutorial_id, total_steps=total
        )
        db.add(progress)

    progress.current_step = min(payload.current_step, total)
    progress.total_steps = total
    if payload.status:
        progress.status = payload.status
    elif progress.current_step >= total:
        progress.status = TrainingStatus.COMPLETED
    elif progress.current_step > 0:
        progress.status = TrainingStatus.IN_PROGRESS

    if progress.status == TrainingStatus.COMPLETED and progress.completed_at is None:
        progress.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(progress)
    return _decorate(tutorial, progress)


@router.get(
    "/overview", response_model=TrainingOverview, summary="Eğitim ilerleme özeti"
)
def overview(
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> TrainingOverview:
    progress = _progress_map(db, user.id)
    recommended = set(tutorials_for_roles(user.role_codes))

    tracks = []
    for track in TRACKS:
        tutorial_ids = track["tutorials"]
        completed = sum(
            1
            for tid in tutorial_ids
            if (p := progress.get(tid)) and p.status == TrainingStatus.COMPLETED
        )
        tracks.append(
            {
                "id": track["id"],
                "title": track["title_tr"] if lang == "tr" else track["title_en"],
                "total": len(tutorial_ids),
                "completed": completed,
                "percent": (
                    round(completed / len(tutorial_ids) * 100, 1)
                    if tutorial_ids
                    else 0.0
                ),
                "recommended": any(tid in recommended for tid in tutorial_ids),
                "tutorials": [
                    {
                        "id": tid,
                        "title": (
                            TUTORIAL_INDEX[tid].title_tr
                            if lang == "tr"
                            else TUTORIAL_INDEX[tid].title_en
                        ),
                        "status": (
                            progress[tid].status
                            if tid in progress
                            else TrainingStatus.NOT_STARTED
                        ),
                        "minutes": TUTORIAL_INDEX[tid].estimated_minutes,
                    }
                    for tid in tutorial_ids
                    if tid in TUTORIAL_INDEX
                ],
            }
        )

    completed_total = sum(
        1 for p in progress.values() if p.status == TrainingStatus.COMPLETED
    )
    in_progress = sum(
        1 for p in progress.values() if p.status == TrainingStatus.IN_PROGRESS
    )

    return TrainingOverview(
        tracks=tracks,
        total_tutorials=len(TUTORIALS),
        completed=completed_total,
        in_progress=in_progress,
        overall_percent=(
            round(completed_total / len(TUTORIALS) * 100, 1) if TUTORIALS else 0.0
        ),
    )


@router.get("/onboarding", response_model=OnboardingState, summary="Onboarding durumu")
def onboarding_state(
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
) -> OnboardingState:
    """Kurulum sihirbazının hangi adımlarının tamamlandığını gerçek veriden çıkarır."""
    organization = db.scalar(select(AppSetting).where(AppSetting.key == "organization"))
    org_configured = bool(
        organization
        and isinstance(organization.value, dict)
        and organization.value.get("name")
        and organization.value.get("name") != "Akıllı Yüzme Okulu"
    )
    has_pool = bool(db.scalar(select(func.count(Pool.id))))
    has_instructor = bool(db.scalar(select(func.count(Instructor.id))))
    has_student = bool(db.scalar(select(func.count(Student.id))))

    from app.core.config import settings

    ai_configured = settings.local_ai_enabled or settings.nvidia_enabled
    backup_configured = settings.backup_schedule_enabled

    from app.models.system import BackupRecord

    if not backup_configured:
        backup_configured = bool(db.scalar(select(func.count(BackupRecord.id))))

    steps_done: list[str] = []
    if org_configured:
        steps_done.append("organization")
    if not user.must_change_password:
        steps_done.append("admin")
    if has_pool:
        steps_done.extend(["pool", "lanes"])
    if has_instructor:
        steps_done.append("instructor")
    if has_student:
        steps_done.append("student")
    if ai_configured:
        steps_done.append("ai")
    if backup_configured:
        steps_done.append("backup")

    return OnboardingState(
        completed=user.onboarding_completed,
        current_step=len(steps_done),
        steps_done=steps_done,
        organization_configured=org_configured,
        has_pool=has_pool,
        has_instructor=has_instructor,
        has_student=has_student,
        ai_configured=ai_configured,
        backup_configured=backup_configured,
    )


@router.get("/onboarding/steps", summary="Onboarding adımları")
def onboarding_steps(lang: str = Depends(get_language)) -> list[dict]:
    return [
        {
            "id": step["id"],
            "title": step["title_tr"] if lang == "tr" else step["title_en"],
            "description": (
                step["description_tr"] if lang == "tr" else step["description_en"]
            ),
            "route": step["route"],
        }
        for step in ONBOARDING_STEPS
    ]


@router.post(
    "/onboarding/complete", response_model=Message, summary="Onboarding'i tamamla"
)
def complete_onboarding(
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    user.onboarding_completed = True
    db.commit()
    return Message(code="common.updated", message=t("common.updated", lang))


@router.post(
    "/onboarding/skip", response_model=Message, summary="Onboarding'i şimdilik geç"
)
def skip_onboarding(
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    """'Şimdilik Geç' - kullanıcı daha sonra Eğitim Merkezi'nden devam edebilir."""
    user.onboarding_completed = True
    db.commit()
    return Message(
        code="common.updated",
        message=t("common.updated", lang),
        data={"hint": "Eğitim Merkezi'nden istediğiniz zaman devam edebilirsiniz."},
    )


@router.post(
    "/mode/{enabled}", response_model=Message, summary="Eğitim modunu aç/kapat"
)
def toggle_training_mode(
    enabled: bool,
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
    lang: str = Depends(get_language),
) -> Message:
    """Training Mode: arayüzde uyarı bandı gösterilir ve demo veriler vurgulanır.

    Gerçek üretim verisini yanlışlıkla değiştirmemek için eğitim sırasında açılır.
    """
    user.training_mode = enabled
    db.commit()
    return Message(
        code="common.updated",
        message=t("common.updated", lang),
        data={
            "training_mode": enabled,
            "notice_tr": (
                "Eğitim Modu açık. Demo kayıtlar üzerinde çalışıyorsunuz; "
                "arayüzde uyarı bandı gösterilir."
                if enabled
                else "Eğitim Modu kapalı."
            ),
            "notice_en": (
                "Training Mode is on. You are working with demo records; "
                "a banner is shown in the interface."
                if enabled
                else "Training Mode is off."
            ),
        },
    )
