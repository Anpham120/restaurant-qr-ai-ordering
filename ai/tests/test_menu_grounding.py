from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.rag.menu_grounding import MenuCandidateRetriever, select_menu_candidates
from app.rag.output_parser import parse_model_response


MENU = [
    {
        "id": "sea_1",
        "name": "Nghêu hấp sả",
        "category_name": "Hải sản",
        "description": "Nghêu tươi hấp sả",
        "tags": ["Hấp", "Nhậu"],
        "is_available": True,
    },
    {
        "id": "sea_2",
        "name": "Tôm rang muối Tây Ninh",
        "category_name": "Hải sản",
        "description": "Tôm sú rang muối",
        "tags": ["Tôm", "Chia sẻ"],
        "is_available": True,
    },
    {
        "id": "main_1",
        "name": "Cơm cá kho tộ",
        "category_name": "Món chính",
        "description": "Cơm cá kho",
        "tags": ["Bữa chính"],
        "is_available": True,
    },
]


class MenuGroundingTests(unittest.TestCase):
    def test_v34_category_request_only_returns_live_category_candidates(self):
        candidates = select_menu_candidates("Cho tôi các món hải sản", MENU)

        self.assertEqual({"sea_1", "sea_2"}, {item["id"] for item in candidates})
        self.assertTrue(all(item["category_name"] == "Hải sản" for item in candidates))

    def test_v34_tag_request_only_returns_matching_tag_candidates(self):
        candidates = select_menu_candidates("Tôi muốn món hấp", MENU)

        self.assertEqual(["sea_1"], [item["id"] for item in candidates])

    def test_v34_response_parser_removes_repeated_sentence(self):
        parsed = parse_model_response(
            '{"content":"Nghêu hấp sả rất hợp. Nghêu hấp sả rất hợp.",'
            '"suggested_cart_actions":[],"guardrail_flags":[]}',
            MENU,
        )

        self.assertIsNotNone(parsed)
        self.assertEqual("Nghêu hấp sả rất hợp.", parsed.content)

    def test_v38_hybrid_live_menu_retrieval_keeps_hard_category_filter(self):
        retriever = MenuCandidateRetriever("hybrid", encoder=_SemanticTestEncoder())

        candidates = retriever.select("Gợi ý hải sản có tôm, vị biển thanh mát", MENU)

        self.assertEqual("sea_2", candidates[0]["id"])

    def test_response_parser_deduplicates_menu_actions(self):
        parsed = parse_model_response(
            '{"content":"Gợi ý món.","suggested_cart_actions":['
            '{"menu_item_id":"sea_1"},{"menu_item_id":"sea_1"}],'
            '"guardrail_flags":[]}',
            MENU,
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(["sea_1"], [item["menu_item_id"] for item in parsed.suggested_cart_actions])
        self.assertNotIn("MENU_FABRICATION_BLOCKED", parsed.guardrail_flags)

    def test_v38_live_menu_has_91_items_including_drinks(self):
        menu_path = Path(__file__).resolve().parents[2] / "backend" / "data" / "menu-dataset.json"
        source_items = json.loads(menu_path.read_text(encoding="utf-8-sig"))["items"]
        menu_items = [
            {
                "id": item["id"],
                "name": item["name"],
                "description": item["description"],
                "category_name": item["categoryName"],
                "tags": item["tags"],
                "is_available": item["isAvailable"],
            }
            for item in source_items
        ]

        candidates = select_menu_candidates("Gợi ý đồ uống có cồn, vị mát dễ uống", menu_items)

        self.assertEqual(91, len(menu_items))
        self.assertEqual(7, len(candidates))
        self.assertTrue(all(item["category_name"] == "Bia & Rượu" for item in candidates))


class _SemanticTestEncoder:
    model_name = "semantic-test"
    model_revision = "1"
    dimension = 3

    def encode_documents(self, texts):
        return [self._vector(text) for text in texts]

    def encode_queries(self, texts):
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text):
        normalized = text.casefold()
        return (
            1.0 if any(term in normalized for term in ("nghêu", "ấm", "sả")) else 0.0,
            1.0 if any(term in normalized for term in ("tôm", "thanh mát", "biển")) else 0.0,
            1.0 if "cơm" in normalized else 0.0,
        )


if __name__ == "__main__":
    unittest.main()
