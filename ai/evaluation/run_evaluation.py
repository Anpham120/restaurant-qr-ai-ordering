"""Automated RAG retrieval evaluation against golden_questions.csv.

Usage:
    python ai/evaluation/run_evaluation.py

Outputs retrieval hit-rate@5, per-case results, and guardrail accuracy.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import app.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ai"))

from app.rag.guardrails import detect_guardrail_flags  # noqa: E402
from app.rag.knowledge_base import load_markdown_knowledge_base  # noqa: E402
from app.rag.retriever import BM25Retriever  # noqa: E402

GOLDEN_CSV = Path(__file__).resolve().parent / "golden_questions.csv"
KB_PATH = PROJECT_ROOT / "ai" / "knowledge-base"
TOP_K = 5


def _load_golden_cases() -> list[dict]:
    with open(GOLDEN_CSV, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run() -> None:
    chunks = load_markdown_knowledge_base(KB_PATH)
    retriever = BM25Retriever(chunks)
    cases = _load_golden_cases()

    print(f"\n{'='*72}")
    print(f"  RAG Evaluation — {len(cases)} golden cases, top_k={TOP_K}")
    print(f"  Knowledge base: {len(chunks)} chunks from {KB_PATH}")
    print(f"{'='*72}\n")

    retrieval_hits = 0
    retrieval_total = 0
    guardrail_hits = 0
    guardrail_total = 0

    for case in cases:
        case_id = case["case_id"]
        question = case["user_question"]
        expected_sources = {s.strip() for s in case["expected_sources"].split(";") if s.strip()}
        expected_flags = {f.strip() for f in case["expected_guardrail_flags"].split(";") if f.strip()}

        # --- Retrieval evaluation ---
        results = retriever.search(question, TOP_K)
        retrieved_sources = {r.chunk.source for r in results}

        if expected_sources:
            retrieval_total += 1
            source_hit = bool(expected_sources.intersection(retrieved_sources))
            if source_hit:
                retrieval_hits += 1
        else:
            source_hit = True  # no expected sources = pass

        # --- Guardrail evaluation ---
        detected_flags = set(detect_guardrail_flags(question))

        if expected_flags:
            guardrail_total += 1
            flag_hit = expected_flags.issubset(detected_flags)
            if flag_hit:
                guardrail_hits += 1
        else:
            flag_hit = True

        # --- Display ---
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

    # --- Summary ---
    print(f"{'='*72}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*72}")

    if retrieval_total:
        hit_rate = retrieval_hits / retrieval_total * 100
        print(f"  Retrieval Hit Rate@{TOP_K}: {retrieval_hits}/{retrieval_total} = {hit_rate:.1f}%")
    else:
        print(f"  Retrieval: no cases with expected sources")

    if guardrail_total:
        guard_rate = guardrail_hits / guardrail_total * 100
        print(f"  Guardrail Accuracy:      {guardrail_hits}/{guardrail_total} = {guard_rate:.1f}%")
    else:
        print(f"  Guardrail: no cases with expected flags")

    total_pass = sum(1 for c in cases if _case_passes(c, retriever))
    print(f"  Overall Pass Rate:       {total_pass}/{len(cases)} = {total_pass/len(cases)*100:.1f}%")
    print(f"{'='*72}\n")


def _case_passes(case: dict, retriever: BM25Retriever) -> bool:
    expected_sources = {s.strip() for s in case["expected_sources"].split(";") if s.strip()}
    expected_flags = {f.strip() for f in case["expected_guardrail_flags"].split(";") if f.strip()}

    if expected_sources:
        results = retriever.search(case["user_question"], TOP_K)
        retrieved = {r.chunk.source for r in results}
        if not expected_sources.intersection(retrieved):
            return False

    if expected_flags:
        detected = set(detect_guardrail_flags(case["user_question"]))
        if not expected_flags.issubset(detected):
            return False

    return True


if __name__ == "__main__":
    run()
