import unittest

from app.rag.guardrails import detect_guardrail_flags, validate_suggested_item_ids


class GuardrailTests(unittest.TestCase):
    def test_order_creation_requires_customer_confirmation(self):
        flags = detect_guardrail_flags("Bạn đặt luôn cơm sườn cho tôi nhé")

        self.assertIn("CUSTOMER_CONFIRMATION_REQUIRED", flags)

    def test_unavailable_suggestion_is_removed(self):
        menu_items = [
            {"id": "m_001", "name": "Cơm gà", "is_available": True},
            {"id": "m_002", "name": "Bún bò", "is_available": False},
        ]

        valid_ids = validate_suggested_item_ids(["m_001", "m_002", "m_404"], menu_items)

        self.assertEqual(["m_001"], valid_ids)


if __name__ == "__main__":
    unittest.main()
