from __future__ import annotations

import unittest

from evaluation.intent_cases_catalog import build_intent_case_catalog, validate_cases
from evaluation.intent_eval_common import (
    load_intent_cases,
    predict_ambiguous,
    score_full,
    score_routing,
    score_solo_flag,
)


class IntentEvalScoringTests(unittest.TestCase):
    def test_score_routing_party_null_match(self) -> None:
        expected = {
            "expected_wants_recommendations": False,
            "expected_party_size": None,
            "expected_is_solo_dining": False,
        }
        pred = {
            "wants_recommendations": False,
            "party_size": None,
            "is_solo_dining": False,
        }
        self.assertTrue(score_routing(pred, expected))

    def test_score_routing_party_mismatch(self) -> None:
        expected = {
            "expected_wants_recommendations": True,
            "expected_party_size": 4,
            "expected_is_solo_dining": False,
        }
        pred = {
            "wants_recommendations": True,
            "party_size": 8,
            "is_solo_dining": False,
        }
        self.assertFalse(score_routing(pred, expected))

    def test_score_solo_flag(self) -> None:
        expected = {
            "expected_wants_recommendations": True,
            "expected_party_size": 1,
            "expected_is_solo_dining": True,
        }
        pred_ok = {
            "wants_recommendations": True,
            "party_size": 1,
            "is_solo_dining": True,
        }
        pred_bad = {
            "wants_recommendations": True,
            "party_size": 1,
            "is_solo_dining": False,
        }
        self.assertTrue(score_solo_flag(pred_ok, expected))
        self.assertFalse(score_solo_flag(pred_bad, expected))

    def test_score_full_requires_both(self) -> None:
        expected = {
            "expected_wants_recommendations": True,
            "expected_party_size": 1,
            "expected_is_solo_dining": True,
        }
        pred = {
            "wants_recommendations": True,
            "party_size": 1,
            "is_solo_dining": False,
        }
        self.assertTrue(score_routing(pred, expected))
        self.assertFalse(score_full(pred, expected))

    def test_catalog_validates(self) -> None:
        cases = build_intent_case_catalog()
        issues = validate_cases(cases)
        self.assertEqual([], issues)
        self.assertGreaterEqual(len(cases), 200)

    def test_materialized_cases_match_catalog_size(self) -> None:
        cases = load_intent_cases()
        catalog = build_intent_case_catalog()
        self.assertEqual(len(catalog), len(cases))

    def test_cases_file_has_broad_coverage(self) -> None:
        cases = load_intent_cases()
        categories = {case["category"] for case in cases}
        tiers = {case.get("tier", "core") for case in cases}
        for required in (
            "ambiguous_solo",
            "clear_info",
            "clear_party",
            "clear_recommend",
            "multi_turn_party",
            "word_party",
            "allergy_recommend",
            "group_social",
            "clear_category",
            "multi_turn_allergy",
            "noisy_input",
            "ambiguous_rejection",
        ):
            self.assertIn(required, categories)
        self.assertIn("multi_turn", tiers)

    def test_wifi_is_not_ambiguous(self) -> None:
        self.assertFalse(predict_ambiguous("wifi mat khau gi"))

    def test_solo_slang_is_not_ambiguous_after_deterministic_routing(self) -> None:
        self.assertFalse(predict_ambiguous("di an solo toi nay"))

    def test_holdout_split_is_objective(self) -> None:
        from evaluation.intent_eval_common import evaluate_keyword_with_holdout, split_eval_cases

        cases = load_intent_cases()
        dev, holdout = split_eval_cases(cases)
        self.assertGreater(len(dev), 0)
        self.assertGreater(len(holdout), 0)
        self.assertEqual(len(dev) + len(holdout), len(cases))

        metrics = evaluate_keyword_with_holdout(cases)
        holdout_routing = metrics["holdout_generated"]["routing_accuracy"]
        dev_routing = metrics["dev_handwritten"]["routing_accuracy"]
        self.assertGreaterEqual(holdout_routing, 0.95)
        self.assertGreaterEqual(dev_routing, 0.95)
        gap = dev_routing - holdout_routing
        self.assertLessEqual(gap, 0.05, "Large dev/holdout gap suggests eval overfitting")


if __name__ == "__main__":
    unittest.main()
