from __future__ import annotations

import unittest

from app.rag.menu_grounding import select_menu_candidates
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


if __name__ == "__main__":
    unittest.main()
