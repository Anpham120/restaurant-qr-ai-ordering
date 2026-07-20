import unittest
from types import SimpleNamespace

from app.rag.kb_info_fast_path import try_kb_info_fast_path


class KbInfoFastPathTests(unittest.TestCase):
    def _chunk(self, source: str, title: str, content: str, score: float = 0.9):
        return SimpleNamespace(
            chunk=SimpleNamespace(source=source, title=title, content=content),
            score=score,
        )

    def test_opening_hours_from_faq(self):
        retrieved = [
            self._chunk(
                "faq.md",
                "Giờ mở cửa của nhà hàng?",
                "CMC Restaurant mở cửa từ 10:00 sáng đến 22:00 tối, phục vụ bữa trưa và bữa tối.",
            )
        ]
        result = try_kb_info_fast_path(
            "gio mo cua nha hang",
            retrieved,
            intent="restaurant_info",
            wants_recommendations=False,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["model"], "deterministic-kb-info")
        self.assertIn("10:00", result["content"])
        self.assertNotIn("chua co", result["content"].lower())

    def test_skips_recommendation_queries(self):
        retrieved = [
            self._chunk("faq.md", "Giờ mở cửa", "Mo cua 10h-22h."),
        ]
        self.assertIsNone(
            try_kb_info_fast_path(
                "goi y mon chay",
                retrieved,
                intent="dietary",
                wants_recommendations=True,
            )
        )

    def test_parking_from_faq_with_gui_xe_synonym(self):
        retrieved = [
            self._chunk(
                "restaurant-info.md",
                "Giao Thông & Đỗ Xe",
                "Khu sân thượng chưa có thang máy. Ô tô đậu bãi công cộng.",
                score=0.95,
            ),
            self._chunk(
                "faq.md",
                "Có chỗ đậu xe không?",
                "Nhà hàng có bãi giữ xe máy miễn phí ngay trước cửa, sức chứa khoảng 30 xe.",
                score=0.7,
            ),
        ]
        result = try_kb_info_fast_path(
            "co cho gui xe khong",
            retrieved,
            intent="restaurant_info",
            wants_recommendations=False,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("bãi giữ xe", result["content"])
        self.assertNotIn("thang máy", result["content"])

    def test_payment_methods(self):
        retrieved = [
            self._chunk(
                "payment-methods.md",
                "Phương thức thanh toán",
                "Nhà hàng chấp nhận tiền mặt, thẻ và VietQR.",
            )
        ]
        result = try_kb_info_fast_path(
            "thanh toan bang gi",
            retrieved,
            intent="payment",
            wants_recommendations=False,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("VietQR", result["content"])

    def test_payment_follow_up_uses_kb_with_group_context(self):
        retrieved = [
            self._chunk(
                "faq.md",
                "Thanh toán bằng hình thức nào?",
                "Nhà hàng chấp nhận tiền mặt, thẻ và VietQR.",
            )
        ]
        history = [
            {"role": "user", "content": "nhóm 8 người"},
            {"role": "assistant", "content": "Gợi ý món", "suggested_cart_actions": [{"menu_item_id": "m_001"}]},
        ]
        result = try_kb_info_fast_path(
            "về thanh toán thì sao",
            retrieved,
            intent="payment",
            wants_recommendations=False,
            history=history,
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("VietQR", result["content"])
        self.assertIn("nhóm 8 người", result["content"])
        self.assertEqual(result["model"], "deterministic-kb-info")

    def test_recommendation_follow_up_skips_kb_fast_path(self):
        history = [
            {"role": "user", "content": "nhóm 8 người"},
            {"role": "assistant", "content": "Gợi ý món", "suggested_cart_actions": [{"menu_item_id": "m_001"}]},
        ]
        self.assertIsNone(
            try_kb_info_fast_path(
                "còn món khác",
                [],
                intent="general",
                wants_recommendations=False,
                history=history,
            )
        )

    def test_is_solo_dining_blocks_kb_fast_path(self):
        retrieved = [
            self._chunk(
                "restaurant-info.md",
                "Không gian",
                "Bàn 2 người phù hợp ăn một mình.",
            )
        ]
        self.assertIsNone(
            try_kb_info_fast_path(
                "chi co minh toi thoi",
                retrieved,
                intent="general",
                wants_recommendations=False,
                is_solo_dining=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
