from __future__ import annotations

import unittest

from evaluation.intent_eval_common import keyword_route
from scripts.run_paraphrase_probe import PROBES


class RoutingParaphraseGeneralizationTests(unittest.TestCase):
    def test_paraphrase_probes_generalize_beyond_eval_catalog(self) -> None:
        failures: list[str] = []
        for probe in PROBES:
            pred = keyword_route(probe["message"], probe["history"])
            ok_wants = pred["wants_recommendations"] == probe["wants"]
            ok_party = pred["party_size"] == probe["party"]
            if not (ok_wants and ok_party):
                failures.append(
                    f"{probe['id']}: {probe['message']} -> {pred}, "
                    f"expected wants={probe['wants']} party={probe['party']}"
                )
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
