from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.research_corpus import load_research_corpus
from evaluation.research_dataset import DatasetValidationError


class ResearchCorpusTests(unittest.TestCase):
    def test_v38_rejects_non_object_menu_items(self) -> None:
        with self.assertRaisesRegex(DatasetValidationError, "must be an object"):
            self._load_menu(["invalid"])

    def test_v38_rejects_invalid_price_and_availability(self) -> None:
        item = self._valid_item()
        item["price"] = -1
        item["isAvailable"] = "yes"

        with self.assertRaisesRegex(DatasetValidationError, "isAvailable"):
            self._load_menu([item])

    def test_v38_rejects_malformed_tags(self) -> None:
        item = self._valid_item()
        item["tags"] = ["healthy", 123]

        with self.assertRaisesRegex(DatasetValidationError, "tags"):
            self._load_menu([item])

    def _load_menu(self, items: list[object]) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            menu_path = root / "menu.json"
            knowledge_path = root / "knowledge"
            knowledge_path.mkdir()
            menu_path.write_text(
                json.dumps({"items": items}, ensure_ascii=False),
                encoding="utf-8",
            )
            load_research_corpus(menu_path, knowledge_path)

    @staticmethod
    def _valid_item() -> dict[str, object]:
        return {
            "id": "m_test",
            "name": "Món thử",
            "categoryId": "cat_test",
            "categoryName": "Danh mục thử",
            "description": "Mô tả",
            "tags": ["healthy"],
            "isAvailable": True,
            "price": 10000,
        }


if __name__ == "__main__":
    unittest.main()
