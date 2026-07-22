"""Regression tests for the 7-case golden LLM eval failure cluster."""

from __future__ import annotations

import unittest

from app.rag.content_grounding import ground_response_content
from app.rag.menu_presence_fast_path import try_menu_presence_fast_path


MENU = [
    {"id": "m_001", "name": "Phở bò tái nạm", "price_vnd": 75000, "is_available": True},
    {"id": "m_002", "name": "Cơm bò lúc lắc", "price_vnd": 95000, "is_available": True},
]


class SevenCaseRegressionTests(unittest.TestCase):
    def test_menu_presence_skips_allergy_avoidance_query(self) -> None:
        result = try_menu_presence_fast_path(
            "Dị ứng mực nên bỏ qua món nào?",
            MENU,
            wants_recommendations=False,
        )
        self.assertIsNone(result)

    def test_policy_bullets_do_not_trigger_fabrication(self) -> None:
        content = (
            "1. Khi muốn thanh toán, nhấn \"Tính tiền\" trên giao diện.\n"
            "2. Hệ thống hiển thị mã VietQR với số tiền cần thanh toán."
        )
        _, flags, _ = ground_response_content(content, [], MENU, wants_recommendations=False)
        self.assertNotIn("MENU_FABRICATION_BLOCKED", flags)

    def test_allergy_advisory_without_cart_actions_is_allowed(self) -> None:
        content = (
            "Với dị ứng tôm, mình không thể cam kết món nào an toàn tuyệt đối. "
            "Bạn nên báo trực tiếp nhân viên để kiểm tra nguyên liệu trước khi gọi món."
        )
        _, flags, _ = ground_response_content(content, [], MENU, wants_recommendations=True)
        self.assertNotIn("MENU_FABRICATION_BLOCKED", flags)


if __name__ == "__main__":
    unittest.main()
