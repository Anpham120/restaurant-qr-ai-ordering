from __future__ import annotations

import asyncio
import unittest
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _CountingRetriever:
    def __init__(self) -> None:
        self.calls = 0

    def search(self, *_args, **_kwargs):
        self.calls += 1
        return []


def _config() -> AiServiceConfig:
    return AiServiceConfig(
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
        pipeline_version="v3",
    )


def _payload(message: str) -> dict:
    return {
        "contract_version": "v2",
        "message": message,
        "history": [
            {
                "role": "assistant",
                "content": "Mình vừa gợi ý Phở bò tái.",
                "suggested_cart_actions": [
                    {"menu_item_id": "m_001", "name": "Phở bò tái"}
                ],
            }
        ],
        "session_state": {
            "referenced_menu_item_ids": ["m_001"],
            "suggested_menu_item_ids": ["m_001"],
            "rolling_summary": "Đang trao đổi về Phở bò tái.",
            "memory_version": "v2",
        },
        "live_context": {
            "catalog_version": "catalog-42",
            "menu_items": [
                {
                    "id": "m_001",
                    "name": "Phở bò tái",
                    "price_vnd": 85000,
                    "is_available": True,
                }
            ],
        },
        "menu_items": [
            {
                "id": "m_001",
                "name": "Phở bò tái",
                "price_vnd": 85000,
                "is_available": True,
            }
        ],
    }


class EvidenceRoutingV2Tests(unittest.TestCase):
    def test_referential_price_question_uses_live_data_without_rag_or_llm(self) -> None:
        service = AiAssistantService(_config())
        retriever = _CountingRetriever()
        service._retriever = retriever  # noqa: SLF001 - explicit route probe

        response = asyncio.run(service.chat(_payload("Cái đó bao nhiêu tiền?")))

        self.assertEqual(0, retriever.calls)
        self.assertEqual("live_data", response["decision"]["route"])
        self.assertEqual("m_001", response["evidence"][0]["menu_item_id"])
        self.assertTrue(response["claims"][0]["verified"])
        self.assertIn("85.000", response["content"])
        self.assertEqual("v3", response["pipeline_version"])
        self.assertEqual("not_called", response["provider_status"])
        self.assertEqual(
            ["m_001"], response["session_updates"]["referenced_menu_item_ids"]
        )

    def test_missing_nutrition_data_abstains_before_rag(self) -> None:
        service = AiAssistantService(_config())
        retriever = _CountingRetriever()
        service._retriever = retriever  # noqa: SLF001

        response = asyncio.run(service.chat(_payload("Món đó bao nhiêu calo?")))

        self.assertEqual(0, retriever.calls)
        self.assertEqual("live_data", response["decision"]["route"])
        self.assertFalse(response["decision"]["evidence_sufficient"])
        self.assertEqual(
            "missing_live_nutrition_data", response["decision"]["abstain_reason"]
        )
        self.assertIn("chưa có dữ liệu", response["content"].casefold())
        self.assertEqual([], response["claims"])

    def test_specific_allergy_question_fails_closed_without_live_ingredients(self) -> None:
        service = AiAssistantService(_config())
        retriever = _CountingRetriever()
        service._retriever = retriever  # noqa: SLF001

        response = asyncio.run(service.chat(_payload("Món đó có đậu phộng không?")))

        self.assertEqual(0, retriever.calls)
        self.assertEqual("live_data", response["decision"]["route"])
        self.assertFalse(response["decision"]["evidence_sufficient"])
        self.assertEqual(
            "missing_live_allergen_data", response["decision"]["abstain_reason"]
        )
        self.assertIn("nhân viên", response["content"].casefold())
        self.assertIn("ALLERGY_DISCLAIMER", response["guardrail_flags"])

    def test_stream_and_non_stream_preserve_identical_typed_state(self) -> None:
        service = AiAssistantService(_config())
        payload = _payload("Cái đó bao nhiêu tiền?")
        direct = asyncio.run(service.chat(payload))

        async def collect_final() -> dict:
            final: dict = {}
            async for event in service.chat_stream(payload):
                if event["type"] == "final":
                    final = event["data"]
            return final

        streamed = asyncio.run(collect_final())

        for key in ("decision", "evidence", "claims", "session_updates"):
            with self.subTest(key=key):
                self.assertEqual(direct[key], streamed[key])

    def test_typed_constraints_and_suggestion_ledger_survive_truncated_history(self) -> None:
        service = AiAssistantService(_config())
        retriever = _CountingRetriever()
        service._retriever = retriever  # noqa: SLF001
        menu_items = [
            {
                "id": f"m_{index:03d}",
                "name": f"Món dùng chung {index}",
                "description": "Món phần lớn phù hợp nhóm đông",
                "category_name": "Món chính",
                "price_vnd": 70000 + index * 10000,
                "is_available": True,
                "tags": ["shared", "family"],
            }
            for index in range(1, 8)
        ]
        payload = {
            "contract_version": "v2",
            "message": "Còn món khác không?",
            "history": [],
            "session_id": "long-session-01",
            "session_state": {
                "facts": [{"key": "occasion", "value": "family"}],
                "constraints": {"party_size": 6, "budget_vnd": 700000},
                "suggested_menu_item_ids": ["m_001"],
                "rolling_summary": "Đã gợi ý m_001 cho nhóm sáu người.",
                "memory_version": "v2",
            },
            "live_context": {
                "catalog_version": "catalog-long-session",
                "menu_items": menu_items,
            },
        }

        response = asyncio.run(service.chat(payload))

        self.assertEqual(0, retriever.calls)
        self.assertEqual("party_fast_path", response["latency_ms"]["path"])
        suggested_ids = {
            action["menu_item_id"] for action in response["suggested_cart_actions"]
        }
        self.assertNotIn("m_001", suggested_ids)
        self.assertIn("m_001", response["session_updates"]["suggested_menu_item_ids"])
        self.assertTrue(
            suggested_ids.issubset(
                set(response["session_updates"]["suggested_menu_item_ids"])
            )
        )
        self.assertEqual(6, response["session_updates"]["constraints"]["party_size"])
        self.assertEqual(700000, response["session_updates"]["constraints"]["budget_vnd"])
        self.assertEqual(
            [{"key": "occasion", "value": "family"}],
            response["session_updates"]["facts"],
        )


if __name__ == "__main__":
    unittest.main()
