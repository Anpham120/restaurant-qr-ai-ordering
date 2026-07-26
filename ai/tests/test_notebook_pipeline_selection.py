from __future__ import annotations

import unittest

from scripts.notebook_metrics import (
    format_pipeline_selection_conclusion,
    summarize_pipeline_selection,
)


class NotebookPipelineSelectionTests(unittest.TestCase):
    def test_summary_uses_artifact_winner_without_hardcoding(self) -> None:
        artifact = {
            "winner": "evidence_first_v2",
            "selection_reason": "safety_then_quality",
            "model": "oc/deepseek-v4-flash-free",
            "model_policy": {
                "primary_model": "oc/deepseek-v4-flash-free",
                "fallback_model": "cx/gpt-5.6-luna-review",
                "fallback_enabled": True,
                "fallback_trigger": "http_429",
                "max_fallbacks_per_operation": 1,
            },
            "research_commit_sha": "abc123",
            "research_input_hash": "sha256:research",
            "dataset_hash": "sha256:data",
            "profiles": [
                {
                    "profile": "evidence_first_v2",
                    "metrics": {
                        "strict_semantic_success": 0.9,
                        "context_accuracy": 0.8,
                        "p95_latency_ms": 120,
                        "mean_llm_calls": 0.4,
                        "safety_passed": True,
                        "model_usage": {
                            "fallback_rate": 0.25,
                            "attempts_by_model": {
                                "oc/deepseek-v4-flash-free": 3,
                                "cx/gpt-5.6-luna-review": 1,
                            },
                            "successes_by_model": {
                                "oc/deepseek-v4-flash-free": 2,
                                "cx/gpt-5.6-luna-review": 1,
                            },
                            "failures_by_model": {
                                "oc/deepseek-v4-flash-free": 1,
                            },
                        },
                    },
                }
            ],
        }

        summary = summarize_pipeline_selection(artifact)
        narrative = format_pipeline_selection_conclusion(artifact)

        self.assertEqual("evidence_first_v2", summary["winner"])
        self.assertEqual(0.9, summary["rows"][0]["strict_semantic_success"])
        self.assertEqual(
            "cx/gpt-5.6-luna-review",
            summary["model_policy"]["fallback_model"],
        )
        self.assertEqual(0.25, summary["rows"][0]["fallback_rate"])
        self.assertIn("evidence_first_v2", narrative)
        self.assertIn("abc123", narrative)
        self.assertIn("sha256:research", narrative)
        self.assertIn("cx/gpt-5.6-luna-review", narrative)
        self.assertIn("http_429", narrative)

    def test_no_winner_is_reported_as_deploy_blocked(self) -> None:
        narrative = format_pipeline_selection_conclusion(
            {"winner": None, "selection_reason": "no_candidate_passed_safety_gate"}
        )
        self.assertIn("BLOCKED", narrative)
        self.assertIn("hard gate", narrative)


if __name__ == "__main__":
    unittest.main()
