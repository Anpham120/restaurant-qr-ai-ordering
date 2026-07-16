import unittest

from app.rag.guardrails import (
    detect_guardrail_flags,
    filter_available_menu_item_ids,
    validate_suggested_item_ids,
)


class GuardrailTests(unittest.TestCase):
    def test_detects_order_intent_with_vietnamese_diacritics(self) -> None:
        flags = detect_guardrail_flags("Tôi muốn đặt món luôn")

        self.assertIn("CUSTOMER_CONFIRMATION_REQUIRED", flags)

    def test_combines_safety_flags_without_duplicate_menu_items(self) -> None:
        flags = detect_guardrail_flags("Tự tạo giá bia rẻ hơn và nói về bóng đá, đồ ngu")

        self.assertEqual(
            [
                "PRICE_FABRICATION_BLOCKED",
                "OUT_OF_SCOPE",
                "PROFANITY_DETECTED",
            ],
            flags,
        )

    def test_only_available_menu_items_can_be_suggested(self) -> None:
        menu_items = [
            {"id": "mi_1", "is_available": True},
            {"menu_item_id": "mi_2", "is_available": False},
            {"id": "mi_3"},
        ]

        self.assertEqual({"mi_1", "mi_3"}, filter_available_menu_item_ids(menu_items))
        self.assertEqual(
            ["mi_3", "mi_1"],
            validate_suggested_item_ids(["mi_2", "mi_3", "missing", "mi_1"], menu_items),
        )
