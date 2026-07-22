# Staging & production readiness checklist (Phase 6)

Last updated: 2026-07-22 (branch `fix/ai-response-followup`).

## Pre-canary gates

| Gate | Status | Evidence |
| --- | --- | --- |
| `composite_pass` GPT-5.5 ≥ 85% on full dev golden | **PASS (100%)** | `ai/evaluation/results/golden_llm_eval_cx_gpt55_v3_full_v3b.json` — 234/234 composite, grounding 100% |
| Safety smoke CI green | **PASS** | `py -m evaluation.ci_golden_gates --run-smoke-eval` — 36 smoke cases, hit@5=1.0, safety recall=1.0 |
| Human eval 50-case sample ≥ 85% pass | **PARTIAL — auto-scored** | `py -m evaluation.populate_human_eval_scores` → `human_eval_sample_50_scored.csv` + responses JSON; **100% auto-pass** from GPT golden; **manual brand_voice/fluency review still required** |
| Session eval duplicate-free | **PASS (offline)** | `py -m evaluation.run_session_e2e_eval` → `session_e2e_eval.json` — 31 cases, duplicate_free_rate=1.0, rolling_summary_rate=1.0 |

### Secondary model (DeepSeek)

- `golden_llm_eval_deepseek_v4_full.json`: **98.72%** composite (231/234); 3 grounding fails (q001 allergy, q086 recommend, q095 follow_up_more).
- Partial menu fabrication fix applied in `content_grounding.py`; re-run DeepSeek eval when 9router is up.

## Staging load test

**Requires staging env** — not run locally.

| Target | Threshold | Next steps |
| --- | --- | --- |
| p95 retrieval | ≤ 150 ms after warm-up | Deploy AI service to staging; run `retrieval_benchmark.py` against staging corpus with warm-up |
| p95 E2E | ≤ 3 s with 9router GPT-5.5 | Load-test `/chat` with 9router pointed at `cx/gpt-5.5`; capture p50/p95 from `latency_ms.total` |
| Fast-path catalog p95 | ≤ 100 ms | Replay catalog/tag/category queries from golden dev subset |

## Rollout

**Requires staging env** — do not fake results.

1. Deploy staging with 9router env (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL=cx/gpt-5.5`)
2. Shadow evaluate ≥ 1 week (log queries, compare shadow vs production responses)
3. Canary 10% tables
4. Full rollout with rollback image pinned

## Research artifacts

| Artifact | Status |
| --- | --- |
| Retrieval ablation | `py -m evaluation.run_retrieval_ablation` → `retrieval_ablation_summary.json` |
| Dev retrieval comparison | `evaluation/results/dev_retrieval_summary.v3.json` (hybrid_e5_small hit@5 ≈ 0.93) |
| Workspace audit | `py scripts/audit_ai_workspace.py` — stale_present=0 |

See also [`AI_PRODUCTION_OPERATIONS.md`](AI_PRODUCTION_OPERATIONS.md).
