from __future__ import annotations

import unittest

from evaluation.pipeline_selection import select_winner


def _candidate(
    profile: str,
    *,
    strict: float,
    context: float,
    p95: float,
    calls: float,
    unsupported_claims: int = 0,
    safety_passed: bool = True,
    provider_calls_succeeded: bool = True,
) -> dict:
    return {
        "profile": profile,
        "metrics": {
            "strict_semantic_success": strict,
            "context_accuracy": context,
            "p95_latency_ms": p95,
            "mean_llm_calls": calls,
            "unsupported_claims": unsupported_claims,
            "safety_passed": safety_passed,
            "allergy_passed": safety_passed,
            "session_isolation_passed": safety_passed,
            "allowed_evidence_only": safety_passed,
            "assistant_text_not_persisted": safety_passed,
            "provider_calls_succeeded": provider_calls_succeeded,
        },
    }


class PipelineSelectionTests(unittest.TestCase):
    def test_safety_gate_excludes_higher_quality_candidate(self) -> None:
        unsafe = _candidate(
            "planner_state_v3",
            strict=1.0,
            context=1.0,
            p95=400,
            calls=1.0,
            unsupported_claims=1,
        )
        safe = _candidate(
            "evidence_first_v2",
            strict=0.95,
            context=0.9,
            p95=500,
            calls=0.8,
        )

        result = select_winner([unsafe, safe])

        self.assertEqual("evidence_first_v2", result["winner"])
        self.assertEqual(["planner_state_v3"], result["rejected_by_safety"])

    def test_quality_difference_of_one_point_or_more_wins_before_context(self) -> None:
        higher_quality = _candidate(
            "evidence_first_v2",
            strict=0.96,
            context=0.80,
            p95=600,
            calls=0.8,
        )
        higher_context = _candidate(
            "planner_state_v3",
            strict=0.95,
            context=1.0,
            p95=400,
            calls=1.5,
        )

        result = select_winner([higher_context, higher_quality])

        self.assertEqual("evidence_first_v2", result["winner"])

    def test_context_breaks_quality_tie_below_one_percentage_point(self) -> None:
        faster = _candidate(
            "evidence_first_v2",
            strict=0.955,
            context=0.88,
            p95=300,
            calls=0.7,
        )
        better_context = _candidate(
            "planner_state_v3",
            strict=0.95,
            context=0.96,
            p95=700,
            calls=1.4,
        )

        result = select_winner([faster, better_context])

        self.assertEqual("planner_state_v3", result["winner"])

    def test_latency_then_llm_calls_break_remaining_ties(self) -> None:
        slower = _candidate(
            "planner_state_v3",
            strict=0.95,
            context=0.95,
            p95=700,
            calls=1.0,
        )
        faster = _candidate(
            "evidence_first_v2",
            strict=0.95,
            context=0.95,
            p95=400,
            calls=1.2,
        )

        result = select_winner([slower, faster])

        self.assertEqual("evidence_first_v2", result["winner"])

    def test_no_candidate_passing_safety_returns_no_winner(self) -> None:
        result = select_winner(
            [
                _candidate(
                    "llm_first_v1",
                    strict=1.0,
                    context=1.0,
                    p95=200,
                    calls=1.0,
                    safety_passed=False,
                )
            ]
        )

        self.assertIsNone(result["winner"])
        self.assertEqual(["llm_first_v1"], result["rejected_by_safety"])

    def test_provider_success_is_a_hard_gate_even_with_fallback_policy(self) -> None:
        result = select_winner(
            [
                _candidate(
                    "planner_state_v3",
                    strict=0.99,
                    context=1.0,
                    p95=200,
                    calls=2.0,
                    provider_calls_succeeded=False,
                )
            ]
        )

        self.assertIsNone(result["winner"])
        self.assertEqual(["planner_state_v3"], result["rejected_by_safety"])


if __name__ == "__main__":
    unittest.main()
