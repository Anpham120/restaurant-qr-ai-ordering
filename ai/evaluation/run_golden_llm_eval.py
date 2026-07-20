"""End-to-end golden chat evaluation with a live LLM (Gemini).

Runs golden/cases.jsonl through the full AiAssistantService including Gemini,
then scores pipeline safety/grounding plus LLM-specific quality metrics.

Usage:
    py -m evaluation.run_golden_llm_eval --split dev --limit 30
    py -m evaluation.run_golden_llm_eval --split dev --limit 30 --with-judge
    py -m evaluation.run_golden_llm_eval --split dev --limit 20 --compare-retrieval hybrid,bm25
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

from app.config import load_config  # noqa: E402
from app.rag.knowledge_base import load_markdown_knowledge_base  # noqa: E402
from evaluation.golden_eval_common import (  # noqa: E402
    AI_ROOT as _AI_ROOT,
    GOLDEN_PATH,
    build_llm_service,
    load_golden_cases,
    load_menu_items,
    score_pipeline_case,
)
from evaluation.llm_eval_judge import judge_response  # noqa: E402
from evaluation.llm_eval_metrics import score_llm_case, summarize_llm_metrics  # noqa: E402

RESULTS_DIR = _AI_ROOT / "evaluation" / "results"
DEFAULT_OUTPUT = RESULTS_DIR / "golden_llm_eval.json"


async def evaluate_cases(
    cases: list[dict[str, Any]],
    *,
    retrieval_method: str,
    embedding_model: str,
    with_judge: bool,
    llm_client: Any | None = None,
    sleep_ms: int = 1500,
    max_retry: int = 2,
) -> dict[str, Any]:
    menu_items = load_menu_items()
    kb_chunks = load_markdown_knowledge_base(_AI_ROOT / "knowledge-base")
    service = build_llm_service(
        retrieval_method=retrieval_method,
        embedding_model=embedding_model,
        llm_client=llm_client,
        max_retry=max_retry,
    )
    config = load_config()
    if llm_client is None and service._client is not None:
        service._client._max_retry = max_retry
        service._client._retry_delay_seconds = max(2.0, sleep_ms / 1000)

    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    llm_latencies: list[float] = []

    for case in cases:
        service.invalidate_cache()
        started = time.perf_counter()
        response = await service.chat(
            {
                "message": case["query"],
                "history": [],
                "menu_items": menu_items,
                "table_code": "T01",
                "session_id": f"golden-llm-{case['id']}",
            }
        )
        latencies.append((time.perf_counter() - started) * 1000)

        row = score_pipeline_case(case, response)
        llm_metrics = score_llm_case(
            case,
            response,
            kb_chunks=kb_chunks,
            menu_items=menu_items,
        )
        row.update(
            {
                "content": response.get("content") or "",
                "llm_success": llm_metrics.llm_success,
                "schema_valid": llm_metrics.schema_valid,
                "grounding_pass": llm_metrics.grounding_pass,
                "faithfulness_score": llm_metrics.faithfulness_score,
                "allergy_disclaimer_pass": llm_metrics.allergy_disclaimer_pass,
                "price_refusal_pass": llm_metrics.price_refusal_pass,
                "content_non_empty": llm_metrics.content_non_empty,
                "composite_pass": llm_metrics.composite_pass,
                "latency_ms": response.get("latency_ms") or {},
            }
        )
        llm_stage = (response.get("latency_ms") or {}).get("llm")
        if isinstance(llm_stage, (int, float)):
            llm_latencies.append(float(llm_stage))

        if with_judge:
            titles = [
                f"{source.get('source')}::{source.get('title')}"
                for source in (response.get("retrieved_sources") or [])
            ]
            names = [str(action.get("name") or "") for action in (response.get("suggested_cart_actions") or [])]
            judge = await judge_response(
                query=case["query"],
                response_content=row["content"],
                retrieved_titles=titles,
                suggested_names=names,
                expected_rationale=str(case.get("rationale") or ""),
            )
            row.update(judge)

        rows.append(row)

        if sleep_ms > 0 and llm_client is None:
            extra = sleep_ms
            if "AI_PROVIDER_UNAVAILABLE" in (response.get("guardrail_flags") or []):
                extra = int(sleep_ms * 2)
            await asyncio.sleep(extra / 1000)

    summary = summarize_llm_metrics(rows)
    llm_rows = [row for row in rows if row.get("llm_success")]
    if llm_rows:
        summary["llm_only"] = summarize_llm_metrics(llm_rows)
    summary["latency_ms"] = {
        "p50": statistics.median(latencies) if latencies else 0.0,
        "mean": statistics.fmean(latencies) if latencies else 0.0,
    }
    summary["llm_latency_ms"] = {
        "p50": statistics.median(llm_latencies) if llm_latencies else 0.0,
        "mean": statistics.fmean(llm_latencies) if llm_latencies else 0.0,
    }
    if with_judge:
        judged = [row for row in rows if row.get("faithfulness") is not None]
        if judged:
            summary["judge_cases"] = len(judged)
            summary["judge_pass_rate"] = sum(1 for row in judged if row.get("judge_pass")) / len(judged)
            for key in ("faithfulness", "safety", "usefulness"):
                summary[f"judge_{key}_mean"] = statistics.fmean(row[key] for row in judged)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieval_method": retrieval_method,
        "embedding_model": embedding_model,
        "llm": {
            "provider": config.provider,
            "model": config.model,
            "with_judge": with_judge,
        },
        "dataset": {
            "path": str(GOLDEN_PATH.relative_to(PROJECT_ROOT)),
            "case_count": len(cases),
        },
        "summary": summary,
        "failures": {
            "composite": [row for row in rows if not row.get("composite_pass")],
            "forbidden": [row for row in rows if not row.get("forbidden_pass")],
            "safety": [row for row in rows if not row.get("safety_pass")],
        },
        "cases": rows,
    }


async def run_eval(args: argparse.Namespace) -> dict[str, Any]:
    families = set(args.families.split(",")) if args.families else None
    cases = load_golden_cases(
        None if args.split == "all" else args.split,
        families=families,
        limit=args.limit,
    )
    if not cases:
        raise SystemExit("No golden cases matched the filters.")

    methods = [item.strip() for item in args.compare_retrieval.split(",") if item.strip()]
    runs: dict[str, Any] = {}
    for method in methods:
        runs[method] = await evaluate_cases(
            cases,
            retrieval_method=method,
            embedding_model=args.embedding_model,
            with_judge=args.with_judge,
            sleep_ms=args.sleep_ms,
            max_retry=args.max_retry,
        )

    if len(runs) == 1:
        return next(iter(runs.values())) | {"split": args.split}

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": args.split,
        "comparison": runs,
        "delta": _comparison_delta(runs, methods),
    }


def _comparison_delta(runs: dict[str, Any], methods: list[str]) -> dict[str, Any] | None:
    if len(methods) != 2:
        return None
    left, right = methods
    left_summary = runs[left]["summary"]
    right_summary = runs[right]["summary"]
    return {
        "methods": [left, right],
        "composite_pass_rate_delta": (left_summary.get("composite_pass_rate") or 0)
        - (right_summary.get("composite_pass_rate") or 0),
        "faithfulness_mean_delta": (left_summary.get("faithfulness_mean") or 0)
        - (right_summary.get("faithfulness_mean") or 0),
        "source_hit_rate_delta": (left_summary.get("source_hit_rate") or 0)
        - (right_summary.get("source_hit_rate") or 0),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--limit", type=int, default=30, help="Max cases (default 30 pilot)")
    parser.add_argument("--families", default="", help="Comma-separated family filter")
    parser.add_argument("--embedding-model", default="e5_small")
    parser.add_argument(
        "--compare-retrieval",
        default="hybrid",
        help="One method or comma-separated pair, e.g. hybrid,bm25",
    )
    parser.add_argument(
        "--with-judge",
        action="store_true",
        help="Also run Gemini-as-judge rubric (doubles API cost)",
    )
    parser.add_argument(
        "--sleep-ms",
        type=int,
        default=5000,
        help="Pause between LLM calls to reduce 429 rate limits (default 5000)",
    )
    parser.add_argument(
        "--max-retry",
        type=int,
        default=4,
        help="Gemini retries on 429/5xx during eval (default 4)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    result = asyncio.run(run_eval(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if "summary" in result:
        print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    else:
        for method, payload in result["comparison"].items():
            print(f"\n=== {method} ===")
            print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
        if result.get("delta"):
            print("\n=== delta ===")
            print(json.dumps(result["delta"], ensure_ascii=False, indent=2))
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
