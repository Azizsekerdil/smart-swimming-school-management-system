"""HSP modelleri / Human Sovereignty Protocol models.

Üç grup tablo:

1. `RightsReceipt` — makinenin bir insan hakkında yaptığı her KNOW/DECIDE/ACT
   eyleminin hash zincirli kanıtı.
2. `NoticeVersion` / `ConsentRecord` / `ConsentWithdrawal` — aydınlatma metni
   ile açık rızanın **ayrı** yönetimi.
3. `ProviderEvidenceRecord` — sağlayıcı kanıtının kurum tarafından doğrulanmış
   hâli; kod içindeki varsayılanı ezer.

Neden ayrı aydınlatma ve rıza tabloları? Mevcut `Student.consent_given`
boolean'ı ikisini tek kutuya sıkıştırıyordu. KVKK, aydınlatma yükümlülüğü ile
açık rızanın ayrı metin, ayrı eylem ve ayrı kanıt olmasını arar; birleşik tek
onay kutusu bu ayrımı ortadan kaldırır. Eski alan silinmez, veri kaybı
olmaması için korunur ve göç sırasında yeni tablolara taşınır.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IntPKMixin, TimestampMixin


class RightsReceipt(Base, IntPKMixin):
    """Makine eyleminin kurcalamaya dayanıklı kanıtı.

    Kayıtlar yalnızca eklenir (append-only); güncelleme ve silme uygulama
    katmanında yapılmaz. Zincir bozulursa `verify_chain` bunu tespit eder.
    """

    __tablename__ = "hsp_rights_receipts"
    __table_args__ = (
        Index("ix_hsp_receipt_subject", "subject_kind", "subject_ref"),
        Index("ix_hsp_receipt_time", "occurred_at"),
        Index("ix_hsp_receipt_decision", "decision"),
    )

    domain: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    personal_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    concerns_child: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)

    provider: Mapped[str | None] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(
        String(24), default="completed", nullable=False
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_role: Mapped[str | None] = mapped_column(String(40))

    # Veri sahibi: gerçek kimlik değil, takma ad veya dahili referans
    subject_kind: Mapped[str | None] = mapped_column(String(20))
    subject_ref: Mapped[str | None] = mapped_column(String(64))

    # Gerekçe ve bağlam — ham kişisel veri içermez
    evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    chain_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class NoticeVersion(Base, IntPKMixin, TimestampMixin):
    """Aydınlatma metninin sürümlenmiş hâli.

    Aydınlatma bir **bilgilendirmedir**, onay değildir. Bu tabloda rıza alanı
    bilinçli olarak yoktur.
    """

    __tablename__ = "hsp_notice_versions"
    __table_args__ = (Index("ix_hsp_notice_active", "code", "is_active"),)

    # "student_enrolment", "photo_usage", "ai_analysis" gibi
    code: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="tr", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Metnin değişmediğini kanıtlamak için
    body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ConsentRecord(Base, IntPKMixin, TimestampMixin):
    """Açık rıza kaydı — aydınlatmadan ayrı, amaca özel ve geri alınabilir.

    Her satır **tek bir amaç** için rızadır. "Hepsini kabul et" tek kaydı
    üretmez; her amaç ayrı satırdır (§10.1).
    """

    __tablename__ = "hsp_consent_records"
    __table_args__ = (
        Index("ix_hsp_consent_subject", "subject_kind", "subject_id"),
        Index("ix_hsp_consent_purpose", "purpose", "is_active"),
    )

    subject_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # "photo_usage", "marketing_email", "ai_progress_analysis" gibi
    purpose: Mapped[str] = mapped_column(String(60), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Hangi aydınlatma metni gösterilerek alındı
    notice_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("hsp_notice_versions.id", ondelete="SET NULL")
    )
    # Rızanın alındığı kanal: web / kagit / resepsiyon
    channel: Mapped[str] = mapped_column(String(30), default="web", nullable=False)
    language: Mapped[str] = mapped_column(String(5), default="tr", nullable=False)

    # Çocuk adına veli rızası veriyorsa
    given_by_guardian_id: Mapped[int | None] = mapped_column(
        ForeignKey("guardians.id", ondelete="SET NULL")
    )
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    evidence_hash: Mapped[str | None] = mapped_column(String(64))
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # Geri alınana kadar aktif
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ConsentWithdrawal(Base, IntPKMixin):
    """Rızanın geri alınması.

    Geri alma kaydı silinmez; rıza satırı pasifleşir ve burada iz kalır.
    Böylece "ne zaman verildi, ne zaman geri alındı" sorusu yanıtlanabilir.
    """

    __tablename__ = "hsp_consent_withdrawals"

    consent_id: Mapped[int] = mapped_column(
        ForeignKey("hsp_consent_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(String(300))
    requested_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    # Aşağı akış sistemlerine yayılım tamamlandı mı
    propagated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    propagation_notes: Mapped[str | None] = mapped_column(Text)
    withdrawn_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class ProviderEvidenceRecord(Base, IntPKMixin, TimestampMixin):
    """Kurumun doğruladığı sağlayıcı kanıtı.

    Koddaki varsayılan kanıt bilinçli olarak eksiktir. Kurum DPA'yı imzalayıp
    bölgeyi doğruladığında bu tabloya kayıt girer ve politika motoru bunu
    kullanır. Kayıt yoksa varsayılan (kısıtlı) geçerlidir.
    """

    __tablename__ = "hsp_provider_evidence"

    provider: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    region: Mapped[str | None] = mapped_column(String(60))
    retains_data: Mapped[bool | None] = mapped_column(Boolean)
    trains_on_data: Mapped[bool | None] = mapped_column(Boolean)
    role: Mapped[str] = mapped_column(String(30), default="unknown", nullable=False)
    dpa_evidence: Mapped[str | None] = mapped_column(String(200))
    transfer_mechanism: Mapped[str | None] = mapped_column(String(60))
    max_classification: Mapped[str] = mapped_column(
        String(20), default="internal", nullable=False
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
