from __future__ import annotations

import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.responses import JSONResponse

import app.main as main
from app.schemas import ChatRequest


class _AssistantState:
    def __init__(self, *, ready: bool) -> None:
        self.is_ready = ready
        self.retrieval_method = "hybrid"


class AiInternalAuthReadinessTests(unittest.TestCase):
    def test_timeout_fallback_preserves_v2_decision_and_session_state(self) -> None:
        request = ChatRequest(
            contract_version="v2",
            message="Còn món khác?",
            session_state={
                "facts": [{"key": "party_size", "value": 4}],
                "constraints": {"party_size": 4},
                "suggested_menu_item_ids": ["m_001"],
                "rolling_summary": "Khách đi bốn người.",
                "memory_version": "v2",
            },
        )

        response = main._build_timeout_response(request)  # noqa: SLF001

        self.assertEqual("v2", response["contract_version"])
        self.assertEqual("unavailable", response["provider_status"])
        self.assertEqual("abstain", response["decision"]["route"])
        self.assertFalse(response["decision"]["evidence_sufficient"])
        self.assertEqual("request_budget_exceeded", response["decision"]["abstain_reason"])
        self.assertEqual([], response["claims"])
        self.assertEqual(["m_001"], response["session_updates"]["suggested_menu_item_ids"])
        self.assertEqual(4, response["session_updates"]["constraints"]["party_size"])

    def test_internal_auth_fails_closed_when_token_is_not_configured(self) -> None:
        with patch.object(main, "config", replace(main.config, internal_token="")):
            with self.assertRaises(HTTPException) as error:
                main.require_internal_token("")

        self.assertEqual(503, error.exception.status_code)

    def test_internal_auth_rejects_invalid_token_and_accepts_valid_bearer(self) -> None:
        with patch.object(main, "config", replace(main.config, internal_token="secret")):
            with self.assertRaises(HTTPException) as error:
                main.require_internal_token("Bearer wrong")
            self.assertEqual(401, error.exception.status_code)

            main.require_internal_token("Bearer secret")

    def test_every_v1_route_is_protected_while_health_routes_are_public(self) -> None:
        routes = {
            route.path: route
            for route in main.app.routes
            if hasattr(route, "dependant")
        }

        protected_paths = [path for path in routes if path.startswith("/v1/")]
        self.assertGreater(len(protected_paths), 0)
        for path in protected_paths:
            dependency_calls = [dependency.call for dependency in routes[path].dependant.dependencies]
            with self.subTest(path=path):
                self.assertIn(main.require_internal_token, dependency_calls)

        for path in ("/health", "/ready"):
            dependency_calls = [dependency.call for dependency in routes[path].dependant.dependencies]
            with self.subTest(path=path):
                self.assertNotIn(main.require_internal_token, dependency_calls)

    def test_readiness_fails_when_retriever_provider_or_internal_auth_is_unavailable(self) -> None:
        invalid_config = replace(
            main.config,
            api_key="",
            internal_token="",
        )
        with (
            patch.object(main, "config", invalid_config),
            patch.object(main, "assistant", _AssistantState(ready=False)),
        ):
            response = main.ready()

        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(503, response.status_code)
        payload = json.loads(response.body)
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["dependencies"]["retriever"]["ready"])
        self.assertFalse(payload["dependencies"]["provider_config"]["ready"])
        self.assertFalse(payload["dependencies"]["internal_auth"]["ready"])

    def test_readiness_succeeds_only_when_all_local_dependencies_are_ready(self) -> None:
        valid_config = replace(
            main.config,
            provider="9router",
            base_url="http://router.example/v1",
            api_key="provider-key",
            model="cx/gpt-5.5",
            internal_token="internal-secret",
        )
        with (
            patch.object(main, "config", valid_config),
            patch.object(main, "assistant", _AssistantState(ready=True)),
        ):
            response = main.ready()

        self.assertIsInstance(response, JSONResponse)
        self.assertEqual(200, response.status_code)
        payload = json.loads(response.body)
        self.assertTrue(payload["ready"])
        self.assertTrue(all(item["ready"] for item in payload["dependencies"].values()))


if __name__ == "__main__":
    unittest.main()
