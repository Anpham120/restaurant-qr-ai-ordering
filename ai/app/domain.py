from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class MenuItemContext:
    id: str
    category_id: str
    category_name: str
    name: str
    description: str
    price_vnd: Decimal
    tags: tuple[str, ...] = ()
    is_available: bool = True

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "MenuItemContext":
        return cls(
            id=str(value.get("id") or value.get("menu_item_id") or "").strip(),
            category_id=str(value.get("category_id") or "").strip(),
            category_name=str(value.get("category_name") or "").strip(),
            name=str(value.get("name") or "").strip(),
            description=str(value.get("description") or "").strip(),
            price_vnd=Decimal(str(value.get("price_vnd") or value.get("price") or 0)),
            tags=tuple(str(tag).strip() for tag in value.get("tags") or [] if str(tag).strip()),
            is_available=bool(value.get("is_available", True)),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "name": self.name,
            "description": self.description,
            "price_vnd": int(self.price_vnd),
            "tags": list(self.tags),
            "is_available": self.is_available,
        }


@dataclass(frozen=True)
class RetrievalDocument:
    id: str
    kind: str
    source: str
    title: str
    text: str
    menu_item_id: str | None = None
    answer: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    document: RetrievalDocument
    score: float
    rank: int

