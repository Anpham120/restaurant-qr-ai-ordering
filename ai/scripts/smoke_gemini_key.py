"""One-shot Gemini API connectivity check (does not print secrets)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ROOT))

from app.clients.gemini import GeminiClient  # noqa: E402
from app.config import load_config  # noqa: E402


async def main() -> int:
    config = load_config()
    print(f"model={config.model}")
    print(f"llm_enabled={config.llm_enabled}")
    if not config.llm_enabled:
        print("status=FAIL reason=missing_key_or_model")
        return 1

    client = GeminiClient(
        config.base_url,
        config.api_key,
        config.model,
        config.llm_timeout_seconds,
        max_retry=4,
        retry_delay_seconds=2.0,
    )
    try:
        raw = await client.complete([{"role": "user", "content": "Reply with the single word: pong"}])
    except Exception as exc:
        print(f"status=FAIL error_type={type(exc).__name__}")
        detail = str(exc)
        if hasattr(exc, "response") and exc.response is not None:
            resp = exc.response
            print(f"http_status={resp.status_code}")
            print(f"retry_after={resp.headers.get('Retry-After')}")
            try:
                body = resp.json()
                print(f"error_body={json.dumps(body.get('error', body), ensure_ascii=False)[:600]}")
            except Exception:
                print(f"error_body={resp.text[:600]}")
        print(f"error={detail[:800]}")
        return 1

    print(f"status=OK response_len={len(raw or '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
