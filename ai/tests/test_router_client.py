from __future__ import annotations

import asyncio
import json
import unittest

import httpx

from app.clients.router import RouterClient


class RouterClientTests(unittest.TestCase):
    def test_deepseek_payload_disables_reasoning_and_reserves_output_tokens(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual({"type": "json_object"}, payload["response_format"])
            self.assertEqual(payload["reasoning_effort"], "none")
            self.assertEqual(payload["max_tokens"], 1200)
            return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "ping"}]))
        self.assertEqual(result, "pong")

    def test_gpt55_calls_9router_openai_compatible_endpoint(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://localhost:20128/v1/chat/completions",
            )
            self.assertEqual(request.headers["Authorization"], "Bearer router-key")
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "cx/gpt-5.5")
            self.assertEqual(payload["reasoning_effort"], "low")
            self.assertEqual({"type": "json_object"}, payload["response_format"])
            self.assertEqual(payload["messages"], [{"role": "user", "content": "Xin chào"}])
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": " Chào bạn "}}]},
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "cx/gpt-5.5",
            30,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "Xin chào"}]))

        self.assertEqual(result, "Chào bạn")

    def test_retries_429_with_retry_after_header(self) -> None:
        attempts = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "0"},
                    json={"error": {"message": "rate limited"}},
                )
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "cx/gpt-5.5",
            30,
            max_retry=2,
            retry_delay_seconds=0,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "Xin chào"}]))

        self.assertEqual(result, "OK")
        self.assertEqual(attempts, 2)

    def test_retries_429_parses_retry_delay_from_error_body(self) -> None:
        attempts = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(
                    429,
                    json={
                        "error": {
                            "message": "Quota exceeded. Please retry in 0.01s.",
                        }
                    },
                )
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "cx/gpt-5.5",
            30,
            max_retry=2,
            retry_delay_seconds=0,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "Xin chào"}]))

        self.assertEqual(result, "OK")
        self.assertEqual(attempts, 2)

    def test_retries_503_then_succeeds(self) -> None:
        attempts = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})
            return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "cx/gpt-5.5",
            30,
            max_retry=1,
            retry_delay_seconds=0,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "Xin chào"}]))

        self.assertEqual(result, "OK")
        self.assertEqual(attempts, 2)

    def test_complete_structured_sends_json_schema(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual(payload["temperature"], 0.0)
            self.assertEqual(payload["max_tokens"], 150)
            response_format = payload["response_format"]
            self.assertEqual(response_format["json_schema"]["name"], "intent_probe")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"intent":"recommend"}'}}]},
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "cx/gpt-5.5",
            30,
            transport=httpx.MockTransport(handler),
        )
        schema = {
            "type": "object",
            "properties": {"intent": {"type": "string"}},
            "required": ["intent"],
        }
        result = asyncio.run(
            client.complete_structured(
                [{"role": "user", "content": "ping"}],
                schema,
                "intent_probe",
                max_tokens=150,
            )
        )
        self.assertIn("recommend", result or "")

    def test_deepseek_structured_uses_json_object_and_embeds_schema(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertEqual({"type": "json_object"}, payload["response_format"])
            self.assertEqual("none", payload["reasoning_effort"])
            self.assertNotIn("json_schema", payload["response_format"])
            system_text = "\n".join(
                message["content"]
                for message in payload["messages"]
                if message["role"] == "system"
            )
            self.assertIn('"required":["intent"]', system_text)
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"intent":"recommend"}'}}]},
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            transport=httpx.MockTransport(handler),
        )
        schema = {
            "type": "object",
            "properties": {"intent": {"type": "string"}},
            "required": ["intent"],
        }

        result = asyncio.run(
            client.complete_structured(
                [{"role": "user", "content": "ping"}],
                schema,
                "intent_probe",
            )
        )

        self.assertIn("recommend", result or "")

    def test_complete_falls_back_to_reasoning_content(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "reasoning_content": '{"content":"ok","suggested_cart_actions":[],"guardrail_flags":[]}',
                            }
                        }
                    ]
                },
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "ping"}]))
        self.assertIn('"content":"ok"', result or "")


if __name__ == "__main__":
    unittest.main()
