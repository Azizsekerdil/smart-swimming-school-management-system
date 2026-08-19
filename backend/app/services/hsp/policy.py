"""HSP politika motoru / Human Sovereignty Protocol policy engine.

Tek soru sorar ve eylemden **önce** cevaplar:

    Bu makine bu insana ne yapmaya yetkili?

Üç ayrı alan bağımsız değerlendirilir:

    KNOW    — sistem insan hakkında ne öğreniyor?
    DECIDE  — insan hakkında hangi kararı veriyor?
    ACT     — insanın dünyasında ne yapıyor?

Motorun iki değişmez kuralı vardır:

1. **Fail-safe.** Kural bulunamazsa, sınıf bilinmiyorsa ya da değerlendirme
   sırasında hata oluşursa sonuç `BLOCK` olur. Sessiz fail-open yoktur (§35).
2. **Gerekçe zorunludur.** Her karar, hangi kuralın neden uygulandığını taşır;
   gerekçesiz `ALLOW` üretilemez.

Motor hukuki görüş vermez. Politika kararı üretir ve kanıtı kaydeder; nihai
hukuki değerlendirme insan incelemesine bırakılır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from app.services.hsp.classification import (
    Classification,
    FieldLabel,
    Handling,
    PersonalDataKind,
    at_least,
    classify_payload,
    involves_child,
)

POLICY_VERSION = "hsp-swim-1.0.0"


class Domain(StrEnum):
    """HSP'nin üç değerlendirme alanı."""

    KNOW = "know"
    DECIDE = "decide"
    ACT = "act"


class Decision(StrEnum):
    """Politika sonucu. Kısıtlılık sırası aşağıdan yukarıya artar."""

    ALLOW = "allow"
    PSEUDONYMIZE = "pseudonymize"
    REDACT = "redact"
    LOCAL_ONLY = "local_only"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


_SEVERITY: dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.PSEUDONYMIZE: 1,
    Decision.REDACT: 2,
    Decision.LOCAL_ONLY: 3,
    Decision.REQUIRE_APPROVAL: 4,
    Decision.BLOCK: 5,
}


def most_restrictive(*decisions: Decision) -> Decision:
    """En kısıtlı kararı seçer. Boş küme `BLOCK` döner (fail-safe)."""
    if not decisions:
        return Decision.BLOCK
    return max(decisions, key=lambda item: _SEVERITY[item])


@dataclass(frozen=True)
class ActionContext:
    """Değerlendirilecek makine eylemi."""

    domain: Domain
    # Ne yapılmak isteniyor: "ai.analyze", "ai.training_plan", "notify.guardian"
    operation: str
    # Yükte geçen alan yolları — sınıflandırma bunlardan türetilir
    field_paths: list[str] = field(default_factory=list)
    # Hedef sağlayıcı yereldeyse True (veri kurumdan çıkmaz)
    provider_is_local: bool = True
    # Sağlayıcı kanıtı: bölge / saklama / eğitimde kullanım
    provider_region: str | None = None
    provider_retains_data: bool | None = None
    provider_trains_on_data: bool | None = None
    # Kararın bir insan hakkında olup olmadığı (DECIDE alanı için)
    decision_affects_person: bool = False
    # Kararın hukuki/ekonomik/fiziksel etkisi var mı (GDPR Art.22 benzeri)
    decision_has_legal_effect: bool = False
    # Eylemin geri alınabilirliği (ACT alanı için)
    action_is_reversible: bool = True
    # İnsan onayı alınmış mı
    human_approved: bool = False
    # Çağıran kullanıcının rolü — yalnızca kanıt için kaydedilir
    actor_role: str | None = None


