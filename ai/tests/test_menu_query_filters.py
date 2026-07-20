from __future__ import annotations

import unittest

from app.rag.knowledge_base import KnowledgeChunk
from app.rag.menu_query_filters import (
    filter_menu_retrieval_results,
    has_allergy_avoidance_context,
    infer_allergen_excluded_menu_item_ids,
    infer_allowed_menu_item_ids,
    infer_excluded_menu_item_ids,
)
from app.rag.retriever import RetrievedChunk


def _item(
    item_id: str,
    *,
    category_id: str = "cat_alcohol",
    category_name: str = "Bia & Rượu",
    tags: tuple[str, ...] = ("nhau",),
) -> dict:
    return {
        "id": item_id,
        "category_id": category_id,
        "category_name": category_name,
        "tags": list(tags),
        "is_available": True,
    }


def _result(item_id: str, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=KnowledgeChunk(
            source=item_id,
            title=item_id,
            content="",
            tags=(),
        ),
        score=score,
    )


class MenuQueryFilterTests(unittest.TestCase):
    def test_alcohol_query_restricts_to_alcohol_category(self) -> None:
        menu_items = [
            _item("menu:m_085"),
            _item("menu:m_086"),
            _item(
                "menu:m_057",
                category_id="cat_cà_phê_trà",
                category_name="Cà phê & Trà",
                tags=("ngot",),
            ),
        ]
        allowed = infer_allowed_menu_item_ids(
            "Quán có bia nào để dùng cùng món nhậu?",
            menu_items,
        )
        self.assertEqual({"menu:m_085", "menu:m_086"}, allowed)

    def test_rejection_healthy_excludes_sweet_items(self) -> None:
        menu_items = [
            _item(
                "menu:m_078",
                category_id="cat_tráng_miệng",
                category_name="Tráng miệng",
                tags=("ngot", "trang mieng"),
            ),
            _item(
                "menu:m_052",
                category_id="cat_món_chay",
                category_name="Món chay",
                tags=("healthy", "it calo"),
            ),
        ]
        excluded = infer_excluded_menu_item_ids(
            "Tôi không thích các món ngọt vừa rồi, gợi ý món healthy khác",
            menu_items,
        )
        self.assertIn("menu:m_078", excluded)
        self.assertNotIn("menu:m_052", excluded)

    def test_filter_does_not_backfill_outside_allowed_category(self) -> None:
        menu_items = [
            _item(f"menu:m_08{index}") for index in range(5, 8)
        ] + [
            _item(
                "menu:m_057",
                category_id="cat_cà_phê_trà",
                category_name="Cà phê & Trà",
                tags=("ngot",),
            ),
        ]
        results = [
            _result("menu:m_085", 0.9),
            _result("menu:m_086", 0.8),
            _result("menu:m_087", 0.7),
            _result("menu:m_057", 0.6),
            _result("menu:m_050", 0.5),
        ]
        filtered = filter_menu_retrieval_results(
            "Quán có bia nào để dùng cùng món nhậu?",
            results,
            menu_items,
        )
        self.assertEqual(
            ["menu:m_085", "menu:m_086", "menu:m_087"],
            [item.chunk.source for item in filtered],
        )

    def test_allergen_exclusion_matches_name_description_and_tags(self) -> None:
        menu_items = [
            {
                "id": "m_024",
                "name": "Tôm sú rang muối",
                "description": "Tôm sú tươi rang muối ớt",
                "tags": ["hai san"],
                "is_available": True,
            },
            {
                "id": "m_001",
                "name": "Gỏi cuốn",
                "description": "Rau tươi cuốn bánh tráng",
                "tags": ["khai vi"],
                "is_available": True,
            },
        ]
        excluded = infer_allergen_excluded_menu_item_ids(["seafood"], menu_items)
        self.assertEqual({"m_024"}, excluded)

    def test_allergy_context_detected_for_avoidance_not_browsing(self) -> None:
        self.assertTrue(has_allergy_avoidance_context("Tôi bị dị ứng hải sản, nên tránh món nào?"))
        self.assertTrue(has_allergy_avoidance_context("Allergic to shellfish, what to avoid?"))
        self.assertFalse(has_allergy_avoidance_context("Có món hải sản nào ngon không?"))


if __name__ == "__main__":
    unittest.main()
