from __future__ import annotations

import json
from pathlib import Path
from threading import RLock

from app.data import documents_from_menu, load_policy_documents, menu_fingerprint
from app.domain import MenuItemContext, RetrievalDocument, SearchResult
from app.retrieval import (
    BM25Config,
    BM25Retriever,
    DenseEmbeddingRetriever,
    FastEmbedEncoder,
    HybridRrfRetriever,
    TfidfRetriever,
)


class RetrievalService:
    def __init__(
        self,
        policies_path: Path,
        production_config_path: Path,
        embedding_cache: Path,
        embedding_model_path: Path | None = None,
    ) -> None:
        self._policy_documents = load_policy_documents(policies_path)
        self._production = json.loads(production_config_path.read_text(encoding="utf-8"))
        self._embedding_cache = embedding_cache
        self._embedding_model_path = embedding_model_path
        self._fingerprint: str | None = None
        self._documents: list[RetrievalDocument] = []
        self._retriever = None
        self._lock = RLock()
        self._encoder = None

    @property
    def method(self) -> str:
        return str(self._production["method"])

    @property
    def threshold(self) -> float:
        return float(self._production.get("threshold") or 0.0)

    def search(self, query: str, menu_items: list[MenuItemContext], top_k: int = 5) -> list[SearchResult]:
        self._ensure_index(menu_items)
        results = self._retriever.search(query, top_k)
        if results and results[0].score < self.threshold:
            return []
        return results

    def _ensure_index(self, menu_items: list[MenuItemContext]) -> None:
        fingerprint = menu_fingerprint(menu_items)
        if fingerprint == self._fingerprint:
            return
        with self._lock:
            if fingerprint == self._fingerprint:
                return
            self._documents = documents_from_menu(menu_items) + self._policy_documents
            self._retriever = self._build_retriever(self._documents)
            self._fingerprint = fingerprint

    def _build_retriever(self, documents: list[RetrievalDocument]):
        method = self.method
        config = self._production.get("config") or {}
        if method == "tfidf":
            return TfidfRetriever(documents)
        if method == "bm25":
            return BM25Retriever(documents, BM25Config(**config))

        dense = DenseEmbeddingRetriever(documents, self._get_encoder())
        if method == "embedding":
            return dense
        if method == "hybrid_rrf":
            bm25 = BM25Retriever(documents, BM25Config(**config["bm25"]))
            return HybridRrfRetriever(
                bm25,
                dense,
                rrf_k=int(config["rrf_k"]),
                lexical_weight=float(config["lexical_weight"]),
                dense_weight=float(config["dense_weight"]),
            )
        if method == "hybrid_tfidf_embedding":
            return HybridRrfRetriever(
                TfidfRetriever(documents),
                dense,
                rrf_k=int(config["rrf_k"]),
                lexical_weight=float(config["lexical_weight"]),
                dense_weight=float(config["dense_weight"]),
            )
        raise ValueError(f"Unsupported production retrieval method: {method}")

    def _get_encoder(self):
        if self._encoder is None:
            model = self._production.get("embedding_model") or self._production.get("config", {}).get("model")
            self._encoder = FastEmbedEncoder(
                model_name=model,
                cache_dir=self._embedding_cache,
                specific_model_path=self._embedding_model_path,
            )
        return self._encoder
