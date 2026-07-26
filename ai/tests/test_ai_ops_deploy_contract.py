from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class AiOpsDeployContractTests(unittest.TestCase):
    def test_compose_uses_canonical_provider_names_and_shares_internal_token(self) -> None:
        compose = (REPO_ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("CHAT_AI_PROVIDER:", compose)
        for name in (
            "LLM_PROVIDER",
            "LLM_BASE_URL",
            "LLM_API_KEY",
            "LLM_MODEL",
            "LLM_RATE_LIMIT_FALLBACK_MODEL",
            "LLM_RATE_LIMIT_FALLBACK_ENABLED",
            "LLM_TIMEOUT_SECONDS",
            "AI_REQUEST_BUDGET_SECONDS",
        ):
            with self.subTest(name=name):
                self.assertIn(f"{name}:", compose)
        self.assertGreaterEqual(compose.count("AI_INTERNAL_TOKEN:"), 2)
        self.assertNotIn("AI_LLM_PROVIDER:", compose)

    def test_health_check_covers_database_ai_readiness_and_protected_safe_smoke(self) -> None:
        script = (REPO_ROOT / "deploy" / "scripts" / "health-check.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn(': "${AI_INTERNAL_TOKEN:?AI_INTERNAL_TOKEN is required}"', script)
        self.assertIn(
            ': "${LLM_RATE_LIMIT_FALLBACK_MODEL:?LLM_RATE_LIMIT_FALLBACK_MODEL is required}"',
            script,
        )
        self.assertIn(
            ': "${LLM_RATE_LIMIT_FALLBACK_ENABLED:?LLM_RATE_LIMIT_FALLBACK_ENABLED is required}"',
            script,
        )
        self.assertIn("/health/ready", script)
        self.assertIn("/ready", script)
        self.assertIn("model_policy", script)
        self.assertIn('policy.get("primary_model") == expected_model', script)
        self.assertIn(
            'policy.get("fallback_model") == expected_fallback_model',
            script,
        )
        self.assertIn(
            'bool(policy.get("fallback_enabled")) is expected_fallback_enabled',
            script,
        )
        self.assertIn('policy.get("fallback_trigger") == "http_429"', script)
        self.assertIn('int(policy.get("max_fallbacks_per_operation") or 0) == 1', script)
        self.assertIn("Authorization: Bearer ${AI_INTERNAL_TOKEN}", script)
        self.assertIn('"message":"Xin chào"', script)
        self.assertIn("/v1/chat", script)
        self.assertIn('{"ok", "not_called"}', script)
        self.assertIn(
            'assert payload.get("primary_model") == expected_model, payload',
            script,
        )
        self.assertIn(
            'assert payload.get("fallback_model") == expected_fallback_model, payload',
            script,
        )
        self.assertNotIn('assert payload.get("model") == expected_model, payload', script)
        self.assertNotIn('payload.get("provider_available") is True', script)
        self.assertIn('run_semantic_probe "pho-list" "Nhà hàng mình có những món phở gì nhỉ?"', script)
        self.assertIn('run_semantic_probe "pho-recommend" "Gợi ý cho mình món phở tại nhà hàng đi"', script)
        self.assertIn('run_semantic_probe "nhau" "Mình có món nhậu không?"', script)

    def test_deploy_vps_requires_and_writes_fallback_model_policy(self) -> None:
        script = (REPO_ROOT / "deploy" / "scripts" / "deploy-vps.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("LLM_RATE_LIMIT_FALLBACK_MODEL", script)
        self.assertIn("LLM_RATE_LIMIT_FALLBACK_ENABLED", script)
        self.assertIn(
            'LLM_RATE_LIMIT_FALLBACK_MODEL=$(env_quote "$LLM_RATE_LIMIT_FALLBACK_MODEL")',
            script,
        )
        self.assertIn(
            'LLM_RATE_LIMIT_FALLBACK_ENABLED=$(env_quote "$LLM_RATE_LIMIT_FALLBACK_ENABLED")',
            script,
        )
        self.assertIn(
            'LLM_TIMEOUT_SECONDS=$(env_quote "${LLM_TIMEOUT_SECONDS:-${AI_TIMEOUT_SECONDS:-30}}")',
            script,
        )
        self.assertIn(
            'AI_REQUEST_BUDGET_SECONDS=$(env_quote "${AI_REQUEST_BUDGET_SECONDS:-45}")',
            script,
        )

    def test_deploy_uses_approved_winner_and_research_owns_router_tunnel(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "deploy-staging.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("uses: ./.github/workflows/ci.yml", workflow)
        self.assertIn("needs: quality-gate", workflow)
        self.assertIn("AI_INTERNAL_TOKEN: ${{ secrets.AI_INTERNAL_TOKEN }}", workflow)
        self.assertIn("LLM_API_KEY: ${{ secrets.NINE_ROUTER_API_KEY }}", workflow)
        self.assertIn("LLM_PROVIDER: 9router", workflow)
        self.assertIn(
            "LLM_RATE_LIMIT_FALLBACK_MODEL: cx/gpt-5.6-luna-review",
            workflow,
        )
        self.assertIn('LLM_RATE_LIMIT_FALLBACK_ENABLED: "true"', workflow)
        self.assertIn('LLM_TIMEOUT_SECONDS: "30"', workflow)
        self.assertIn('AI_REQUEST_BUDGET_SECONDS: "45"', workflow)
        self.assertNotIn("GEMINI", workflow.upper())
        production_workflow = (
            REPO_ROOT / ".github" / "workflows" / "deploy-production.yml"
        ).read_text(encoding="utf-8")
        for deploy_workflow in (workflow, production_workflow):
            self.assertIn("approved/pipeline_selection.json", deploy_workflow)
            self.assertIn("--verify-current-research-inputs", deploy_workflow)
            self.assertIn("--verify-current-canonical-dataset", deploy_workflow)
            self.assertIn("--expected-primary-model", deploy_workflow)
            self.assertIn("--expected-fallback-model", deploy_workflow)
            self.assertIn("--expected-fallback-trigger", deploy_workflow)
            self.assertIn("--expected-max-fallbacks", deploy_workflow)
            self.assertIn("--require-fallback-enabled", deploy_workflow)
            self.assertNotIn("Open secure 9router tunnel", deploy_workflow)
            self.assertIn('LLM_TIMEOUT_SECONDS: "30"', deploy_workflow)
            self.assertIn('AI_REQUEST_BUDGET_SECONDS: "45"', deploy_workflow)

        research_workflow = (
            REPO_ROOT / ".github" / "workflows" / "research-pipeline-selection.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("-L 20128:127.0.0.1:20128", research_workflow)
        self.assertIn("Open secure 9router tunnel", research_workflow)
        self.assertIn("Diagnose 9router origin", research_workflow)
        self.assertIn("read -r ROUTER_API_KEY", research_workflow)
        self.assertIn("emit_router_origin_probe | ssh", research_workflow)
        self.assertIn("export ROUTER_API_KEY; bash -s", research_workflow)
        self.assertIn("9router origin listener=", research_workflow)
        self.assertIn("9router docker candidates=", research_workflow)
        self.assertIn("9router systemd candidates=", research_workflow)
        self.assertIn("Preflight 9router HTTP readiness", research_workflow)
        self.assertIn("/v1/models", research_workflow)
        self.assertIn("oc/deepseek-v4-flash-free", research_workflow)
        self.assertIn("run_pipeline_profile_eval.py", research_workflow)
        self.assertIn(
            "LLM_RATE_LIMIT_FALLBACK_MODEL: cx/gpt-5.6-luna-review",
            research_workflow,
        )
        self.assertIn('LLM_RATE_LIMIT_FALLBACK_ENABLED: "true"', research_workflow)
        self.assertIn("if-no-files-found: ignore", research_workflow)
        # The research result is eligible to select production only when every
        # non-profile runtime control is identical to the deployed service.
        for runtime_control in (
            'LLM_TIMEOUT_SECONDS: "30"',
            'AI_REQUEST_BUDGET_SECONDS: "45"',
            'AI_MAX_RETRY: "0"',
            'AI_MAX_TOKENS: "700"',
            'AI_REASONING_EFFORT: low',
        ):
            with self.subTest(runtime_control=runtime_control):
                self.assertIn(runtime_control, research_workflow)

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
                    "LLM_RATE_LIMIT_FALLBACK_MODEL",
                    "LLM_RATE_LIMIT_FALLBACK_ENABLED",
                    "AI_INTERNAL_TOKEN",
                ):
                    self.assertIn(f"{name}=", example)
                self.assertNotIn("AI_LLM_PROVIDER=", example)
                self.assertNotIn("gemini", example.casefold())

    def test_router_recovery_is_explicit_targeted_and_verifies_listener(self) -> None:
        workflow = (
            REPO_ROOT / ".github" / "workflows" / "recover-9router.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("RESTART_9ROUTER", workflow)
        self.assertIn("environment: staging", workflow)
        self.assertIn("sudo -n systemctl restart 9router.service", workflow)
        self.assertIn("systemctl is-active --quiet 9router.service", workflow)
        self.assertIn("9router listener is ready", workflow)
        self.assertNotIn("docker restart", workflow)


if __name__ == "__main__":
    unittest.main()
