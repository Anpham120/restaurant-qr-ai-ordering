from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from typing import Any, Protocol

from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retriever import RetrievalFilters, RetrievedChunk


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_EMBEDDING_REVISION = "fd1525a9fd15316a2d503bf26ab031a61d056e98"
DEFAULT_EMBEDDING_DIMENSION = 384


class EmbeddingEncoder(Protocol):
    model_name: str
    model_revision: str
    dimension: int

    def encode_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...

    def encode_queries(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


class SentenceTransformerE5Encoder:
    """Pinned multilingual E5 encoder loaded only when dense retrieval is requested."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        model_revision: str = DEFAULT_EMBEDDING_REVISION,
        *,
        device: str | None = None,
        batch_size: int = 32,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Dense retrieval requires ai/requirements-evaluation.txt."
            ) from exc

        self.model_name = model_name
        self.model_revision = model_revision
        self._batch_size = batch_size
        self._model: Any = SentenceTransformer(
            model_name,
            revision=model_revision,
            device=device,
            trust_remote_code=False,
        )
        if hasattr(self._model, "get_embedding_dimension"):
            dimension = self._model.get_embedding_dimension()
        else:
            dimension = self._model.get_sentence_embedding_dimension()
        if dimension is None or dimension <= 0:
            raise ValueError("Embedding model did not expose a valid dimension")
        self.dimension = int(dimension)

    def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._encode(self._prefix(texts, "passage"))

    def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._encode(self._prefix(texts, "query"))

    @staticmethod
    def _prefix(texts: Sequence[str], kind: str) -> list[str]:
        if kind not in {"passage", "query"}:
            raise ValueError(f"Unsupported E5 input kind: {kind}")
        return [f"{kind}: {text.strip()}" for text in texts]

    def _encode(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [tuple(float(value) for value in vector) for vector in vectors]


class DenseRetriever:
    """Cosine-similarity retriever over precomputed document embeddings."""

    def __init__(
        self,
        chunks: Sequence[KnowledgeChunk],
        encoder: EmbeddingEncoder,
        *,
        vector_cache: dict[str, tuple[tuple[float, ...], str]] | None = None,
    ) -> None:
        self._chunks = list(chunks)
        self._encoder = encoder
        self._dimension = encoder.dimension
        if self._dimension <= 0:
            raise ValueError("encoder.dimension must be positive")

        document_texts = [_document_text(chunk) for chunk in self._chunks]
        self._document_vectors = build_document_vectors_cached(
            self._chunks,
            document_texts,
            encoder,
            vector_cache,
        )

    @property
    def model_name(self) -> str:
        return self._encoder.model_name

    @property
    def model_revision(self) -> str:
        return self._encoder.model_revision

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        if top_k <= 0 or not query.strip():
            return []

        raw_query_vectors = self._encoder.encode_queries([query])
        if len(raw_query_vectors) != 1:
            raise ValueError("Encoder must return exactly one query embedding")
        query_vector = self._normalize(raw_query_vectors[0])

        scored: list[RetrievedChunk] = []
        for chunk, document_vector in zip(self._chunks, self._document_vectors, strict=True):
            if filters is not None and not filters.allows(chunk):
                continue
            score = sum(left * right for left, right in zip(query_vector, document_vector, strict=True))
            scored.append(RetrievedChunk(chunk=chunk, score=round(score, 8)))

        return sorted(scored, key=lambda item: (-item.score, item.chunk.source))[:top_k]

    def _normalize(self, vector: Sequence[float]) -> tuple[float, ...]:
        return _normalize_vector(vector, self._dimension)


def build_document_vectors_cached(
    chunks: Sequence[KnowledgeChunk],
    document_texts: Sequence[str],
    encoder: EmbeddingEncoder,
    vector_cache: dict[str, tuple[tuple[float, ...], str]] | None,
) -> list[tuple[float, ...]]:
    if len(document_texts) != len(chunks):
        raise ValueError("document_texts must align with chunks")

    if not document_texts:
        return []

    cache = vector_cache if vector_cache is not None else {}
    vectors: list[tuple[float, ...] | None] = [None] * len(chunks)
    texts_to_encode: list[str] = []
    encode_indices: list[int] = []

    for index, (chunk, text) in enumerate(zip(chunks, document_texts, strict=True)):
        content_hash = _content_hash(text)
        cached = cache.get(chunk.source)
        if cached is not None and cached[1] == content_hash:
            vectors[index] = cached[0]
            continue
        texts_to_encode.append(text)
        encode_indices.append(index)

    if texts_to_encode:
        encoded = encoder.encode_documents(texts_to_encode)
        if len(encoded) != len(texts_to_encode):
            raise ValueError("Encoder returned a different number of document embeddings")
        for index, vector in zip(encode_indices, encoded, strict=True):
            normalized = _normalize_vector(vector, encoder.dimension)
            vectors[index] = normalized
            content_hash = _content_hash(document_texts[index])
            cache[chunks[index].source] = (normalized, content_hash)

    if any(vector is None for vector in vectors):
        raise ValueError("Failed to build embeddings for all chunks")
    return vectors  # type: ignore[return-value]


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_vector(vector: Sequence[float], dimension: int) -> tuple[float, ...]:
    if len(vector) != dimension:
        raise ValueError(f"Expected embedding dimension {dimension}, received {len(vector)}")
    values = tuple(float(value) for value in vector)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("Embedding vectors must contain only finite values")
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise ValueError("Embedding vectors must not be all zeros")
    return tuple(value / norm for value in values)


def _document_text(chunk: KnowledgeChunk) -> str:
    tags = ", ".join(chunk.tags)
    return f"{chunk.title}\n{chunk.content}\nTags: {tags}"
