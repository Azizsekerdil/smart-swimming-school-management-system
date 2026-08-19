"""Veritabanı oturum yönetimi / Database session management.

SQLite ile başlar, PostgreSQL'e geçiş için URL değiştirmek yeterlidir.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("database")

_db_url = settings.resolved_database_url()
_is_sqlite = _db_url.startswith("sqlite")

engine: Engine = create_engine(
    _db_url,
    echo=settings.database_echo,
    future=True,
    # SQLite'ta FastAPI'nin thread havuzu için gerekli
    connect_args={"check_same_thread": False, "timeout": 30} if _is_sqlite else {},
    pool_pre_ping=not _is_sqlite,
)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(
        dbapi_connection, connection_record
    ) -> None:  # noqa: ANN001, ARG001
        """SQLite'ı üretim kalitesine yaklaştıran ayarlar.

        - foreign_keys: yabancı anahtar kısıtlamalarını zorunlu kılar (varsayılan KAPALI!)
        - journal_mode=WAL: eşzamanlı okuma/yazma performansı
        - synchronous=NORMAL: WAL ile güvenli ve hızlı
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, future=True
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI bağımlılığı: istek başına bir oturum."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Betikler / arka plan görevleri için işlem kapsamı."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def database_file_path() -> str | None:
    """SQLite kullanılıyorsa veritabanı dosya yolunu döndürür."""
    if _is_sqlite:
        return _db_url.replace("sqlite:///", "")
    return None


def is_sqlite() -> bool:
    return _is_sqlite
