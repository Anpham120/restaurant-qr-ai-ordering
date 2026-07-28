"""Naming a food is not declaring an allergy to it.

`ALLERGEN_KEYWORDS["seafood"]` contains "hai san", and allergens were matched by
term alone.  So "Cho xem menu hải sản" set `allergens=['seafood']`, the allergen
filter then excluded all 24 seafood dishes, and a guest who asked to browse the
seafood menu was shown a menu with the seafood removed.

The same question also set `category='hai san'`, which meant the genuine allergy
question — "Tôi dị ứng hải sản, món nào an toàn?" — filtered the menu *to* seafood
while excluding every seafood dish.  The intersection is empty, so the model
received no dishes and asked the guest to supply the menu it already had, on a
safety-critical question.

Both directions matter, so both are pinned here: an allergy must still be
detected, and a plain request for a category must not be read as one.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.rag.constraint_extractor import extract_constraints
from app.rag.menu_query_filters import infer_allergen_excluded_menu_item_ids

AI_ROOT = Path(__file__).resolve().parents[1]
GOLDEN = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"


def _menu() -> list[dict]:
    return [
        {"id": "m_1", "name": "Tôm rang muối", "description": "tôm sú", "tags": ["co hai san"]},
        {"id": "m_2", "name": "Mực xào sa tế", "description": "mực tươi", "tags": ["co hai san"]},
        {"id": "m_3", "name": "Phở gà ta", "description": "gà ta", "tags": []},
        {"id": "m_4", "name": "Cơm rang dưa bò", "description": "thịt bò", "tags": []},
    ]


class AllergyContextGateTests(unittest.TestCase):
    def test_browsing_a_category_is_not_an_allergy(self) -> None:
        for query in (
            "Cho xem menu hai san",
            "Browse seafood menu",
            "Nha hang co mon hai san gi?",
        ):
            with self.subTest(query=query):
                constraints = extract_constraints(query)
                self.assertEqual([], constraints["allergens"])
                # The guest asked for the category, so it must survive.
                self.assertEqual("hai san", constraints["category"])

    def test_browsing_a_category_no_longer_hides_that_category(self) -> None:
        constraints = extract_constraints("Cho xem menu hai san")
        excluded = infer_allergen_excluded_menu_item_ids(constraints["allergens"], _menu())
        self.assertEqual(set(), excluded)

    def test_every_allergy_case_in_the_eval_set_is_still_detected(self) -> None:
        cases = [
            json.loads(line)
            for line in GOLDEN.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        allergy_cases = [c for c in cases if c.get("family") == "allergy"]
        self.assertTrue(allergy_cases)
        missed = [
            c["query"]
            for c in allergy_cases
            if not extract_constraints(c["query"])["allergens"]
        ]
        self.assertEqual([], missed)

    def test_a_declared_allergy_still_excludes_the_dishes(self) -> None:
        constraints = extract_constraints("Tôi dị ứng hải sản, món nào an toàn?")
        self.assertEqual(["seafood"], constraints["allergens"])
        excluded = infer_allergen_excluded_menu_item_ids(constraints["allergens"], _menu())
        self.assertEqual({"m_1", "m_2"}, excluded)

    def test_an_allergy_does_not_become_a_requested_category(self) -> None:
        # Filtering *to* seafood while excluding all seafood leaves nothing.
        constraints = extract_constraints("Tôi dị ứng hải sản, món nào an toàn?")
        self.assertIsNone(constraints["category"])

    def test_other_avoidance_phrasings_count_as_allergy_context(self) -> None:
        for query in (
            "Tôi không ăn được tôm, gợi ý món khác",
            "Tránh món có tôm cua mực giúp tôi",
            "Allergic to shellfish, what to avoid?",
            "Co mon nao khong co hai san khong?",
        ):
            with self.subTest(query=query):
                self.assertEqual(["seafood"], extract_constraints(query)["allergens"])


if __name__ == "__main__":
    unittest.main()
