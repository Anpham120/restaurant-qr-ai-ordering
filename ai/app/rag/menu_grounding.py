from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from app.rag.embedding_retriever import EmbeddingEncoder
from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retrieval_factory import build_retriever_stack
from app.rag.retriever import RetrievalFilters, Retriever


MAX_MENU_CANDIDATES = 8
CATEGORY_QUERY_ALIASES = {
    "bia ruou": ("do uong co con", "co con", "bia", "ruou", "cocktail"),
}


class MenuCandidateRetriever:
    """Rank the live menu while keeping category/tag intent as hard filters."""

    def __init__(
        self,
        method: str = "bm25",
        *,
        encoder: EmbeddingEncoder | None = None,
    ) -> None:
        self._method = method
        self._encoder = encoder
        self._signature: tuple | None = None
        self._retriever: Retriever | None = None
        self._items_by_id: dict[str, dict] = {}

    def select(
        self,
        message: str,
        menu_items: list[dict],
        *,
        excluded_ids: frozenset[str] = frozenset(),
        limit: int = MAX_MENU_CANDIDATES,
    ) -> list[dict]:
        available = _available_items(menu_items)
        if not available or limit <= 0:
            return []

        self._refresh_if_needed(available)
        query = _normalize(message)
        allowed_ids = _allowed_ids(query, available)
        filters = RetrievalFilters(
            allowed_source_ids=frozenset(allowed_ids),
            excluded_source_ids=excluded_ids,
        )
        if not query:
            return [
                item
                for item_id, item in sorted(self._items_by_id.items())
                if filters.allows(_menu_chunk(item))
            ][:limit]

        assert self._retriever is not None
        results = self._retriever.search(message, min(limit, MAX_MENU_CANDIDATES), filters=filters)
        selected_ids = [result.chunk.source for result in results]
        selected_ids.extend(
            item_id
            for item_id in sorted(allowed_ids)
            if item_id not in selected_ids and item_id not in excluded_ids
        )
        return [self._items_by_id[item_id] for item_id in selected_ids[: min(limit, MAX_MENU_CANDIDATES)]]

    def _refresh_if_needed(self, available: list[dict]) -> None:
        signature = _menu_signature(available)
        if signature == self._signature:
            return

        chunks = [_menu_chunk(item) for item in available]
        stack = build_retriever_stack(chunks, self._method, encoder=self._encoder)
        self._encoder = stack.encoder
        self._retriever = stack.retriever
        self._items_by_id = {_item_id(item): item for item in available}
        self._signature = signature


def select_menu_candidates(
    message: str,
    menu_items: list[dict],
    limit: int = MAX_MENU_CANDIDATES,
) -> list[dict]:
    """Backward-compatible deterministic entrypoint used by focused tests."""

    return MenuCandidateRetriever("bm25").select(message, menu_items, limit=limit)


def _available_items(menu_items: list[dict]) -> list[dict]:
    unique: dict[str, dict] = {}
    for item in menu_items:
        item_id = _item_id(item)
        if item_id and bool(item.get("is_available", True)):
            unique[item_id] = item
    return [unique[item_id] for item_id in sorted(unique)]


def _allowed_ids(query: str, available: list[dict]) -> set[str]:
    category_matches = {
        _normalize(str(item.get("category_name") or ""))
        for item in available
        if _is_meaningful(item.get("category_name"))
        and _contains_phrase(query, _normalize(str(item.get("category_name") or "")))
    }
    available_categories = {
        _normalize(str(item.get("category_name") or "")) for item in available
    }
    category_matches.update(
        category
        for category, aliases in CATEGORY_QUERY_ALIASES.items()
        if category in available_categories and any(_contains_phrase(query, alias) for alias in aliases)
    )
    tag_matches = {
        _normalize(str(tag))
        for item in available
        for tag in _tags(item)
        if _is_meaningful(tag) and _contains_phrase(query, _normalize(str(tag)))
    }
    if category_matches:
        return {
            _item_id(item)
            for item in available
            if _normalize(str(item.get("category_name") or "")) in category_matches
        }
    if tag_matches:
        return {
            _item_id(item)
            for item in available
            if any(_normalize(str(tag)) in tag_matches for tag in _tags(item))
        }
    return {_item_id(item) for item in available}


def _menu_chunk(item: dict) -> KnowledgeChunk:
    category = str(item.get("category_name") or "")
    tags = tuple(str(tag) for tag in _tags(item))
    content = "\n".join(
        value
        for value in (
            str(item.get("description") or "").strip(),
            f"Danh mục: {category}" if category else "",
            f"Tags: {', '.join(tags)}" if tags else "",
        )
        if value
    )
    return KnowledgeChunk(
        source=_item_id(item),
        title=str(item.get("name") or "").strip(),
        content=content,
        tags=tags,
    )


def _menu_signature(items: Sequence[dict]) -> tuple:
    return tuple(
        (
            _item_id(item),
            str(item.get("name") or ""),
            str(item.get("description") or ""),
            str(item.get("category_name") or ""),
            tuple(str(tag) for tag in _tags(item)),
        )
        for item in items
    )


def _item_id(item: dict) -> str:
    return str(item.get("id") or item.get("menu_item_id") or "").strip()


def _tags(item: dict) -> list[object]:
    tags = item.get("tags") or []
    return [tags] if isinstance(tags, str) else list(tags)


def _is_meaningful(value: object) -> bool:
    return len(_normalize(str(value or ""))) >= 3


def _contains_phrase(query: str, phrase: str) -> bool:
    return bool(phrase) and f" {phrase} " in f" {query} "


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return " ".join(re.findall(r"[a-z0-9]+", without_marks))
