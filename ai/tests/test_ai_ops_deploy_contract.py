from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class AiOpsDeployContractTests(unittest.TestCase):
    def test_compose_uses_canonical_provider_names_and_shares_internal_token(self) -> None:
        compose = (REPO_ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("CHAT_AI_PROVIDER:", compose)
        for name in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
            with self.subTest(name=name):
                self.assertIn(f"{name}:", compose)
        self.assertGreaterEqual(compose.count("AI_INTERNAL_TOKEN:"), 2)
        self.assertNotIn("AI_LLM_PROVIDER:", compose)

    def test_health_check_covers_database_ai_readiness_and_protected_safe_smoke(self) -> None:
        script = (REPO_ROOT / "deploy" / "scripts" / "health-check.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn(': "${AI_INTERNAL_TOKEN:?AI_INTERNAL_TOKEN is required}"', script)
        self.assertIn("/health/ready", script)
        self.assertIn("/ready", script)
        self.assertIn("Authorization: Bearer ${AI_INTERNAL_TOKEN}", script)
        self.assertIn('"message":"Xin chào"', script)
        self.assertIn("/v1/chat", script)
        self.assertIn('{"ok", "not_called"}', script)
        self.assertNotIn('payload.get("provider_available") is True', script)

    def test_staging_deploy_waits_for_ci_and_receives_ai_secrets(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "deploy-staging.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("uses: ./.github/workflows/ci.yml", workflow)
        self.assertIn("needs: quality-gate", workflow)
        self.assertIn("AI_INTERNAL_TOKEN: ${{ secrets.AI_INTERNAL_TOKEN }}", workflow)
        self.assertIn("LLM_API_KEY: ${{ secrets.NINE_ROUTER_API_KEY }}", workflow)
        self.assertIn("LLM_PROVIDER: 9router", workflow)
        self.assertNotIn("GEMINI", workflow.upper())

    def test_deploy_examples_document_canonical_ai_contract(self) -> None:
        for environment in ("staging", "production"):
            example = (
                REPO_ROOT / "deploy" / "env" / f"{environment}.example.env"
            ).read_text(encoding="utf-8")
            with self.subTest(environment=environment):
                for name in (
                    "CHAT_AI_PROVIDER",
                    "LLM_PROVIDER",
                    "LLM_BASE_URL",
                    "LLM_API_KEY",
                    "LLM_MODEL",
                    "AI_INTERNAL_TOKEN",
                ):
                    self.assertIn(f"{name}=", example)
                self.assertNotIn("AI_LLM_PROVIDER=", example)
                self.assertNotIn("gemini", example.casefold())


if __name__ == "__main__":
    unittest.main()
