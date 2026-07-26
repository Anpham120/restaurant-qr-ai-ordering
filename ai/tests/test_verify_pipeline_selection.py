from __future__ import annotations

import unittest

from evaluation.verify_pipeline_selection import validate_artifact


def _artifact() -> dict:
    return {
        "schema_version": "pipeline-selection-v1",
        "model": "oc/deepseek-v4-flash-free",
        "winner": "evidence_first_v2",
        "commit_sha": "abc123",
        "working_tree_dirty": False,
        "dataset_hash": "sha256:data",
        "generated_at": "2026-07-25T00:00:00Z",
        "profiles": [
            {
                "profile": "evidence_first_v2",
                "metrics": {
                    "unsupported_claims": 0,
                    "safety_passed": True,
                    "allergy_passed": True,
                    "session_isolation_passed": True,
                    "allowed_evidence_only": True,
                    "assistant_text_not_persisted": True,
                    "deepseek_calls_succeeded": True,
                },
            }
        ],
    }


class VerifyPipelineSelectionTests(unittest.TestCase):
    def test_accepts_safe_winner_and_expected_runtime(self) -> None:
        winner = validate_artifact(
            _artifact(),
            expected_profile="evidence_first_v2",
            expected_model="oc/deepseek-v4-flash-free",
            expected_commit="abc123",
        )
        self.assertEqual("evidence_first_v2", winner)

    def test_rejects_profile_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "profile"):
            validate_artifact(
                _artifact(),
                expected_profile="planner_state_v3",
                expected_model="oc/deepseek-v4-flash-free",
            )

    def test_rejects_winner_that_fails_hard_gate(self) -> None:
        artifact = _artifact()
        artifact["profiles"][0]["metrics"]["allergy_passed"] = False
        with self.assertRaisesRegex(ValueError, "safety"):
            validate_artifact(
                artifact,
                expected_model="oc/deepseek-v4-flash-free",
            )

    def test_rejects_dirty_source_for_deployment(self) -> None:
        artifact = _artifact()
        artifact["working_tree_dirty"] = True
        with self.assertRaisesRegex(ValueError, "dirty"):
            validate_artifact(
                artifact,
                expected_model="oc/deepseek-v4-flash-free",
            )


if __name__ == "__main__":
    unittest.main()
