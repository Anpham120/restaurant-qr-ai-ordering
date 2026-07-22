# Kế Hoạch Đánh Giá AI/RAG

## Bộ dữ liệu canonical

- **Quality gate:** `ai/evaluation/golden/cases.jsonl` (325 case, dev/test split)
- **CI smoke retrieval:** `ai/evaluation/golden/smoke_retrieval.jsonl`
- **Legacy archived:** `golden_questions.csv` (see `golden_questions.ARCHIVED.md`)

## Thước đo theo lớp

| Lớp | Script | KPI chính? |
| --- | --- | --- |
| E2E+LLM (9router) | `run_golden_llm_eval.py` | **Có** — composite_pass, grounding, faithfulness |
| Retrieval research | `run_retrieval_experiment.py` | Có (ADR retriever) |
| Pipeline no-LLM | `run_golden_chat_eval.py` | Không — CI smoke safety/forbidden |

## Chỉ số E2E+LLM

| Chỉ số | Ý nghĩa |
| --- | --- |
| composite_pass_rate | Tổng hợp safety + grounding + nội dung |
| grounding_pass_rate | Không bịa món |
| faithfulness_mean | Overlap câu trả lời ↔ context |
| llm_call_rate / by_intent | Tỷ lệ gọi LLM (FAQ nên giảm nhờ fast-path) |

## Quy trình

1. Unit tests: `py -m unittest discover -s ai/tests`
2. CI smoke: `py ai/evaluation/ci_golden_gates.py --run-smoke-eval`
3. Quality gate (manual): `py -m evaluation.run_dual_llm_eval --split dev --limit 234`
4. Failure taxonomy: `py ai/evaluation/export_llm_error_analysis.py`
5. Human sample: `py ai/evaluation/generate_human_eval_sample.py`

Chi tiết protocol: [`docs/ai/AI_RAG_RESEARCH_PROTOCOL.md`](ai/AI_RAG_RESEARCH_PROTOCOL.md)
