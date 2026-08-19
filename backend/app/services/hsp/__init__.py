"""Human Sovereignty Protocol — makine yetkisinin eylemden önce değerlendirilmesi.

    Bu makine bu insana ne yapmaya yetkili?

Katmanlar:

    classification  KNOW  — hangi veri, hangi sınıf, kimin hakkında
    providers       KNOW  — hedef sağlayıcının veri koruma kanıtı
    policy          hepsi — eylemden önce ALLOW/REDACT/LOCAL_ONLY/BLOCK kararı
    redaction       hepsi — kararın veri üzerinde uygulanması
    gateway         KNOW  — AI çağrılarının tek denetim noktası
    receipts        hepsi — hash zincirli, kurcalamaya dayanıklı kanıt
"""

from app.services.hsp.classification import (
    Classification,
    FieldLabel,
    Handling,
    PersonalDataKind,
    classify_payload,
    label_for,
)
from app.services.hsp.policy import (
    ActionContext,
    Decision,
    Domain,
    Evaluation,
    evaluate,
)
from app.services.hsp.providers import ProviderEvidence, evidence_for, registry_view

__all__ = [
    "ActionContext",
    "Classification",
    "Decision",
    "Domain",
    "Evaluation",
    "FieldLabel",
    "Handling",
    "PersonalDataKind",
    "ProviderEvidence",
    "classify_payload",
    "evaluate",
    "evidence_for",
    "label_for",
    "registry_view",
]
