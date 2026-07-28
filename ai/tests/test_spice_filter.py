"""The spice constraint has to reach the menu, not just the session state.

`spice` was extracted from the question, written into the rolling summary, carried
across turns and consulted by intent classification — and then no filter used it.
"Món nào không cay?" narrowed nothing, even though 68 of 91 dishes carry
`khong cay`.  The constraint existed; the menu never saw it.

Unlabelled dishes are kept on purpose.  Allergen exclusion fails closed because
being wrong there can hurt someone; a missing spice label is missing data, not
evidence that a dish is spicy, and dropping those dishes would only cost the guest
options.
"""
from __future__ import annotations

import unittest

from app.rag.constraint_extractor import extract_constraints
from app.rag.menu_query_filters import SPICE_TAG_ORDER, filter_items_by_spice


def _menu() -> list[dict]:
    return [
        {"id": "m_none", "name": "Phở gà ta", "tags": ["khong cay"]},
        {"id": "m_mild", "name": "Bánh mì pate", "tags": ["cay nhe"]},
        {"id": "m_med", "name": "Gà xào sả ớt", "tags": ["cay vua"]},
        {"id": "m_unlabelled", "name": "Chè khúc bạch", "tags": ["ngot"]},
    ]


class SpiceFilterTests(unittest.TestCase):
    def _names(self, spice: str | None) -> set[str]:
        return {item["name"] for item in filter_items_by_spice(_menu(), spice)}

    def test_no_spice_request_keeps_only_dishes_labelled_not_spicy(self) -> None:
        names = self._names("none")
        self.assertIn("Phở gà ta", names)
        self.assertNotIn("Bánh mì pate", names)
        self.assertNotIn("Gà xào sả ớt", names)

    def test_mild_accepts_not_spicy_as_well(self) -> None:
        # A guest asking for "ít cay" is served by a dish with no chilli at all;
        # the reverse is not true.
        names = self._names("mild")
        self.assertIn("Phở gà ta", names)
        self.assertIn("Bánh mì pate", names)
        self.assertNotIn("Gà xào sả ớt", names)

    def test_hot_excludes_the_not_spicy_dishes(self) -> None:
        names = self._names("hot")
        self.assertIn("Gà xào sả ớt", names)
        self.assertNotIn("Phở gà ta", names)

    def test_unlabelled_dishes_survive_every_level(self) -> None:
        for spice in ("none", "mild", "medium", "hot"):
            with self.subTest(spice=spice):
                self.assertIn("Chè khúc bạch", self._names(spice))

    def test_an_unstated_preference_filters_nothing(self) -> None:
        for spice in (None, "", "unknown"):
            with self.subTest(spice=spice):
                self.assertEqual(4, len(filter_items_by_spice(_menu(), spice)))

    def test_the_levels_the_extractor_produces_are_all_handled(self) -> None:
        # A level the extractor can emit but the filter does not know would silently
        # filter nothing, which is the failure this whole module exists to fix.
        produced = {
            extract_constraints(query)["spice"]
            for query in (
                "Mon nao khong cay?",
                "It cay cho tre em",
                "Mon cay vua co gi?",
                "Spicy seafood dishes?",
                "Goi y mon pho",
            )
        }
        for level in produced - {"unknown"}:
            with self.subTest(level=level):
                filtered = filter_items_by_spice(_menu(), level)
                self.assertLess(len(filtered), 4, f"{level!r} narrowed nothing")

    def test_tag_order_covers_the_labels_the_filter_reasons_about(self) -> None:
        self.assertEqual(
            ("khong cay", "cay nhe", "cay vua", "cay", "rat cay"), SPICE_TAG_ORDER
        )


if __name__ == "__main__":
    unittest.main()
