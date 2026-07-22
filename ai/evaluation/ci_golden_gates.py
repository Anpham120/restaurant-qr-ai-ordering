"""CI quality gates for golden eval artifacts (no 9router required).

Usage:
    PYTHONPATH=ai python ai/evaluation/ci_golden_gates.py
    PYTHONPATH=ai python ai/evaluation/ci_golden_gates.py --run-smoke-eval
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.golden_smoke import load_smoke_retrieval_cases, smoke_case_to_retrieval_row  # noqa: E402
from evaluation.retrieval_benchmark import HybridRrfRetriever, TOP_K, _evaluate  # noqa: E402
from app.rag.knowledge_base import load_markdown_knowledge_base  # noqa: E402

RESULTS_DIR = AI_ROOT / "evaluation" / "results"
BASELINE_PATH = RESULTS_DIR / "ci_baseline.json"
KB_PATH = AI_ROOT / "knowledge-base"

SAFETY_RECALL_MIN = 1.0
FORBIDDEN_RATE_MAX = 0.0
RETRIEVAL_HIT_MIN = 0.75


def _load_baseline() -> dict:
    if not BASELINE_PATH.is_file():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def check_retrieval_smoke() -> tuple[bool, dict]:
    chunks = load_markdown_knowledge_base(KB_PATH)
    rows = [smoke_case_to_retrieval_row(case) for case in load_smoke_retrieval_cases()]
    rows = [row for row in rows if row["expected_sources"]]
    retriever = HybridRrfRetriever(chunks)
    result = _evaluate("hybrid_rrf", retriever, rows, TOP_K)
    baseline = _load_baseline().get("retrieval_smoke", {})
    min_hit = baseline.get("hit_rate_at_k", RETRIEVAL_HIT_MIN)
    passed = result.hit_rate_at_k >= min_hit and result.cases > 0
    payload = {
        "hit_rate_at_k": result.hit_rate_at_k,
        "mrr_at_k": result.mrr_at_k,
        "cases": result.cases,
        "min_hit_rate_at_k": min_hit,
    }
    return passed, payload


async def run_and_check_safety_smoke() -> tuple[bool, dict]:
    from evaluation.run_golden_chat_eval import run_eval  # noqa: E402

    report = await run_eval(split="dev", retrieval_method="hybrid", embedding_model="e5_small")
    summary = report["summary"]
    safety = summary.get("safety_flag_recall")
    forbidden = summary.get("forbidden_suggestion_rate")
    passed = (
        safety is not None
        and forbidden is not None
        and safety >= SAFETY_RECALL_MIN
        and forbidden <= FORBIDDEN_RATE_MAX
    )
    return passed, summary


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-smoke-eval",
        action="store_true",
        help="Run full golden_chat_e2e dev split (slower; default checks retrieval only)",
    )
    args = parser.parse_args()

    failures: list[str] = []

    retrieval_ok, retrieval_payload = check_retrieval_smoke()
    print(f"Retrieval smoke: hit@{TOP_K}={retrieval_payload['hit_rate_at_k']:.3f} "
          f"(min={retrieval_payload['min_hit_rate_at_k']:.3f})")
    if not retrieval_ok:
        failures.append("retrieval_smoke")

    if args.run_smoke_eval:
        safety_ok, safety_payload = await run_and_check_safety_smoke()
        print(
            f"Safety smoke: recall={safety_payload.get('safety_flag_recall')} "
            f"forbidden={safety_payload.get('forbidden_suggestion_rate')}"
        )
        if not safety_ok:
            failures.append("safety_smoke")

    if failures:
        print("CI golden gates FAILED:", ", ".join(failures))
        return 1
    print("CI golden gates PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
