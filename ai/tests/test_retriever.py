import unittest
from pathlib import Path

from app.rag.knowledge_base import load_markdown_knowledge_base
from app.rag.retriever import LexicalRetriever


class RetrieverTests(unittest.TestCase):
    def test_search_finds_ordering_policy_for_takeaway_question(self):
        chunks = load_markdown_knowledge_base(Path("ai/knowledge-base"))
        retriever = LexicalRetriever(chunks)

        results = retriever.search("Nhà hàng có nhận đơn mang về không?", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.chunk.source == "ordering-policy.md" for result in results))

    def test_search_finds_menu_for_fresh_drink_question(self):
        chunks = load_markdown_knowledge_base(Path("ai/knowledge-base"))
        retriever = LexicalRetriever(chunks)

        results = retriever.search("Có món nào thanh mát không?", top_k=5)

        self.assertTrue(results)
        self.assertTrue(any(result.chunk.source == "menu.md" for result in results))


if __name__ == "__main__":
    unittest.main()
