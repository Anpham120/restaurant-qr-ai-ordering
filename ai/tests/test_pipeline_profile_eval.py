from __future__ import annotations

import unittest

from evaluation.run_pipeline_profile_eval import (
    DEEPSEEK_MODEL,
    aggregate_profile,
    build_selection_artifact,
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
                        "strict_semantic_success": 0.99,
                        "context_accuracy": 0.99,
                        "p95_latency_ms": 10,
                        "mean_llm_calls": 1,
                    },
                }
            ],
            commit_sha="abc123",
            dataset_hash="sha256:dataset",
            generated_at="2026-07-25T00:00:00Z",
        )

        self.assertEqual(DEEPSEEK_MODEL, artifact["model"])
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


if __name__ == "__main__":
    unittest.main()
