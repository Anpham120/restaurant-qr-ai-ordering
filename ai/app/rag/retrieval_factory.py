from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.rag.embedding_retriever import (
    DenseRetriever,
    EmbeddingEncoder,
    create_encoder,
    resolve_encoder_key,
)
from app.rag.hybrid_retriever import HybridRrfRetriever
from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retriever import BM25Retriever, Retriever


SUPPORTED_RETRIEVAL_METHODS = frozenset({"bm25", "dense", "hybrid"})


@dataclass(frozen=True)
class RetrieverStack:
    retriever: Retriever
    method: str
    encoder: EmbeddingEncoder | None


def build_retriever_stack(
    chunks: Sequence[KnowledgeChunk],
    method: str,
    *,
    encoder: EmbeddingEncoder | None = None,
    vector_cache: dict[str, tuple[tuple[float, ...], str]] | None = None,
) -> RetrieverStack:
    """Build one retrieval stack and expose its encoder for live-menu reuse."""

    normalized_method = method.strip().lower()
    if normalized_method not in SUPPORTED_RETRIEVAL_METHODS:
        raise ValueError(f"Unsupported retrieval method: {method}")

    lexical = BM25Retriever(chunks)
    if normalized_method == "bm25":
        return RetrieverStack(lexical, normalized_method, None)

    resolved_encoder = encoder or create_encoder(resolve_encoder_key())
    dense = DenseRetriever(chunks, resolved_encoder, vector_cache=vector_cache)
    if normalized_method == "dense":
        return RetrieverStack(dense, normalized_method, resolved_encoder)

    return RetrieverStack(
        HybridRrfRetriever([lexical, dense]),
        normalized_method,
        resolved_encoder,
    )
