"""Allergen exclusion must be conservative about risk, not about Vietnamese.

The filter matched an allergen's name against diacritic-stripped menu text.  In a
Vietnamese catalogue the stripped forms collide, and every collision removed a
dish a guest could safely have eaten:

    trứng (egg)     vs  "miền Trung", "tầm trung"   43 of 91 dishes excluded,
                                                     only 7 carry `co trung`
    bơ    (butter)  vs  "bò"                        Phở bò, Bún bò Huế,
                                                     Cơm bò lúc lắc, Lẩu bò
    cua   (crab)    vs  "của"                       "phiên bản chay của Bún bò Huế"
    mực   (squid)   vs  "mức"                       "chọn mức đường" — trà sữa
    lạc   (peanut)  vs  "lắc"                       "bò lúc lắc"

and one case where a sentence saying a dish has *no* seafood was read as saying it
has some: Gỏi cuốn chay, whose description reads "Không thịt, không hải sản".

48 wrong exclusions in total.  These tests pin both directions, because a filter
that excludes nothing is as broken as one that excludes everything: the dishes
that genuinely declare an allergen must still be removed.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from app.rag.menu_query_filters import infer_allergen_excluded_menu_item_ids
from evaluation.golden_eval_common import load_menu_items

AI_ROOT = Path(__file__).resolve().parents[1]

# allergen -> the catalogue label that authoritatively declares it
DECLARED = {
    "seafood": "co hai san",
    "peanut": "co dau phong",
    "gluten": "co gluten",
    "egg": "co trung",
    "dairy": "co sua",
}


class AllergenExclusionPrecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.menu = load_menu_items()

    def _excluded_names(self, allergen: str) -> set[str]:
        ids = infer_allergen_excluded_menu_item_ids([allergen], self.menu)
        return {item["name"] for item in self.menu if item["id"] in ids}

    def test_every_declared_dish_is_still_excluded(self) -> None:
        # The fail-closed direction.  Loosening the matching must not let a dish
        # that declares the allergen through.
        for allergen, label in DECLARED.items():
            declared = {
                item["name"]
                for item in self.menu
                if label in (item.get("tags") or [])
            }
            with self.subTest(allergen=allergen):
                self.assertTrue(declared, f"no dish carries {label}")
                self.assertTrue(declared <= self._excluded_names(allergen))

    def test_beef_is_not_a_dairy_product(self) -> None:
        excluded = self._excluded_names("dairy")
        for dish in ("Phở bò tái nạm", "Bún bò Huế", "Cơm bò lúc lắc"):
            with self.subTest(dish=dish):
                self.assertNotIn(dish, excluded)

    def test_central_vietnam_and_mid_price_are_not_eggs(self) -> None:
        excluded = self._excluded_names("egg")
        # "Bún bò Huế" carries both "mien Trung" and "tam trung".
        self.assertNotIn("Bún bò Huế", excluded)
        # The exclusion should be close to the declared count, not five times it.
        declared = sum(
            1 for item in self.menu if "co trung" in (item.get("tags") or [])
        )
        self.assertLessEqual(len(excluded), declared + 3)

    def test_the_word_for_of_is_not_a_crab(self) -> None:
        # "Bún chay Huế" is vegan; its description says "phiên bản chay của...".
        self.assertNotIn("Bún chay Huế", self._excluded_names("seafood"))

    def test_a_sweetness_level_is_not_squid(self) -> None:
        # "Trà sữa trân châu" says "chọn mức đường".  It is excluded for dairy —
        # it carries `co sua` — but never for seafood.
        self.assertNotIn("Trà sữa trân châu", self._excluded_names("seafood"))
        self.assertIn("Trà sữa trân châu", self._excluded_names("dairy"))

    def test_shaken_beef_is_not_a_peanut(self) -> None:
        self.assertNotIn("Cơm bò lúc lắc", self._excluded_names("peanut"))

    def test_saying_a_dish_has_no_seafood_does_not_add_seafood(self) -> None:
        excluded = self._excluded_names("seafood")
        self.assertNotIn("Gỏi cuốn chay", excluded)
        # It does declare peanut sauce, so that one must still fire.
        self.assertIn("Gỏi cuốn chay", self._excluded_names("peanut"))

    def test_a_genuine_mention_without_a_label_is_still_caught(self) -> None:
        # "Bún đậu mắm tôm" has no `co hai san` tag, but mắm tôm is shrimp paste.
        # Text matching earns its place by covering gaps in the labels.
        self.assertIn("Bún đậu mắm tôm", self._excluded_names("seafood"))


if __name__ == "__main__":
    unittest.main()
