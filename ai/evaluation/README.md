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
- `run_research_baseline.py`: BM25 baseline trên dev split;
- `run_retrieval_experiment.py`: so sánh BM25, multilingual E5 và hybrid RRF
  trên cùng corpus/split/metrics.

Quy trình chạy, cổng dữ liệu và quy tắc không mở test split nằm tại
`../../docs/AI_EVALUATION_RUNBOOK.md`.
