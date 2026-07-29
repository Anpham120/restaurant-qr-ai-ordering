"""A budget the guest stated has to reach the menu, on both lists.

`budget_vnd` was extracted from the question and never used to filter, so "2 người
budget 250k" was offered a 350.000đ hotpot and "có món nào dưới 50000 không?" a
65.000đ roll.

Filtering `available_menu_items` alone was not enough: the generation step reads
`candidate_menu_items`, selected separately from the full menu with only exclusions,
item kind and category applied.  With one list filtered and the other not, the model
was still shown dishes the guest had ruled out.  Both carry the constraints now.
"""
from __future__ import annotations

import unittest

from app.rag.menu_query_filters import filter_items_by_budget


def _menu() -> list[dict]:
    return [
        {"id": "m_cheap", "name": "Gỏi cuốn chay", "price_vnd": 45000},
        {"id": "m_mid", "name": "Phở bò tái nạm", "price_vnd": 75000},
        {"id": "m_pricey", "name": "Lẩu bò nhúng giấm", "price_vnd": 350000},
        {"id": "m_nopricce", "name": "Món theo mùa"},
    ]


class BudgetFilterTests(unittest.TestCase):
    def _names(self, budget: int | None) -> set[str]:
        return {item["name"] for item in filter_items_by_budget(_menu(), budget)}

    def test_a_dish_dearer_than_the_whole_budget_is_dropped(self) -> None:
        names = self._names(250000)
        self.assertNotIn("Lẩu bò nhúng giấm", names)
        self.assertIn("Phở bò tái nạm", names)

    def test_a_tight_budget_keeps_only_what_fits(self) -> None:
        names = self._names(50000)
        self.assertEqual({"Gỏi cuốn chay", "Món theo mùa"}, names)

    def test_a_dish_without_a_price_is_kept(self) -> None:
        # Missing price is missing data, not evidence the dish is expensive.
        for budget in (50000, 250000):
            with self.subTest(budget=budget):
                self.assertIn("Món theo mùa", self._names(budget))

    def test_no_budget_filters_nothing(self) -> None:
        for budget in (None, 0):
            with self.subTest(budget=budget):
                self.assertEqual(4, len(filter_items_by_budget(_menu(), budget)))

    def test_the_threshold_is_inclusive(self) -> None:
        # "dưới 50000" is read as "not more than the budget"; a dish priced exactly
        # at the stated figure is a legitimate answer, and excluding it would drop
        # the cheapest thing that fits.
        self.assertIn("Gỏi cuốn chay", self._names(45000))
