"""Rapor üretici uçları / Report builder endpoints."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, get_language, require_permissions
from app.core.exceptions import PermissionDeniedError
from app.core.i18n import t
from app.core.permissions import Perm
from app.models.system import ReportTemplate
from app.models.user import User
from app.schemas.common import Message
from app.schemas.statistics import (
    ReportDefinition,
    ReportPreview,
    ReportRequest,
    ReportTemplateIn,
    ReportTemplateOut,
)
from app.services import audit
from app.services.crud import get_or_404
from app.services.reporting import (
    REPORT_DEFINITIONS,
    REPORT_INDEX,
    build_report,
    export_report,
)

router = APIRouter(prefix="/reports", tags=["Raporlar"])


def _check_report_permission(user: User, report_key: str) -> None:
    definition = REPORT_INDEX.get(report_key)
    if definition is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError(details={"report_key": report_key})
    if not user.has_permission(definition.required_permission):
        raise PermissionDeniedError(
            details={"required": definition.required_permission}
        )


@router.get(
    "/definitions", response_model=list[ReportDefinition], summary="Rapor kataloğu"
)
def list_definitions(user: User = Depends(get_current_user)) -> list[ReportDefinition]:
    """Kullanıcının yetkili olduğu raporları listeler."""
    return [d for d in REPORT_DEFINITIONS if user.has_permission(d.required_permission)]


@router.post("/preview", response_model=ReportPreview, summary="Rapor önizleme")
def preview_report(
    payload: ReportRequest,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.REPORT_READ)),
) -> ReportPreview:
    _check_report_permission(user, payload.report_key)
    return build_report(db, payload)


@router.post("/export", summary="Rapor dışa aktar (PDF/Excel/CSV)")
def export(
    payload: ReportRequest,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.REPORT_EXPORT)),
) -> Response:
    _check_report_permission(user, payload.report_key)
    content, filename, media_type = export_report(db, payload)

    audit.record(
        db,
        action="export",
        entity_type="report",
        entity_id=payload.report_key,
        user=user,
        summary=f"Rapor dışa aktarıldı: {payload.report_key} ({payload.format})",
        commit=True,
    )

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


# ---------------------------------------------------------------------------
# Kayıtlı rapor şablonları
# ---------------------------------------------------------------------------
@router.get(
    "/templates", response_model=list[ReportTemplateOut], summary="Kayıtlı şablonlar"
)
def list_templates(
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.REPORT_READ)),
) -> list[ReportTemplateOut]:
    rows = db.scalars(
        select(ReportTemplate)
        .where(
            (ReportTemplate.owner_user_id == user.id)
            | (ReportTemplate.is_shared.is_(True))
        )
        .order_by(ReportTemplate.name)
    ).all()
    return [ReportTemplateOut.model_validate(r, from_attributes=True) for r in rows]


@router.post(
    "/templates",
    response_model=ReportTemplateOut,
    status_code=201,
    summary="Şablon kaydet",
)
def create_template(
    payload: ReportTemplateIn,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.REPORT_READ)),
) -> ReportTemplateOut:
    _check_report_permission(user, payload.report_key)
    template = ReportTemplate(**payload.model_dump(), owner_user_id=user.id)
    db.add(template)
    db.commit()
    db.refresh(template)
    return ReportTemplateOut.model_validate(template, from_attributes=True)


@router.delete("/templates/{template_id}", response_model=Message, summary="Şablon sil")
def delete_template(
    template_id: int,
    db: Session = Depends(db_session),
    user: User = Depends(require_permissions(Perm.REPORT_READ)),
    lang: str = Depends(get_language),
) -> Message:
    template = get_or_404(db, ReportTemplate, template_id)
    if template.owner_user_id != user.id and not user.is_superuser:
        raise PermissionDeniedError()
    db.delete(template)
    db.commit()
    return Message(code="common.deleted", message=t("common.deleted", lang))
