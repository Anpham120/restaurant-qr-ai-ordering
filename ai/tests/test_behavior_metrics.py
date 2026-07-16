from __future__ import annotations

import unittest

from evaluation.behavior_metrics import (
    score_behavior_case,
    summarize_behavior_metrics,
)


class BehaviorMetricsTests(unittest.TestCase):
    def test_v38_out_of_catalog_guardrail_contributes_to_metrics(self) -> None:
        row = score_behavior_case(
            "out-of-catalog-01",
            ["OUT_OF_CATALOG_TAG"],
            ["OUT_OF_CATALOG_TAG"],
        )
        summary = summarize_behavior_metrics([row])
        self.assertEqual(1.0, summary.exact_flag_match_rate)
        self.assertEqual(1.0, summary.macro_flag_f1)

    def test_v38_forbidden_suggestion_is_counted(self) -> None:
        row = score_behavior_case(
            "allergy-01",
            ["ALLERGEN_CONFIRMATION_REQUIRED"],
            ["ALLERGEN_CONFIRMATION_REQUIRED"],
            ["menu:safe", "menu:unsafe"],
            ["menu:unsafe"],
        )
        summary = summarize_behavior_metrics([row])
        self.assertEqual(("menu:unsafe",), row.forbidden_suggestions)
        self.assertEqual(1.0, summary.forbidden_suggestion_rate)

    def test_v38_true_negative_does_not_inflate_macro_flag_f1(self) -> None:
        positive_miss = score_behavior_case("positive", ["REQUIRED"], [])
        true_negative = score_behavior_case("negative", [], [])

        summary = summarize_behavior_metrics([positive_miss, true_negative])

        self.assertEqual(2, summary.evaluated_cases)
        self.assertEqual(1, summary.flag_evaluated_cases)
        self.assertEqual(0.0, summary.macro_flag_f1)
        self.assertEqual(0.5, summary.exact_flag_match_rate)


if __name__ == "__main__":
    unittest.main()
