from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import GEMINI_OPENAI_BASE_URL, load_config


class GeminiConfigTests(unittest.TestCase):
    def _load_config(self, env: dict[str, str]) -> object:
        with patch.dict(os.environ, env, clear=True), patch("app.config._load_env_file", return_value=None):
            return load_config()

    def test_custom_base_url_is_used_for_openai_compatible_router(self) -> None:
        config = self._load_config(
            {
                "AI_PROVIDER": "openai",
                "AI_BASE_URL": "http://127.0.0.1:20128/v1",
                "AI_API_KEY": "router-test-key",
                "AI_MODEL": "gcli/grok-4.5",
            }
        )

        self.assertEqual(config.base_url, "http://127.0.0.1:20128/v1")
        self.assertEqual(config.model, "gcli/grok-4.5")
        self.assertTrue(config.llm_enabled)
        self.assertFalse(config.uses_gemini_native_features)

    def test_gemini_ignores_custom_base_url_when_not_set(self) -> None:
        config = self._load_config(
            {
                "AI_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-gemini-key",
                "AI_MODEL": "gemini-3.5-flash",
            }
        )

        self.assertEqual(config.base_url, GEMINI_OPENAI_BASE_URL)
        self.assertTrue(config.llm_enabled)
        self.assertTrue(config.uses_gemini_native_features)

    def test_legacy_api_key_does_not_enable_gemini(self) -> None:
        config = self._load_config(
            {
                "AI_PROVIDER": "gemini",
                "AI_API_KEY": "legacy-gateway-key",
                "AI_MODEL": "gemini-3.5-flash",
            }
        )

        self.assertFalse(config.llm_enabled)

    def test_defaults_to_9router_openai_profile(self) -> None:
        config = self._load_config({})

        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.base_url, "http://localhost:20128/v1")
        self.assertEqual(config.model, "cx/gpt-5.5")
        self.assertFalse(config.llm_enabled)

    def test_gemini_provider_still_supported_when_explicit(self) -> None:
        config = self._load_config(
            {
                "AI_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-gemini-key",
                "AI_MODEL": "gemini-3.5-flash",
            }
        )

        self.assertEqual(config.base_url, GEMINI_OPENAI_BASE_URL)
        self.assertEqual(config.model, "gemini-3.5-flash")
        self.assertTrue(config.uses_gemini_native_features)

    def test_intent_classification_config_defaults(self) -> None:
        config = self._load_config(
            {
                "AI_PROVIDER": "openai",
                "AI_BASE_URL": "http://127.0.0.1:20128/v1",
                "AI_API_KEY": "router-test-key",
                "AI_MODEL": "gcli/grok-4.5",
            }
        )
        self.assertTrue(config.llm_intent_classification_enabled)
        self.assertEqual(config.intent_classification_timeout_seconds, 2.5)


if __name__ == "__main__":
    unittest.main()
