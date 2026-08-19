"""Analiz kapsamlarının veri haritası / Data map for analysis scopes.

Her AI analiz kapsamının hangi alanlara dokunduğunu bildirir. Politika motoru
bu listeden yükü sınıflandırır.

Bu harita bilinçli olarak **elle** tutulur. Otomatik çıkarım, yeni bir alan
eklendiğinde sessizce "kişisel veri yok" sonucuna varabilirdi; elle tutulan
harita eksik kaldığında ise kapsam `general` sayılır ve en kısıtlı muameleyi
görür — yani hata güvenli tarafa düşer.
"""

from __future__ import annotations

from typing import Any

# Kişisel veri taşımayan işletme metrikleri
_OPERATIONAL = ["lesson.start_time", "pool.name", "attendance.status"]

SCOPE_FIELDS: dict[str, list[str]] = {
    "student_performance": [
        "student.full_name",
        "student.swim_level",
        "performance.time_seconds",
        "attendance.status",
    ],
    "training_suggestion": [
        "student.full_name",
        "student.swim_level",
        "student.goals",
        "performance.time_seconds",
    ],
    "weakest_stroke": [
        "student.full_name",
        "performance.time_seconds",
    ],
    "declining_students": [
        "student.full_name",
        "performance.time_seconds",
        "attendance.status",
    ],
    "top_improvers": [
        "student.full_name",
        "performance.time_seconds",
    ],
    "competition_readiness": [
        "student.full_name",
        "student.swim_level",
        "performance.time_seconds",
    ],
    "attendance": [
        "student.full_name",
        "attendance.status",
    ],
    "retention": [
        # Kohort metrikleri toplulaştırılmıştır; birey adı taşımaz.
        *_OPERATIONAL,
    ],
    "finance": [
        "invoice.amount",
        "invoice.balance",
    ],
    "instructor_workload": [
        "instructor.full_name",
        "lesson.start_time",
    ],
    "schedule_optimization": _OPERATIONAL,
    "free_lanes": _OPERATIONAL,
    "payment_risk": [
        "student.full_name",
        "invoice.amount",
        "invoice.balance",
    ],
    # Bilinmeyen/karma kapsam: en kısıtlı muamele için kişi adı varsayılır.
    "general": [
        "student.full_name",
        "invoice.balance",
        *_OPERATIONAL,
    ],
}

# Metrik sözlüklerinde kişi adı taşıyan anahtarlar ve veri sahibi türü
NAME_KEYS: dict[str, str] = {
    "student": "student",
    "student_name": "student",
    "full_name": "student",
    "instructor": "instructor",
    "instructor_name": "instructor",
    "guardian": "guardian",
    "guardian_name": "guardian",
}


def fields_for(scope: str) -> list[str]:
    """Kapsamın alan listesi. Tanımsız kapsam `general` gibi ele alınır."""
    return SCOPE_FIELDS.get(scope, SCOPE_FIELDS["general"])


def collect_names(value: Any, found: dict[str, str] | None = None) -> dict[str, str]:
    """Metrik yapısını gezip kişi adlarını toplar.

    Dönüş: {gerçek ad: veri sahibi türü}. Geçit bu haritadan takma ad üretir.
    İç içe sözlük ve listeler tam olarak taranır; ad taşıyan bir anahtar
    gözden kaçarsa o ad prompt'a gerçek hâliyle gider, bu yüzden `NAME_KEYS`
    kapsayıcı tutulur.
    """
    found = {} if found is None else found

    if isinstance(value, dict):
        for key, item in value.items():
            subject = NAME_KEYS.get(key)
            if subject and isinstance(item, str) and item.strip():
                found[item.strip()] = subject
            else:
                collect_names(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            collect_names(item, found)

    return found
