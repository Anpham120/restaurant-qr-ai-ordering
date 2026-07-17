from __future__ import annotations

import re
import unicodedata
from typing import Any


_DISH_LINE_PATTERN = re.compile(
    r"^(\d+[\.\)]\s*|-+\s*|\*\s*|\•\s*)?.+$",
    re.MULTILINE,
)


def ground_response_content(
    content: str,
    suggested_actions: list[dict[str, Any]],
    menu_items: list[dict[str, Any]],
    *,
    wants_recommendations: bool = False,
) -> tuple[str, list[str], list[dict[str, Any]]]:
    """Ensure assistant prose and cards only reference live menu items."""

    flags: list[str] = []
    actions = list(suggested_actions)
    menu_names = _menu_name_index(menu_items)

    if wants_recommendations and not actions:
        flags.append("MENU_FABRICATION_BLOCKED")

    if _content_has_ungrounded_dishes(content, menu_names):
        flags.append("MENU_FABRICATION_BLOCKED")
        if actions:
            content = format_grounded_recommendation_content(actions)
        elif wants_recommendations:
            content = (
                "Mình chưa tìm được món phù hợp chính xác trong thực đơn hiện tại. "
                "Bạn có thể xem tab Thực đơn hoặc mô tả rõ hơn khẩu vị/nhóm món bạn muốn."
            )
        else:
            content = _strip_ungrounded_lines(content, menu_names) or (
                "Mình chỉ có thể tư vấn dựa trên thực đơn hiện có của nhà hàng. "
                "Bạn vui lòng hỏi lại theo món hoặc nhóm món trong menu nhé."
            )

    if wants_recommendations and actions and not _content_mentions_any_action(content, actions):
        content = format_grounded_recommendation_content(actions, intro=_short_intro(content))

    return content.strip(), _dedupe_flags(flags), actions


def format_grounded_recommendation_content(
    actions: list[dict[str, Any]],
    *,
    intro: str | None = None,
) -> str:
    if not actions:
        return (
            "Hiện chưa có món phù hợp trong thực đơn để gợi ý. "
            "Bạn thử xem tab Thực đơn hoặc đổi tiêu chí nhé."
        )

    header = intro or "Dựa trên thực đơn hiện tại, mình gợi ý các món sau:"
    lines = [header, ""]
    for index, action in enumerate(actions, start=1):
        name = str(action.get("name") or "Món").strip()
        reason = str(action.get("reason") or "").strip()
        price = action.get("price_vnd") or action.get("price")
        price_text = ""
        if isinstance(price, (int, float)):
            price_text = f" ({int(price):,}đ)".replace(",", ".")
        line = f"{index}. {name}{price_text}"
        if reason:
            line += f" — {reason}"
        lines.append(line)
    lines.append("")
    lines.append("Bạn muốn mình gợi ý thêm món khác hay xem chi tiết món nào?")
    return "\n".join(lines)


def _content_has_ungrounded_dishes(content: str, menu_names: dict[str, str]) -> bool:
    if not content.strip() or not menu_names:
        return False

    candidate_lines = _candidate_dish_lines(content)
    if candidate_lines:
        ungrounded = [line for line in candidate_lines if not _line_matches_menu(line, menu_names)]
        if not ungrounded:
            return False
        if len(ungrounded) == len(candidate_lines):
            return True
        return len(ungrounded) >= max(1, len(candidate_lines) // 2)

    if _content_mentions_known_menu_name(content, menu_names):
        return False

    return len(content) > 120 and bool(re.search(r"\d+[\.\)]\s+", content))


def _content_mentions_known_menu_name(content: str, menu_names: dict[str, str]) -> bool:
    normalized_content = _normalize(content)
    return any(name in normalized_content for name in menu_names if len(name) >= 4)


def _content_mentions_any_action(content: str, actions: list[dict[str, Any]]) -> bool:
    normalized_content = _normalize(content)
    for action in actions:
        name = _normalize(str(action.get("name") or ""))
        if name and name in normalized_content:
            return True
    return False


def _candidate_dish_lines(content: str) -> list[str]:
    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^\d+[\.\)]\s+", line) or line.startswith("- ") or line.startswith("• "):
            lines.append(line)
    return lines


def _line_matches_menu(line: str, menu_names: dict[str, str]) -> bool:
    normalized_line = _normalize(line)
    return any(name in normalized_line for name in menu_names if len(name) >= 4)


def _strip_ungrounded_lines(content: str, menu_names: dict[str, str]) -> str:
    kept: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            kept.append("")
            continue
        if line in _candidate_dish_lines(content) and not _line_matches_menu(line, menu_names):
            continue
        kept.append(raw_line)
    collapsed = "\n".join(kept).strip()
    return re.sub(r"\n{3,}", "\n\n", collapsed)


def _menu_name_index(menu_items: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in menu_items:
        name = str(item.get("name") or "").strip()
        normalized = _normalize(name)
        if normalized:
            names[normalized] = name
    return names


def _short_intro(content: str) -> str | None:
    first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if not first_line or first_line.startswith(("1.", "-", "•")):
        return None
    if len(first_line) <= 180:
        return first_line
    return None


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))


def _dedupe_flags(flags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for flag in flags:
        text = flag.strip().upper()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
