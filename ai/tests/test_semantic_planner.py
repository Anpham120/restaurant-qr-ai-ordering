from __future__ import annotations

import unittest

from app.rag.semantic_planner import (
    apply_semantic_plan,
    parse_semantic_plan,
)


class SemanticPlannerTests(unittest.TestCase):
    def test_parse_rejects_non_json_and_unknown_mode(self) -> None:
        self.assertIsNone(parse_semantic_plan("not-json"))
        self.assertIsNone(
            parse_semantic_plan(
                """
                {
                  "intent": "recommend",
                  "response_mode": "invent",
                  "category": null,
                  "tags": [],
                  "referent_ordinal": null,
                  "constraint_patch": {},
                  "remove_constraints": [],
                  "needs_clarification": false,
                  "clarification_slot": null,
                  "confidence": 0.9
                }
                """
            )
        )

    def test_apply_plan_resolves_second_prior_suggestion_and_increments_turn(self) -> None:
        plan = parse_semantic_plan(
            """
            {
              "intent": "ask_price",
              "response_mode": "factual",
              "category": null,
              "tags": [],
              "referent_ordinal": 2,
              "constraint_patch": {},
              "remove_constraints": [],
              "needs_clarification": false,
              "clarification_slot": null,
              "confidence": 0.97
            }
            """
        )
        assert plan is not None

        result = apply_semantic_plan(
            plan,
            session_state={
                "suggested_menu_item_ids": ["m_001", "m_002", "m_003"],
                "conversation_frame": {
                    "active_topic": "menu",
                    "focus_menu_item_ids": ["m_003"],
                    "turn_sequence": 4,
                },
            },
            constraints={"party_size": 2},
        )

        self.assertEqual(["m_002"], result.frame["focus_menu_item_ids"])
        self.assertEqual(5, result.frame["turn_sequence"])
        self.assertEqual("ask_price", result.frame["active_intent"])
        self.assertEqual({"party_size": 2}, result.constraints)

    def test_explicit_constraint_patch_overrides_and_remove_is_honored(self) -> None:
        plan = parse_semantic_plan(
            """
            {
              "intent": "recommend",
              "response_mode": "recommendation",
              "category": "pho bun",
              "tags": ["nhau"],
              "referent_ordinal": null,
              "constraint_patch": {"party_size": 4, "budget_vnd": 500000},
              "remove_constraints": ["spice"],
              "needs_clarification": false,
              "clarification_slot": null,
              "confidence": 0.91
            }
            """
        )
        assert plan is not None

        result = apply_semantic_plan(
            plan,
            session_state={"conversation_frame": {"turn_sequence": 1}},
            constraints={"party_size": 2, "spice": "mild"},
        )

        self.assertEqual(4, result.constraints["party_size"])
        self.assertEqual(500000, result.constraints["budget_vnd"])
        self.assertNotIn("spice", result.constraints)
        self.assertEqual("pho bun", result.frame["resolved_category"])
        self.assertEqual(["nhau"], result.frame["resolved_tags"])
        self.assertEqual("explicit", result.frame["constraint_provenance"]["party_size"]["source"])

    def test_ambiguous_referent_creates_targeted_clarification(self) -> None:
        plan = parse_semantic_plan(
            """
            {
              "intent": "ask_price",
              "response_mode": "clarification",
              "category": null,
              "tags": [],
              "referent_ordinal": 4,
              "constraint_patch": {},
              "remove_constraints": [],
              "needs_clarification": true,
              "clarification_slot": "menu_item",
              "confidence": 0.4
            }
            """
        )
        assert plan is not None

        result = apply_semantic_plan(
            plan,
            session_state={
                "suggested_menu_item_ids": ["m_001", "m_002"],
                "conversation_frame": {"turn_sequence": 2},
            },
            constraints={},
        )

        self.assertEqual([], result.frame["focus_menu_item_ids"])
        self.assertEqual(
            "menu_item",
            result.frame["pending_clarification"]["slot"],
        )


if __name__ == "__main__":
    unittest.main()
