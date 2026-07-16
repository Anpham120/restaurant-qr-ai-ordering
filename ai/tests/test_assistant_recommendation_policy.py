from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _RecommendationClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, _messages: list[dict[str, str]]) -> str:
        self.calls += 1
        return json.dumps(
            {
                "content": "Mình đã chọn các món phù hợp.",
                "suggested_cart_actions": [
                    {"menu_item_id": "m_001", "quantity": 1},
                    {"menu_item_id": "m_002", "quantity": 1},
                ],
                "guardrail_flags": [],
            },
            ensure_ascii=False,
        )


class AssistantRecommendationPolicyTests(unittest.TestCase):
    def test_explicit_card_count_excludes_items_suggested_earlier_in_session(self) -> None:
        client = _RecommendationClient()
        config = AiServiceConfig(
            provider="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key="test-key",
            model="gemini-test",
            timeout_seconds=1,
            max_retry=0,
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=3,
            retrieval_method="bm25",
        )
        service = AiAssistantService(config, llm_client=client)
        menu = [
            {
                "id": f"m_{index:03d}",
                "name": f"Món ngon {index}",
                "description": "Món ngon phù hợp để tư vấn",
                "category_name": "Món chính",
                "price_vnd": 50000 + index,
                "is_available": True,
            }
            for index in range(1, 6)
        ]

        response = asyncio.run(
            service.chat(
                {
                    "message": "Gợi ý cho tôi 3 món",
                    "history": [],
                    "session_memory": "SUGGESTED_MENU_ITEM_IDS: m_001",
                    "menu_items": menu,
                    "table_code": "T01",
                }
            )
        )

        action_ids = [item["menu_item_id"] for item in response["suggested_cart_actions"]]
        self.assertEqual(3, len(action_ids))
        self.assertNotIn("m_001", action_ids)
        self.assertEqual(3, len(set(action_ids)))
        self.assertEqual(1, client.calls)
        self.assertIn("CUSTOMER_CONFIRMATION_REQUIRED", response["guardrail_flags"])


if __name__ == "__main__":
    unittest.main()
