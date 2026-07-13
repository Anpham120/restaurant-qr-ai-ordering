from __future__ import annotations

import asyncio

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
        max_retry: int = 1,
        retry_delay_seconds: float = 0.5,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_retry = max(0, max_retry)
        self._retry_delay_seconds = max(0, retry_delay_seconds)
        self._transport = transport

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        payload = {
            "model": self._model,
            "stream": False,
            "temperature": 0.2,
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
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            for attempt in range(self._max_retry + 1):
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                if response.status_code not in RETRYABLE_STATUS_CODES or attempt == self._max_retry:
                    response.raise_for_status()
                    data = response.json()
                    break
                await asyncio.sleep(self._retry_delay_seconds * (2**attempt))

        choices = data.get("choices") or []
        if not choices:
            return None

        first = choices[0]
        message = first.get("message") or {}
        content = message.get("content") or first.get("text")
        return content.strip() if isinstance(content, str) and content.strip() else None
