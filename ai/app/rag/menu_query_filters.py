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
        # Cách khách nói ngắn gọn hơn, và bản tiếng Anh.
        "gia re",
        "mon re",
        "gia thap",
        "re nhat",
        "thap nhat",
        "cheap",
        "affordable",
        "inexpensive",
        "budget friendly",
    ),
    "2 3 nguoi": (
        "hai nguoi",
        "ba khach",
        "2 den 3 nguoi",
        "cap doi",
        "ban ba nguoi",
    ),
    # Nhãn bữa ăn, mức giá và đối tượng đã có trên thực đơn (129 + 90 + 71 nhãn)
    # nhưng chỉ khớp khi khách gõ đúng tên nhãn. Khách viết "buổi tối", "món rẻ",
    # "ông bà" thì không khớp gì, nên các nhãn đó nằm không.
    "trua": ("buoi trua", "bua trua", "an trua", "lunch", "business lunch", "midday"),
    "sang": ("buoi sang", "bua sang", "an sang", "breakfast", "morning"),
    "an khuya": ("khuya", "dem muon", "late night", "midnight"),
    "cao cap": ("sang trong", "dat tien", "premium", "high end", "luxury", "fine dining"),
    "nguoi gia": (
        "ong ba",
        "nguoi cao tuoi",
        "cao tuoi",
        "de nhai",
        "mem de an",
        "elderly",
        "senior",
        "grandparent",
    ),
    "gia dinh": ("ca nha", "family", "family meal"),
    "nhom ban": ("nhom", "dong nguoi", "nhieu nguoi", "group", "party of", "team"),
}

# The menu dataset stores ASCII tags.  These two tags collide with common
# Vietnamese words after diacritic stripping (tôi -> toi, mức -> muc), so they
# are only hard-filtered when the user writes the intended accented entity.
TAG_SURFACE_QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    # CHƯA GIẢI QUYẾT: nhãn `toi` nhập nhằng và thực đơn không có tài liệu định
    # nghĩa nhãn. 64/91 món mang nhãn này — hợp với "tối" (bộ bữa ăn sang 22 /
    # trua 39 / toi 64 / an khuya 4 liền mạch) và cũng hợp với "tỏi" (gia vị phổ
    # biến nhất). Chỉ 17% món có nhãn đó nhắc tỏi trong mô tả, nhưng mô tả ngắn
    # nên không kết luận được. Giữ nguyên cách hiểu "tỏi" như mã gốc cho tới khi
    # chủ dữ liệu xác nhận; đoán sai chiều nào cũng làm một loại câu hỏi trả sai.
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
PAYMENT_QUERY_TERMS = (
    "tra bang",
    "tra tien",
    "thanh toan",
    "quet the",
    "chuyen khoan",
    "tien mat",
    "hoa don",
    "bill",
)

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


# Phrases that mean the food is for a young child. "be"/"chau"/"con" alone are
# too ambiguous in Vietnamese ("bé" also = small, "con" also = classifier), so
# they only count next to an eating/age word.
_CHILD_CONTEXT_TERMS: tuple[str, ...] = (
    "tre em",
    "tre nho",
    "tre con",
    "em be",
    "cho be",
    "be an",
    "chau an",
    "con an",
    "cho chau",
    # "cho tre" đứng cạnh "cho be"/"cho chau" trong mọi cách nói tự nhiên nhưng bị
    # thiếu, nên "ít cay cho trẻ" không kích hoạt bộ lọc an toàn cho trẻ em.
    "cho tre",
    "tre an",
    "kid",
    "child",
    "toddler",
    "for my son",
    "for my daughter",
)

_CHILD_AGE_PATTERN = re.compile(r"\b(\d{1,2})\s*tuoi\b")
# Above this age the general menu is appropriate; below it, only dishes the
# catalogue marks as child-friendly should be suggested.
CHILD_AGE_CEILING = 12


