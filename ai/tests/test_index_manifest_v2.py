from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.build_index import build_manifest


class IndexManifestV2Tests(unittest.TestCase):
    def test_manifest_locks_corpus_chunking_model_revision_and_hardware(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            kb_path = Path(directory)
            (kb_path / "faq.md").write_text(
                """---
id: kb.faq
tags: [faq]
safety_level: standard
---
# Giờ mở cửa
Nhà hàng mở cửa lúc 08:00.
""",
                encoding="utf-8",
            )
            config = SimpleNamespace(
                retrieval_method="hybrid",
                embedding_model="e5_small",
                rag_config_id="hybrid-e5-v2",
                pipeline_version="v3",
            )

            manifest = build_manifest(kb_path, config, [])

        self.assertEqual("knowledge-index-v2", manifest["manifest_version"])
        self.assertEqual(64, len(manifest["corpus_sha256"]))
        self.assertEqual(64, len(manifest["index_sha256"]))
        self.assertEqual("markdown-heading", manifest["chunking_config"]["strategy"])
        self.assertEqual("parent-child", manifest["chunking_config"]["hierarchy"])
        self.assertEqual("intfloat/multilingual-e5-small", manifest["embedding_model"])
        self.assertEqual(40, len(manifest["embedding_model_revision"]))
        self.assertIn("cpu_count", manifest["hardware"])
        self.assertEqual("hybrid-e5-v2", manifest["rag_config_id"])
        self.assertTrue(manifest["chunks"][0]["chunk_id"].startswith("kb:"))


if __name__ == "__main__":
    unittest.main()
