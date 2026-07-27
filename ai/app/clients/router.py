from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Callable, Literal

import httpx


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class ModelAttempt:
    model: str
    role: Literal["primary", "rate_limit_fallback"]
    outcome: str
    status_code: int | None
    latency_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


class ModelAttemptCollector:
    def __init__(self) -> None:
        self._attempts: list[ModelAttempt] = []

    def record(self, attempt: ModelAttempt) -> None:
        self._attempts.append(attempt)

    def snapshot(self) -> tuple[ModelAttempt, ...]:
        return tuple(self._attempts)


_attempt_collector: ContextVar[ModelAttemptCollector | None] = ContextVar(
    "router_model_attempt_collector",
    default=None,
)


@contextmanager
def capture_model_attempts():
    collector = ModelAttemptCollector()
    token = _attempt_collector.set(collector)
    try:
        yield collector
    finally:
        _attempt_collector.reset(token)


class _PrimaryRateLimited(Exception):
    pass


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
        fallback_model: str | None = None,
        fallback_enabled: bool = False,
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
        self._fallback_model = (fallback_model or "").strip() or None
        self._fallback_enabled = bool(
            fallback_enabled
            and self._fallback_model
            and "deepseek" in self._model.casefold()
        )
        self._transport = transport
        if http_client is not None:
            self._http_client = http_client
            self._owns_client = False
        elif transport is not None:
            self._http_client = None
            self._owns_client = False
        else:
            self._http_client = None
            self._owns_client = False

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool,
        model: str | None = None,
    ) -> dict:
        selected_model = model or self._model
        payload: dict = {
            "model": selected_model,
            "stream": stream,
            "temperature": 0.2,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        if "deepseek" not in selected_model.casefold():
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
        client = httpx.AsyncClient(
            timeout=self._timeout_seconds,
            transport=self._transport,
        )
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

    @staticmethod
    def _record_attempt(
        *,
        model: str,
        role: Literal["primary", "rate_limit_fallback"],
        outcome: str,
        status_code: int | None,
        started: float,
    ) -> None:
        collector = _attempt_collector.get()
        if collector is None:
            return
        collector.record(
            ModelAttempt(
                model=model,
                role=role,
                outcome=outcome,
                status_code=status_code,
                latency_ms=round((perf_counter() - started) * 1000, 3),
            )
        )

    async def _post_payload(
        self,
        payload: dict,
        *,
        model: str,
        role: Literal["primary", "rate_limit_fallback"],
        allow_rate_limit_fallback: bool,
    ) -> dict:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        client, owns_client = await self._request_client()
        response: httpx.Response | None = None
        data: dict = {}
        try:
            for attempt in range(self._max_retry + 1):
                started = perf_counter()
                try:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                except httpx.TimeoutException:
                    self._record_attempt(
                        model=model,
                        role=role,
                        outcome="timeout",
                        status_code=None,
                        started=started,
                    )
                    if attempt == self._max_retry:
                        raise
                    await asyncio.sleep(self._retry_wait_seconds(None, attempt))
                    continue
                except httpx.ConnectError:
                    self._record_attempt(
                        model=model,
                        role=role,
                        outcome="connect_error",
                        status_code=None,
                        started=started,
                    )
                    if attempt == self._max_retry:
                        raise
                    await asyncio.sleep(self._retry_wait_seconds(None, attempt))
                    continue

                if (
                    response.status_code == 429
                    and allow_rate_limit_fallback
                    and self._fallback_enabled
                ):
                    self._record_attempt(
                        model=model,
                        role=role,
                        outcome="http_429",
                        status_code=429,
                        started=started,
                    )
                    raise _PrimaryRateLimited

                if response.status_code not in RETRYABLE_STATUS_CODES or attempt == self._max_retry:
                    if response.is_error:
                        self._record_attempt(
                            model=model,
                            role=role,
                            outcome=f"http_{response.status_code}",
                            status_code=response.status_code,
                            started=started,
                        )
                        response.raise_for_status()
                    try:
                        data = response.json()
                    except json.JSONDecodeError:
                        self._record_attempt(
                            model=model,
                            role=role,
                            outcome="invalid_json",
                            status_code=response.status_code,
                            started=started,
                        )
                        raise
                    self._record_attempt(
                        model=model,
                        role=role,
                        outcome="success",
                        status_code=response.status_code,
                        started=started,
                    )
                    break
                self._record_attempt(
                    model=model,
                    role=role,
                    outcome=f"http_{response.status_code}",
                    status_code=response.status_code,
                    started=started,
                )
                await asyncio.sleep(self._retry_wait_seconds(response, attempt))
        finally:
            if owns_client:
                await client.aclose()
        return data

    async def _post_chat_completions(
        self,
        payload_factory: Callable[[str], dict],
    ) -> dict:
        try:
            return await self._post_payload(
                payload_factory(self._model),
                model=self._model,
                role="primary",
                allow_rate_limit_fallback=True,
            )
        except _PrimaryRateLimited:
            if not self._fallback_model:
                raise
            return await self._post_payload(
                payload_factory(self._fallback_model),
                model=self._fallback_model,
                role="rate_limit_fallback",
                allow_rate_limit_fallback=False,
            )

    async def complete(self, messages: list[dict[str, str]]) -> str | None:
        data = await self._post_chat_completions(
            lambda model: self._build_payload(
                messages,
                stream=False,
                model=model,
            )
        )
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

        def build_structured_payload(model: str) -> dict:
            is_deepseek = "deepseek" in model.casefold()
            request_messages = [dict(message) for message in messages]
            if is_deepseek:
                schema_instruction = (
                    "Return exactly one JSON object that validates against this schema. "
                    "Do not add markdown or fields outside the schema.\n"
                    f"JSON Schema ({schema_name}): "
                    f"{json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}"
                )
                request_messages.insert(
                    0,
                    {"role": "system", "content": schema_instruction},
                )
            payload: dict = {
                "model": model,
                "stream": False,
                "temperature": temperature,
                "max_tokens": max(64, max_tokens),
                "messages": request_messages,
                "reasoning_effort": "none",
                "response_format": (
                    {"type": "json_object"}
                    if is_deepseek
                    else {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema_name,
                            "strict": True,
                            "schema": schema,
                        },
                    }
                ),
            }
            if not is_deepseek:
                payload["reasoning_effort"] = self._reasoning_effort
            return payload

        data = await self._post_chat_completions(build_structured_payload)
        choices = data.get("choices") or []
        if not choices:
            return None
        return self._extract_choice_text(choices[0])

    async def complete_stream(
        self,
        messages: list[dict[str, str]],
    ) -> AsyncIterator[str]:
        """Stream completion token deltas via SSE."""

        headers = {"Authorization": f"Bearer {self._api_key}"}
        operations: list[
            tuple[str, Literal["primary", "rate_limit_fallback"]]
        ] = [(self._model, "primary")]
        if self._fallback_enabled and self._fallback_model:
            operations.append((self._fallback_model, "rate_limit_fallback"))

        for operation_index, (model, role) in enumerate(operations):
            payload = self._build_payload(messages, stream=True, model=model)
            client, owns_client = await self._request_client()
            started = perf_counter()
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                ) as response:
                    if (
                        response.status_code == 429
                        and operation_index == 0
                        and len(operations) == 2
                    ):
                        self._record_attempt(
                            model=model,
                            role=role,
                            outcome="http_429",
                            status_code=429,
                            started=started,
                        )
                        continue
                    if response.is_error:
                        self._record_attempt(
                            model=model,
                            role=role,
                            outcome=f"http_{response.status_code}",
                            status_code=response.status_code,
                            started=started,
                        )
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
                            delta = (
                                delta_obj.get("content")
                                or delta_obj.get("reasoning_content")
                                or ""
                            )
                            if delta:
                                yield delta
                        except (ValueError, IndexError, KeyError):
                            continue
                    self._record_attempt(
                        model=model,
                        role=role,
                        outcome="success",
                        status_code=response.status_code,
                        started=started,
                    )
                    return
            except httpx.TimeoutException:
                self._record_attempt(
                    model=model,
                    role=role,
                    outcome="timeout",
                    status_code=None,
                    started=started,
                )
                raise
            except httpx.ConnectError:
                self._record_attempt(
                    model=model,
                    role=role,
                    outcome="connect_error",
                    status_code=None,
                    started=started,
                )
                raise
            finally:
                if owns_client:
                    await client.aclose()
