"""Integration-style tests for golden LLM eval runner (mock Gemini)."""

from __future__ import annotations

import asyncio
import json
import unittest

from evaluation.golden_eval_common import load_golden_cases
from evaluation.run_golden_llm_eval import evaluate_cases


class _MockGeminiClient:
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
    def test_evaluate_cases_with_mock_llm(self) -> None:
        cases = [case for case in load_golden_cases("dev", limit=5) if case.get("family") == "allergy"]
        self.assertTrue(cases)

        result = asyncio.run(
            evaluate_cases(
                cases[:1],
                retrieval_method="bm25",
                embedding_model="e5_small",
                with_judge=False,
                llm_client=_MockGeminiClient(),
            )
        )
        self.assertEqual(1, result["summary"]["evaluated_cases"])
        self.assertTrue(result["cases"][0]["llm_success"])
        self.assertTrue(result["cases"][0]["forbidden_pass"])


if __name__ == "__main__":
    unittest.main()
