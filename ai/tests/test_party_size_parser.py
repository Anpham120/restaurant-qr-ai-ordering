from __future__ import annotations

import unittest

from app.rag.conversation_policy import build_conversation_policy
from app.rag.constraint_extractor import extract_constraints
from app.rag.party_size_parser import extract_party_size_from_text, is_solo_dining_text
from app.rag.vietnamese_normalizer import normalize_query_text


class PartySizeParserTests(unittest.TestCase):
    def test_word_party_sizes(self) -> None:
        self.assertEqual(4, extract_party_size_from_text(normalize_query_text("bon nguoi an gi")))
        self.assertEqual(6, extract_party_size_from_text(normalize_query_text("sau nguoi goi y")))
        self.assertEqual(2, extract_party_size_from_text(normalize_query_text("hai nguoi an gi")))

    def test_solo_slang(self) -> None:
        normalized = normalize_query_text("di an solo toi nay")
        self.assertTrue(is_solo_dining_text(normalized))
        self.assertEqual(1, extract_party_size_from_text(normalized))

    def test_solo_seating_is_not_party_one(self) -> None:
        normalized = normalize_query_text("mot minh co duoc khong")
        self.assertIsNone(extract_party_size_from_text(normalized))

    def test_cho_nguoi_is_party_not_seating(self) -> None:
        normalized = normalize_query_text("cho 8 nguoi goi mon gi")
        self.assertEqual(8, extract_party_size_from_text(normalized))


class RoutingAccuracyRegressionTests(unittest.TestCase):
    def test_solo_slang_wants_recommendation(self) -> None:
        policy = build_conversation_policy("di an solo toi nay", [], "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(1, policy.party_size)

    def test_word_party_sets_size(self) -> None:
        policy = build_conversation_policy("bon nguoi an gi", [], "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(4, policy.party_size)

    def test_rejection_overrides_goi_y(self) -> None:
        policy = build_conversation_policy("bo qua goi y do", [], "", [])
        self.assertFalse(policy.wants_recommendations)

    def test_payment_faq_is_not_recommendation(self) -> None:
        policy = build_conversation_policy("co tra bang the khong", [], "", [])
        self.assertFalse(policy.wants_recommendations)

    def test_capacity_question_is_not_recommendation(self) -> None:
        policy = build_conversation_policy("suc chua phong bao nhieu nguoi", [], "", [])
        self.assertFalse(policy.wants_recommendations)

    def test_catalog_browse_is_not_recommendation(self) -> None:
        policy = build_conversation_policy("co mon gi trong menu", [], "", [])
        self.assertFalse(policy.wants_recommendations)

    def test_dietary_constraint_triggers_recommendation(self) -> None:
        policy = build_conversation_policy("mon cay vua thoi", [], "", [])
        self.assertTrue(policy.wants_recommendations)

    def test_multi_turn_follow_up_wants_recommendation(self) -> None:
        history = [
            {"role": "user", "content": "4 nguoi an gi"},
            {"role": "assistant", "content": "Mình gợi ý lẩu hải sản."},
        ]
        policy = build_conversation_policy("the con mon gi nua", history, "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(4, policy.party_size)

    def test_goi_mon_gi_is_recommendation_not_order(self) -> None:
        policy = build_conversation_policy("4 nguoi goi mon gi", [], "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(4, policy.party_size)

    def test_cho_nguoi_goi_y_wants_recommendation(self) -> None:
        policy = build_conversation_policy("cho 8 nguoi goi y mon", [], "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(8, policy.party_size)

    def test_multi_turn_du_cho_party_follow_up(self) -> None:
        history = [
            {"role": "user", "content": "4 nguoi an gi"},
            {"role": "assistant", "content": "Goi y combo lau + goi cuon."},
        ]
        policy = build_conversation_policy("du cho 4 nguoi khong", history, "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(4, policy.party_size)

    def test_multi_turn_du_tien_follow_up(self) -> None:
        history = [
            {"role": "user", "content": "500k cho 5 nguoi"},
            {"role": "assistant", "content": "Combo lau + goi cuon khoang 480k."},
        ]
        policy = build_conversation_policy("du tien khong", history, "", [])
        self.assertTrue(policy.wants_recommendations)
        self.assertEqual(5, policy.party_size)

    def test_solo_flag_in_constraints(self) -> None:
        constraints = extract_constraints("di an solo toi nay", [])
        self.assertTrue(constraints.get("is_solo_dining"))


if __name__ == "__main__":
    unittest.main()
