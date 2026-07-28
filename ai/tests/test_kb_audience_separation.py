"""Guidance written for the assistant must never be quoted to a guest.

The knowledge base holds two kinds of text in one corpus: facts a guest may be
told, and instructions written for the assistant — brand voice, answer-structure
templates, "Lưu Ý Cho AI", "Không Được Nói", and the internal order-mining
analysis.  Nothing separated them, so a guest asking "Bếp trưởng tên gì?" was
served the answer-structure template verbatim:

    1. Mở đầu ngắn (1 câu): xác nhận hiểu yêu cầu.
    2. Danh sách món: tên, giá, mô tả ngắn.

and, after the first fix, the internal comparison-axis table.  Both arrived
through deterministic paths, so both would have reached production.

These tests pin the separation at the three places that matter: the data declares
it, the loader honours it, and the answer paths refuse to quote it.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from app.rag.knowledge_base import load_markdown_knowledge_base

AI_ROOT = Path(__file__).resolve().parents[1]
KB_PATH = AI_ROOT / "knowledge-base"

# Documents that are guidance from front matter to last line.
AI_ONLY_DOCUMENTS = (
    "brand-voice.md",
    "negative-examples.md",
    "context-disambiguation.md",
    "data-mining-insights.md",
    "dish-comparison.md",
)

# Sections inside otherwise guest-facing documents.
AI_ONLY_SECTIONS = (
    ("allergy-dietary.md", "Lưu Ý Cho AI"),
    ("allergy-disclaimer.md", "Không Được Nói"),
    ("combo-pairing.md", "Lưu Ý Cho AI"),
    ("menu.md", "Quy Tắc Gợi Ý Món"),
    ("seasonal-promotion.md", "Lưu Ý Cho AI"),
)

# Phrases that only ever appear in guidance.  If one of these reaches a guest,
# the separation has broken somewhere.
GUIDANCE_PHRASES = (
    "Mở đầu ngắn",
    "Danh sách món: tên, giá, mô tả ngắn",
    "min_support",
    "Tài liệu này quy định",
)


class KnowledgeBaseAudienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.chunks = load_markdown_knowledge_base(KB_PATH)

    def test_whole_guidance_documents_are_ai_only(self) -> None:
        for source in AI_ONLY_DOCUMENTS:
            chunks = [c for c in self.chunks if c.source == source]
            with self.subTest(source=source):
                self.assertTrue(chunks, f"{source} produced no chunks")
                leaked = [c.section_path[-1] for c in chunks if c.is_customer_facing]
                self.assertEqual([], leaked)

    def test_guidance_sections_inside_guest_documents_are_ai_only(self) -> None:
        for source, section in AI_ONLY_SECTIONS:
            matches = [
                c
                for c in self.chunks
                if c.source == source and c.section_path[-1] == section
            ]
            with self.subTest(source=source, section=section):
                self.assertTrue(matches, f"{source}::{section} not found")
                self.assertTrue(all(c.audience == "ai" for c in matches))

    def test_policy_a_guest_actually_asks_about_stays_guest_facing(self) -> None:
        # "Quy Tắc An Toàn" reads like guidance but carries
        # `question_variants: AI có tự đặt đơn không` — guests do ask whether the
        # assistant orders for them, and "AI không tự tạo đơn" is the answer.
        # Audience is declared per section for exactly this reason; a
        # title-pattern rule would have mislabelled it.
        matches = [
            c
            for c in self.chunks
            if c.source == "ordering-policy.md" and c.section_path[-1] == "Quy Tắc An Toàn"
        ]
        self.assertTrue(matches)
        self.assertTrue(all(c.is_customer_facing for c in matches))

    def test_no_guidance_phrase_survives_in_guest_facing_content(self) -> None:
        guest_text = "\n".join(c.content for c in self.chunks if c.is_customer_facing)
        for phrase in GUIDANCE_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, guest_text)

    def test_both_kinds_of_content_still_exist(self) -> None:
        # A filter that swallowed the whole corpus would pass every test above.
        guest = [c for c in self.chunks if c.is_customer_facing]
        guidance = [c for c in self.chunks if c.audience == "ai"]
        self.assertGreater(len(guest), 150)
        self.assertGreater(len(guidance), 20)

    def test_golden_answer_keys_never_point_at_guidance(self) -> None:
        import json

        guidance_keys = {
            f"{c.source}::{c.section_path[-1]}"
            for c in self.chunks
            if c.audience == "ai"
        }
        golden = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"
        offenders: list[tuple[str, str]] = []
        for line in golden.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            case = json.loads(line)
            for key in case.get("expected_chunk_ids") or []:
                if key in guidance_keys:
                    offenders.append((case["id"], key))
        # Grading retrieval against a chunk the guest may never see measures
        # nothing: 96 of 1263 keys did this before the repair.
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
