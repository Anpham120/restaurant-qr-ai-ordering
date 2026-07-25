from __future__ import annotations

import unittest

from evaluation.dual_model_comparison import compare_model_artifacts


def _artifact(
    model: str,
    cases: list[dict],
    *,
    retriever_runtime: dict | None = None,
    generation_config: dict | None = None,
) -> dict:
    return {
        "split": "dev",
        "llm": {
            "provider": "9router",
            "model": model,
            "generation_config": generation_config
            or {
                "max_tokens": 700,
                "reasoning_effort": "low",
                "llm_intent_classification_enabled": False,
            },
        },
        "retriever_runtime": retriever_runtime or {
            "requested_method": "hybrid",
            "effective_method": "hybrid",
            "embedding_model": "e5_small",
            "fallback_used": False,
        },
        "dataset": {"case_count": len(cases)},
        "cases": cases,
    }


class DualModelComparisonTests(unittest.TestCase):
    def test_separates_provider_availability_from_quality_on_success(self) -> None:
        gpt = _artifact(
            "cx/gpt-5.5",
            [
                {"id": "a", "llm_success": True, "composite_pass": True, "grounding_pass": True, "schema_valid": True, "faithfulness_score": 0.8, "latency_ms": {"total": 1000}},
                {"id": "b", "llm_success": False, "composite_pass": False, "grounding_pass": False, "schema_valid": False, "faithfulness_score": 0.0, "latency_ms": {"total": 500}},
            ],
        )
        deepseek = _artifact(
            "oc/deepseek-v4-flash-free",
            [
                {"id": "a", "llm_success": True, "composite_pass": False, "grounding_pass": False, "schema_valid": True, "faithfulness_score": 0.4, "latency_ms": {"total": 1500}},
                {"id": "b", "llm_success": True, "composite_pass": True, "grounding_pass": True, "schema_valid": True, "faithfulness_score": 0.7, "latency_ms": {"total": 2000}},
            ],
        )

        result = compare_model_artifacts({"gpt55": gpt, "deepseek": deepseek})

        rows = {row["profile"]: row for row in result["models"]}
        self.assertEqual({"numerator": 1, "denominator": 2, "rate": 0.5}, rows["gpt55"]["availability"])
        self.assertEqual({"numerator": 1, "denominator": 1, "rate": 1.0}, rows["gpt55"]["quality_on_success"])
        self.assertEqual({"numerator": 1, "denominator": 2, "rate": 0.5}, rows["deepseek"]["quality_on_success"])
        self.assertEqual("comparable", result["comparison_status"])
        self.assertEqual(2, result["paired"]["common_case_count"])

    def test_marks_different_case_sets_not_comparable(self) -> None:
        left = _artifact("cx/gpt-5.5", [{"id": "a", "llm_success": False}])
        right = _artifact("oc/deepseek-v4-flash-free", [{"id": "b", "llm_success": False}])

        result = compare_model_artifacts({"gpt55": left, "deepseek": right})

        self.assertEqual("not_comparable_case_sets", result["comparison_status"])

    def test_zero_success_model_is_availability_only_not_quality_comparable(self) -> None:
        gpt = _artifact(
            "cx/gpt-5.5",
            [
                {"id": "a", "llm_success": False, "composite_pass": False},
                {"id": "b", "llm_success": False, "composite_pass": False},
            ],
        )
        deepseek = _artifact(
            "oc/deepseek-v4-flash-free",
            [
                {"id": "a", "llm_success": True, "composite_pass": True},
                {"id": "b", "llm_success": True, "composite_pass": False},
            ],
        )

        result = compare_model_artifacts({"gpt55": gpt, "deepseek": deepseek})

        self.assertEqual("availability_only_no_shared_success", result["comparison_status"])
        self.assertEqual(2, result["paired"]["common_case_count"])
        self.assertEqual(0, result["paired"]["shared_llm_success_case_count"])
        self.assertEqual({"gpt55": 0, "deepseek": 2}, result["paired"]["availability_wins"])
        self.assertEqual({"gpt55": 0, "deepseek": 0}, result["paired"]["quality_wins"])
        self.assertEqual(0, result["paired"]["quality_ties"])

    def test_provider_availability_excludes_cases_that_did_not_call_llm(self) -> None:
        gpt = _artifact(
            "cx/gpt-5.5",
            [
                {"id": "a", "llm_called": True, "llm_success": True, "composite_pass": True},
                {"id": "b", "llm_called": True, "llm_success": False, "composite_pass": False},
                {"id": "c", "llm_called": False, "llm_success": False, "composite_pass": False},
            ],
        )
        deepseek = _artifact(
            "oc/deepseek-v4-flash-free",
            [
                {"id": "a", "llm_called": True, "llm_success": True, "composite_pass": True},
                {"id": "b", "llm_called": True, "llm_success": True, "composite_pass": True},
                {"id": "c", "llm_called": False, "llm_success": False, "composite_pass": False},
            ],
        )

        result = compare_model_artifacts({"gpt55": gpt, "deepseek": deepseek})
        rows = {row["profile"]: row for row in result["models"]}

        self.assertEqual({"numerator": 1, "denominator": 2, "rate": 0.5}, rows["gpt55"]["availability"])
        self.assertEqual({"numerator": 2, "denominator": 2, "rate": 1.0}, rows["deepseek"]["availability"])
        self.assertEqual({"numerator": 2, "denominator": 3, "rate": 2 / 3}, rows["gpt55"]["llm_call_rate"])

    def test_records_retriever_runtime_fallback_without_hiding_model_comparability(self) -> None:
        runtime = {
            "requested_method": "hybrid",
            "effective_method": "bm25-fallback",
            "embedding_model": "e5_small",
            "fallback_used": True,
            "fallback_error_type": "RuntimeError",
        }
        gpt = _artifact(
            "cx/gpt-5.5",
            [{"id": "a", "llm_success": True, "composite_pass": True}],
            retriever_runtime=runtime,
        )
        deepseek = _artifact(
            "oc/deepseek-v4-flash-free",
            [{"id": "a", "llm_success": True, "composite_pass": False}],
            retriever_runtime=runtime,
        )

        result = compare_model_artifacts({"gpt55": gpt, "deepseek": deepseek})

        self.assertEqual("comparable", result["comparison_status"])
        self.assertTrue(result["retriever_runtime"]["same_runtime"])
        self.assertTrue(result["retriever_runtime"]["fallback_present"])
        self.assertEqual("bm25-fallback", result["retriever_runtime"]["by_profile"]["gpt55"]["effective_method"])

    def test_proves_generation_input_parity_without_storing_prompts(self) -> None:
        shared_hash = "a" * 64
        gpt = _artifact(
            "cx/gpt-5.5",
            [
                {
                    "id": "a",
                    "llm_called": True,
                    "llm_success": True,
                    "generation_input_sha256": shared_hash,
                }
            ],
        )
        deepseek = _artifact(
            "oc/deepseek-v4-flash-free",
            [
                {
                    "id": "a",
                    "llm_called": True,
                    "llm_success": True,
                    "generation_input_sha256": shared_hash,
                }
            ],
        )

        result = compare_model_artifacts({"gpt55": gpt, "deepseek": deepseek})

        self.assertEqual(
            {
                "common_llm_called_pair_count": 1,
                "verifiable_pair_count": 1,
                "matching_pair_count": 1,
                "missing_pair_count": 0,
                "mismatching_pair_count": 0,
                "same_generation_config": True,
                "pass": True,
            },
            result["generation_input_parity"],
        )

    def test_generation_input_parity_fails_on_missing_or_different_hash(self) -> None:
        gpt = _artifact(
            "cx/gpt-5.5",
            [
                {"id": "a", "llm_called": True, "generation_input_sha256": "a" * 64},
                {"id": "b", "llm_called": True},
            ],
        )
        deepseek = _artifact(
            "oc/deepseek-v4-flash-free",
            [
                {"id": "a", "llm_called": True, "generation_input_sha256": "b" * 64},
                {"id": "b", "llm_called": True, "generation_input_sha256": "c" * 64},
            ],
        )

        result = compare_model_artifacts({"gpt55": gpt, "deepseek": deepseek})

        self.assertFalse(result["generation_input_parity"]["pass"])
        self.assertEqual(1, result["generation_input_parity"]["missing_pair_count"])
        self.assertEqual(1, result["generation_input_parity"]["mismatching_pair_count"])


if __name__ == "__main__":
    unittest.main()
