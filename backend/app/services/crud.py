"""Ortak CRUD yardımcıları / Shared CRUD helpers.

Yinelenen listeleme, sayfalama, sıralama ve arama mantığını tek yerde toplar.
"""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.base import Base
from app.schemas.common import PaginationParams

ModelT = TypeVar("ModelT", bound=Base)


def get_or_404(
    db: Session, model: type[ModelT], obj_id: int, message_key: str = "common.not_found"
) -> ModelT:
    """Kaydı getirir, yoksa yerelleştirilmiş 404 fırlatır."""
    obj = db.get(model, obj_id)
    if obj is None:
        raise NotFoundError(
            message_key, details={"id": obj_id, "entity": model.__name__}
        )
    return obj


def apply_search(
    stmt: Select, model: type[ModelT], query: str | None, fields: list[str]
) -> Select:
    """Verilen alanlarda büyük/küçük harf duyarsız LIKE araması uygular."""
    if not query or not query.strip():
        return stmt
    term = f"%{query.strip().lower()}%"
    clauses = [
        func.lower(getattr(model, field)).like(term)
        for field in fields
        if hasattr(model, field)
    ]
    return stmt.where(or_(*clauses)) if clauses else stmt


def apply_sort(
    stmt: Select,
    model: type[ModelT],
    params: PaginationParams,
    default_field: str = "id",
) -> Select:
    """Güvenli sıralama: yalnızca modelde var olan sütunlara izin verir."""
    field_name = params.sort_by or default_field
    column = getattr(model, field_name, None)
    if column is None:
        column = getattr(model, default_field, None)
    if column is None:
        return stmt
    return stmt.order_by(column.desc() if params.sort_dir == "desc" else column.asc())


def paginate(
    db: Session, stmt: Select, params: PaginationParams
) -> tuple[list[Any], int]:
    """(kayıtlar, toplam) döndürür."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.offset(params.offset).limit(params.page_size)).unique().all()
    return list(rows), total


def next_sequence_number(
    db: Session, model: type[ModelT], field: str, prefix: str, width: int = 5
) -> str:
    """`PREFIX00001` biçiminde artan numara üretir (öğrenci no, fiş no vb.)."""
    column = getattr(model, field)
    last = db.scalar(
        select(column).where(column.like(f"{prefix}%")).order_by(column.desc()).limit(1)
    )
    counter = 1
    if last:
        digits = "".join(ch for ch in str(last)[len(prefix) :] if ch.isdigit())
        if digits:
            counter = int(digits) + 1
    return f"{prefix}{counter:0{width}d}"


def apply_updates(
    obj: Any, payload: Any, exclude: set[str] | None = None
) -> dict[str, Any]:
    """Pydantic modelindeki `set` alanları ORM nesnesine uygular, farkı döndürür."""
    exclude = exclude or set()
    data = (
        payload.model_dump(exclude_unset=True)
        if hasattr(payload, "model_dump")
        else dict(payload)
    )
    changes: dict[str, Any] = {}
    for key, value in data.items():
        if key in exclude or not hasattr(obj, key):
            continue
        old = getattr(obj, key)
        if old != value:
            changes[key] = {"from": old, "to": value}
            setattr(obj, key, value)
    return changes
