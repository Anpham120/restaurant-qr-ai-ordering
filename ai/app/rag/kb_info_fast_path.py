from __future__ import annotations

import re
from typing import Any

from app.rag.conversation_policy import (
    _is_context_only_follow_up,
    _is_more_dishes_request,
    _party_size_from_history,
    _was_recommendation_thread,
)
from app.rag.policy_faq_fast_path import try_wifi_policy_fast_path
from app.rag.guardrails import detect_guardrail_flags
from app.rag.knowledge_base import stable_chunk_id
from app.rag.retriever import RetrievalFilters, Retriever
from app.rag.vietnamese_normalizer import normalize_query_text


INFO_INTENTS = frozenset(
    {
        "restaurant_info",
        "payment",
        "service",
        "promotion",
        "general",
        "ask_price",
        "dietary",
        "occasion",
        "kids_elderly",
    }
)

JUNK_INFO_SOURCES = frozenset({"data-mining-insights.md", "combo-pairing.md"})

INTENT_PREFERRED_SOURCES: dict[str, tuple[str, ...]] = {
    "restaurant_info": ("faq.md", "restaurant-info.md", "service-guide.md"),
    "payment": ("payment-methods.md", "faq.md", "ordering-policy.md"),
    "service": ("service-guide.md", "faq.md", "restaurant-info.md"),
    "promotion": ("seasonal-promotion.md", "faq.md", "ordering-policy.md"),
    "general": ("faq.md", "restaurant-info.md", "service-guide.md"),
    "ask_price": ("menu.md", "faq.md"),
    "dietary": ("allergy-dietary.md", "vegan-halal-keto.md", "ingredient-nutrition.md", "faq.md", "menu.md"),
    "occasion": ("faq.md", "occasion-dining.md", "combo-pairing.md"),
    "kids_elderly": ("kids-elderly.md", "faq.md"),
}

_QUERY_STOPWORDS = frozenset(
    {
        "la",
        "gi",
        "co",
        "khong",
        "nao",
        "the",
        "nhu",
        "toi",
        "minh",
        "ban",
        "nha",
        "hang",
        "duoc",
        "hay",
        "giup",
        "voi",
        "tai",
        "con",
    }
)

# Vietnamese domain tokens are often 2 chars (xe, mo, com) but carry FAQ intent.
_SHORT_DOMAIN_TOKENS = frozenset({"xe", "mo", "an", "com", "bo", "ga", "nuoc", "bia"})

# Map normalized query phrases -> substring expected in faq.md section title.
# English phrasings are listed alongside the Vietnamese ones: guests do ask in
# English ("payment methods?", "opening hours?"), and without these the query
# misses the deterministic path and falls through to the LLM, which then tends
# to abstain even though the KB has the answer.
_FAQ_TOPIC_ROUTES: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        (
            "gio mo cua", "mo cua", "dong cua", "gio hoat dong",
            "opening hour", "opening time", "open time", "closing time", "business hour",
        ),
        "gio mo cua",
    ),
    (
        (
            "gui xe", "dau xe", "do xe", "bai xe", "cho dau", "cho gui", "gui oto",
            "parking", "car park",
        ),
        "dau xe",
    ),
    (
        (
            "thanh toan", "vietqr", "tien mat", "chuyen khoan",
            "payment method", "payment option", "how to pay", "pay by card", "credit card",
        ),
        "thanh toan",
    ),
    (("dat ban", "dat truoc", "reservation", "book a table", "reserve a table"), "dat ban"),
    (("phong vip", "phong rieng", "private room", "vip room"), "phong rieng"),
    (("san thuong", "ngoai troi", "rooftop", "outdoor seating", "terrace"), "san thuong"),
    (("tre em", "tre con", "highchair", "high chair"), "tre em"),
    (("children portion", "child portion", "kids portion", "kid friendly"), "tre em"),
    (("office lunch", "quick lunch", "business lunch", "an trua nhanh"), "an trua nhanh"),
    (("sinh nhat", "tiec sinh nhat"), "sinh nhat"),
    (("dia chi", "o dau", "nam o dau"), "o dau"),
    (("mang ve", "takeaway", "take away", "giao hang", "delivery"), "mang ve"),
    (("huy don", "huy mon", "cancel order", "cancel my order"), "huy don"),
    (("cho mon", "thoi gian cho", "waiting time", "how long"), "thoi gian cho"),
    (("khuyen tat", "xe lan", "wheelchair", "accessible"), "khuyet tat"),
    (("nuoc mien phi", "nuoc loc", "free water"), "nuoc uong"),
    (("khuyen mai", "uu dai", "giam gia", "happy hour", "promotion", "discount"), "happy hour"),
    (("loi thanh toan", "thanh toan loi", "khong thanh toan duoc"), "thanh toan"),
)


