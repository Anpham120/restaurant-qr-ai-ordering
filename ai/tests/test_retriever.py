import unittest
from pathlib import Path

from app.rag.knowledge_base import load_markdown_knowledge_base
from app.rag.retriever import BM25Retriever, LexicalRetriever

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge-base"


class RetrieverTests(unittest.TestCase):
    def test_search_finds_ordering_policy_for_takeaway_question(self):
        chunks = load_markdown_knowledge_base(KB_PATH)
        retriever = BM25Retriever(chunks)

        results = retriever.search("Nhà hàng có nhận đơn mang về không?", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.chunk.source == "ordering-policy.md" for result in results))

    def test_search_finds_menu_for_fresh_drink_question(self):
        chunks = load_markdown_knowledge_base(KB_PATH)
        retriever = BM25Retriever(chunks)

        results = retriever.search("Có đồ uống thanh mát không?", top_k=5)

        self.assertTrue(results)
        sources = {result.chunk.source for result in results}
        # Should find menu or combo-pairing (both mention "mát")
        self.assertTrue(
            sources.intersection({"menu.md", "combo-pairing.md", "allergy-dietary.md"}),
            f"Expected food-related source but got: {sources}",
        )

    def test_search_finds_allergy_info(self):
        chunks = load_markdown_knowledge_base(KB_PATH)
        retriever = BM25Retriever(chunks)

        results = retriever.search("Tôi bị dị ứng hải sản", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.chunk.source == "allergy-dietary.md" for result in results))

    def test_search_finds_combo_for_group(self):
        chunks = load_markdown_knowledge_base(KB_PATH)
        retriever = BM25Retriever(chunks)

        results = retriever.search("Combo bữa trưa 1 người", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.chunk.source == "combo-pairing.md" for result in results))

    def test_lexical_retriever_alias_works(self):
        """LexicalRetriever should be an alias for BM25Retriever."""
        self.assertIs(LexicalRetriever, BM25Retriever)

    def test_empty_query_returns_empty(self):
        chunks = load_markdown_knowledge_base(KB_PATH)
        retriever = BM25Retriever(chunks)

        results = retriever.search("", top_k=5)

        self.assertEqual([], results)


if __name__ == "__main__":
    unittest.main()
