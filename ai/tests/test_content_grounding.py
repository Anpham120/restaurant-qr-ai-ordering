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

    def test_comma_separated_hallucination_is_replaced_when_cards_exist(self) -> None:
        hallucinated = (
            "Dạ, bên em có các món ăn nhẹ như khoai tây chiên, gỏi cuốn, súp, salad hoặc các món bánh ngọt ạ."
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
        self.assertNotIn("khoai tây chiên", content)
        self.assertEqual(actions, kept_actions)

    def test_mixed_list_with_one_fabricated_dish_is_replaced(self) -> None:
        mixed = (
            "Dạ, em xin gợi ý 5 món ngon:\n"
            "1. Bánh mì pate Sài Gòn (35.000đ) – khai vị nhanh.\n"
            "2. Gỏi cuốn tôm thịt (65.000đ) – thanh mát.\n"
            "3. Lẩu mắm miền Tây (320.000đ) – đậm đà.\n"
            "4. Lẩu hải sản chua cay (450.000đ) – hải sản tươi.\n"
            "5. Sầu riêng Ri6 – tráng miệng thơm béo."
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
            mixed,
            actions,
            MENU,
            wants_recommendations=True,
        )

        self.assertIn("MENU_FABRICATION_BLOCKED", flags)
        self.assertIn("Cơm tấm sườn bì chả", content)
        self.assertNotIn("Sầu riêng Ri6", content)
        self.assertEqual(actions, kept_actions)

    def test_format_grounded_recommendation_content(self) -> None:
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
