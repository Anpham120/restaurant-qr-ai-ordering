from __future__ import annotations

from collections import defaultdict

from app.domain import SearchResult
from app.retrieval.base import Retriever


class HybridRrfRetriever:
    name = "hybrid_rrf"

    def __init__(
        self,
        lexical: Retriever,
        dense: Retriever,
        rrf_k: int = 60,
        lexical_weight: float = 1.0,
        dense_weight: float = 1.0,
    ) -> None:
        self.lexical = lexical
        self.dense = dense
        self.rrf_k = rrf_k
        self.lexical_weight = lexical_weight
        self.dense_weight = dense_weight

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        candidate_k = max(top_k * 4, 20)
        lexical_results = self.lexical.search(query, candidate_k)
        dense_results = self.dense.search(query, candidate_k)
        scores: dict[str, float] = defaultdict(float)
        documents = {}
        for results, weight in (
            (lexical_results, self.lexical_weight),
            (dense_results, self.dense_weight),
        ):
            for result in results:
                scores[result.document.id] += weight / (self.rrf_k + result.rank)
                documents[result.document.id] = result.document
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:top_k]
        return [
            SearchResult(document=documents[document_id], score=score, rank=rank)
            for rank, (document_id, score) in enumerate(ranked, start=1)
        ]
