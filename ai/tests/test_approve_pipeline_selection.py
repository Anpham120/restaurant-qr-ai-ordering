from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.approve_pipeline_selection import build_approved_artifact


def _raw_artifact() -> dict:
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
        "profiles": [
            {
                "profile": "evidence_first_v2",
                "metrics": {
                    "strict_semantic_success": 0.91,
                    "context_accuracy": 0.86,
                    "p95_latency_ms": 22838.62,
                    "mean_llm_calls": 1.58,
                    "unsupported_claims": 0,
                    "allowed_evidence_only": True,
                    "allergy_passed": True,
                    "session_isolation_passed": True,
                    "assistant_text_not_persisted": True,
                    "provider_calls_succeeded": True,
                    "safety_passed": True,
                },
            }
        ],
        "winner": "evidence_first_v2",
        "selection_reason": "safety_gate_then_strict_quality_then_context_then_p95_latency_then_llm_calls",
        "rejected_by_safety": [],
        "commit_sha": "543e4f9d4ca2abf5ca9b081c0f59aeaf4e20f540",
        "research_input_hash": "sha256:research",
        "working_tree_dirty": False,
        "dataset_hash": "sha256:data",
        "generated_at": "2026-07-26T12:00:00+00:00",
    }


class ApprovePipelineSelectionTests(unittest.TestCase):
    def test_adds_approval_provenance_to_clean_raw_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="approve-pipeline-selection-") as temp_dir:
            raw_path = Path(temp_dir) / "pipeline_selection.json"
            raw_path.write_text(
                json.dumps(_raw_artifact(), ensure_ascii=False),
                encoding="utf-8",
            )

            approved = build_approved_artifact(
                _raw_artifact(),
                source_artifact_path=raw_path,
                source_run_id=30185742540,
                source_artifact_name="pipeline-selection-local-543e4f9",
                approved_at="2026-07-26T13:00:00+00:00",
            )

        self.assertEqual("pipeline-selection-v3", approved["schema_version"])
        self.assertEqual("543e4f9d4ca2abf5ca9b081c0f59aeaf4e20f540", approved["research_commit_sha"])
        self.assertEqual("2026-07-26T13:00:00+00:00", approved["approved_at"])
        self.assertEqual(30185742540, approved["source_run_id"])
        self.assertEqual("pipeline-selection-local-543e4f9", approved["source_artifact_name"])
        self.assertTrue(str(approved["source_artifact_sha256"]).startswith("sha256:"))
        self.assertNotIn("runs", approved["profiles"][0])

    def test_rejects_dirty_raw_artifact(self) -> None:
        raw = _raw_artifact()
        raw["working_tree_dirty"] = True
        with tempfile.TemporaryDirectory(prefix="approve-pipeline-selection-") as temp_dir:
            raw_path = Path(temp_dir) / "pipeline_selection.json"
            raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "clean source tree"):
                build_approved_artifact(
                    raw,
                    source_artifact_path=raw_path,
                    source_run_id=1,
                    source_artifact_name="dirty",
                )


if __name__ == "__main__":
    unittest.main()
