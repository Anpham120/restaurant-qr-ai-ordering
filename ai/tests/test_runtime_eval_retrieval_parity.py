from __future__ import annotations

import unittest
from collections.abc import Sequence

from app.rag.knowledge_base import KnowledgeChunk
from app.rag.retrieval_factory import build_retriever_stack
from evaluation.run_retrieval_experiment import RetrievalMethod, _build_method


class _DeterministicEncoder:
    model_name = "fake/parity"
    model_revision = "test-revision"
    dimension = 4

    @staticmethod
    def _encode(text: str) -> tuple[float, ...]:
        lowered = text.casefold()
        return (
            float(lowered.count("wifi")),
            float(lowered.count("thanh toán") + lowered.count("thanh toan")),
            float(lowered.count("mở cửa") + lowered.count("mo cua")),
            1.0,
        )

    def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [self._encode(text) for text in texts]

    def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [self._encode(text) for text in texts]


class RuntimeEvalRetrievalParityTests(unittest.TestCase):
    def test_same_hybrid_query_returns_identical_chunk_ids_and_scores(self) -> None:
        chunks = [
            KnowledgeChunk(
                source="faq.md",
                title="WiFi",
                content="Nhà hàng có wifi miễn phí.",
                tags=("faq",),
            ),
            KnowledgeChunk(
                source="faq.md",
                title="Thanh toán",
                content="Có thể thanh toán bằng tiền mặt hoặc VietQR.",
                tags=("payment",),
            ),
            KnowledgeChunk(
                source="info.md",
                title="Giờ mở cửa",
                content="Nhà hàng mở cửa từ 8 giờ.",
                tags=("hours",),
            ),
        ]
        encoder = _DeterministicEncoder()
        runtime = build_retriever_stack(chunks, "hybrid", encoder=encoder).retriever
        eval_factory, _ = _build_method(RetrievalMethod.HYBRID_E5_SMALL, encoder)
        evaluation = eval_factory(chunks)

        runtime_results = runtime.search("wifi và thanh toán", top_k=3)
        evaluation_results = evaluation.search("wifi và thanh toán", top_k=3)

        self.assertEqual(
            [item.chunk.chunk_id for item in runtime_results],
            [item.chunk.chunk_id for item in evaluation_results],
        )
        self.assertEqual(
            [item.score for item in runtime_results],
            [item.score for item in evaluation_results],
        )


if __name__ == "__main__":
    unittest.main()