@dataclass
class Evaluation:
    """Politika değerlendirmesinin sonucu ve kanıtı."""

    decision: Decision
    domain: Domain
    operation: str
    classification: Classification
    personal_kind: PersonalDataKind
    concerns_child: bool
    reasons_tr: list[str] = field(default_factory=list)
    reasons_en: list[str] = field(default_factory=list)
    # Hangi alanın nasıl işleneceği — gateway bunu uygular
    field_handling: dict[str, Handling] = field(default_factory=dict)
    policy_version: str = POLICY_VERSION
    # Bu değerlendirme insan incelemesi gerektiriyor mu
    requires_human_review: bool = False

    @property
    def allowed(self) -> bool:
        """Eylem hiç yapılabilir mi? (Dönüşümlerle birlikte)"""
        return self.decision not in (Decision.BLOCK, Decision.REQUIRE_APPROVAL)

    def add(self, tr: str, en: str) -> None:
        self.reasons_tr.append(tr)
        self.reasons_en.append(en)

    def to_evidence(self) -> dict:
        """Denetim kaydına yazılacak kanıt. Ham veri içermez."""
        return {
            "decision": str(self.decision),
            "domain": str(self.domain),
            "operation": self.operation,
            "classification": str(self.classification),
            "personal_kind": str(self.personal_kind),
            "concerns_child": self.concerns_child,
            "policy_version": self.policy_version,
            "requires_human_review": self.requires_human_review,
            "reasons": self.reasons_en,
            "field_count": len(self.field_handling),
        }


# ---------------------------------------------------------------------------
# Alan bazlı kurallar
# ---------------------------------------------------------------------------
def _evaluate_know(ctx: ActionContext, labels: list[FieldLabel]) -> list[Decision]:
    """KNOW: sistemin insan hakkında ne öğrendiği ve nereye gönderdiği."""
    decisions: list[Decision] = []
    classification, kind, _ = classify_payload(ctx.field_paths)

    # Özel nitelikli veri hiçbir dış sağlayıcıya gitmez.
    if kind is PersonalDataKind.SENSITIVE and not ctx.provider_is_local:
        decisions.append(Decision.BLOCK)
    elif kind is PersonalDataKind.SENSITIVE:
        # Yerelde bile özel nitelikli alanlar prompt'a konmaz; yalnızca
        # türetilmiş ölçüm gönderilir.
        decisions.append(Decision.REDACT)

    # Bilinmeyen sınıf serbest değildir.
    if kind is PersonalDataKind.UNKNOWN:
        decisions.append(Decision.REQUIRE_APPROVAL)

    # Varsayılan yönlendirme eşiği (§12): confidential yerel tercih edilir,
    # restricted yalnızca yerel.
    if classification is Classification.RESTRICTED:
        decisions.append(Decision.LOCAL_ONLY)
    elif (
        at_least(classification, Classification.CONFIDENTIAL)
        and not ctx.provider_is_local
    ):
        decisions.append(Decision.LOCAL_ONLY)

    # Bulut sağlayıcıya kişisel veri: kanıt yoksa gönderilmez.
    if kind is PersonalDataKind.PERSONAL and not ctx.provider_is_local:
        if ctx.provider_trains_on_data is not False:
            # "Eğitimde kullanılmıyor" kanıtı yoksa varsayım lehte değildir.
            decisions.append(Decision.BLOCK)
        elif ctx.provider_region is None:
            decisions.append(Decision.REQUIRE_APPROVAL)
        else:
            decisions.append(Decision.PSEUDONYMIZE)

    # Çocuk verisi ek koruma alır.
    if involves_child(labels) and not ctx.provider_is_local:
        decisions.append(Decision.BLOCK)

    return decisions or [Decision.ALLOW]


def _evaluate_decide(ctx: ActionContext) -> list[Decision]:
    """DECIDE: insan hakkında karar üretimi."""
    if not ctx.decision_affects_person:
        return [Decision.ALLOW]

    decisions: list[Decision] = []
    # Hukuki/ekonomik etkisi olan tamamen otomatik karar insan onayı ister.
    if ctx.decision_has_legal_effect and not ctx.human_approved:
        decisions.append(Decision.REQUIRE_APPROVAL)
    else:
        # Etkisi sınırlı olsa da karar bir insan hakkındaysa itiraz yolu
        # açık kalmalı; bu yüzden karar kaydı zorunludur (makbuz üretilir).
        decisions.append(Decision.ALLOW)
    return decisions


def _evaluate_act(ctx: ActionContext) -> list[Decision]:
    """ACT: insanın dünyasında fiili değişiklik."""
    decisions: list[Decision] = []
    if not ctx.action_is_reversible and not ctx.human_approved:
        decisions.append(Decision.REQUIRE_APPROVAL)
    return decisions or [Decision.ALLOW]


