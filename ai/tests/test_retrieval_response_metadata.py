from __future__ import annotations

import unittest
import asyncio
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _FailingEncoder:
    model_name = "test-failing-encoder"
    model_revision = "test"
    dimension = 2

    def encode_documents(self, texts):
        raise RuntimeError("encoder unavailable")

    def encode_queries(self, texts):
        raise RuntimeError("encoder unavailable")


class RetrievalResponseMetadataTests(unittest.TestCase):
    def test_runtime_search_returns_stable_v2_chunk_identity(self) -> None:
        config = AiServiceConfig(
            provider="9router",
            base_url="http://localhost:20128/v1",
            api_key="",
            model="cx/gpt-5.5",
            llm_timeout_seconds=1,
            request_budget_seconds=2,
            max_retry=0,
            max_tokens=700,
            reasoning_effort="low",
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=3,
            retrieval_method="bm25",
        )
        service = AiAssistantService(config)

        results = service.search("giờ mở cửa", 3)

        self.assertTrue(results)
        for item in results:
            with self.subTest(chunk_id=item.get("chunk_id")):
                self.assertTrue(str(item["chunk_id"]).startswith("kb:"))
                self.assertTrue(item["document_id"])
                self.assertTrue(item["section_path"])
                self.assertEqual(64, len(item["content_hash"]))
                self.assertIn("risk_tier", item)

    def test_chat_response_records_effective_retriever_when_hybrid_falls_back(self) -> None:
        config = AiServiceConfig(
            provider="9router",
            base_url="http://localhost:20128/v1",
            api_key="",
            model="cx/gpt-5.5",
            llm_timeout_seconds=1,
            request_budget_seconds=2,
            max_retry=0,
            max_tokens=700,
            reasoning_effort="low",
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=3,
            retrieval_method="hybrid",
        )
        service = AiAssistantService(config, embedding_encoder=_FailingEncoder())

        response = asyncio.run(
            service.chat(
                {
                    "message": "Nhà hàng có chỗ đậu xe không?",
                    "history": [],
                    "menu_items": [],
                    "table_code": "T01",
                    "session_id": "retriever-runtime-meta",
                    "language": "vi",
                }
            )
        )

        self.assertEqual("hybrid", response["retriever_runtime"]["requested_method"])
        self.assertEqual("bm25-fallback", response["retriever_runtime"]["effective_method"])
        self.assertTrue(response["retriever_runtime"]["fallback_used"])
        self.assertEqual("RuntimeError", response["retriever_runtime"]["fallback_error_type"])


if __name__ == "__main__":
    unittest.main()
