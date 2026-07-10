import unittest
from pathlib import Path

from app.data import documents_from_menu, load_policy_documents
from app.retrieval import BM25Retriever, TfidfRetriever
from research.menu_seed import load_snapshot


AI_ROOT = Path(__file__).resolve().parents[1]


class RetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        items = load_snapshot(AI_ROOT / "research" / "menu_snapshot.json").items
        cls.documents = documents_from_menu(items) + load_policy_documents(AI_ROOT / "data" / "policies.json")

    def test_tfidf_finds_exact_menu_item(self):
        results = TfidfRetriever(self.documents).search("Cho tôi Phở bò tái nạm", top_k=5)

        self.assertEqual("menu:m_008", results[0].document.id)

    def test_bm25_normalizes_vietnamese_diacritics(self):
        results = BM25Retriever(self.documents).search("quan co bun bo hue khong", top_k=5)

        self.assertEqual("menu:m_010", results[0].document.id)

    def test_policy_and_menu_use_same_document_contract(self):
        results = TfidfRetriever(self.documents).search("quán có mạng miễn phí không", top_k=5)

        self.assertEqual("policy:wifi", results[0].document.id)


if __name__ == "__main__":
    unittest.main()