def _normalize(text: str) -> str:
    return normalize_query_text(text)


# Tokens that indicate the query is about food/menu items, not policy/FAQ.
_FOOD_CONTEXT_TOKENS = frozenset({
    "pho", "bun", "com", "lau", "banh", "che", "goi", "cha",
    "ga", "bo", "heo", "tom", "ca", "muc", "oc", "cua",
    "nuoc", "tra", "bia", "cafe", "sinh", "mon", "an",
    "suon", "hai", "san", "trang", "mieng", "khai",
})

# Sources that should NOT be used for food-specific queries.
_POLICY_ONLY_SOURCES = frozenset({
    "ordering-policy.md", "payment-methods.md", "service-guide.md",
    "staff-escalation.md", "out-of-domain-redirect.md", "negative-examples.md",
    "brand-voice.md",
})


def _query_tokens(normalized_query: str) -> list[str]:
    tokens: list[str] = []
    for token in normalized_query.split():
        if token in _QUERY_STOPWORDS:
            continue
        if len(token) > 2 or token in _SHORT_DOMAIN_TOKENS:
            tokens.append(token)
    return tokens


def _expand_query_tokens(tokens: list[str]) -> set[str]:
    expanded = set(tokens)
    if "gui" in expanded:
        expanded.update({"dau", "xe"})
    if "gui" in expanded and "xe" in expanded:
        expanded.add("dau")
    if "dau" in expanded and "xe" in expanded:
        expanded.add("gui")
    if "mo" in expanded and "cua" in expanded:
        expanded.update({"mo", "cua", "gio"})
    return expanded


def _topic_needle_for_query(normalized_query: str) -> str | None:
    for query_terms, title_needle in _FAQ_TOPIC_ROUTES:
        if any(term in normalized_query for term in query_terms):
            return title_needle
    return None


def _topic_terms_for_query(normalized_query: str) -> tuple[str, ...] | None:
    for query_terms, _title_needle in _FAQ_TOPIC_ROUTES:
        if any(term in normalized_query for term in query_terms):
            return query_terms
    return None


def _find_faq_by_topic(normalized_query: str, candidates: list[Any]) -> Any | None:
    title_needle = _topic_needle_for_query(normalized_query)
    if title_needle is None:
        return None
    hits = [
        item
        for item in candidates
        if item.chunk.source == "faq.md" and title_needle in _normalize(item.chunk.title)
    ]
    if hits:
        return max(hits, key=lambda item: float(item.score))
    return None


def _find_topic_chunk_any_source(
    normalized_query: str,
    candidates: list[Any],
    preferred_sources: tuple[str, ...] = (),
) -> Any | None:
    """Fallback for topics whose real content lives outside faq.md (e.g. "Phòng
    VIP" under restaurant-info.md answers the "phong rieng" topic route, but
    its title uses the "phong vip" synonym, not the route's canonical needle).

    Only called once a topic is already confidently detected (see call site),
    so this widens WHERE we look, not WHETHER we're confident a real FAQ topic
    was asked — it does not loosen any confidence threshold.

    Candidates are ranked by how well their *content* answers the question, not
    just by title: a topic word in the title is a weak signal on its own (the
    payment topic matches "Xử Lý Sự Cố Thanh Toán", a troubleshooting section,
    while the section that actually lists the payment methods is titled
    "Tổng Quan"). Chunks whose body is only a `question_variants` marker are
    skipped — they render as an empty answer.
    """
    terms = _topic_terms_for_query(normalized_query)
    if terms is None:
        return None
    hits = [
        item
        for item in candidates
        if (
            any(term in _normalize(item.chunk.title) for term in terms)
            or any(term in _normalize(item.chunk.content) for term in terms)
        )
        and _format_chunk_answer(item.chunk.content)
    ]
    if not hits:
        return None
    # The topic words themselves carry no signal here — every candidate matched
    # the same topic — and _relevance_score's title bonus actively rewards
    # sections that merely repeat them ("Xử Lý Sự Cố Thanh Toán"), which are the
    # meta/troubleshooting ones.  Rank on the *remaining* query words instead:
    # for "thanh toan bang the" those are "bang"/"the", which pick the card
    # section over the troubleshooting section.
    topic_words = {word for term in terms for word in term.split()}
    distinguishing = [
        token for token in _query_tokens(normalized_query) if token not in topic_words
    ]

    def rank(item: Any) -> tuple[int, float, float]:
        content = _normalize(item.chunk.title) + " " + _normalize(item.chunk.content)
        matched = sum(1 for token in distinguishing if token in content)
        return (
            matched,
            _relevance_score(normalized_query, item, preferred_sources),
            float(item.score),
        )

    return max(hits, key=rank)


