import asyncio
import json
import unittest
from pathlib import Path

import httpx

from app.clients.router import RouterClient
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

    def test_429_fallback_reports_effective_luna_route_without_logging_prompt(
        self,
    ) -> None:
        secret = "router-secret-never-log"
        prompt = "Gợi ý món nhẹ cho tôi"

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            if payload["model"] == "oc/deepseek-v4-flash-free":
                return httpx.Response(429, json={"error": {"message": "limited"}})
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "content": "Mình gợi ý Nem rán Hà Nội.",
                                        "suggested_cart_actions": [
                                            {
                                                "menu_item_id": "m_nem",
                                                "name": "Nem rán Hà Nội",
                                                "price_vnd": 65000,
                                                "quantity": 1,
                                            }
                                        ],
                                        "claims": [
                                            {
                                                "text": "Nem rán Hà Nội có trong thực đơn.",
                                                "evidence_ids": ["m_nem"],
                                            }
                                        ],
                                        "guardrail_flags": [],
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                },
            )

        config = AiServiceConfig(
            provider="9router",
            base_url="http://localhost:20128/v1",
            api_key=secret,
            model="oc/deepseek-v4-flash-free",
            llm_timeout_seconds=2,
            request_budget_seconds=4,
            max_retry=0,
            max_tokens=700,
            reasoning_effort="low",
            knowledge_base_path=Path(__file__).resolve().parents[1] / "knowledge-base",
            top_k=3,
            retrieval_method="bm25",
            llm_intent_classification_enabled=False,
            rate_limit_fallback_model="cx/gpt-5.6-luna-review",
            rate_limit_fallback_enabled=True,
        )
        client = RouterClient(
            config.base_url,
            config.api_key,
            config.model,
            config.llm_timeout_seconds,
            max_retry=0,
            fallback_model=config.rate_limit_fallback_model,
            fallback_enabled=config.rate_limit_fallback_enabled,
            transport=httpx.MockTransport(handler),
        )
        service = AiAssistantService(config, llm_client=client)

        with self.assertLogs("app.services.assistant", level="INFO") as captured:
            response = asyncio.run(
                service.chat(
                    {
                        "message": prompt,
                        "history": [],
                        "menu_items": [
                            {
                                "id": "m_nem",
                                "name": "Nem rán Hà Nội",
                                "description": "Khai vị",
                                "category_name": "Khai vị",
                                "category_id": "cat_appetizer",
                                "price_vnd": 65000,
                                "is_available": True,
                            }
                        ],
                        "table_code": "T01",
                    }
                )
            )

        self.assertEqual("cx/gpt-5.6-luna-review", response["model"])
        self.assertTrue(response["provider_available"])
        self.assertEqual("available", response["provider_status"])
        self.assertEqual(
            "oc/deepseek-v4-flash-free",
            response["primary_model"],
        )
        self.assertEqual(
            "cx/gpt-5.6-luna-review",
            response["fallback_model"],
        )
        self.assertTrue(response["fallback_used"])
        self.assertEqual("rate_limit_429", response["fallback_reason"])
        self.assertEqual(
            ["http_429", "success"],
            [attempt["outcome"] for attempt in response["model_attempts"]],
        )
        log_output = "\n".join(captured.output)
        self.assertIn("pipeline_profile=llm_first_v1", log_output)
        self.assertIn("model_route=", log_output)
        self.assertIn("resolved_menu_item_ids=", log_output)
        self.assertIn("verifier_result=", log_output)
        self.assertNotIn(secret, log_output)
        self.assertNotIn(prompt, log_output)
