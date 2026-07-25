"""Integration-style tests for golden LLM eval runner (mock 9router)."""

from __future__ import annotations

import asyncio
import json
import unittest

from evaluation.golden_eval_common import (
    DEFAULT_STRATIFIED_SAMPLING_SEED,
    load_golden_cases,
    summarize_case_sample,
)
from evaluation.run_golden_llm_eval import evaluate_cases


class _MockRouterClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str:
        return json.dumps(
            {
                "content": (
                    "Mình gợi ý Phở gà ta. Với dị ứng hải sản, bạn nên xác nhận với nhân viên trước khi đặt."
                ),
                "suggested_cart_actions": [
                    {
                        "menu_item_id": "m_009",
                        "name": "Phở gà ta",
                        "price_vnd": 65000,
                        "quantity": 1,
                        "reason": "Không chứa hải sản",
                        "requires_customer_confirmation": True,
                    }
                ],
                "guardrail_flags": ["ALLERGY_DISCLAIMER"],
            },
            ensure_ascii=False,
        )


class GoldenLlmEvalTests(unittest.TestCase):
    def test_head_sampling_remains_backward_compatible(self) -> None:
        cases = load_golden_cases("dev", limit=6)

        self.assertEqual(["q001", "q002", "q003", "q004", "q005", "q006"], [case["id"] for case in cases])

    def test_stratified_sampling_is_deterministic_and_covers_distinct_families(self) -> None:
        first = load_golden_cases(
            "dev",
            limit=12,
            sampling_strategy="stratified",
            sampling_seed=DEFAULT_STRATIFIED_SAMPLING_SEED,
        )
        second = load_golden_cases(
            "dev",
            limit=12,
            sampling_strategy="stratified",
            sampling_seed=DEFAULT_STRATIFIED_SAMPLING_SEED,
        )

        self.assertEqual([case["id"] for case in first], [case["id"] for case in second])
        self.assertEqual(12, len({case["family"] for case in first}))
        self.assertEqual(12, len({case["intent"] for case in first}))

    def test_sample_summary_records_distribution_and_case_hashes(self) -> None:
        cases = load_golden_cases(
            "dev",
            limit=12,
            sampling_strategy="stratified",
            sampling_seed=73,
        )

        summary = summarize_case_sample(
            cases,
            sampling_strategy="stratified",
            sampling_seed=73,
        )

        self.assertEqual("stratified", summary["strategy"])
        self.assertEqual(73, summary["seed"])
        self.assertEqual(12, sum(summary["family_distribution"].values()))
        self.assertEqual(12, len(summary["family_distribution"]))
        self.assertRegex(summary["case_set_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(summary["case_order_sha256"], r"^[0-9a-f]{64}$")

    def test_evaluate_cases_with_mock_llm(self) -> None:
        cases = [case for case in load_golden_cases("dev", limit=5) if case.get("family") == "allergy"]
        self.assertTrue(cases)

        result = asyncio.run(
            evaluate_cases(
                cases[:1],
                retrieval_method="bm25",
                embedding_model="e5_small",
                with_judge=False,
                llm_client=_MockRouterClient(),
            )
        )
        self.assertEqual(1, result["summary"]["evaluated_cases"])
        self.assertTrue(result["cases"][0]["llm_success"])
        self.assertTrue(result["cases"][0]["forbidden_pass"])
        self.assertEqual("bm25", result["retriever_runtime"]["requested_method"])
        self.assertEqual("bm25", result["retriever_runtime"]["effective_method"])
        self.assertFalse(result["retriever_runtime"]["fallback_used"])
        self.assertRegex(result["cases"][0]["generation_input_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            {
                "max_tokens": result["llm"]["generation_config"]["max_tokens"],
                "reasoning_effort": result["llm"]["generation_config"]["reasoning_effort"],
                "llm_intent_classification_enabled": result["llm"]["generation_config"][
                    "llm_intent_classification_enabled"
                ],
            },
            result["llm"]["generation_config"],
        )


if __name__ == "__main__":
    unittest.main()
