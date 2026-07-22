"""Tests for single-pass intent in query rewriting."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.rag.intent_classifier import IntentResult
from app.rag.query_rewriter import rewrite_query


class RewriteQueryIntentTests(unittest.TestCase):
    def test_reuses_provided_intent_without_second_classification(self) -> None:
        intent = IntentResult(
            intent="payment",
            confidence=0.9,
            source_hints=("payment-methods.md",),
            query_boost_terms=("thanh toán",),
        )
        with patch("app.rag.query_rewriter.classify_intent_with_history") as classify:
            rewritten = rewrite_query("Thanh toán thế nào?", [], intent=intent)
        classify.assert_not_called()
        self.assertIn("thanh toán", rewritten.lower())


if __name__ == "__main__":
    unittest.main()
