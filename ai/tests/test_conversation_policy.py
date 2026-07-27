from __future__ import annotations

import unittest

from app.rag.conversation_policy import (
    build_conversation_policy,
    build_prior_suggestion_actions,
    enforce_suggestion_policy,
)
from app.rag.constraint_extractor import extract_constraints
from app.rag.query_rewriter import rewrite_query


MENU = [
    {"id": f"m_{index:03d}", "name": f"Món {index}", "price_vnd": index * 10000}
    for index in range(1, 7)
]


class ConversationPolicyTests(unittest.TestCase):
    def test_structured_memory_and_rejection_exclude_previous_suggestions(self) -> None:
        policy = build_conversation_policy(
            "Gợi ý 2 món khác",
            [
                {
                    "role": "assistant",
                    "content": "Mình gợi ý Món 1.",
                    "suggested_cart_actions": [{"menu_item_id": "m_001"}],
                },
                {"role": "user", "content": "Không lấy các món này"},
            ],
            "SUGGESTED_MENU_ITEM_IDS: m_002\nREJECTED_MENU_ITEM_IDS: m_003",
            MENU,
        )

        self.assertEqual(2, policy.requested_count)
        self.assertEqual(
            frozenset({"m_001", "m_002", "m_003"}),
            policy.excluded_menu_item_ids,
        )

    def test_explicit_count_is_filled_without_duplicates(self) -> None:
        policy = build_conversation_policy("Gợi ý 2 món", [], "", MENU)
        actions = [
            {"menu_item_id": "m_001", "name": "Món 1"},
            {"menu_item_id": "m_001", "name": "Món 1"},
        ]

        result = enforce_suggestion_policy(actions, MENU, policy)

        self.assertEqual(["m_001", "m_002"], [item["menu_item_id"] for item in result])

    def test_vietnamese_word_count_limits_recommendations(self) -> None:
        policy = build_conversation_policy("Gợi ý hai món", [], "", MENU)

        result = enforce_suggestion_policy([], MENU, policy)

        self.assertEqual(2, policy.requested_count)
        self.assertEqual(
            ["m_001", "m_002"],
            [item["menu_item_id"] for item in result],
        )

    def test_information_question_does_not_hide_previously_mentioned_item(self) -> None:
        policy = build_conversation_policy(
            "Món 1 giá bao nhiêu?",
            [],
            "SUGGESTED_MENU_ITEM_IDS: m_001",
            MENU,
        )

        self.assertFalse(policy.wants_recommendations)
        self.assertEqual(frozenset(), policy.excluded_menu_item_ids)

    def test_general_recommendation_fills_cards_without_explicit_count(self) -> None:
        policy = build_conversation_policy("Gợi ý món ăn nhậu", [], "", MENU)

        result = enforce_suggestion_policy([], MENU, policy)

        self.assertTrue(policy.wants_recommendations)
        self.assertGreater(len(result), 0)
        self.assertLessEqual(len(result), policy.max_suggestions)

    def test_recommendation_actions_outside_candidate_evidence_are_replaced(self) -> None:
        candidate_menu = [
            {"id": "m_pho", "name": "Phở bò", "price_vnd": 70000, "is_available": True}
        ]
        policy = build_conversation_policy(
            "Gợi ý món phở",
            [],
            "",
            candidate_menu,
        )

        result = enforce_suggestion_policy(
            [{"menu_item_id": "m_unrelated", "name": "Gà xào sả ớt"}],
            candidate_menu,
            policy,
        )

        self.assertEqual(["m_pho"], [item["menu_item_id"] for item in result])

    def test_party_size_triggers_recommendation_cards(self) -> None:
        policy = build_conversation_policy("nhóm 8 người", [], "", MENU)
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(8, policy.party_size)

        menu = [
            {"id": "m_036", "name": "Gà rô ti kiểu Việt", "price_vnd": 320000, "is_available": True},
            {"id": "m_037", "name": "Gà hấp lá chanh", "price_vnd": 280000, "is_available": True},
            {"id": "m_038", "name": "Mẹt gà thập cẩm", "price_vnd": 350000, "is_available": True},
        ]
        content = (
            "Với nhóm 8 người, mình gợi ý: gà rô ti kiểu Việt, gà hấp lá chanh, "
            "mẹt gà thập cẩm."
        )
        from app.rag.conversation_policy import infer_suggested_actions_from_content

        actions = infer_suggested_actions_from_content(content, menu, policy)
        self.assertEqual(
            ["m_036", "m_037", "m_038"],
            [item["menu_item_id"] for item in actions],
        )

    def test_follow_up_mon_khac_after_party_size_in_history(self) -> None:
        history = [
            {"role": "user", "content": "nhóm 8 người"},
            {
                "role": "assistant",
                "content": "Mình gợi ý Món 1 và Món 2 cho nhóm 8 người.",
                "suggested_cart_actions": [{"menu_item_id": "m_001"}, {"menu_item_id": "m_002"}],
            },
        ]
        policy = build_conversation_policy("còn món khác?", history, "", MENU)

        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(frozenset({"m_001", "m_002"}), policy.previously_suggested_ids)

    def test_follow_up_inherits_party_size_from_history(self) -> None:
        history = [{"role": "user", "content": "nhóm 8 người"}]
        constraints = extract_constraints("còn món khác?", history)

        self.assertEqual(8, constraints["party_size"])
        self.assertTrue(constraints["is_recommendation"])

        rewritten = rewrite_query("còn món khác?", history)
        self.assertIn("8 nguoi", rewritten)

    def test_context_question_does_not_trigger_more_dish_recommendations(self) -> None:
        history = [
            {"role": "user", "content": "cho gia đình 8 người"},
            {
                "role": "assistant",
                "content": "Gợi ý Bánh xèo và Lẩu bò.",
                "suggested_cart_actions": [{"menu_item_id": "m_001"}, {"menu_item_id": "m_002"}],
            },
        ]
        policy = build_conversation_policy("mấy món đó đủ cho 8 người chưa?", history, "", MENU)

        self.assertFalse(policy.wants_recommendations)
        self.assertTrue(policy.surface_prior_suggestion_cards)
        actions = build_prior_suggestion_actions(MENU, policy)
        self.assertEqual(["m_001", "m_002"], [item["menu_item_id"] for item in actions])

    def test_the_con_payment_follow_up_does_not_trigger_dish_cards(self) -> None:
        history = [
            {"role": "user", "content": "nhóm 8 người"},
            {"role": "assistant", "content": "Gợi ý món", "suggested_cart_actions": [{"menu_item_id": "m_001"}]},
        ]
        policy = build_conversation_policy("thế còn thanh toán thì sao?", history, "", MENU)

        self.assertFalse(policy.wants_recommendations)
        self.assertFalse(policy.surface_prior_suggestion_cards)

    def test_category_listing_with_recommendation_cue_still_wants_recommendations(
        self,
    ) -> None:
        seafood_menu = [
            {
                "id": "m_101",
                "name": "Tôm nướng muối ớt",
                "category_name": "Hải sản",
                "category_id": "cat_hai_san",
                "price_vnd": 180000,
                "is_available": True,
            },
            {
                "id": "m_102",
                "name": "Mực hấp gừng",
                "category_name": "Hải sản",
                "category_id": "cat_hai_san",
                "price_vnd": 160000,
                "is_available": True,
            },
        ]
        message = "có món hải sản nào ngon không"
        constraints = extract_constraints(message, [])
        policy = build_conversation_policy(
            message,
            [],
            "",
            seafood_menu,
            category=constraints.get("category"),
        )

        # The customer is both naming a category ("có món hải sản") and
        # asking to be recommended one ("nào ngon") — the recommendation
        # cue must win so a suggestion card is still produced.
        self.assertTrue(policy.wants_recommendations)

    def test_party_of_eight_prefers_shared_dishes_in_fill(self) -> None:
        group_menu = [
            {
                "id": "m_036",
                "name": "Gà rô ti kiểu Việt",
                "price_vnd": 320000,
                "is_available": True,
            },
            {
                "id": "m_037",
                "name": "Gà hấp lá chanh",
                "price_vnd": 280000,
                "is_available": True,
            },
            {
                "id": "m_033",
                "name": "Lẩu hải sản chua cay",
                "category_name": "Lẩu",
                "tags": ["nau", "tom"],
                "price_vnd": 450000,
                "is_available": True,
            },
            {
                "id": "m_029",
                "name": "Lẩu chua cá lăng",
                "category_name": "Lẩu",
                "tags": ["nau", "ca"],
                "price_vnd": 420000,
                "is_available": True,
            },
        ]
        policy = build_conversation_policy("nhóm 8 người", [], "", group_menu)
        llm_actions = [
            {"menu_item_id": "m_036", "name": "Gà rô ti kiểu Việt"},
            {"menu_item_id": "m_037", "name": "Gà hấp lá chanh"},
        ]

        result = enforce_suggestion_policy(llm_actions, group_menu, policy)
        picked_ids = [item["menu_item_id"] for item in result]

        self.assertGreaterEqual(len(picked_ids), 2)
        self.assertTrue(any(item_id in {"m_029", "m_033"} for item_id in picked_ids[:2]))


if __name__ == "__main__":
    unittest.main()
