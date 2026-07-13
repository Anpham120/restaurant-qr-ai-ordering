"""Reproducible retrieval benchmark for the restaurant RAG corpus.

The vector baseline is TF-IDF cosine rather than a neural embedding model.  It
is intentionally labelled as such: no result may be presented as a semantic
embedding experiment until an encoder, version, and frozen corpus are recorded.
"""

from __future__ import annotations

import csv
import math
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.rag.knowledge_base import KnowledgeChunk, load_markdown_knowledge_base
from app.rag.retriever import BM25Retriever, RetrievedChunk, _tokenize_list


PROJECT_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_CSV = PROJECT_ROOT / "ai" / "evaluation" / "golden_questions.csv"
KB_PATH = PROJECT_ROOT / "ai" / "knowledge-base"
TOP_K = 5
RRF_K = 60


@dataclass(frozen=True)
class BenchmarkResult:
    method: str
    hit_rate_at_k: float
    mrr_at_k: float
    p50_latency_ms: float
    p95_latency_ms: float
    cases: int


class TfidfVectorRetriever:
    """Dependency-free sparse vector baseline for a fair lexical comparison."""

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks
        self._documents = [Counter(_tokenize_list(f"{chunk.title} {chunk.content} {' '.join(chunk.tags)}")) for chunk in chunks]
        document_frequency: Counter[str] = Counter()
        for document in self._documents:
            document_frequency.update(document.keys())
        count = max(1, len(chunks))
        self._idf = {token: math.log((count + 1) / (frequency + 1)) + 1 for token, frequency in document_frequency.items()}
        self._norms = [self._norm(document) for document in self._documents]

    def search(self, query: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
        query_vector = Counter(_tokenize_list(query))
        query_norm = self._norm(query_vector)
        if not query_norm:
            return []
        scored: list[RetrievedChunk] = []
        for chunk, document, norm in zip(self._chunks, self._documents, self._norms, strict=True):
            if not norm:
                continue
            dot = sum(query_tf * document.get(token, 0) * self._idf.get(token, 0) ** 2 for token, query_tf in query_vector.items())
            if dot:
                scored.append(RetrievedChunk(chunk, dot / (query_norm * norm)))
        return sorted(scored, key=lambda result: result.score, reverse=True)[:top_k]

    def _norm(self, vector: Counter[str]) -> float:
        return math.sqrt(sum((frequency * self._idf.get(token, 0)) ** 2 for token, frequency in vector.items()))


class HybridRrfRetriever:
    """Reciprocal-rank fusion of BM25 and sparse-vector rankings."""

    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        self._bm25 = BM25Retriever(chunks)
        self._vector = TfidfVectorRetriever(chunks)
        self._chunk_count = len(chunks)

    def search(self, query: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
        scores: defaultdict[str, float] = defaultdict(float)
        chunk_by_key: dict[str, KnowledgeChunk] = {}
        for ranking in (self._bm25.search(query, self._chunk_count), self._vector.search(query, self._chunk_count)):
            for rank, result in enumerate(ranking, start=1):
                key = f"{result.chunk.source}:{result.chunk.title}"
                chunk_by_key[key] = result.chunk
                scores[key] += 1 / (RRF_K + rank)
        return [
            RetrievedChunk(chunk_by_key[key], score)
            for key, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
        ]


def benchmark_all(top_k: int = TOP_K) -> list[BenchmarkResult]:
    chunks = load_markdown_knowledge_base(KB_PATH)
    cases = _load_cases()
    retrievers = {
        "bm25": BM25Retriever(chunks),
        "tfidf_vector": TfidfVectorRetriever(chunks),
        "hybrid_rrf": HybridRrfRetriever(chunks),
    }
    return [_evaluate(name, retriever, cases, top_k) for name, retriever in retrievers.items()]


def _evaluate(method: str, retriever: object, cases: list[dict[str, str]], top_k: int) -> BenchmarkResult:
    hit_count = 0
    reciprocal_ranks: list[float] = []
    latencies: list[float] = []
    evaluated = 0
    for case in cases:
        expected = {value.strip() for value in case["expected_sources"].split(";") if value.strip()}
        if not expected:
            continue
        started = time.perf_counter()
        results = retriever.search(case["user_question"], top_k)  # type: ignore[attr-defined]
        latencies.append((time.perf_counter() - started) * 1000)
        evaluated += 1
        ranks = [rank for rank, result in enumerate(results, start=1) if result.chunk.source in expected]
        if ranks:
            hit_count += 1
            reciprocal_ranks.append(1 / ranks[0])
        else:
            reciprocal_ranks.append(0)
    ordered_latency = sorted(latencies)
    return BenchmarkResult(
        method=method,
        hit_rate_at_k=hit_count / evaluated if evaluated else 0,
        mrr_at_k=statistics.mean(reciprocal_ranks) if reciprocal_ranks else 0,
        p50_latency_ms=statistics.median(latencies) if latencies else 0,
        p95_latency_ms=ordered_latency[math.ceil(len(ordered_latency) * 0.95) - 1] if ordered_latency else 0,
        cases=evaluated,
    )


def _load_cases() -> list[dict[str, str]]:
    with GOLDEN_CSV.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


if __name__ == "__main__":
    for result in benchmark_all():
        print(
            f"{result.method}: hit@{TOP_K}={result.hit_rate_at_k:.3f}; "
            f"MRR@{TOP_K}={result.mrr_at_k:.3f}; p50={result.p50_latency_ms:.3f}ms; "
            f"p95={result.p95_latency_ms:.3f}ms; cases={result.cases}"
        )
