from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import GEMINI_OPENAI_BASE_URL, load_config


class GeminiConfigTests(unittest.TestCase):
    def test_gateway_url_cannot_override_official_gemini_endpoint(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "gemini",
                "AI_BASE_URL": "http://127.0.0.1:20128/v1",
                "GEMINI_API_KEY": "test-gemini-key",
                "AI_MODEL": "gemini-3.5-flash",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.base_url, GEMINI_OPENAI_BASE_URL)
        self.assertTrue(config.llm_enabled)

    def test_legacy_api_key_does_not_enable_gemini(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "gemini",
                "AI_API_KEY": "legacy-gateway-key",
                "AI_MODEL": "gemini-3.5-flash",
            },
            clear=True,
        ):
            config = load_config()

        self.assertFalse(config.llm_enabled)

    def test_v31_defaults_to_current_verified_gemini_model(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "gemini",
                "GEMINI_API_KEY": "test-gemini-key",
            },
            clear=True,
        ):
            config = load_config()

        self.assertEqual(config.model, "gemini-3.5-flash")


if __name__ == "__main__":
    unittest.main()
