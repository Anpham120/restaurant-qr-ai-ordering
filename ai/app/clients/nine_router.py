from __future__ import annotations

import httpx


class NineRouterClient:
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        model: str,
        max_output_tokens: int,
    ) -> None:
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_output_tokens = max_output_tokens

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        payload = {
            "model": self._model,
            "stream": False,
            "temperature": 0.2,
            "max_tokens": self._max_output_tokens,
            "messages": messages,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        response = await self._http_client.post(
            f"{self._base_url}/chat/completions", json=payload, headers=headers
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
