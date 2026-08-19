"""AI sağlayıcı kanıt kaydı / AI provider evidence registry.

Mevcut `app.services.ai.providers` modülü sağlayıcının **nasıl çağrılacağını**
bilir. Bu modül ayrı bir soruyu yanıtlar: sağlayıcıya veri göndermek
**hukuken savunulabilir mi?**

Bu ayrım bilinçlidir. Bir sağlayıcının çalışıyor olması, ona kişisel veri
gönderilebileceği anlamına gelmez.

Kanıt eksikse alan `None` bırakılır ve politika motoru bunu lehte değil,
aleyhte yorumlar: "eğitimde kullanılmıyor" iddiası kanıtlanana kadar
doğrulanmamış sayılır (§12).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.hsp.classification import Classification


@dataclass(frozen=True)
class ProviderEvidence:
    """Bir AI sağlayıcısının veri koruma kanıtı."""

    name: str
    display_name: str
    is_local: bool
    # İşlemenin gerçekleştiği bölge. Yerel sağlayıcıda kurumun kendi konumu.
    region: str | None
    # Sağlayıcı verileri saklıyor mu? None = kanıt yok.
    retains_data: bool | None
    # Sağlayıcı verileri model eğitiminde kullanıyor mu? None = kanıt yok.
    trains_on_data: bool | None
    # KVKK/GDPR rolü: controller / processor / unknown
    role: str
    # Veri işleme sözleşmesi (DPA) kanıtı var mı
    dpa_evidence: str | None
    # Yurt dışı aktarım mekanizması: adequacy / SCC / standart sözleşme / none
    transfer_mechanism: str | None
    # Bu sağlayıcıya gönderilebilecek en yüksek gizlilik sınıfı
    max_classification: Classification
    # Kanıtın en son ne zaman doğrulandığı (ISO tarih) — None = hiç
    evidence_reviewed_on: str | None
    notes_tr: str
    notes_en: str

    @property
    def evidence_complete(self) -> bool:
        """Kişisel veri göndermeye yetecek kanıt var mı?"""
        if self.is_local:
            return True
        return (
            self.region is not None
            and self.retains_data is not None
            and self.trains_on_data is not None
            and self.dpa_evidence is not None
            and self.transfer_mechanism is not None
        )

    def public_view(self) -> dict:
        """Arayüzde gösterilecek özet. Sır içermez."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "is_local": self.is_local,
            "region": self.region or "UNKNOWN",
            "retains_data": self.retains_data,
            "trains_on_data": self.trains_on_data,
            "role": self.role,
            "dpa_evidence": self.dpa_evidence or "MISSING",
            "transfer_mechanism": self.transfer_mechanism or "NONE",
            "max_classification": str(self.max_classification),
            "evidence_complete": self.evidence_complete,
            "evidence_reviewed_on": self.evidence_reviewed_on,
            "notes_tr": self.notes_tr,
            "notes_en": self.notes_en,
        }


# ---------------------------------------------------------------------------
# Kayıt defteri
# ---------------------------------------------------------------------------
# Not: Bulut sağlayıcıların kanıt alanları bilinçli olarak `None` bırakılmıştır.
# Kurum kendi DPA'sını imzalayıp bölgeyi doğruladığında bu değerler
# yapılandırmadan doldurulmalıdır. Kanıtı burada varsaymak, §35'teki
# "provider şartı uydurma" yasağını ihlal ederdi.

_PROVIDERS: tuple[ProviderEvidence, ...] = (
    ProviderEvidence(
        name="local",
        display_name="LM Studio (Yerel)",
        is_local=True,
        region="on-premise",
        retains_data=False,
        trains_on_data=False,
        role="processor-none",
        dpa_evidence="not-required-local",
        transfer_mechanism="no-transfer",
        max_classification=Classification.CONFIDENTIAL,
        evidence_reviewed_on=None,
        notes_tr=(
            "Model kurum içinde çalışır; veri ağdan çıkmaz. Yurt dışı aktarım "
            "söz konusu değildir. Özel nitelikli veri yine de prompt'a konmaz."
        ),
        notes_en=(
            "The model runs on-premise; data does not leave the network. No "
            "cross-border transfer occurs. Special category data is still kept "
            "out of prompts."
        ),
    ),
    ProviderEvidence(
        name="nvidia",
        display_name="NVIDIA Build (Bulut)",
        is_local=False,
        region=None,
        retains_data=None,
        trains_on_data=None,
        role="unknown",
        dpa_evidence=None,
        transfer_mechanism=None,
        max_classification=Classification.INTERNAL,
        evidence_reviewed_on=None,
        notes_tr=(
            "Kanıt tamamlanmamıştır. Bölge, saklama, eğitimde kullanım, DPA ve "
            "aktarım mekanizması kurum tarafından doğrulanıp kaydedilene kadar "
            "kişisel veri gönderilmez."
        ),
        notes_en=(
            "Evidence is incomplete. No personal data is sent until the region, "
            "retention, training use, DPA and transfer mechanism are verified and "
            "recorded by the organisation."
        ),
    ),
    ProviderEvidence(
        name="openai_compat",
        display_name="OpenAI Uyumlu Sağlayıcı",
        is_local=False,
        region=None,
        retains_data=None,
        trains_on_data=None,
        role="unknown",
        dpa_evidence=None,
        transfer_mechanism=None,
        max_classification=Classification.INTERNAL,
        evidence_reviewed_on=None,
        notes_tr=(
            "Uç nokta kuruma göre değişir. Kendi sunucunuzsa kanıtı siz "
            "doldurmalısınız; üçüncü taraf ise sözleşme kanıtı gerekir."
        ),
        notes_en=(
            "The endpoint varies by deployment. If it is your own server you must "
            "supply the evidence; if it is a third party, contractual evidence is "
            "required."
        ),
    ),
)

PROVIDER_EVIDENCE: dict[str, ProviderEvidence] = {
    item.name: item for item in _PROVIDERS
}


UNKNOWN_PROVIDER = ProviderEvidence(
    name="unknown",
    display_name="Bilinmeyen sağlayıcı",
    is_local=False,
    region=None,
    retains_data=None,
    trains_on_data=None,
    role="unknown",
    dpa_evidence=None,
    transfer_mechanism=None,
    max_classification=Classification.PUBLIC,
    evidence_reviewed_on=None,
    notes_tr="Kayıtlı olmayan sağlayıcı; yalnızca kişisel olmayan veri gönderilebilir.",
    notes_en="Unregistered provider; only non-personal data may be sent.",
)


def evidence_for(provider_name: str | None) -> ProviderEvidence:
    """Sağlayıcı kanıtını getirir. Kayıtlı değilse en kısıtlı varsayılan döner."""
    if not provider_name:
        return UNKNOWN_PROVIDER
    return PROVIDER_EVIDENCE.get(provider_name, UNKNOWN_PROVIDER)


def registry_view() -> list[dict]:
    """Tüm sağlayıcıların kanıt özeti — AI Kontrol Merkezi ekranı için."""
    return [item.public_view() for item in _PROVIDERS]
