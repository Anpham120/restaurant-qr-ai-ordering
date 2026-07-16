from __future__ import annotations

import unittest

from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retriever import BM25Retriever, RetrievalFilters


class BM25RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spicy_shrimp = KnowledgeChunk(
            source="menu:m_001",
            title="Tôm sốt cay",
            content="Tôm biển dùng với sốt ớt",
            tags=("hai-san", "cay"),
        )
        self.steamed_shrimp = KnowledgeChunk(
            source="menu:m_002",
            title="Tôm hấp",
            content="Tôm biển hấp sả",
            tags=("hai-san", "thanh-dam"),
        )
        self.retriever = BM25Retriever([self.spicy_shrimp, self.steamed_shrimp])

    def test_search_keeps_existing_positional_top_k_contract(self) -> None:
        results = self.retriever.search("tôm", 1)

        self.assertEqual(1, len(results))

    def test_hard_filters_are_applied_before_ranking(self) -> None:
        filters = RetrievalFilters(
            excluded_source_ids=frozenset({"menu:m_001"}),
            required_tags=frozenset({"hai-san"}),
        )

        results = self.retriever.search("tôm", filters=filters)

        self.assertEqual(["menu:m_002"], [result.chunk.source for result in results])

    def test_allowed_sources_take_precedence_over_unrestricted_candidates(self) -> None:
        filters = RetrievalFilters(allowed_source_ids=frozenset({"menu:m_002"}))

        results = self.retriever.search("tôm", filters=filters)

        self.assertEqual(["menu:m_002"], [result.chunk.source for result in results])

    def test_equal_scores_are_ordered_by_source(self) -> None:
        chunks = [
            KnowledgeChunk("menu:b", "Tôm", "Tôm", ("hai-san",)),
            KnowledgeChunk("menu:a", "Tôm", "Tôm", ("hai-san",)),
        ]

        results = BM25Retriever(chunks).search("tôm")

        self.assertEqual(["menu:a", "menu:b"], [result.chunk.source for result in results])

    def test_non_positive_top_k_returns_no_results(self) -> None:
        self.assertEqual([], self.retriever.search("tôm", 0))


if __name__ == "__main__":
    unittest.main()
