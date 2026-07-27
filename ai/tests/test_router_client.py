from __future__ import annotations

import asyncio
import json
import unittest

import httpx

from app.clients import router as router_module
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

    def test_deepseek_429_retries_once_with_luna_and_records_trace(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            payloads.append(payload)
            if payload["model"] == "oc/deepseek-v4-flash-free":
                return httpx.Response(
                    429,
                    json={"error": {"message": "rate limited"}},
                )
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": '{"content":"CÃ³ phá»Ÿ."}'}}
                    ]
                },
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        async def run_request():
            with router_module.capture_model_attempts() as trace:
                result = await client.complete(
                    [{"role": "user", "content": "CÃ³ phá»Ÿ khÃ´ng?"}]
                )
            return result, trace.snapshot()

        result, trace = asyncio.run(run_request())

        self.assertEqual('{"content":"CÃ³ phá»Ÿ."}', result)
        self.assertEqual(
            [
                "oc/deepseek-v4-flash-free",
                "cx/gpt-5.6-luna-review",
            ],
            [payload["model"] for payload in payloads],
        )
        self.assertEqual(
            [
                ("oc/deepseek-v4-flash-free", "primary", "http_429"),
                ("cx/gpt-5.6-luna-review", "rate_limit_fallback", "success"),
            ],
            [(item.model, item.role, item.outcome) for item in trace],
        )

    def test_structured_429_rebuilds_luna_json_schema_payload(self) -> None:
        payloads: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            payloads.append(payload)
            if payload["model"] == "oc/deepseek-v4-flash-free":
                return httpx.Response(429, json={"error": {"message": "limited"}})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": '{"intent":"recommend"}'}}]},
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )
        schema = {
            "type": "object",
            "properties": {"intent": {"type": "string"}},
            "required": ["intent"],
            "additionalProperties": False,
        }

        result = asyncio.run(
            client.complete_structured(
                [{"role": "user", "content": "Gá»£i Ã½ mÃ³n"}],
                schema,
                "intent_probe",
            )
        )

        self.assertIn("recommend", result or "")
        luna_payload = payloads[-1]
        self.assertEqual("cx/gpt-5.6-luna-review", luna_payload["model"])
        self.assertEqual("json_schema", luna_payload["response_format"]["type"])
        self.assertEqual(
            "intent_probe",
            luna_payload["response_format"]["json_schema"]["name"],
        )
        self.assertEqual(schema, luna_payload["response_format"]["json_schema"]["schema"])
        self.assertFalse(
            any(
                "JSON Schema (intent_probe)" in message["content"]
                for message in luna_payload["messages"]
            )
        )

    def test_stream_429_reopens_once_with_luna_and_records_trace(self) -> None:
        models: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            models.append(payload["model"])
            if payload["model"] == "oc/deepseek-v4-flash-free":
                return httpx.Response(429, json={"error": {"message": "limited"}})
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content=(
                    'data: {"choices":[{"delta":{"content":"Xin "}}]}\n\n'
                    'data: {"choices":[{"delta":{"content":"chÃ o"}}]}\n\n'
                    "data: [DONE]\n\n"
                ).encode("utf-8"),
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        async def run_stream():
            with router_module.capture_model_attempts() as trace:
                chunks = [
                    chunk
                    async for chunk in client.complete_stream(
                        [{"role": "user", "content": "Xin chÃ o"}]
                    )
                ]
            return chunks, trace.snapshot()

        chunks, trace = asyncio.run(run_stream())

        self.assertEqual(["Xin ", "chÃ o"], chunks)
        self.assertEqual(
            [
                "oc/deepseek-v4-flash-free",
                "cx/gpt-5.6-luna-review",
            ],
            models,
        )
        self.assertEqual(
            ["http_429", "success"],
            [attempt.outcome for attempt in trace],
        )

    def test_malformed_primary_json_does_not_fallback_and_records_invalid_json(
        self,
    ) -> None:
        models: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            models.append(payload["model"])
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                content=b"not-json",
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        async def run_request():
            with router_module.capture_model_attempts() as trace:
                with self.assertRaises(json.JSONDecodeError):
                    await client.complete([{"role": "user", "content": "ping"}])
            return trace.snapshot()

        trace = asyncio.run(run_request())

        self.assertEqual(["oc/deepseek-v4-flash-free"], models)
        self.assertEqual(["invalid_json"], [attempt.outcome for attempt in trace])

    def test_primary_5xx_never_switches_to_luna(self) -> None:
        for status_code in (500, 502, 503, 504):
            with self.subTest(status_code=status_code):
                models: list[str] = []

                def handler(request: httpx.Request) -> httpx.Response:
                    payload = json.loads(request.content)
                    models.append(payload["model"])
                    return httpx.Response(
                        status_code,
                        json={"error": {"message": "provider unavailable"}},
                    )

                client = RouterClient(
                    "http://localhost:20128/v1",
                    "router-key",
                    "oc/deepseek-v4-flash-free",
                    30,
                    max_retry=0,
                    fallback_model="cx/gpt-5.6-luna-review",
                    fallback_enabled=True,
                    transport=httpx.MockTransport(handler),
                )

                with self.assertRaises(httpx.HTTPStatusError):
                    asyncio.run(
                        client.complete([{"role": "user", "content": "ping"}])
                    )

                self.assertEqual(["oc/deepseek-v4-flash-free"], models)

    def test_primary_timeout_never_switches_to_luna(self) -> None:
        models: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            models.append(payload["model"])
            raise httpx.ReadTimeout("timed out", request=request)

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            max_retry=0,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(httpx.ReadTimeout):
            asyncio.run(client.complete([{"role": "user", "content": "ping"}]))

        self.assertEqual(["oc/deepseek-v4-flash-free"], models)

    def test_non_deepseek_primary_429_never_switches_to_luna(self) -> None:
        models: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            models.append(payload["model"])
            return httpx.Response(429, json={"error": {"message": "limited"}})

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "cx/gpt-5.5",
            30,
            max_retry=0,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(httpx.HTTPStatusError):
            asyncio.run(client.complete([{"role": "user", "content": "ping"}]))

        self.assertEqual(["cx/gpt-5.5"], models)

    def test_luna_failure_stops_without_a_third_provider_attempt(self) -> None:
        models: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            models.append(payload["model"])
            if payload["model"] == "oc/deepseek-v4-flash-free":
                return httpx.Response(429, json={"error": {"message": "limited"}})
            return httpx.Response(503, json={"error": {"message": "unavailable"}})

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            max_retry=0,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        async def run_request():
            with router_module.capture_model_attempts() as trace:
                with self.assertRaises(httpx.HTTPStatusError):
                    await client.complete([{"role": "user", "content": "ping"}])
            return trace.snapshot()

        trace = asyncio.run(run_request())

        self.assertEqual(
            [
                "oc/deepseek-v4-flash-free",
                "cx/gpt-5.6-luna-review",
            ],
            models,
        )
        self.assertEqual(
            ["http_429", "http_503"],
            [attempt.outcome for attempt in trace],
        )

    def test_parallel_requests_do_not_share_model_attempt_traces(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            message = payload["messages"][-1]["content"]
            await asyncio.sleep(0)
            if payload["model"] == "oc/deepseek-v4-flash-free":
                return httpx.Response(429, json={"error": {"message": message}})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": message}}]},
            )

        client = RouterClient(
            "http://localhost:20128/v1",
            "router-key",
            "oc/deepseek-v4-flash-free",
            30,
            fallback_model="cx/gpt-5.6-luna-review",
            fallback_enabled=True,
            transport=httpx.MockTransport(handler),
        )

        async def one_request(message: str):
            with router_module.capture_model_attempts() as trace:
                result = await client.complete(
                    [{"role": "user", "content": message}]
                )
            return result, trace.snapshot()

        async def run_parallel():
            return await asyncio.gather(
                one_request("session-a"),
                one_request("session-b"),
            )

        results = asyncio.run(run_parallel())

        self.assertEqual(["session-a", "session-b"], [row[0] for row in results])
        for _, trace in results:
            self.assertEqual(2, len(trace))
            self.assertEqual(
                [
                    "oc/deepseek-v4-flash-free",
                    "cx/gpt-5.6-luna-review",
                ],
                [attempt.model for attempt in trace],
            )


if __name__ == "__main__":
    unittest.main()
