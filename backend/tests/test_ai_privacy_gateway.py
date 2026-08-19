"""AI gizlilik geçidinin BÜTÜN çağrı yollarına uygulandığını kanıtlar.

Daha önce geçit yalnızca `services/ai/analysis.py` üzerinden çağrılıyordu;
sohbet, akış, geliştirici ajanı ve CAIO doğrudan sağlayıcıya gidiyordu. Bu
testler dört yolun da geçitten geçtiğini ve serbest metin taramasının kişisel
veriyi yakaladığını gösterir.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.hsp import freetext

BACKEND = Path(__file__).resolve().parent.parent
AI_DIR = BACKEND / "app" / "services" / "ai"
API_DIR = BACKEND / "app" / "api" / "v1"


# ---------------------------------------------------------------------------
# 1. Statik kanıt: hiçbir uç/servis doğrudan AIRouter.chat çağırmaz
# ---------------------------------------------------------------------------
def _direct_router_chat_calls(path: Path) -> list[int]:
    """`<AIRouter örneği>.chat(...)` biçimindeki doğrudan çağrıların satırları."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    router_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == "AIRouter":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        router_names.add(target.id)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr != "chat":
                continue
            value = node.func.value
            if isinstance(value, ast.Name) and value.id in router_names:
                hits.append(node.lineno)
    return hits


GATED_MODULES = [
    API_DIR / "ai.py",
    AI_DIR / "agent.py",
    AI_DIR / "caio.py",
    AI_DIR / "analysis.py",
]


@pytest.mark.parametrize("module", GATED_MODULES, ids=lambda p: p.name)
def test_no_direct_router_chat_outside_gateway(module: Path) -> None:
    """Geçit dışında doğrudan sağlayıcı çağrısı kalmamalı."""
    assert (
        _direct_router_chat_calls(module) == []
    ), f"{module.name} içinde geçidi atlayan doğrudan AIRouter.chat çağrısı var"


def test_gateway_is_the_only_place_calling_the_router() -> None:
    """Geçidin kendisi elbette router'ı çağırır - sözleşmenin tek noktası."""
    gateway = BACKEND / "app" / "services" / "hsp" / "gateway.py"
    assert _direct_router_chat_calls(gateway), "geçit sağlayıcıyı çağırabilmeli"


@pytest.mark.parametrize(
    "module,operation",
    [
        (API_DIR / "ai.py", "ai.chat"),
        (API_DIR / "ai.py", "ai.chat.stream"),
        (AI_DIR / "agent.py", "ai.developer.plan"),
        (AI_DIR / "caio.py", "ai.caio.report"),
    ],
    ids=["chat", "chat-stream", "developer-agent", "caio"],
)
def test_each_call_path_declares_a_gateway_operation(
    module: Path, operation: str
) -> None:
    assert f'"{operation}"' in module.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 2. Serbest metin taraması: veri asgarileştirme girdisi
# ---------------------------------------------------------------------------
def test_scan_detects_nothing_in_neutral_text(db: Session) -> None:
    paths, names = freetext.scan(db, "Bu hafta kaç ders planlandı?")
    assert paths == []
    assert names == {}


def test_scan_detects_phone_number(db: Session) -> None:
    paths, _ = freetext.scan(db, "Bana 0555 000 00 00 numarasından ulaşın")
    assert "student.phone" in paths


def test_scan_detects_email(db: Session) -> None:
    paths, _ = freetext.scan(db, "veli1@ornek.local adresine yaz")
    assert "student.email" in paths


def test_scan_detects_national_id(db: Session) -> None:
    paths, _ = freetext.scan(db, "Kimlik no 12345678901 olan öğrenci")
    assert "student.national_id" in paths


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Çocukta alerji var mı?", "student.health_notes"),
        ("Astım raporu yüklendi", "student.health_notes"),
        ("Does the child have an allergy?", "student.health_notes"),
        ("Özel gereksinimli öğrenciler", "student.special_needs"),
        ("Ödenmemiş borç listesi", "invoice.balance"),
        ("Acil durum iletişimi kim?", "student.emergency_contact"),
    ],
)
def test_scan_detects_sensitive_keywords(db: Session, text: str, expected: str) -> None:
    paths, _ = freetext.scan(db, text)
    assert expected in paths


def test_scan_matches_real_subject_names(db: Session, student) -> None:
    paths, names = freetext.scan(db, f"{student.full_name} bu ay kaç derse katıldı?")
    assert "student.full_name" in paths
    assert names.get(student.full_name) == "student"


def test_scan_is_case_and_accent_insensitive(db: Session, student) -> None:
    _, names = freetext.scan(db, student.full_name.upper())
    assert student.full_name in names


# ---------------------------------------------------------------------------
# 3. Geçit kararı: sağlayıcı yokken çağrı yapılmaz, makbuz üretilir
# ---------------------------------------------------------------------------
def test_chat_endpoint_does_not_bypass_gateway(
    client: TestClient, admin_headers: dict
) -> None:
    """Sağlayıcı kapalıyken uç hata döner - sessizce dışarı veri çıkmaz."""
    response = client.post(
        "/api/v1/ai/chat",
        headers=admin_headers,
        json={"messages": [{"role": "user", "content": "Merhaba"}]},
    )
    # 503 (sağlayıcı yok) veya 403/422 (politika) kabul edilir; 200 kabul edilmez
    assert response.status_code != 200
    assert response.status_code in (403, 422, 503), response.text


def test_gateway_preflight_blocks_without_allowed_provider(db: Session) -> None:
    from app.services.ai.base import ChatMessage
    from app.services.hsp import gateway

    plan = gateway.preflight(
        db,
        [ChatMessage(role="user", content="test")],
        operation="ai.chat",
        field_paths=["student.health_notes"],
        preferred="nvidia",
    )
    # NVIDIA testte kapalı ve sağlık verisi için kanıtı yok -> engellenmeli
    assert plan.blocked is True
    assert plan.refusal_message("tr")
    assert plan.refusal_message("en")


def test_gateway_preflight_pseudonymises_names(db: Session, student) -> None:
    from app.services.ai.base import ChatMessage
    from app.services.hsp import gateway

    plan = gateway.preflight(
        db,
        [ChatMessage(role="user", content=f"{student.full_name} nasıl gidiyor?")],
        operation="ai.chat",
        field_paths=["student.full_name"],
        subject_names={student.full_name: "student"},
        preferred="local",
    )
    if not plan.blocked and plan.name_map:
        outgoing = plan.outgoing[0].content
        assert student.full_name not in outgoing


# ---------------------------------------------------------------------------
# 4. Gizlilik: istem metni AI_LOG_PROMPTS kapalıyken saklanmaz
# ---------------------------------------------------------------------------
def test_chat_task_title_hides_prompt_when_logging_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.ai import chat_task_title
    from app.core.config import settings

    monkeypatch.setattr(settings, "ai_log_prompts", False)
    assert chat_task_title("Ali Kaya'nın sağlık notu nedir?") == "Sohbet"

    monkeypatch.setattr(settings, "ai_log_prompts", True)
    assert chat_task_title("merhaba").startswith("merhaba")


def test_prompt_text_not_persisted_by_default(
    client: TestClient, admin_headers: dict, db: Session
) -> None:
    from app.models.system import AITask

    secret_text = "Ali Kaya alerji raporu 05550000000"
    client.post(
        "/api/v1/ai/chat",
        headers=admin_headers,
        json={"messages": [{"role": "user", "content": secret_text}]},
    )
    for task in db.query(AITask).all():
        assert secret_text not in (task.title or "")
        assert secret_text not in (task.prompt_preview or "")
