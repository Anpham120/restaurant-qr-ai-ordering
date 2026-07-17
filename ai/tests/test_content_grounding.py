from __future__ import annotations

import unittest

from app.rag.content_grounding import format_grounded_recommendation_content, ground_response_content


MENU = [
    {"id": "m_015", "name": "Cơm tấm sườn bì chả", "price_vnd": 65000, "is_available": True},
    {"id": "m_085", "name": "Bia Tiger", "price_vnd": 25000, "is_available": True},
]


class ContentGroundingTests(unittest.TestCase):
    def test_hallucinated_dish_list_is_replaced_with_grounded_cards(self) -> None:
        hallucinated = (
            "Dạ, mình gợi ý bữa nhậu:\n"
            "1. Sụn gà rang muối\n"
            "2. Chân gà rút xương\n"
            "3. Đậu phụ hun khói"
        )
        actions = [
            {
                "menu_item_id": "m_015",
                "name": "Cơm tấm sườn bì chả",
                "price_vnd": 65000,
                "reason": "Món no, hợp nhậu nhẹ.",
            }
        ]

        content, flags, kept_actions = ground_response_content(
            hallucinated,
            actions,
            MENU,
            wants_recommendations=True,
        )

        self.assertIn("MENU_FABRICATION_BLOCKED", flags)
        self.assertIn("Cơm tấm sườn bì chả", content)
        self.assertNotIn("Sụn gà rang muối", content)
        self.assertEqual(actions, kept_actions)

    def test_format_grounded_recommendation_content_lists_only_real_items(self) -> None:
        content = format_grounded_recommendation_content(
            [
                {
                    "name": "Bia Tiger",
                    "price_vnd": 25000,
                    "reason": "Dễ uống.",
                }
            ]
        )

        self.assertIn("Bia Tiger", content)
        self.assertIn("25.000đ", content)


if __name__ == "__main__":
    unittest.main()
