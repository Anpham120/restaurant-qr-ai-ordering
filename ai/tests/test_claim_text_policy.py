from __future__ import annotations

import unittest

from app.rag.prompts import SYSTEM_POLICY


class ClaimTextPolicyTests(unittest.TestCase):
    """claims[].text is internal-only (never rendered to the customer — see
    ChatAssistantReply in the .NET backend, which has no Claims field) so it
    should stay evidence-anchored even when `content` is paraphrased for the
    customer. This guards the instruction against accidental removal."""

    def test_system_policy_scopes_paraphrase_rule_to_content_only(self) -> None:
        self.assertIn(
            'Quy tắc diễn đạt lại này áp dụng cho "content"',
            SYSTEM_POLICY,
        )

    def test_system_policy_tells_model_to_keep_claims_evidence_anchored(self) -> None:
        self.assertIn("claims[].text KHÔNG hiển thị cho khách", SYSTEM_POLICY)
        self.assertIn("BÁM SÁT từ ngữ và số liệu trong evidence", SYSTEM_POLICY)


if __name__ == "__main__":
    unittest.main()
