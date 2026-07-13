from __future__ import annotations

import unittest

from evaluation.retrieval_metrics import evaluate_rankings, score_query


class RetrievalMetricsTests(unittest.TestCase):
    def test_v38_scores_binary_relevance_at_multiple_cutoffs(self) -> None:
        metrics = score_query(
            "case-1",
            ["irrelevant", "expected-a", "expected-b"],
            ["expected-a", "expected-b"],
            k_values=(1, 3),
        )

        self.assertEqual(0.0, metrics.by_k[1].reciprocal_rank)
        self.assertEqual(0.5, metrics.by_k[3].reciprocal_rank)
        self.assertEqual(0.0, metrics.by_k[1].hit)
        self.assertEqual(1.0, metrics.by_k[3].hit)
        self.assertAlmostEqual(2 / 3, metrics.by_k[3].precision)
        self.assertEqual(1.0, metrics.by_k[3].recall)
        self.assertGreater(metrics.by_k[3].ndcg, 0.0)

    def test_v38_reports_forbidden_documents(self) -> None:
        metrics = score_query(
            "case-2",
            ["allowed", "forbidden"],
            ["allowed"],
            ["forbidden"],
        )
        self.assertEqual((), metrics.by_k[1].forbidden_hits)
        self.assertEqual(("forbidden",), metrics.by_k[3].forbidden_hits)

    def test_v38_forbidden_hit_rate_respects_each_cutoff(self) -> None:
        summary, _ = evaluate_rankings(
            rankings={"case": ["allowed", "forbidden"]},
            expected_by_case={"case": ["allowed"]},
            forbidden_by_case={"case": ["forbidden"]},
            k_values=(1, 3),
        )

        self.assertEqual(0.0, summary.by_k[1].forbidden_hit_rate)
        self.assertEqual(1.0, summary.by_k[3].forbidden_hit_rate)

    def test_v38_summarizes_only_cases_with_relevance_labels(self) -> None:
        summary, rows = evaluate_rankings(
            rankings={
                "case-1": ["a", "b"],
                "case-2": ["x"],
            },
            expected_by_case={
                "case-1": ["a"],
                "case-2": [],
            },
            k_values=(1, 3),
        )
        self.assertEqual(1, summary.evaluated_cases)
        self.assertEqual(1, len(rows))
        self.assertEqual(1.0, summary.by_k[1].mrr)
        self.assertEqual(1.0, summary.by_k[1].hit_rate)

    def test_v38_mrr_does_not_count_hits_past_cutoff(self) -> None:
        metrics = score_query(
            "case-3",
            ["x1", "x2", "x3", "x4", "x5", "expected"],
            ["expected"],
            k_values=(5, 10),
        )
        self.assertEqual(0.0, metrics.by_k[5].reciprocal_rank)
        self.assertAlmostEqual(1 / 6, metrics.by_k[10].reciprocal_rank)


if __name__ == "__main__":
    unittest.main()
