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


class _PlannerClient:
    def __init__(self, *, planner_raw: str | None = None) -> None:
        self.planner_calls = 0
        self.answer_calls = 0
        self.planner_raw = planner_raw or json.dumps(
            {
                "intent": "recommend",
                "response_mode": "recommendation",
                "category": "pho bun",
                "tags": [],
                "referent_ordinal": None,
                "constraint_patch": {"party_size": 4},
                "remove_constraints": [],
                "needs_clarification": False,
                "clarification_slot": None,
                "confidence": 0.96,
            },
            ensure_ascii=False,
        )

    async def complete_structured(
        self,
        _messages,
        _schema,
        _schema_name,
        **_kwargs,
    ) -> str:
        self.planner_calls += 1
        return self.planner_raw

    async def complete(self, _messages: list[dict[str, str]]) -> str:
        self.answer_calls += 1
        return json.dumps(
            {
                "content": "Mình gợi ý Phở bò tái cho nhóm 4 người.",
                "suggested_cart_actions": [
                    {
                        "menu_item_id": "m_pho",
                        "name": "Phở bò tái",
                        "price_vnd": 85000,
                        "quantity": 1,
                    }
                ],
                "claims": [
                    {
                        "text": "Phở bò tái có trong thực đơn hiện tại.",
                        "evidence_ids": ["m_pho"],
                    }
                ],
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

    def test_evidence_first_profile_lists_pho_without_calling_llm(self) -> None:
        client = _CountingClient()
        config = _llm_first_config()
        config = AiServiceConfig(
            **{
                **config.__dict__,
                "pipeline_profile": "evidence_first_v2",
            }
        )
        service = AiAssistantService(config, llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Nhà hàng mình có những món phở gì nhỉ",
                    "history": [],
                    "menu_items": [
                        {
                            "id": "m_pho_bo",
                            "name": "Phở bò tái",
                            "category_name": "Phở & Bún",
                            "category_id": "cat_pho_bun",
                            "price_vnd": 85000,
                            "is_available": True,
                        },
                        {
                            "id": "m_pho_ga",
                            "name": "Phở gà ta",
                            "category_name": "Phở & Bún",
                            "category_id": "cat_pho_bun",
                            "price_vnd": 80000,
                            "is_available": True,
                        },
                        *_menu(),
                    ],
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(0, client.calls)
        self.assertEqual("catalog_fast_path", response["latency_ms"]["path"])
        self.assertIn("Phở bò tái", response["content"])
        self.assertIn("Phở gà ta", response["content"])

    def test_evidence_first_profile_resolves_nhau_tag_without_calling_llm(self) -> None:
        client = _CountingClient()
        config = _llm_first_config()
        config = AiServiceConfig(
            **{
                **config.__dict__,
                "pipeline_profile": "evidence_first_v2",
            }
        )
        service = AiAssistantService(config, llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Mình có món nhậu không",
                    "history": [],
                    "menu_items": _menu(),
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(0, client.calls)
        self.assertEqual("menu_presence", response["latency_ms"]["path"])
        self.assertIn("Nem rán", response["content"])

    def test_evidence_first_profile_lists_seafood_category_without_treating_it_as_allergy(self) -> None:
        client = _CountingClient()
        config = _llm_first_config()
        config = AiServiceConfig(
            **{
                **config.__dict__,
                "pipeline_profile": "evidence_first_v2",
            }
        )
        service = AiAssistantService(config, llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Cho mình xem các món hải sản",
                    "history": [],
                    "menu_items": [
                        {
                            "id": "m_seafood",
                            "name": "Nghêu hấp sả",
                            "description": "Hải sản hấp",
                            "category_name": "Hải sản",
                            "category_id": "cat_seafood",
                            "price_vnd": 95000,
                            "tags": ["co hai san"],
                            "is_available": True,
                        },
                        *_menu(),
                    ],
                }
            )
        )

        self.assertEqual(0, client.calls)
        self.assertEqual("catalog_fast_path", response["latency_ms"]["path"])
        self.assertIn("m_seafood", response["resolved_menu_item_ids"])
        self.assertNotIn("ALLERGY_DISCLAIMER", response["guardrail_flags"])

    def test_persisted_allergy_is_enforced_on_later_recommendation_turn(self) -> None:
        client = _CountingClient()
        config = _llm_first_config()
        config = AiServiceConfig(
            **{
                **config.__dict__,
                "pipeline_profile": "evidence_first_v2",
            }
        )
        service = AiAssistantService(config, llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Gợi ý món khai vị cho tôi",
                    "history": [
                        {"role": "user", "content": "Tôi dị ứng đậu phộng"},
                    ],
                    "session_state": {
                        "constraints": {"allergens": ["dau phong"]},
                        "memory_version": "v2",
                    },
                    "menu_items": [
                        {
                            "id": "m_unsafe",
                            "name": "Gỏi cuốn tôm thịt",
                            "description": "Có đậu phộng",
                            "category_name": "Khai vị",
                            "category_id": "cat_appetizer",
                            "price_vnd": 65000,
                            "tags": ["co dau phong"],
                            "is_available": True,
                        },
                        {
                            "id": "m_safe",
                            "name": "Bánh cuốn Thanh Trì",
                            "description": "Món hấp thanh nhẹ",
                            "category_name": "Khai vị",
                            "category_id": "cat_appetizer",
                            "price_vnd": 55000,
                            "tags": ["khong cay"],
                            "is_available": True,
                        },
                    ],
                }
            )
        )

        self.assertNotIn("m_unsafe", response["resolved_menu_item_ids"])
        self.assertIn("ALLERGY_DISCLAIMER", response["guardrail_flags"])

    def test_planner_profile_calls_structured_planner_before_answer_and_persists_frame(self) -> None:
        client = _PlannerClient()
        config = _llm_first_config()
        config = AiServiceConfig(
            **{
                **config.__dict__,
                "pipeline_profile": "planner_state_v3",
            }
        )
        service = AiAssistantService(config, llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Gợi ý món phở cho nhóm mình",
                    "history": [],
                    "session_state": {
                        "memory_version": "v2",
                        "conversation_frame": {"turn_sequence": 2},
                    },
                    "menu_items": [
                        {
                            "id": "m_pho",
                            "name": "Phở bò tái",
                            "description": "Phở bò",
                            "category_name": "Phở & Bún",
                            "category_id": "cat_pho_bun",
                            "price_vnd": 85000,
                            "is_available": True,
                        }
                    ],
                    "table_code": "T01",
                }
            )
        )

        self.assertEqual(1, client.planner_calls)
        self.assertEqual(1, client.answer_calls)
        self.assertEqual("planner_state_v3", response["pipeline_profile"])
        self.assertEqual(4, response["session_updates"]["constraints"]["party_size"])
        self.assertEqual(
            3,
            response["session_updates"]["conversation_frame"]["turn_sequence"],
        )
        self.assertEqual(
            "recommend",
            response["session_updates"]["conversation_frame"]["active_intent"],
        )

    def test_planner_profile_marks_degraded_planner_without_persisting_invented_state(self) -> None:
        client = _PlannerClient(planner_raw="not-json")
        config = _llm_first_config()
        config = AiServiceConfig(
            **{
                **config.__dict__,
                "pipeline_profile": "planner_state_v3",
            }
        )
        service = AiAssistantService(config, llm_client=client)
        response = asyncio.run(
            service.chat(
                {
                    "message": "Gợi ý món ngon đi",
                    "history": [],
                    "session_state": {"memory_version": "v2"},
                    "menu_items": [
                        {
                            "id": "m_pho",
                            "name": "Phở bò tái",
                            "description": "Phở bò",
                            "category_name": "Phở & Bún",
                            "category_id": "cat_pho_bun",
                            "price_vnd": 85000,
                            "is_available": True,
                        }
                    ],
                }
            )
        )

        self.assertEqual(1, client.planner_calls)
        self.assertIn("SEMANTIC_PLANNER_DEGRADED", response["guardrail_flags"])
        self.assertEqual(
            {},
            response["session_updates"]["conversation_frame"].get(
                "constraint_provenance",
                {},
            ),
        )


if __name__ == "__main__":
    unittest.main()
