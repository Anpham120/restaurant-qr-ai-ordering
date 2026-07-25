from __future__ import annotations

import unittest

from evaluation.export_llm_error_analysis import classify_failure


class LlmErrorTaxonomyTests(unittest.TestCase):
    def test_failure_taxonomy_uses_specific_pipeline_causes(self) -> None:
        cases = {
            "retrieval_miss": {"expected_source_hit": False, "expected_chunk_hit": False},
            "wrong_route": {"route_expected": "live", "route_actual": "rag"},
            "unresolved_reference": {"abstain_reason": "unresolved_reference"},
            "insufficient_evidence": {"evidence_sufficient": False},
            "unsupported_claim": {"claims_verified": False},
            "stale_data": {"guardrail_flags": ["STALE_DATA"]},
            "provider_schema_failure": {"llm_success": False, "schema_valid": False},
        }
        for expected, row in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(expected, classify_failure(row))


if __name__ == "__main__":
    unittest.main()
