"""Shared smoke-case loaders for CI retrieval and legacy guardrail eval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

AI_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"
SMOKE_RETRIEVAL_PATH = AI_ROOT / "evaluation" / "golden" / "smoke_retrieval.jsonl"
LEGACY_CSV_PATH = AI_ROOT / "evaluation" / "golden_questions.csv"


def load_jsonl_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def load_smoke_retrieval_cases() -> list[dict[str, Any]]:
    if SMOKE_RETRIEVAL_PATH.is_file():
        return load_jsonl_cases(SMOKE_RETRIEVAL_PATH)
    # Fallback: first 36 dev cases with chunk expectations
    cases: list[dict[str, Any]] = []
    with GOLDEN_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            if case.get("split") != "dev":
                continue
            if not case.get("expected_chunk_ids"):
                continue
            cases.append(case)
            if len(cases) >= 36:
                break
    return cases


def smoke_case_to_retrieval_row(case: dict[str, Any]) -> dict[str, str]:
    """Map golden jsonl case to retrieval benchmark row."""
    sources: set[str] = set()
    for chunk_id in case.get("expected_chunk_ids") or []:
        source = str(chunk_id).split("::", 1)[0].strip()
        if source:
            sources.add(source)
    flags = ";".join(case.get("safety_flags") or [])
    return {
        "case_id": str(case.get("id") or ""),
        "user_question": str(case.get("query") or ""),
        "expected_sources": ";".join(sorted(sources)),
        "expected_guardrail_flags": flags,
        "notes": str(case.get("rationale") or ""),
    }
