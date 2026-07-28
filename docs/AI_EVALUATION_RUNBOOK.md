# AI/RAG evaluation runbook

## Mục đích

Runbook này quy định cách audit dataset/corpus, chạy baseline và bảo vệ frozen
test split trước khi so sánh BM25, neural embedding và hybrid. Thiết kế nghiên
cứu đầy đủ nằm trong `docs/ai/AI_DECISION_HISTORY.md`.

## Nguồn dữ liệu

- Dev family source: `ai/evaluation/datasets/query_families.dev.v1.json`.
- Dev JSONL: `ai/evaluation/datasets/retrieval_cases.dev.v1.jsonl`.
- Frozen test source: `ai/evaluation/datasets/query_families.test.v1.json`.
- Frozen test JSONL: `ai/evaluation/datasets/retrieval_cases.test.v1.jsonl`.
- Menu snapshot: `backend/data/menu-dataset.json`.
- Knowledge base: `ai/knowledge-base`.

Family source và JSONL của mỗi split phải khớp tuyệt đối. Dev-run chỉ mở hai file
dev. Hai file test được tách vật lý, khóa bằng SHA-256 trong code và chỉ được mở
khi caller truyền cờ xác nhận. Notebook phải ghi hash dataset/corpus vào manifest.

Cài môi trường nghiên cứu đã pin phiên bản:

```bash
python -m pip install -r ai/requirements-evaluation.txt
```

## Audit trước thí nghiệm

Từ repository root:

```bash
PYTHONPATH=ai python ai/evaluation/audit_research_dataset.py
```

Audit mặc định chỉ parse dev labels; với test nó chỉ kiểm tra byte hash và kích
thước file. Audit thất bại khi:

- family ID hoặc normalized query bị trùng;
- paraphrase family không có split hợp lệ;
- selector không khớp document thật;
- expected và forbidden document giao nhau;
- JSONL khác family source;
- thiếu intent bắt buộc;
- dev ít hơn 125 case hoặc thiếu coverage cho danh mục Bia & Rượu;
- frozen test artifact khác hash đã khóa (235 case).

Materialize lại dev sau khi sửa family source:

```bash
PYTHONPATH=ai python ai/evaluation/materialize_research_datasets.py
```

## BM25 baseline

Chỉ chạy dev trong quá trình phát triển:

```bash
PYTHONPATH=ai python ai/evaluation/run_research_baseline.py --split dev --top-k 10
```

Runner dùng hai index tách biệt cho menu và knowledge, nhưng cùng BM25
implementation production. Output chứa dataset/corpus hash, metrics và latency.

## So sánh BM25, embedding và hybrid

Encoder được khóa tại `intfloat/multilingual-e5-small`, revision
`fd1525a9fd15316a2d503bf26ab031a61d056e98`, vector 384 chiều, dùng đúng prefix
`query:`/`passage:` và normalized embedding. Chạy cả ba phương pháp trên dev:

```bash
PYTHONPATH=ai python ai/evaluation/run_retrieval_experiment.py \
  --method all --split dev --top-k 10 \
  --output ai/evaluation/results/dev-retrieval-comparison.json
```

Mỗi retriever được warm-up tối đa 5 query cho từng target. Mỗi query được đo 7
lần, lấy median; thứ tự case và thứ tự phương pháp được shuffle bằng seed cố
định. Artifact ghi protocol, package versions, Git SHA/dirty diff hash và toàn bộ
per-query latency samples. Đây là benchmark warm trên một máy, không thay thế
load test production.

Frozen test chỉ được mở sau khi khóa tokenizer, hyperparameter và decision rule:

```bash
PYTHONPATH=ai python ai/evaluation/run_research_baseline.py \
  --split test --top-k 10 --allow-frozen-test
```

Không dùng `--allow-frozen-test` để tuning.

Quy tắc này cũng được cưỡng chế trong Python API: caller phải truyền
`allow_frozen_test=True`; không thể lách bằng notebook hoặc import trực tiếp.
Trước lần đánh giá test duy nhất, ghi commit SHA và decision rule vào tài liệu,
kiểm tra hai frozen SHA-256, sau đó chạy `run_retrieval_experiment.py --method
all --split test --allow-frozen-test` đúng một lần. Audit đầy đủ test cũng cần
`audit_research_dataset.py --include-frozen-test`.

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
- McNemar exact cho hit/miss, kèm paired rate-delta bootstrap CI;
- Wilcoxon signed-rank cho per-query score/latency, kèm rank-biserial effect và
  paired median-delta bootstrap CI;
- Holm-Bonferroni cho nhiều phép so sánh.

Notebook và benchmark không được tự định nghĩa công thức metric khác. Chúng phải
gọi các module trong `ai/evaluation` để production decision và report dùng cùng
một phép đo.

Mỗi artifact baseline phải lưu Git SHA, dirty state + diff hash, timestamp UTC,
seed, Python/hardware, exact package versions, retriever và tham số, SHA nguồn
menu/knowledge base, cùng ranking, score, latency
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
