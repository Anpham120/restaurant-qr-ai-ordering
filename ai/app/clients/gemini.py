from __future__ import annotations

import httpx


class GeminiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        payload = {
            "model": self._model,
            "stream": False,
            "temperature": 0.2,
            "messages": messages,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            transport=self._transport,
        ) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            return None

        first = choices[0]
        message = first.get("message") or {}
        content = message.get("content") or first.get("text")
        return content.strip() if isinstance(content, str) and content.strip() else None
