from __future__ import annotations

import unittest
from collections.abc import Sequence

from app.rag.embedding_retriever import DenseRetriever, SentenceTransformerE5Encoder
from app.rag.embedding_retriever import build_document_vectors_cached
from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retriever import RetrievalFilters


class FakeEncoder:
    model_name = "fake-semantic-encoder"
    model_revision = "test-revision"
    dimension = 3

    def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        vectors = []
        for text in texts:
            if "Tôm nướng" in text:
                vectors.append((1.0, 0.0, 0.0))
            elif "Bò nướng" in text:
                vectors.append((0.0, 1.0, 0.0))
            else:
                vectors.append((0.0, 0.0, 1.0))
        return vectors

    def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [(1.0, 0.0, 0.0) for _ in texts]


class DenseRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shrimp = KnowledgeChunk(
            source="menu:shrimp",
            title="Tôm nướng",
            content="Hải sản nướng",
            tags=("hai-san",),
        )
        self.beef = KnowledgeChunk(
            source="menu:beef",
            title="Bò nướng",
            content="Thịt bò nướng",
            tags=("thit",),
        )
        self.retriever = DenseRetriever([self.beef, self.shrimp], FakeEncoder())

    def test_semantic_similarity_ranks_the_expected_document_first(self) -> None:
        results = self.retriever.search("Tôi muốn món biển")

        self.assertEqual("menu:shrimp", results[0].chunk.source)
        self.assertEqual(1.0, results[0].score)

    def test_metadata_filters_remove_candidates_before_ranking(self) -> None:
        filters = RetrievalFilters(excluded_source_ids=frozenset({"menu:shrimp"}))

        results = self.retriever.search("Tôi muốn món biển", filters=filters)

        self.assertEqual(["menu:beef"], [result.chunk.source for result in results])

    def test_model_provenance_is_exposed(self) -> None:
        self.assertEqual("fake-semantic-encoder", self.retriever.model_name)
        self.assertEqual("test-revision", self.retriever.model_revision)

    def test_e5_prefixes_queries_and_documents_as_required(self) -> None:
        self.assertEqual(
            ["query: món hải sản"],
            SentenceTransformerE5Encoder._prefix(["  món hải sản  "], "query"),
        )
        self.assertEqual(
            ["passage: thực đơn"],
            SentenceTransformerE5Encoder._prefix(["thực đơn"], "passage"),
        )

    def test_wrong_document_dimension_is_rejected(self) -> None:
        class WrongDimensionEncoder(FakeEncoder):
            def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
                return [(1.0, 0.0) for _ in texts]

        with self.assertRaisesRegex(ValueError, "Expected embedding dimension"):
            DenseRetriever([self.shrimp], WrongDimensionEncoder())

    def test_zero_query_vector_is_rejected(self) -> None:
        class ZeroQueryEncoder(FakeEncoder):
            def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
                return [(0.0, 0.0, 0.0) for _ in texts]

        retriever = DenseRetriever([self.shrimp], ZeroQueryEncoder())

        with self.assertRaisesRegex(ValueError, "must not be all zeros"):
            retriever.search("món biển")

    def test_vector_cache_keys_by_chunk_id_not_source_filename(self) -> None:
        chunks = [
            KnowledgeChunk(source="faq.md", title="Giờ mở cửa", content="Nhà hàng mở cửa.", tags=("faq",)),
            KnowledgeChunk(source="faq.md", title="WiFi", content="Nhà hàng có wifi.", tags=("faq",)),
        ]
        texts = ["Tôm nướng", "Bò nướng"]
        cache: dict[str, tuple[tuple[float, ...], str]] = {}

        vectors = build_document_vectors_cached(chunks, texts, FakeEncoder(), cache)

        self.assertEqual(2, len(vectors))
        self.assertEqual(2, len(cache))
        self.assertEqual(
            {chunk.chunk_id for chunk in chunks},
            set(cache.keys()),
        )


if __name__ == "__main__":
    unittest.main()
