"""Unit tests for automatic LLM evaluation metrics."""

from __future__ import annotations

import unittest

from evaluation.llm_eval_metrics import (
    build_retrieval_context,
    faithfulness_score,
    score_llm_case,
    summarize_llm_metrics,
)


class LlmEvalMetricsTests(unittest.TestCase):
    def test_faithfulness_rewards_overlap_with_retrieved_context(self) -> None:
        response = {
            "retrieved_sources": [
                {"source": "allergy-dietary.md", "title": "Dị Ứng Hải Sản"},
            ],
            "suggested_cart_actions": [{"menu_item_id": "m_009", "name": "Phở gà ta"}],
        }
        context = build_retrieval_context(
            response,
            kb_chunks=[],
            menu_items=[{"id": "m_009", "name": "Phở gà ta", "description": "nhe hon pho bo"}],
        )
        high = faithfulness_score("Phở gà ta phù hợp nếu bạn tránh hải sản.", context)
        low = faithfulness_score("Bitcoin hôm nay tăng mạnh.", context)
        self.assertGreater(high, low)

    def test_allergy_case_requires_disclaimer_language(self) -> None:
        case = {
            "id": "q001",
            "safety_flags": ["ALLERGY_DISCLAIMER"],
            "forbidden_menu_ids": [],
        }
        good = score_llm_case(
            case,
            {
                "content": "Bạn nên xác nhận với nhân viên về dị ứng trước khi đặt.",
                "guardrail_flags": ["ALLERGY_DISCLAIMER"],
                "suggested_cart_actions": [],
                "retrieved_sources": [],
                "provider_available": True,
            },
            menu_items=[],
        )
        bad = score_llm_case(
            case,
            {
                "content": "Mình gợi ý phở gà và cơm sườn.",
                "guardrail_flags": [],
                "suggested_cart_actions": [],
                "retrieved_sources": [],
                "provider_available": True,
            },
            menu_items=[],
        )
        self.assertTrue(good.allergy_disclaimer_pass)
        self.assertFalse(bad.allergy_disclaimer_pass)

    def test_fast_path_with_menu_actions_passes_without_llm_provider(self) -> None:
        case = {"id": "q040", "safety_flags": [], "forbidden_menu_ids": []}
        metrics = score_llm_case(
            case,
            {
                "content": "Với nhóm 4 người mình gợi ý phở bò tái và gỏi cuốn tôm thịt.",
                "guardrail_flags": ["CUSTOMER_CONFIRMATION_REQUIRED"],
                "suggested_cart_actions": [
                    {"menu_item_id": "m_001", "name": "Phở bò tái"},
                    {"menu_item_id": "m_002", "name": "Gỏi cuốn tôm thịt"},
                ],
                "retrieved_sources": [],
                "provider_available": False,
                "latency_ms": {"path": "party_fast_path"},
            },
            menu_items=[
                {"id": "m_001", "name": "Phở bò tái", "description": "phở", "category_name": "Phở"},
                {"id": "m_002", "name": "Gỏi cuốn tôm thịt", "description": "gỏi", "category_name": "Khai vị"},
            ],
        )
        self.assertTrue(metrics.composite_pass)

    def test_summarize_llm_metrics(self) -> None:
        summary = summarize_llm_metrics(
            [
                {"llm_success": True, "schema_valid": True, "grounding_pass": True, "composite_pass": True,
                 "faithfulness_score": 0.2, "safety_pass": True, "forbidden_pass": True,
                 "expected_source_hit": True, "expected_menu_hit": None,
                 "allergy_disclaimer_pass": None, "price_refusal_pass": None},
                {"llm_success": False, "schema_valid": False, "grounding_pass": False, "composite_pass": False,
                 "faithfulness_score": 0.05, "safety_pass": False, "forbidden_pass": True,
                 "expected_source_hit": False, "expected_menu_hit": True,
                 "allergy_disclaimer_pass": True, "price_refusal_pass": True},
            ]
        )
        self.assertEqual(2, summary["evaluated_cases"])
        self.assertEqual(0.5, summary["llm_success_rate"])
        self.assertEqual(0.5, summary["composite_pass_rate"])


if __name__ == "__main__":
    unittest.main()
