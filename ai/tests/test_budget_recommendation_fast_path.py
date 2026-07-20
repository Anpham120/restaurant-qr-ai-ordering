from __future__ import annotations

import unittest

from app.rag.budget_recommendation_fast_path import try_budget_recommendation_fast_path
from app.rag.conversation_policy import build_conversation_policy


GROUP_MENU = [
    {
        "id": "m_033",
        "name": "Lẩu hải sản chua cay",
        "category_name": "Lẩu",
        "tags": ["nau", "tom"],
        "price_vnd": 450000,
        "is_available": True,
    },
    {
        "id": "m_001",
        "name": "Gỏi cuốn tôm thịt",
        "category_name": "Khai vị",
        "tags": ["tom"],
        "price_vnd": 65000,
        "is_available": True,
    },
    {
        "id": "m_008",
        "name": "Phở bò tái nạm",
        "category_name": "Phở",
        "price_vnd": 85000,
        "is_available": True,
    },
]


class BudgetRecommendationFastPathTests(unittest.TestCase):
    def test_budget_party_query_uses_fast_path(self) -> None:
        message = "gợi ý cho tôi món cho 4 người với ngân sách khoảng 400k"
        policy = build_conversation_policy(message, [], "", GROUP_MENU)
        constraints = {
            "budget_vnd": 400000,
            "party_size": 4,
            "diet": "unknown",
        }
        budget_picks = [
            {
                "menu_item_id": "m_033",
                "name": "Lẩu hải sản chua cay",
                "price_vnd": 450000,
                "quantity": 1,
                "reason": "test",
                "requires_customer_confirmation": True,
            }
        ]

        response = try_budget_recommendation_fast_path(
            constraints,
            policy,
            GROUP_MENU,
            budget_picks,
        )

        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("400,000", response["content"])
        self.assertGreater(len(response["suggested_cart_actions"]), 0)
        self.assertNotIn("hơi chậm", response["content"])


if __name__ == "__main__":
    unittest.main()
