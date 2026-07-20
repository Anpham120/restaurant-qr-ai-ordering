from __future__ import annotations

import contextlib
import io
import unittest

from evaluation.research_dataset import DatasetSplit
from evaluation.run_research_baseline import (
    _hash_framed_records,
    _percentile,
    main,
    run_baseline,
)


class ResearchBaselineTests(unittest.TestCase):
    def test_v38_dev_baseline_is_reproducible_and_does_not_open_test(self) -> None:
        first = run_baseline(DatasetSplit.DEV, top_k=5)
        second = run_baseline(DatasetSplit.DEV, top_k=5)
        result = first

        self.assertEqual("bm25", result["method"])
        self.assertEqual("dev", result["split"])
        self.assertEqual(125, result["dataset"]["case_count"])
        self.assertEqual(296, result["corpus"]["document_count"])
        self.assertFalse(result["frozen_test_opened"])
        self.assertEqual(110, result["per_query_count"])
        self.assertEqual(110, result["latency_ms"]["samples"])
        self.assertEqual(
            7,
            result["latency_ms"]["protocol"]["repetitions_per_query"],
        )
        self.assertIn(5, result["metrics"]["by_k"])
        self.assertEqual(110, len(result["cases"]))
        self.assertIn("menu_source_sha256", result["corpus"])
        self.assertIn("knowledge_base_sha256", result["corpus"])

        for key in ("method", "split", "top_k", "dataset", "corpus", "metrics"):
            self.assertEqual(first[key], second[key])
        first_provenance = dict(first["provenance"])
        second_provenance = dict(second["provenance"])
        first_provenance.pop("generated_at_utc")
        second_provenance.pop("generated_at_utc")
        self.assertEqual(first_provenance, second_provenance)
        self.assertEqual(
            self._deterministic_cases(first["cases"]),
            self._deterministic_cases(second["cases"]),
        )

    def test_v38_python_api_refuses_frozen_test_without_opt_in(self) -> None:
        with self.assertRaises(PermissionError):
            run_baseline(DatasetSplit.TEST, top_k=5)

    def test_v38_cli_refuses_frozen_test_without_traceback(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            exit_code = main(["--split", "test"])

        self.assertEqual(2, exit_code)
        self.assertIn("Refusing to open frozen test split", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_v38_p95_uses_nearest_rank_definition(self) -> None:
        self.assertEqual(10, _percentile(list(range(1, 11)), 0.95))

    def test_v38_dirty_state_hash_uses_unambiguous_record_framing(self) -> None:
        self.assertNotEqual(
            _hash_framed_records([b"a", b"bc"]),
            _hash_framed_records([b"ab", b"c"]),
        )

    @staticmethod
    def _deterministic_cases(cases: list[dict[str, object]]) -> list[dict[str, object]]:
        output = []
        for case in cases:
            stable = dict(case)
            stable.pop("latency_ms")
            stable.pop("latency_samples_ms")
            output.append(stable)
        return output


if __name__ == "__main__":
    unittest.main()
