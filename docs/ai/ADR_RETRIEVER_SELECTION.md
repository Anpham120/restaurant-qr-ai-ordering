# ADR: Retriever Selection for CMC Restaurant RAG

**Status:** Accepted (provisional)

**Date:** 2026-07-14

**Decision owners:** AI/RAG engineering
**Related plan:** `docs/AI_LLM_RAG_REFACTOR_PLAN.md` §5.5

## Context

Phase 3 evaluation requires a registered, reproducible retriever choice before the
frozen test split is opened. Dev experiments on 110 selector-backed cases showed
hybrid BM25 + sparse-vector RRF outperforming BM25 alone on MRR@5 and nDCG@5 with
Holm-corrected significance versus BM25 (`docs/AI_RETRIEVAL_DEV_RESULTS.md`).

The full 17-section notebook protocol (`ai/notebooks/llm_rag_retrieval_study.ipynb`)
has not yet been executed end-to-end in a clean environment with the new Phase 3 golden
set (`ai/evaluation/golden/cases.jsonl`, ≥300 cases).

## Decision

**Production retrieval method remains `hybrid` (BM25 + dense RRF)** as implemented in
`app.rag.retrieval_factory.build_retriever_stack`, pending confirmation from the full
notebook run on dev and a single frozen-test evaluation.

This is a **provisional winner**, not a final test-certified claim.

## Decision rule (Plan §5.5)

1. Eliminate any method that violates hard safety/grounding gates (§2.2).
2. Among survivors, select highest **nDCG@5 on dev**.
3. If 95% CIs overlap and McNemar/Wilcoxon show no significant difference, prefer lower
   p95 latency and simpler operations.
4. Lock configuration; run **frozen test exactly once**.
5. Ship to production only if test confirms hard gates and no significant regression vs
   BM25 baseline.

The rule explicitly allows BM25 to remain the production choice if hybrid/dense gains
are not statistically or operationally justified.

## Current state

| Item | Value |
| --- | --- |
| Production method | `hybrid` (BM25 + multilingual E5 dense via RRF) |
| Dev provisional winner | Hybrid RRF |
| Frozen test opened | No |
| Phase 3 golden set | `ai/evaluation/golden/cases.jsonl` |
| Split manifest | `ai/evaluation/split_manifest.json` |
| Benchmark entrypoint | `ai/evaluation/run_retrieval_benchmark.py` |

## Consequences

- Integration and assistant code continue to default to hybrid retrieval.
- Marketing or thesis claims about embedding superiority require notebook artifacts:
  `ai/evaluation/results/retrieval_metrics.json`, statistical tests, and frozen-test row.
- If notebook dev results reverse the ranking or fail gates, revert production default
  to BM25 per §5.5 step 5.

## Revisit triggers

- Completion of `llm_rag_retrieval_study.ipynb` with conflicting dev metrics.
- Frozen test regression vs BM25 on Hit@5, MRR@5, or nDCG@5.
- Corpus hash change without re-benchmark (`split_manifest.json` SHA mismatch).
- New hard safety gate failure on adversarial set (`adversarial_injection_cases.jsonl`).
