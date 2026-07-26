from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from app.rag.menu_item_kind import ItemKind, classify_menu_item_kind, detect_requested_item_kind
from app.rag.retriever import RetrievedChunk
from app.rag.vietnamese_normalizer import normalize_query_text

CATEGORY_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "bia ruou": ("do uong co con", "co con", "bia", "ruou", "cocktail"),
}

TAG_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "binh dan": (
        "gia tiet kiem",
        "ngan sach thap",
        "gia mem",
        "chi tieu vua phai",
    ),
    "2 3 nguoi": (
        "hai nguoi",
        "ba khach",
        "2 den 3 nguoi",
        "cap doi",
        "ban ba nguoi",
    ),
}

# The menu dataset stores ASCII tags.  These two tags collide with common
# Vietnamese words after diacritic stripping (tôi -> toi, mức -> muc), so they
# are only hard-filtered when the user writes the intended accented entity.
TAG_SURFACE_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "toi": ("tỏi",),
    "muc": ("mực",),
}
AMBIGUOUS_ASCII_TAGS = frozenset(TAG_SURFACE_QUERY_ALIASES)

# ``trả`` (pay) and ``trà`` (tea) both normalize to ``tra``.  Preserve the
# original surface form for this category alias so policy questions never
# acquire an irrelevant tea-only evidence scope.
SEMANTIC_SURFACE_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "tra": ("trà", "tra"),
}

ALCOHOL_CATEGORY_IDS = frozenset({"cat_alcohol"})
SWEET_CATEGORY_IDS = frozenset(
    {
        "cat_tráng_miệng",
        "cat_trái_cây_tươi",
        "cat_nước_ép_sinh_tố",
    }
)
SWEET_TAG_MARKERS = frozenset({"ngot", "trang mieng", "che", "sinh to", "nuoc ep"})

REJECTION_TERMS = (
    "bo qua",
    "khong thich",
    "dung lap lai",
    "loai",
    "mon ngot",
    "ngot",
    "khong hop",
)
HEALTHY_TERMS = ("healthy", "an lanh", "it calo", "thanh", "diet")

ALLERGEN_ITEM_TERMS: dict[str, tuple[str, ...]] = {
    "seafood": (
        "hai san",
        "tom",
        "cua",
        "muc",
        "oc",
        "ngheu",
        "so",
        "seafood",
        "shrimp",
        "crab",
        "squid",
        "clam",
    ),
    "peanut": ("dau phong", "lac", "peanut"),
    "gluten": ("bot mi", "gluten", "wheat"),
    "egg": ("trung", "egg"),
    "dairy": ("sua", "pho mai", "cheese", "milk", "bo"),
    "soy": ("dau nanh", "dau hu", "tofu", "soy"),
}

ALLERGY_CONTEXT_TERMS = (
    "di ung",
    "allerg",
    "tranh",
    "khong an",
    "khong co",
    "khong dung",
    "an toan",
    "avoid",
    "safe",
)


def has_allergy_avoidance_context(query: str) -> bool:
    """True when the query signals allergy or avoidance intent (vs plain browsing)."""

    normalized = normalize_query_text(query)
    return any(term in normalized for term in ALLERGY_CONTEXT_TERMS)


def infer_allergen_excluded_menu_item_ids(
    allergens: Sequence[str],
    menu_items: Sequence[dict[str, Any]],
) -> set[str]:
    """Exclude items whose name/description/tags mention a detected allergen."""

    patterns = [
        re.compile(rf"\b{re.escape(term)}\b")
        for allergen in allergens
        for term in ALLERGEN_ITEM_TERMS.get(str(allergen), ())
    ]
    if not patterns:
        return set()

    excluded: set[str] = set()
    for item in menu_items:
        item_id = _item_id(item)
        if not item_id:
            continue
        haystack = normalize_query_text(
            " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("description") or ""),
                    " ".join(str(tag) for tag in _tags(item)),
                ]
            )
        )
        if any(pattern.search(haystack) for pattern in patterns):
            excluded.add(item_id)
    return excluded


