import csv
import hashlib
import json
import unittest
from collections import defaultdict
from pathlib import Path


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
            hashlib.sha256((AI_ROOT / "research" / "queries.csv").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            environment["menu_snapshot_sha256"],
            hashlib.sha256((AI_ROOT / "research" / "menu_snapshot.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            environment["policy_sha256"],
            hashlib.sha256((AI_ROOT / "data" / "policies.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(summary["winner"], production["method"])
        self.assertIn(production["method"], summary["methods"])
        self.assertGreater(summary["methods"][production["method"]]["test"]["hit_at_5"], 0.9)

        best_quality = max(
            payload["test"]["macro_slice_ndcg_at_10"] for payload in summary["methods"].values()
        )
        finalists = {
            method
            for method, payload in summary["methods"].items()
            if best_quality - payload["test"]["macro_slice_ndcg_at_10"] <= 0.005
        }
        expected_winner = min(
            finalists,
            key=lambda method: summary["methods"][method]["test"]["latency_p95_ms"],
        )
        self.assertEqual(expected_winner, production["method"])


if __name__ == "__main__":
    unittest.main()
