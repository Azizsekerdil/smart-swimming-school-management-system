"""Hak makbuzları ve kurcalamaya dayanıklı kayıt / Rights receipts and tamper-evident log.

HSP'nin ikinci değişmezi: bir makine bir insan hakkında bir şey öğrendiğinde,
karar verdiğinde veya onun dünyasında bir şey yaptığında bunun **kanıtı**
kalmalıdır. Kanıt sonradan sessizce değiştirilememelidir.

Bu modül bunu hash zinciri ile sağlar:

    receipt[n].chain_hash = SHA256( receipt[n].payload_hash || receipt[n-1].chain_hash )

Herhangi bir kayıt değiştirilir veya araya kayıt sokulursa, o noktadan sonraki
bütün zincir doğrulaması bozulur. Bu, kurcalamayı **imkânsız** kılmaz;
**görünür** kılar. Aradaki fark önemlidir ve raporlarda böyle ifade edilir.

Makbuz ham kişisel veri taşımaz — yalnızca hangi kategorilerin işlendiği,
hangi kararın verildiği ve gerekçesi tutulur (§14: "ham PII/secret tutulmaz").
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hsp import RightsReceipt
from app.services.hsp.policy import Evaluation

GENESIS = "0" * 64


def _canonical(payload: dict) -> str:
    """Kararlı JSON gösterimi — hash'in yeniden üretilebilir olması için."""
    return json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def chain_hash(current_payload_hash: str, previous_chain_hash: str) -> str:
    return hashlib.sha256(
        (current_payload_hash + previous_chain_hash).encode("utf-8")
    ).hexdigest()


def _latest(db: Session) -> RightsReceipt | None:
    return db.scalar(select(RightsReceipt).order_by(RightsReceipt.id.desc()).limit(1))


def issue(
    db: Session,
    evaluation: Evaluation,
    *,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    subject_kind: str | None = None,
    subject_ref: str | None = None,
    provider: str | None = None,
    outcome: str = "completed",
    flush: bool = True,
) -> RightsReceipt:
    """Bir makine eylemi için hak makbuzu üretir ve zincire ekler.

    `subject_ref` gerçek kimlik değil, takma ad ya da dahili kimliktir; makbuz
    okunabilir kişisel veri taşımaz.
    """
    body = {
        "occurred_at": datetime.now(UTC).isoformat(),
        "domain": str(evaluation.domain),
        "operation": evaluation.operation,
        "decision": str(evaluation.decision),
        "classification": str(evaluation.classification),
        "personal_kind": str(evaluation.personal_kind),
        "concerns_child": evaluation.concerns_child,
        "policy_version": evaluation.policy_version,
        "provider": provider,
        "outcome": outcome,
        "actor_role": actor_role,
        "subject_kind": subject_kind,
        "subject_ref": subject_ref,
        "reasons": evaluation.reasons_en,
    }
    body_hash = payload_hash(body)
    previous = _latest(db)
    previous_hash = previous.chain_hash if previous else GENESIS

    receipt = RightsReceipt(
        domain=str(evaluation.domain),
        operation=evaluation.operation,
        decision=str(evaluation.decision),
        classification=str(evaluation.classification),
        personal_kind=str(evaluation.personal_kind),
        concerns_child=evaluation.concerns_child,
        policy_version=evaluation.policy_version,
        provider=provider,
        outcome=outcome,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        subject_kind=subject_kind,
        subject_ref=subject_ref,
        evidence=body,
        payload_hash=body_hash,
        prev_hash=previous_hash,
        chain_hash=chain_hash(body_hash, previous_hash),
        occurred_at=datetime.now(UTC),
    )
    db.add(receipt)
    if flush:
        db.flush()
    return receipt


# ---------------------------------------------------------------------------
# Doğrulama
# ---------------------------------------------------------------------------
def verify_chain(db: Session, limit: int | None = None) -> dict:
    """Makbuz zincirini baştan sona doğrular.

    Dönüş: {"ok": bool, "checked": n, "broken_at": id|None, "reason": str|None}
    """
    query = select(RightsReceipt).order_by(RightsReceipt.id.asc())
    if limit:
        query = query.limit(limit)
    receipts = list(db.scalars(query))

    previous_hash = GENESIS
    for receipt in receipts:
        recomputed_body = payload_hash(receipt.evidence)
        if recomputed_body != receipt.payload_hash:
            return {
                "ok": False,
                "checked": len(receipts),
                "broken_at": receipt.id,
                "reason": "payload_hash_mismatch",
            }
        if receipt.prev_hash != previous_hash:
            return {
                "ok": False,
                "checked": len(receipts),
                "broken_at": receipt.id,
                "reason": "chain_break",
            }
        expected = chain_hash(receipt.payload_hash, receipt.prev_hash)
        if expected != receipt.chain_hash:
            return {
                "ok": False,
                "checked": len(receipts),
                "broken_at": receipt.id,
                "reason": "chain_hash_mismatch",
            }
        previous_hash = receipt.chain_hash

    return {"ok": True, "checked": len(receipts), "broken_at": None, "reason": None}
