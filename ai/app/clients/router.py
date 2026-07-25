from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator

import httpx


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class RouterClient:
    """Minimal OpenAI-compatible client for GPT-5.5/DeepSeek via 9router."""

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
        payload: dict = {
            "model": self._model,
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if "deepseek" not in self._model.casefold():
            payload["reasoning_effort"] = self._reasoning_effort
        else:
            # Some DeepSeek routes default to thinking mode and
            # can exhaust max_tokens on reasoning_content, leaving content empty.
            payload["reasoning_effort"] = "none"
            payload["max_tokens"] = max(self._max_tokens, 1200)
        return payload

    @staticmethod
    def _extract_choice_text(choice: dict) -> str | None:
        message = choice.get("message") or {}
        for key in ("content", "text", "reasoning_content"):
            value = message.get(key) if key != "text" else choice.get("text")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    async def _request_client(self) -> tuple[httpx.AsyncClient, bool]:
        if self._http_client is not None:
            return self._http_client, self._owns_client
        client = httpx.AsyncClient(timeout=self._timeout_seconds)
        return client, True

    def _retry_wait_seconds(self, response: httpx.Response | None, attempt: int) -> float:
        """Backoff for retryable HTTP statuses; 429 waits longer and honors Retry-After."""

        if response is not None and response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return max(float(retry_after), 5.0)
                except ValueError:
                    pass
            try:
                body = response.json()
                message = str((body.get("error") or {}).get("message") or "")
                match = re.search(r"retry in ([0-9.]+)s", message, re.IGNORECASE)
                if match:
                    return max(float(match.group(1)) + 1.0, 5.0)
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
            return max(10.0, self._retry_delay_seconds * (2**attempt))

        return self._retry_delay_seconds * (2**attempt)

    async def _post_chat_completions(self, payload: dict) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client, owns_client = await self._request_client()
        response: httpx.Response | None = None
        data: dict = {}
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
                    await asyncio.sleep(self._retry_wait_seconds(None, attempt))
                    continue

                if response.status_code not in RETRYABLE_STATUS_CODES or attempt == self._max_retry:
                    response.raise_for_status()
                    data = response.json()
                    break
                await asyncio.sleep(self._retry_wait_seconds(response, attempt))
        finally:
            if owns_client:
                await client.aclose()
        return data

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        payload = self._build_payload(messages, stream=False)
        data = await self._post_chat_completions(payload)
        choices = data.get("choices") or []
        if not choices:
            return None
        return self._extract_choice_text(choices[0])

    async def complete_structured(
        self,
        messages: list[dict[str, str]],
        schema: dict,
        schema_name: str,
        *,
        max_tokens: int = 150,
        temperature: float = 0.0,
    ) -> str | None:
        """Return raw JSON text from a compact structured-output call."""

        payload: dict = {
            "model": self._model,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max(64, max_tokens),
            "messages": messages,
            "reasoning_effort": "none",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        if "deepseek" not in self._model.casefold():
            payload["reasoning_effort"] = self._reasoning_effort
        data = await self._post_chat_completions(payload)
        choices = data.get("choices") or []
        if not choices:
            return None
        return self._extract_choice_text(choices[0])

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
                        delta_obj = chunk.get("choices", [{}])[0].get("delta", {})
                        delta = delta_obj.get("content") or delta_obj.get("reasoning_content") or ""
                        if delta:
                            yield delta
                    except (ValueError, IndexError, KeyError):
                        continue
        finally:
            if owns_client:
                await client.aclose()
