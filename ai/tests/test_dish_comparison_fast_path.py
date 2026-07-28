"""Contract for the deterministic dish-comparison path.

The path exists because the generation step measured poorly on comparison
questions: it described taste without citing a figure, attached no cart card, and
sometimes dropped one of the named dishes entirely.  These tests pin the
behaviour that justified adding it, and — just as importantly — pin the cases
where it must stay out of the way.
"""
from __future__ import annotations

import unittest

from app.rag.dish_comparison_fast_path import (
    find_named_dishes,
    has_comparison_intent,
    try_dish_comparison_fast_path,
)


def _menu() -> list[dict]:
    return [
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
            "id": "m_bun_bo",
            "name": "Bún bò Huế",
            "category_name": "Phở & Bún",
            "price_vnd": 80000,
            "tags": ["cay vua", "co hai san"],
            "is_available": True,
        },
        {
            "id": "m_bia",
            "name": "Bia Tiger Crystal",
            "category_name": "Bia & Rượu",
            "price_vnd": 35000,
            "tags": [],
            "is_available": True,
        },
        {
            "id": "m_het",
            "name": "Cá lóc nướng trui",
            "category_name": "Hải sản",
            "price_vnd": 150000,
            "tags": [],
            "is_available": False,
        },
    ]


class DishComparisonFastPathTests(unittest.TestCase):
    def test_compares_two_dishes_with_figures_from_the_live_menu(self) -> None:
        response = try_dish_comparison_fast_path(
            "Phở bò với phở gà khác gì nhau?", _menu()
        )

        self.assertIsNotNone(response)
        content = response["content"]
        # Số liệu phải lấy từ thực đơn, không được là mô tả cảm quan chung.
        self.assertIn("75.000đ", content)
        self.assertIn("70.000đ", content)
        self.assertIn("Phở & Bún", content)
        self.assertTrue(response["model"].startswith("deterministic-"))

    def test_attaches_a_cart_card_for_every_dish_compared(self) -> None:
        response = try_dish_comparison_fast_path(
            "so sánh phở bò và phở gà", _menu()
        )

        ids = [action["menu_item_id"] for action in response["suggested_cart_actions"]]
        self.assertEqual({"m_pho_bo", "m_pho_ga"}, set(ids))
        self.assertTrue(
            all(a["requires_customer_confirmation"] for a in response["suggested_cart_actions"])
        )

    def test_every_claim_cites_a_real_menu_item(self) -> None:
        response = try_dish_comparison_fast_path(
            "nên chọn phở bò hay phở gà?", _menu()
        )

        menu_ids = {item["id"] for item in _menu()}
        for claim in response["claims"]:
            self.assertTrue(claim["verified"])
            self.assertTrue(claim["evidence_ids"])
            for evidence_id in claim["evidence_ids"]:
                self.assertIn(evidence_id, menu_ids)

    def test_matches_the_short_name_a_guest_actually_types(self) -> None:
        # Khách gõ "phở bò", thực đơn ghi "Phở bò tái nạm".
        dishes = find_named_dishes("phở bò với phở gà", _menu())

        self.assertEqual(
            {"m_pho_bo", "m_pho_ga"}, {dish["id"] for dish in dishes}
        )

    def test_does_not_fire_when_no_dish_is_named(self) -> None:
        # Câu này thật sự mơ hồ: phải nhường cho đường hỏi lại, không được đoán.
        self.assertIsNone(
            try_dish_comparison_fast_path("Món nào ngon hơn vậy bạn?", _menu())
        )

    def test_does_not_fire_for_a_single_dish(self) -> None:
        self.assertIsNone(
            try_dish_comparison_fast_path("phở bò bao nhiêu tiền?", _menu())
        )

    def test_does_not_fire_without_a_comparison_signal(self) -> None:
        # Nhắc tên hai món trong câu kể không phải là yêu cầu so sánh.
        self.assertIsNone(
            try_dish_comparison_fast_path(
                "hôm qua mình ăn phở bò tái nạm rồi phở gà ta", _menu()
            )
        )

    def test_refuses_to_compare_across_item_kinds(self) -> None:
        # Đối chiếu một món ăn với một loại bia không có ý nghĩa.
        self.assertIsNone(
            try_dish_comparison_fast_path("so sánh phở bò với bia Tiger", _menu())
        )

    def test_ignores_dishes_that_are_sold_out(self) -> None:
        response = try_dish_comparison_fast_path(
            "so sánh phở bò với cá lóc nướng trui", _menu()
        )

        # Chỉ còn một món khả dụng nên không đủ để so sánh.
        self.assertIsNone(response)

    def test_reports_the_price_gap_between_dishes(self) -> None:
        response = try_dish_comparison_fast_path(
            "so sánh phở bò và phở gà", _menu()
        )

        # 75.000 − 70.000 = 5.000
        self.assertIn("5.000đ", response["content"])

    def test_names_a_spice_level_only_when_the_catalogue_records_one(self) -> None:
        response = try_dish_comparison_fast_path(
            "so sánh bún bò Huế và phở gà", _menu()
        )

        content = response["content"]
        self.assertIn("cay vừa", content)      # bún bò Huế có nhãn cay vừa
        self.assertIn("không cay", content)    # phở gà có nhãn không cay
        self.assertIn("hai san", content)      # dị nguyên phải được nêu

    def test_does_not_rank_dishes_as_better(self) -> None:
        response = try_dish_comparison_fast_path(
            "phở bò hay phở gà ngon hơn?", _menu()
        )

        content = response["content"].casefold()
        # dish-comparison.md cấm xếp hạng theo "ngon hơn" — độ ngon là chủ quan.
        self.assertNotIn("ngon hơn", content)
        self.assertNotIn("tốt hơn", content)

    def test_comparison_intent_needs_a_marker_or_two_matched_dishes(self) -> None:
        self.assertTrue(has_comparison_intent("so sánh hai món này", matched_count=0))
        self.assertTrue(has_comparison_intent("phở bò với phở gà", matched_count=2))
        self.assertFalse(has_comparison_intent("phở bò với phở gà", matched_count=1))


if __name__ == "__main__":
    unittest.main()
