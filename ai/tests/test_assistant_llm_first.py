"""Assistant routing when AI_LLM_FIRST=true (default)."""
from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _CountingClient:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, _messages: list[dict[str, str]]) -> str:
        self.calls += 1
        return json.dumps(
            {
                "content": "Mình gợi ý vài món ăn phù hợp.",
                "suggested_cart_actions": [
                    {"menu_item_id": "m_001", "name": "Nem rán", "quantity": 1},
                ],
                "claims": [],
                "guardrail_flags": [],
            },
            ensure_ascii=False,
        )


def _menu() -> list[dict]:
    return [
        {
            "id": "m_001",
            "name": "Nem rán Hà Nội",
            "description": "Khai vị nhậu",
            "category_name": "Khai vị",
            "category_id": "cat_appetizer",
            "price_vnd": 65000,
            "is_available": True,
            "tags": ["nhau"],
        },
        {
            "id": "m_drink",
            "name": "Bia Tiger Crystal",
            "description": "Bia",
            "category_name": "Bia & Rượu",
            "category_id": "cat_alcohol",
            "price_vnd": 35000,
            "is_available": True,
        },
    ]


def _llm_first_config(*, llm_first: bool = True) -> AiServiceConfig:
    return AiServiceConfig(
        provider="9router",
        base_url="http://localhost:20128/v1",
        api_key="test-key",
        model="oc/deepseek-v4-flash-free",
        llm_timeout_seconds=5,
        request_budget_seconds=8,
        max_retry=0,
        max_tokens=700,
        reasoning_effort="low",
        knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
        top_k=3,
        retrieval_method="bm25",
        llm_first=llm_first,
    )


class AssistantLlmFirstTests(unittest.TestCase):
    def test_party_size_recommendation_calls_llm_not_fast_path(self) -> None:
        client = _CountingClient()
        service = AiAssistantService(_llm_first_config(), llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Gợi ý món nhẹ cho 2 người",
                    "history": [],
                    "session_state": {"constraints": {"party_size": 2}},
                    "menu_items": _menu(),
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(1, client.calls)
        self.assertEqual("llm", response["latency_ms"]["path"])
        self.assertNotEqual("party_fast_path", response["latency_ms"]["path"])

    def test_nhau_query_calls_llm(self) -> None:
        client = _CountingClient()
        service = AiAssistantService(_llm_first_config(), llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Món dễ ăn nhậu",
                    "history": [],
                    "menu_items": _menu(),
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(1, client.calls)
        self.assertEqual("llm", response["latency_ms"]["path"])
        self.assertTrue(response.get("provider_available"))

    def test_pho_presence_uses_menu_not_llm_when_llm_first(self) -> None:
        client = _CountingClient()
        service = AiAssistantService(_llm_first_config(), llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Ở đây có phở không",
                    "history": [],
                    "menu_items": [
                        {
                            "id": "m_pho",
                            "name": "Phở bò tái",
                            "description": "Phở",
                            "category_name": "Phở",
                            "category_id": "cat_pho",
                            "price_vnd": 85000,
                            "is_available": True,
                        },
                        *_menu(),
                    ],
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(0, client.calls)
        self.assertEqual("menu_presence", response["latency_ms"]["path"])
        self.assertIn("phở", response["content"].casefold())

    def test_llm_first_false_still_allows_party_fast_path(self) -> None:
        client = _CountingClient()
        service = AiAssistantService(
            _llm_first_config(llm_first=False),
            llm_client=client,
        )
        response = asyncio.run(
            service.chat(
                {
                    "message": "Còn món khác không?",
                    "history": [],
                    "session_state": {"constraints": {"party_size": 2}},
                    "menu_items": _menu(),
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(0, client.calls)
        self.assertEqual("party_fast_path", response["latency_ms"]["path"])


if __name__ == "__main__":
    unittest.main()
