from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.schemas import ChatRequest, ChatResponse


class ChatContractV2Tests(unittest.TestCase):
    def test_v2_request_preserves_backend_bounded_history_and_live_context(self) -> None:
        request = ChatRequest(
            contract_version="v2",
            message="Còn món khác không?",
            history=[
                {"role": "user", "content": f"turn {index}"}
                for index in range(12)
            ],
            session_state={
                "facts": [{"kind": "party_size", "value": 4}],
                "rolling_summary": "Khách đi 4 người.",
                "suggested_menu_item_ids": ["m_001"],
                "rejected_menu_item_ids": ["m_002"],
            },
            live_context={
                "catalog_version": "menu-2026-07-22",
                "menu_items": [
                    {"id": "m_001", "name": "Phở bò", "category_id": "pho"},
                ],
                "cart_items": [{"menuItemId": "m_001", "quantity": 1}],
                "table_code": "T01",
            },
        )

        self.assertEqual("v2", request.contract_version)
        self.assertEqual(12, len(request.history))
        self.assertEqual("turn 0", request.history[0].content)
        self.assertEqual("menu-2026-07-22", request.catalog_version)
        self.assertEqual("menu-2026-07-22", request.menu_version)
        self.assertEqual("Khách đi 4 người.", request.rolling_summary)
        self.assertEqual([{"kind": "party_size", "value": 4}], request.facts)
        self.assertEqual("m_001", request.menu_items[0].id)
        self.assertEqual("T01", request.table_code)

    def test_v2_request_rejects_more_than_12_turns_instead_of_silently_cutting(self) -> None:
        with self.assertRaises(ValidationError):
            ChatRequest(
                contract_version="v2",
                message="follow-up",
                history=[
                    {"role": "user", "content": f"turn {index}"}
                    for index in range(13)
                ],
            )

    def test_v1_request_remains_backward_compatible_without_hidden_truncation(self) -> None:
        request = ChatRequest(
            contract_version="v1",
            message="legacy",
            history=[
                {"role": "user", "content": f"turn {index}"}
                for index in range(14)
            ],
        )

        self.assertEqual(14, len(request.history))

    def test_v2_response_can_carry_decision_evidence_claims_and_session_updates(self) -> None:
        response = ChatResponse(
            content="Phở bò đang có trong menu.",
            provider_available=True,
            model="cx/gpt-5.5",
            decision={
                "intent": "menu_query",
                "route": "live_menu",
                "confidence": 0.91,
                "evidence_sufficient": True,
            },
            evidence=[
                {"source": "live_menu", "menu_item_id": "m_001", "score": 1.0},
            ],
            claims=[
                {"text": "Phở bò đang có trong menu.", "evidence_ids": ["m_001"], "verified": True},
            ],
            session_updates={
                "facts": [{"kind": "referenced_menu_item", "value": "m_001"}],
                "suggested_menu_item_ids": ["m_001"],
                "rejected_menu_item_ids": ["m_002"],
                "rolling_summary": "Đã nhắc tới phở bò.",
            },
        )

        self.assertEqual("live_menu", response.decision.route)
        self.assertTrue(response.claims[0].verified)
        self.assertEqual(["m_002"], response.session_updates.rejected_menu_item_ids)

    def test_menu_context_keeps_live_safety_fields(self) -> None:
        request = ChatRequest(
            contract_version="v2",
            message="Món này bao nhiêu calo?",
            live_context={
                "catalog_version": "catalog-1",
                "menu_items": [
                    {
                        "id": "m_001",
                        "name": "Phở bò",
                        "calories_kcal": 450,
                        "sugar_g": 3.5,
                        "protein_g": 28,
                        "ingredients": ["bánh phở", "thịt bò"],
                        "allergens": ["gluten"],
                    }
                ],
            },
        )

        item = request.menu_items[0]
        self.assertEqual(450, item.calories_kcal)
        self.assertEqual(3.5, item.sugar_g)
        self.assertEqual(["gluten"], item.allergens)

    def test_v2_contract_carries_pipeline_profile_and_typed_conversation_frame(self) -> None:
        request = ChatRequest(
            contract_version="v2",
            message="Món thứ hai bao nhiêu tiền?",
            pipeline_profile="planner_state_v3",
            session_state={
                "memory_version": "v2",
                "conversation_frame": {
                    "active_topic": "menu",
                    "active_intent": "ask_price",
                    "focus_menu_item_ids": ["m_002"],
                    "turn_sequence": 3,
                    "pending_clarification": None,
                },
            },
        )

        self.assertEqual("planner_state_v3", request.pipeline_profile)
        self.assertEqual(
            ["m_002"],
            request.session_state.conversation_frame.focus_menu_item_ids,
        )
        self.assertEqual(3, request.session_state.conversation_frame.turn_sequence)

        response = ChatResponse(
            content="Món thứ hai có giá 80.000 đồng.",
            provider_available=False,
            model="deterministic-live-menu",
            pipeline_profile="planner_state_v3",
            resolved_menu_item_ids=["m_002"],
            verifier_result="passed",
            session_updates={
                "memory_version": "v2",
                "conversation_frame": {
                    "active_topic": "menu",
                    "active_intent": "ask_price",
                    "focus_menu_item_ids": ["m_002"],
                    "turn_sequence": 4,
                },
            },
        )

        self.assertEqual("planner_state_v3", response.pipeline_profile)
        self.assertEqual(["m_002"], response.resolved_menu_item_ids)
        self.assertEqual("passed", response.verifier_result)


if __name__ == "__main__":
    unittest.main()
