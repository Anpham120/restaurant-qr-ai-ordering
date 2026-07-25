from __future__ import annotations

from collections.abc import Sequence

from app.rag.retriever import RetrievalFilters, RetrievedChunk, Retriever


class HybridRrfRetriever:
    """Fuse retriever rankings with weighted reciprocal-rank fusion."""

    def __init__(
        self,
        retrievers: Sequence[Retriever],
        *,
        weights: Sequence[float] | None = None,
        rrf_k: int = 60,
        candidate_multiplier: int = 4,
    ) -> None:
        if not retrievers:
            raise ValueError("At least one retriever is required")
        if rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        if candidate_multiplier <= 0:
            raise ValueError("candidate_multiplier must be positive")

        resolved_weights = tuple(weights) if weights is not None else (1.0,) * len(retrievers)
        if len(resolved_weights) != len(retrievers):
            raise ValueError("weights must match the number of retrievers")
        if any(weight <= 0 for weight in resolved_weights):
            raise ValueError("weights must be positive")

        self._retrievers = tuple(retrievers)
        self._weights = resolved_weights
        self._rrf_k = rrf_k
        self._candidate_multiplier = candidate_multiplier

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        if top_k <= 0 or not query.strip():
            return []

        candidate_depth = top_k * self._candidate_multiplier
        chunks_by_id = {}
        scores_by_id: dict[str, float] = {}

        for retriever, weight in zip(self._retrievers, self._weights, strict=True):
            results = retriever.search(query, candidate_depth, filters=filters)
            seen_chunk_ids: set[str] = set()
            for rank, result in enumerate(results, start=1):
                chunk_id = result.chunk.chunk_id
                if chunk_id in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(chunk_id)
                chunks_by_id.setdefault(chunk_id, result.chunk)
                scores_by_id[chunk_id] = scores_by_id.get(chunk_id, 0.0) + (
                    weight / (self._rrf_k + rank)
                )

        fused = [
            RetrievedChunk(chunk=chunks_by_id[chunk_id], score=round(score, 10))
            for chunk_id, score in scores_by_id.items()
        ]
        return sorted(fused, key=lambda item: (-item.score, item.chunk.chunk_id))[:top_k]
