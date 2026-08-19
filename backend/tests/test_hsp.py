"""HSP testleri / Human Sovereignty Protocol tests.

Bu testler "kod çalışıyor mu"dan çok "koruma gerçekten devrede mi" sorusunu
yanıtlar. Her test, ihlal edildiğinde gerçek bir kişisel veri sızıntısı ya da
denetlenemez bir makine kararı anlamına gelen bir değişmezi sabitler.
"""

from __future__ import annotations

import pytest

from app.services.hsp.classification import (
    Classification,
    Handling,
    PersonalDataKind,
    classify_payload,
    involves_child,
    label_for,
    strictest,
)
from app.services.hsp.policy import (
    ActionContext,
    Decision,
    Domain,
    evaluate,
    most_restrictive,
)
from app.services.hsp.providers import evidence_for
from app.services.hsp.redaction import build_name_map, pseudonym, replace_names
from app.services.hsp.scopes import collect_names, fields_for


# ---------------------------------------------------------------------------
# Sınıflandırma
# ---------------------------------------------------------------------------
class TestClassification:
    def test_bilinmeyen_alan_serbest_degil(self):
        """Kayıtta olmayan alan RESTRICTED + UNKNOWN sayılır, PUBLIC değil."""
        label = label_for("student.gizemli_yeni_alan")
        assert label.classification is Classification.RESTRICTED
        assert label.kind is PersonalDataKind.UNKNOWN
        assert label.handling is Handling.REDACT

    def test_saglik_notu_ozel_nitelikli_ve_asla_gonderilmez(self):
        label = label_for("student.health_notes")
        assert label.kind is PersonalDataKind.SENSITIVE
        assert label.handling is Handling.NEVER

    def test_tek_hassas_alan_tum_yuku_kisitlar(self):
        """Bir sağlık notu, yanındaki kamuya açık alanları da yukarı çeker."""
        classification, kind, _ = classify_payload(
            ["pool.name", "lesson.start_time", "student.health_notes"]
        )
        assert classification is Classification.RESTRICTED
        assert kind is PersonalDataKind.SENSITIVE

    def test_bos_yuk_public(self):
        classification, kind, labels = classify_payload([])
        assert classification is Classification.PUBLIC
        assert kind is PersonalDataKind.NON_PERSONAL
        assert labels == []

    def test_strictest_bos_girdide_restricted_doner(self):
        """Fail-safe: bilgi yoksa en kısıtlı sınıf."""
        assert strictest() is Classification.RESTRICTED

    def test_ogrenci_verisi_cocuk_isaretli(self):
        _, _, labels = classify_payload(["student.full_name"])
        assert involves_child(labels) is True

    def test_havuz_adi_cocuk_isaretli_degil(self):
        _, _, labels = classify_payload(["pool.name"])
        assert involves_child(labels) is False


# ---------------------------------------------------------------------------
# Politika motoru
# ---------------------------------------------------------------------------
def _ctx(paths: list[str], provider: str, **kwargs) -> ActionContext:
    evidence = evidence_for(provider)
    return ActionContext(
        domain=kwargs.pop("domain", Domain.KNOW),
        operation=kwargs.pop("operation", "ai.analyze.test"),
        field_paths=paths,
        provider_is_local=evidence.is_local,
        provider_region=evidence.region,
        provider_retains_data=evidence.retains_data,
        provider_trains_on_data=evidence.trains_on_data,
        **kwargs,
    )


