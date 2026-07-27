from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from evaluation.verify_pipeline_selection import validate_artifact


def _artifact() -> dict:
    return {
        "schema_version": "pipeline-selection-v3",
        "model": "oc/deepseek-v4-flash-free",
        "model_policy": {
            "primary_model": "oc/deepseek-v4-flash-free",
            "fallback_model": "cx/gpt-5.6-luna-review",
            "fallback_enabled": True,
            "fallback_trigger": "http_429",
            "max_fallbacks_per_operation": 1,
        },
        "winner": "evidence_first_v2",
        "research_commit_sha": "abc123",
        "research_input_hash": "sha256:research",
        "working_tree_dirty": False,
        "dataset_hash": "sha256:data",
        "generated_at": "2026-07-25T00:00:00Z",
        "source_run_id": 123,
        "source_artifact_sha256": "sha256:source",
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
                    "provider_calls_succeeded": True,
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
            expected_primary_model="oc/deepseek-v4-flash-free",
            expected_fallback_model="cx/gpt-5.6-luna-review",
            expected_fallback_trigger="http_429",
            expected_max_fallbacks=1,
            require_fallback_enabled=True,
            expected_research_input_hash="sha256:research",
        )
        self.assertEqual("evidence_first_v2", winner)

    def test_accepts_different_deployment_commit_when_research_inputs_match(self) -> None:
        artifact = _artifact()
        artifact["deployment_commit_sha"] = "different-runtime-commit"

        winner = validate_artifact(
            artifact,
            expected_profile="evidence_first_v2",
            expected_primary_model="oc/deepseek-v4-flash-free",
            expected_fallback_model="cx/gpt-5.6-luna-review",
            expected_fallback_trigger="http_429",
            expected_max_fallbacks=1,
            require_fallback_enabled=True,
            expected_research_input_hash="sha256:research",
        )

        self.assertEqual("evidence_first_v2", winner)

    def test_rejects_research_input_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "research input drift"):
            validate_artifact(
                _artifact(),
                expected_profile="evidence_first_v2",
                expected_primary_model="oc/deepseek-v4-flash-free",
                expected_fallback_model="cx/gpt-5.6-luna-review",
                expected_fallback_trigger="http_429",
                expected_max_fallbacks=1,
                require_fallback_enabled=True,
                expected_research_input_hash="sha256:changed",
            )

    def test_rejects_canonical_dataset_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "dataset drift"):
            validate_artifact(
                _artifact(),
                expected_profile="evidence_first_v2",
                expected_primary_model="oc/deepseek-v4-flash-free",
                expected_fallback_model="cx/gpt-5.6-luna-review",
                expected_fallback_trigger="http_429",
                expected_max_fallbacks=1,
                require_fallback_enabled=True,
                expected_dataset_hash="sha256:canonical-data",
            )

    def test_rejects_profile_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "profile"):
            validate_artifact(
                _artifact(),
                expected_profile="planner_state_v3",
                expected_primary_model="oc/deepseek-v4-flash-free",
                expected_fallback_model="cx/gpt-5.6-luna-review",
                expected_fallback_trigger="http_429",
                expected_max_fallbacks=1,
                require_fallback_enabled=True,
            )

    def test_rejects_winner_that_fails_hard_gate(self) -> None:
        artifact = _artifact()
        artifact["profiles"][0]["metrics"]["allergy_passed"] = False
        with self.assertRaisesRegex(ValueError, "safety"):
            validate_artifact(
                artifact,
                expected_primary_model="oc/deepseek-v4-flash-free",
                expected_fallback_model="cx/gpt-5.6-luna-review",
                expected_fallback_trigger="http_429",
                expected_max_fallbacks=1,
                require_fallback_enabled=True,
            )

    def test_rejects_dirty_source_for_deployment(self) -> None:
        artifact = _artifact()
        artifact["working_tree_dirty"] = True
        with self.assertRaisesRegex(ValueError, "dirty"):
            validate_artifact(
                artifact,
                expected_primary_model="oc/deepseek-v4-flash-free",
                expected_fallback_model="cx/gpt-5.6-luna-review",
                expected_fallback_trigger="http_429",
                expected_max_fallbacks=1,
                require_fallback_enabled=True,
            )

    def test_rejects_fallback_policy_drift(self) -> None:
        artifact = _artifact()
        artifact["model_policy"]["fallback_model"] = "cx/gpt-5.5"
        with self.assertRaisesRegex(ValueError, "fallback model drift"):
            validate_artifact(
                artifact,
                expected_primary_model="oc/deepseek-v4-flash-free",
                expected_fallback_model="cx/gpt-5.6-luna-review",
                expected_fallback_trigger="http_429",
                expected_max_fallbacks=1,
                require_fallback_enabled=True,
            )

    def test_cli_exports_primary_and_fallback_env(self) -> None:
        artifact = _artifact()
        with tempfile.TemporaryDirectory(prefix="verify-pipeline-env-") as temp_dir:
            artifact_path = Path(temp_dir) / "pipeline_selection.json"
            env_path = Path(temp_dir) / "github.env"
            artifact_path.write_text(
                json.dumps(artifact, ensure_ascii=False),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "python",
                    "evaluation/verify_pipeline_selection.py",
                    str(artifact_path),
                    "--expected-primary-model",
                    "oc/deepseek-v4-flash-free",
                    "--expected-fallback-model",
                    "cx/gpt-5.6-luna-review",
                    "--expected-fallback-trigger",
                    "http_429",
                    "--expected-max-fallbacks",
                    "1",
                    "--require-fallback-enabled",
                    "--github-env",
                    str(env_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
            )
            exported = env_path.read_text(encoding="utf-8")

        self.assertIn("AI_PIPELINE_PROFILE=evidence_first_v2", exported)
        self.assertIn("LLM_MODEL=oc/deepseek-v4-flash-free", exported)
        self.assertIn(
            "LLM_RATE_LIMIT_FALLBACK_MODEL=cx/gpt-5.6-luna-review",
            exported,
        )
        self.assertIn("LLM_RATE_LIMIT_FALLBACK_ENABLED=true", exported)


if __name__ == "__main__":
    unittest.main()
