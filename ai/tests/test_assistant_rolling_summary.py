"""Assistant responses include updated_rolling_summary for backend persistence."""
from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _StubLlmClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str:
        return (
            '{"content":"Goi y pho bo.","suggested_cart_actions":[],"'
            '"guardrail_flags":[],"claims":[]}'
        )


class _EmptyRetriever:
    def search(self, _query: str, _top_k: int) -> list:
        return [
            type("Hit", (), {
                "chunk": type("Chunk", (), {
                    "chunk_id": "faq-hours",
                    "document_id": "faq.md",
                    "section_path": ["FAQ"],
                    "source": "faq.md",
                    "title": "FAQ",
                    "content": "Gio mo cua 10h-22h",
                    "citation": "faq.md",
                    "tags": [],
                })(),
                "score": 0.04,
            })()
        ]


class AssistantRollingSummaryResponseTests(unittest.TestCase):
    def test_chat_response_includes_updated_rolling_summary(self) -> None:
        config = AiServiceConfig(
            provider="9router",
            base_url="https://example.com/v1",
            api_key="test-key",
            model="oc/deepseek-v4-flash-free",
            llm_timeout_seconds=1,
            request_budget_seconds=2,
            max_retry=0,
            max_tokens=700,
            reasoning_effort="low",
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=3,
            retrieval_method="bm25",
        )
        service = AiAssistantService(config, llm_client=_StubLlmClient())
        service._retriever = _EmptyRetriever()  # noqa: SLF001

        response = asyncio.run(
            service.chat(
                {
                    "message": "2 nguoi an gi re",
                    "history": [],
                    "rolling_summary": "",
                    "menu_items": [
                        {
                            "id": "m_001",
                            "name": "Phở bò",
                            "description": "Phở",
                            "category_name": "Phở",
                            "price_vnd": 85000,
                            "is_available": True,
                        }
                    ],
                    "table_code": "T01",
                }
            )
        )

        summary = response.get("updated_rolling_summary")
        self.assertIsInstance(summary, str)
        self.assertTrue(summary)
        self.assertIn("Lượt gần đây:", summary)


if __name__ == "__main__":
    unittest.main()