class TestPolicyKnow:
    def test_ogrenci_adi_buluta_gitmez(self):
        """En kritik değişmez: çocuk kişisel verisi kanıtsız buluta gönderilemez."""
        result = evaluate(_ctx(["student.full_name"], "nvidia"))
        assert result.decision is Decision.BLOCK
        assert result.allowed is False

    def test_ogrenci_adi_yerelde_islenebilir(self):
        result = evaluate(_ctx(["student.full_name"], "local"))
        assert result.decision is Decision.ALLOW
        assert result.allowed is True

    def test_saglik_notu_yerelde_bile_maskelenir(self):
        result = evaluate(_ctx(["student.health_notes"], "local"))
        assert result.field_handling["student.health_notes"] is Handling.NEVER

    def test_kisisel_olmayan_veri_buluta_gidebilir(self):
        result = evaluate(_ctx(["pool.name", "lesson.start_time"], "nvidia"))
        assert result.decision is Decision.ALLOW

    def test_bilinmeyen_alan_onay_ister(self):
        result = evaluate(_ctx(["student.tanimsiz_alan"], "nvidia"))
        assert result.decision is Decision.REQUIRE_APPROVAL
        assert result.requires_human_review is True

    def test_karar_her_zaman_gerekce_tasir(self):
        for provider in ("local", "nvidia"):
            for paths in (
                ["pool.name"],
                ["student.full_name"],
                ["student.health_notes"],
            ):
                result = evaluate(_ctx(paths, provider))
                assert result.reasons_tr, f"gerekçe yok: {provider} {paths}"
                assert result.reasons_en, f"reason missing: {provider} {paths}"

    def test_kayitli_olmayan_saglayici_en_kisitli_muamele_gorur(self):
        result = evaluate(_ctx(["student.full_name"], "hic-olmayan-saglayici"))
        assert result.decision is Decision.BLOCK


class TestPolicyDecideAndAct:
    def test_hukuki_etkili_otomatik_karar_onay_ister(self):
        result = evaluate(
            _ctx(
                ["student.full_name"],
                "local",
                domain=Domain.DECIDE,
                decision_affects_person=True,
                decision_has_legal_effect=True,
            )
        )
        assert result.decision is Decision.REQUIRE_APPROVAL

    def test_insan_onayi_verilmisse_karar_gecer(self):
        result = evaluate(
            _ctx(
                ["student.full_name"],
                "local",
                domain=Domain.DECIDE,
                decision_affects_person=True,
                decision_has_legal_effect=True,
                human_approved=True,
            )
        )
        assert result.decision is Decision.ALLOW

    def test_geri_alinamaz_eylem_onay_ister(self):
        result = evaluate(
            _ctx(["pool.name"], "local", domain=Domain.ACT, action_is_reversible=False)
        )
        assert result.decision is Decision.REQUIRE_APPROVAL

    def test_geri_alinabilir_eylem_serbest(self):
        result = evaluate(
            _ctx(["pool.name"], "local", domain=Domain.ACT, action_is_reversible=True)
        )
        assert result.decision is Decision.ALLOW


class TestFailSafe:
    def test_bos_karar_kumesi_block_verir(self):
        """Karar üretilemezse sonuç BLOCK olmalı — sessiz fail-open yok."""
        assert most_restrictive() is Decision.BLOCK

    def test_degerlendirme_cokerse_block_doner(self, monkeypatch):
        """Politika motoru hata verirse eylem yapılmaz."""
        import app.services.hsp.policy as policy_module

        def patlat(*args, **kwargs):
            raise RuntimeError("beklenmedik hata")

        monkeypatch.setattr(policy_module, "classify_payload", patlat)
        result = evaluate(_ctx(["student.full_name"], "local"))
        assert result.decision is Decision.BLOCK
        assert result.requires_human_review is True
        assert result.reasons_tr

    def test_kisitlilik_sirasi_dogru(self):
        assert most_restrictive(Decision.ALLOW, Decision.BLOCK) is Decision.BLOCK
        assert (
            most_restrictive(Decision.ALLOW, Decision.PSEUDONYMIZE)
            is Decision.PSEUDONYMIZE
        )
        assert (
            most_restrictive(Decision.REDACT, Decision.LOCAL_ONLY)
            is Decision.LOCAL_ONLY
        )


