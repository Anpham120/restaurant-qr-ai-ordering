from __future__ import annotations

import asyncio
import unittest

from evaluation.golden_eval_common import build_offline_service, load_menu_items
from evaluation.run_session_e2e_eval import (
    _run_extended_session,
    build_extended_session_cases,
)


class SessionEvalV2Tests(unittest.TestCase):
    def test_default_matrix_contains_50_sessions_of_12_to_20_turns(self) -> None:
        cases = build_extended_session_cases()

        self.assertEqual(50, len(cases))
        self.assertTrue(all(12 <= len(case["messages"]) <= 20 for case in cases))
        self.assertEqual(50, len({case["id"] for case in cases}))

    def test_extended_session_measures_typed_context_references_and_safety(self) -> None:
        menu_items = load_menu_items()
        service = build_offline_service("bm25", "e5_small")
        case = build_extended_session_cases(count=1)[0]

        result = asyncio.run(
            _run_extended_session(
                service,
                case,
                menu_items,
                use_llm=False,
            )
        )

        self.assertEqual(12, result["turns_run"])
        self.assertGreater(result["context_checks"]["denominator"], 0)
        self.assertEqual(
            result["context_checks"]["denominator"],
            result["context_checks"]["numerator"],
        )
        self.assertGreater(result["referent_checks"]["denominator"], 0)
        self.assertEqual(0, result["duplicate_recommendation_count"])
        self.assertEqual(0, result["invalid_action_count"])
        self.assertTrue(result["allergy_fail_closed"])
        self.assertLessEqual(result["max_history_turns_sent"], 12)
        self.assertTrue(result["final_state"]["rejected_menu_item_ids"])


if __name__ == "__main__":
    unittest.main()
