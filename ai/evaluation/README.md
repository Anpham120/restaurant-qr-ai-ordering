# AI/RAG Evaluation

Research package dùng chung cho BM25, neural embedding và hybrid:

- `datasets/query_families.dev.v1.json`: nguồn authoring chỉ dành cho tuning;
- `datasets/retrieval_cases.dev.v1.jsonl`: case-level artifact của dev split;
- `datasets/query_families.test.v1.json` và `retrieval_cases.test.v1.jsonl`:
  frozen test artifacts được bảo vệ bằng SHA-256 và không được load trong dev-run;
- `materialize_research_datasets.py`: materialize dev mặc định; test cần cờ xác nhận;
- `research_corpus.py`: snapshot đủ 91 món (bao gồm đồ uống) và knowledge chunks;
- `retrieval_metrics.py`: Hit/Precision/Recall/MRR/nDCG theo cutoff;
- `behavior_metrics.py`: guardrail và forbidden-suggestion metrics;
- `statistical_tests.py`: bootstrap, McNemar, Wilcoxon và Holm;
- `run_research_baseline.py`: BM25 baseline trên dev split (menu cases áp dụng
  cùng bộ lọc category/rejection/allergen như production qua `menu_query_filters`);
- `run_retrieval_experiment.py`: so sánh BM25, 3 dense encoders (e5-small, MPNet-base, vi-bi)
  và 3 hybrid RRF tương ứng trên cùng corpus/split/metrics.
- `summarize_retrieval_comparison.py`: rút gọn JSON comparison thành summary v2.
- `run_golden_chat_eval.py`: E2E chat eval — chạy golden cases qua toàn bộ pipeline
  production (không LLM) và đo safety flag recall, forbidden suggestion rate,
  chunk/source hit rate. Artifact: `results/golden_chat_e2e.json`.
- `run_golden_llm_eval.py`: E2E chat eval **có Gemini thật** — thêm
  `llm_success_rate`, `grounding_pass_rate`, `faithfulness_mean`, `composite_pass_rate`;
  tùy chọn `--with-judge` (LLM-as-judge rubric) và `--compare-retrieval hybrid,bm25`.
  Artifact: `results/golden_llm_eval.json`.
- `llm_eval_metrics.py`: rule-based LLM quality scoring (faithfulness overlap,
  allergy/price refusal checks, menu grounding).
- `generate_golden_cases.py`: regenerate `golden/cases.jsonl` theo KB hiện tại
  (chạy lại sau khi sửa `knowledge-base/` để tránh corpus drift).

Quy trình chạy, cổng dữ liệu và quy tắc không mở test split nằm tại
`../../docs/AI_EVALUATION_RUNBOOK.md`.

Legacy smoke eval (100 curated cases, guardrail + retrieval):
- `golden_questions.csv`: 100 case thủ công (allergy, budget, guardrails, tiếng Anh/không dấu, …)
- `run_evaluation.py`: mặc định dùng **hybrid + e5_small** (giống production); `--method bm25` để so sánh