# ---------------------------------------------------------------------------
# Takma adlaştırma
# ---------------------------------------------------------------------------
class TestPseudonymisation:
    def test_takma_ad_kararli(self):
        assert pseudonym("Ayşe Yılmaz") == pseudonym("Ayşe Yılmaz")

    def test_farkli_kisiler_farkli_takma_ad(self):
        assert pseudonym("Ayşe Yılmaz") != pseudonym("Mehmet Demir")

    def test_takma_ad_gercek_adi_icermez(self):
        alias = pseudonym("Ayşe Yılmaz")
        assert "Ayşe" not in alias
        assert "Yılmaz" not in alias

    def test_buyuk_kucuk_harf_ayni_takma_adi_verir(self):
        assert pseudonym("ayşe yılmaz") == pseudonym("AYŞE YILMAZ")

    def test_metindeki_ad_degistirilir(self):
        names = build_name_map(["Ayşe Yılmaz"], "student")
        text = "Ayşe Yılmaz'ın derecesi geriliyor."
        replaced = replace_names(text, names)
        assert "Ayşe Yılmaz" not in replaced
        assert names["Ayşe Yılmaz"] in replaced

    def test_uzun_ad_once_degistirilir(self):
        """'Ali' ve 'Ali Veli' birlikteyken kısmi eşleşme bozuk çıktı vermemeli."""
        names = build_name_map(["Ali", "Ali Veli"], "student")
        replaced = replace_names("Ali Veli geldi", names)
        assert names["Ali Veli"] in replaced

    def test_geri_esleme_orijinali_dondurur(self):
        names = build_name_map(["Ayşe Yılmaz"], "student")
        reverse = {alias: real for real, alias in names.items()}
        text = replace_names("Ayşe Yılmaz gelişiyor.", names)
        assert replace_names(text, reverse) == "Ayşe Yılmaz gelişiyor."


# ---------------------------------------------------------------------------
# Kapsam haritası
# ---------------------------------------------------------------------------
class TestScopes:
    def test_tum_kapsamlar_tanimli(self):
        from app.services.ai.analysis import SCOPE_COLLECTORS
        from app.services.hsp.scopes import SCOPE_FIELDS

        eksik = set(SCOPE_COLLECTORS) - set(SCOPE_FIELDS)
        assert not eksik, f"HSP alan haritasinda eksik kapsam: {eksik}"

    def test_tanimsiz_kapsam_general_gibi_ele_alinir(self):
        assert fields_for("hic-boyle-bir-kapsam-yok") == fields_for("general")

    def test_ic_ice_yapidan_adlar_toplanir(self):
        metrics = {
            "overdue_invoices": [
                {"student": "Ayşe Yılmaz", "balance": 500},
                {"student": "Mehmet Demir", "balance": 300},
            ],
            "top": {"instructor": "Zeynep Kaya"},
            "count": 2,
        }
        names = collect_names(metrics)
        assert names == {
            "Ayşe Yılmaz": "student",
            "Mehmet Demir": "student",
            "Zeynep Kaya": "instructor",
        }

    def test_ad_olmayan_yapidan_bos_doner(self):
        assert collect_names({"count": 5, "rate": 0.9}) == {}


# ---------------------------------------------------------------------------
# Sağlayıcı kanıtı
# ---------------------------------------------------------------------------
class TestProviderEvidence:
    def test_bulut_saglayici_kaniti_eksik_kabul_edilir(self):
        """Kanıt uydurulmaz: doğrulanana kadar eksiktir."""
        assert evidence_for("nvidia").evidence_complete is False

    def test_yerel_saglayici_kaniti_tam(self):
        assert evidence_for("local").evidence_complete is True

    def test_bilinmeyen_saglayici_en_dusuk_siniri_alir(self):
        evidence = evidence_for("bilinmeyen")
        assert evidence.max_classification is Classification.PUBLIC
        assert evidence.is_local is False

    def test_kanit_gorunumu_sir_icermez(self):
        for name in ("local", "nvidia", "openai_compat"):
            view = evidence_for(name).public_view()
            metin = str(view).lower()
            assert "api_key" not in metin
            assert "nvapi-" not in metin


