from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.rag.kb_info_fast_path import _build_fast_path_response
from app.rag.knowledge_base import KnowledgeChunk
from app.rag.menu_presence_fast_path import try_menu_presence_fast_path
from app.services.assistant import _finalize_response_payload


class FastPathClaimGroundingTests(unittest.TestCase):
    def test_kb_fast_path_exposes_stable_chunk_evidence_and_verified_claim(self) -> None:
        chunk = KnowledgeChunk(
            source="faq.md",
            title="Giờ mở cửa",
            content="Nhà hàng mở cửa lúc 08:00 mỗi ngày.",
            tags=("faq",),
        )

        response = _build_fast_path_response(
            SimpleNamespace(chunk=chunk, score=0.91),
            chunk.content,
            model="deterministic-kb-info",
        )

        self.assertEqual(chunk.chunk_id, response["retrieved_sources"][0]["chunk_id"])
        self.assertEqual(chunk.chunk_id, response["evidence"][0]["chunk_id"])
        self.assertEqual([chunk.chunk_id], response["claims"][0]["evidence_ids"])
        self.assertTrue(response["claims"][0]["verified"])

    def test_menu_presence_fast_path_cites_each_live_menu_item(self) -> None:
        response = try_menu_presence_fast_path(
            "Nhà hàng có món phở nào không?",
            [
                {
                    "id": "m_001",
                    "name": "Phở bò tái",
                    "price_vnd": 85000,
                    "is_available": True,
                }
            ],
            wants_recommendations=False,
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual("m_001", response["evidence"][0]["menu_item_id"])
        self.assertEqual(["m_001"], response["claims"][0]["evidence_ids"])
        self.assertTrue(response["claims"][0]["verified"])

    def test_suggestion_fast_path_gets_live_menu_claims_during_finalization(self) -> None:
        response = {
            "content": "Mình gợi ý Phở bò tái (85.000đ).",
            "provider_available": False,
            "model": "deterministic-party",
            "retrieved_sources": [],
            "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
            "suggested_cart_actions": [
                {
                    "menu_item_id": "m_001",
                    "name": "Phở bò tái",
                    "price_vnd": 85000,
                    "quantity": 1,
                }
            ],
            "follow_up": {"can_show_more": False, "remaining_count": 0},
            "latency_ms": {"path": "party_fast_path"},
        }
        context = {
            "intent": "recommend",
            "pipeline_version": "v3",
            "message": "Gợi ý món cho bốn người",
            "session_state": {"memory_version": "v2"},
            "constraints": {"party_size": 4},
            "facts": [],
        }

        finalized = _finalize_response_payload(response, context)

        self.assertEqual("live_data", finalized["decision"]["route"])
        self.assertEqual("m_001", finalized["evidence"][0]["menu_item_id"])
        self.assertEqual(["m_001"], finalized["claims"][0]["evidence_ids"])
        self.assertTrue(finalized["claims"][0]["verified"])

    def test_factual_fast_path_without_claims_fails_closed(self) -> None:
        response = {
            "content": "Nhà hàng mở cửa lúc 07:00.",
            "provider_available": False,
            "model": "deterministic-kb-info",
            "retrieved_sources": [
                {
                    "source": "faq.md",
                    "title": "Giờ mở cửa",
                    "chunk_id": "kb:faq:hours",
                    "score": 0.9,
                }
            ],
            "guardrail_flags": [],
            "suggested_cart_actions": [],
            "follow_up": {"can_show_more": False, "remaining_count": 0},
            "latency_ms": {"path": "kb_fast_path"},
        }
        context = {
            "intent": "restaurant_info",
            "pipeline_version": "v3",
            "message": "Mấy giờ mở cửa?",
            "session_state": {},
            "constraints": {},
            "facts": [],
        }

        finalized = _finalize_response_payload(response, context)

        self.assertEqual("kb_rag", finalized["decision"]["route"])
        self.assertEqual([], finalized.get("claims"))

    def test_claim_marked_unverified_cannot_pass_the_response_gate(self) -> None:
        response = {
            "content": "Phở bò tái có giá 20.000 đồng.",
            "provider_available": True,
            "model": "cx/gpt-5.5",
            "retrieved_sources": [],
            "evidence": [
                {
                    "source": "live_menu",
                    "menu_item_id": "m_001",
                    "title": "Phở bò tái",
                    "score": 1.0,
                }
            ],
            "claims": [
                {
                    "text": "Phở bò tái có giá 20.000 đồng.",
                    "evidence_ids": ["m_001"],
                    "verified": False,
                    "reason": "numeric_value_not_in_evidence",
                }
            ],
            "guardrail_flags": [],
            "suggested_cart_actions": [],
            "follow_up": {"can_show_more": False, "remaining_count": 0},
            "latency_ms": {"path": "llm"},
        }
        context = {
            "intent": "ask_price",
            "pipeline_version": "v3",
            "message": "Phở bao nhiêu?",
            "session_state": {},
            "constraints": {},
            "facts": [],
        }

        finalized = _finalize_response_payload(response, context)

        self.assertEqual("abstain", finalized["decision"]["route"])
        self.assertEqual("unverified_claims", finalized["decision"]["abstain_reason"])


if __name__ == "__main__":
    unittest.main()
