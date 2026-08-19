"""Ortak şema yapıları / Shared schema structures."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

T = TypeVar("T")

# E-posta tipi.
# Not: Standart `EmailStr`, `.local` / `.internal` gibi özel amaçlı alan adlarını
# reddeder. Yüzme okulu sistemi çoğunlukla kurum içi (offline) kurulduğu için
# `admin@yuzmeokulu.local` gibi adreslerin geçerli olması gerekir.
EMAIL_PATTERN = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=255, pattern=EMAIL_PATTERN
    ),
]


class ORMModel(BaseModel):
    """ORM nesnelerinden okuyabilen taban şema."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Page(BaseModel, Generic[T]):
    """Sayfalanmış liste yanıtı."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 25

    @property
    def pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=200)
    sort_by: str | None = None
    sort_dir: str = Field(default="asc", pattern="^(asc|desc)$")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Message(BaseModel):
    """Basit bilgi yanıtı."""

    code: str
    message: str
    data: dict[str, Any] | None = None


class DateRange(BaseModel):
    start: date
    end: date


class IdName(BaseModel):
    """Açılır listeler için hafif gösterim."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class BulkIds(BaseModel):
    ids: list[int] = Field(min_length=1)


class HealthComponent(BaseModel):
    name: str
    status: str  # ok | degraded | down | disabled
    detail: str | None = None
    latency_ms: int | None = None


class HealthReport(BaseModel):
    status: str
    checked_at: datetime
    app_version: str
    components: list[HealthComponent]
