from __future__ import annotations

import asyncio
import json
import unittest

import httpx

from app.clients.gemini import GeminiClient


class GeminiClientTests(unittest.TestCase):
    def test_openai_compatible_payload_omits_gemini_only_fields(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            self.assertNotIn("response_format", payload)
            self.assertEqual(payload["reasoning_effort"], "none")
            self.assertEqual(payload["max_tokens"], 1200)
            return httpx.Response(200, json={"choices": [{"message": {"content": "pong"}}]})

        client = GeminiClient(
            "http://localhost:20128/v1",
            "router-key",
            "gcli/grok-4.5",
            30,
            use_gemini_features=False,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "ping"}]))
        self.assertEqual(result, "pong")

    def test_complete_calls_official_openai_compatible_endpoint(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            )
            self.assertEqual(request.headers["Authorization"], "Bearer test-gemini-key")
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "gemini-3.5-flash")
            self.assertEqual(payload["reasoning_effort"], "low")
            response_format = payload["response_format"]
            self.assertEqual(response_format["type"], "json_schema")
            self.assertTrue(response_format["json_schema"]["strict"])
            self.assertEqual(
                response_format["json_schema"]["schema"]["required"],
                ["content", "suggested_cart_actions", "guardrail_flags"],
            )
            self.assertEqual(payload["messages"], [{"role": "user", "content": "Xin chào"}])
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": " Chào bạn "}}]},
            )

        client = GeminiClient(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "test-gemini-key",
            "gemini-3.5-flash",
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

        client = GeminiClient(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "test-gemini-key",
            "gemini-3.5-flash",
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

        client = GeminiClient(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "test-gemini-key",
            "gemini-3.5-flash",
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

        client = GeminiClient(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "test-gemini-key",
            "gemini-3.5-flash",
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

        client = GeminiClient(
            "http://localhost:20128/v1",
            "router-key",
            "gcli/grok-4.5",
            30,
            use_gemini_features=False,
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

        client = GeminiClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            use_gemini_features=False,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "ping"}]))
        self.assertIn('"content":"ok"', result or "")


if __name__ == "__main__":
    unittest.main()
