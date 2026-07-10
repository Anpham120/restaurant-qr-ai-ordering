from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Protocol

import numpy as np

from app.domain import RetrievalDocument, SearchResult


DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class TextEncoder(Protocol):
    model_name: str

    def encode(self, texts: Iterable[str]) -> np.ndarray: ...


class FastEmbedEncoder:
    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: str | Path = ".cache/fastembed",
        specific_model_path: str | Path | None = None,
    ) -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        kwargs = {"specific_model_path": str(specific_model_path)} if specific_model_path else {}
        self._model = TextEmbedding(model_name=model_name, cache_dir=str(cache_dir), **kwargs)

    def encode(self, texts: Iterable[str]) -> np.ndarray:
        matrix = np.asarray(list(self._model.embed(list(texts))), dtype=np.float32)
        return _normalize_rows(matrix)

    @staticmethod
    def model_checksum(model_path: str | Path | None) -> str | None:
        if not model_path:
            return None
        path = Path(model_path)
        candidates = sorted(path.glob("*.onnx"))
        if not candidates:
            return None
        digest = hashlib.sha256()
        with candidates[0].open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()


class DenseEmbeddingRetriever:
    name = "embedding"

    def __init__(self, documents: list[RetrievalDocument], encoder: TextEncoder) -> None:
        self.documents = documents
        self.encoder = encoder
        self._matrix = encoder.encode(document.text for document in documents)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if not query.strip() or not self.documents:
            return []
        vector = self.encoder.encode([query])[0]
        scores = self._matrix @ vector
        indices = np.argsort(-scores)[:top_k]
        return [
            SearchResult(document=self.documents[int(index)], score=float(scores[index]), rank=rank)
            for rank, index in enumerate(indices, start=1)
        ]


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms

