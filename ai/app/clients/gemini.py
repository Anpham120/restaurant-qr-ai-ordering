from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

import httpx


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RESTAURANT_CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "content": {"type": "string"},
        "suggested_cart_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "menu_item_id": {"type": "string"},
                    "name": {"type": "string"},
                    "price_vnd": {"type": ["number", "null"]},
                    "quantity": {"type": "integer"},
                    "reason": {"type": ["string", "null"]},
                    "requires_customer_confirmation": {"type": "boolean"},
                },
                "required": [
                    "menu_item_id",
                    "name",
                    "price_vnd",
                    "quantity",
                    "reason",
                    "requires_customer_confirmation",
                ],
                "additionalProperties": False,
            },
        },
        "guardrail_flags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["content", "suggested_cart_actions", "guardrail_flags"],
    "additionalProperties": False,
}


class GeminiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retry: int = 0,
        retry_delay_seconds: float = 0.5,
        *,
        http_client: httpx.AsyncClient | None = None,
        max_tokens: int = 700,
        reasoning_effort: str = "low",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retry = max(0, max_retry)
        self._retry_delay_seconds = max(0, retry_delay_seconds)
        self._max_tokens = max(64, max_tokens)
        self._reasoning_effort = reasoning_effort.strip() or "low"
        if http_client is not None:
            self._http_client = http_client
            self._owns_client = False
        elif transport is not None:
            self._http_client = httpx.AsyncClient(timeout=timeout_seconds, transport=transport)
            self._owns_client = True
        else:
            self._http_client = None
            self._owns_client = False

    def _build_payload(self, messages: list[dict[str, str]], *, stream: bool) -> dict:
        return {
            "model": self._model,
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": self._max_tokens,
            "reasoning_effort": self._reasoning_effort,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "restaurant_chat_response",
                    "strict": True,
                    "schema": RESTAURANT_CHAT_SCHEMA,
                },
            },
            "messages": messages,
        }

    async def _request_client(self) -> tuple[httpx.AsyncClient, bool]:
        if self._http_client is not None:
            return self._http_client, self._owns_client
        client = httpx.AsyncClient(timeout=self._timeout_seconds)
        return client, True

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        payload = self._build_payload(messages, stream=False)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client, owns_client = await self._request_client()
        try:
            for attempt in range(self._max_retry + 1):
                try:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                except (httpx.TimeoutException, httpx.ConnectError):
                    if attempt == self._max_retry:
                        raise
                    await asyncio.sleep(self._retry_delay_seconds * (2**attempt))
                    continue

                if response.status_code not in RETRYABLE_STATUS_CODES or attempt == self._max_retry:
                    response.raise_for_status()
                    data = response.json()
                    break
                await asyncio.sleep(self._retry_delay_seconds * (2**attempt))
        finally:
            if owns_client:
                await client.aclose()

        choices = data.get("choices") or []
        if not choices:
            return None

        first = choices[0]
        message = first.get("message") or {}
        content = message.get("content") or first.get("text")
        return content.strip() if isinstance(content, str) and content.strip() else None

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Stream completion token deltas via SSE."""

        payload = self._build_payload(messages, stream=True)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client, owns_client = await self._request_client()
        try:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except (ValueError, IndexError, KeyError):
                        continue
        finally:
            if owns_client:
                await client.aclose()
