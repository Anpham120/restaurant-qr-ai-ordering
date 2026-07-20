from __future__ import annotations

from collections.abc import Sequence

from app.rag.embedding_retriever import EmbeddingEncoder
from app.rag.knowledge_base import KnowledgeChunk
from app.rag.menu_item_kind import ItemKind, detect_requested_item_kind
from app.rag.menu_query_filters import infer_allowed_menu_item_ids, infer_excluded_menu_item_ids
from app.rag.retrieval_factory import build_retriever_stack
from app.rag.retriever import RetrievalFilters, Retriever
from app.rag.vietnamese_normalizer import normalize_query_text


MAX_MENU_CANDIDATES = 8


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
        self._vector_cache: dict[str, tuple[tuple[float, ...], str]] = {}

    def select(
        self,
        message: str,
        menu_items: list[dict],
        *,
        excluded_ids: frozenset[str] = frozenset(),
        limit: int = MAX_MENU_CANDIDATES,
        requested_item_kind: ItemKind | None = None,
        excluded_category_ids: frozenset[str] = frozenset(),
    ) -> list[dict]:
        if excluded_category_ids:
            menu_items = [
                item
                for item in menu_items
                if str(item.get("category_id") or "").strip() not in excluded_category_ids
            ]

        available = _available_items(menu_items)
        if not available or limit <= 0:
            return []

        if requested_item_kind is None:
            requested_item_kind = detect_requested_item_kind(message)

        self._refresh_if_needed(available)
        query = normalize_query_text(message)
        allowed = infer_allowed_menu_item_ids(
            message,
            available,
            requested_item_kind=requested_item_kind,
        )
        rejected = infer_excluded_menu_item_ids(message, available)
        allowed_ids = allowed if allowed is not None else {_item_id(item) for item in available}
        allowed_ids -= rejected
        blocked_ids = excluded_ids | rejected
        filters = RetrievalFilters(
            allowed_source_ids=frozenset(allowed_ids) if allowed is not None else None,
            excluded_source_ids=blocked_ids,
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
            if item_id not in selected_ids and item_id not in blocked_ids
        )
        return [self._items_by_id[item_id] for item_id in selected_ids[: min(limit, MAX_MENU_CANDIDATES)]]

    def _refresh_if_needed(self, available: list[dict]) -> None:
        signature = _menu_signature(available)
        if signature == self._signature:
            return

        chunks = [_menu_chunk(item) for item in available]
        stack = build_retriever_stack(
            chunks,
            self._method,
            encoder=self._encoder,
            vector_cache=self._vector_cache,
        )
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
