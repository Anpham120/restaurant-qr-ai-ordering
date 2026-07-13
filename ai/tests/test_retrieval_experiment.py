from __future__ import annotations

import unittest
from collections.abc import Sequence
from unittest.mock import patch

from evaluation.research_dataset import DatasetSplit
from evaluation.run_retrieval_experiment import (
    RetrievalMethod,
    run_comparison,
    run_method,
)


class DeterministicFakeEncoder:
    model_name = "fake-e5"
    model_revision = "fake-revision"
    dimension = 3

    def encode_documents(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [
            (1.0, float((len(text) % 7) + 1), float((index % 5) + 1))
            for index, text in enumerate(texts)
        ]

    def encode_queries(self, texts: Sequence[str]) -> list[tuple[float, ...]]:
        return [(1.0, float((len(text) % 7) + 1), 1.0) for text in texts]


class RetrievalExperimentTests(unittest.TestCase):
    def test_dense_method_uses_same_dev_dataset_and_records_model_provenance(self) -> None:
        result = run_method(
            RetrievalMethod.DENSE_E5,
            top_k=5,
            encoder=DeterministicFakeEncoder(),
        )

        self.assertEqual("dense_e5", result["method"])
        self.assertEqual("dev", result["split"])
        self.assertEqual(110, result["per_query_count"])
        retriever = result["provenance"]["retriever"]
        self.assertEqual("fake-e5", retriever["parameters"]["model_name"])
        self.assertEqual("fake-revision", retriever["parameters"]["model_revision"])

    def test_hybrid_method_records_both_retrieval_components(self) -> None:
        result = run_method(
            RetrievalMethod.HYBRID_RRF,
            top_k=5,
            encoder=DeterministicFakeEncoder(),
        )

        retriever = result["provenance"]["retriever"]
        self.assertEqual("hybrid_rrf", result["method"])
        self.assertIn("lexical", retriever["parameters"])
        self.assertIn("dense", retriever["parameters"])

    def test_comparison_preserves_method_names(self) -> None:
        result = run_comparison(
            [RetrievalMethod.BM25, RetrievalMethod.DENSE_E5],
            top_k=3,
            encoder=DeterministicFakeEncoder(),
        )

        self.assertEqual({"bm25", "dense_e5"}, set(result["methods"]))
        comparison = result["pairwise_statistics"]
        self.assertEqual(1, comparison["comparison_count"])
        self.assertIn("dense_e5_vs_bm25", comparison["comparisons"])
        self.assertEqual(5, comparison["adjusted_test_count"])
        self.assertEqual(
            "within each test family across method pairs",
            comparison["correction_scope"],
        )

    def test_comparison_uses_largest_evaluated_cutoff(self) -> None:
        result = run_comparison(
            [RetrievalMethod.BM25, RetrievalMethod.DENSE_E5],
            top_k=2,
            encoder=DeterministicFakeEncoder(),
        )

        self.assertEqual(1, result["pairwise_statistics"]["cutoff"])

    def test_single_method_comparison_keeps_statistics_schema(self) -> None:
        result = run_comparison([RetrievalMethod.BM25], top_k=3)
        comparison = result["pairwise_statistics"]

        self.assertEqual(0, comparison["comparison_count"])
        self.assertEqual(0, comparison["adjusted_test_count"])
        self.assertEqual({}, comparison["comparisons"])
        self.assertEqual(
            "within each test family across method pairs",
            comparison["correction_scope"],
        )

    def test_frozen_test_guard_applies_to_every_method(self) -> None:
        with patch(
            "evaluation.run_retrieval_experiment.SentenceTransformerE5Encoder"
        ) as encoder_constructor:
            with self.assertRaises(PermissionError):
                run_method(RetrievalMethod.DENSE_E5, DatasetSplit.TEST)

        encoder_constructor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
