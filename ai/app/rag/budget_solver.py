"""Greedy budget solver for menu recommendations under a VND cap."""
from __future__ import annotations

from typing import Any


def solve_budget(
    menu_items: list[dict[str, Any]],
    budget_vnd: int,
    party_size: int | None = None,
    excluded_ids: frozenset[str] | set[str] | None = None,
    max_items: int = 4,
) -> list[dict[str, Any]]:
    """Pick available items under budget, preferring category variety."""
    excluded = frozenset(excluded_ids or ())
    per_person = budget_vnd
    if party_size and party_size > 0:
        per_person = max(budget_vnd // party_size, 0)

    candidates: list[dict[str, Any]] = []
    for item in menu_items:
        item_id = _item_id(item)
        if not item_id or item_id in excluded:
            continue
        if not bool(item.get("is_available", True)):
            continue
        price = _price(item)
        if price is None or price <= 0 or price > budget_vnd:
            continue
        candidates.append(item)

    candidates.sort(key=lambda item: (_price(item) or 0, str(item.get("name") or "")))

    selected: list[dict[str, Any]] = []
    used_categories: set[str] = set()
    spent = 0

    # First pass: one item per category for variety.
    for item in candidates:
        if len(selected) >= max_items:
            break
        category = _category(item)
        price = _price(item) or 0
        if category in used_categories:
            continue
        if spent + price > budget_vnd:
            continue
        selected.append(_to_pick(item, reason="Phù hợp ngân sách và đa dạng nhóm món."))
        used_categories.add(category)
        spent += price

    # Second pass: fill remaining budget with cheapest unmatched items.
    selected_ids = {_item_id(item) for item in selected}
    for item in candidates:
        if len(selected) >= max_items:
            break
        item_id = _item_id(item)
        if item_id in selected_ids:
            continue
        price = _price(item) or 0
        if spent + price > budget_vnd:
            continue
        selected.append(_to_pick(item, reason="Bổ sung trong hạn mức ngân sách."))
        selected_ids.add(item_id)
        spent += price

    if party_size and party_size > 1 and per_person > 0:
        for pick in selected:
            pick["reason"] = (
                f"{pick.get('reason', '')} Ước tính ~{per_person:,} VND/người trong tổng {budget_vnd:,} VND."
            ).strip()

    return selected


def _to_pick(item: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        "menu_item_id": _item_id(item),
        "name": str(item.get("name") or "").strip(),
        "price_vnd": _price(item),
        "quantity": 1,
        "reason": reason,
        "requires_customer_confirmation": True,
    }


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("menu_item_id") or item.get("id") or "").strip()


def _price(item: dict[str, Any]) -> int | float | None:
    value = item.get("price_vnd") or item.get("price") or item.get("unit_price_vnd")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(str(value).replace(",", "").replace(".", ""))
    except (TypeError, ValueError):
        return None


def _category(item: dict[str, Any]) -> str:
    return str(item.get("category_name") or item.get("category_id") or "unknown").casefold()
