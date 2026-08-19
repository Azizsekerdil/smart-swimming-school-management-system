"""CAIO Agent uçları / CAIO (Chief AI Officer) endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, pagination, require_permissions
from app.core.permissions import Perm
from app.models.system import CAIOFinding
from app.models.user import User
from app.schemas.ai import (
    CAIOFindingOut,
    CAIOFindingUpdate,
    CAIOReport,
    CAIORunRequest,
)
from app.schemas.common import Page, PaginationParams
from app.services import audit
from app.services.ai.caio import observe, run_caio
from app.services.crud import get_or_404, paginate

router = APIRouter(prefix="/ai/caio", tags=["CAIO"])


@router.post("/run", response_model=CAIOReport, summary="CAIO analizini çalıştır")
def run(
    payload: CAIORunRequest,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_CAIO)),
) -> CAIOReport:
    """Observe -> Analyze -> Propose döngüsünü çalıştırır.

    CAIO üretim koduna doğrudan değişiklik YAPMAZ; yalnızca bulgu ve öneri üretir.
    Yama üretimi için AI Developer Console'un onay akışı kullanılır.
    """
    report = run_caio(
        db,
        include_ai=payload.include_ai,
        provider=payload.provider,
        user_id=current.id,
        categories=payload.categories or None,
    )
    audit.record(
        db,
        action="caio_run",
        entity_type="caio",
        user=current,
        summary=(
            f"CAIO analizi: {len(report['findings'])} bulgu, "
            f"AI yorumu: {report['ai_available']}"
        ),
        commit=True,
    )
    return CAIOReport(
        run_at=report["run_at"],
        duration_ms=report["duration_ms"],
        observations=report["observations"],
        findings=[CAIOFindingOut.model_validate(f) for f in report["findings"]],
        findings_by_severity=report["findings_by_severity"],
        ai_available=report["ai_available"],
        ai_summary=report["ai_summary"],
        ai_proposals=report["ai_proposals"],
        provider=report["provider"],
    )


@router.get("/observe", summary="Yalnızca gözlem (AI çalıştırmaz)")
def observe_only(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AI_CAIO)),
) -> dict:
    """Ölçülmüş sistem verilerini döndürür. AI çağrısı yapılmaz."""
    return observe(db)


@router.get("/findings", response_model=Page[CAIOFindingOut], summary="Bulgular")
def list_findings(
    status: str | None = "open",
    severity: str | None = None,
    category: str | None = None,
    params: PaginationParams = Depends(pagination),
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AI_CAIO)),
) -> Page[CAIOFindingOut]:
    stmt = select(CAIOFinding)
    if status:
        stmt = stmt.where(CAIOFinding.status == status)
    if severity:
        stmt = stmt.where(CAIOFinding.severity == severity)
    if category:
        stmt = stmt.where(CAIOFinding.category == category)
    stmt = stmt.order_by(CAIOFinding.created_at.desc())
    rows, total = paginate(db, stmt, params)
    return Page[CAIOFindingOut](
        items=[CAIOFindingOut.model_validate(r) for r in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.patch(
    "/findings/{finding_id}",
    response_model=CAIOFindingOut,
    summary="Bulgu durumunu güncelle",
)
def update_finding(
    finding_id: int,
    payload: CAIOFindingUpdate,
    db: Session = Depends(db_session),
    current: User = Depends(require_permissions(Perm.AI_CAIO)),
) -> CAIOFindingOut:
    finding = get_or_404(db, CAIOFinding, finding_id)
    finding.status = payload.status
    if payload.status in ("resolved", "dismissed"):
        finding.resolved_at = datetime.now(timezone.utc)
    if payload.note:
        finding.recommendation = (
            f"{finding.recommendation or ''}\n\n[Not] {payload.note}".strip()
        )

    audit.record(
        db,
        action="update",
        entity_type="caio_finding",
        entity_id=finding_id,
        user=current,
        summary=f"CAIO bulgusu güncellendi: {finding.title[:80]} -> {payload.status}",
    )
    db.commit()
    db.refresh(finding)
    return CAIOFindingOut.model_validate(finding)


@router.get("/summary", summary="CAIO özet kartı")
def summary(
    db: Session = Depends(db_session),
    _: User = Depends(require_permissions(Perm.AI_CAIO)),
) -> dict:
    """Dashboard için hafif özet - tam analiz çalıştırmaz."""
    findings = db.scalars(select(CAIOFinding).where(CAIOFinding.status == "open")).all()
    by_severity: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for finding in findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        by_category[finding.category] = by_category.get(finding.category, 0) + 1

    latest = db.scalar(
        select(CAIOFinding).order_by(CAIOFinding.created_at.desc()).limit(1)
    )
    return {
        "open_findings": len(findings),
        "by_severity": by_severity,
        "by_category": by_category,
        "critical_count": by_severity.get("critical", 0),
        "high_count": by_severity.get("high", 0),
        "last_run_at": latest.created_at.isoformat() if latest else None,
        "top_findings": [
            {
                "id": f.id,
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "recommendation": f.recommendation,
            }
            for f in sorted(
                findings,
                key=lambda f: {
                    "critical": 0,
                    "high": 1,
                    "medium": 2,
                    "low": 3,
                    "info": 4,
                }.get(f.severity, 9),
            )[:5]
        ],
    }
