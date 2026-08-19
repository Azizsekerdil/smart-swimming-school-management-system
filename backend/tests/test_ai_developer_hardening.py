"""AI geliştirici konsolu ve AI ayar ucu sertleştirmelerinin regresyon testleri.

* `python -c` beyaz listeden çıkarıldı (dinamik kod çalıştırma = kum havuzu kaçışı)
* `patch_id` / `checkpoint_id` doğrulanıyor (dizin dışına çıkma)
* `PUT /ai/config` değerleri `.env` dosyasına satır enjekte edemiyor
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ValidationError
from app.schemas.ai import AIConfigUpdate
from app.services.ai import agent
from app.services.ai.policy import policy


@pytest.fixture
def shell_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kabuk erişimi varsayılan olarak KAPALIDIR; testte açıkça açılır."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "ai_developer_allow_shell", True)


# ---------------------------------------------------------------------------
# 1. Dinamik kod çalıştırma engellendi
# ---------------------------------------------------------------------------
def test_python_dash_c_is_not_allowlisted() -> None:
    from app.services.ai.policy import ALLOWED_SUBCOMMANDS

    assert "-c" not in ALLOWED_SUBCOMMANDS["python"]


@pytest.mark.parametrize(
    "command",
    [
        'python -c "import os"',
        "python -c print(1)",
        "python  -X utf8 -c import socket",
        "py -c import shutil",
        "python3 -c open('.env').read()",
    ],
)
def test_dynamic_code_execution_is_blocked(
    command: str, shell_enabled: None  # noqa: ARG001
) -> None:
    """Kabuk açıkken bile `-c` reddedilir (asıl güvenlik iddiası budur)."""
    decision = policy.check_command(command)
    assert decision.allowed is False, command


def test_dynamic_code_execution_blocked_with_shell_disabled() -> None:
    assert policy.check_command('python -c "import os"').allowed is False


def test_legitimate_python_module_run_still_allowed(
    shell_enabled: None,  # noqa: ARG001
) -> None:
    assert policy.check_command("python -m pytest").allowed is True


def test_pytest_still_allowed(shell_enabled: None) -> None:  # noqa: ARG001
    assert policy.check_command("pytest backend/tests").allowed is True


# ---------------------------------------------------------------------------
# 2. Kimlik doğrulaması (path traversal)
# ---------------------------------------------------------------------------
BAD_IDS = [
    "../../../etc/passwd",
    "..\\..\\.env",
    "/absolute/path",
    "C:/Windows/win.ini",
    "patch_20260101_000000_abcdef/../../secret",
    "",
    "patch_x",
    "ckpt_x",
    "patch_20260101_000000_ABCDEF",  # büyük harf: üretilen biçim değil
]


@pytest.mark.parametrize("bad", BAD_IDS)
def test_get_patch_rejects_invalid_id(bad: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        agent.get_patch(bad)
    assert excinfo.value.details["reason"] == "invalid_patch_id"


@pytest.mark.parametrize("bad", BAD_IDS)
def test_rollback_rejects_invalid_checkpoint_id(bad: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        agent.rollback_checkpoint(bad)
    assert excinfo.value.details["reason"] == "invalid_checkpoint_id"


def test_valid_id_shape_passes_validation_then_reports_not_found() -> None:
    """Doğru biçimli ama var olmayan kimlik: 'bulunamadı' (dosya sistemi yok)."""
    with pytest.raises(ValidationError) as excinfo:
        agent.get_patch("patch_20260101_000000_abcdef")
    assert excinfo.value.details["reason"] == "patch_not_found"


# ---------------------------------------------------------------------------
# 3. `.env` satır enjeksiyonu
# ---------------------------------------------------------------------------
INJECTION_VALUES = [
    "http://localhost:1234/v1\nSECRET_KEY=attacker",
    "http://localhost:1234/v1\r\nAI_DEVELOPER_ALLOW_SHELL=true",
    "model\nFIRST_ADMIN_PASSWORD=admin",
    "model\x00SECRET_KEY=x",
]


@pytest.mark.parametrize("value", INJECTION_VALUES)
def test_config_update_rejects_newline_injection_in_urls(value: str) -> None:
    with pytest.raises(PydanticValidationError):
        AIConfigUpdate(local_base_url=value)


@pytest.mark.parametrize("value", INJECTION_VALUES)
def test_config_update_rejects_newline_injection_in_model(value: str) -> None:
    with pytest.raises(PydanticValidationError):
        AIConfigUpdate(nvidia_model=value)


def test_config_update_rejects_newline_injection_in_api_key() -> None:
    with pytest.raises(PydanticValidationError):
        AIConfigUpdate(nvidia_api_key="key\nSECRET_KEY=attacker")


def test_config_update_rejects_non_http_url() -> None:
    with pytest.raises(PydanticValidationError):
        AIConfigUpdate(nvidia_base_url="file:///etc/passwd")


def test_config_update_rejects_unknown_provider_in_chain() -> None:
    with pytest.raises(PydanticValidationError):
        AIConfigUpdate(fallback_chain=["local", "attacker\nSECRET_KEY=x"])


def test_config_update_accepts_clean_values() -> None:
    payload = AIConfigUpdate(
        local_base_url="http://localhost:1234/v1",
        nvidia_model="meta/llama-3.3-70b-instruct",
        fallback_chain=["local", "nvidia"],
    )
    assert payload.local_base_url == "http://localhost:1234/v1"
