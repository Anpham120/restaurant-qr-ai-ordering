# AI RAG Research Protocol

## Quality measurement layers

| Layer | Script | Primary KPI |
| --- | --- | --- |
| E2E+LLM (9router) | `run_golden_llm_eval.py` | `composite_pass_rate`, grounding, faithfulness |
| Retrieval research | `run_retrieval_experiment.py` | MRR@5, forbidden@10 |
| Pipeline no-LLM | `run_golden_chat_eval.py` | safety recall, forbidden rate (CI smoke only) |

Production LLM stack: **9router** with `cx/gpt-5.5` (quality gate) and `oc/deepseek-v4-flash-free` (cheap sweep).

## Mandatory workflow

1. Change code/KB → run unit tests (`python -m unittest discover -s ai/tests`)
2. CI smoke: `python ai/evaluation/ci_golden_gates.py --run-smoke-eval`
3. Quality gate (manual/scheduled): full dev `run_golden_llm_eval` for GPT-5.5 and DeepSeek
4. Export failures: `python ai/evaluation/export_llm_error_analysis.py`
5. Frozen test split: open once per retriever change (`--allow-frozen-test`)

## JSON output with 9router

Native Gemini `response_format` is **not** used. Structured output relies on prompt + `parse_model_response` repair path.

## Human eval

Use `ai/evaluation/templates/human_eval_scores.csv` — stratified 50-case sample before declaring Phase 2 complete.

## Ablation & chunk audit

- `python ai/evaluation/run_retrieval_ablation.py`
- `python ai/evaluation/audit_kb_chunks.py`
- Optional rerank: `evaluation/rerank_cross_encoder.py` (requires sentence-transformers)
