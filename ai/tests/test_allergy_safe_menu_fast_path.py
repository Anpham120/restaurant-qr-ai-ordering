"""Contract for the deterministic allergy path.

Allergy was the only family the evaluation set answered 0% deterministically —
every one of its thirteen cases went to the generation step, and asked "Tôi dị ứng
hải sản, món nào an toàn?" the assistant replied by asking the guest to send the
menu it was already holding.

These tests pin what the path must do, and — more importantly for a safety path —
what it must never say.  ``knowledge-base/allergy-disclaimer.md`` forbids claiming
a dish is "an toàn 100%", that it "chắc chắn không có" an allergen, or that the
kitchen separates preparation.  A menu description is not a kitchen audit.
"""
from __future__ import annotations

import unittest

from app.rag.allergy_safe_menu_fast_path import (
    DISCLAIMER_EN,
    DISCLAIMER_VI,
    try_allergy_safe_menu_fast_path,
    wants_avoid_list,
)

FORBIDDEN_CLAIMS = (
    "an toàn 100",
    "chắc chắn không",
    "tách riêng hoàn toàn",
    "100% safe",
    "guaranteed",
)


def _menu() -> list[dict]:
    return [
        {
            "id": "m_tom",
            "name": "Gỏi cuốn tôm thịt",
            "category_name": "Khai vị",
            "price_vnd": 65000,
            "tags": ["co hai san"],
            "is_available": True,
        },
        {
            "id": "m_cua",
            "name": "Súp măng cua",
            "category_name": "Khai vị",
            "price_vnd": 65000,
            "tags": ["co hai san"],
            "is_available": True,
        },
        {
            "id": "m_pho_bo",
            "name": "Phở bò tái nạm",
            "category_name": "Phở & Bún",
            "price_vnd": 75000,
            "tags": ["khong cay"],
            "is_available": True,
        },
        {
            "id": "m_pho_ga",
            "name": "Phở gà ta",
            "category_name": "Phở & Bún",
            "price_vnd": 70000,
            "tags": ["khong cay"],
            "is_available": True,
        },
        {
            "id": "m_het",
            "name": "Cá lóc nướng trui",
            "category_name": "Hải sản",
            "price_vnd": 150000,
            "tags": ["co hai san"],
            "is_available": False,
        },
    ]


class AllergySafeMenuFastPathTests(unittest.TestCase):
    def test_lists_dishes_that_record_no_allergen(self) -> None:
        response = try_allergy_safe_menu_fast_path(
            "Dị ứng hải sản nặng, menu nào an toàn?", _menu(), allergens=["seafood"]
        )
        self.assertIsNotNone(response)
        content = response["content"]
        self.assertIn("Phở bò tái nạm", content)
        self.assertIn("Phở gà ta", content)
        self.assertNotIn("Gỏi cuốn tôm thịt", content)
        self.assertNotIn("Súp măng cua", content)

    def test_never_claims_a_dish_is_safe(self) -> None:
        for query in (
            "Dị ứng hải sản nặng, menu nào an toàn?",
            "Tôi bị dị ứng hải sản, nên tránh món nào?",
            "Allergic to shellfish, what to avoid?",
        ):
            response = try_allergy_safe_menu_fast_path(
                query, _menu(), allergens=["seafood"]
            )
            content = response["content"].casefold()
            for phrase in FORBIDDEN_CLAIMS:
                with self.subTest(query=query, phrase=phrase):
                    self.assertNotIn(phrase.casefold(), content)

    def test_always_carries_the_mandatory_disclaimer(self) -> None:
        vietnamese = try_allergy_safe_menu_fast_path(
            "Dị ứng hải sản, món nào ăn được?", _menu(), allergens=["seafood"]
        )
        self.assertIn(DISCLAIMER_VI, vietnamese["content"])
        english = try_allergy_safe_menu_fast_path(
            "Allergic to shellfish, what is safe?", _menu(), allergens=["seafood"]
        )
        self.assertIn(DISCLAIMER_EN, english["content"])

    def test_always_offers_staff_confirmation(self) -> None:
        response = try_allergy_safe_menu_fast_path(
            "Dị ứng hải sản, món nào ăn được?", _menu(), allergens=["seafood"]
        )
        self.assertTrue(response["suggest_staff_handoff"])
        self.assertIn("ALLERGY_DISCLAIMER", response["guardrail_flags"])

    def test_offers_cart_cards_only_for_the_safe_list(self) -> None:
        safe = try_allergy_safe_menu_fast_path(
            "Khach di ung tom, goi y mon an toan", _menu(), allergens=["seafood"]
        )
        ids = {a["menu_item_id"] for a in safe["suggested_cart_actions"]}
        self.assertEqual({"m_pho_bo", "m_pho_ga"}, ids)

        avoid = try_allergy_safe_menu_fast_path(
            "Tôi bị dị ứng hải sản, nên tránh món nào?", _menu(), allergens=["seafood"]
        )
        # Offering to add a dish the guest just said they cannot eat is worse than
        # offering nothing.
        self.assertEqual([], avoid["suggested_cart_actions"])

    def test_avoid_list_names_the_dishes_that_record_the_allergen(self) -> None:
        response = try_allergy_safe_menu_fast_path(
            "Con tom cua muc thi tranh gi?", _menu(), allergens=["seafood"]
        )
        content = response["content"]
        self.assertIn("Gỏi cuốn tôm thịt", content)
        self.assertIn("Súp măng cua", content)
        self.assertNotIn("Phở gà ta", content)

    def test_sold_out_dishes_appear_in_neither_list(self) -> None:
        for query in (
            "Dị ứng hải sản, món nào ăn được?",
            "Dị ứng hải sản, nên tránh món nào?",
        ):
            response = try_allergy_safe_menu_fast_path(
                query, _menu(), allergens=["seafood"]
            )
            with self.subTest(query=query):
                self.assertNotIn("Cá lóc nướng trui", response["content"])

    def test_every_claim_cites_a_real_menu_item(self) -> None:
        response = try_allergy_safe_menu_fast_path(
            "Dị ứng hải sản, món nào ăn được?", _menu(), allergens=["seafood"]
        )
        menu_ids = {item["id"] for item in _menu()}
        self.assertTrue(response["claims"])
        for claim in response["claims"]:
            self.assertTrue(claim["verified"])
            for evidence_id in claim["evidence_ids"]:
                self.assertIn(evidence_id, menu_ids)

    def test_does_not_fire_without_a_declared_allergen(self) -> None:
        self.assertIsNone(
            try_allergy_safe_menu_fast_path("Gợi ý món phở", _menu(), allergens=[])
        )

    def test_a_question_asking_both_ways_gets_the_actionable_answer(self) -> None:
        # "món nào không ăn được" contains an avoid marker, but a guest asking
        # what is safe can order from the answer; a list of what to skip they
        # cannot.
        self.assertFalse(wants_avoid_list("Di ung hai san, mon nao an toan?"))
        self.assertTrue(wants_avoid_list("Di ung hai san, nen tranh mon nao?"))

    def test_respects_exclusions_from_elsewhere(self) -> None:
        response = try_allergy_safe_menu_fast_path(
            "Dị ứng hải sản, món nào ăn được?",
            _menu(),
            allergens=["seafood"],
            excluded_ids=frozenset({"m_pho_bo"}),
        )
        self.assertNotIn("Phở bò tái nạm", response["content"])
        self.assertIn("Phở gà ta", response["content"])


if __name__ == "__main__":
    unittest.main()
