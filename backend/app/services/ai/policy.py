"""AI geliştirici ajanı güvenlik politikası / Developer agent security policy.

TEMEL İLKE: Yapay zekâ Windows terminaline sınırsız erişemez.

Varsayılan olarak YASAK:
  * proje klasörü dışına yazma
  * sistem dosyalarını değiştirme
  * registry değiştirme
  * disk biçimlendirme
  * kullanıcı hesabı değiştirme
  * kimlik bilgisi okuma
  * tarayıcı şifrelerini okuma

Yıkıcı işlemler kullanıcı onayı gerektirir.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import SecurityPolicyError
from app.core.logging_config import get_logger

logger = get_logger("developer-agent")

# ---------------------------------------------------------------------------
# İzin verilen komutlar (beyaz liste)
# ---------------------------------------------------------------------------
ALLOWED_COMMANDS: dict[str, str] = {
    "pytest": "Test çalıştırma",
    "python": "Python betiği (yalnızca proje içinden)",
    "ruff": "Lint denetimi",
    "black": "Kod biçimlendirme",
    "mypy": "Tip denetimi",
    "alembic": "Veritabanı migration",
    "npm": "Frontend paket komutları (run/ci/test/build/lint)",
    "npx": "Frontend araçları",
    "git": "Sürüm kontrolü (yalnızca güvenli alt komutlar)",
}

# npm/git için izin verilen alt komutlar
ALLOWED_SUBCOMMANDS: dict[str, set[str]] = {
    "npm": {"run", "ci", "test", "install", "list", "audit"},
    "npx": {"tsc", "eslint", "prettier", "vitest"},
    "git": {"status", "diff", "log", "show", "add", "stash", "rev-parse", "branch"},
    # `-c` KASITLI OLARAK YOK: rastgele Python kaynağı çalıştırmak, bu
    # dosyadaki komut beyaz listesini ve engelli desenleri tümüyle atlatır.
    "python": {"-m", "-V", "--version"},
}

# Bu komutlarda TÜM bayraklar beyaz listeye tabidir (yalnızca ilk argüman
# değil). Yorumlayıcılar için zorunludur: tek bir `-c` bayrağı, aşağıdaki
# bütün engelleri atlayarak rastgele kod çalıştırabilir.
STRICT_FLAG_COMMANDS = frozenset({"python", "python3", "py"})


# ---------------------------------------------------------------------------
# Kesinlikle yasak desenler
# ---------------------------------------------------------------------------
BLOCKED_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+-rf\b", "Özyinelemeli zorla silme"),
    (r"\bdel\s+/[sqf]", "Toplu dosya silme"),
    (r"\brmdir\s+/s", "Klasör ağacı silme"),
    (r"\bRemove-Item\b.*-Recurse.*-Force", "PowerShell özyinelemeli silme"),
    (r"\bformat\b\s+[a-z]:", "Disk biçimlendirme"),
    (r"\bdiskpart\b", "Disk yönetimi"),
    (r"\breg(edit)?\s+(add|delete|import)", "Registry değişikliği"),
    (r"Set-ItemProperty.*HK(LM|CU):", "Registry değişikliği"),
    (r"New-ItemProperty.*HK(LM|CU):", "Registry değişikliği"),
    (r"\bnet\s+user\b", "Kullanıcı hesabı değişikliği"),
    (r"\bnet\s+localgroup\b", "Grup üyeliği değişikliği"),
    (
        r"New-LocalUser|Set-LocalUser|Add-LocalGroupMember",
        "Kullanıcı hesabı değişikliği",
    ),
    (r"\bicacls\b|\bcacls\b|\btakeown\b", "Dosya izni değişikliği"),
    (
        r"\bshutdown\b|\bRestart-Computer\b|\bStop-Computer\b",
        "Sistem kapatma/yeniden başlatma",
    ),
    (r"\bsc\s+(config|delete|stop|start)\b", "Windows servis değişikliği"),
    (r"Set-Service|Stop-Service|New-Service", "Windows servis değişikliği"),
    (r"\bschtasks\b|\bRegister-ScheduledTask\b", "Zamanlanmış görev oluşturma"),
    (r"\bbcdedit\b|\bvssadmin\b", "Önyükleme/gölge kopya değişikliği"),
    (r"\bnetsh\s+(firewall|advfirewall)", "Güvenlik duvarı değişikliği"),
    (r"Set-MpPreference|Add-MpPreference", "Antivirüs ayarı değişikliği"),
    (
        r"\bcurl\b.*\|\s*(sh|bash|powershell)",
        "İnternetten indirilen betiğin çalıştırılması",
    ),
    (
        r"Invoke-WebRequest.*\|\s*(iex|Invoke-Expression)",
        "İnternetten indirilen betiğin çalıştırılması",
    ),
    (r"\biwr\b.*\|\s*iex", "İnternetten indirilen betiğin çalıştırılması"),
    (r"\bInvoke-Expression\b|\biex\b\s", "Dinamik kod çalıştırma"),
    (r"\bStart-Process\b.*-Verb\s+RunAs", "Yükseltilmiş yetkiyle çalıştırma"),
    (r"\brunas\b", "Yükseltilmiş yetkiyle çalıştırma"),
    (r"Get-Credential|cmdkey|vaultcmd", "Kimlik bilgisi erişimi"),
    (r"\bmimikatz\b|\blsass\b", "Kimlik bilgisi çıkarma"),
    (r"Login Data|Local State|\\Chrome\\User Data", "Tarayıcı şifre deposu erişimi"),
    (r"logins\.json|key4\.db|cookies\.sqlite", "Tarayıcı kimlik deposu erişimi"),
    (r"\.env\b", ".env dosyasına erişim (sır sızıntısı riski)"),
    (r"\bpip\s+install\b", "Bağımlılık kurulumu (manuel onay gerekir)"),
    (r"\bnpm\s+(publish|adduser|login|token)", "Paket yayınlama / kimlik işlemi"),
    (
        r"\bgit\s+(push|remote\s+add|config\s+--global)",
        "Uzak depo / global yapılandırma değişikliği",
    ),
    (r"[;&|]{1,2}\s*\w", "Komut zincirleme (tek komut çalıştırılabilir)"),
    (r"`|\$\(", "Komut ikamesi"),
    (r">\s*[A-Za-z]:\\", "Mutlak yola yönlendirme"),
    (r"\bpy(?:thon)?[0-9.]*\s+(?:-\S+\s+)*-c\b", "Dinamik kod çalıştırma (python -c)"),
    (r"\bexec\s*\(|\beval\s*\(", "Dinamik kod çalıştırma"),
    (r"\bcode\.interact\b|\brunpy\b", "Etkileşimli/dolaylı kod çalıştırma"),
]

# Kullanıcı onayı gerektiren (yıkıcı olabilecek) işlemler
REQUIRES_CONFIRMATION = [
    "dosya silme",
    "veritabanı migration (alembic upgrade/downgrade)",
    "yama uygulama (apply_patch)",
    "geri alma (rollback)",
    "10'dan fazla dosyayı etkileyen değişiklik",
]

# Ajanın hiçbir koşulda okuyamayacağı/yazamayacağı yollar
FORBIDDEN_PATH_PARTS = (
    ".env",
    ".git/config",
    "id_rsa",
    "credentials",
    "secrets",
    ".venv",
    "node_modules",
    "backups",
    "data/swimming_school.db",
)

# Yazılabilir uzantılar
WRITABLE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".txt",
    ".toml",
    ".cfg",
    ".ini",
    ".sql",
}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    requires_confirmation: bool = False


class CommandPolicy:
    """Komut ve dosya erişim politikası."""

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = (project_root or settings.developer_root_path).resolve()

    # ------------------------------------------------------------------
    # Yol denetimi
    # ------------------------------------------------------------------
    def resolve_path(self, relative_path: str) -> Path:
        """Göreli yolu proje kökü içinde çözer. Dışarı çıkma girişimini engeller."""
        candidate = (self.project_root / relative_path).resolve()
        try:
            candidate.relative_to(self.project_root)
        except ValueError:
            logger.warning("Proje dışı yol erişimi engellendi: %s", relative_path)
            raise SecurityPolicyError(
                "ai.path_outside_project", details={"path": relative_path}
            ) from None
        return candidate

    def can_read(self, relative_path: str) -> PolicyDecision:
        normalized = relative_path.replace("\\", "/").lower()
        for part in FORBIDDEN_PATH_PARTS:
            if part.lower() in normalized:
                return PolicyDecision(False, f"Yasak yol: {part}")
        try:
            self.resolve_path(relative_path)
        except SecurityPolicyError:
            return PolicyDecision(False, "Proje dizini dışında")
        return PolicyDecision(True, "izinli")

    def can_write(self, relative_path: str) -> PolicyDecision:
        read_decision = self.can_read(relative_path)
        if not read_decision.allowed:
            return read_decision

        path = self.resolve_path(relative_path)
        if path.suffix.lower() not in WRITABLE_EXTENSIONS:
            return PolicyDecision(
                False, f"Yazılamayan dosya türü: {path.suffix or '(uzantısız)'}"
            )
        # Migration dosyaları elle gözden geçirilmelidir
        if "alembic/versions" in relative_path.replace("\\", "/"):
            return PolicyDecision(
                True,
                "Migration dosyası - dikkatli inceleyin",
                requires_confirmation=True,
            )
        return PolicyDecision(True, "izinli")

    # ------------------------------------------------------------------
    # Komut denetimi
    # ------------------------------------------------------------------
    def check_command(self, command: str) -> PolicyDecision:
        """Komutun çalıştırılabilir olup olmadığını denetler."""
        if not settings.ai_developer_allow_shell:
            return PolicyDecision(False, "Kabuk erişimi ayarlardan kapatılmış")

        stripped = command.strip()
        if not stripped:
            return PolicyDecision(False, "Boş komut")
        if len(stripped) > 500:
            return PolicyDecision(False, "Komut çok uzun")

        for pattern, description in BLOCKED_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                logger.warning(
                    "Politika komutu engelledi (%s): %s", description, stripped[:120]
                )
                return PolicyDecision(False, f"Yasak işlem: {description}")

        try:
            parts = shlex.split(stripped, posix=False)
        except ValueError:
            return PolicyDecision(False, "Komut ayrıştırılamadı")
        if not parts:
            return PolicyDecision(False, "Boş komut")

        executable = Path(parts[0].strip('"')).name.lower().removesuffix(".exe")
        if executable not in ALLOWED_COMMANDS:
            return PolicyDecision(
                False,
                f"'{executable}' izin verilen komutlar arasında değil "
                f"({', '.join(sorted(ALLOWED_COMMANDS))})",
            )

        allowed_subs = ALLOWED_SUBCOMMANDS.get(executable)
        if allowed_subs and len(parts) > 1:
            subcommand = parts[1].lower()
            if executable in STRICT_FLAG_COMMANDS:
                # Katı mod: BÜTÜN argümanlar denetlenir. Aksi hâlde `-` ile
                # başlayan her bayrak serbest kalır ve `-c` gibi dinamik kod
                # çalıştıran bayraklar beyaz listeyi anlamsız hâle getirir.
                for argument in parts[1:]:
                    flag = argument.lower()
                    if not flag.startswith("-"):
                        break
                    if flag.split("=", 1)[0] not in allowed_subs:
                        return PolicyDecision(
                            False, f"'{executable} {flag}' izin verilmiyor"
                        )
            elif subcommand not in allowed_subs and not subcommand.startswith("-"):
                return PolicyDecision(
                    False, f"'{executable} {subcommand}' izin verilmiyor"
                )

        needs_confirmation = executable == "alembic" and any(
            keyword in stripped.lower() for keyword in ("upgrade", "downgrade", "stamp")
        )
        return PolicyDecision(
            True, f"{ALLOWED_COMMANDS[executable]} çalıştırılabilir", needs_confirmation
        )

    def public_info(self) -> dict:
        """Politikanın kullanıcıya şeffaf gösterimi."""
        return {
            "shell_enabled": settings.ai_developer_allow_shell,
            "apply_enabled": settings.ai_developer_allow_apply,
            "project_root": str(self.project_root),
            "allowed_commands": [
                f"{name} — {description}"
                for name, description in ALLOWED_COMMANDS.items()
            ],
            "blocked_patterns": [description for _, description in BLOCKED_PATTERNS],
            "write_scope": (
                f"Yalnızca {self.project_root} altındaki "
                f"{', '.join(sorted(WRITABLE_EXTENSIONS))} dosyaları"
            ),
            "requires_confirmation": REQUIRES_CONFIRMATION,
        }


policy = CommandPolicy()
