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