def has_child_dining_context(query: str) -> bool:
    """True when the guest is asking what a young child should eat.

    Recommending an adult dish (rare beef, strong spice, bones, whole nuts) to a
    toddler is a real safety problem, so this is deliberately conservative: an
    explicit young age ("bé 3 tuổi") or an unambiguous child phrase is required.
    """
    normalized = normalize_query_text(query)
    age_match = _CHILD_AGE_PATTERN.search(normalized)
    if age_match and int(age_match.group(1)) <= CHILD_AGE_CEILING:
        return True
    return any(term in normalized for term in _CHILD_CONTEXT_TERMS)


def infer_child_unsuitable_menu_item_ids(
    menu_items: Sequence[dict[str, Any]],
) -> set[str]:
    """Exclude everything the catalogue does not mark as child-friendly.

    Fail-closed on purpose: an unlabelled dish is treated as unsuitable rather
    than assumed safe, mirroring how allergen exclusion errs on the safe side.
    """
    excluded: set[str] = set()
    for item in menu_items:
        item_id = str(item.get("id") or item.get("menu_item_id") or "").strip()
        if not item_id:
            continue
        tags = item.get("tags") or []
        tag_text = normalize_query_text(
            " ".join(str(tag) for tag in tags) if not isinstance(tags, str) else tags
        )
        if "tre em" not in tag_text and "tre nho" not in tag_text:
            excluded.add(item_id)
    return excluded


# Nhãn khai báo trên thực đơn — tín hiệu có thẩm quyền, không phải suy luận.
ALLERGEN_DECLARED_TAGS: dict[str, tuple[str, ...]] = {
    "seafood": ("co hai san",),
    "peanut": ("co dau phong",),
    "gluten": ("co gluten",),
    "egg": ("co trung",),
    "dairy": ("co sua",),
    "soy": ("co dau nanh",),
}

# Term mà dạng rút dấu trùng với từ khác thật sự có trong thực đơn này. Sáu trường
# hợp đo được, mỗi trường hợp loại oan ít nhất một món:
#   trứng (egg)    vs  miền Trung, tầm trung        43/91 món bị loại, chỉ 7 đúng
#   bơ    (butter) vs  bò (thịt bò)                 Phở bò, Bún bò Huế, Cơm bò...
#   cua   (crab)   vs  của, cửa                     "phiên bản chay của Bún bò Huế"
#   mực   (squid)  vs  mức                          "chọn mức đường" (trà sữa)
#   lạc   (peanut) vs  lắc                          "bò lúc lắc"
#   sò    (clam)   vs  so, số                       -
ALLERGEN_AMBIGUOUS_TERMS: dict[str, tuple[str, ...]] = {
    "trung": ("trứng",),
    "bo": ("bơ",),
    "cua": ("cua",),
    "muc": ("mực",),
    "lac": ("lạc",),
    "so": ("sò",),
}

# "Không thịt, không hải sản" là lời khẳng định KHÔNG chứa, nhưng khớp chuỗi đọc nó
# thành có: Gỏi cuốn chay từng bị loại khỏi thực đơn cho người dị ứng hải sản vì
# chính câu nói nó không có hải sản.
_ALLERGEN_NEGATIONS: tuple[str, ...] = ("khong ", "ko ", "no ", "without ", "free of ")


