"""Tests for FAQ-aware confidence gate."""

from __future__ import annotations

import unittest

from app.rag.confidence import compute_retrieval_confidence
from app.rag.retriever import RetrievedChunk


class ConfidenceFaqIntentTests(unittest.TestCase):
    def test_faq_intent_low_confidence_skips_llm(self) -> None:
        result = compute_retrieval_confidence([], intent="payment")
        self.assertFalse(result.should_call_llm)

    def test_menu_intent_very_low_still_calls_llm(self) -> None:
        results = [{"score": 0.005, "source": "menu.md"}]
        result = compute_retrieval_confidence(results, intent="party_size_planning")
        self.assertTrue(result.should_call_llm)


if __name__ == "__main__":
    unittest.main()
