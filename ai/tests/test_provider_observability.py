import asyncio
import unittest
from pathlib import Path

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _UnavailableProviderClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str:
        raise RuntimeError("model_not_supported")


class ProviderObservabilityTests(unittest.TestCase):
    def test_provider_failure_is_logged_and_returns_guarded_fallback(self) -> None:
        config = AiServiceConfig(
            provider="9router",
            base_url="http://localhost:20128/v1",
            api_key="test-key",
            model="cx/gpt-5.5",
            llm_timeout_seconds=1,
            request_budget_seconds=2,
            max_retry=1,
            max_tokens=700,
            reasoning_effort="low",
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=1,
            retrieval_method="bm25",
        )
        service = AiAssistantService(config, llm_client=_UnavailableProviderClient())

        with self.assertLogs("app.services.assistant", level="ERROR") as captured:
            response = asyncio.run(
                service.chat(
                    {
                        "message": "Gợi ý món nhẹ",
                        "history": [],
                        "menu_items": [],
                    }
                )
            )

        self.assertFalse(response["provider_available"])
        self.assertIn("AI_PROVIDER_UNAVAILABLE", response["guardrail_flags"])
        log_output = "\n".join(captured.output)
        self.assertIn("provider=9router", log_output)
        self.assertIn("model=cx/gpt-5.5", log_output)
        self.assertIn("error_type=RuntimeError", log_output)
        self.assertNotIn("test-key", log_output)
        self.assertNotIn("Gợi ý món nhẹ", log_output)
