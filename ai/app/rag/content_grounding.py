from __future__ import annotations

import re
from typing import Any

from app.rag.vietnamese_normalizer import normalize_query_text


_DISH_LINE_PATTERN = re.compile(
    r"^(\d+[\.\)]\s*|-+\s*|\*\s*|\•\s*)?.+$",
    re.MULTILINE,
)

_MENU_ID_TOKEN = re.compile(
    r"\(\s*menu_item_id:\s*m_\d+\s*\)|\bm_\d{2,4}\b",
    re.IGNORECASE,
)

# Patterns indicating the response is listing items to AVOID (allergy/dietary),
# not recommending them. In this context, mentioning dish names is informational
# warning, not fabrication.
_AVOIDANCE_MARKERS = (
    "tranh", "khong nen", "khong an", "can tranh", "khong goi",
    "nen bo qua", "khong phu hop", "can luu y", "chua",
    "di ung", "allerg", "avoid", "khong duoc an",
)


def _is_avoidance_context(content: str) -> bool:
    """Return True if the content is listing dishes to AVOID (allergy/dietary).

    When the AI warns about allergens or lists dishes the customer should not
    order, mentioning dish names is informational — not fabrication.
    """
    normalized = normalize_query_text(content)
    # Need at least 2 avoidance markers to be confident this is avoidance context
    marker_count = sum(1 for m in _AVOIDANCE_MARKERS if m in normalized)
    return marker_count >= 2


def _is_allergy_advisory_response(content: str) -> bool:
    """Allergy-safe guidance that intentionally avoids naming specific menu picks."""
    normalized = normalize_query_text(content)
    return (
        any(term in normalized for term in ("di ung", "allerg", "an toan", "lan cheo", "nhiem cheo"))
        and any(term in normalized for term in ("nhan vien", "xac nhan", "khong the cam ket", "bao truoc"))
    )


def strip_menu_ids(content: str) -> str:
    """Remove internal menu item ids (m_xxx) from customer-facing prose."""

    if not content or "m_" not in content.casefold():
        return content
    cleaned = _MENU_ID_TOKEN.sub("", content)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +([,.;:)\]])", r"\1", cleaned)
    return cleaned.strip()


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
        if not _is_avoidance_context(content) and not _is_allergy_advisory_response(content):
            flags.append("MENU_FABRICATION_BLOCKED")

    # When the response is an allergy/dietary avoidance context (listing dishes
    # to AVOID), dish names are informational warnings, not fabricated recommendations.
    if _is_avoidance_context(content):
        pass  # skip ungrounded dish check entirely
    elif not wants_recommendations:
        pass  # FAQ/KB/policy answers are not menu recommendation lists
    elif _content_has_ungrounded_dishes(content, menu_names):
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
    elif wants_recommendations and _content_has_fabricated_dish_names(content, menu_names):
        flags.append("MENU_FABRICATION_BLOCKED")
        if actions:
            content = format_grounded_recommendation_content(actions)

    if wants_recommendations and actions and not _content_mentions_any_action(content, actions):
        content = format_grounded_recommendation_content(actions, intro=_short_intro(content))

    return strip_menu_ids(content.strip()), _dedupe_flags(flags), actions


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
        return bool(ungrounded)

    if _content_mentions_known_menu_name(content, menu_names):
        return False

    return len(content) > 120 and bool(re.search(r"\d+[\.\)]\s+", content))


def _content_has_fabricated_dish_names(content: str, menu_names: dict[str, str]) -> bool:
    phrases = _extract_dish_phrases(content) + _extract_prose_dish_phrases(content)
    if not phrases:
        return False

    fabricated = [
        phrase
        for phrase in phrases
        if not _fuzzy_matches_menu(phrase, menu_names)
    ]
    return bool(fabricated)


# Segments containing these markers are advisory/meta prose, not dish names.
_PROSE_META_MARKERS = (
    "nhan vien",
    "di ung",
    "menu",
    "thuc don",
    "he thong",
    "du lieu",
    "xac nhan",
    "vui long",
    "giao dien",
    "chua co",
    "khong the",
    "an toan",
    "lan cheo",
    "nhiem cheo",
    "truoc khi",
    "ban nen",
    "nguy co",
    # Allergy/dietary avoidance markers
    "tranh",
    "khong nen",
    "khong an",
    "can tranh",
    "khong goi",
    "nen bo qua",
    "can luu y",
    "allerg",
    "avoid",
    "khong phu hop",
    "hai san",
    "tom cua",
    "dau phong",
    "gluten",
)


def _extract_prose_dish_phrases(content: str) -> list[str]:
    normalized = _normalize(content)
    if "," not in normalized and " hoac " not in normalized:
        return []
    phrases: list[str] = []
    for segment in re.split(r"[,;]| hoac ", normalized):
        cleaned = segment.strip(" .")
        cleaned = re.sub(r"^(nhu|mon|cac mon|goi y)\s+", "", cleaned)
        token_count = len(cleaned.split())
        # Dish names are short noun phrases; long segments are prose sentences.
        if token_count < 2 or token_count > 5:
            continue
        if any(marker in cleaned for marker in _PROSE_META_MARKERS):
            continue
        phrases.append(cleaned)
    return phrases


def _extract_dish_phrases(content: str) -> list[str]:
    phrases: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r"^\d+[\.\)]\s+", line):
            line = re.sub(r"^\d+[\.\)]\s+", "", line)
        elif line.startswith(("- ", "• ", "* ")):
            line = line[2:].strip()
        else:
            continue
        line = re.split(r"\s*[—\-–]\s*", line, maxsplit=1)[0]
        line = re.sub(r"\([^)]*\)", "", line)
        line = re.sub(r"\d[\d\.,]*\s*(?:đ|vnd|k)?$", "", line, flags=re.IGNORECASE).strip(" .")
        normalized = _normalize(line)
        if len(normalized.split()) >= 2:
            phrases.append(normalized)
    return phrases


def _fuzzy_matches_menu(phrase: str, menu_names: dict[str, str], threshold: float = 0.55) -> bool:
    if not phrase:
        return True
    if phrase in menu_names:
        return True

    phrase_tokens = set(phrase.split())
    if not phrase_tokens:
        return True

    for name in menu_names:
        if phrase in name or name in phrase:
            return True
        name_tokens = set(name.split())
        if not name_tokens:
            continue
        overlap = len(phrase_tokens & name_tokens)
        if overlap >= 2:
            return True
        jaccard = overlap / len(phrase_tokens | name_tokens)
        if jaccard >= threshold:
            return True
    return False


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
    return normalize_query_text(value)


def _dedupe_flags(flags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for flag in flags:
        text = flag.strip().upper()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
