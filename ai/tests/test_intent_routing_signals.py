from __future__ import annotations

import unittest

from app.rag.intent_routing_signals import (
    is_concrete_dish_order,
    is_open_menu_question,
    is_seating_inquiry,
    is_suggestion_adequacy_follow_up,
)
from app.rag.vietnamese_normalizer import normalize_query_text


def _n(text: str) -> str:
    return normalize_query_text(text)


class IntentRoutingSignalsTests(unittest.TestCase):
    def test_open_menu_question_vs_concrete_order(self) -> None:
        self.assertTrue(is_open_menu_question(_n("4 nguoi goi mon gi")))
        self.assertTrue(is_open_menu_question(_n("nen goi mon gi cho tre em")))
        self.assertFalse(is_concrete_dish_order(_n("4 nguoi goi mon gi")))
        self.assertTrue(is_concrete_dish_order(_n("goi mon bun bo luon")))
        self.assertFalse(is_concrete_dish_order(_n("goi y 3 mon cay nhe")))

    def test_party_preposition_is_not_seating_inquiry(self) -> None:
        self.assertFalse(is_seating_inquiry(_n("cho 8 nguoi goi y mon")))
        self.assertFalse(is_seating_inquiry(_n("500k cho 5 nguoi an gi")))
        self.assertTrue(is_seating_inquiry(_n("mot minh co duoc khong")))
        self.assertTrue(is_seating_inquiry(_n("co ban cho 4 nguoi khong")))

    def test_adequacy_follow_up_shape(self) -> None:
        self.assertTrue(is_suggestion_adequacy_follow_up(_n("du tien khong")))
        self.assertTrue(is_suggestion_adequacy_follow_up(_n("du cho 4 nguoi khong")))
        self.assertFalse(is_suggestion_adequacy_follow_up(_n("wifi mat khau gi")))

    def test_ingredient_presence_follow_up_shape(self) -> None:
        from app.rag.intent_routing_signals import is_ingredient_presence_follow_up

        self.assertTrue(is_ingredient_presence_follow_up(_n("tom cua co khong")))
        self.assertTrue(is_ingredient_presence_follow_up(_n("co hai san khong")))
        self.assertTrue(is_ingredient_presence_follow_up(_n("mon do co lac khong")))
        self.assertFalse(is_ingredient_presence_follow_up(_n("wifi co khong")))
        self.assertFalse(is_ingredient_presence_follow_up(_n("co ban khong")))

    def test_budget_inadequacy_follow_up_shape(self) -> None:
        from app.rag.intent_routing_signals import is_suggestion_adequacy_follow_up

        self.assertTrue(is_suggestion_adequacy_follow_up(_n("het tien khong du")))
        self.assertTrue(is_suggestion_adequacy_follow_up(_n("ngan sach khong du")))


if __name__ == "__main__":
    unittest.main()