def infer_allowed_menu_item_ids(
    query: str,
    menu_items: Sequence[dict[str, Any]],
    *,
    requested_item_kind: ItemKind | None = None,
) -> set[str] | None:
    """Return strict allowed ids when query names a menu category; else None."""

    normalized_query = normalize_query_text(query)
    if not normalized_query:
        return None

    available = [item for item in menu_items if _item_id(item)]
    if not available:
        return None

    if requested_item_kind is None:
        requested_item_kind = detect_requested_item_kind(query)

    semantic_item_matches = _matched_semantic_item_ids(query, normalized_query, available)
    category_matches = _matched_categories(normalized_query, available)
    tag_matches = _matched_tags(query, normalized_query, available)

    if semantic_item_matches:
        allowed = semantic_item_matches
    elif category_matches:
        allowed = {
            _item_id(item)
            for item in available
            if normalize_query_text(str(item.get("category_name") or "")) in category_matches
        }
    elif tag_matches:
        allowed = {
            _item_id(item)
            for item in available
            if any(normalize_query_text(str(tag)) in tag_matches for tag in _tags(item))
        }
    else:
        return None

    allowed = _apply_kind_filter(allowed, available, requested_item_kind)
    return allowed or None


def infer_excluded_menu_item_ids(
    query: str,
    menu_items: Sequence[dict[str, Any]],
) -> set[str]:
    """Exclude sweet/heavy items when user rejects prior sweet picks for healthy options."""

    normalized_query = normalize_query_text(query)
    if not any(term in normalized_query for term in REJECTION_TERMS):
        return set()
    if not any(term in normalized_query for term in HEALTHY_TERMS):
        return set()

    excluded: set[str] = set()
    for item in menu_items:
        item_id = _item_id(item)
        if not item_id:
            continue
        category_id = str(item.get("category_id") or "").strip()
        if category_id in SWEET_CATEGORY_IDS:
            excluded.add(item_id)
            continue
        tags = {normalize_query_text(str(tag)) for tag in _tags(item)}
        if tags & SWEET_TAG_MARKERS:
            excluded.add(item_id)
    return excluded


def filter_menu_retrieval_results(
    query: str,
    results: Sequence[RetrievedChunk],
    menu_items: Sequence[dict[str, Any]],
) -> list[RetrievedChunk]:
    """Apply the same category/rejection filters used in live menu grounding."""

    allowed = infer_allowed_menu_item_ids(query, menu_items)
    excluded = infer_excluded_menu_item_ids(query, menu_items)
    if allowed is None and not excluded:
        return list(results)

    filtered: list[RetrievedChunk] = []
    seen: set[str] = set()
    for result in results:
        source = result.chunk.source
        if source in seen:
            continue
        if allowed is not None and source not in allowed:
            continue
        if source in excluded:
            continue
        seen.add(source)
        filtered.append(result)

    if allowed is not None:
        allowed_ranked = [
            result
            for result in filtered
            if result.chunk.source in allowed
        ]
        if allowed_ranked:
            filtered = allowed_ranked

    if len(filtered) >= len(results[: max(1, min(len(results), 10))]):
        return filtered[: len(results)]

    for result in results:
        source = result.chunk.source
        if source in seen:
            continue
        if allowed is not None and source not in allowed:
            continue
        if source in excluded:
            continue
        seen.add(source)
        filtered.append(result)
    return filtered[: len(results)]


def menu_document_to_item(document: Any, *, document_id: str | None = None) -> dict[str, Any]:
    metadata = document.metadata
    return {
        "id": document_id or metadata.menu_item_id,
        "category_id": metadata.category_id,
        "category_name": metadata.category_name,
        "tags": list(metadata.tags),
        "is_available": metadata.is_available,
    }


def _matched_categories(normalized_query: str, available: Sequence[dict[str, Any]]) -> set[str]:
    available_categories = {
        normalize_query_text(str(item.get("category_name") or "")) for item in available
    }
    matches = {
        normalize_query_text(str(item.get("category_name") or ""))
        for item in available
        if _is_meaningful(item.get("category_name"))
        and _contains_phrase(normalized_query, normalize_query_text(str(item.get("category_name") or "")))
    }
    matches.update(
        category
        for category, aliases in CATEGORY_QUERY_ALIASES.items()
        if category in available_categories
        and any(_contains_phrase(normalized_query, alias) for alias in aliases)
    )
    return {match for match in matches if match}


