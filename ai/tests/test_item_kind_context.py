"""A question about food must not be answered with a drink.

Asked "Không cay cho ông bà", the assistant cited "Đu đủ chín mật ong" and a
beverage.  The `nguoi gia` label was right; the item kind was never constrained,
because `detect_requested_item_kind` returned None: the question contains no "món"
token and no phrase from the food list.

Spice level is a property of food — nobody describes a drink as "không cay" — and a
named meal is food.  Both are now food context.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.rag.menu_item_kind import detect_requested_item_kind
from app.rag.menu_query_filters import has_child_dining_context

AI_ROOT = Path(__file__).resolve().parents[1]
GOLDEN = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"


class ItemKindContextTests(unittest.TestCase):
    def test_a_spice_preference_implies_food(self) -> None:
        for query in (
            "Khong cay cho ong ba",
            "It cay cho tre",
            "Mon khong qua man cho nguoi gia",
        ):
            with self.subTest(query=query):
                self.assertEqual("food", detect_requested_item_kind(query))

    def test_a_named_meal_implies_food(self) -> None:
        for query in ("Bua sang co gi?", "An trua 3 nguoi", "Bua toi an gi?"):
            with self.subTest(query=query):
                self.assertEqual("food", detect_requested_item_kind(query))

    def test_drink_and_dessert_questions_are_untouched(self) -> None:
        expected = {
            "Nhom do uong": "drink",
            "Cho xem do uong": "drink",
            "Bia gi ngon?": "drink",
            "Nuoc ep gi ngon?": "drink",
            "Sinh to xoai": "drink",
            "Trang mieng menu": "dessert",
        }
        for query, kind in expected.items():
            with self.subTest(query=query):
                self.assertEqual(kind, detect_requested_item_kind(query))

    def test_che_on_its_own_is_a_dessert(self) -> None:
        # "Chè có gì?" returned None and was answered from the whole menu.
        for query in ("Che co gi?", "Cho xem che", "Mon che nao ngon?"):
            with self.subTest(query=query):
                self.assertEqual("dessert", detect_requested_item_kind(query))

    def test_food_for_a_child_is_recognised_however_it_is_phrased(self) -> None:
        # "cho tre" sat next to "cho be" and "cho chau" in every natural phrasing
        # but was missing, so "ít cay cho trẻ" did not reach the child-safety filter.
        for query in ("It cay cho tre", "Mon cho tre", "Nhe cho tre nho", "Be 3 tuoi an gi?"):
            with self.subTest(query=query):
                self.assertTrue(has_child_dining_context(query))

    def test_youngest_dish_is_not_a_child(self) -> None:
        # "trẻ nhất" shares the token `tre`; it is not a dining context.
        self.assertFalse(has_child_dining_context("Tre nhat trong menu la gi?"))
        self.assertFalse(has_child_dining_context("Goi y mon pho"))

    def test_eval_cases_that_browse_for_dishes_are_constrained_to_food(self) -> None:
        # Named per case rather than counted: a threshold hides which cases matter,
        # and three of the unconstrained ones are unconstrained correctly.
        for query in (
            "Khong an duoc cay, chon gi?",
            "It cay cho tre em",
            "Mon nao khong cay?",
            "Mon khong qua man cho nguoi gia",
            "Nguoi gia an gi de nhai?",
        ):
            with self.subTest(query=query):
                self.assertEqual("food", detect_requested_item_kind(query))

    def test_questions_that_are_not_about_choosing_a_dish_stay_unconstrained(self) -> None:
        # A high chair is furniture, and the spice level of a dish the guest already
        # named is answered from that dish — neither is a request to browse food.
        for query in (
            "Co ghe tre em khong?",
            "Highchair available?",
            "Muc do cay pho bo?",
            "Bun bo hue cay khong?",
        ):
            with self.subTest(query=query):
                self.assertIsNone(detect_requested_item_kind(query))


if __name__ == "__main__":
    unittest.main()
