"""Automated RAG retrieval evaluation against golden_questions.csv.

Usage:
    py evaluation/run_evaluation.py
    py evaluation/run_evaluation.py --method hybrid
    py evaluation/run_evaluation.py --method bm25 --quiet

Outputs retrieval hit-rate@5, per-case results, and guardrail accuracy.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path
from typing import Protocol

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from app.rag.embedding_retriever import create_encoder  # noqa: E402
from app.rag.guardrails import detect_guardrail_flags  # noqa: E402
from app.rag.intent_classifier import classify_intent  # noqa: E402
from app.rag.knowledge_base import KnowledgeChunk, load_markdown_knowledge_base  # noqa: E402
from app.rag.retrieval_factory import build_retriever_stack  # noqa: E402
from app.rag.retriever import BM25Retriever  # noqa: E402

GOLDEN_CSV = Path(__file__).resolve().parent / "golden_questions.csv"
KB_PATH = AI_ROOT / "knowledge-base"
TOP_K = 5


class Searchable(Protocol):
    def search(self, query: str, top_k: int) -> list: ...


def _load_golden_cases() -> list[dict]:
    with GOLDEN_CSV.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _build_retriever(method: str, chunks: list[KnowledgeChunk]) -> tuple[Searchable, str]:
    if method == "bm25":
        return BM25Retriever(chunks), "bm25"
    if method == "hybrid":
        stack = build_retriever_stack(chunks, "hybrid", encoder=create_encoder("e5_small"))
        return stack.retriever, stack.method
    raise ValueError(f"Unsupported method: {method}")


def _rerank_by_intent(results: list, source_hints: tuple[str, ...]) -> list:
    """Mirror production intent rerank (app.services.assistant._rerank_by_intent)."""

    if not source_hints or not results:
        return results
    hint_set = set(source_hints)
    hint_results = sorted(
        (r for r in results if r.chunk.source in hint_set), key=lambda r: r.score, reverse=True
    )
    other_results = sorted(
        (r for r in results if r.chunk.source not in hint_set), key=lambda r: r.score, reverse=True
    )
    if not hint_results:
        return results

    merged = [hint_results[0]]
    hi, oi = 1, 0
    while hi < len(hint_results) or oi < len(other_results):
        if oi < len(other_results):
            merged.append(other_results[oi])
            oi += 1
        if hi < len(hint_results):
            merged.append(hint_results[hi])
            hi += 1
    return merged


def _evaluate_case(case: dict, retriever: Searchable) -> tuple[bool, bool, list, set[str], set[str], set[str]]:
    question = case["user_question"]
    expected_sources = {s.strip() for s in case["expected_sources"].split(";") if s.strip()}
    expected_flags = {f.strip() for f in case["expected_guardrail_flags"].split(";") if f.strip()}

    results = retriever.search(question, TOP_K)
    intent = classify_intent(question)
    if intent.source_hints and intent.confidence >= 0.1:
        results = _rerank_by_intent(results, intent.source_hints)
    retrieved_sources = {r.chunk.source for r in results}

    if expected_sources:
        source_hit = bool(expected_sources.intersection(retrieved_sources))
    else:
        source_hit = True

    detected_flags = set(detect_guardrail_flags(question))
    if expected_flags:
        flag_hit = expected_flags.issubset(detected_flags)
    else:
        flag_hit = True

    return source_hit, flag_hit, results, expected_sources, detected_flags, retrieved_sources


def run(*, method: str = "hybrid", quiet: bool = False) -> dict[str, float | int]:
    chunks = load_markdown_knowledge_base(KB_PATH)
    retriever, resolved_method = _build_retriever(method, chunks)
    cases = _load_golden_cases()

    print(f"\n{'='*72}")
    print(f"  RAG Evaluation — {len(cases)} golden cases, top_k={TOP_K}")
    print(f"  Retriever: {resolved_method}")
    print(f"  Knowledge base: {len(chunks)} chunks from {KB_PATH}")
    print(f"{'='*72}\n")

    retrieval_hits = 0
    retrieval_total = 0
    guardrail_hits = 0
    guardrail_total = 0
    total_pass = 0

    for case in cases:
        case_id = case["case_id"]
        question = case["user_question"]
        expected_flags = {f.strip() for f in case["expected_guardrail_flags"].split(";") if f.strip()}
        source_hit, flag_hit, results, expected_sources, detected_flags, retrieved_sources = _evaluate_case(
            case, retriever
        )

        if expected_sources:
            retrieval_total += 1
            if source_hit:
                retrieval_hits += 1
        if expected_flags:
            guardrail_total += 1
            if flag_hit:
                guardrail_hits += 1
        if source_hit and flag_hit:
            total_pass += 1

        if quiet:
            continue

        status = "PASS" if (source_hit and flag_hit) else "FAIL"
        print(f"  {status} {case_id}: {question}")
        if results:
            top_result = results[0]
            print(f"     Top-1: {top_result.chunk.source}::{top_result.chunk.title} (score={top_result.score})")
        print(f"     Retrieved: {retrieved_sources or '{none}'}")
        print(f"     Expected:  {expected_sources or '{any}'}")
        if expected_flags or detected_flags:
            print(f"     Guardrail expected: {expected_flags or '{none}'}")
            print(f"     Guardrail detected: {detected_flags or '{none}'}")
        print()

    print(f"{'='*72}")
    print("  RESULTS SUMMARY")
    print(f"{'='*72}")

    if retrieval_total:
        hit_rate = retrieval_hits / retrieval_total * 100
        print(f"  Retrieval Hit Rate@{TOP_K}: {retrieval_hits}/{retrieval_total} = {hit_rate:.1f}%")
    else:
        print("  Retrieval: no cases with expected sources")

    if guardrail_total:
        guard_rate = guardrail_hits / guardrail_total * 100
        print(f"  Guardrail Accuracy:      {guardrail_hits}/{guardrail_total} = {guard_rate:.1f}%")
    else:
        print("  Guardrail: no cases with expected flags")

    print(f"  Overall Pass Rate:       {total_pass}/{len(cases)} = {total_pass/len(cases)*100:.1f}%")
    print(f"{'='*72}\n")

    return {
        "cases": len(cases),
        "retrieval_hits": retrieval_hits,
        "retrieval_total": retrieval_total,
        "guardrail_hits": guardrail_hits,
        "guardrail_total": guardrail_total,
        "total_pass": total_pass,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--method",
        choices=("hybrid", "bm25"),
        default="hybrid",
        help="Retriever to score (default: hybrid, matches production)",
    )
    parser.add_argument("--quiet", action="store_true", help="Print summary only")
    args = parser.parse_args()
    run(method=args.method, quiet=args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
