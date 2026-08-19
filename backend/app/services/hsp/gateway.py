"""HSP AI geçidi / HSP AI gateway.

Bütün AI çağrıları buradan geçer. Geçit sırayla şunu yapar (§12):

    1. Yükü sınıflandır (hangi alanlar, hangi veri sahibi, çocuk mu?)
    2. Hedef sağlayıcının kanıtını çöz (bölge, saklama, eğitim, DPA)
    3. HSP politikasını **eylemden önce** çalıştır
    4. Kararı uygula: gönder / takma adlaştır / maskele / yerele zorla / engelle
    5. Yanıtı geri eşle (takma ad → gerçek ad, yalnızca uygulama içinde)
    6. Hak makbuzu üret ve zincire ekle

Geçidin sözleşmesi: **karar BLOCK ise çağrı yapılmaz.** Sağlayıcı hatası
durumunda bile politika gevşetilmez; fallback zinciri yalnızca politikanın
izin verdiği sağlayıcılarla sınırlıdır (§12 "Failover sensitive-data policy'yi
gevşetemez").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.services.ai.base import ChatMessage, ChatResult
from app.services.ai.registry import AIRouter, get_provider
from app.services.hsp import receipts
from app.services.hsp.classification import Handling
from app.services.hsp.policy import (
    ActionContext,
    Decision,
    Domain,
    Evaluation,
    evaluate,
)
from app.services.hsp.providers import ProviderEvidence, evidence_for
from app.services.hsp.redaction import build_name_map, replace_names


@dataclass
class GatewayOutcome:
    """Geçidin sonucu — hem AI yanıtı hem de yönetişim kanıtı."""

    evaluation: Evaluation
    result: ChatResult | None = None
    attempted: list[str] = field(default_factory=list)
    fallback_used: bool = False
    receipt_id: int | None = None
    # Kaç gerçek ad takma adla değiştirildi
    pseudonymised: int = 0
    # Politika hangi sağlayıcıları eledi
    excluded_providers: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.result is None

    def refusal_message(self, lang: str = "tr") -> str:
        """Engellendiğinde kullanıcıya gösterilecek açıklama."""
        reasons = (
            self.evaluation.reasons_tr if lang == "tr" else self.evaluation.reasons_en
        )
        head = (
            "Bu analiz yapay zekâya gönderilmedi."
            if lang == "tr"
            else "This analysis was not sent to the AI."
        )
        return head + " " + " ".join(reasons)


def _candidate_providers(router: AIRouter, preferred: str) -> list[str]:
    return router.resolve_chain(preferred)


def _decide_for_provider(
    operation: str,
    field_paths: list[str],
    evidence: ProviderEvidence,
    *,
    actor_role: str | None,
) -> Evaluation:
    return evaluate(
        ActionContext(
            domain=Domain.KNOW,
            operation=operation,
            field_paths=field_paths,
            provider_is_local=evidence.is_local,
            provider_region=evidence.region,
            provider_retains_data=evidence.retains_data,
            provider_trains_on_data=evidence.trains_on_data,
            actor_role=actor_role,
        )
    )


@dataclass
class GatewayPlan:
    """Çağrı öncesi politika kararı — akış (streaming) uçları için.

    ``chat()`` tam bir istek/yanıt döngüsü yürütür. Akışta yanıt parça parça
    geldiği için aynı adımlar iki parçaya ayrılır: önce `preflight()` kararı
    verir ve içeriği dönüştürür, sonra çağıran akışı yürütüp
    `issue_receipt()` ile makbuzu yazar.
    """

    evaluation: Evaluation
    allowed: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    name_map: dict[str, str] = field(default_factory=dict)
    outgoing: list[ChatMessage] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return not self.allowed

    def refusal_message(self, lang: str = "tr") -> str:
        reasons = (
            self.evaluation.reasons_tr if lang == "tr" else self.evaluation.reasons_en
        )
        head = (
            "Bu istek yapay zekâya gönderilmedi."
            if lang == "tr"
            else "This request was not sent to the AI."
        )
        return head + " " + " ".join(reasons)


def preflight(
    db: Session,
    messages: list[ChatMessage],
    *,
    operation: str,
    field_paths: list[str],
    subject_names: dict[str, str] | None = None,
    preferred: str = "auto",
    actor_role: str | None = None,
) -> GatewayPlan:
    """Politika değerlendirmesi + içerik dönüşümü (çağrı yapmadan).

    Geçidin 1-4. adımları. Akış uçları ve geçidin kendi `chat()`'i bunu
    paylaşır; böylece "tek noktadan uygulama" sözleşmesi gerçekten tek
    kod yolundan yürür.
    """
    router = AIRouter(db)
    chain = _candidate_providers(router, preferred)

    allowed: list[str] = []
    excluded: list[str] = []
    evaluations: dict[str, Evaluation] = {}

    for name in chain:
        evidence = evidence_for(name)
        decision = _decide_for_provider(
            operation, field_paths, evidence, actor_role=actor_role
        )
        evaluations[name] = decision
        if decision.decision in (Decision.BLOCK, Decision.REQUIRE_APPROVAL):
            excluded.append(name)
            continue
        if decision.decision is Decision.LOCAL_ONLY and not evidence.is_local:
            excluded.append(name)
            continue
        allowed.append(name)

    if not allowed:
        blocking = evaluations.get(chain[0]) if chain else None
        if blocking is None:
            blocking = evaluate(
                ActionContext(
                    domain=Domain.KNOW, operation=operation, field_paths=field_paths
                )
            )
        return GatewayPlan(evaluation=blocking, allowed=[], excluded=excluded)

    chosen = allowed[0]
    evaluation = evaluations[chosen]

    name_map: dict[str, str] = {}
    if subject_names:
        needs_pseudonym = evaluation.decision in (
            Decision.PSEUDONYMIZE,
            Decision.REDACT,
        ) or any(
            handling in (Handling.PSEUDONYMIZE, Handling.REDACT, Handling.NEVER)
            for handling in evaluation.field_handling.values()
        )
        if needs_pseudonym:
            for kind in set(subject_names.values()):
                names = [n for n, k in subject_names.items() if k == kind]
                name_map.update(build_name_map(names, kind))

    outgoing = messages
    if name_map:
        outgoing = [
            ChatMessage(role=item.role, content=replace_names(item.content, name_map))
            for item in messages
        ]

    return GatewayPlan(
        evaluation=evaluation,
        allowed=allowed,
        excluded=excluded,
        name_map=name_map,
        outgoing=list(outgoing),
    )


def issue_receipt(
    db: Session,
    plan: GatewayPlan,
    *,
    outcome: str,
    provider: str | None = None,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    subject_kind: str | None = None,
    subject_ref: str | None = None,
) -> int | None:
    """Hak makbuzunu zincire ekler ve makbuz kimliğini döndürür."""
    receipt = receipts.issue(
        db,
        plan.evaluation,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        subject_kind=subject_kind,
        subject_ref=subject_ref,
        provider=provider,
        outcome=outcome,
    )
    return receipt.id


def chat(
    db: Session,
    messages: list[ChatMessage],
    *,
    operation: str,
    field_paths: list[str],
    subject_names: dict[str, str] | None = None,
    preferred: str = "auto",
    task: str | None = None,
    json_mode: bool = False,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    subject_kind: str | None = None,
    subject_ref: str | None = None,
) -> GatewayOutcome:
    """Politika denetimli AI çağrısı.

    `field_paths`  : yükte geçen alanların kayıt defteri yolları
    `subject_names`: {gerçek ad: veri sahibi türü} — takma adlaştırma için
    """
    # 1-4) Sınıflandırma, sağlayıcı kanıtı, politika kararı ve içerik dönüşümü
    #      tek ortak kod yolundan (`preflight`) yürür.
    plan = preflight(
        db,
        messages,
        operation=operation,
        field_paths=field_paths,
        subject_names=subject_names,
        preferred=preferred,
        actor_role=actor_role,
    )
    allowed = plan.allowed
    excluded = plan.excluded
    evaluation = plan.evaluation
    name_map = plan.name_map
    outgoing = plan.outgoing

    if plan.blocked:
        receipt_id = issue_receipt(
            db,
            plan,
            outcome="blocked",
            provider=None,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            subject_kind=subject_kind,
            subject_ref=subject_ref,
        )
        return GatewayOutcome(
            evaluation=evaluation,
            result=None,
            attempted=[],
            receipt_id=receipt_id,
            excluded_providers=excluded,
        )

    chosen = allowed[0]

    # 5) Çağrıyı yalnızca izin verilen sağlayıcılarla yap.
    #    Zincir politikayla daraltıldığı için failover politikayı gevşetemez.
    result: ChatResult | None = None
    attempted: list[str] = []
    fallback_used = False
    error: Exception | None = None

    for index, name in enumerate(allowed):
        provider = get_provider(name)
        if provider is None or not provider.enabled:
            continue
        try:
            single = AIRouter(db)
            result, tried, _ = single.chat(
                outgoing,
                preferred=name,
                task=task,
                json_mode=json_mode,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            attempted.extend(tried)
            fallback_used = index > 0
            break
        except Exception as exc:  # sağlayıcı hatası — sıradakini dene
            error = exc
            attempted.append(name)
            continue

    if result is None:
        receipt_id = issue_receipt(
            db,
            plan,
            outcome="provider_error",
            provider=chosen,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            subject_kind=subject_kind,
            subject_ref=subject_ref,
        )
        outcome = GatewayOutcome(
            evaluation=evaluation,
            result=None,
            attempted=attempted,
            receipt_id=receipt_id,
            pseudonymised=len(name_map),
            excluded_providers=excluded,
        )
        if error is not None:
            raise error
        return outcome

    # 6) Yanıttaki takma adları uygulama içinde geri eşle.
    if name_map:
        reverse = {alias: real for real, alias in name_map.items()}
        result.content = replace_names(result.content, reverse)

    receipt_id = issue_receipt(
        db,
        plan,
        outcome="completed",
        provider=result.provider,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        subject_kind=subject_kind,
        subject_ref=subject_ref,
    )

    return GatewayOutcome(
        evaluation=evaluation,
        result=result,
        attempted=attempted,
        fallback_used=fallback_used,
        receipt_id=receipt_id,
        pseudonymised=len(name_map),
        excluded_providers=excluded,
    )
