from __future__ import annotations

import unittest

from app.rag.hybrid_retriever import HybridRrfRetriever
from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retriever import RetrievalFilters, RetrievedChunk


def _chunk(source: str, title: str | None = None) -> KnowledgeChunk:
    resolved_title = title or source
    return KnowledgeChunk(source=source, title=resolved_title, content=resolved_title, tags=("menu",))


class StubRetriever:
    def __init__(self, sources: list[str]) -> None:
        self._results = [
            RetrievedChunk(chunk=_chunk(source), score=float(len(sources) - index))
            for index, source in enumerate(sources)
        ]
        self.received_filters: list[RetrievalFilters | None] = []

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        filters: RetrievalFilters | None = None,
    ) -> list[RetrievedChunk]:
        self.received_filters.append(filters)
        allowed = [
            result
            for result in self._results
            if filters is None or filters.allows(result.chunk)
        ]
        return allowed[:top_k]


class HybridRrfRetrieverTests(unittest.TestCase):
    def test_rrf_rewards_documents_supported_by_both_retrievers(self) -> None:
        hybrid = HybridRrfRetriever(
            [StubRetriever(["menu:a", "menu:b"]), StubRetriever(["menu:b", "menu:c"])]
        )

        results = hybrid.search("query", top_k=3)

        self.assertEqual("menu:b", results[0].chunk.source)
        self.assertEqual(3, len(results))

    def test_filters_are_forwarded_to_every_retriever(self) -> None:
        first = StubRetriever(["menu:a", "menu:b"])
        second = StubRetriever(["menu:b", "menu:c"])
        filters = RetrievalFilters(excluded_source_ids=frozenset({"menu:b"}))
        hybrid = HybridRrfRetriever([first, second])

        results = hybrid.search("query", top_k=3, filters=filters)

        self.assertIs(filters, first.received_filters[0])
        self.assertIs(filters, second.received_filters[0])
        self.assertNotIn("menu:b", [result.chunk.source for result in results])

    def test_duplicate_sources_from_one_retriever_are_counted_once(self) -> None:
        hybrid = HybridRrfRetriever([StubRetriever(["menu:a", "menu:a", "menu:b"])])

        results = hybrid.search("query", top_k=3)

        self.assertEqual(["menu:a", "menu:b"], [result.chunk.source for result in results])

    def test_same_source_different_chunks_are_not_collapsed(self) -> None:
        class SameFileRetriever:
            def search(
                self,
                query: str,
                top_k: int = 5,
                *,
                filters: RetrievalFilters | None = None,
            ) -> list[RetrievedChunk]:
                return [
                    RetrievedChunk(chunk=_chunk("faq.md", "Giờ mở cửa"), score=2.0),
                    RetrievedChunk(chunk=_chunk("faq.md", "WiFi"), score=1.0),
                ][:top_k]

        hybrid = HybridRrfRetriever([SameFileRetriever()])

        results = hybrid.search("query", top_k=5)

        self.assertEqual(
            ["Giờ mở cửa", "WiFi"],
            [result.chunk.title for result in results],
        )

    def test_equal_fused_scores_are_ordered_by_source(self) -> None:
        hybrid = HybridRrfRetriever(
            [StubRetriever(["menu:b"]), StubRetriever(["menu:a"])]
        )

        results = hybrid.search("query", top_k=2)

        self.assertEqual(["menu:a", "menu:b"], [result.chunk.source for result in results])

    def test_invalid_configuration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            HybridRrfRetriever([])
        with self.assertRaises(ValueError):
            HybridRrfRetriever([StubRetriever([])], weights=[1.0, 2.0])
        with self.assertRaises(ValueError):
            HybridRrfRetriever([StubRetriever([])], rrf_k=0)


if __name__ == "__main__":
    unittest.main()
