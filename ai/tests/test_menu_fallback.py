from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _FailingClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str:
        raise TimeoutError("simulated timeout")


class MenuFallbackTests(unittest.TestCase):
    def test_recommendation_query_falls_back_to_real_menu_items(self) -> None:
        config = AiServiceConfig(
            provider="9router",
            base_url="http://localhost:20128/v1",
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
        service = AiAssistantService(config, llm_client=_FailingClient())
        menu = [
            {
                "id": "m_085",
                "name": "Bia Tiger",
                "description": "Bia lon",
                "category_name": "Bia & rượu",
                "tags": ["Nhậu", "Bia"],
                "price_vnd": 25000,
                "is_available": True,
            },
            {
                "id": "m_002",
                "name": "Nem rán Hà Nội",
                "description": "Khai vị",
                "category_name": "Khai vị",
                "tags": ["Nhậu", "Chiên"],
                "price_vnd": 55000,
                "is_available": True,
            },
        ]

        response = asyncio.run(
            service.chat(
                {
                    "message": "gợi ý cho tôi các món để ăn nhậu",
                    "history": [],
                    "menu_items": menu,
                    "table_code": "T03",
                }
            )
        )

        self.assertFalse(response["provider_available"])
        self.assertIn("AI_PROVIDER_UNAVAILABLE", response["guardrail_flags"])
        self.assertGreater(len(response["suggested_cart_actions"]), 0)
        self.assertNotIn("combo-pairing.md", response["content"])
        self.assertNotIn("LLM", response["content"])

    def test_stream_without_llm_uses_menu_fallback(self) -> None:
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
        service = AiAssistantService(config, llm_client=None)
        menu = [
            {
                "id": "m_085",
                "name": "Bia Tiger",
                "description": "Bia lon",
                "category_name": "Bia & rượu",
                "tags": ["Nhậu", "Bia"],
                "price_vnd": 25000,
                "is_available": True,
            },
            {
                "id": "m_002",
                "name": "Nem rán Hà Nội",
                "description": "Khai vị",
                "category_name": "Khai vị",
                "tags": ["Nhậu", "Chiên"],
                "price_vnd": 55000,
                "is_available": True,
            },
        ]

        async def collect_stream() -> dict:
            final: dict = {}
            async for event in service.chat_stream(
                {
                    "message": "gợi ý cho tôi các món để ăn nhậu",
                    "history": [],
                    "menu_items": menu,
                    "table_code": "T03",
                }
            ):
                if event["type"] == "final":
                    final = event["data"]
            return final

        response = asyncio.run(collect_stream())

        self.assertFalse(response["provider_available"])
        self.assertGreater(len(response["suggested_cart_actions"]), 0)
        self.assertNotIn("trợ lý AI đang hơi chậm", response["content"])


if __name__ == "__main__":
    unittest.main()
