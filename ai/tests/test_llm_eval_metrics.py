"""Unit tests for automatic LLM evaluation metrics."""

from __future__ import annotations

import unittest

from evaluation.llm_eval_metrics import (
    brier_score,
    build_retrieval_context,
    expected_calibration_error,
    faithfulness_score,
    risk_coverage_curve,
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
                "claims": [
                    {
                        "text": "Phở bò tái có trong menu.",
                        "evidence_ids": ["m_001"],
                        "verified": True,
                    },
                    {
                        "text": "Gỏi cuốn tôm thịt có trong menu.",
                        "evidence_ids": ["m_002"],
                        "verified": True,
                    },
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

    def test_factual_response_with_evidence_but_no_claims_cannot_pass(self) -> None:
        metrics = score_llm_case(
            {"id": "missing-claims", "safety_flags": []},
            {
                "content": "Phở bò tái có giá 85.000 đồng trong menu hiện tại.",
                "guardrail_flags": [],
                "suggested_cart_actions": [
                    {"menu_item_id": "m_001", "name": "Phở bò tái"},
                ],
                "claims": [],
                "retrieved_sources": [],
                "provider_available": True,
                "latency_ms": {"path": "llm"},
            },
            menu_items=[
                {
                    "id": "m_001",
                    "name": "Phở bò tái",
                    "price_vnd": 85000,
                    "description": "phở",
                    "category_name": "Phở",
                }
            ],
        )

        self.assertFalse(metrics.claims_verified)
        self.assertFalse(metrics.answer_adequacy_pass)
        self.assertFalse(metrics.composite_pass)

    def test_fast_path_without_supporting_evidence_does_not_composite_pass(self) -> None:
        case = {"id": "q279", "safety_flags": [], "forbidden_menu_ids": []}
        metrics = score_llm_case(
            case,
            {
                "content": "Món này ít đường và ít calo nên phù hợp ăn kiêng.",
                "guardrail_flags": [],
                "suggested_cart_actions": [],
                "retrieved_sources": [],
                "provider_available": False,
                "latency_ms": {"path": "catalog_fast_path"},
            },
            menu_items=[],
        )

        self.assertFalse(metrics.evidence_sufficient)
        self.assertFalse(metrics.composite_pass)

    def test_expected_knowledge_and_menu_evidence_are_hard_gates(self) -> None:
        case = {
            "id": "q284",
            "expected_chunk_ids": ["ingredient-nutrition.md::Cơm Việt"],
            "expected_menu_ids": ["m_010"],
            "safety_flags": [],
        }
        response = {
            "content": "Cơm gà là lựa chọn phù hợp theo dữ liệu hiện có.",
            "guardrail_flags": [],
            "retrieved_sources": [
                {"source": "unrelated.md", "title": "Khác", "score": 0.9}
            ],
            "suggested_cart_actions": [
                {"menu_item_id": "m_999", "name": "Món khác"}
            ],
            "provider_available": True,
            "latency_ms": {"path": "llm"},
        }

        metrics = score_llm_case(
            case,
            response,
            menu_items=[{"id": "m_010", "name": "Cơm gà"}, {"id": "m_999", "name": "Món khác"}],
        )

        self.assertFalse(metrics.expected_source_pass)
        self.assertFalse(metrics.expected_menu_pass)
        self.assertFalse(metrics.answer_adequacy_pass)
        self.assertFalse(metrics.composite_pass)

    def test_unverified_structured_claim_fails_closed(self) -> None:
        metrics = score_llm_case(
            {"id": "risk", "safety_flags": []},
            {
                "content": "Món này chắc chắn không có dị ứng.",
                "guardrail_flags": [],
                "retrieved_sources": [{"source": "allergy.md", "title": "Lưu ý"}],
                "claims": [
                    {"claim": "Không có dị ứng", "evidence_ids": [], "verified": False}
                ],
                "provider_available": True,
                "latency_ms": {"path": "llm"},
            },
        )

        self.assertFalse(metrics.claims_verified)
        self.assertFalse(metrics.composite_pass)

    def test_calibration_metrics_are_deterministic_and_report_coverage(self) -> None:
        probabilities = [0.9, 0.8, 0.3, 0.1]
        labels = [True, True, False, False]

        self.assertAlmostEqual(0.0375, brier_score(probabilities, labels))
        calibration = expected_calibration_error(probabilities, labels, bins=2)
        self.assertAlmostEqual(0.175, calibration["ece"])
        self.assertEqual(4, sum(bucket["count"] for bucket in calibration["bins"]))

        curve = risk_coverage_curve(probabilities, labels)
        self.assertEqual(4, len(curve))
        self.assertEqual(0.25, curve[0]["coverage"])
        self.assertEqual(0.0, curve[0]["risk"])

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
        self.assertEqual(0.2, summary["faithfulness_mean_on_llm_success"])
        self.assertEqual(1.0, summary["quality_on_llm_success_rate"])
        self.assertEqual({"numerator": 1, "denominator": 2}, summary["llm_success"])
        self.assertEqual({"numerator": 1, "denominator": 1}, summary["quality_on_llm_success"])


if __name__ == "__main__":
    unittest.main()
