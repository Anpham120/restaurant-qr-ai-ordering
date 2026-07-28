# AI RAG Research Protocol

## Quality measurement layers

| Layer | Script | Primary KPI |
| --- | --- | --- |
| E2E+LLM (9router) | `run_golden_llm_eval.py` | `composite_pass_rate`, grounding, faithfulness |
| Retrieval research | `run_retrieval_experiment.py` | MRR@5, forbidden@10 |
| Pipeline no-LLM | `run_golden_chat_eval.py` | safety recall, forbidden rate (CI smoke only) |

Production LLM stack: **GPT-5.6 Luna only through 9router**, model
`cx/gpt-5.6-luna-review`. DeepSeek (`oc/deepseek-v4-flash-free`) is no longer
the primary model — the 9router route serving it rejects
`response_format:json_object`, which every real request requires (see
`docs/ai/AI_ASSISTANT_QUALITY_FIX_REPORT.md`). The old GPT/DeepSeek comparison
remains a historical model experiment; it is not the architecture-selection
gate.

## Pipeline architecture selection

Run:

```text
python ai/evaluation/run_pipeline_profile_eval.py
```

This compares `llm_first_v1`, `evidence_first_v2`, and `planner_state_v3` under
the same primary model, menu, KB, retrieval configuration, prompt budget, and
dataset (pass `--model` to override the primary model under test; defaults to
`config.DEFAULT_LLM_MODEL`). Selection order is safety hard gate, strict
semantic success, context accuracy, p95 latency, then mean LLM calls.

The result is `ai/evaluation/results/pipeline_selection.json`. Production must
derive `AI_PIPELINE_PROFILE` from its winner and validate it with
`verify_pipeline_selection.py`; a missing winner blocks deployment.

## Mandatory workflow

1. Change code/KB → run unit tests (`python -m unittest discover -s ai/tests`)
2. CI smoke: `python ai/evaluation/ci_golden_gates.py --run-smoke-eval`
3. Quality gate (manual/scheduled): full dev `run_golden_llm_eval` for GPT-5.5 and GPT-5.6 Luna
4. Export failures: `python ai/evaluation/export_llm_error_analysis.py`
5. Frozen test split: open once per retriever change (`--allow-frozen-test`)

## JSON output with 9router

Use the JSON response mode supported by the selected 9router route. `parse_model_response` remains the bounded validation/repair path for malformed provider output.

## Human eval

Use `ai/evaluation/templates/human_eval_scores.csv` — stratified 50-case sample before declaring Phase 2 complete.

## Ablation & chunk audit

- `python ai/evaluation/run_retrieval_ablation.py`
- `python ai/evaluation/audit_kb_chunks.py`
- Optional rerank: `evaluation/rerank_cross_encoder.py` (requires sentence-transformers)
