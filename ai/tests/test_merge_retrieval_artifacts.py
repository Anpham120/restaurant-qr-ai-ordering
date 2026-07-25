from __future__ import annotations

import unittest
from unittest.mock import patch

from evaluation.merge_retrieval_artifacts import merge_artifact_payloads


def _payload(method: str, *, corpus_hash: str = "corpus", repetitions: int = 1) -> dict:
    return {
        "split": "dev",
        "top_k": 10,
        "encoder_registry": {"e5_small": {"model_name": "example"}},
        "methods": {
            method: {
                "method": method,
                "corpus": {"corpus_sha256": corpus_hash},
                "dataset": {
                    "family_source_sha256": "families",
                    "materialized_cases_sha256": "cases",
                },
                "latency_ms": {
                    "protocol": {"repetitions_per_query": repetitions}
                },
                "cases": [],
            }
        },
    }


class MergeRetrievalArtifactsTests(unittest.TestCase):
    @patch(
        "evaluation.merge_retrieval_artifacts.compare_retrieval_results",
        return_value={"comparison_count": 1},
    )
    def test_merges_isolated_methods_and_recomputes_pairwise_statistics(
        self,
        compare,
    ) -> None:
        merged = merge_artifact_payloads(
            [
                ("bm25.json", _payload("bm25")),
                ("dense_e5_small.json", _payload("dense_e5_small")),
            ],
            expected_methods=("bm25", "dense_e5_small"),
        )

        self.assertEqual({"bm25", "dense_e5_small"}, set(merged["methods"]))
        self.assertEqual(1, merged["screening_protocol"]["latency_repetitions"])
        self.assertEqual("isolated-single-method", merged["screening_protocol"]["execution"])
        self.assertEqual({"comparison_count": 1}, merged["pairwise_statistics"])
        compare.assert_called_once()

    def test_rejects_corpus_or_latency_protocol_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "corpus"):
            merge_artifact_payloads(
                [
                    ("bm25.json", _payload("bm25")),
                    (
                        "dense_e5_small.json",
                        _payload("dense_e5_small", corpus_hash="different"),
                    ),
                ],
                expected_methods=("bm25", "dense_e5_small"),
            )

        with self.assertRaisesRegex(ValueError, "latency repetitions"):
            merge_artifact_payloads(
                [
                    ("bm25.json", _payload("bm25")),
                    (
                        "dense_e5_small.json",
                        _payload("dense_e5_small", repetitions=3),
                    ),
                ],
                expected_methods=("bm25", "dense_e5_small"),
            )


if __name__ == "__main__":
    unittest.main()
