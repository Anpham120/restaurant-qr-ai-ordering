from __future__ import annotations

import unittest

from evaluation.statistical_tests import (
    holm_bonferroni,
    mcnemar_exact,
    paired_bootstrap,
    wilcoxon_signed_rank,
)


class StatisticalTests(unittest.TestCase):
    def test_v38_bootstrap_is_deterministic_and_detects_positive_delta(self) -> None:
        result = paired_bootstrap(
            [0.9, 0.8, 0.7, 0.9, 0.8, 0.9, 0.7, 0.8],
            [0.5, 0.4, 0.3, 0.5, 0.4, 0.5, 0.3, 0.4],
            iterations=500,
            seed=7,
        )
        self.assertGreater(result.mean_delta, 0)
        self.assertGreater(result.ci_lower, 0)
        self.assertLess(result.p_value, 0.05)

    def test_v38_bootstrap_p_value_uses_null_sign_permutation(self) -> None:
        result = paired_bootstrap(
            [0.8, 0.4, 0.8, 0.4],
            [0.4, 0.8, 0.4, 0.8],
            iterations=500,
            seed=11,
        )

        self.assertAlmostEqual(0.0, result.mean_delta)
        self.assertEqual(1.0, result.p_value)

    def test_v38_mcnemar_uses_only_discordant_pairs(self) -> None:
        result = mcnemar_exact(
            [True, True, True, False, True],
            [False, False, True, False, False],
        )
        self.assertEqual(3, result.method_a_only)
        self.assertEqual(0, result.method_b_only)
        self.assertGreater(result.success_rate_delta, 0)
        self.assertGreaterEqual(result.ci_upper, result.ci_lower)
        self.assertAlmostEqual(0.25, result.p_value)

    def test_v38_wilcoxon_reports_identical_pairs_as_no_difference(self) -> None:
        result = wilcoxon_signed_rank([1.0, 2.0], [1.0, 2.0])
        self.assertEqual(0, result.non_zero_pairs)
        self.assertEqual(0.0, result.rank_biserial)
        self.assertEqual(0.0, result.median_delta)
        self.assertEqual(1.0, result.p_value)

    def test_v38_wilcoxon_reports_effect_size_and_interval(self) -> None:
        result = wilcoxon_signed_rank(
            [5.0, 6.0, 7.0, 8.0],
            [1.0, 2.0, 3.0, 4.0],
        )

        self.assertEqual(1.0, result.rank_biserial)
        self.assertEqual(4.0, result.median_delta)
        self.assertEqual(4.0, result.ci_lower)
        self.assertEqual(4.0, result.ci_upper)

    def test_v38_holm_adjustment_is_monotonic(self) -> None:
        adjusted = holm_bonferroni({"a": 0.01, "b": 0.04, "c": 0.03})
        self.assertEqual(0.03, adjusted["a"])
        self.assertEqual(0.06, adjusted["c"])
        self.assertEqual(0.06, adjusted["b"])


if __name__ == "__main__":
    unittest.main()
