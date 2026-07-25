"""Verify assistant skips LLM when retrieval confidence is very_low."""
from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _CountingClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, _messages: list[dict[str, str]]) -> str:
        self.calls += 1
        return '{"content":"ok","suggested_cart_actions":[],"guardrail_flags":[]}'


class _EmptyRetriever:
    def search(self, _query: str, _top_k: int) -> list:
        return []


class AssistantConfidenceGateTests(unittest.TestCase):
    def test_very_low_retrieval_skips_llm_client(self) -> None:
        client = _CountingClient()
        config = AiServiceConfig(
            provider="9router",
            base_url="https://example.com/v1",
            api_key="test-key",
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
        service = AiAssistantService(config, llm_client=client)
        service._retriever = _EmptyRetriever()  # noqa: SLF001 — test seam

        response = asyncio.run(
            service.chat(
                {
                    "message": "zzqwx nonsense retrieval probe",
                    "history": [],
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

        self.assertEqual(0, client.calls)
        self.assertIn("RETRIEVAL_FAILED", response.get("guardrail_flags", []))
        self.assertTrue(response.get("content"))


if __name__ == "__main__":
    unittest.main()