def _title_overlap(normalized_query: str, title: str) -> int:
    title_norm = _normalize(title)
    tokens = _expand_query_tokens(_query_tokens(normalized_query))
    if not tokens:
        return 0
    return sum(1 for token in tokens if token in title_norm)


def _is_food_query(tokens: list[str]) -> bool:
    """Return True when the query is primarily about food items, not policy/info."""
    return bool(set(tokens) & _FOOD_CONTEXT_TOKENS)


def _chunk_matches_query_context(normalized_query: str, item: Any, tokens: list[str]) -> bool:
    """Check if the chunk's domain is compatible with the query's actual intent.

    This prevents policy/FAQ chunks from answering food-specific questions
    and vice versa.  The check is intentionally conservative: when uncertain,
    it returns True (allowing the chunk through) so the LLM can decide.
    """
    if not tokens:
        return True

    # Food-specific query should not be answered by pure policy chunks
    if _is_food_query(tokens) and item.chunk.source in _POLICY_ONLY_SOURCES:
        # Exception: queries that also contain policy terms (e.g. "mon nao dat nhat")
        policy_terms = {"thanh", "toan", "hoa", "don", "huy", "gui", "qr"}
        if not (set(tokens) & policy_terms):
            return False

    return True


def _relevance_score(normalized_query: str, item: Any, preferred_sources: tuple[str, ...]) -> float:
    content = _normalize(item.chunk.content)
    title = _normalize(item.chunk.title)
    tokens = list(_expand_query_tokens(_query_tokens(normalized_query)))
    if not tokens:
        return 0.0

    # Context mismatch penalty: if chunk domain doesn't match query intent
    if not _chunk_matches_query_context(normalized_query, item, tokens):
        return 0.0

    overlap = sum(1 for token in tokens if token in content or token in title)
    # Require minimum token coverage — at least 40% of query tokens must appear
    coverage = overlap / len(tokens) if tokens else 0.0
    if coverage < 0.4:
        return overlap * 0.5  # Heavily penalise low-coverage matches

    source_bonus = 3.0 if item.chunk.source in preferred_sources else 0.0
    title_overlap = _title_overlap(normalized_query, item.chunk.title)
    title_bonus = 4.0 if title_overlap >= 2 else 0.0
    faq_title_bonus = 8.0 if item.chunk.source == "faq.md" and title_overlap >= 2 else 0.0
    retrieval_bonus = float(item.score) * 10.0
    return overlap + source_bonus + title_bonus + faq_title_bonus + retrieval_bonus


