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
    def test_budget_aliases_resolve_to_the_live_budget_tag(self) -> None:
        menu_items = [
            _item(
                "menu:m_cheap",
                category_id="cat_main",
                category_name="Món chính",
                tags=["bình dân"],
            ),
            _item(
                "menu:m_premium",
                category_id="cat_main",
                category_name="Món chính",
                tags=["cao cấp"],
            ),
        ]

        for query in (
            "Tôi muốn chọn món có mức giá tiết kiệm",
            "Menu có món nào hợp ngân sách thấp không?",
            "Cho tôi xem các lựa chọn giá mềm",
            "Món nào phù hợp khi tôi muốn chi tiêu vừa phải?",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    {"menu:m_cheap"},
                    infer_allowed_menu_item_ids(query, menu_items),
                )

    def test_budget_aliases_do_not_match_unrelated_squid_or_garlic_terms(self) -> None:
        menu_items = [
            _item(
                "menu:m_squid",
                category_id="cat_main",
                category_name="Món chính",
                tags=["mực", "hải sản"],
            ),
            _item(
                "menu:m_garlic",
                category_id="cat_main",
                category_name="Món chính",
                tags=["tỏi"],
            ),
            _item(
                "menu:m_cheap",
                category_id="cat_main",
                category_name="Món chính",
                tags=["bình dân"],
            ),
        ]

        allowed = infer_allowed_menu_item_ids(
            "Tôi muốn hỏi mức cay của món mực xào tỏi",
            menu_items,
        )
        self.assertNotIn("menu:m_cheap", allowed or set())

    def test_party_size_aliases_resolve_to_the_live_portion_tag(self) -> None:
        menu_items = [
            _item(
                "menu:m_shared",
                category_id="cat_main",
                category_name="Món chính",
                tags=["2-3 người"],
            ),
            _item(
                "menu:m_solo",
                category_id="cat_main",
                category_name="Món chính",
                tags=["1 người"],
            ),
        ]

        for query in (
            "Gợi ý món cho hai người cùng ăn",
            "Bàn tôi có ba khách thì nên chọn món nào?",
            "Món nào đủ để chia sẻ cho nhóm 2 đến 3 người?",
            "Tư vấn món chung cho một cặp đôi",
            "Có lựa chọn nào phù hợp bàn ba người không?",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    {"menu:m_shared"},
                    infer_allowed_menu_item_ids(query, menu_items),
                )

    def test_specific_tag_does_not_collide_with_vietnamese_function_words(self) -> None:
        menu_items = [
            _item(
                "menu:m_spicy",
                category_id="cat_main",
                category_name="Món chính",
                tags=["cay dam"],
            ),
            _item(
                "menu:m_garlic",
                category_id="cat_main",
                category_name="Món chính",
                tags=["toi"],
            ),
            _item(
                "menu:m_squid",
                category_id="cat_main",
                category_name="Món chính",
                tags=["muc"],
            ),
        ]

        for query in (
            "Tôi muốn món cay đậm ở mức vừa phải",
            "Toi muon mon cay dam o muc vua phai",
        ):
            with self.subTest(query=query):
                self.assertEqual(
                    {"menu:m_spicy"},
                    infer_allowed_menu_item_ids(query, menu_items),
                )

        self.assertIsNone(
            infer_allowed_menu_item_ids("Tôi muốn chọn món", menu_items)
        )

    def test_ambiguous_ascii_tags_require_explicit_accented_aliases(self) -> None:
        menu_items = [
            _item(
                "menu:m_garlic",
                category_id="cat_main",
                category_name="Món chính",
                tags=["toi"],
            ),
            _item(
                "menu:m_squid",
                category_id="cat_main",
                category_name="Món chính",
                tags=["muc", "xao"],
            ),
            _item(
                "menu:m_other_stir_fry",
                category_id="cat_main",
                category_name="Món chính",
                tags=["xao"],
            ),
        ]

        self.assertEqual(
            {"menu:m_garlic"},
            infer_allowed_menu_item_ids("Có món dùng tỏi không?", menu_items),
        )
        self.assertEqual(
            {"menu:m_squid"},
            infer_allowed_menu_item_ids("Có món mực xào không?", menu_items),
        )

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

    def test_named_pho_family_restricts_candidates_to_pho_items(self) -> None:
        menu_items = [
            {
                "id": "m_pho_bo",
                "name": "Phở bò tái nạm",
                "category_id": "cat_pho_bun",
                "category_name": "Phở & Bún",
                "tags": [],
                "is_available": True,
            },
            {
                "id": "m_pho_ga",
                "name": "Phở gà ta",
                "category_id": "cat_pho_bun",
                "category_name": "Phở & Bún",
                "tags": [],
                "is_available": True,
            },
            {
                "id": "m_bun_bo",
                "name": "Bún bò Huế",
                "category_id": "cat_pho_bun",
                "category_name": "Phở & Bún",
                "tags": [],
                "is_available": True,
            },
            {
                "id": "m_ga_xao",
                "name": "Gà xào sả ớt",
                "category_id": "cat_chicken",
                "category_name": "Món gà",
                "tags": [],
                "is_available": True,
            },
        ]

        allowed = infer_allowed_menu_item_ids(
            "Gợi ý cho mình món phở tại nhà hàng đi",
            menu_items,
        )

        self.assertEqual({"m_pho_bo", "m_pho_ga"}, allowed)

    def test_accented_payment_word_does_not_match_tea_alias(self) -> None:
        menu_items = [
            {
                "id": "m_tea",
                "name": "Trà đào cam sả",
                "category_id": "cat_drinks",
                "category_name": "Cà phê & Trà",
                "tags": [],
                "is_available": True,
            },
            {
                "id": "m_other",
                "name": "Cơm tấm sườn bì chả",
                "category_id": "cat_rice",
                "category_name": "Cơm Việt",
                "tags": [],
                "is_available": True,
            },
        ]

        allowed = infer_allowed_menu_item_ids(
            "Mình muốn trả bằng thẻ được không?",
            menu_items,
        )

        self.assertIsNone(allowed)

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
