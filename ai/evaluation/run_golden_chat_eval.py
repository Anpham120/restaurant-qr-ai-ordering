"""End-to-end chat evaluation against golden/cases.jsonl (no live LLM).

Runs the full AiAssistantService pipeline (retrieval, guardrails, policy,
menu grounding, fallback composer) without a live LLM, then scores:
- safety flag recall (expected safety_flags detected in guardrail_flags)
- forbidden suggestion rate (suggested cart actions vs forbidden_menu_ids/tags)
- knowledge chunk hit rate (expected_chunk_ids in retrieved_sources)
- expected menu suggestion hit rate (expected_menu_ids in suggested actions)

Usage:
    py -m evaluation.run_golden_chat_eval --split dev
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.golden_eval_common import (  # noqa: E402
    GOLDEN_PATH,
    build_offline_service,
    load_golden_cases,
    load_menu_items,
    score_pipeline_case,
)

RESULTS_DIR = AI_ROOT / "evaluation" / "results"
DEFAULT_OUTPUT = RESULTS_DIR / "golden_chat_e2e.json"


async def run_eval(
    split: str | None,
    retrieval_method: str,
    embedding_model: str,
) -> dict[str, Any]:
    cases = load_golden_cases(split)
    menu_items = load_menu_items()
    service = build_offline_service(retrieval_method, embedding_model)

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in cases:
        started = time.perf_counter()
        response = await service.chat(
            {
                "message": case["query"],
                "history": [],
                "menu_items": menu_items,
                "table_code": "T01",
                "session_id": f"golden-{case['id']}",
            }
        )
        latencies.append((time.perf_counter() - started) * 1000)
        rows.append(score_pipeline_case(case, response))

    safety_rows = [row for row in rows if row["safety_flags_expected"]]
    chunk_rows = [row for row in rows if row["expected_chunk_hit"] is not None]
    menu_rows = [row for row in rows if row["expected_menu_hit"] is not None]
    summary = {
        "evaluated_cases": len(rows),
        "safety_flag_cases": len(safety_rows),
        "safety_flag_recall": (
            sum(1 for row in safety_rows if row["safety_pass"]) / len(safety_rows)
            if safety_rows
            else None
        ),
        "forbidden_suggestion_rate": (
            sum(1 for row in rows if not row["forbidden_pass"]) / len(rows) if rows else None
        ),
        "chunk_hit_cases": len(chunk_rows),
        "chunk_hit_rate": (
            sum(1 for row in chunk_rows if row["expected_chunk_hit"]) / len(chunk_rows)
            if chunk_rows
            else None
        ),
        "source_hit_rate": (
            sum(1 for row in chunk_rows if row["expected_source_hit"]) / len(chunk_rows)
            if chunk_rows
            else None
        ),
        "expected_menu_cases": len(menu_rows),
        "expected_menu_hit_rate": (
            sum(1 for row in menu_rows if row["expected_menu_hit"]) / len(menu_rows)
            if menu_rows
            else None
        ),
        "latency_ms": {
            "p50": statistics.median(latencies) if latencies else 0.0,
            "mean": statistics.fmean(latencies) if latencies else 0.0,
        },
    }
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": split or "all",
        "retrieval_method": retrieval_method,
        "embedding_model": embedding_model,
        "llm": "disabled (deterministic fallback path)",
        "dataset": {
            "path": str(GOLDEN_PATH.relative_to(PROJECT_ROOT)),
            "case_count": len(cases),
        },
        "summary": summary,
        "failures": {
            "safety": [row for row in rows if not row["safety_pass"]],
            "forbidden": [row for row in rows if not row["forbidden_pass"]],
        },
        "cases": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--retrieval-method", default="hybrid")
    parser.add_argument("--embedding-model", default="e5_small")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    split = None if args.split == "all" else args.split
    result = asyncio.run(run_eval(split, args.retrieval_method, args.embedding_model))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = result["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
