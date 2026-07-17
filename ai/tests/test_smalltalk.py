from __future__ import annotations

import unittest

from app.rag.smalltalk import try_smalltalk


class SmalltalkTests(unittest.TestCase):
    def test_greeting_returns_instant_template(self) -> None:
        response = try_smalltalk("Xin chào")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual("smalltalk-fastpath", response["model"])
        self.assertIn("CMC Restaurant", response["content"])

    def test_food_related_short_message_is_not_smalltalk(self) -> None:
        self.assertIsNone(try_smalltalk("menu"))

    def test_long_message_is_not_smalltalk(self) -> None:
        self.assertIsNone(try_smalltalk("xin chào bạn ơi mình muốn hỏi về thực đơn hôm nay"))


if __name__ == "__main__":
    unittest.main()
