from __future__ import annotations

import unittest

from app.rag.party_menu_ranking import (
    is_shared_group_dish,
    rank_candidates_for_party,
    shared_dish_score,
)


class PartyMenuRankingTests(unittest.TestCase):
    def test_lau_scores_higher_than_individual_chicken(self) -> None:
        lau = {
            "name": "Lẩu hải sản chua cay",
            "category_name": "Lẩu",
            "tags": ["nau", "tom"],
        }
        chicken = {"name": "Gà rô ti kiểu Việt", "category_name": "Gà"}

        self.assertGreater(shared_dish_score(lau), shared_dish_score(chicken))
        self.assertTrue(is_shared_group_dish(lau))

    def test_rank_candidates_for_party_puts_lau_first(self) -> None:
        menu = [
            {"id": "m_036", "name": "Gà rô ti kiểu Việt"},
            {"id": "m_033", "name": "Lẩu hải sản chua cay", "category_name": "Lẩu", "tags": ["nau"]},
            {"id": "m_008", "name": "Phở bò tái nạm", "category_name": "Phở"},
        ]

        ranked = rank_candidates_for_party(menu, 8)

        self.assertEqual("m_033", ranked[0]["id"])


if __name__ == "__main__":
    unittest.main()
