from __future__ import annotations

import re
from typing import Any

from app.rag.vietnamese_normalizer import normalize_query_text


_WIFI_TERMS = ("wifi", "internet", "mang khong day", "mang wifi")
_PASSWORD_TERMS = ("mat khau", "password", "pass ", " pass", "mk wifi", "mk mang")
_GUEST_SSID_MARKER = "cmc_restaurant_guest"
_PASSWORD_MARKER = "cmcfood2026"


def _normalize(text: str) -> str:
    return normalize_query_text(text)


def _chunk_has_wifi_credentials(content: str) -> bool:
    lowered = content.casefold().replace("-", "_")
    return _GUEST_SSID_MARKER in lowered and _PASSWORD_MARKER in lowered


def _is_wifi_question(normalized: str) -> bool:
    return any(term in normalized for term in _WIFI_TERMS)


def _wants_wifi_password(normalized: str) -> bool:
    return _is_wifi_question(normalized) and any(term in normalized for term in _PASSWORD_TERMS)


def _chunk_is_wifi_faq(item: Any) -> bool:
    content = item.chunk.content
    title = item.chunk.title.casefold()
    lowered = content.casefold()
    if "wifi" in title:
        return True
    if _chunk_has_wifi_credentials(content):
        return True
    return "wifi" in lowered and ("miễn phí" in lowered or "mien phi" in normalize_query_text(content))


def _find_wifi_chunk(retrieved: list[Any]) -> Any | None:
    for item in retrieved:
        if _chunk_is_wifi_faq(item):
            return item
    return None


def _format_wifi_answer(chunk_content: str, *, include_password: bool) -> str:
    if include_password:
        match = re.search(
            r"(?i)tên mạng:\s*([^,\n]+).*?mật khẩu:\s*(\S+)",
            chunk_content,
        )
        if match:
            ssid = match.group(1).strip()
            password = match.group(2).strip().rstrip(".")
            return (
                f"WiFi miễn phí tại nhà hàng: mạng {ssid}, mật khẩu {password}. "
                "Mật khẩu cũng được dán tại mỗi bàn."
            )

        match = re.search(
            r"(?i)ssid:\s*([^,\n|]+).*?(?:pass|mật khẩu):\s*(\S+)",
            chunk_content,
        )
        if match:
            ssid = match.group(1).strip()
            password = match.group(2).strip().rstrip(".")
            return (
                f"WiFi miễn phí tại nhà hàng: mạng {ssid}, mật khẩu {password}. "
                "Mật khẩu cũng được dán tại mỗi bàn."
            )

    if "wifi miễn phí" in chunk_content.casefold() or "cung cấp wifi" in chunk_content.casefold():
        first_sentence = chunk_content.strip().split("\n")[0].strip()
        if first_sentence:
            return first_sentence

    return (
        "Nhà hàng có WiFi miễn phí cho khách. "
        "Bạn có thể hỏi nhân viên hoặc xem tem dán tại bàn để biết mật khẩu."
    )


def try_wifi_policy_fast_path(message: str, retrieved: list[Any]) -> dict[str, Any] | None:
    """Return a deterministic WiFi FAQ answer when KB chunk is already retrieved."""

    normalized = _normalize(message)
    if not _is_wifi_question(normalized):
        return None

    wifi_chunk = _find_wifi_chunk(retrieved)
    if wifi_chunk is None:
        return None

    include_password = _wants_wifi_password(normalized)
    content = _format_wifi_answer(wifi_chunk.chunk.content, include_password=include_password)
    return {
        "content": content,
        "provider_available": False,
        "model": "deterministic-wifi-faq",
        "retrieved_sources": [
            {
                "source": wifi_chunk.chunk.source,
                "title": wifi_chunk.chunk.title,
                "score": float(wifi_chunk.score),
            }
        ],
        "guardrail_flags": [],
        "suggested_cart_actions": [],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": False,
    }
