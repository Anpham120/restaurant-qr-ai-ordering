import json
import unittest

from app.rag.output_parser import parse_model_response


class OutputParserTests(unittest.TestCase):
    def test_valid_json_suggestion_is_kept_and_requires_confirmation(self):
        menu_items = [
            {"id": "m_001", "name": "Phở bò", "price_vnd": 65000, "is_available": True},
        ]
        payload = json.dumps(
            {
                "content": "Mình gợi ý Phở bò vì dễ ăn và hợp bữa trưa.",
                "suggested_cart_actions": [
                    {
                        "menu_item_id": "m_001",
                        "quantity": 2,
                        "reason": "Hợp bữa trưa",
                        "requires_customer_confirmation": False,
                    }
                ],
                "guardrail_flags": [],
            },
            ensure_ascii=False,
        )

        parsed = parse_model_response(payload, menu_items)

        self.assertIsNotNone(parsed)
        self.assertEqual("m_001", parsed.suggested_cart_actions[0]["menu_item_id"])
        self.assertTrue(parsed.suggested_cart_actions[0]["requires_customer_confirmation"])
        self.assertIn("CUSTOMER_CONFIRMATION_REQUIRED", parsed.guardrail_flags)

    def test_unavailable_and_unknown_items_are_blocked(self):
        menu_items = [
            {"id": "m_001", "name": "Phở bò", "is_available": False},
        ]
        payload = json.dumps(
            {
                "content": "Mình chưa có món phù hợp để thêm vào giỏ.",
                "suggested_cart_actions": [{"menu_item_id": "m_001"}, {"menu_item_id": "m_404"}],
                "guardrail_flags": [],
            },
            ensure_ascii=False,
        )

        parsed = parse_model_response(payload, menu_items)

        self.assertIsNotNone(parsed)
        self.assertEqual([], parsed.suggested_cart_actions)
        self.assertIn("MENU_FABRICATION_BLOCKED", parsed.guardrail_flags)

    def test_free_form_output_is_rejected(self):
        parsed = parse_model_response("Bạn nên ăn phở bò nhé.", [])

        self.assertIsNone(parsed)


if __name__ == "__main__":
    unittest.main()
