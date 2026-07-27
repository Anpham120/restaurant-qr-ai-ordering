from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import AsyncMock

from app.rag.constraint_extractor import extract_constraints
from app.rag.conversation_policy import build_conversation_policy
from app.rag.intent_classifier import IntentResult, classify_intent
from app.rag.llm_intent_classifier import (
    LlmIntentSignals,
    classify_with_llm,
    is_ambiguous,
    merge_llm_signals_into_constraints,
    merge_llm_signals_into_policy,
    parse_classification_response,
)


class LlmIntentClassifierTests(unittest.TestCase):
    def test_parse_classification_response_valid_json(self) -> None:
        raw = json.dumps(
            {
                "intent": "recommend",
                "party_size": 1,
                "wants_recommendations": True,
                "is_solo_dining": True,
                "kb_topic": None,
                "confidence": 0.92,
            }
        )
        signals = parse_classification_response(raw)
        self.assertIsNotNone(signals)
        assert signals is not None
        self.assertEqual(signals.intent, "recommend")
        self.assertEqual(signals.party_size, 1)
        self.assertTrue(signals.is_solo_dining)

    def test_is_ambiguous_for_general_low_confidence(self) -> None:
        message = "di an solo toi nay"
        intent = IntentResult(intent="general", confidence=0.0, source_hints=(), query_boost_terms=())
        constraints = extract_constraints(message, [])
        policy = build_conversation_policy(message, [], "", [])
        # Deterministic solo routing now resolves party/wants — no LLM needed.
        self.assertFalse(is_ambiguous(intent, constraints, policy, message=message))

    def test_is_ambiguous_for_unresolved_solo_slang(self) -> None:
        message = "ok la sao ay"
        intent = IntentResult(intent="general", confidence=0.0, source_hints=(), query_boost_terms=())
        constraints = extract_constraints(message, [])
        policy = build_conversation_policy(message, [], "", [])
        self.assertTrue(is_ambiguous(intent, constraints, policy, message=message))

    def test_wifi_query_with_borderline_confidence_gets_llm_assist(self) -> None:
        # The rule classifier assigns "wifi mat khau gi" the correct intent
        # (restaurant_info) but with confidence 0.3 — just under
        # AMBIGUITY_CONFIDENCE_THRESHOLD (0.35). It used to be treated as
        # "not ambiguous" only because "wifi" was on a generic keyword
        # shortlist, not because the classification was actually confident.
        # Removing that shortlist means borderline-confidence classifications
        # now correctly get the cheap LLM-assist double-check.
        message = "wifi mat khau gi"
        intent = classify_intent(message)
        self.assertEqual("restaurant_info", intent.intent)
        self.assertLess(intent.confidence, 0.35)
        constraints = extract_constraints(message, [])
        policy = build_conversation_policy(message, [], "", [])
        self.assertTrue(is_ambiguous(intent, constraints, policy, message=message))

    def test_is_not_ambiguous_for_explicit_party_size(self) -> None:
        message = "8 nguoi an gi"
        intent = classify_intent(message)
        constraints = extract_constraints(message, [])
        policy = build_conversation_policy(message, [], "", [])
        self.assertFalse(is_ambiguous(intent, constraints, policy, message=message))

    def test_merge_fills_party_without_overwriting(self) -> None:
        constraints = {"intent": "general", "party_size": None, "is_recommendation": False}
        signals = LlmIntentSignals(
            intent="recommend",
            party_size=1,
            wants_recommendations=True,
            is_solo_dining=True,
            kb_topic=None,
            confidence=0.9,
        )
        merged = merge_llm_signals_into_constraints(constraints, signals)
        self.assertEqual(merged["party_size"], 1)
        self.assertTrue(merged["is_solo_dining"])
        self.assertTrue(merged["is_recommendation"])

    def test_merge_policy_sets_wants_recommendations(self) -> None:
        policy = build_conversation_policy("chi co minh toi", [], "", [])
        signals = LlmIntentSignals(
            intent="recommend",
            party_size=1,
            wants_recommendations=True,
            is_solo_dining=True,
            kb_topic=None,
            confidence=0.88,
        )
        merged = merge_llm_signals_into_policy(policy, signals)
        self.assertTrue(merged.wants_recommendations)
        self.assertEqual(merged.party_size, 1)

    def test_classify_with_llm_uses_client(self) -> None:
        client = AsyncMock()
        client.complete_structured = AsyncMock(
            return_value=json.dumps(
                {
                    "intent": "recommend",
                    "party_size": 1,
                    "wants_recommendations": True,
                    "is_solo_dining": True,
                    "kb_topic": None,
                    "confidence": 0.95,
                }
            )
        )
        result = asyncio.run(
            classify_with_llm(client, "di an solo", [], "", timeout_seconds=5.0)
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.is_solo_dining)
        client.complete_structured.assert_awaited_once()

    def test_classify_with_llm_returns_none_on_failure(self) -> None:
        client = AsyncMock()
        client.complete_structured = AsyncMock(side_effect=RuntimeError("down"))
        result = asyncio.run(classify_with_llm(client, "di an solo", [], ""))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