def _matched_semantic_item_ids(
    query: str,
    normalized_query: str,
    available: Sequence[dict[str, Any]],
) -> set[str]:
    """Prefer the named dish family over its broader menu category.

    ``Phở & Bún`` is one catalog category, but a customer asking for ``phở``
    should never receive a bún or unrelated dish merely because both share a
    category.  Reuse the constraint extractor aliases so semantic routing and
    retrieval use the same vocabulary.
    """

    from app.rag.constraint_extractor import CATEGORY_ALIASES

    matched_aliases = {
        normalized_alias
        for aliases in CATEGORY_ALIASES.values()
        for alias in aliases
        for normalized_alias in (normalize_query_text(alias),)
        if _semantic_alias_matches(query, normalized_query, normalized_alias)
    }
    if not matched_aliases:
        return set()

    max_specificity = max(len(alias.split()) for alias in matched_aliases)
    most_specific_aliases = {
        alias
        for alias in matched_aliases
        if len(alias.split()) == max_specificity
    }
    return {
        _item_id(item)
        for item in available
        if any(
            _contains_phrase(
                normalize_query_text(str(item.get("name") or "")),
                alias,
            )
            for alias in most_specific_aliases
        )
    }


def _semantic_alias_matches(
    query: str,
    normalized_query: str,
    normalized_alias: str,
) -> bool:
    surface_aliases = SEMANTIC_SURFACE_QUERY_ALIASES.get(normalized_alias)
    if surface_aliases:
        surface_query = _surface_text(query)
        return any(
            _contains_phrase(surface_query, _surface_text(alias))
            for alias in surface_aliases
        )
    return _contains_phrase(normalized_query, normalized_alias)


def _matched_tags(
    query: str,
    normalized_query: str,
    available: Sequence[dict[str, Any]],
) -> set[str]:
    available_tags = {
        normalize_query_text(str(tag))
        for item in available
        for tag in _tags(item)
        if _is_meaningful(tag)
    }
    alias_matches = [
        (tag, len(alias.split()))
        for tag, aliases in TAG_QUERY_ALIASES.items()
        if tag in available_tags
        for alias in aliases
        if _contains_phrase(normalized_query, alias)
    ]
    surface_query = _surface_text(query)
    alias_matches.extend(
        (tag, len(_surface_text(alias).split()))
        for tag, aliases in TAG_SURFACE_QUERY_ALIASES.items()
        if tag in available_tags
        for alias in aliases
        if _contains_phrase(surface_query, _surface_text(alias))
    )
    if alias_matches:
        max_specificity = max(specificity for _, specificity in alias_matches)
        return {
            tag
            for tag, specificity in alias_matches
            if specificity == max_specificity
        }

    direct_matches = [
        (tag, len(tag.split()))
        for tag in available_tags
        if tag not in AMBIGUOUS_ASCII_TAGS
        and _contains_phrase(normalized_query, tag)
    ]
    if not direct_matches:
        return set()
    max_specificity = max(specificity for _, specificity in direct_matches)
    return {
        tag
        for tag, specificity in direct_matches
        if specificity == max_specificity
    }


def _apply_kind_filter(
    allowed_ids: set[str],
    available: Sequence[dict[str, Any]],
    requested_item_kind: ItemKind | None,
) -> set[str]:
    if requested_item_kind is None:
        return allowed_ids

    items_by_id = {_item_id(item): item for item in available}
    kind_filtered = {
        item_id
        for item_id in allowed_ids
        if item_id in items_by_id
        and classify_menu_item_kind(items_by_id[item_id]) == requested_item_kind
    }
    if kind_filtered:
        return kind_filtered

    return {
        _item_id(item)
        for item in available
        if classify_menu_item_kind(item) == requested_item_kind
    }


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("menu_item_id") or "").strip()


def _tags(item: dict[str, Any]) -> list[str]:
    raw = item.get("tags") or []
    return [str(tag) for tag in raw if str(tag).strip()]


def _is_meaningful(value: Any) -> bool:
    return bool(str(value or "").strip())


def _contains_phrase(query: str, phrase: str) -> bool:
    return bool(phrase) and f" {phrase} " in f" {query} "


def _surface_text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", str(value or "").casefold())
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))
