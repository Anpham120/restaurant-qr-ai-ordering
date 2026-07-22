"""Optional cross-encoder rerank stage for retrieval experiments."""

from __future__ import annotations

from typing import Any, Sequence


def rerank_with_cross_encoder(
    query: str,
    results: Sequence[Any],
    *,
    top_k: int,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> list[Any]:
    """Rerank retrieval hits with a lightweight cross-encoder (CPU-friendly)."""
    if not results:
        return []
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Cross-encoder rerank requires sentence-transformers in the eval environment"
        ) from exc

    model = CrossEncoder(model_name)
    pairs = [
        (query, f"{result.chunk.title}\n{result.chunk.content[:512]}")
        for result in results
    ]
    scores = model.predict(pairs)
    ranked = sorted(
        zip(results, scores, strict=True),
        key=lambda item: float(item[1]),
        reverse=True,
    )
    reranked: list[Any] = []
    for result, score in ranked[:top_k]:
        reranked.append(type(result)(result.chunk, float(score)))
    return reranked
