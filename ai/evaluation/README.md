# AI/RAG Evaluation

Research package dùng chung cho BM25, neural embedding và hybrid.

## Quality gates (thứ tự ưu tiên)

| Lớp | Script | KPI chính? |
| --- | --- | --- |
| **E2E+LLM (9router)** | `run_dual_llm_eval.py` / `run_golden_llm_eval.py` | **Có** — availability tách riêng quality-on-success, claim support, faithfulness, adequacy và abstention |
| Retrieval research | `run_retrieval_experiment.py` | Có (ADR retriever) |
| Pipeline no-LLM | `run_golden_chat_eval.py` | **Không** — CI smoke safety/forbidden only |
| CI gates | `ci_golden_gates.py` | Safety + retrieval smoke (no API) |

Không dùng `composite_pass=100%` làm headline hoặc bằng chứng release nếu
availability, faithfulness, answer adequacy, human review hay frozen-test gate chưa
đạt. Mọi tỷ lệ phải kèm tử số/mẫu số; provider failure không được gộp vào chất
lượng trên nhóm gọi thành công.

### E2E+LLM qua 9router

```powershell
cd ai
$env:LLM_PROVIDER='9router'
$env:LLM_BASE_URL='http://localhost:20128/v1'
$env:LLM_API_KEY='...'
$env:LLM_MODEL='cx/gpt-5.5'
py -m evaluation.run_golden_llm_eval --split dev --limit 234

$env:LLM_MODEL='oc/deepseek-v4-flash-free'
py -m evaluation.run_golden_llm_eval --split dev --limit 234 --output evaluation/results/golden_llm_eval_deepseek_v4_full.json

# Paired comparison: cùng case, evidence, prompt và budget cho cả hai model
py -m evaluation.run_dual_llm_eval --split dev --limit 234 --run-id current-approved-candidate
```

### CI smoke (no 9router)

```powershell
PYTHONPATH=ai python ai/evaluation/ci_golden_gates.py --run-smoke-eval
```

## Datasets

- `golden/cases.jsonl` — canonical golden (325 case, dev/test split)
- `golden/smoke_retrieval.jsonl` — ~36 case smoke cho retrieval benchmark + legacy `run_evaluation.py`
- `golden_questions.csv` — **archived legacy**; replaced by smoke subset from jsonl

## Scripts

- `run_golden_chat_eval.py`: pipeline no-LLM — safety, forbidden, source/menu hit (reference only)
- `run_golden_llm_eval.py`: full pipeline + live LLM via 9router
- `run_retrieval_experiment.py`: BM25/dense/hybrid compare + optional ablations
- `generate_golden_cases.py`: regenerate golden from KB
- `run_session_e2e_eval.py`: multi-turn session eval (ledger, rolling summary)
- `populate_human_eval_scores.py`: fill 50-case human eval sample from GPT golden eval (auto-scores + response export)

Quy trình đầy đủ: `../../docs/AI_EVALUATION_RUNBOOK.md` và `../../docs/ai/AI_RAG_RESEARCH_PROTOCOL.md`.
