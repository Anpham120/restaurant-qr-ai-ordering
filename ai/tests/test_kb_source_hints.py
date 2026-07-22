"""Verify KB intent source hints reference real knowledge-base files."""
from __future__ import annotations

import unittest
from pathlib import Path

from app.rag.intent_classifier import INTENT_RULES
from app.rag.kb_info_fast_path import INTENT_PREFERRED_SOURCES


KB_DIR = Path(__file__).resolve().parents[1] / "knowledge-base"


class KbSourceHintsTests(unittest.TestCase):
    def test_intent_preferred_sources_exist(self) -> None:
        kb_files = {p.name for p in KB_DIR.glob("*.md")}
        missing: list[str] = []
        for intent, sources in INTENT_PREFERRED_SOURCES.items():
            for source in sources:
                if source not in kb_files:
                    missing.append(f"{intent}:{source}")
        self.assertEqual([], missing, f"Missing KB files in INTENT_PREFERRED_SOURCES: {missing}")

    def test_intent_classifier_sources_exist(self) -> None:
        kb_files = {p.name for p in KB_DIR.glob("*.md")}
        missing: list[str] = []
        for _name, _keywords, sources, _boost in INTENT_RULES:
            for source in sources:
                if source not in kb_files:
                    missing.append(f"{_name}:{source}")
        self.assertEqual([], missing, f"Missing KB files in INTENT_RULES: {missing}")

    def test_promotion_uses_seasonal_promotion_not_legacy_name(self) -> None:
        self.assertIn("seasonal-promotion.md", INTENT_PREFERRED_SOURCES["promotion"])
        self.assertNotIn("promotions.md", INTENT_PREFERRED_SOURCES["promotion"])


if __name__ == "__main__":
    unittest.main()
