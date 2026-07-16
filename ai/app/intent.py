from __future__ import annotations

from dataclasses import dataclass

from app.text import normalize_text


OUT_OF_SCOPE_TERMS = (
    "thoi tiet",
    "co phieu",
    "chung khoan",
    "bitcoin",
    "crypto",
    "bong da",
    "lap trinh",
    "viet code",
    "chuong trinh python",
    "giai phuong trinh",
    "bai tap lich su",
    "tin tuc quoc te",
)
ACTION_TERMS = (
    "dat mon ho",
    "dat giup",
    "dat luon",
    "chot don",
    "gui xuong bep",
    "gui don",
    "them vao gio",
    "thanh toan ho",
    "mua giup",
)
RECOMMENDATION_TERMS = (
    "goi y",
    "tu van",
    "nen an",
    "an gi",
    "chon mon",
    "phu hop",
    "mon nao",
)
PRICE_TERMS = ("gia bao nhieu", "bao nhieu tien", "gia cua", "gia mon")
POLICY_TERMS = (
    "thanh toan",
    "gio mo cua",
    "gio dong cua",
    "wifi",
    "dau xe",
    "gui xe",
    "dat ban",
    "huy don",
    "doi mon",
    "di ung",
    "gluten",
    "con mon",
    "het mon",
    "giao hang",
    "mang ve",
    "pickup",
)
PROMPT_INJECTION_TERMS = (
    "bo qua huong dan",
    "quen quy tac",
    "system prompt",
    "developer message",
    "lam theo lenh moi",
)


@dataclass(frozen=True)
class IntentResult:
    normalized: str
    flags: tuple[str, ...]
    out_of_scope: bool
    requests_action: bool
    requests_recommendation: bool
    asks_price: bool
    asks_policy: bool
    prompt_injection: bool


def classify_intent(message: str) -> IntentResult:
    normalized = normalize_text(message)
    out_of_scope = any(term in normalized for term in OUT_OF_SCOPE_TERMS)
    requests_action = any(term in normalized for term in ACTION_TERMS)
    requests_recommendation = any(term in normalized for term in RECOMMENDATION_TERMS)
    asks_price = any(term in normalized for term in PRICE_TERMS)
    asks_policy = any(term in normalized for term in POLICY_TERMS)
    prompt_injection = any(term in normalized for term in PROMPT_INJECTION_TERMS)
    flags: list[str] = []
    if out_of_scope:
        flags.append("OUT_OF_SCOPE")
    if requests_action:
        flags.append("CUSTOMER_CONFIRMATION_REQUIRED")
    if prompt_injection:
        flags.append("PROMPT_INJECTION_BLOCKED")
    return IntentResult(
        normalized=normalized,
        flags=tuple(flags),
        out_of_scope=out_of_scope,
        requests_action=requests_action,
        requests_recommendation=requests_recommendation,
        asks_price=asks_price,
        asks_policy=asks_policy,
        prompt_injection=prompt_injection,
    )
