import os
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from research.menu_seed import load_snapshot


AI_ROOT = Path(__file__).resolve().parents[1]


class ApiTests(unittest.TestCase):
    def test_health_retrieval_and_chat_use_production_config(self):
        env = {
            "AI_API_KEY": "",
            "AI_POLICIES_PATH": str(AI_ROOT / "data" / "policies.json"),
            "RAG_PRODUCTION_CONFIG_PATH": str(
                AI_ROOT / "research" / "artifacts" / "production_config.json"
            ),
        }
        menu = [item.to_mapping() for item in load_snapshot(AI_ROOT / "research" / "menu_snapshot.json").items]

        with patch.dict(os.environ, env, clear=False), TestClient(app) as client:
            health = client.get("/health")
            search = client.post(
                "/v1/retrieval/search",
                json={"query": "pho bo tai nam", "menu_items": menu, "top_k": 3},
            )
            chat = client.post(
                "/v1/chat",
                json={
                    "message": "Giá của Phở bò tái nạm bao nhiêu?",
                    "menu_items": menu,
                    "history": [],
                    "table_code": "T01",
                },
            )

        self.assertEqual(200, health.status_code)
        self.assertEqual("tfidf", health.json()["retrieval_method"])
        self.assertEqual(200, search.status_code)
        self.assertEqual("m_008", search.json()["results"][0]["menu_item_id"])
        self.assertEqual(200, chat.status_code)
        self.assertEqual("price", chat.json()["fast_path"])
        self.assertIn("75.000 VND", chat.json()["content"])
        self.assertFalse(chat.json()["provider_available"])


if __name__ == "__main__":
    unittest.main()
