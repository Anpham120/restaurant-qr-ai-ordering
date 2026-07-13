# AI/RAG Evaluation

Research package dùng chung cho BM25, neural embedding và hybrid:

- `datasets/query_families.v1.json`: nguồn authoring theo query family;
- `datasets/retrieval_cases.v1.jsonl`: case-level artifact đóng băng;
- `research_corpus.py`: snapshot 84 món và knowledge chunks;
- `retrieval_metrics.py`: Hit/Precision/Recall/MRR/nDCG theo cutoff;
- `behavior_metrics.py`: guardrail và forbidden-suggestion metrics;
- `statistical_tests.py`: bootstrap, McNemar, Wilcoxon và Holm;
- `run_research_baseline.py`: BM25 baseline trên dev split.

Quy trình chạy, cổng dữ liệu và quy tắc không mở test split nằm tại
`../../docs/AI_EVALUATION_RUNBOOK.md`.

