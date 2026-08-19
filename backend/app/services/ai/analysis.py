"""İstatistik + AI birleşik analiz katmanı / Statistics + AI analysis layer.

Akış:
    Veritabanı -> Statistics Engine -> Yapılandırılmış Metrikler -> AI -> Doğal dil raporu

AI ham veriyi yorumlamaz; ÖNCE gerçek metrikler hesaplanır, AI'ya yalnızca bu
hesaplanmış özet gönderilir. Yanıtta gerçek veri ile AI yorumu ayrı alanlarda
döner.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.enums import AITaskKind
from app.models.people import Student
from app.schemas.ai import AIAnalysisRequest, AIAnalysisResponse
from app.services.ai.base import AIProviderError, ChatMessage
from app.services.ai.prompts import analyst_system_prompt, coach_system_prompt
from app.services.ai.registry import finish_task, start_task
from app.services.formatting import format_swim_time
from app.services.hsp import gateway as hsp_gateway
from app.services.hsp.scopes import collect_names, fields_for
from app.services.statistics_engine import (
    attendance_statistics,
    cohort_retention,
    competition_readiness,
    find_declining_athletes,
    find_top_improvers,
    instructor_statistics,
    pool_statistics,
    resolve_period,
    student_performance_summary,
    student_statistics,
)

logger = get_logger("ai")

MIN_DATA_POINTS = 3


# ===========================================================================
# Metrik toplayıcılar
# ===========================================================================
def _student_performance_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    if not request.student_id:
        return (
            {"error": "student_id_required"},
            0,
            "Öğrenci seçilmedi.",
            "No student selected.",
        )

    summary = student_performance_summary(
        db, request.student_id, request.date_from, request.date_to
    )
    metrics = {
        "student": summary.student_name,
        "total_records": summary.total_records,
        "training_records": summary.training_count,
        "competition_records": summary.competition_count,
        "personal_bests": summary.personal_best_count,
        "date_range": {
            "first": (
                summary.first_record_date.isoformat()
                if summary.first_record_date
                else None
            ),
            "last": (
                summary.last_record_date.isoformat()
                if summary.last_record_date
                else None
            ),
        },
        "strongest_stroke": summary.strongest_stroke,
        "weakest_stroke": summary.weakest_stroke,
        "overall_improvement_percent": summary.overall_improvement_percent,
        "events": [
            {
                "event": f"{e.distance_m} m {e.stroke}",
                "records": e.record_count,
                "best_time": format_swim_time(e.best_time),
                "mean_time": format_swim_time(e.mean_time),
                "median_time": format_swim_time(e.median_time),
                "std_dev_seconds": e.std_dev,
                "first_time": format_swim_time(e.first_time),
                "last_time": format_swim_time(e.last_time),
                "improvement_seconds": e.improvement_seconds,
                "improvement_percent": e.improvement_percent,
                "change_30d_seconds": e.change_30d,
                "change_90d_seconds": e.change_90d,
                "trend": e.trend,
            }
            for e in summary.events
        ],
    }

    lines_tr = [f"{summary.student_name} · {summary.total_records} performans kaydı"]
    lines_en = [f"{summary.student_name} · {summary.total_records} performance records"]
    for e in summary.events:
        lines_tr.append(
            f"- {e.distance_m} m {e.stroke}: en iyi {format_swim_time(e.best_time)}, "
            f"ilk→son {format_swim_time(e.first_time)}→{format_swim_time(e.last_time)} "
            f"({e.improvement_seconds:+.2f} sn, %{e.improvement_percent:+.2f}), eğilim: {e.trend}"
        )
        lines_en.append(
            f"- {e.distance_m} m {e.stroke}: best {format_swim_time(e.best_time)}, "
            f"first→last {format_swim_time(e.first_time)}→{format_swim_time(e.last_time)} "
            f"({e.improvement_seconds:+.2f}s, {e.improvement_percent:+.2f}%), trend: {e.trend}"
        )
    return metrics, summary.total_records, "\n".join(lines_tr), "\n".join(lines_en)


def _declining_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    rows = find_declining_athletes(db, lookback_days=90, min_records=4, limit=20)
    metrics = {
        "declining_count": len(rows),
        "athletes": [
            {
                "student": r.student_name,
                "event": f"{r.distance_m} m {r.stroke}",
                "baseline_mean": format_swim_time(r.baseline_mean),
                "recent_mean": format_swim_time(r.recent_mean),
                "decline_seconds": r.decline_seconds,
                "decline_percent": r.decline_percent,
                "records": r.record_count,
                "last_record": r.last_record_date.isoformat(),
            }
            for r in rows
        ],
    }
    tr = (
        f"Son 90 günde performansı gerileyen {len(rows)} sporcu-etkinlik tespit edildi.\n"
        + "\n".join(
            f"- {r.student_name} ({r.distance_m} m {r.stroke}): %{r.decline_percent:.1f} gerileme "
            f"({format_swim_time(r.baseline_mean)} → {format_swim_time(r.recent_mean)})"
            for r in rows[:10]
        )
    )
    en = (
        f"{len(rows)} athlete-event pairs declined over the last 90 days.\n"
        + "\n".join(
            f"- {r.student_name} ({r.distance_m} m {r.stroke}): {r.decline_percent:.1f}% decline"
            for r in rows[:10]
        )
    )
    return metrics, len(rows), tr, en


def _top_improvers_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    rows = find_top_improvers(db, lookback_days=90, min_records=3, limit=20)
    metrics = {
        "improver_count": len(rows),
        "athletes": [
            {
                "student": r.student_name,
                "event": f"{r.distance_m} m {r.stroke}",
                "first_time": format_swim_time(r.first_time),
                "last_time": format_swim_time(r.last_time),
                "improvement_seconds": r.improvement_seconds,
                "improvement_percent": r.improvement_percent,
                "records": r.record_count,
            }
            for r in rows
        ],
    }
    tr = f"Son 90 günde en çok gelişen {len(rows)} sporcu-etkinlik:\n" + "\n".join(
        f"- {r.student_name} ({r.distance_m} m {r.stroke}): "
        f"{format_swim_time(r.first_time)} → {format_swim_time(r.last_time)} "
        f"(%{r.improvement_percent:.2f} iyileşme)"
        for r in rows[:10]
    )
    en = f"Top {len(rows)} improving athlete-events over 90 days:\n" + "\n".join(
        f"- {r.student_name} ({r.distance_m} m {r.stroke}): {r.improvement_percent:.2f}% faster"
        for r in rows[:10]
    )
    return metrics, len(rows), tr, en


def _weakest_stroke_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    metrics, count, tr, en = _student_performance_metrics(db, request)
    if "error" in metrics:
        return metrics, count, tr, en
    metrics["focus"] = "weakest_stroke"
    return metrics, count, tr, en


def _readiness_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    rows = competition_readiness(db, lookback_days=60)
    metrics = {"athlete_count": len(rows), "readiness": rows[:25]}
    tr = (
        f"{len(rows)} sporcu-etkinlik için hazırlık skoru hesaplandı (istatistiksel).\n"
        + "\n".join(
            f"- {r['student_name']} ({r['event_name']}): skor {r['readiness_score']}, "
            f"en iyi {r['best_time_formatted']}, eğilim {r['trend']}"
            for r in rows[:10]
        )
    )
    en = (
        f"Readiness scores computed for {len(rows)} athlete-events (statistical).\n"
        + "\n".join(
            f"- {r['student_name']} ({r['event_name']}): score {r['readiness_score']}, trend {r['trend']}"
            for r in rows[:10]
        )
    )
    return metrics, len(rows), tr, en


def _attendance_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    start, end = resolve_period(
        "custom" if request.date_from else "quarter", request.date_from, request.date_to
    )
    stats = attendance_statistics(db, start, end)
    metrics = stats.model_dump(mode="json", exclude={"trend"})
    total = (
        stats.present_count
        + stats.absent_count
        + stats.late_count
        + stats.excused_count
    )
    tr = (
        f"{start} - {end} arası devam oranı %{stats.overall_rate}. "
        f"Geldi: {stats.present_count}, gelmedi: {stats.absent_count}, "
        f"geç: {stats.late_count}, mazeretli: {stats.excused_count}. "
        f"Devamsızlık oranı %{stats.no_show_rate}."
    )
    en = (
        f"Attendance rate between {start} and {end} is {stats.overall_rate}%. "
        f"Present: {stats.present_count}, absent: {stats.absent_count}, "
        f"late: {stats.late_count}, excused: {stats.excused_count}."
    )
    return metrics, total, tr, en


def _retention_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    start, end = resolve_period("quarter", request.date_from, request.date_to)
    stats = student_statistics(db, start, end)
    previous_start = start - timedelta(days=(end - start).days + 1)
    previous = student_statistics(db, previous_start, start - timedelta(days=1))
    cohorts = cohort_retention(db, months=6)

    metrics = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "current": {
            "total_students": stats.total_students,
            "active": stats.active_students,
            "new_registrations": stats.new_registrations,
            "lost_students": stats.lost_students,
            "retention_rate": stats.retention_rate,
            "churn_rate": stats.churn_rate,
            "attendance_rate": stats.attendance_rate,
            "avg_membership_days": stats.average_membership_days,
        },
        "previous_period": {
            "new_registrations": previous.new_registrations,
            "lost_students": previous.lost_students,
            "retention_rate": previous.retention_rate,
            "churn_rate": previous.churn_rate,
        },
        "level_distribution": [d.model_dump() for d in stats.level_distribution],
        "cohorts": [c.model_dump() for c in cohorts.cohorts[-6:]],
    }
    tr = (
        f"{start} - {end}: aktif öğrenci {stats.active_students}, yeni kayıt "
        f"{stats.new_registrations}, ayrılan {stats.lost_students}. "
        f"Tutundurma %{stats.retention_rate}, kayıp oranı %{stats.churn_rate}. "
        f"Önceki dönem: ayrılan {previous.lost_students}, kayıp %{previous.churn_rate}. "
        f"Ortalama devam oranı %{stats.attendance_rate}."
    )
    en = (
        f"{start} - {end}: active {stats.active_students}, new {stats.new_registrations}, "
        f"lost {stats.lost_students}. Retention {stats.retention_rate}%, churn {stats.churn_rate}%. "
        f"Previous period churn {previous.churn_rate}%."
    )
    return metrics, stats.total_students, tr, en


def _finance_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    from sqlalchemy import func, select

    from app.models.enums import PaymentStatus
    from app.models.finance import Expense, Invoice, Payment

    start, end = resolve_period(
        "custom" if request.date_from else "month", request.date_from, request.date_to
    )
    income = (
        db.scalar(
            select(
                func.coalesce(func.sum(Payment.amount - Payment.refunded_amount), 0)
            ).where(
                Payment.payment_date >= start,
                Payment.payment_date <= end,
                Payment.status != PaymentStatus.CANCELLED,
            )
        )
        or 0
    )
    expense = (
        db.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.expense_date >= start, Expense.expense_date <= end
            )
        )
        or 0
    )
    outstanding = (
        db.scalar(
            select(
                func.coalesce(func.sum(Invoice.total_amount - Invoice.paid_amount), 0)
            ).where(Invoice.total_amount > Invoice.paid_amount)
        )
        or 0
    )
    overdue_count = (
        db.scalar(
            select(func.count(Invoice.id)).where(
                Invoice.due_date < date.today(),
                Invoice.total_amount > Invoice.paid_amount,
            )
        )
        or 0
    )

    metrics = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "currency": settings.app_currency,
        "total_income": round(float(income), 2),
        "total_expense": round(float(expense), 2),
        "net": round(float(income) - float(expense), 2),
        "outstanding_total": round(float(outstanding), 2),
        "overdue_invoice_count": overdue_count,
    }
    tr = (
        f"{start} - {end}: gelir {float(income):,.2f}, gider {float(expense):,.2f}, "
        f"net {float(income) - float(expense):,.2f} {settings.app_currency}. "
        f"Bekleyen alacak {float(outstanding):,.2f}, geciken fatura {overdue_count}."
    )
    en = (
        f"{start} - {end}: income {float(income):,.2f}, expense {float(expense):,.2f}, "
        f"net {float(income) - float(expense):,.2f}. Outstanding {float(outstanding):,.2f}."
    )
    return metrics, 1 if income or expense else 0, tr, en


def _instructor_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    start, end = resolve_period(
        "custom" if request.date_from else "month", request.date_from, request.date_to
    )
    stats = instructor_statistics(db, start, end)
    metrics = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "total_hours": stats.total_hours,
        "average_occupancy": stats.average_occupancy,
        "instructors": [r.model_dump() for r in stats.rows],
    }
    tr = (
        f"{start} - {end} eğitmen yükü (toplam {stats.total_hours} saat):\n"
        + "\n".join(
            f"- {r.full_name}: {r.lesson_count} ders, {r.total_hours} saat, "
            f"doluluk %{r.occupancy_rate}, devam %{r.attendance_rate}, iptal %{r.cancellation_rate}"
            for r in stats.rows[:12]
        )
    )
    en = (
        f"{start} - {end} instructor workload (total {stats.total_hours}h):\n"
        + "\n".join(
            f"- {r.full_name}: {r.lesson_count} lessons, {r.total_hours}h, occupancy {r.occupancy_rate}%"
            for r in stats.rows[:12]
        )
    )
    return metrics, len(stats.rows), tr, en


def _schedule_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    start, end = resolve_period(
        "custom" if request.date_from else "month", request.date_from, request.date_to
    )
    stats = pool_statistics(db, start, end, request.pool_id)
    metrics = {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "overall_occupancy": stats.overall_occupancy,
        "busiest_hour": stats.busiest_hour,
        "quietest_hour": stats.quietest_hour,
        "most_used_lane": stats.most_used_lane,
        "free_capacity_hours": stats.free_capacity_hours,
        "hourly_load": [p.model_dump() for p in stats.hourly_load],
        "daily_load": [p.model_dump() for p in stats.daily_load],
        "lane_usage": [d.model_dump() for d in stats.lane_usage],
    }
    tr = (
        f"{start} - {end}: genel havuz doluluğu %{stats.overall_occupancy}. "
        f"En yoğun saat {stats.busiest_hour}, en boş saat {stats.quietest_hour}. "
        f"Kullanılmayan kapasite {stats.free_capacity_hours} saat.\n"
        + "\n".join(
            f"- {p.label}: {p.value} dakika" for p in stats.hourly_load if p.value > 0
        )
    )
    en = (
        f"{start} - {end}: overall pool occupancy {stats.overall_occupancy}%. "
        f"Busiest {stats.busiest_hour}, quietest {stats.quietest_hour}. "
        f"Unused capacity {stats.free_capacity_hours} hours."
    )
    return metrics, 1, tr, en


def _payment_risk_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    from sqlalchemy import select

    from app.models.enums import MembershipStatus
    from app.models.finance import Invoice
    from app.models.membership import Membership

    overdue = db.scalars(
        select(Invoice).where(
            Invoice.due_date < date.today(), Invoice.total_amount > Invoice.paid_amount
        )
    ).all()
    expiring = db.scalars(
        select(Membership).where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.end_date.is_not(None),
            Membership.end_date <= date.today() + timedelta(days=14),
        )
    ).all()

    # Satırlar ve toplam önce tipli yerel değişkenlerde tutulur; heterojen
    # `metrics` sözlüğünden okumak tip bilgisini kaybettiriyordu.
    overdue_rows: list[dict[str, Any]] = [
        {
            "student": inv.student.full_name if inv.student else None,
            "balance": round(inv.balance, 2),
            "days_overdue": inv.days_overdue,
            "due_date": inv.due_date.isoformat(),
        }
        for inv in overdue[:40]
    ]
    overdue_total = round(sum(inv.balance for inv in overdue), 2)
    metrics = {
        "overdue_invoices": overdue_rows,
        "overdue_count": len(overdue),
        "overdue_total": overdue_total,
        "expiring_memberships": len(expiring),
    }
    tr = (
        f"{len(overdue)} geciken fatura, toplam {overdue_total:,.2f} "
        f"{settings.app_currency}. 14 gün içinde bitecek {len(expiring)} üyelik var.\n"
        + "\n".join(
            f"- {row['student']}: {row['balance']:,.2f} "
            f"({row['days_overdue']} gün gecikmiş)"
            for row in overdue_rows[:10]
        )
    )
    en = (
        f"{len(overdue)} overdue invoices totalling {overdue_total:,.2f}. "
        f"{len(expiring)} memberships expire within 14 days."
    )
    return metrics, len(overdue) + len(expiring), tr, en


def _general_metrics(
    db: Session, request: AIAnalysisRequest
) -> tuple[dict, int, str, str]:
    from app.services.statistics_engine import dashboard_summary

    data = dashboard_summary(db)
    metrics = {
        key: value
        for key, value in data.items()
        if key
        not in (
            "today_lessons",
            "revenue_trend",
            "attendance_trend",
            "level_distribution",
            "pool_load",
            "generated_at",
        )
    }
    tr = (
        f"Aktif öğrenci {data['active_students']}, bugünkü ders {data['lessons_today']}, "
        f"havuz doluluğu %{data['pool_occupancy_rate']}, aylık gelir "
        f"{data['monthly_revenue']:,.2f}, geciken ödeme {data['overdue_count']} adet "
        f"({data['overdue_amount']:,.2f}), bitmek üzere olan üyelik "
        f"{data['expiring_memberships']}."
    )
    en = (
        f"Active students {data['active_students']}, lessons today {data['lessons_today']}, "
        f"pool occupancy {data['pool_occupancy_rate']}%, monthly revenue {data['monthly_revenue']:,.2f}."
    )
    return metrics, data["total_students"], tr, en


SCOPE_COLLECTORS = {
    "student_performance": _student_performance_metrics,
    "training_suggestion": _student_performance_metrics,
    "weakest_stroke": _weakest_stroke_metrics,
    "declining_students": _declining_metrics,
    "top_improvers": _top_improvers_metrics,
    "competition_readiness": _readiness_metrics,
    "attendance": _attendance_metrics,
    "retention": _retention_metrics,
    "finance": _finance_metrics,
    "instructor_workload": _instructor_metrics,
    "schedule_optimization": _schedule_metrics,
    "free_lanes": _schedule_metrics,
    "payment_risk": _payment_risk_metrics,
    "general": _general_metrics,
}


# ===========================================================================
# AI yanıtı ayrıştırma
# ===========================================================================
def _parse_sections(text: str) -> tuple[str, list[str], list[str]]:
    """AI yanıtını yorum / nedenler / öneriler bölümlerine ayırır."""
    interpretation_lines: list[str] = []
    causes: list[str] = []
    recommendations: list[str] = []
    current = "interpretation"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        lowered = line.lower().lstrip("#").strip()
        if lowered.startswith(
            ("olası nedenler", "possible causes", "nedenler", "causes")
        ):
            current = "causes"
            continue
        if lowered.startswith(("öneriler", "recommendations", "tavsiyeler", "actions")):
            current = "recommendations"
            continue
        if lowered.startswith(
            ("yorum", "interpretation", "değerlendirme", "assessment", "analiz")
        ):
            current = "interpretation"
            continue
        if not line:
            continue

        if line.startswith(("-", "•", "*")) or (
            line[:2].rstrip(".").isdigit() and "." in line[:3]
        ):
            item = line.lstrip("-•*0123456789. ").strip()
            if not item:
                continue
            if current == "causes":
                causes.append(item)
            elif current == "recommendations":
                recommendations.append(item)
            else:
                interpretation_lines.append(item)
        elif current == "interpretation":
            interpretation_lines.append(line)
        elif current == "causes":
            causes.append(line)
        else:
            recommendations.append(line)

    return " ".join(interpretation_lines).strip(), causes[:8], recommendations[:8]


def _resolve_language(request_language: str, user_language: str) -> str:
    if request_language in ("tr", "en"):
        return request_language
    if settings.ai_response_language in ("tr", "en"):
        return settings.ai_response_language
    return (
        user_language
        if user_language in ("tr", "en")
        else settings.app_default_language
    )


# ===========================================================================
# Ana analiz fonksiyonu
# ===========================================================================
def run_analysis(
    db: Session,
    request: AIAnalysisRequest,
    *,
    user_id: int | None = None,
    user_language: str = "tr",
) -> AIAnalysisResponse:
    """Metrikleri hesaplar, AI'ya gönderir ve ayrıştırılmış yanıt döndürür.

    AI kullanılamıyorsa yalnızca gerçek metriklerle yanıt döner - hata fırlatmaz.
    """
    lang = _resolve_language(request.language, user_language)
    collector = SCOPE_COLLECTORS.get(request.scope, _general_metrics)
    metrics, data_points, summary_tr, summary_en = collector(db, request)

    response = AIAnalysisResponse(
        question=request.question,
        scope=request.scope,
        metrics=metrics,
        metrics_summary_tr=summary_tr,
        metrics_summary_en=summary_en,
        data_points=data_points,
        data_sufficient=data_points >= MIN_DATA_POINTS,
    )

    if not response.data_sufficient:
        response.ai_interpretation = None
        response.ai_available = False
        return response

    is_coaching = request.scope in (
        "training_suggestion",
        "student_performance",
        "weakest_stroke",
        "competition_readiness",
    )
    system_prompt = (
        coach_system_prompt(lang) if is_coaching else analyst_system_prompt(lang)
    )

    student_name = None
    if request.student_id:
        student = db.get(Student, request.student_id)
        student_name = student.full_name if student else None

    user_content = (
        f"SORU: {request.question}\n\n"
        f"HESAPLANMIŞ İSTATİSTİKLER (gerçek veri):\n"
        f"{summary_tr if lang == 'tr' else summary_en}\n\n"
        f"AYRINTILI METRİKLER (JSON):\n"
        f"{json.dumps(metrics, ensure_ascii=False, default=str)[:6000]}\n"
    )
    if student_name:
        user_content += f"\nSporcu: {student_name}\n"
    user_content += (
        "\nYukarıdaki gerçek verilere dayanarak yanıt ver. Sayıları değiştirme."
        if lang == "tr"
        else "\nAnswer based on the real data above. Do not alter the numbers."
    )

    task = start_task(
        db,
        kind=AITaskKind.ANALYSIS,
        title=f"[{request.scope}] {request.question[:120]}",
        user_id=user_id,
        prompt=user_content,
    )

    try:
        # HSP geçidi: yük sınıflandırılır, sağlayıcı kanıtı doğrulanır ve
        # gerçek kişi adları modele gitmeden takma adla değiştirilir.
        # Karar BLOCK ise çağrı hiç yapılmaz; istatistikler yine döner.
        names = collect_names(metrics)
        if student_name:
            names[student_name] = "student"

        outcome = hsp_gateway.chat(
            db,
            [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_content),
            ],
            operation=f"ai.analyze.{request.scope}",
            field_paths=fields_for(request.scope),
            subject_names=names,
            preferred=request.provider,
            task="reasoning" if is_coaching else "general",
            actor_user_id=user_id,
            subject_kind="student" if request.student_id else None,
            subject_ref=str(request.student_id) if request.student_id else None,
        )

        response.hsp_decision = str(outcome.evaluation.decision)
        response.hsp_receipt_id = outcome.receipt_id
        response.hsp_pseudonymised = outcome.pseudonymised

        if outcome.blocked:
            response.ai_available = False
            response.ai_interpretation = None
            response.hsp_blocked_reason = outcome.refusal_message(lang)
            logger.info(
                "HSP analizi engelledi: kapsam=%s karar=%s",
                request.scope,
                outcome.evaluation.decision,
            )
            finish_task(db, task, error=response.hsp_blocked_reason)
            response.task_id = task.id
            return response

        result = outcome.result
        assert result is not None  # blocked kontrolünden sonra garanti
        attempted, fallback_used = outcome.attempted, outcome.fallback_used
        interpretation, causes, recommendations = _parse_sections(result.content)

        response.ai_available = True
        response.ai_interpretation = interpretation or result.content[:2000]
        response.ai_possible_causes = causes
        response.ai_recommendations = recommendations
        response.provider = result.provider
        response.model = result.model
        response.duration_ms = result.duration_ms

        finish_task(
            db, task, result=result, attempted=attempted, fallback_used=fallback_used
        )
        response.task_id = task.id

    except AIProviderError as exc:
        logger.warning(
            "AI analizi başarısız, yalnızca istatistikler döndürülüyor: %s", exc
        )
        response.ai_available = False
        response.ai_interpretation = None
        finish_task(db, task, error=str(exc))
        response.task_id = task.id

    return response


def generate_training_plan(
    db: Session,
    student_id: int,
    weeks: int = 4,
    *,
    user_id: int | None = None,
    lang: str = "tr",
) -> dict[str, Any]:
    """Sporcu için AI destekli antrenman planı taslağı üretir.

    Plan `is_approved=False` olarak kaydedilir; eğitmen onayı olmadan yürürlüğe girmez.
    """
    from app.models.performance import TrainingPlan

    student = db.get(Student, student_id)
    if student is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("student.not_found")

    summary = student_performance_summary(db, student_id)
    request = AIAnalysisRequest(
        question=(
            f"{student.full_name} için gelecek {weeks} haftalık antrenman önerisi oluştur."
            if lang == "tr"
            else f"Create a {weeks}-week training plan for {student.full_name}."
        ),
        scope="training_suggestion",
        student_id=student_id,
        language=lang,
    )
    analysis = run_analysis(db, request, user_id=user_id, user_language=lang)

    plan = TrainingPlan(
        student_id=student_id,
        title=(
            f"{weeks} Haftalık AI Antrenman Planı"
            if lang == "tr"
            else f"{weeks}-Week AI Training Plan"
        ),
        start_date=date.today(),
        end_date=date.today() + timedelta(weeks=weeks),
        focus_areas=[summary.weakest_stroke] if summary.weakest_stroke else [],
        weekly_sessions=[],
        goals=analysis.ai_interpretation,
        notes="\n".join(analysis.ai_recommendations),
        ai_generated=True,
        ai_provider=analysis.provider,
        ai_model=analysis.model,
        is_approved=False,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return {
        "plan_id": plan.id,
        "student_id": student_id,
        "student_name": student.full_name,
        "weeks": weeks,
        "ai_available": analysis.ai_available,
        "metrics": analysis.metrics,
        "metrics_summary": (
            analysis.metrics_summary_tr if lang == "tr" else analysis.metrics_summary_en
        ),
        "ai_interpretation": analysis.ai_interpretation,
        "ai_recommendations": analysis.ai_recommendations,
        "requires_approval": True,
        "disclaimer": (
            analysis.ai_disclaimer_tr if lang == "tr" else analysis.ai_disclaimer_en
        ),
    }
