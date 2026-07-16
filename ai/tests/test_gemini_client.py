from __future__ import annotations

import asyncio
import json
import unittest

import httpx

from app.clients.gemini import GeminiClient


class GeminiClientTests(unittest.TestCase):
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

    def test_v32_retries_retryable_status_then_succeeds(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
