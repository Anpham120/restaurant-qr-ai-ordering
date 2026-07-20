from __future__ import annotations

import unittest

from app.rag.conversation_policy import build_conversation_policy, enforce_suggestion_policy
from app.rag.menu_exclusions import detect_excluded_category_ids, filter_items_by_excluded_categories


MENU = [
    {
        "id": "m_085",
        "name": "Bia Tiger Crystal",
        "category_id": "cat_alcohol",
        "category_name": "Bia & Rượu",
        "price_vnd": 22000,
        "is_available": True,
    },
    {
        "id": "m_070",
        "name": "Trà đào cam sả",
        "category_id": "cat_drink",
        "category_name": "Cà phê & Trà",
        "tags": ["mat"],
        "price_vnd": 35000,
        "is_available": True,
    },
    {
        "id": "m_075",
        "name": "Nước ép cam",
        "category_id": "cat_juice",
        "category_name": "Nước ép & Sinh tố",
        "tags": ["mat"],
        "price_vnd": 40000,
        "is_available": True,
    },
]


class MenuExclusionTests(unittest.TestCase):
    def test_detects_non_alcoholic_drink_preference(self) -> None:
        excluded = detect_excluded_category_ids("đồ uống chứ không phải bia rượu")
        self.assertIn("cat_alcohol", excluded)

    def test_non_alcoholic_drink_query_skips_beer_cards(self) -> None:
        excluded = detect_excluded_category_ids("đồ uống chứ không phải bia rượu")
        filtered = filter_items_by_excluded_categories(MENU, excluded)
        policy = build_conversation_policy("đồ uống chứ không phải bia rượu", [], "", filtered)
        actions = enforce_suggestion_policy([], filtered, policy)

        self.assertTrue(actions)
        self.assertTrue(all(action["menu_item_id"] != "m_085" for action in actions))
        self.assertNotEqual(
            "Món phù hợp với yêu cầu hiện tại và đang còn bán.",
            actions[0]["reason"],
        )


if __name__ == "__main__":
    unittest.main()
