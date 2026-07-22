"""Tests for FAQ-aware confidence gate."""

from __future__ import annotations

import unittest

from app.rag.confidence import compute_retrieval_confidence
from app.rag.retriever import RetrievedChunk


class ConfidenceFaqIntentTests(unittest.TestCase):
    def test_faq_intent_low_confidence_skips_llm(self) -> None:
        chunk = type("Chunk", (), {"source": "faq.md", "title": "WiFi", "content": "wifi"})()
        results = [RetrievedChunk(chunk, 0.02)]
        result = compute_retrieval_confidence(results, intent="payment")
        self.assertFalse(result.should_call_llm)

    def test_menu_intent_very_low_still_calls_llm(self) -> None:
        results = [{"score": 0.005, "source": "menu.md"}]
        result = compute_retrieval_confidence(results, intent="party_size_planning")
        self.assertTrue(result.should_call_llm)


if __name__ == "__main__":
    unittest.main()
