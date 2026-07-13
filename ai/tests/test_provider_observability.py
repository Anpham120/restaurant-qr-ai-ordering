import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import AiServiceConfig
from app.services.assistant import AiAssistantService


class _UnavailableProviderClient:
    async def complete(self, _messages: list[dict[str, str]]) -> str:
        raise RuntimeError("model_not_supported")


class ProviderObservabilityTests(unittest.TestCase):
    def test_provider_failure_is_logged_and_returns_guarded_fallback(self) -> None:
        config = AiServiceConfig(
            provider="gemini",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            api_key="test-key",
            model="gemini-3.5-flash",
            timeout_seconds=1,
            max_retry=1,
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=1,
        )
        service = AiAssistantService(config)

        with (
            patch(
                "app.services.assistant.GeminiClient",
                return_value=_UnavailableProviderClient(),
            ),
            self.assertLogs("app.services.assistant", level="ERROR") as captured,
        ):
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
        self.assertIn("provider=gemini", log_output)
        self.assertIn("model=gemini-3.5-flash", log_output)
        self.assertIn("error_type=RuntimeError", log_output)
        self.assertNotIn("test-key", log_output)
        self.assertNotIn("Gợi ý món nhẹ", log_output)