def infer_allergen_excluded_menu_item_ids(
    allergens: Sequence[str],
    menu_items: Sequence[dict[str, Any]],
) -> set[str]:
    """Exclude items that declare, or read as containing, a detected allergen.

    The catalogue carries explicit `co <allergen>` labels, and those are the
    authoritative signal.  Matching the allergen's *name* against diacritic-
    stripped text is only a supplement, because the stripped forms collide: an egg
    allergy matched `trung` inside "miền Trung" and "tầm trung" and excluded 43 of
    91 dishes when only 7 carry `co trung`, and a dairy allergy matched `bo`
    ("bơ", butter) against "bò" (beef) and took out Phở bò, Bún bò Huế, Cơm bò lúc
    lắc and Lẩu bò nhúng giấm.  84% of the egg exclusions were wrong.

    Terms listed as ambiguous are matched against accented text instead, and the
    rest keep the stripped match so genuine mentions in free-text descriptions are
    still caught.
    """

    declared_tags = {
        tag
        for allergen in allergens
        for tag in ALLERGEN_DECLARED_TAGS.get(str(allergen), ())
    }
    plain_patterns = [
        re.compile(rf"\b{re.escape(term)}\b")
        for allergen in allergens
        for term in ALLERGEN_ITEM_TERMS.get(str(allergen), ())
        if term not in ALLERGEN_AMBIGUOUS_TERMS
    ]
    accented_patterns = [
        re.compile(rf"\b{re.escape(accented)}\b")
        for allergen in allergens
        for term in ALLERGEN_ITEM_TERMS.get(str(allergen), ())
        if term in ALLERGEN_AMBIGUOUS_TERMS
        for accented in ALLERGEN_AMBIGUOUS_TERMS[term]
    ]
    if not declared_tags and not plain_patterns and not accented_patterns:
        return set()

    excluded: set[str] = set()
    for item in menu_items:
        item_id = _item_id(item)
        if not item_id:
            continue
        tags = [str(tag) for tag in _tags(item)]
        if declared_tags & {normalize_query_text(tag) for tag in tags}:
            excluded.add(item_id)
            continue
        parts = [
            str(item.get("name") or ""),
            str(item.get("description") or ""),
            " ".join(tags),
        ]
        haystack = normalize_query_text(" ".join(parts))
        if any(
            _mentions_allergen(haystack, pattern) for pattern in plain_patterns
        ):
            excluded.add(item_id)
            continue
        if accented_patterns:
            accented = " ".join(parts).casefold()
            if any(
                _mentions_allergen(accented, pattern) for pattern in accented_patterns
            ):
                excluded.add(item_id)
    return excluded


def _mentions_allergen(haystack: str, pattern: re.Pattern[str]) -> bool:
    """True only for a mention that is not immediately negated."""
    for match in pattern.finditer(haystack):
        window = haystack[max(0, match.start() - 12) : match.start()]
        if any(negation in window for negation in _ALLERGEN_NEGATIONS):
            continue
        return True
    return False


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
    if normalized_alias == "tra" and any(
        _contains_phrase(normalized_query, term) for term in PAYMENT_QUERY_TERMS
    ):
        return False
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


# Nhãn độ cay trên thực đơn, xếp từ nhẹ tới nặng. 88 món có một trong các nhãn này.
SPICE_TAG_ORDER: tuple[str, ...] = ("khong cay", "cay nhe", "cay vua", "cay", "rat cay")

# Mức khách nêu -> các nhãn được coi là thoả. Khách xin "ít cay" vẫn nhận món không
# cay, vì không cay thoả yêu cầu ít cay; ngược lại thì không.
SPICE_LEVEL_TO_TAGS: dict[str, tuple[str, ...]] = {
    "none": ("khong cay",),
    "mild": ("khong cay", "cay nhe"),
    "medium": ("cay nhe", "cay vua"),
    "hot": ("cay vua", "cay", "rat cay"),
}


def filter_items_by_spice(
    menu_items: Sequence[dict[str, Any]],
    spice: str | None,
) -> list[dict[str, Any]]:
    """Giữ các món khớp mức cay khách nêu.

    Ràng buộc `spice` đã được trích từ câu hỏi, ghi vào bộ nhớ phiên và dùng trong
    phân loại ý định từ trước — nhưng chưa có chỗ nào dùng nó để lọc thực đơn. Nên
    câu "Món nào không cay?" không được lọc gì cả, dù 68 món mang nhãn `khong cay`.

    Món chưa ghi nhãn độ cay được **giữ lại**: thiếu nhãn là thiếu dữ liệu, không
    phải bằng chứng món đó cay. Với dị nguyên thì fail-closed là đúng, còn độ cay
    không gây nguy hiểm — loại bỏ món chưa gán nhãn chỉ làm khách mất lựa chọn.
    """
    if not spice or spice == "unknown":
        return list(menu_items)
    allowed = SPICE_LEVEL_TO_TAGS.get(str(spice))
    if not allowed:
        return list(menu_items)

    kept: list[dict[str, Any]] = []
    for item in menu_items:
        tags = {normalize_query_text(str(tag)) for tag in _tags(item)}
        recorded = tags & set(SPICE_TAG_ORDER)
        if not recorded or recorded & set(allowed):
            kept.append(item)
    return kept
