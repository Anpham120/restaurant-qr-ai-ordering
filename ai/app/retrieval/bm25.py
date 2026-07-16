from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from heapq import nlargest

from app.domain import RetrievalDocument, SearchResult
from app.text import tokenize


@dataclass(frozen=True)
class BM25Config:
    k1: float = 1.5
    b: float = 0.75
    title_boost: float = 1.2


class BM25Retriever:
    name = "bm25"

    def __init__(self, documents: list[RetrievalDocument], config: BM25Config | None = None) -> None:
        self.documents = documents
        self.config = config or BM25Config()
        self._tokens = [tokenize(document.text) for document in documents]
        self._term_frequencies = [Counter(tokens) for tokens in self._tokens]
        self._title_tokens = [set(tokenize(document.title)) for document in documents]
        self._doc_lengths = [len(tokens) for tokens in self._tokens]
        self._average_doc_length = sum(self._doc_lengths) / max(len(self._doc_lengths), 1)
        self._document_frequency: Counter[str] = Counter()
        for tokens in self._tokens:
            self._document_frequency.update(set(tokens))

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        query_tokens = set(tokenize(query))
        if not query_tokens or not self.documents:
            return []

        scored: list[tuple[float, int]] = []
        document_count = len(self.documents)
        config = self.config
        for index, term_frequency in enumerate(self._term_frequencies):
            overlap = query_tokens.intersection(term_frequency)
            if not overlap:
                continue
            document_length = self._doc_lengths[index]
            score = 0.0
            for token in overlap:
                frequency = term_frequency[token]
                document_frequency = self._document_frequency[token]
                inverse_frequency = math.log(
                    (document_count - document_frequency + 0.5) / (document_frequency + 0.5) + 1.0
                )
                denominator = frequency + config.k1 * (
                    1.0 - config.b + config.b * document_length / max(self._average_doc_length, 1.0)
                )
                score += inverse_frequency * frequency * (config.k1 + 1.0) / denominator
            score += config.title_boost * len(query_tokens.intersection(self._title_tokens[index]))
            scored.append((score, index))

        best = nlargest(max(0, top_k), scored, key=lambda value: value[0])
        return [
            SearchResult(document=self.documents[index], score=float(score), rank=rank)
            for rank, (score, index) in enumerate(best, start=1)
        ]

