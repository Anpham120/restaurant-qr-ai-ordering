# AI Evaluation Report (rolling)

Update after each full dev E2E+LLM run via 9router.

## Current release evidence

| Layer | Artifact | Result |
| --- | --- | --- |
| Retrieval dev — 7 phương pháp | `ai/evaluation/results/dev_retrieval_summary.v3.json` | Hybrid E5 Hit@5 **109/110 (99,09%)**, MRR@5 **0,9367**, nDCG@5 **0,8332**; Dense E5 **110/110**, nDCG@5 **0,8401**. Cả hai đạt gate; chênh nDCG chưa có ý nghĩa thống kê. Latency của bảng này là screening-only, 1 lần đo/query |
| Hybrid E5 release-candidate | `ai/evaluation/results/dev_hybrid_e5_release_candidate.v1.json` | Cùng 110 case, 7 lần đo/query: Hit@5 **109/110**, nDCG@5 **0,8332**, p95 retrieval **29,34 ms**; chưa thay staging load test |
| Session regression | `ai/evaluation/results/session_e2e_eval.json` | Context retention **1200/1200**, deterministic templated offline only |
| Paired GPT-5.5/DeepSeek | `ai/evaluation/results/dual_model/20260723-9router-paired-18-final/comparison.json` | Protocol PASS: cùng case/order, retriever không fallback, exact generation-input hash **11/11** khớp. Availability cùng **11/11**; quality-on-success GPT‑5.5 **2/11**, DeepSeek **3/11**; chỉ là mô tả trên mẫu nhỏ |
| Human/frozen test | Approved review + locked artifact | **Chưa được thay thế bởi auto-score** |

Không dùng `composite_pass=100%` làm headline nếu availability, faithfulness,
answer adequacy, human review hoặc frozen-test gate chưa đạt.

## Historical artifacts — provenance only

| Profile | Artifact | Notes |
| --- | --- | --- |
| GPT-5.5 baseline | `ai/evaluation/results/golden_llm_eval_cx_gpt55_v3_full_v3b.json` | Pre-truth-reset composite artifact; không phải current release gate |
| DeepSeek baseline | `ai/evaluation/results/golden_llm_eval_deepseek_v4_full.json` | Pre-truth-reset composite artifact; không phải current release gate |
| Safety smoke | `ai/evaluation/results/golden_chat_e2e.json` | CI only |
| Session eval | `ai/evaluation/results/session_e2e_eval.json` | Multi-turn |

## Commands

```powershell
cd ai
py -m evaluation.run_retrieval_experiment --method hybrid_e5_small --split dev --top-k 10 --latency-repetitions 7 --output evaluation/results/dev_hybrid_e5_release_candidate.v1.json
py -m evaluation.run_dual_llm_eval --split dev --limit 18 --sampling-strategy stratified --run-id 20260723-9router-paired-18-final
py -m evaluation.export_llm_error_analysis
py -m evaluation.generate_human_eval_sample
py -m evaluation.run_session_e2e_eval --tier multi_turn
```

See [`AI_RAG_RESEARCH_PROTOCOL.md`](AI_RAG_RESEARCH_PROTOCOL.md).