def _flatten_markdown_table(block: str) -> str | None:
    """Turn a "| header | ... |" markdown table into a natural sentence list.

    Raw pipe-table syntax reads as machine output in a chat bubble; customers
    should get the same facts as a normal sentence.
    """
    lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
    if len(lines) < 3 or not lines[0].startswith("|"):
        return None
    if not re.fullmatch(r"[\s|:\-]+", lines[1]):
        return None
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[str] = []
    for line in lines[2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        pairs = [
            f"{header} {value}" if header.casefold() in {"ngày", "tiện nghi"} else f"{header}: {value}"
            for header, value in zip(headers, cells)
            if value and value not in {"—", "-"}
        ]
        if pairs:
            rows.append(", ".join(pairs))
    if not rows:
        return None
    return "; ".join(rows) + "."


def _format_chunk_answer(content: str) -> str:
    text = re.sub(r"<!--.*?-->", "", content.strip(), flags=re.DOTALL)
    text = re.sub(r"^#+\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    if not paragraphs:
        # A heading whose body lives entirely in its subsections holds nothing
        # but its `<!-- question_variants: ... -->` marker.  Returning the raw
        # content here used to show that HTML comment to the customer; return
        # empty so callers fall through to the next candidate chunk instead.
        return ""

    body = paragraphs[0]
    table_text = _flatten_markdown_table(body)
    if table_text is not None:
        return table_text
    if len(body) > 420 and ". " in body:
        sentences = body.split(". ")
        body = ". ".join(sentences[:2]).strip()
        if not body.endswith("."):
            body += "."
    return body


def _apply_session_context_prefix(content: str, history: list[dict[str, Any]]) -> str:
    party_size = _party_size_from_history(history)
    stripped = content.strip()
    if not party_size or party_size < 2 or not stripped:
        return content
    lead = stripped[0].lower() + stripped[1:]
    return f"Với nhóm {party_size} người như anh/chị đang đặt bàn, {lead}"


def _build_fast_path_response(
    item: Any,
    content: str,
    *,
    model: str,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    document_id = str(getattr(item.chunk, "document_id", "") or item.chunk.source)
    section_path = tuple(
        getattr(item.chunk, "section_path", ()) or (item.chunk.title,)
    )
    chunk_id = str(getattr(item.chunk, "chunk_id", "") or "") or stable_chunk_id(
        document_id=document_id,
        section_path=section_path,
        content_hash="",
    )
    claim_text = content.strip()
    if history:
        content = _apply_session_context_prefix(content, history)
    flags: list[str] = []
    if item.chunk.source == "allergy-dietary.md":
        flags.append("ALLERGY_DISCLAIMER")
        if "nhan vien" not in normalize_query_text(content):
            content = (
                f"{content}\n\n"
                "Bạn nên xác nhận thêm với nhân viên về dị ứng trước khi đặt món."
            )
    return {
        "content": content,
        "provider_available": False,
        "model": model,
        "retrieved_sources": [
            {
                "source": item.chunk.source,
                "title": item.chunk.title,
                "score": float(item.score),
                "chunk_id": chunk_id,
                "document_id": document_id,
                "section_path": list(section_path),
            }
        ],
        "evidence": [
            {
                "source": item.chunk.source,
                "title": item.chunk.title,
                "chunk_id": chunk_id,
                "section": " / ".join(section_path),
                "score": float(item.score),
            }
        ],
        "claims": [
            {
                "text": claim_text,
                "evidence_ids": [chunk_id],
                "verified": True,
                "reason": None,
            }
        ],
        "guardrail_flags": flags,
        "suggested_cart_actions": [],
        "follow_up": {"can_show_more": False, "remaining_count": 0},
        "suggest_staff_handoff": False,
    }


def try_kb_info_fast_path(
    message: str,
    retrieved: list[Any],
    *,
    intent: str,
    wants_recommendations: bool,
    retriever: Retriever | None = None,
    history: list[dict[str, Any]] | None = None,
    is_solo_dining: bool = False,
) -> dict[str, Any] | None:
    """Deterministic KB answers for restaurant policy/FAQ (non-recommendation) queries."""

    if "CUSTOMER_CONFIRMATION_REQUIRED" in detect_guardrail_flags(message):
        return None
    if intent in {"combo_pairing", "menu_recommendation", "beverage_pairing", "nutrition_info"}:
        return None
    if wants_recommendations or is_solo_dining:
        return None
    if intent not in INFO_INTENTS:
        return None

    # Sections written for the assistant are never quotable.  Without this a guest
    # asking about the head chef received brand-voice.md's answer-structure
    # template verbatim ("1. Mở đầu ngắn (1 câu): xác nhận hiểu yêu cầu.").  They
    # stay in the corpus as guidance; they just cannot become the answer.
    retrieved = [
        item
        for item in retrieved
        if getattr(getattr(item, "chunk", None), "is_customer_facing", True)
    ]

    history = history or []
    normalized = _normalize(message)
    if (
        _was_recommendation_thread(history, "")
        and _is_more_dishes_request(normalized)
        and not _is_context_only_follow_up(normalized)
    ):
        return None

    wifi_answer = try_wifi_policy_fast_path(message, retrieved)
    if wifi_answer is not None:
        return wifi_answer

    if any(
        term in normalized
        for term in (
            "co mon",
            "mon nao",
            "co gi an",
            "co nhung mon",
            "mon khac",
            "mon phu hop",
            "goi y",
            "tu van",
            "de xuat",
            "nhom",
            "nhieu nguoi",
            "dong nguoi",
            "gia dinh",
            "an chung",
            "mot minh",
            "di mot minh",
            "an mot minh",
            "minh toi",
        )
    ):
        return None

    # Bare "general" queries without info markers must not dump restaurant-info.
    # A query matching a recognised FAQ topic route (see _FAQ_TOPIC_ROUTES) is
    # always a legitimate info marker too — checking it here (instead of only
    # this hand-maintained keyword list) keeps this gate in sync with every
    # topic that table already knows how to answer, so new/renamed topics
    # don't silently fall through to the LLM and risk an unnecessary abstain.
    if (
        intent == "general"
        and not any(
            term in normalized
            for term in (
                "dia chi",
                "o dau",
                "hotline",
                "lien he",
                "wifi",
                "mo cua",
                "gio",
                "gui xe",
                "vip",
                "thanh toan",
                "hoa don",
                "khuyen mai",
                "faq",
            )
        )
        and _topic_needle_for_query(normalized) is None
    ):
        return None

    preferred = INTENT_PREFERRED_SOURCES.get(intent, ("faq.md", "restaurant-info.md"))
    min_score = 5.0 if intent in {"payment", "restaurant_info", "service", "promotion"} else 6.0

    topic_faq = _find_faq_by_topic(normalized, retrieved)
    if topic_faq is None and retriever is not None and _topic_needle_for_query(normalized):
        faq_candidates = [
            item
            for item in retriever.search(
                message,
                top_k=30,
                filters=RetrievalFilters(allowed_source_ids=frozenset({"faq.md"})),
            )
            # This second lookup bypasses the filter applied to `retrieved` above,
            # so it needs the same guard.
            if getattr(getattr(item, "chunk", None), "is_customer_facing", True)
        ]
        topic_faq = _find_faq_by_topic(normalized, faq_candidates)
    if topic_faq is None:
        topic_faq = _find_topic_chunk_any_source(normalized, retrieved, preferred)
    if topic_faq is not None:
        content = _format_chunk_answer(topic_faq.chunk.content)
        if content:
            return _build_fast_path_response(
                topic_faq, content, model="deterministic-kb-info", history=history
            )

    faq_title_hits = [
        item
        for item in retrieved
        if item.chunk.source == "faq.md" and _title_overlap(normalized, item.chunk.title) >= 2
    ]
    if faq_title_hits:
        best_faq = max(
            faq_title_hits,
            key=lambda item: (_title_overlap(normalized, item.chunk.title), float(item.score)),
        )
        content = _format_chunk_answer(best_faq.chunk.content)
        if content:
            return _build_fast_path_response(
                best_faq, content, model="deterministic-kb-info", history=history
            )

    # Short queries (≤ 2 meaningful tokens) are too ambiguous for deterministic
    # answers — let the LLM interpret context instead of guessing from keywords.
    query_tokens = _query_tokens(normalized)
    if len(query_tokens) <= 2 and intent not in {"kids_elderly", "occasion", "payment", "restaurant_info"}:
        return None

    scored: list[tuple[float, Any]] = []

    for item in retrieved:
        if item.chunk.source in JUNK_INFO_SOURCES:
            continue
        score = _relevance_score(normalized, item, preferred)
        # Threshold tuned per intent; FAQ/policy intents allow slightly weaker lexical overlap.
        if score >= min_score:
            scored.append((score, item))

    if not scored:
        return None

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best = scored[0][1]
    content = _format_chunk_answer(best.chunk.content)
    if not content:
        return None

    return _build_fast_path_response(best, content, model="deterministic-kb-info", history=history)
