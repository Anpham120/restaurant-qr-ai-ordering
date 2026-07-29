from __future__ import annotations

import unittest

from app.rag.constraint_extractor import extract_constraints
from app.rag.conversation_policy import build_conversation_policy
from app.rag.party_recommendation_fast_path import try_party_recommendation_fast_path
from app.services.assistant import _try_catalog_fast_path


class CatalogListingPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.history = [
            {"role": "user", "content": "2 nguoi an gi"},
            {"role": "assistant", "content": "Goi y mon"},
        ]
        self.menu = [
            {
                "menu_item_id": "m_008",
                "name": "Pho bo tai nam",
                "category_name": "Pho & Bun",
                "category_id": "cat_pho_bun",
                "is_available": True,
                "price_vnd": 75000,
            },
            {
                "menu_item_id": "m_009",
                "name": "Pho ga ta",
                "category_name": "Pho & Bun",
                "category_id": "cat_pho_bun",
                "is_available": True,
                "price_vnd": 70000,
            },
            {
                "menu_item_id": "m_001",
                "name": "Goi xoai tom su",
                "category_name": "Khai vi",
                "category_id": "cat_appetizer",
                "is_available": True,
                "price_vnd": 85000,
            },
            {
                "menu_item_id": "m_020",
                "name": "Bun bo Hue",
                "category_name": "Pho & Bun",
                "category_id": "cat_pho_bun",
                "is_available": True,
                "price_vnd": 80000,
            },
        ]

    def test_pho_listing_uses_catalog_not_party_path(self) -> None:
        message = "o day co nhung mon pho gi"
        constraints = extract_constraints(message, self.history)
        policy = build_conversation_policy(
            message,
            self.history,
            "",
            self.menu,
            category=constraints.get("category"),
        )

        self.assertTrue(constraints["is_catalog_only"])
        self.assertFalse(policy.wants_recommendations)
        self.assertIsNone(
            try_party_recommendation_fast_path(constraints, policy, self.menu),
        )

        catalog = _try_catalog_fast_path(message, constraints, self.menu, frozenset())
        self.assertIsNotNone(catalog)
        content = catalog["content"]
        self.assertIn("Pho bo tai nam", content)
        self.assertIn("Pho ga ta", content)
        self.assertNotIn("Goi xoai", content)
        self.assertNotIn("Với 2 người", content)
        self.assertNotIn("Bun bo Hue", content)
        # Listing a category should still let the customer add a dish to
        # their cart directly from the answer instead of a text-only list.
        cart_ids = [action["menu_item_id"] for action in catalog["suggested_cart_actions"]]
        self.assertIn("m_008", cart_ids)
        self.assertIn("m_009", cart_ids)

    def test_order_request_skips_catalog_fast_path(self) -> None:
        for message in ("Ban dat com suon nhe", "Order pho bo for me"):
            with self.subTest(message=message):
                constraints = extract_constraints(message, self.history)
                self.assertFalse(constraints["is_catalog_only"])
                self.assertIsNone(
                    _try_catalog_fast_path(message, constraints, self.menu, frozenset()),
                )


if __name__ == "__main__":
    unittest.main()


class CatalogTagSelectionTests(unittest.TestCase):
    """A catalogue label names a selection just as a category does.

    "Bữa sáng có gì?" names `sang` and resolves to a concrete dish set, but this
    path required a *category*, so the question reached the model and came back as
    a counter-question while the dishes sat right there.
    """

    @staticmethod
    def _menu() -> list[dict]:
        return [
            {
                "id": "m_pho",
                "name": "Phở bò tái nạm",
                "category_id": "cat_pho",
                "category_name": "Phở & Bún",
                "price_vnd": 75000,
                "tags": ["sang", "trua", "khong cay"],
                "is_available": True,
            },
            {
                "id": "m_banh",
                "name": "Bánh cuốn Thanh Trì",
                "category_id": "cat_appetiser",
                "category_name": "Khai vị",
                "price_vnd": 55000,
                "tags": ["sang", "khong cay"],
                "is_available": True,
            },
            {
                "id": "m_lau",
                "name": "Lẩu bò nhúng giấm",
                "category_id": "cat_hotpot",
                "category_name": "Lẩu",
                "price_vnd": 250000,
                "tags": ["toi", "nhom ban"],
                "is_available": True,
            },
        ]

    def _run(self, message: str):
        return _try_catalog_fast_path(
            message,
            extract_constraints(message),
            self._menu(),
            frozenset(),
        )

    def test_a_label_with_a_browse_marker_lists_dishes(self) -> None:
        response = self._run("Bua sang co gi?")
        self.assertIsNotNone(response)
        content = response["content"]
        self.assertIn("Bánh cuốn Thanh Trì", content)
        self.assertIn("Phở bò tái nạm", content)
        self.assertNotIn("Lẩu bò nhúng giấm", content)

    def test_a_bare_browse_question_names_nothing_and_is_left_alone(self) -> None:
        # Without this the path would enumerate the whole menu for "có gì không?".
        self.assertIsNone(self._run("Co gi khong?"))

    def test_a_preference_without_a_browse_marker_is_left_alone(self) -> None:
        # "Tôi thích món ngọt" brushes a label but is not a request to enumerate.
        self.assertIsNone(self._run("Toi thich mon ngot"))

    def test_category_browsing_still_uses_the_category_wording(self) -> None:
        response = self._run("Cho xem mon lau")
        self.assertIsNotNone(response)
        self.assertIn("nhóm", response["content"])
