from __future__ import annotations

import hashlib
import math
import os
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retriever import RetrievalFilters, RetrievedChunk


DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_EMBEDDING_REVISION = "fd1525a9fd15316a2d503bf26ab031a61d056e98"
DEFAULT_EMBEDDING_DIMENSION = 384
DEFAULT_EMBEDDING_KEY = "e5_small"


@dataclass(frozen=True)
class EncoderSpec:
    key: str
    model_name: str
    model_revision: str | None
    prefix_kind: str  # "e5" | "none"
    display_name: str
    estimated_size_mb: int
    trust_remote_code: bool = False


ENCODER_REGISTRY: dict[str, EncoderSpec] = {
    "e5_small": EncoderSpec(
        key="e5_small",
        model_name="intfloat/multilingual-e5-small",
        model_revision="fd1525a9fd15316a2d503bf26ab031a61d056e98",
        prefix_kind="e5",
        display_name="multilingual-e5-small",
        estimated_size_mb=120,
    ),
    "mpnet_base": EncoderSpec(
        key="mpnet_base",
        model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        model_revision=None,
        prefix_kind="none",
        display_name="paraphrase-multilingual-mpnet-base-v2",
        estimated_size_mb=420,
        trust_remote_code=False,
    ),
    "vi_bi": EncoderSpec(
        key="vi_bi",
        model_name="bkai-foundation-models/vietnamese-bi-encoder",
        model_revision=None,
        prefix_kind="none",
        display_name="vietnamese-bi-encoder",
        estimated_size_mb=540,
    ),
}


class EmbeddingEncoder(Protocol):
    model_name: str
    model_revision: str
    dimension: int

    def encode_documents(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...

    def encode_queries(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


def resolve_encoder_key(value: str | None = None) -> str:
    raw = (value or os.getenv("AI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_KEY)).strip().lower()
    aliases = {
        "intfloat/multilingual-e5-small": "e5_small",
        "intfloat/multilingual-e5-base": "mpnet_base",
        "e5_base": "mpnet_base",
        "dense_e5_base": "mpnet_base",
        "hybrid_e5_base": "mpnet_base",
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": "mpnet_base",
        "bkai-foundation-models/vietnamese-bi-encoder": "vi_bi",
        "dense_e5": "e5_small",
        "hybrid_rrf": "e5_small",
    }
    resolved = aliases.get(raw, raw)
    if resolved not in ENCODER_REGISTRY:
        supported = ", ".join(sorted(ENCODER_REGISTRY))
        raise ValueError(f"Unsupported embedding model key: {raw}. Supported: {supported}")
    return resolved


def create_encoder(
    model_key: str | None = None,
    *,
    device: str | None = None,
    batch_size: int = 32,
) -> EmbeddingEncoder:
    spec = ENCODER_REGISTRY[resolve_encoder_key(model_key)]
    if spec.prefix_kind == "e5":
        return SentenceTransformerE5Encoder(
            model_name=spec.model_name,
            model_revision=spec.model_revision or DEFAULT_EMBEDDING_REVISION,
            device=device,
            batch_size=batch_size,
            trust_remote_code=spec.trust_remote_code,
        )
    return SentenceTransformerBiEncoder(
        model_name=spec.model_name,
        model_revision=spec.model_revision,
        device=device,
        batch_size=batch_size,
        trust_remote_code=spec.trust_remote_code,
    )


def estimate_encoder_memory_mb(encoder: EmbeddingEncoder) -> float:
    for spec in ENCODER_REGISTRY.values():
        if spec.model_name == encoder.model_name:
            return float(spec.estimated_size_mb)
    return float(max(encoder.dimension * 1024, DEFAULT_EMBEDDING_DIMENSION * 384) // 1024)


class _SentenceTransformerEncoderBase:
    def __init__(
        self,
        model_name: str,
        model_revision: str | None,
        *,
        device: str | None = None,
        batch_size: int = 32,
        trust_remote_code: bool = False,
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
        self.model_revision = model_revision or "main"
        self._batch_size = batch_size
        kwargs: dict[str, Any] = {
            "device": device,
            "trust_remote_code": trust_remote_code,
        }
        if model_revision:
            kwargs["revision"] = model_revision
        self._model: Any = SentenceTransformer(model_name, **kwargs)
        if hasattr(self._model, "get_embedding_dimension"):
            dimension = self._model.get_embedding_dimension()
        else:
            dimension = self._model.get_sentence_embedding_dimension()
        if dimension is None or dimension <= 0:
            raise ValueError("Embedding model did not expose a valid dimension")
        self.dimension = int(dimension)

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


class SentenceTransformerE5Encoder(_SentenceTransformerEncoderBase):
    """Pinned multilingual E5 encoder loaded only when dense retrieval is requested."""

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        model_revision: str = DEFAULT_EMBEDDING_REVISION,
        *,
        device: str | None = None,
        batch_size: int = 32,
        trust_remote_code: bool = False,
    ) -> None:
        super().__init__(
            model_name,
            model_revision,
            device=device,
            batch_size=batch_size,
            trust_remote_code=trust_remote_code,
        )

    def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._encode(self._prefix(texts, "passage"))

    def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._encode(self._prefix(texts, "query"))

    @staticmethod
    def _prefix(texts: Sequence[str], kind: str) -> list[str]:
        if kind not in {"passage", "query"}:
            raise ValueError(f"Unsupported E5 input kind: {kind}")
        return [f"{kind}: {text.strip()}" for text in texts]


class SentenceTransformerBiEncoder(_SentenceTransformerEncoderBase):
    """Bi-encoder without query/passage prefixes (PhoBERT, MiniLM, etc.)."""

    def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._encode([text.strip() for text in texts])

    def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return self._encode([text.strip() for text in texts])


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
