# AI/RAG evaluation runbook

## Mục đích

Runbook này quy định cách audit dataset/corpus, chạy baseline và bảo vệ frozen
test split trước khi so sánh BM25, neural embedding và hybrid. Thiết kế nghiên
cứu đầy đủ nằm trong `AI_LLM_RAG_REFACTOR_PLAN.md`.

## Nguồn dữ liệu

- Family source: `ai/evaluation/datasets/query_families.v1.json`.
- Case-level JSONL: `ai/evaluation/datasets/retrieval_cases.v1.jsonl`.
- Menu snapshot: `backend/data/menu-dataset.json`.
- Knowledge base: `ai/knowledge-base`.

Family source và JSONL phải khớp tuyệt đối. Audit sinh SHA-256 cho cả hai file và
corpus; notebook phải ghi các hash này vào manifest kết quả.

## Audit trước thí nghiệm

Từ repository root:

```bash
PYTHONPATH=ai python ai/evaluation/audit_research_dataset.py
```

Audit thất bại khi:

- family ID hoặc normalized query bị trùng;
- paraphrase family không có split hợp lệ;
- selector không khớp document thật;
- expected và forbidden document giao nhau;
- JSONL khác family source;
- thiếu intent bắt buộc;
- dataset ít hơn 350 case.

## BM25 baseline

Chỉ chạy dev trong quá trình phát triển:

```bash
PYTHONPATH=ai python ai/evaluation/run_research_baseline.py --split dev --top-k 10
```

Runner dùng hai index tách biệt cho menu và knowledge, nhưng cùng BM25
implementation production. Output chứa dataset/corpus hash, metrics và latency.

Frozen test chỉ được mở sau khi khóa tokenizer, hyperparameter và decision rule:

```bash
PYTHONPATH=ai python ai/evaluation/run_research_baseline.py \
  --split test --top-k 10 --allow-frozen-test
```

Không dùng `--allow-frozen-test` để tuning.

Quy tắc này cũng được cưỡng chế trong Python API: caller phải truyền
`allow_frozen_test=True`; không thể lách bằng notebook hoặc import trực tiếp.

## Metrics bắt buộc

Retrieval, tại cutoff 1/3/5/10:

- Hit rate;
- Precision;
- Recall;
- MRR tại đúng cutoff;
- nDCG;
- forbidden-document hit rate.

Behavior:

- guardrail precision/recall/F1 trên các case có expected hoặc detected flag;
- exact flag match;
- forbidden suggestion rate.

True-negative không được cộng `1.0` vào macro guardrail F1; chúng chỉ đóng góp
vào exact flag match.

So sánh cặp phương pháp:

- paired bootstrap 10.000 vòng và CI 95%;
- McNemar exact cho hit/miss;
- Wilcoxon signed-rank cho per-query score/latency;
- Holm-Bonferroni cho nhiều phép so sánh.

Notebook và benchmark không được tự định nghĩa công thức metric khác. Chúng phải
gọi các module trong `ai/evaluation` để production decision và report dùng cùng
một phép đo.

Mỗi artifact baseline phải lưu Git SHA, dirty state + diff hash, timestamp UTC,
seed, Python/hardware,
retriever và tham số, SHA nguồn menu/knowledge base, cùng ranking, score, latency
và metrics của từng case để các phép so sánh cặp có thể audit lại.

`annotation_origin`, `review_status` và `reviewer_evidence` có default ở cấp
dataset nhưng được phép override ở từng family; materialized case phải giữ đúng
provenance sau khi parse.

## Verification

```bash
PYTHONPATH=ai python -m unittest discover -s ai/tests
python -m compileall ai/app ai/evaluation ai/tests
```

Không commit raw production chat, QR token, API key hoặc dữ liệu nhận dạng khách.
