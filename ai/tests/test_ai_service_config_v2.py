from __future__ import annotations

import os
import unittest
import warnings
from unittest.mock import patch

from app.config import load_config


class AiServiceConfigV2Tests(unittest.TestCase):
    @staticmethod
    def _load_config(env: dict[str, str]):
        with (
            patch.dict(os.environ, env, clear=True),
            patch("app.config._load_env_file", return_value=None),
        ):
            return load_config()

    def test_llm_environment_names_take_precedence_over_legacy_ai_names(self) -> None:
        env = {
            "LLM_PROVIDER": "9router",
            "LLM_BASE_URL": "http://router.example/v1",
            "LLM_API_KEY": "new-key",
            "LLM_MODEL": "cx/gpt-5.5",
            "AI_PROVIDER": "gemini",
            "AI_BASE_URL": "http://legacy.example/v1",
            "AI_API_KEY": "legacy-key",
            "AI_MODEL": "legacy-model",
            "AI_INTERNAL_TOKEN": "internal-token",
            "AI_PIPELINE": "v3",
            "RAG_CONFIG_ID": "hybrid-e5-v2",
        }

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", DeprecationWarning)
            config = self._load_config(env)

        self.assertEqual("9router", config.provider)
        self.assertEqual("http://router.example/v1", config.base_url)
        self.assertEqual("new-key", config.api_key)
        self.assertEqual("cx/gpt-5.5", config.model)
        self.assertEqual("internal-token", config.internal_token)
        self.assertEqual("v3", config.pipeline_version)
        self.assertEqual("hybrid-e5-v2", config.rag_config_id)
        self.assertEqual([], captured, "ignored aliases must not emit migration warnings")

    def test_legacy_ai_environment_names_work_for_one_release_with_warnings(self) -> None:
        env = {
            "AI_PROVIDER": "openai",
            "AI_BASE_URL": "http://legacy.example/v1",
            "AI_API_KEY": "legacy-key",
            "AI_MODEL": "oc/deepseek-v4-flash-free",
        }

        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always", DeprecationWarning)
            config = self._load_config(env)

        self.assertEqual("9router", config.provider)
        self.assertEqual("http://legacy.example/v1", config.base_url)
        self.assertEqual("legacy-key", config.api_key)
        self.assertEqual("oc/deepseek-v4-flash-free", config.model)
        warning_text = "\n".join(str(item.message) for item in captured)
        for legacy_name, canonical_name in (
            ("AI_PROVIDER", "LLM_PROVIDER"),
            ("AI_BASE_URL", "LLM_BASE_URL"),
            ("AI_API_KEY", "LLM_API_KEY"),
            ("AI_MODEL", "LLM_MODEL"),
        ):
            with self.subTest(legacy_name=legacy_name):
                self.assertIn(legacy_name, warning_text)
                self.assertIn(canonical_name, warning_text)


if __name__ == "__main__":
    unittest.main()
