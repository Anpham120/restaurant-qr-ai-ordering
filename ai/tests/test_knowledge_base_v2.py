from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.rag.knowledge_base import KnowledgeChunk, load_markdown_knowledge_base
from app.rag.retriever import BM25Retriever


class KnowledgeBaseV2Tests(unittest.TestCase):
    def test_frontmatter_and_heading_hierarchy_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.md"
            path.write_text(
                """---
id: kb.policy.v2
title: Chính sách
domain: policy
tags: [faq, policy]
language: vi
source: approved_manual
reviewed_by: reviewer
reviewed_at: 2026-01-01
expires_at: 2030-12-31
safety_level: high
---

# Chính sách

Tổng quan.

## Hoàn tiền

Chỉ nhân viên được xác nhận hoàn tiền.
""",
                encoding="utf-8",
            )

            chunks = load_markdown_knowledge_base(Path(directory))

        self.assertEqual(2, len(chunks))
        child = chunks[1]
        self.assertEqual("kb.policy.v2", child.document_id)
        self.assertEqual(("Chính sách", "Hoàn tiền"), child.section_path)
        self.assertEqual(("faq", "policy"), child.tags)
        self.assertEqual("high", child.risk_tier)
        self.assertEqual("2026-01-01", child.valid_from)
        self.assertEqual("2030-12-31", child.valid_to)
        self.assertIsNotNone(child.parent_id)
        self.assertTrue(child.chunk_id.startswith("kb:kb.policy.v2:"))

    def test_chunk_id_is_stable_while_content_hash_tracks_edits(self) -> None:
        first = KnowledgeChunk(
            source="faq.md",
            document_id="kb.faq.v2",
            title="Giờ mở cửa",
            section_path=("FAQ", "Giờ mở cửa"),
            content="Mở cửa lúc 8 giờ.",
            tags=("faq",),
        )
        edited = KnowledgeChunk(
            source="faq.md",
            document_id="kb.faq.v2",
            title="Giờ mở cửa",
            section_path=("FAQ", "Giờ mở cửa"),
            content="Mở cửa lúc 9 giờ.",
            tags=("faq",),
        )

        self.assertEqual(first.chunk_id, edited.chunk_id)
        self.assertNotEqual(first.content_hash, edited.content_hash)

    def test_expired_chunks_are_never_ranked(self) -> None:
        expired = KnowledgeChunk(
            source="old.md",
            title="Khuyến mãi cũ",
            content="Giảm giá đặc biệt",
            tags=("promotion",),
            valid_to="2020-01-01",
        )
        current = KnowledgeChunk(
            source="current.md",
            title="Khuyến mãi hiện tại",
            content="Giảm giá đặc biệt",
            tags=("promotion",),
            valid_to="2099-01-01",
        )

        results = BM25Retriever([expired, current]).search("giảm giá đặc biệt", top_k=5)

        self.assertEqual([current.chunk_id], [item.chunk.chunk_id for item in results])


if __name__ == "__main__":
    unittest.main()