# ---------------------------------------------------------------------------
# Makbuz zinciri (veritabanı gerektirir)
# ---------------------------------------------------------------------------
class TestReceiptChain:
    def test_zincir_dogrulanir(self, db):
        from app.services.hsp import receipts

        for index in range(5):
            receipts.issue(
                db,
                evaluate(_ctx(["student.full_name"], "local")),
                provider="local",
                subject_ref=str(index),
            )
        db.flush()
        assert receipts.verify_chain(db)["ok"] is True

    def test_kurcalama_tespit_edilir(self, db):
        """Bir makbuzun içeriği değiştirilirse zincir doğrulaması bozulmalı."""
        from app.services.hsp import receipts

        first = receipts.issue(
            db, evaluate(_ctx(["student.full_name"], "local")), provider="local"
        )
        receipts.issue(db, evaluate(_ctx(["pool.name"], "local")), provider="local")
        db.flush()
        assert receipts.verify_chain(db)["ok"] is True

        # Kanıtı sessizce değiştir
        tampered = dict(first.evidence)
        tampered["decision"] = "allow"
        tampered["operation"] = "degistirildi"
        first.evidence = tampered
        db.flush()

        report = receipts.verify_chain(db)
        assert report["ok"] is False
        assert report["broken_at"] == first.id
        assert report["reason"] == "payload_hash_mismatch"

    def test_makbuz_ham_kisisel_veri_tasimaz(self, db):
        from app.services.hsp import receipts

        receipt = receipts.issue(
            db,
            evaluate(_ctx(["student.full_name", "student.health_notes"], "local")),
            provider="local",
            subject_kind="student",
            subject_ref="42",
        )
        db.flush()
        metin = str(receipt.evidence)
        # Kanıt yalnızca kategori ve karar taşır; ad/not içermez
        assert "health_notes" not in metin or "sensitive" in metin
        assert receipt.chain_hash and len(receipt.chain_hash) == 64
        assert receipt.payload_hash != receipt.chain_hash

    def test_bos_zincir_gecerlidir(self, db):
        from app.services.hsp import receipts

        assert receipts.verify_chain(db) == {
            "ok": True,
            "checked": 0,
            "broken_at": None,
            "reason": None,
        }


# ---------------------------------------------------------------------------
# Rıza / aydınlatma ayrımı
# ---------------------------------------------------------------------------
class TestConsentSeparation:
    def test_aydinlatma_ve_riza_ayri_tablolardir(self):
        from app.models.hsp import ConsentRecord, NoticeVersion

        notice_columns = set(NoticeVersion.__table__.columns.keys())
        # Aydınlatma bir bilgilendirmedir; onay alanı taşımamalıdır.
        assert "granted" not in notice_columns
        assert "consent" not in notice_columns

        consent_columns = set(ConsentRecord.__table__.columns.keys())
        assert "granted" in consent_columns
        assert "purpose" in consent_columns
        # Rıza hangi aydınlatma metniyle alındığını göstermelidir
        assert "notice_version_id" in consent_columns

    def test_riza_amaca_ozeldir(self):
        """Tek satır tüm amaçları kapsayamaz; amaç zorunlu alandır."""
        from app.models.hsp import ConsentRecord

        assert ConsentRecord.__table__.columns["purpose"].nullable is False

    def test_geri_alma_ayri_kayittir(self):
        from app.models.hsp import ConsentWithdrawal

        columns = set(ConsentWithdrawal.__table__.columns.keys())
        assert {"consent_id", "withdrawn_at", "propagated"} <= columns


@pytest.mark.parametrize(
    "scope",
    ["student_performance", "declining_students", "payment_risk", "attendance"],
)
def test_kisi_iceren_kapsamlar_bulutta_engellenir(scope):
    """Kişi verisi taşıyan hiçbir analiz kapsamı kanıtsız buluta gitmez."""
    result = evaluate(_ctx(fields_for(scope), "nvidia"))
    assert result.decision is Decision.BLOCK, scope


# ---------------------------------------------------------------------------
# Geçit — uçtan uca
# ---------------------------------------------------------------------------
class _SahteSaglayici:
    enabled = True


def _sahte_router(kayit: dict, yanit: str | None = None):
    """Sağlayıcıya giden yükü yakalayan sahte yönlendirici üretir."""
    from app.services.ai.base import ChatResult

    class SahteRouter:
        def __init__(self, db=None):
            self.db = db

        def resolve_chain(self, preferred: str = "auto") -> list[str]:
            return ["local"]

        def chat(self, messages, **kwargs):
            kayit["messages"] = messages
            # Yanıt verilmemişse modelin gördüğü metni aynen geri yolla:
            # böylece geri eşlemenin doğruluğu sınanabilir.
            icerik = yanit if yanit is not None else messages[-1].content
            return (
                ChatResult(
                    content=icerik, provider="local", model="test", duration_ms=1
                ),
                ["local"],
                False,
            )

    return SahteRouter


