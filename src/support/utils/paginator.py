"""Paginação genérica, independente de domínio."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """Uma página de resultados com metadados de paginação."""

    items: list[T]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        if self.per_page <= 0:
            return 0
        return (self.total + self.per_page - 1) // self.per_page

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_prev(self) -> bool:
        return self.page > 1


class Paginator:
    """Converte page/per_page em offset/limit para queries."""

    @staticmethod
    def offset(page: int, per_page: int) -> int:
        return max(page - 1, 0) * per_page

    @staticmethod
    def build(items: list[T], total: int, page: int, per_page: int) -> Page[T]:
        return Page(items=items, total=total, page=page, per_page=per_page)
