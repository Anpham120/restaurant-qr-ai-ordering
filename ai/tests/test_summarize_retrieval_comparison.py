from __future__ import annotations

import unittest

from evaluation.summarize_retrieval_comparison import summarize_comparison


class SummarizeRetrievalComparisonTests(unittest.TestCase):
    def test_preserves_screening_latency_scope_and_repetition_counts(self) -> None:
        method = {
            "per_query_count": 1,
            "corpus": {},
            "dataset": {},
            "metrics": {
                "by_k": {
                    str(k): {
                        "hit_rate": 1.0,
                        "mrr": 1.0,
                        "ndcg": 1.0,
                        "forbidden_hit_rate": 0.0,
                    }
                    for k in (1, 5, 10)
                }
            },
            "latency_ms": {
                "p50": 5.0,
                "p95": 7.0,
                "protocol": {"repetitions_per_query": 1},
            },
            "provenance": {
                "retriever": {
                    "parameters": {
                        "model_name": None,
                        "estimated_encoder_memory_mb": None,
                    }
                }
            },
        }
        comparison = {
            "split": "dev",
            "top_k": 10,
            "methods": {"bm25": method},
            "screening_protocol": {
                "execution": "isolated-single-method",
                "latency_repetitions": 1,
                "latency_claim_scope": "screening-only",
            },
            "experiment_profile": {
                "name": "all-research-encoders-isolated",
                "measured_methods": ["bm25"],
                "not_measured_methods": [],
            },
        }

        result = summarize_comparison(comparison)

        self.assertEqual("screening-only", result["screening_protocol"]["latency_claim_scope"])
        self.assertEqual(1, result["methods"]["bm25"]["latency_repetitions"])
        self.assertEqual(
            "all-research-encoders-isolated",
            result["experiment_profile"]["name"],
        )


if __name__ == "__main__":
    unittest.main()
