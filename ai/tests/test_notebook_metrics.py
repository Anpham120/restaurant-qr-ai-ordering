from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.notebook_metrics import (
    artifact_provenance,
    format_artifact_provenance_table,
    format_hit5_screening_vs_release_table,
    format_model_tier_strict_sentence,
    format_part12_narrative,
    format_part4_narrative,
    format_part17_bullet_part4,
    format_model_tier_sentence,
    is_non_abstain_success,
    is_strict_pipeline_success,
    load_retrieval_headlines,
    summarize_dual_model,
    summarize_live_pipeline,
    summarize_live_test,
    summarize_model_tiers,
)


MINI_DUAL = {
    "timestamp": "2026-01-01T00:00:00",
    "models": ["cx/gpt-5.5", "oc/deepseek-v4-flash-free"],
    "queries": [
        {"query": "wifi?", "category": "KB FAQ"},
        {"query": "combo?", "category": "Menu"},
    ],
    "results": {
        "cx/gpt-5.5": [
            {"route": "kb_rag", "latency_ms": 40.0},
            {"route": "abstain", "latency_ms": 100.0},
        ],
        "oc/deepseek-v4-flash-free": [
            {"route": "kb_rag", "latency_ms": 35.0},
            {"route": "llm_gen", "latency_ms": 200.0},
        ],
    },
}

TIER_DUAL = {
    "timestamp": "t",
    "models": ["cx/gpt-5.5", "cx/gpt-5.6-luna", "oc/deepseek-v4-flash-free"],
    "queries": [{"query": f"q{i}"} for i in range(20)],
    "results": {
        "cx/gpt-5.5": [{"route": "kb_rag"} for _ in range(20)],
        "cx/gpt-5.6-luna": [{"route": "kb_rag"} for _ in range(20)],
        "oc/deepseek-v4-flash-free": [
            *[{"route": "kb_rag"} for _ in range(16)],
            *[{"route": "abstain"} for _ in range(4)],
        ],
    },
}


class NotebookMetricsTests(unittest.TestCase):
    def test_is_non_abstain_success(self) -> None:
        self.assertTrue(is_non_abstain_success({"route": "kb_rag"}))
        self.assertFalse(is_non_abstain_success({"route": "abstain"}))
        self.assertFalse(is_non_abstain_success({"route": "kb_rag", "error": "x"}))

    def test_is_strict_pipeline_success(self) -> None:
        self.assertFalse(
            is_strict_pipeline_success(
                {
                    "route": None,
                    "flags": ["EVIDENCE_INSUFFICIENT"],
                    "content": "Mình chưa đủ bằng chứng",
                }
            )
        )
        self.assertTrue(
            is_strict_pipeline_success(
                {"route": "kb_rag", "content": "WiFi miễn phí", "flags": []}
            )
        )

    def test_summarize_dual_model_counts(self) -> None:
        summary = summarize_dual_model(MINI_DUAL)
        self.assertEqual(summary["total_q"], 2)
        gpt = summary["per_model"]["cx/gpt-5.5"]
        ds = summary["per_model"]["oc/deepseek-v4-flash-free"]
        self.assertEqual(gpt["ok"], 1)
        self.assertEqual(ds["ok"], 2)
        self.assertIn("strict_ok", gpt)
        self.assertEqual(summary["deepseek_only_wins"], ["combo?"])

    def test_model_tier_sentence(self) -> None:
        summary = summarize_dual_model(TIER_DUAL)
        text = format_model_tier_sentence(summary)
        self.assertIn("gpt-5.5", text)
        self.assertIn("gpt-5.6-luna", text)
        self.assertIn("16/20", text)
        tiers = summarize_model_tiers(TIER_DUAL)
        self.assertIn(20, tiers["tiers"])
        self.assertIn(16, tiers["tiers"])

    def test_summarize_live_pipeline(self) -> None:
        live = {
            "timestamp": "t",
            "model": "cx/gpt-5.5",
            "pipeline_results": [
                {"route": "kb_rag", "content": "ok"},
                {
                    "route": None,
                    "flags": ["EVIDENCE_INSUFFICIENT"],
                    "content": "Mình chưa đủ bằng chứng",
                },
            ],
        }
        pipe = summarize_live_pipeline(live)
        self.assertEqual(pipe["availability_ok"], 2)
        self.assertEqual(pipe["strict_ok"], 1)

    def test_summarize_live_test(self) -> None:
        live = {
            "timestamp": "t",
            "model": "cx/gpt-5.5",
            "pipeline_results": [
                {"route": "kb_rag"},
                {"route": "abstain"},
            ],
        }
        s = summarize_live_test(live)
        self.assertEqual(s["pipeline_ok"], 1)
        self.assertEqual(s["pipeline_total"], 2)

    def test_format_part4_narrative_lists_deepseek_win(self) -> None:
        summary = summarize_dual_model(MINI_DUAL)
        text = format_part4_narrative(summary)
        self.assertIn("DeepSeek thắng riêng", text)
        self.assertIn("combo?", text)
        self.assertNotIn("50%", text)

    def test_format_part4_tiers_not_single_leader(self) -> None:
        summary = summarize_dual_model(TIER_DUAL)
        text = format_part4_narrative(summary)
        self.assertIn("gpt-5.6-luna", text)
        self.assertIn("Strict success", text)
        self.assertNotIn("Model dẫn đầu availability", text)

    def test_format_model_tier_strict(self) -> None:
        summary = summarize_dual_model(TIER_DUAL)
        text = format_model_tier_strict_sentence(summary)
        self.assertIn("strict", text)
        self.assertIn("16/20", text)

    def test_artifact_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notebook_live_test.json"
            path.write_text('{"timestamp": "2026-01-01"}', encoding="utf-8")
            info = artifact_provenance(path)
            self.assertTrue(info["present"])
            self.assertEqual(info["timestamp"], "2026-01-01")
            self.assertEqual(len(info["sha256_prefix"]), 8)

    def test_format_hit5_table(self) -> None:
        text = format_hit5_screening_vs_release_table()
        self.assertIn("107", text)
        self.assertIn("110", text)
        self.assertIn("dev_retrieval_summary.v3.json", text)

    def test_format_artifact_provenance_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "evaluation" / "results"
            results.mkdir(parents=True)
            (results / "dual_model_test.json").write_text(
                '{"timestamp": "t"}', encoding="utf-8"
            )
            table = format_artifact_provenance_table(root)
            self.assertIn("dual_model_test.json", table)
            self.assertIn("missing", table.lower())

    def test_format_part12_narrative(self) -> None:
        live = {
            "timestamp": "t",
            "model": "cx/gpt-5.5",
            "pipeline_results": [{"route": "kb_rag", "content": "x"}],
        }
        text = format_part12_narrative(live, None)
        self.assertIn("Availability", text)
        self.assertIn("Strict success", text)

    def test_load_retrieval_headlines_screening(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = root / "evaluation" / "results"
            results.mkdir(parents=True)
            (results / "notebook_retrieval_screening.json").write_text(
                json.dumps({"hit5_overall": 0.87}),
                encoding="utf-8",
            )
            headlines = load_retrieval_headlines(root)
            self.assertEqual(headlines["screening_hit5"], 0.87)
            self.assertIn("87%", headlines["screening_label"])

    def test_format_part17_no_fixed_leader(self) -> None:
        summary = summarize_dual_model(MINI_DUAL)
        bullet = format_part17_bullet_part4(summary)
        self.assertIn("Part IV", bullet)
        self.assertIn("2/2", bullet)


if __name__ == "__main__":
    unittest.main()
