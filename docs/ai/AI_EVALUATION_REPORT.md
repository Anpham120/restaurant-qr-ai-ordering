# AI Evaluation Report (rolling)

Update after each full dev E2E+LLM run via 9router.

## Latest artifacts

| Profile | Artifact | Notes |
| --- | --- | --- |
| GPT-5.5 gate | `ai/evaluation/results/golden_llm_eval_cx_gpt55_v3_full_v3b.json` | **100%** composite (234 dev) |
| DeepSeek sweep | `ai/evaluation/results/golden_llm_eval_deepseek_v4_full.json` | **98.72%** composite (234 dev) |
| Safety smoke | `ai/evaluation/results/golden_chat_e2e.json` | CI only |
| Session eval | `ai/evaluation/results/session_e2e_eval.json` | Multi-turn |

## Commands

```powershell
cd ai
py -m evaluation.run_dual_llm_eval --split dev --limit 234
py -m evaluation.export_llm_error_analysis
py -m evaluation.generate_human_eval_sample
py -m evaluation.run_session_e2e_eval --tier multi_turn
```

See [`AI_RAG_RESEARCH_PROTOCOL.md`](AI_RAG_RESEARCH_PROTOCOL.md).
