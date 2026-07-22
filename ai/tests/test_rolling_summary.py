"""Tests for deterministic rolling summary updates."""
from __future__ import annotations

import unittest

from app.rag.rolling_summary import update_rolling_summary


class RollingSummaryTests(unittest.TestCase):
    def test_first_turn_creates_summary(self) -> None:
        summary = update_rolling_summary(
            "",
            user_message="Ở đây có những món phở gì?",
            assistant_content="Nhà hàng có phở bò, phở gà, phở tái.",
            suggested_actions=[],
            constraints={"party_size": 2},
        )
        self.assertIn("Số khách: 2 người", summary)
        self.assertIn("Lượt gần đây:", summary)
        self.assertIn("Khách: Ở đây có những món phở gì", summary)

    def test_second_turn_merges_constraints_and_suggestions(self) -> None:
        previous = update_rolling_summary(
            "",
            user_message="2 người",
            assistant_content="Mình ghi nhận 2 người.",
            suggested_actions=[],
            constraints={"party_size": 2},
        )
        summary = update_rolling_summary(
            previous,
            user_message="Tránh tôm cua",
            assistant_content="Mình sẽ tránh các món có tôm, cua.",
            suggested_actions=[{"name": "Phở bò", "menu_item_id": "m_001"}],
            constraints={"allergens": ["tôm", "cua"], "party_size": 2},
        )
        self.assertIn("Tránh: tôm, cua", summary)
        self.assertIn("Đã gợi ý: Phở bò", summary)
        self.assertEqual(summary.count("Lượt gần đây:"), 1)
        self.assertIn("2 người", summary)

    def test_recent_turns_capped(self) -> None:
        summary = ""
        for index in range(6):
            summary = update_rolling_summary(
                summary,
                user_message=f"Câu {index}",
                assistant_content=f"Trả lời {index}",
                suggested_actions=[],
                constraints={},
            )
        recent_lines = [line for line in summary.splitlines() if line.startswith("- Khách:")]
        self.assertLessEqual(len(recent_lines), 4)


if __name__ == "__main__":
    unittest.main()