class TestGateway:
    def test_gercek_ad_saglayiciya_ulasmaz(self, db, monkeypatch):
        """En kritik uçtan uca değişmez: gerçek ad modele gitmez."""
        from app.services.ai.base import ChatMessage
        from app.services.hsp import gateway

        kayit: dict = {}
        monkeypatch.setattr(gateway, "AIRouter", _sahte_router(kayit))
        monkeypatch.setattr(gateway, "get_provider", lambda name: _SahteSaglayici())

        sonuc = gateway.chat(
            db,
            [ChatMessage(role="user", content="Kerem Şahin gecikmiş ödeme taşıyor.")],
            operation="ai.analyze.payment_risk",
            field_paths=["student.full_name", "invoice.balance"],
            subject_names={"Kerem Şahin": "student"},
            preferred="local",
        )

        gonderilen = kayit["messages"][-1].content
        assert "Kerem Şahin" not in gonderilen
        assert "Öğrenci-" in gonderilen
        assert sonuc.pseudonymised == 1

    def test_yanittaki_takma_ad_geri_eslenir(self, db, monkeypatch):
        """Kullanıcı gerçek adı görür; model hiç görmemiştir."""
        from app.services.ai.base import ChatMessage
        from app.services.hsp import gateway

        kayit: dict = {}
        monkeypatch.setattr(gateway, "AIRouter", _sahte_router(kayit))
        monkeypatch.setattr(gateway, "get_provider", lambda name: _SahteSaglayici())

        özgün = "Kerem Şahin gecikmiş ödeme taşıyor."
        sonuc = gateway.chat(
            db,
            [ChatMessage(role="user", content=özgün)],
            operation="ai.analyze.payment_risk",
            field_paths=["student.full_name"],
            subject_names={"Kerem Şahin": "student"},
            preferred="local",
        )

        assert sonuc.result is not None
        # Sahte sağlayıcı gördüğü metni aynen geri yolladı; geri eşleme
        # doğruysa kullanıcıya özgün metin döner.
        assert sonuc.result.content == özgün

    def test_engellenen_cagri_saglayiciya_ulasmaz(self, db, monkeypatch):
        """BLOCK kararında hiçbir istek gönderilmez."""
        from app.services.ai.base import ChatMessage
        from app.services.hsp import gateway

        kayit: dict = {}
        router = _sahte_router(kayit)

        class BulutRouter(router):  # type: ignore[valid-type,misc]
            def resolve_chain(self, preferred: str = "auto") -> list[str]:
                return ["nvidia"]

        monkeypatch.setattr(gateway, "AIRouter", BulutRouter)
        monkeypatch.setattr(gateway, "get_provider", lambda name: _SahteSaglayici())

        sonuc = gateway.chat(
            db,
            [ChatMessage(role="user", content="Kerem Şahin ...")],
            operation="ai.analyze.payment_risk",
            field_paths=["student.full_name"],
            subject_names={"Kerem Şahin": "student"},
            preferred="auto",
        )

        assert sonuc.blocked is True
        assert "messages" not in kayit, "engellenmiş çağrı sağlayıcıya ulaştı"
        assert sonuc.receipt_id is not None, "engelleme de makbuz üretmeli"

    def test_engelleme_gerekce_metni_uretir(self, db, monkeypatch):
        from app.services.ai.base import ChatMessage
        from app.services.hsp import gateway

        kayit: dict = {}
        router = _sahte_router(kayit)

        class BulutRouter(router):  # type: ignore[valid-type,misc]
            def resolve_chain(self, preferred: str = "auto") -> list[str]:
                return ["nvidia"]

        monkeypatch.setattr(gateway, "AIRouter", BulutRouter)
        monkeypatch.setattr(gateway, "get_provider", lambda name: _SahteSaglayici())

        sonuc = gateway.chat(
            db,
            [ChatMessage(role="user", content="test")],
            operation="ai.analyze.payment_risk",
            field_paths=["student.full_name"],
            preferred="auto",
        )
        mesaj = sonuc.refusal_message("tr")
        assert "gönderilmedi" in mesaj
        assert len(mesaj) > 40, "gerekçesiz ret mesajı"
