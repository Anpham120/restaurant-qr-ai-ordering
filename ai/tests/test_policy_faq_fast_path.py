import unittest
from types import SimpleNamespace

from app.rag.policy_faq_fast_path import try_wifi_policy_fast_path


class PolicyFaqFastPathTests(unittest.TestCase):
    def _chunk(self, source: str, title: str, content: str, score: float = 0.9):
        return SimpleNamespace(
            chunk=SimpleNamespace(source=source, title=title, content=content),
            score=score,
        )

    def test_wifi_password_question_returns_credentials(self):
        retrieved = [
            self._chunk(
                "faq.md",
                "Nhà hàng có wifi không?",
                "Có, nhà hàng cung cấp wifi miễn phí cho khách. "
                "Tên mạng: CMC_Restaurant_Guest, mật khẩu: cmcfood2026.",
            )
        ]
        result = try_wifi_policy_fast_path("mật khẩu wifi tại nhà hàng là gì", retrieved)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("CMC_Restaurant_Guest", result["content"])
        self.assertIn("cmcfood2026", result["content"])
        self.assertEqual(result["model"], "deterministic-wifi-faq")

    def test_wifi_availability_without_password(self):
        retrieved = [
            self._chunk(
                "faq.md",
                "Nhà hàng có wifi không?",
                "Có, nhà hàng cung cấp wifi miễn phí cho khách.",
            )
        ]
        result = try_wifi_policy_fast_path("nhà hàng có wifi không", retrieved)
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("wifi", result["content"].casefold())
        self.assertNotIn("cmcfood2026", result["content"])

    def test_non_wifi_question_returns_none(self):
        retrieved = [
            self._chunk(
                "faq.md",
                "Nhà hàng có wifi không?",
                "Tên mạng: CMC_Restaurant_Guest, mật khẩu: cmcfood2026.",
            )
        ]
        self.assertIsNone(try_wifi_policy_fast_path("giá phở bò bao nhiêu", retrieved))


if __name__ == "__main__":
    unittest.main()
