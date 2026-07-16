from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.domain import MenuItemContext


CATEGORY_PATTERN = re.compile(r'Cat\("(?P<id>[^"]+)",\s*"(?P<name>[^"]+)"')
ITEM_PATTERN = re.compile(
    r'Item\(\s*(?P<number>\d+)\s*,\s*"(?P<category>[^"]+)"\s*,\s*'
    r'"(?P<name>(?:[^"\\]|\\.)*)"\s*,\s*(?P<price>\d+)\s*,\s*'
    r'"(?P<description>(?:[^"\\]|\\.)*)"\s*,\s*"(?P<slug>[^"]+)"\s*,\s*'
    r'seededAt\s*,\s*\[(?P<tags>[^\]]*)\]\s*\)',
    re.MULTILINE,
)
TAG_PATTERN = re.compile(r'"((?:[^"\\]|\\.)*)"')


@dataclass(frozen=True)
class MenuSnapshot:
    source: str
    items: list[MenuItemContext]

    def to_mapping(self) -> dict:
        return {"source": self.source, "item_count": len(self.items), "items": [item.to_mapping() for item in self.items]}


def parse_restaurant_menu_seed(path: Path) -> MenuSnapshot:
    source = path.read_text(encoding="utf-8")
    categories = {match.group("id"): _unescape(match.group("name")) for match in CATEGORY_PATTERN.finditer(source)}
    items: list[MenuItemContext] = []
    for match in ITEM_PATTERN.finditer(source):
        number = int(match.group("number"))
        category_id = match.group("category")
        items.append(
            MenuItemContext(
                id=f"m_{number:03d}",
                category_id=category_id,
                category_name=categories.get(category_id, category_id),
                name=_unescape(match.group("name")),
                description=_unescape(match.group("description")),
                price_vnd=Decimal(match.group("price")),
                tags=tuple(_unescape(value) for value in TAG_PATTERN.findall(match.group("tags"))),
                is_available=True,
            )
        )

    ids = [item.id for item in items]
    if len(items) != 91 or len(set(ids)) != 91:
        raise ValueError(f"Expected exactly 91 unique menu items, found {len(items)} items and {len(set(ids))} IDs")
    if len(categories) != 13:
        raise ValueError(f"Expected exactly 13 categories, found {len(categories)}")
    return MenuSnapshot(source=str(path), items=items)


def write_snapshot(snapshot: MenuSnapshot, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot.to_mapping(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_snapshot(path: Path) -> MenuSnapshot:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = [MenuItemContext.from_mapping(item) for item in payload["items"]]
    if len(items) != 91:
        raise ValueError(f"Snapshot must contain 91 items, found {len(items)}")
    return MenuSnapshot(source=str(payload.get("source") or path), items=items)


def _unescape(value: str) -> str:
    return bytes(value, "utf-8").decode("unicode_escape") if "\\" in value else value

