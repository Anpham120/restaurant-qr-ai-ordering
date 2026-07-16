from __future__ import annotations

import unittest

from app.rag.conversation_policy import (
    build_conversation_policy,
    enforce_suggestion_policy,
)


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

    def test_information_question_does_not_hide_previously_mentioned_item(self) -> None:
        policy = build_conversation_policy(
            "Món 1 giá bao nhiêu?",
            [],
            "SUGGESTED_MENU_ITEM_IDS: m_001",
            MENU,
        )

        self.assertFalse(policy.wants_recommendations)
        self.assertEqual(frozenset(), policy.excluded_menu_item_ids)


if __name__ == "__main__":
    unittest.main()
