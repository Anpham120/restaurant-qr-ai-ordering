import asyncio
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("httpx", types.SimpleNamespace(AsyncClient=object))

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class AssistantTests(unittest.TestCase):
    def test_provider_failure_returns_safe_fallback_without_cart_action(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as tmp_dir:
                Path(tmp_dir, "faq.md").write_text("# FAQ\nKhách có thể đặt món mang về.\n", encoding="utf-8")
                service = AiAssistantService(
                    AiServiceConfig(
                        provider="9router",
                        base_url="http://127.0.0.1:20128/v1",
                        api_key="test-key",
                        model="gh/gemini-3.1-pro-preview",
                        timeout_seconds=1,
                        knowledge_base_path=Path(tmp_dir),
                        top_k=3,
                    )
                )

                with patch("app.services.assistant.NineRouterClient.complete", side_effect=RuntimeError("offline")):
                    response = await service.chat({"message": "Nhà hàng có nhận mang về không?"})

                self.assertFalse(response["provider_available"])
                self.assertEqual([], response["suggested_cart_actions"])
                self.assertIn("AI_PROVIDER_UNAVAILABLE", response["guardrail_flags"])
                self.assertTrue(response["content"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
