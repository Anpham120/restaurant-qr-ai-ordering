# Staging & production readiness checklist (Phase 6)

Last updated: 2026-07-23.

**Current release status: NOT READY.** Historical `composite_pass` artifacts are
retained for provenance only; they do not satisfy the current evidence-first
release contract.

## Pre-canary gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Critical hallucination = 0 on frozen release set | **CHƯA ĐO** | Frozen test chỉ được mở sau config lock |
| Retrieval Hit@5 ≥ 95% | **PASS — 109/110 (99,09%)** | `dev_retrieval_summary.v3.json`, `hybrid_e5_small`, dev |
| Retrieval nDCG@5 ≥ 0,75 | **PASS — 0,8332** | Cùng artifact; 7-method screening. Dense E5 = 0,8401 nhưng chênh với Hybrid E5 chưa có ý nghĩa thống kê |
| Hybrid E5 p95 retrieval | **PASS CỤC BỘ — 29,34 ms** | `dev_hybrid_e5_release_candidate.v1.json`, 110 case × 7 lần đo/query; staging load test vẫn chưa chạy |
| Current paired GPT-5.5/DeepSeek run | **PASS PROTOCOL, CHƯA PASS QUALITY RELEASE** | `dual_model/20260723-9router-paired-18-final/comparison.json`: 11/11 exact input hashes khớp, cùng retriever/no fallback; availability 11/11 mỗi model; quality GPT 2/11, DeepSeek 3/11 |
| Human overall ≥ 95%, safety = 100% | **CHƯA ĐO** | Auto-score không thay human review; cần 50–100 câu, ít nhất 20% chấm đôi |
| Context retention ≥ 98% | **PASS OFFLINE — 1200/1200** | `session_e2e_eval.json`; deterministic templated regression, không phải bằng chứng free-form LLM |

### Historical LLM baseline — không dùng làm release headline

- `golden_llm_eval_cx_gpt55_v3_full_v3b.json` và
  `golden_llm_eval_deepseek_v4_full.json` là artifact trước truth-reset.
- Có thể trích dẫn chúng như baseline lịch sử nếu nêu rõ availability,
  faithfulness/adequacy và giới hạn metric; không dùng `composite_pass=100%` để
  kết luận hệ thống hiện tại không bịa.

## Staging load test

**Requires staging env** — not run locally.

| Target | Threshold | Next steps |
| --- | --- | --- |
| p95 retrieval | ≤ 150 ms after warm-up | Deploy AI service to staging; replay the locked retrieval cases after warm-up |
| p95 E2E | ≤ 6 s with 9router DeepSeek | Load-test `/chat` with `LLM_MODEL=oc/deepseek-v4-flash-free`; report TTFT separately from end-to-end p50/p95 |
| Fast-path catalog p95 | ≤ 100 ms | Replay catalog/tag/category queries from golden dev subset |

## Rollout

**Requires staging env** — do not fake results.

1. Deploy staging with 9router env (`LLM_PROVIDER=9router`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL=oc/deepseek-v4-flash-free`)
2. Shadow evaluate ≥ 1 week (log queries, compare shadow vs production responses)
3. Canary 10% tables
4. Full rollout with rollback image pinned

## Research artifacts

| Artifact | Status |
| --- | --- |
| Retrieval ablation | `py -m evaluation.run_retrieval_ablation` → `retrieval_ablation_summary.json` |
| Dev retrieval comparison | `evaluation/results/dev_retrieval_summary.v3.json` (7 phương pháp; latency screening-only 1 lần/query; `hybrid_e5_small`: Hit@5 109/110 = 99,09%; nDCG@5 0,8332) |
| Hybrid E5 release-candidate latency | `evaluation/results/dev_hybrid_e5_release_candidate.v1.json` (7 lần/query; p95 29,34 ms) |
| Workspace audit | `py scripts/audit_ai_workspace.py` — stale_present=0 |

See also [`VPS_STAGING_AI_RUNBOOK.md`](VPS_STAGING_AI_RUNBOOK.md).
