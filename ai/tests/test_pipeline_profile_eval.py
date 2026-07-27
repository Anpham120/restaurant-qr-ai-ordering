from __future__ import annotations

import unittest

from app.config import AiServiceConfig
from evaluation.run_pipeline_profile_eval import (
    DEEPSEEK_MODEL,
    aggregate_profile,
    build_selection_artifact,
    create_eval_router_client,
    required_runs,
    score_case,
)


class PipelineProfileEvalTests(unittest.TestCase):
    def test_deterministic_case_runs_once_and_llm_case_runs_three_times(self) -> None:
        self.assertEqual(1, required_runs(0))
        self.assertEqual(3, required_runs(1))
        self.assertEqual(3, required_runs(2))

    def test_score_case_requires_verified_expected_menu_evidence(self) -> None:
        case = {
            "id": "pho-list",
            "expected_menu_ids": ["m_008", "m_009"],
            "match": "all",
        }
        response = {
            "content": "Có phở bò và phở gà.",
            "claims": [
                {
                    "text": "Có phở bò và phở gà.",
                    "evidence_ids": ["m_008", "m_009"],
                    "verified": True,
                }
            ],
            "evidence": [
                {"source": "live_menu", "menu_item_id": "m_008"},
                {"source": "live_menu", "menu_item_id": "m_009"},
            ],
            "resolved_menu_item_ids": ["m_008", "m_009"],
            "suggested_cart_actions": [],
        }

        score = score_case(case, response, allowed_menu_ids={"m_008", "m_009"})

        self.assertTrue(score["strict_semantic_success"])
        self.assertEqual(0, score["unsupported_claims"])
        self.assertTrue(score["allowed_evidence_only"])

    def test_score_case_rejects_forged_id_and_unverified_claim(self) -> None:
        case = {"id": "forged", "forbidden_menu_ids": ["m_fake"]}
        response = {
            "content": "Món giả có giá 1 đồng.",
            "claims": [
                {
                    "text": "Món giả có giá 1 đồng.",
                    "evidence_ids": ["m_fake"],
                    "verified": False,
                }
            ],
            "evidence": [{"source": "live_menu", "menu_item_id": "m_fake"}],
            "resolved_menu_item_ids": ["m_fake"],
            "suggested_cart_actions": [{"menu_item_id": "m_fake"}],
        }

        score = score_case(case, response, allowed_menu_ids={"m_008"})

        self.assertFalse(score["strict_semantic_success"])
        self.assertEqual(1, score["unsupported_claims"])
        self.assertFalse(score["allowed_evidence_only"])
        self.assertFalse(score["id_price_passed"])

    def test_artifact_records_provenance_and_refuses_unsafe_winner(self) -> None:
        artifact = build_selection_artifact(
            profile_results=[
                {
                    "profile": "llm_first_v1",
                    "metrics": {
                        "unsupported_claims": 1,
                        "safety_passed": False,
                        "allergy_passed": True,
                        "session_isolation_passed": True,
                        "allowed_evidence_only": True,
                        "assistant_text_not_persisted": True,
                        "provider_calls_succeeded": True,
                        "strict_semantic_success": 0.99,
                        "context_accuracy": 0.99,
                        "p95_latency_ms": 10,
                        "mean_llm_calls": 1,
                    },
                }
            ],
            commit_sha="abc123",
            research_input_hash="sha256:research",
            dataset_hash="sha256:dataset",
            generated_at="2026-07-25T00:00:00Z",
        )

        self.assertEqual(DEEPSEEK_MODEL, artifact["model"])
        self.assertEqual("pipeline-selection-v3", artifact["schema_version"])
        self.assertEqual("abc123", artifact["research_commit_sha"])
        self.assertEqual("sha256:research", artifact["research_input_hash"])
        self.assertEqual(
            {
                "primary_model": "oc/deepseek-v4-flash-free",
                "fallback_model": "cx/gpt-5.6-luna-review",
                "fallback_enabled": True,
                "fallback_trigger": "http_429",
                "max_fallbacks_per_operation": 1,
            },
            artifact["model_policy"],
        )
        self.assertEqual("abc123", artifact["commit_sha"])
        self.assertIsNone(artifact["winner"])
        self.assertEqual(
            "no_candidate_passed_safety_gate",
            artifact["selection_reason"],
        )

    def test_profile_fails_gate_when_real_deepseek_calls_never_succeed(self) -> None:
        score = {
            "id": "provider-check",
            "strict_semantic_success": False,
            "safety_success": True,
            "observed_menu_ids": [],
            "unsupported_claims": 0,
            "allowed_evidence_only": True,
            "allergy_passed": True,
            "id_price_passed": True,
            "assistant_text_not_persisted": True,
        }
        candidate = aggregate_profile(
            "llm_first_v1",
            [
                {
                    "case_id": "provider-check",
                    "category": "safety",
                    "score": score,
                    "llm_calls": 1,
                    "successful_llm_calls": 0,
                    "latency_ms": 10,
                }
            ],
            session_isolation_passed=True,
            availability_passed=True,
        )

        self.assertFalse(candidate["metrics"]["deepseek_calls_succeeded"])
        self.assertFalse(candidate["metrics"]["provider_calls_succeeded"])

        successful_candidate = aggregate_profile(
            "llm_first_v1",
            [
                {
                    "case_id": "provider-check",
                    "category": "safety",
                    "score": score,
                    "llm_calls": 2,
                    "successful_llm_calls": 1,
                    "latency_ms": 10,
                }
            ],
            session_isolation_passed=True,
            availability_passed=True,
        )
        self.assertTrue(
            successful_candidate["metrics"]["deepseek_calls_succeeded"]
        )
        self.assertEqual(
            0.5,
            successful_candidate["metrics"]["deepseek_call_success_rate"],
        )
        self.assertTrue(successful_candidate["metrics"]["provider_calls_succeeded"])

    def test_profile_aggregates_primary_and_fallback_attempts_separately(self) -> None:
        score = {
            "id": "fallback-check",
            "strict_semantic_success": True,
            "safety_success": True,
            "observed_menu_ids": ["m_001"],
            "unsupported_claims": 0,
            "allowed_evidence_only": True,
            "allergy_passed": True,
            "id_price_passed": True,
            "assistant_text_not_persisted": True,
        }
        candidate = aggregate_profile(
            "evidence_first_v2",
            [
                {
                    "case_id": "fallback-check",
                    "category": "safety",
                    "score": score,
                    "llm_calls": 1,
                    "successful_llm_calls": 1,
                    "latency_ms": 10,
                    "model_attempts": [
                        {
                            "model": "oc/deepseek-v4-flash-free",
                            "role": "primary",
                            "outcome": "http_429",
                            "status_code": 429,
                            "latency_ms": 1.0,
                        },
                        {
                            "model": "cx/gpt-5.6-luna-review",
                            "role": "rate_limit_fallback",
                            "outcome": "success",
                            "status_code": 200,
                            "latency_ms": 9.0,
                        },
                    ],
                }
            ],
            session_isolation_passed=True,
            availability_passed=True,
        )

        usage = candidate["metrics"]["model_usage"]
        self.assertEqual(
            {
                "oc/deepseek-v4-flash-free": 1,
                "cx/gpt-5.6-luna-review": 1,
            },
            usage["attempts_by_model"],
        )
        self.assertEqual(
            {"cx/gpt-5.6-luna-review": 1},
            usage["successes_by_model"],
        )
        self.assertEqual(
            {"oc/deepseek-v4-flash-free": 1},
            usage["failures_by_model"],
        )
        self.assertEqual(1, usage["fallback_count"])
        self.assertEqual(1.0, usage["fallback_rate"])
        self.assertTrue(candidate["metrics"]["provider_calls_succeeded"])

    def test_eval_router_client_enforces_deepseek_luna_429_policy(self) -> None:
        config = AiServiceConfig(
            provider="9router",
            base_url="http://localhost:20128/v1",
            api_key="test-key",
            model="oc/deepseek-v4-flash-free",
            llm_timeout_seconds=12.0,
            request_budget_seconds=22.0,
            max_retry=0,
            max_tokens=700,
            reasoning_effort="low",
            knowledge_base_path=__file__,
            top_k=5,
            rate_limit_fallback_model="cx/gpt-5.6-luna-review",
            rate_limit_fallback_enabled=True,
        )

        client = create_eval_router_client(config)

        self.assertEqual("oc/deepseek-v4-flash-free", client._model)
        self.assertEqual("cx/gpt-5.6-luna-review", client._fallback_model)
        self.assertTrue(client._fallback_enabled)


if __name__ == "__main__":
    unittest.main()
