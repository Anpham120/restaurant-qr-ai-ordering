"""Deterministic rolling summary for multi-turn chat sessions.

Builds a compact Vietnamese summary persisted by the .NET backend as
``ChatSession.RollingSummary``. The LLM prompt only keeps the last 8 turns;
this summary carries older session context forward without another model call.
"""
from __future__ import annotations

import re
from typing import Any

MAX_SUMMARY_CHARS = 3800
MAX_RECENT_TURNS = 4
MAX_SUGGESTED_NAMES = 8

_SECTION_RECENT = "Lượt gần đây:"

_SLOT_LABELS = {
    "số khách": "Số khách",
    "tránh": "Tránh",
    "chế độ ăn": "Chế độ ăn",
    "ngân sách": "Ngân sách",
    "độ cay": "Độ cay",
}


def _clip(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def _parse_slots(previous: str) -> dict[str, str]:
    slots: dict[str, str] = {}
    for line in (previous or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("- ") or stripped == _SECTION_RECENT:
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key and value:
            slots[key] = value
    return slots


def _parse_recent_turns(previous: str) -> list[str]:
    lines = (previous or "").splitlines()
    collecting = False
    turns: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == _SECTION_RECENT:
            collecting = True
            continue
        if collecting and stripped.startswith("- "):
            turns.append(stripped[2:].strip())
    return turns


def _parse_suggested_names(previous: str) -> list[str]:
    for line in (previous or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("đã gợi ý:"):
            raw = stripped.split(":", 1)[1]
            names = [part.strip() for part in raw.split(",") if part.strip()]
            return names
    return []


def _format_budget(value: Any) -> str | None:
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return f"{amount:,}".replace(",", ".") + "đ"


def _collect_constraint_slots(constraints: dict[str, Any]) -> dict[str, str]:
    slots: dict[str, str] = {}
    party_size = constraints.get("party_size")
    if party_size:
        slots["số khách"] = f"{party_size} người"

    allergens = constraints.get("allergens") or constraints.get("avoid_allergens")
    if isinstance(allergens, (list, tuple, set)):
        items = [str(item).strip() for item in allergens if str(item).strip()]
        if items:
            slots["tránh"] = ", ".join(items)
    elif isinstance(allergens, str) and allergens.strip() and allergens != "unknown":
        slots["tránh"] = allergens.strip()

    diet = constraints.get("diet")
    if isinstance(diet, str) and diet.strip() and diet != "unknown":
        slots["chế độ ăn"] = diet.strip()

    budget = _format_budget(constraints.get("budget_vnd"))
    if budget:
        slots["ngân sách"] = budget

    spice = constraints.get("spice")
    if isinstance(spice, str) and spice.strip() and spice != "unknown":
        slots["độ cay"] = spice.strip()

    return slots


def _merge_suggested_names(previous_names: list[str], suggested_actions: list[dict[str, Any]]) -> list[str]:
    names = list(previous_names)
    for action in suggested_actions:
        name = str(action.get("name") or "").strip()
        if not name:
            continue
        if name not in names:
            names.append(name)
    return names[-MAX_SUGGESTED_NAMES:]


def _build_turn_line(user_message: str, assistant_content: str) -> str:
    user_part = _clip(user_message, 80)
    assistant_part = _clip(re.sub(r"\*{1,2}|`|#", "", assistant_content), 100)
    return f"Khách: {user_part} → Bot: {assistant_part}"


def update_rolling_summary(
    previous: str,
    *,
    user_message: str,
    assistant_content: str,
    suggested_actions: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
    facts: list[dict[str, Any]] | None = None,
) -> str:
    """Return an updated rolling summary after one chat turn."""
    slots = _parse_slots(previous)
    slots.update(_collect_constraint_slots(constraints or {}))

    if facts:
        for fact in facts:
            kind = str(fact.get("kind") or "").strip().lower()
            value = str(fact.get("value") or "").strip()
            if not kind or not value:
                continue
            if kind in {"allergy", "allergen", "avoid"}:
                slots["tránh"] = value
            elif kind in {"party_size", "party"}:
                slots["số khách"] = f"{value} người" if value.isdigit() else value
            elif kind in {"budget", "budget_vnd"}:
                budget = _format_budget(value)
                if budget:
                    slots["ngân sách"] = budget

    suggested_names = _merge_suggested_names(
        _parse_suggested_names(previous),
        suggested_actions or [],
    )

    recent = _parse_recent_turns(previous)
    turn_line = _build_turn_line(user_message, assistant_content)
    if not recent or recent[-1] != turn_line:
        recent.append(turn_line)
    recent = recent[-MAX_RECENT_TURNS:]

    lines: list[str] = []
    slot_order = ("số khách", "tránh", "chế độ ăn", "ngân sách", "độ cay")
    for key in slot_order:
        value = slots.get(key)
        if value:
            lines.append(f"{_SLOT_LABELS[key]}: {value}")

    if suggested_names:
        lines.append("Đã gợi ý: " + ", ".join(suggested_names))

    if recent:
        lines.append(_SECTION_RECENT)
        lines.extend(f"- {turn}" for turn in recent)

    summary = "\n".join(lines).strip()
    if len(summary) <= MAX_SUMMARY_CHARS:
        return summary

    # Trim oldest turns first if we overflow.
    while len(summary) > MAX_SUMMARY_CHARS and len(recent) > 1:
        recent = recent[1:]
        lines = [line for line in lines if not line.startswith("- Khách:")]
        base_lines = [line for line in lines if line != _SECTION_RECENT and not line.startswith("- ")]
        lines = base_lines
        if recent:
            lines.append(_SECTION_RECENT)
            lines.extend(f"- {turn}" for turn in recent)
        summary = "\n".join(lines).strip()

    return summary[:MAX_SUMMARY_CHARS]
