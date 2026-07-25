from __future__ import annotations

import unittest

from evaluation.summarize_retrieval_comparison import attach_knowledge_index_provenance


class RetrievalSummaryProvenanceTests(unittest.TestCase):
    def test_links_distinct_full_eval_and_knowledge_index_hashes(self) -> None:
        summary = {
            "corpus": {
                "corpus_sha256": "full-eval-corpus",
                "knowledge_source_sha256": {"faq.md": "source-hash"},
            }
        }
        manifest = {
            "corpus_sha256": "kb-index-corpus",
            "index_sha256": "index-hash",
            "knowledge_source_sha256": {"faq.md": "source-hash"},
        }

        result = attach_knowledge_index_provenance(
            summary,
            manifest,
            manifest_sha256="manifest-hash",
        )

        corpus = result["corpus"]
        self.assertEqual("full-eval-corpus", corpus["corpus_sha256"])
        self.assertEqual("kb-index-corpus", corpus["knowledge_index_corpus_sha256"])
        self.assertEqual("index-hash", corpus["knowledge_index_sha256"])
        self.assertEqual("manifest-hash", corpus["knowledge_index_manifest_sha256"])

    def test_rejects_stale_knowledge_manifest(self) -> None:
        summary = {
            "corpus": {"knowledge_source_sha256": {"faq.md": "new"}}
        }
        manifest = {
            "corpus_sha256": "kb-index-corpus",
            "index_sha256": "index-hash",
            "knowledge_source_sha256": {"faq.md": "old"},
        }

        with self.assertRaisesRegex(ValueError, "source hashes do not match"):
            attach_knowledge_index_provenance(
                summary,
                manifest,
                manifest_sha256="manifest-hash",
            )


if __name__ == "__main__":
    unittest.main()
