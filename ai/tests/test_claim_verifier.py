from __future__ import annotations

import unittest

from app.rag.claim_verifier import verify_claims
from app.rag.knowledge_base import KnowledgeChunk


class ClaimVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.menu = [
            {
                "id": "m_001",
                "name": "Phở bò tái",
                "price_vnd": 85000,
                "is_available": True,
                "description": "Phở bò với thịt tái",
            }
        ]
        self.chunk = KnowledgeChunk(
            source="faq.md",
            title="Giờ mở cửa",
            content="Nhà hàng mở cửa lúc 08:00 mỗi ngày.",
            tags=("faq",),
        )

    def test_live_menu_price_claim_is_verified(self) -> None:
        claims, all_verified = verify_claims(
            [{"text": "Phở bò tái có giá 85.000 đồng.", "evidence_ids": ["m_001"]}],
            chunks=[self.chunk],
            menu_items=self.menu,
        )

        self.assertTrue(all_verified)
        self.assertTrue(claims[0]["verified"])

    def test_fabricated_number_is_blocked_even_with_real_menu_id(self) -> None:
        claims, all_verified = verify_claims(
            [{"text": "Phở bò tái có giá 20.000 đồng.", "evidence_ids": ["m_001"]}],
            chunks=[self.chunk],
            menu_items=self.menu,
        )

        self.assertFalse(all_verified)
        self.assertFalse(claims[0]["verified"])
        self.assertEqual("numeric_value_not_in_evidence", claims[0]["reason"])

    def test_missing_or_unknown_evidence_fails_closed(self) -> None:
        claims, all_verified = verify_claims(
            [{"text": "Nhà hàng mở lúc 7 giờ.", "evidence_ids": ["missing"]}],
            chunks=[self.chunk],
            menu_items=self.menu,
        )

        self.assertFalse(all_verified)
        self.assertEqual("unknown_evidence_id", claims[0]["reason"])


if __name__ == "__main__":
    unittest.main()
