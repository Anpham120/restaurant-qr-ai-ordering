"""Contract for the answer-quality metric.

A metric that scores the system is itself something to be wrong about, and three of
its first findings were its own false positives, not faults in the assistant:

* the five comparison answers were marked ungrounded for correctly stating a price
  *gap* ("thấp hơn 5.000đ"), a figure that matches no dish's price;
* the deflection rate read 43% because an answer that listed dishes and then offered
  to go further — "... Bạn muốn thêm gì không?" — was counted as asking back;
* a nutrition lookup citing one dish was marked unactionable for carrying no cart
  card, when the guest asked for a figure rather than to order.

So the metric is tested in both directions: it must catch the real faults, and it
must not invent them.
"""
from __future__ import annotations

import unittest

from evaluation.answer_quality_metrics import (
    looks_like_deflection,
    score_actionability,
    score_answer,
    score_constraint_respect,
    score_containment,
    score_grounding,
)


def _menu() -> list[dict]:
    return [
        {
            "id": "m_pho_bo",
            "name": "Phở bò tái nạm",
            "category_id": "cat_pho",
            "category_name": "Phở & Bún",
            "price_vnd": 75000,
            "tags": ["khong cay", "tre em"],
        },
        {
            "id": "m_pho_ga",
            "name": "Phở gà ta",
            "category_id": "cat_pho",
            "category_name": "Phở & Bún",
            "price_vnd": 70000,
            "tags": ["khong cay", "tre em"],
        },
        {
            "id": "m_lau",
            "name": "Lẩu bò nhúng giấm",
            "category_id": "cat_hotpot",
            "category_name": "Lẩu",
            "price_vnd": 350000,
            "tags": ["cay vua"],
        },
        {
            "id": "m_tom",
            "name": "Gỏi cuốn tôm thịt",
            "category_id": "cat_appetiser",
            "category_name": "Khai vị",
            "price_vnd": 65000,
            "tags": ["co hai san"],
        },
    ]


def _response(**overrides) -> dict:
    base = {
        "content": "Mình gợi ý Phở bò tái nạm (75.000đ).",
        "evidence": [{"source": "live_menu", "menu_item_id": "m_pho_bo"}],
        "suggested_cart_actions": [{"menu_item_id": "m_pho_bo"}],
    }
    base.update(overrides)
    return base


class ConstraintRespectTests(unittest.TestCase):
    def test_a_dish_over_the_budget_is_a_violation(self) -> None:
        response = _response(
            evidence=[{"menu_item_id": "m_lau"}],
            suggested_cart_actions=[{"menu_item_id": "m_lau"}],
        )
        score = score_constraint_respect(
            "2 nguoi budget 250k", {"budget_vnd": 250000}, response, _menu()
        )
        self.assertIn("budget", score["violations"])

    def test_a_dish_within_the_budget_is_not(self) -> None:
        score = score_constraint_respect(
            "2 nguoi budget 250k", {"budget_vnd": 250000}, _response(), _menu()
        )
        self.assertTrue(score["respected"])

    def test_offering_an_allergen_dish_is_a_violation(self) -> None:
        response = _response(
            content="Mình gợi ý Gỏi cuốn tôm thịt.",
            evidence=[{"menu_item_id": "m_tom"}],
            suggested_cart_actions=[{"menu_item_id": "m_tom"}],
        )
        score = score_constraint_respect(
            "Di ung hai san, mon nao an toan?",
            {"allergens": ["seafood"]},
            response,
            _menu(),
        )
        self.assertIn("allergen_offered", score["violations"])

    def test_naming_a_dish_to_avoid_is_not_a_violation(self) -> None:
        # The avoid list exists to name exactly these dishes.
        response = _response(
            content="Các món sau có ghi nhận hải sản, bạn nên bỏ qua:\n- Gỏi cuốn tôm thịt",
            evidence=[{"menu_item_id": "m_tom"}],
            suggested_cart_actions=[],
        )
        score = score_constraint_respect(
            "Di ung hai san, nen tranh mon nao?",
            {"allergens": ["seafood"]},
            response,
            _menu(),
        )
        self.assertTrue(score["respected"])

    def test_a_spicy_dish_for_a_no_spice_request_is_a_violation(self) -> None:
        response = _response(evidence=[{"menu_item_id": "m_lau"}])
        score = score_constraint_respect(
            "Mon nao khong cay?", {"spice": "none"}, response, _menu()
        )
        self.assertIn("spice", score["violations"])


