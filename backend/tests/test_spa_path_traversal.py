"""SPA geri düşüş (fallback) yolunun dizin dışına çıkamadığını kanıtlar.

Geçmişte `GET /{full_path}` ucu, `frontend/dist` altındaki dosyayı kapsam
denetimi yapmadan sunuyordu. Kimlik doğrulaması gerektirmeyen bu uç, `..`
içeren bir yol ile proje kökündeki `.env`, veritabanı ve yedek dosyalarını
okumaya izin veriyordu.

Bu testler düzeltmenin (`app.main.resolve_spa_asset`) Windows mutlak yolları,
UNC yolları, kodlanmış varyantlar ve sembolik bağlar dâhil bütün kaçış
biçimlerini reddettiğini gösterir.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.testclient import TestClient

from app.main import resolve_spa_asset

SENTINEL = "SECRET_KEY=SENTINEL_NOT_A_REAL_VALUE"


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    """`<kök>/frontend/dist` benzeri bir ağaç ve kökte gizli bir dosya."""
    project_root = tmp_path / "project"
    frontend_dist = project_root / "frontend" / "dist"
    (frontend_dist / "assets").mkdir(parents=True)
    (frontend_dist / "index.html").write_text("SPA-INDEX", encoding="utf-8")
    (frontend_dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (project_root / ".env").write_text(SENTINEL, encoding="utf-8")
    (project_root / "data").mkdir()
    (project_root / "data" / "swimming_school.db").write_text(
        "DBDATA", encoding="utf-8"
    )
    return frontend_dist


# ---------------------------------------------------------------------------
# Birim: kapsam çözücü
# ---------------------------------------------------------------------------
def test_serves_real_file_inside_dist(dist: Path) -> None:
    resolved = resolve_spa_asset("index.html", dist)
    assert resolved is not None
    assert resolved.read_text(encoding="utf-8") == "SPA-INDEX"


def test_serves_nested_file_inside_dist(dist: Path) -> None:
    resolved = resolve_spa_asset("assets/app.js", dist)
    assert resolved is not None and resolved.name == "app.js"


TRAVERSAL_INPUTS = [
    # POSIX traversal
    "../.env",
    "../../.env",
    "../../../.env",
    "../../data/swimming_school.db",
    "a/../../../.env",
    "./../../.env",
    # Windows ters eğik çizgi
    "..\\..\\.env",
    "..\\\\..\\\\.env",
    "assets\\..\\..\\..\\.env",
    # Yüzde kodlaması (çift kodlanmış olarak sunucuya ulaşabilir)
    "%2e%2e/%2e%2e/.env",
    "%2e%2e%5c%2e%2e%5c.env",
    "..%2f..%2f.env",
    "%252e%252e%252f.env",
    # Mutlak yollar
    "/etc/passwd",
    "/.env",
    "C:/Windows/win.ini",
    "C:\\Windows\\win.ini",
    "c:/windows/win.ini",
    "C:/SwimmingSchool/.env",
    "C:.env",
    # UNC
    "//server/share/secret.txt",
    "\\\\server\\share\\secret.txt",
    # NUL bayt
    "index.html\x00.png",
]


@pytest.mark.parametrize("candidate", TRAVERSAL_INPUTS)
def test_traversal_inputs_are_rejected(dist: Path, candidate: str) -> None:
    assert resolve_spa_asset(candidate, dist) is None


def test_directory_is_not_served(dist: Path) -> None:
    assert resolve_spa_asset("assets", dist) is None
    assert resolve_spa_asset("", dist) is None
    assert resolve_spa_asset(".", dist) is None


@pytest.mark.skipif(
    os.name == "nt" and not os.environ.get("SWS_TEST_SYMLINKS"),
    reason="Windows'ta sembolik bağ oluşturmak yönetici hakkı ister",
)
def test_symlink_escape_is_rejected(dist: Path) -> None:
    link = dist / "escape.txt"
    link.symlink_to(dist.parent.parent / ".env")
    assert resolve_spa_asset("escape.txt", dist) is None


# ---------------------------------------------------------------------------
# Uçtan uca: gerçek yönlendirme mantığıyla aynı uç
# ---------------------------------------------------------------------------
@pytest.fixture
def spa_client(dist: Path) -> TestClient:
    """`app.main` içindeki `serve_spa` ile aynı gövdeyi kullanan mini uygulama."""
    spa_app = FastAPI()

    @spa_app.get("/")
    @spa_app.get("/{full_path:path}")
    def serve_spa(full_path: str = ""):  # noqa: ANN202
        if full_path.startswith(("api/", "docs", "redoc", "openapi.json", "uploads/")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        target = resolve_spa_asset(full_path, dist)
        if target is not None:
            return FileResponse(target)
        return FileResponse(dist / "index.html")

    return TestClient(spa_app)


@pytest.mark.parametrize(
    "url",
    [
        "/../.env",
        "/../../.env",
        "/..%2f..%2f.env",
        "/%2e%2e/%2e%2e/.env",
        "/assets/../../../.env",
        "/C:/Windows/win.ini",
        "/../../data/swimming_school.db",
    ],
)
def test_endpoint_never_returns_out_of_tree_content(
    spa_client: TestClient, url: str
) -> None:
    response = spa_client.get(url)
    assert response.status_code in (200, 404)
    body = response.text
    assert SENTINEL not in body
    assert "DBDATA" not in body
    if response.status_code == 200:
        assert body == "SPA-INDEX"


def test_endpoint_serves_index_for_client_routes(spa_client: TestClient) -> None:
    assert spa_client.get("/students").text == "SPA-INDEX"


def test_endpoint_serves_real_asset(spa_client: TestClient) -> None:
    assert spa_client.get("/assets/app.js").text == "console.log(1)"
