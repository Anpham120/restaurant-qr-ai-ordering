"""Tests for retrieval confidence scoring — specifically RRF normalization."""
from __future__ import annotations

import unittest

from app.rag.confidence import (
    HIGH_CONFIDENCE,
    LOW_CONFIDENCE,
    MEDIUM_CONFIDENCE,
    ConfidenceResult,
    compute_retrieval_confidence,
)


class TestConfidenceResultFromScore(unittest.TestCase):
    """Unit tests for ConfidenceResult.from_score thresholds."""

    def test_high_confidence(self):
        result = ConfidenceResult.from_score(0.8, "test")
        self.assertEqual(result.level, "high")
        self.assertTrue(result.should_call_llm)
        self.assertIsNone(result.guardrail_flag)

    def test_medium_confidence(self):
        result = ConfidenceResult.from_score(0.5, "test")
        self.assertEqual(result.level, "medium")
        self.assertTrue(result.should_call_llm)
        self.assertEqual(result.guardrail_flag, "LOW_RETRIEVAL_CONFIDENCE")

    def test_low_confidence(self):
        result = ConfidenceResult.from_score(0.15, "test")
        self.assertEqual(result.level, "low")
        self.assertTrue(result.should_call_llm)
        self.assertEqual(result.guardrail_flag, "LOW_RETRIEVAL_CONFIDENCE")

    def test_very_low_confidence(self):
        result = ConfidenceResult.from_score(0.05, "test")
        self.assertEqual(result.level, "very_low")
        self.assertFalse(result.should_call_llm)
        self.assertEqual(result.guardrail_flag, "RETRIEVAL_FAILED")


class TestRRFScoreNormalization(unittest.TestCase):
    """Verify RRF scores (0.01-0.05) are normalized properly, not treated as near-zero."""

    def test_rrf_typical_score_not_very_low(self):
        """RRF score 0.03 should NOT result in very_low confidence."""
        results = [
            {"score": 0.033, "source": "faq.md"},
            {"score": 0.032, "source": "restaurant-info.md"},
            {"score": 0.030, "source": "service-guide.md"},
        ]
        conf = compute_retrieval_confidence(results)
        self.assertNotEqual(
            conf.level,
            "very_low",
            f"RRF 0.033 should not be very_low, got score={conf.score:.3f} level={conf.level}",
        )
        self.assertTrue(conf.should_call_llm)

    def test_rrf_strong_score_medium_or_higher(self):
        """RRF score 0.05 (max typical) should yield medium or high confidence."""
        results = [
            {"score": 0.050, "source": "faq.md"},
            {"score": 0.020, "source": "menu.md"},
            {"score": 0.010, "source": "allergy-dietary.md"},
        ]
        conf = compute_retrieval_confidence(results)
        self.assertIn(
            conf.level,
            ("medium", "high"),
            f"RRF 0.050 should be medium+, got score={conf.score:.3f} level={conf.level}",
        )

    def test_rrf_very_weak_is_low(self):
        """RRF score 0.005 (barely any match) should be low or very_low."""
        results = [{"score": 0.005, "source": "faq.md"}]
        conf = compute_retrieval_confidence(results)
        self.assertIn(
            conf.level,
            ("low", "very_low"),
            f"RRF 0.005 should be low/very_low, got score={conf.score:.3f} level={conf.level}",
        )

    def test_bm25_high_score_normalized(self):
        """BM25 score 8.0 should be normalized to ~0.8 weight."""
        results = [
            {"score": 8.0, "source": "faq.md"},
            {"score": 5.0, "source": "menu.md"},
            {"score": 3.0, "source": "service-guide.md"},
        ]
        conf = compute_retrieval_confidence(results)
        self.assertIn(
            conf.level,
            ("medium", "high"),
            f"BM25 8.0 should be medium+, got score={conf.score:.3f} level={conf.level}",
        )

    def test_dense_cosine_passthrough(self):
        """Dense cosine 0.85 should pass through directly."""
        results = [
            {"score": 0.85, "source": "faq.md"},
            {"score": 0.60, "source": "menu.md"},
            {"score": 0.40, "source": "ordering-policy.md"},
        ]
        conf = compute_retrieval_confidence(results)
        self.assertIn(
            conf.level,
            ("medium", "high"),
            f"Dense 0.85 should be medium+, got score={conf.score:.3f} level={conf.level}",
        )


class TestEmptyResults(unittest.TestCase):
    """Edge cases with no results."""

    def test_no_results(self):
        conf = compute_retrieval_confidence([])
        self.assertEqual(conf.score, 0.0)
        self.assertEqual(conf.level, "very_low")
        self.assertFalse(conf.should_call_llm)

    def test_single_result(self):
        results = [{"score": 0.04, "source": "faq.md"}]
        conf = compute_retrieval_confidence(results)
        self.assertTrue(conf.should_call_llm)


if __name__ == "__main__":
    unittest.main()
