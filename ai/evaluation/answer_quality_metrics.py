# -*- coding: utf-8 -*-
"""Score the answer, not the retrieval.

Why this exists
---------------
``run_golden_chat_eval.py`` scores which chunks came back and which menu ids were
cited.  Both matter, but neither can see whether the guest got a usable answer.
Every guest-visible fix measured in this round was invisible to it, and one scored
as a regression:

    stopped serving brand-voice templates to guests      unchanged
    48 wrong allergen exclusions removed                 unchanged
    allergy answered deterministically, 0/13 -> 13/13    chunk_hit_rate fell
    dishes over the stated budget, 3/7 -> 0/7            unchanged

A metric that cannot distinguish those from doing nothing cannot be used to steer
answer quality.  The checks here are deliberately objective — no human panel and no
model-as-judge — so they can run on every commit:

* **constraint respect** the answer must not offer something the guest ruled out: a
  dish over their budget, a spice level they declined, an allergen they declared,
  the wrong item kind, an adult dish for a small child.
* **grounding** every dish named must exist in the live catalogue, and any price
  quoted must be that dish's price.
* **actionability** a dish the guest could order should come with a cart card.
* **containment** no guidance text, HTML comment or forbidden safety claim.
* **deflection** did it answer, or ask a question back?

Deflection is reported, never scored as failure: asking back is right when the
question is genuinely ambiguous.  It is a rate to watch, not a gate to pass.
"""
from __future__ import annotations

import re
from typing import Any, Sequence

from app.rag.menu_item_kind import classify_menu_item_kind, detect_requested_item_kind
from app.rag.menu_query_filters import (
    SPICE_LEVEL_TO_TAGS,
    SPICE_TAG_ORDER,
    has_child_dining_context,
    infer_allergen_excluded_menu_item_ids,
    infer_child_unsuitable_menu_item_ids,
)
from app.rag.vietnamese_normalizer import normalize_query_text

# Text that only ever appears in sections written for the assistant.  One of these
# reaching a guest means the audience separation has broken somewhere.
GUIDANCE_MARKERS: tuple[str, ...] = (
    "Danh sách món: tên, giá",
    "min_support",
    "Lưu Ý Cho AI",
    "<!--",
)

# Claims knowledge-base/allergy-disclaimer.md forbids outright.
FORBIDDEN_SAFETY_CLAIMS: tuple[str, ...] = (
    "an toàn 100",
    "chắc chắn không",
    "tách riêng hoàn toàn",
    "100% safe",
)

DEFLECTION_MARKERS: tuple[str, ...] = (
    "bạn muốn",
    "bạn thích",
    "cho mình biết",
    "bạn đang hỏi",
    "bạn cần",
    "would you like",
    "could you tell",
)

AVOID_LIST_MARKERS: tuple[str, ...] = (
    "nên bỏ qua",
    "nên tránh",
    "cần tránh",
    "ones to skip",
)

_PRICE_PATTERN = re.compile(r"(\d[\d.,]*)\s*(?:đ|vnd)\b", re.IGNORECASE)


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("menu_item_id") or "").strip()


def _price(item: dict[str, Any]) -> int | None:
    value = item.get("price_vnd") or item.get("price")
    return int(value) if isinstance(value, (int, float)) else None


def cited_menu_ids(response: dict[str, Any]) -> list[str]:
    return [
        str(entry.get("menu_item_id")).strip()
        for entry in (response.get("evidence") or [])
        if entry.get("menu_item_id")
    ]


def reads_as_avoid_list(response: dict[str, Any]) -> bool:
    text = str(response.get("content") or "").casefold()
    return any(marker in text for marker in AVOID_LIST_MARKERS)