def evaluate(ctx: ActionContext) -> Evaluation:
    """Eylemi değerlendirir. Hata durumunda bile asla açık uçlu kalmaz."""
    try:
        classification, kind, labels = classify_payload(ctx.field_paths)
        child = involves_child(labels)

        result = Evaluation(
            decision=Decision.BLOCK,  # fail-safe başlangıç
            domain=ctx.domain,
            operation=ctx.operation,
            classification=classification,
            personal_kind=kind,
            concerns_child=child,
        )

        if ctx.domain is Domain.KNOW:
            decisions = _evaluate_know(ctx, labels)
        elif ctx.domain is Domain.DECIDE:
            decisions = _evaluate_decide(ctx)
        else:
            decisions = _evaluate_act(ctx)

        result.decision = most_restrictive(*decisions)

        # Alan bazlı işleme planı — gateway bunu birebir uygular.
        for item in labels:
            handling = item.handling
            if result.decision is Decision.REDACT and handling is Handling.PASS:
                handling = Handling.REDACT
            result.field_handling[item.path] = handling

        _explain(result, ctx, kind, classification, child)
        result.requires_human_review = (
            result.decision
            in (
                Decision.REQUIRE_APPROVAL,
                Decision.BLOCK,
            )
            or kind is PersonalDataKind.UNKNOWN
        )
        return result

    except Exception as exc:  # pragma: no cover - savunma amaçlı
        # Değerlendirme çökerse eylem yapılmaz. Bu dal bilinçli olarak geniştir.
        failed = Evaluation(
            decision=Decision.BLOCK,
            domain=ctx.domain,
            operation=ctx.operation,
            classification=Classification.RESTRICTED,
            personal_kind=PersonalDataKind.UNKNOWN,
            concerns_child=False,
            requires_human_review=True,
        )
        failed.add(
            f"Politika değerlendirmesi başarısız oldu ({type(exc).__name__}); eylem engellendi.",
            f"Policy evaluation failed ({type(exc).__name__}); action blocked.",
        )
        return failed


def _explain(
    result: Evaluation,
    ctx: ActionContext,
    kind: PersonalDataKind,
    classification: Classification,
    child: bool,
) -> None:
    """Karara gerekçe ekler. Gerekçesiz karar üretilmez."""
    target = "yerel model" if ctx.provider_is_local else "bulut sağlayıcı"
    target_en = "local model" if ctx.provider_is_local else "cloud provider"

    if kind is PersonalDataKind.SENSITIVE:
        result.add(
            "Yük özel nitelikli kişisel veri içeriyor (KVKK m.6 / GDPR Art.9).",
            "Payload contains special category personal data (KVKK Art.6 / GDPR Art.9).",
        )
    if kind is PersonalDataKind.UNKNOWN:
        result.add(
            "Yükte sınıflandırılmamış alan var; bilinmeyen otomatik olarak izinli sayılmaz.",
            "Payload has unclassified fields; unknown is not treated as allowed.",
        )
    if child:
        result.add(
            "Veri çocuğa ait olabilir; ek koruma uygulandı.",
            "Data may concern a child; additional protection applied.",
        )
    if not ctx.provider_is_local and kind is not PersonalDataKind.NON_PERSONAL:
        if ctx.provider_trains_on_data is not False:
            result.add(
                "Sağlayıcının veriyi eğitimde kullanmadığına dair kanıt yok.",
                "No evidence that the provider excludes the data from training.",
            )
        if ctx.provider_region is None:
            result.add(
                "Sağlayıcı işleme bölgesi bilinmiyor; yurt dışı aktarım değerlendirilemiyor.",
                "Provider processing region is unknown; cross-border transfer cannot be assessed.",
            )
    if ctx.domain is Domain.DECIDE and ctx.decision_has_legal_effect:
        result.add(
            "Karar hukuki veya benzer ölçüde önemli etki taşıyor; insan incelemesi gerekli.",
            "Decision carries legal or similarly significant effect; human review required.",
        )
    if ctx.domain is Domain.ACT and not ctx.action_is_reversible:
        result.add(
            "Eylem geri alınamaz; önce insan onayı gerekiyor.",
            "Action is irreversible; human approval is required first.",
        )
    if not result.reasons_tr:
        result.add(
            f"Sınıf {classification} ve {target} için tanımlı kısıtlama tetiklenmedi.",
            f"No restriction triggered for classification {classification} and {target_en}.",
        )
