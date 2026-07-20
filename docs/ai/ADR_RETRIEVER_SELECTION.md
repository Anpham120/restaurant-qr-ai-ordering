# ADR: Retriever Selection for CMC Restaurant RAG

**Status:** Accepted (confirmed on frozen test, 2026-07-17)

**Date:** 2026-07-14 (updated 2026-07-17)

**Decision owners:** AI/RAG engineering
**Related plan:** `docs/AI_LLM_RAG_REFACTOR_PLAN.md` §5.5

## Context

Phase 3 evaluation required a registered, reproducible retriever choice before the
frozen test split was opened. Dev experiments on the selector-backed golden set
(`ai/evaluation/golden/cases.jsonl`) compared 7 methods (BM25, 3 dense encoders,
3 hybrid RRF variants) with paired statistical tests
(`docs/AI_RETRIEVAL_DEV_RESULTS.md`).

The original 17-section notebook protocol (`llm_rag_retrieval_study.ipynb`) was
superseded by `ai/notebooks/rag_retrieval_research.ipynb`, which has been executed
end-to-end against the v3 artifacts.

## Decision

**Production retrieval method is `hybrid` (BM25 + dense `e5_small` via RRF)** as
implemented in `app.rag.retrieval_factory.build_retriever_stack`, confirmed by a
single frozen-test run with production menu filters applied
(`ai/evaluation/results/test_hybrid_e5_small_filtered.json`).

## Decision rule (Plan §5.5)

1. Eliminate any method that violates hard safety/grounding gates (§2.2).
2. Among survivors, select highest **nDCG@5 on dev**.
3. If 95% CIs overlap and McNemar/Wilcoxon show no significant difference, prefer lower
   p95 latency and simpler operations.
4. Lock configuration; run **frozen test exactly once**.
5. Ship to production only if test confirms hard gates and no significant regression vs
   BM25 baseline.

## Current state

| Item | Value |
| --- | --- |
| Production method | `hybrid` (BM25 + multilingual E5 small via RRF) |
| Encoder env | `AI_EMBEDDING_MODEL=e5_small` |
| Frozen test opened | Yes — one run, forbidden@10 = 0 |
| Phase 3 golden set | `ai/evaluation/golden/cases.jsonl` |
| Split manifest | `ai/evaluation/split_manifest.json` |
| Experiment entrypoint | `ai/evaluation/run_retrieval_experiment.py` |
| E2E behavior eval | `ai/evaluation/run_golden_chat_eval.py` |
| Legacy smoke eval | `ai/evaluation/run_evaluation.py` (hybrid default) |
| Research notebook | `ai/notebooks/rag_retrieval_research.ipynb` |

## Consequences

- Integration and assistant code default to hybrid retrieval with `e5_small`.
- Claims about retrieval quality reference the v3 artifacts:
  `ai/evaluation/results/dev_retrieval_summary.v3.json` and
  `ai/evaluation/results/test_hybrid_e5_small_filtered.json`.
- If future dev results reverse the ranking or fail gates, revert production default
  to BM25 per §5.5 step 5.

## Revisit triggers

- Frozen test regression vs BM25 on Hit@5, MRR@5, or nDCG@5 after corpus changes.
- Corpus hash change without re-benchmark (`split_manifest.json` SHA mismatch).
- New hard safety gate failure on adversarial set (`adversarial_injection_cases.jsonl`).
