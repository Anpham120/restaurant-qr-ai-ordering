from __future__ import annotations

import re
import unicodedata

from app.schemas import ChatResponse, FollowUp


_FOOD_KEYWORDS = frozenset(
    {
        "mon",
        "menu",
        "gia",
        "price",
        "goi y",
        "tu van",
        "recommend",
        "dat",
        "order",
        "cart",
        "gio",
        "com",
        "pizza",
        "hai san",
        "seafood",
        "drink",
        "uong",
        "budget",
        "ngan sach",
        "di ung",
        "allergy",
        "chay",
        "vegan",
        "promo",
        "khuyen mai",
    }
)

_GREETING = re.compile(
    r"^(xin\s+chao|chao(\s+ban|\s+anh|\s+chi|\s+em)?|hello|hi|hey|good\s+(morning|afternoon|evening))[\s!.?]*$",
    re.IGNORECASE,
)
_THANKS = re.compile(
    r"^(cam\s+on|thank\s+you|thanks|tks|ok\s+cam\s+on)[\s!.?]*$",
    re.IGNORECASE,
)
_GOODBYE = re.compile(
    r"^(tam\s+biet|bye|goodbye|see\s+you)[\s!.?]*$",
    re.IGNORECASE,
)
_ACK = re.compile(r"^(ok|oke|okay|uh|u|vang|da|yes|yep|duoc)[\s!.?]*$", re.IGNORECASE)


def try_smalltalk(message: str) -> dict | None:
    """Return an instant template response for narrow social phrases only."""

    text = message.strip()
    if not text:
        return None

    normalized = _normalize(text)
    words = normalized.split()
    if len(words) > 5:
        return None
    if any(keyword in normalized for keyword in _FOOD_KEYWORDS):
        return None

    language = "en" if _looks_english(normalized) else "vi"
    kind = _classify(normalized)
    if kind is None:
        return None

    content = _template(kind, language)
    return ChatResponse(
        content=content,
        provider_available=False,
        model="smalltalk-fastpath",
        retrieved_sources=[],
        guardrail_flags=[],
        suggested_cart_actions=[],
        follow_up=FollowUp(can_show_more=False, remaining_count=0),
        suggest_staff_handoff=False,
        latency_ms={"total": 0.0, "path": "smalltalk"},
    ).model_dump()


def _classify(normalized: str) -> str | None:
    if _GREETING.match(normalized):
        return "greeting"
    if _THANKS.match(normalized):
        return "thanks"
    if _GOODBYE.match(normalized):
        return "goodbye"
    if _ACK.match(normalized):
        return "ack"
    return None


def _template(kind: str, language: str) -> str:
    if language == "en":
        templates = {
            "greeting": (
                "Hello! I'm the CMC Restaurant assistant. "
                "Would you like to browse the menu or get dish recommendations?"
            ),
            "thanks": "You're welcome! Let me know if you'd like more menu suggestions.",
            "goodbye": "Goodbye! Hope you enjoy your meal at CMC Restaurant.",
            "ack": "Got it. Tell me what you'd like to eat or drink and I'll suggest options.",
        }
    else:
        templates = {
            "greeting": (
                "Xin chào! Mình là trợ lý AI của CMC Restaurant. "
                "Bạn muốn xem thực đơn hay cần gợi ý món?"
            ),
            "thanks": "Không có gì! Bạn cần gợi ý thêm món nào cứ nói nhé.",
            "goodbye": "Tạm biệt bạn! Chúc bạn ngon miệng tại CMC Restaurant.",
            "ack": "Dạ vâng. Bạn muốn ăn/uống gì, mình sẽ gợi ý món phù hợp.",
        }
    return templates[kind]


def _looks_english(normalized: str) -> bool:
    english_markers = ("hello", "hi", "hey", "thank", "thanks", "bye", "goodbye", "yes", "ok", "okay")
    return any(marker in normalized for marker in english_markers)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))
