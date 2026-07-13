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
            self.assertEqual(payload["model"], "gemini-2.5-flash")
            self.assertEqual(payload["messages"], [{"role": "user", "content": "Xin chào"}])
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": " Chào bạn "}}]},
            )

        client = GeminiClient(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "test-gemini-key",
            "gemini-2.5-flash",
            30,
            transport=httpx.MockTransport(handler),
        )

        result = asyncio.run(client.complete([{"role": "user", "content": "Xin chào"}]))

        self.assertEqual(result, "Chào bạn")


if __name__ == "__main__":
    unittest.main()
