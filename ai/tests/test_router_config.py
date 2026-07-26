from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import DEFAULT_PIPELINE_PROFILE, DEFAULT_ROUTER_BASE_URL, load_config


class RouterConfigTests(unittest.TestCase):
    def _load_config(self, env: dict[str, str]):
        with patch.dict(os.environ, env, clear=True), patch(
            "app.config._load_env_file", return_value=None
        ):
            return load_config()

    def test_defaults_to_9router_deepseek_profile_without_enabling_missing_key(self) -> None:
        config = self._load_config({})

        self.assertEqual("9router", config.provider)
        self.assertEqual(DEFAULT_ROUTER_BASE_URL, config.base_url)
        self.assertEqual("oc/deepseek-v4-flash-free", config.model)
        self.assertFalse(config.llm_enabled)

    def test_blank_pipeline_profile_uses_default_for_unconfigured_ci_variable(self) -> None:
        config = self._load_config({"AI_PIPELINE_PROFILE": "  "})

        self.assertEqual(DEFAULT_PIPELINE_PROFILE, config.pipeline_profile)

    def test_canonical_9router_config_accepts_gpt55_and_deepseek(self) -> None:
        for model in ("cx/gpt-5.5", "oc/deepseek-v4-flash-free"):
            with self.subTest(model=model):
                config = self._load_config(
                    {
                        "LLM_PROVIDER": "9router",
                        "LLM_BASE_URL": "http://127.0.0.1:20128/v1/",
                        "LLM_API_KEY": "router-test-key",
                        "LLM_MODEL": model,
                    }
                )
                self.assertEqual("http://127.0.0.1:20128/v1", config.base_url)
                self.assertEqual(model, config.model)
                self.assertTrue(config.llm_enabled)

    def test_legacy_openai_profile_is_normalized_with_deprecation_warning(self) -> None:
        with self.assertWarns(DeprecationWarning):
            config = self._load_config(
                {
                    "AI_PROVIDER": "openai",
                    "AI_BASE_URL": "http://127.0.0.1:20128/v1",
                    "AI_API_KEY": "router-test-key",
                    "AI_MODEL": "cx/gpt-5.5",
                }
            )

        self.assertEqual("9router", config.provider)
        self.assertTrue(config.llm_enabled)

    def test_gemini_provider_and_model_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "9router"):
            self._load_config(
                {
                    "LLM_PROVIDER": "gemini",
                    "LLM_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
                    "LLM_API_KEY": "old-key",
                    "LLM_MODEL": "gemini-3.5-flash",
                }
            )

    def test_gemini_api_host_in_base_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Gemini endpoints"):
            self._load_config(
                {
                    "LLM_PROVIDER": "9router",
                    "LLM_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
                    "LLM_API_KEY": "router-test-key",
                    "LLM_MODEL": "oc/deepseek-v4-flash-free",
                }
            )

    def test_gemini_hostname_substring_in_path_is_allowed(self) -> None:
        config = self._load_config(
            {
                "LLM_PROVIDER": "9router",
                "LLM_BASE_URL": "http://127.0.0.1:20128/v1/generativelanguage.googleapis.com",
                "LLM_API_KEY": "router-test-key",
                "LLM_MODEL": "oc/deepseek-v4-flash-free",
            }
        )
        self.assertTrue(config.llm_enabled)

    def test_non_gpt55_or_deepseek_model_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "GPT-5.5 or DeepSeek"):
            self._load_config(
                {
                    "LLM_PROVIDER": "9router",
                    "LLM_API_KEY": "router-test-key",
                    "LLM_MODEL": "gcli/grok-4.5",
                }
            )

    def test_intent_classification_config_defaults(self) -> None:
        config = self._load_config(
            {
                "LLM_PROVIDER": "9router",
                "LLM_API_KEY": "router-test-key",
                "LLM_MODEL": "cx/gpt-5.5",
            }
        )
        self.assertTrue(config.llm_intent_classification_enabled)
        self.assertEqual(2.5, config.intent_classification_timeout_seconds)


if __name__ == "__main__":
    unittest.main()
