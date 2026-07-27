# -*- coding: utf-8 -*-
"""Minimal 9router connectivity smoke (no secrets in logs)."""
from __future__ import annotations

import argparse
import json
import sys

ALLOWED_MODELS = frozenset(
    {"cx/gpt-5.5", "cx/gpt-5.6-luna-review", "oc/deepseek-v4-flash-free"}
)


def build_smoke_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": 'Reply with JSON only: {"status":"pong"}',
        }
    ]


def parse_smoke_response(raw: str) -> str:
    payload = json.loads(raw)
    status = payload.get("status")
    if status != "pong":
        raise ValueError(f"unexpected smoke status: {status!r}")
    return str(status)


def parse_smoke_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="9router smoke")
    parser.add_argument("--model", default="cx/gpt-5.6-luna-review")
    args = parser.parse_args(argv)
    if args.model not in ALLOWED_MODELS:
        print(f"Unsupported model: {args.model}", file=sys.stderr)
        raise SystemExit(2)
    return args


def main(argv: list[str] | None = None) -> int:
    parse_smoke_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
