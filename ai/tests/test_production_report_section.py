from __future__ import annotations

import unittest

from scripts.notebook_metrics import format_production_report_section


class ProductionReportSectionTests(unittest.TestCase):
    def test_report_mentions_guardrails_session_and_partial_off_topic(self) -> None:
        text = format_production_report_section()
        self.assertIn("OUT_OF_SCOPE", text)
        self.assertIn("session_memory", text)
        self.assertIn("hybrid", text)
        self.assertNotIn("Notebook vs triển khai", text)


if __name__ == "__main__":
    unittest.main()