class GroundingTests(unittest.TestCase):
    def test_a_dish_that_does_not_exist_is_ungrounded(self) -> None:
        response = _response(evidence=[{"menu_item_id": "m_invented"}])
        self.assertFalse(score_grounding(response, _menu())["grounded"])

    def test_a_price_gap_between_two_cited_dishes_is_grounded(self) -> None:
        # 75.000 - 70.000 = 5.000 matches no dish's price and is still correct.
        response = _response(
            content="Phở gà ta thấp hơn Phở bò tái nạm 5.000đ.",
            evidence=[{"menu_item_id": "m_pho_bo"}, {"menu_item_id": "m_pho_ga"}],
        )
        self.assertTrue(score_grounding(response, _menu())["grounded"])

    def test_a_price_belonging_to_no_cited_dish_is_ungrounded(self) -> None:
        response = _response(content="Phở bò tái nạm (99.000đ).")
        self.assertFalse(score_grounding(response, _menu())["grounded"])


class ContainmentTests(unittest.TestCase):
    def test_guidance_text_is_caught(self) -> None:
        response = _response(content="Danh sách món: tên, giá, mô tả ngắn.")
        self.assertFalse(score_containment(response)["contained"])

    def test_a_forbidden_safety_claim_is_caught(self) -> None:
        response = _response(content="Món này an toàn 100% cho người dị ứng.")
        self.assertFalse(score_containment(response)["contained"])

    def test_an_ordinary_answer_is_contained(self) -> None:
        self.assertTrue(score_containment(_response())["contained"])


class ActionabilityAndDeflectionTests(unittest.TestCase):
    def test_a_listing_without_cards_is_not_actionable(self) -> None:
        response = _response(
            evidence=[{"menu_item_id": "m_pho_bo"}, {"menu_item_id": "m_pho_ga"}],
            suggested_cart_actions=[],
        )
        self.assertFalse(score_actionability(response)["actionable"])

    def test_a_single_dish_lookup_needs_no_card(self) -> None:
        response = _response(
            content="Bún bò Huế khoảng 600 kcal.",
            evidence=[{"menu_item_id": "m_pho_bo"}],
            suggested_cart_actions=[],
        )
        self.assertTrue(score_actionability(response)["actionable"])

    def test_answering_then_offering_more_is_not_a_deflection(self) -> None:
        response = _response(
            content="Mình gợi ý Phở bò tái nạm (75.000đ). Bạn muốn thêm gì không?"
        )
        self.assertFalse(looks_like_deflection(response))

    def test_asking_back_with_nothing_to_act_on_is_a_deflection(self) -> None:
        response = _response(
            content="Bạn muốn món no hay món ăn vặt để mình gợi ý đúng hơn?",
            evidence=[],
            suggested_cart_actions=[],
        )
        self.assertTrue(looks_like_deflection(response))

    def test_a_statement_is_not_a_deflection(self) -> None:
        response = _response(content="Nhà hàng mở cửa 10:00 - 22:00.", evidence=[])
        self.assertFalse(looks_like_deflection(response))


class OverallScoreTests(unittest.TestCase):
    def test_a_good_answer_is_usable(self) -> None:
        score = score_answer("Goi y mon pho", {}, _response(), _menu())
        self.assertTrue(score["usable"])

    def test_a_budget_violation_makes_it_unusable(self) -> None:
        response = _response(
            content="Mình gợi ý Lẩu bò nhúng giấm (350.000đ).",
            evidence=[{"menu_item_id": "m_lau"}],
            suggested_cart_actions=[{"menu_item_id": "m_lau"}],
        )
        score = score_answer(
            "2 nguoi budget 250k", {"budget_vnd": 250000}, response, _menu()
        )
        self.assertFalse(score["usable"])


if __name__ == "__main__":
    unittest.main()
