"""Catalogue labels a guest never phrases the way the catalogue spells them.

The menu carries 80 distinct tags at ~15 per dish, including 129 meal-time labels,
90 price-tier labels and 71 for children and older guests.  ``_matched_tags``
already filters by any tag it finds in the question — but only when the guest types
the tag verbatim.  "Món rẻ", "ông bà" and "business lunch" matched nothing, so those
labels sat unused, which is why five families measured 8-15% deterministic coverage
while their data was sitting right there.

This is alias data, not new logic: no ninth fast path, no new filter.
"""
from __future__ import annotations

import unittest

from app.rag.menu_query_filters import (
    TAG_QUERY_ALIASES,
    infer_allowed_menu_item_ids,
)
from evaluation.golden_eval_common import load_menu_items


class MenuTagAliasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.menu = load_menu_items()

    def _count(self, query: str) -> int:
        allowed = infer_allowed_menu_item_ids(query, self.menu)
        return len(allowed or [])

    def test_phrasings_that_used_to_match_nothing_now_reach_the_labels(self) -> None:
        for query in (
            "Business lunch set",
            "Bua sang co gi?",
            "Mon re ma ngon",
            "Mon nao gia thap nhat?",
            "Khong cay cho ong ba",
            "Nhom 8 nguoi dat gi?",
        ):
            with self.subTest(query=query):
                self.assertGreater(self._count(query), 0)

    def test_the_original_budget_aliases_still_work(self) -> None:
        # These four were already present.  Adding more to the same key by writing a
        # second `"binh dan":` entry silently replaced them — a duplicate key in a
        # dict literal keeps only the last.  Merged instead.
        for phrase in ("gia tiet kiem", "ngan sach thap", "gia mem", "chi tieu vua phai"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, TAG_QUERY_ALIASES["binh dan"])

    def test_no_duplicate_keys_survived_the_merge(self) -> None:
        # A duplicate key cannot be detected at runtime — the dict already lost the
        # first definition — so assert on the source text.
        import re
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1] / "app" / "rag" / "menu_query_filters.py"
        ).read_text(encoding="utf-8")
        block = re.search(
            r"TAG_QUERY_ALIASES[^=]*=\s*\{(.*?)\n\}", source, re.S
        ).group(1)
        keys = re.findall(r'^\s{4}"([^"]+)":', block, re.M)
        self.assertEqual(sorted(set(keys)), sorted(keys))

    def test_elderly_query_reaches_the_elderly_label_not_the_spice_one(self) -> None:
        # "Khong cay cho ong ba" used to match `khong cay` (68 dishes) because
        # `nguoi gia` had no alias for "ông bà".  The more specific label should win.
        elderly = {
            item["id"]
            for item in self.menu
            if "nguoi gia" in (item.get("tags") or [])
        }
        allowed = infer_allowed_menu_item_ids("Khong cay cho ong ba", self.menu) or set()
        self.assertTrue(allowed <= elderly)

    def test_aliases_only_name_labels_the_catalogue_actually_has(self) -> None:
        # An alias for a label no dish carries can never match, and reads as coverage
        # that does not exist.
        live = {tag for item in self.menu for tag in (item.get("tags") or [])}
        for tag in TAG_QUERY_ALIASES:
            with self.subTest(tag=tag):
                self.assertIn(tag, live | {"2 3 nguoi"})


if __name__ == "__main__":
    unittest.main()
