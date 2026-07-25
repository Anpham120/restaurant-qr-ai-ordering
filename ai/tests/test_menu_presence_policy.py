from __future__ import annotations

import unittest

from app.rag.conversation_policy import build_conversation_policy
from app.rag.menu_presence_fast_path import try_menu_presence_fast_path

MENU = [
    {
        "id": "m_001",
        "name": "Phở bò tái",
        "price_vnd": 85000,
        "is_available": True,
    }
]


class MenuPresencePolicyTests(unittest.TestCase):
    def test_co_mon_pho_khong_is_not_recommendation(self) -> None:
        message = "ở đây có món phở không"
        policy = build_conversation_policy(message, [], "", MENU)
        self.assertFalse(policy.wants_recommendations)
        response = try_menu_presence_fast_path(
            message,
            MENU,
            wants_recommendations=policy.wants_recommendations,
        )
        self.assertIsNotNone(response)
        assert response is not None
        self.assertIn("Phở", response["content"])


if __name__ == "__main__":
    unittest.main()