def score_constraint_respect(
    query: str,
    constraints: dict[str, Any],
    response: dict[str, Any],
    menu_items: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Which of the guest's stated constraints the cited dishes violate."""
    by_id = {_item_id(item): item for item in menu_items if _item_id(item)}
    cited = [by_id[i] for i in cited_menu_ids(response) if i in by_id]
    violations: dict[str, list[str]] = {}

    budget = constraints.get("budget_vnd")
    if budget:
        over = [
            str(item.get("name")) for item in cited if (_price(item) or 0) > int(budget)
        ]
        if over:
            violations["budget"] = over

    allowed_spice = SPICE_LEVEL_TO_TAGS.get(str(constraints.get("spice") or ""))
    if allowed_spice:
        wrong = []
        for item in cited:
            tags = {normalize_query_text(str(t)) for t in (item.get("tags") or [])}
            recorded = tags & set(SPICE_TAG_ORDER)
            if recorded and not recorded & set(allowed_spice):
                wrong.append(str(item.get("name")))
        if wrong:
            violations["spice"] = wrong

    allergens = constraints.get("allergens") or []
    if allergens:
        unsafe_ids = infer_allergen_excluded_menu_item_ids(allergens, menu_items)
        offered = {
            str(action.get("menu_item_id"))
            for action in (response.get("suggested_cart_actions") or [])
        }
        # Naming a dish so the guest can avoid it is correct.  Offering it to order
        # is not, whatever the wording around it.
        offered_unsafe = [
            str(item.get("name"))
            for item in cited
            if _item_id(item) in unsafe_ids and _item_id(item) in offered
        ]
        if offered_unsafe:
            violations["allergen_offered"] = offered_unsafe
        elif not reads_as_avoid_list(response):
            cited_unsafe = [
                str(item.get("name")) for item in cited if _item_id(item) in unsafe_ids
            ]
            if cited_unsafe:
                violations["allergen_cited"] = cited_unsafe

    requested_kind = detect_requested_item_kind(query)
    if requested_kind:
        wrong_kind = [
            str(item.get("name"))
            for item in cited
            if classify_menu_item_kind(item) != requested_kind
        ]
        if wrong_kind:
            violations["item_kind"] = wrong_kind

    if has_child_dining_context(query):
        unsuitable = infer_child_unsuitable_menu_item_ids(menu_items)
        for_child = [
            str(item.get("name")) for item in cited if _item_id(item) in unsuitable
        ]
        if for_child:
            violations["child_suitability"] = for_child

    return {
        "cited_count": len(cited),
        "violations": violations,
        "respected": not violations,
    }


def score_grounding(
    response: dict[str, Any],
    menu_items: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """A dish named must exist, and a price quoted must be that dish's price."""
    by_id = {_item_id(item): item for item in menu_items if _item_id(item)}
    content = str(response.get("content") or "")
    ids = cited_menu_ids(response)
    cited = [by_id[i] for i in ids if i in by_id]

    unknown = [i for i in ids if i not in by_id]
    real_prices = {
        f"{_price(item):,}".replace(",", ".")
        for item in cited
        if _price(item) is not None
    }
    # A price gap between two cited dishes is a legitimate figure that matches no
    # dish's price.  Without this the five comparison cases all scored as ungrounded
    # for correctly saying "thấp hơn 5.000đ" — a false positive in this metric, not
    # a fault in the answer.
    real_prices |= {
        f"{abs(a - b):,}".replace(",", ".")
        for a in (p for p in map(_price, cited) if p is not None)
        for b in (p for p in map(_price, cited) if p is not None)
        if a != b
    }
    quoted = {match.group(1) for match in _PRICE_PATTERN.finditer(content)}
    unverifiable = sorted(quoted - real_prices) if cited else []

    return {
        "unknown_menu_ids": unknown,
        "unverifiable_prices": unverifiable,
        "grounded": not unknown and not unverifiable,
    }


def score_containment(response: dict[str, Any]) -> dict[str, Any]:
    content = str(response.get("content") or "")
    leaked = [marker for marker in GUIDANCE_MARKERS if marker in content]
    folded = content.casefold()
    forbidden = [
        claim for claim in FORBIDDEN_SAFETY_CLAIMS if claim.casefold() in folded
    ]
    return {
        "leaked_guidance": leaked,
        "forbidden_claims": forbidden,
        "contained": not leaked and not forbidden,
    }


def score_actionability(response: dict[str, Any]) -> dict[str, Any]:
    cited = cited_menu_ids(response)
    cards = [
        str(action.get("menu_item_id"))
        for action in (response.get("suggested_cart_actions") or [])
    ]
    if reads_as_avoid_list(response):
        # An avoid list is correct precisely by carrying no cards.
        return {"cited": len(cited), "cards": len(cards), "actionable": not cards}
    if len(cited) == 1:
        # A question about one named dish — "Calories bún bò Huế?" — is answered by
        # the figure.  Requiring a cart card there marked a correct answer as
        # unusable; a card belongs on an offer, not on a lookup.
        return {"cited": len(cited), "cards": len(cards), "actionable": True}
    return {
        "cited": len(cited),
        "cards": len(cards),
        "actionable": not cited or bool(cards),
    }


def looks_like_deflection(response: dict[str, Any]) -> bool:
    """Asked a question back *instead of* answering.

    Reported, never scored as failure: asking back is the right move when the
    question is genuinely ambiguous.

    An answer that names dishes and then offers to go further — "...  Bạn muốn thêm
    gì không?" — has answered.  Counting that as a deflection put the rate at 43%
    when many of those replies listed dishes with prices; a deflection is a reply
    that offers nothing to act on.
    """
    if cited_menu_ids(response):
        return False
    content = str(response.get("content") or "")
    if "?" not in content:
        return False
    folded = content.casefold()
    return any(marker in folded for marker in DEFLECTION_MARKERS)


def score_answer(
    query: str,
    constraints: dict[str, Any],
    response: dict[str, Any],
    menu_items: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    constraint = score_constraint_respect(query, constraints, response, menu_items)
    grounding = score_grounding(response, menu_items)
    containment = score_containment(response)
    actionability = score_actionability(response)
    return {
        "constraint": constraint,
        "grounding": grounding,
        "containment": containment,
        "actionability": actionability,
        "deflected": looks_like_deflection(response),
        "usable": (
            constraint["respected"]
            and grounding["grounded"]
            and containment["contained"]
            and actionability["actionable"]
        ),
    }
