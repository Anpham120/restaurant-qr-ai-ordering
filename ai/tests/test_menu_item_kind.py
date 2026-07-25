from __future__ import annotations

import unittest

from app.rag.conversation_policy import build_conversation_policy, enforce_suggestion_policy
from app.rag.menu_grounding import select_menu_candidates
from app.rag.menu_item_kind import (
    classify_menu_item_kind,
    detect_requested_item_kind,
    filter_items_by_kind,
)


MENU = [
    {
        "id": "food_1",
        "name": "Nem rán Hà Nội",
        "category_id": "cat_appetizer",
        "category_name": "Khai vị",
        "tags": ["nhau", "chien"],
        "is_available": True,
    },
    {
        "id": "drink_1",
        "name": "Bia Tiger Crystal",
        "category_id": "cat_alcohol",
        "category_name": "Bia & Rượu",
        "tags": ["nhau", "bia"],
        "is_available": True,
    },
    {
        "id": "dessert_1",
        "name": "Chè khúc bạch",
        "category_id": "cat_dessert",
        "category_name": "Tráng miệng",
        "tags": ["ngot"],
        "is_available": True,
    },
    {
        "id": "drink_2",
        "name": "Trà đào",
        "category_id": "cat_drink",
        "category_name": "Cà phê & Trà",
        "tags": ["mat"],
        "is_available": True,
    },
]


class MenuItemKindTests(unittest.TestCase):
    def test_classify_food_drink_dessert(self) -> None:
        self.assertEqual(classify_menu_item_kind(MENU[0]), "food")
        self.assertEqual(classify_menu_item_kind(MENU[1]), "drink")
        self.assertEqual(classify_menu_item_kind(MENU[2]), "dessert")

    def test_an_nhau_requests_food_not_drinks(self) -> None:
        self.assertEqual(
            detect_requested_item_kind("gợi ý cho tôi các món để ăn nhậu"),
            "food",
        )
        candidates = select_menu_candidates("gợi ý cho tôi các món để ăn nhậu", MENU)
        kinds = {classify_menu_item_kind(item) for item in candidates}
        self.assertEqual(kinds, {"food"})
        self.assertNotIn("drink_1", {item["id"] for item in candidates})

    def test_drink_request_only_returns_drinks(self) -> None:
        self.assertEqual(detect_requested_item_kind("Gợi ý đồ uống mát"), "drink")
        candidates = select_menu_candidates("Gợi ý đồ uống mát", MENU)
        self.assertTrue(candidates)
        self.assertTrue(all(classify_menu_item_kind(item) == "drink" for item in candidates))

    def test_dessert_request_only_returns_desserts(self) -> None:
        self.assertEqual(detect_requested_item_kind("Cho tôi món tráng miệng"), "dessert")
        filtered = filter_items_by_kind(MENU, "dessert")
        self.assertEqual(["dessert_1"], [item["id"] for item in filtered])

    def test_enforce_policy_skips_drink_cards_for_food_query(self) -> None:
        policy = build_conversation_policy("Gợi ý món ăn nhậu", [], "", MENU)
        actions = enforce_suggestion_policy(
            [
                {
                    "menu_item_id": "drink_1",
                    "name": "Bia Tiger Crystal",
                    "quantity": 1,
                }
            ],
            MENU,
            policy,
        )
        self.assertTrue(all(action["menu_item_id"] != "drink_1" for action in actions))

    def test_beer_listing_query_fills_drink_cards(self) -> None:
        policy = build_conversation_policy("Ở đây có những bia gì nhỉ", [], "", MENU)
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual("drink", policy.requested_item_kind)
        actions = enforce_suggestion_policy([], MENU, policy)
        self.assertTrue(actions)
        self.assertTrue(all(action["menu_item_id"].startswith("drink_") for action in actions))

    def test_beer_price_question_does_not_force_cards(self) -> None:
        policy = build_conversation_policy("Bia Tiger Crystal giá bao nhiêu?", [], "", MENU)
        self.assertFalse(policy.wants_recommendations)

    def test_light_snack_browse_query_fills_food_cards(self) -> None:
        policy = build_conversation_policy("Ở đây có món gì ăn nhẹ không", [], "", MENU)
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual("food", policy.requested_item_kind)
        actions = enforce_suggestion_policy([], MENU, policy)
        self.assertTrue(actions)
        self.assertTrue(all(action["menu_item_id"] == "food_1" for action in actions))

    def test_food_context_wins_over_beer_in_same_sentence(self) -> None:
        for message in (
            "mon de an nhau voi bia",
            "mon de nhat voi bia",
            "tu van mon de an nhau",
            "Gợi ý món dễ ăn nhậu với bia",
        ):
            with self.subTest(message=message):
                self.assertEqual(detect_requested_item_kind(message), "food")

    def test_drink_only_beer_question_stays_drink(self) -> None:
        self.assertEqual(detect_requested_item_kind("uong bia gi"), "drink")

    def test_drink_listing_with_nhau_pairing_stays_drink(self) -> None:
        message = "Quán có bia nào để dùng cùng món nhậu?"
        self.assertEqual(detect_requested_item_kind(message), "drink")


if __name__ == "__main__":
    unittest.main()
