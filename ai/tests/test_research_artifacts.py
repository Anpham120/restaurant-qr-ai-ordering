import csv
import json
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from research.run_experiments import _select_winner, _sha256


AI_ROOT = Path(__file__).resolve().parents[1]


class ResearchArtifactTests(unittest.TestCase):
    def test_locked_dataset_and_production_decision_are_consistent(self):
        with (AI_ROOT / "research" / "queries.csv").open(encoding="utf-8") as handle:
            cases = list(csv.DictReader(handle))
        summary = json.loads((AI_ROOT / "research" / "artifacts" / "summary.json").read_text(encoding="utf-8"))
        production = json.loads(
            (AI_ROOT / "research" / "artifacts" / "production_config.json").read_text(encoding="utf-8")
        )

        self.assertEqual(235, len(cases))
        splits_by_group = defaultdict(set)
        for case in cases:
            splits_by_group[case["group_id"]].add(case["split"])
        self.assertTrue(all(len(splits) == 1 for splits in splits_by_group.values()))
        environment = json.loads(
            (AI_ROOT / "research" / "artifacts" / "environment.json").read_text(encoding="utf-8")
        )
        menu_snapshot = json.loads(
            (AI_ROOT / "research" / "menu_snapshot.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            "backend/src/RestaurantQrAiOrdering.Api/Data/RestaurantMenuSeed.cs",
            menu_snapshot["source"],
        )
        self.assertEqual(environment["case_counts"]["test"], sum(case["split"] == "test" for case in cases))
        self.assertEqual(
            environment["queries_sha256"],
            _sha256(AI_ROOT / "research" / "queries.csv"),
        )
        self.assertEqual(
            environment["menu_snapshot_sha256"],
            _sha256(AI_ROOT / "research" / "menu_snapshot.json"),
        )
        self.assertEqual(
            environment["policy_sha256"],
            _sha256(AI_ROOT / "data" / "policies.json"),
        )
        self.assertEqual(summary["winner"], production["method"])
        self.assertIn(production["method"], summary["methods"])
        self.assertGreater(summary["methods"][production["method"]]["test"]["hit_at_5"], 0.9)

        self.assertEqual("dev", summary["selection_split"])
        self.assertIn("development", production["selection_rule"].lower())
        self.assertIn("frozen test", production["selection_rule"].lower())

        best_quality = max(
            payload["dev"]["macro_slice_ndcg_at_10"] for payload in summary["methods"].values()
        )
        finalists = {
            method
            for method, payload in summary["methods"].items()
            if best_quality - payload["dev"]["macro_slice_ndcg_at_10"] <= 0.005
        }
        expected_winner = min(
            finalists,
            key=lambda method: summary["methods"][method]["dev"]["latency_p95_ms"],
        )
        self.assertEqual(expected_winner, production["method"])

    def test_production_selection_uses_dev_not_frozen_test(self):
        summaries = {
            "dev_winner": {
                "dev": {"macro_slice_ndcg_at_10": 0.91, "latency_p95_ms": 9.0},
                "test": {"macro_slice_ndcg_at_10": 0.40, "latency_p95_ms": 9.0},
            },
            "test_winner": {
                "dev": {"macro_slice_ndcg_at_10": 0.70, "latency_p95_ms": 1.0},
                "test": {"macro_slice_ndcg_at_10": 0.99, "latency_p95_ms": 1.0},
            },
        }

        self.assertEqual("dev_winner", _select_winner(summaries))

    def test_provenance_hash_is_line_ending_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf = root / "lf.txt"
            crlf = root / "crlf.txt"
            lf.write_bytes(b"alpha\nbeta\n")
            crlf.write_bytes(b"alpha\r\nbeta\r\n")

            self.assertEqual(_sha256(lf), _sha256(crlf))


if __name__ == "__main__":
    unittest.main()
