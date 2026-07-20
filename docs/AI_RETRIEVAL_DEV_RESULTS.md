# AI retrieval dev results (v3)

## Kết luận

Sau khi làm giàu `menu.md`, chuẩn hóa normalize tiếng Việt, so sánh **7 phương pháp**
(BM25 + 3 encoder × dense/hybrid) và áp dụng bộ lọc menu giống production vào eval,
**`hybrid_e5_small`** được chọn cho production:

- MRR@5 dev cao nhất (`0.8723`), Hit@10 dev `0.9909`, forbidden@10 = `0`
- Encoder ~120MB — phù hợp VPS 4 vCPU / 8GB RAM

Frozen test (235 case, mở một lần) xác nhận **`hybrid_e5_small`** vẫn dẫn MRR@5
(`0.7883` sau khi áp dụng menu filters; trước đó `0.7744`) với **forbidden@10 = 0**
và latency thấp hơn ~2× so với `hybrid_vi_bi`.

| Phương pháp (test) | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | forbidden@10 | p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid_e5_small | 0.7238 | 0.9048 | **0.7883** | **0.6664** | **0** | 27.8ms |
| hybrid_vi_bi (chưa filter) | 0.6429 | 0.9381 | 0.7619 | 0.5848 | 0.048 | 60.0ms |

Artifact test: `ai/evaluation/results/test_hybrid_e5_small_filtered.json`

## Kết quả dev v3 (110 case, đã áp dụng menu filters)

| Phương pháp | Hit@1 | Hit@5 | Hit@10 | MRR@5 | nDCG@5 | forb@10 | p50 | p95 | RAM est. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 0.7545 | 0.9273 | 0.9545 | 0.8176 | 0.6420 | 0 | 1.8ms | 2.9ms | — |
| dense_e5_small | 0.7455 | 0.9273 | 0.9545 | 0.8142 | 0.6529 | 0 | 17.0ms | 22.8ms | 120MB |
| dense_mpnet | 0.6000 | 0.8000 | 0.8182 | 0.6824 | 0.4871 | 0 | 34.2ms | 44.0ms | 420MB |
| dense_vi_bi | 0.6545 | 0.8909 | 0.9182 | 0.7498 | 0.5264 | 0 | 34.6ms | 47.6ms | 540MB |
| **hybrid_e5_small** | **0.8091** | 0.9636 | 0.9909 | **0.8723** | **0.7089** | 0 | 23.6ms | 81.5ms | 120MB |
| hybrid_mpnet | 0.8000 | 0.9273 | 0.9636 | 0.8480 | 0.6454 | 0 | 35.4ms | 51.6ms | 420MB |
| hybrid_vi_bi | 0.7909 | **0.9909** | **1.0000** | 0.8688 | 0.6614 | 0 | 39.5ms | 54.8ms | 540MB |

So với v2 (chưa filter menu), mọi phương pháp tăng Hit@1/MRR vì các case menu-category
và rejection giờ được lọc cùng logic với production (`app/rag/menu_query_filters.py`).

Encoder so sánh:
- `e5_small`: intfloat/multilingual-e5-small (384d)
- `mpnet_base`: paraphrase-multilingual-mpnet-base-v2 (768d) — thay thế e5-base/GTE do lỗi load; export cũ dùng tên `e5_base`/`dense_e5_base`
- `vi_bi`: bkai-foundation-models/vietnamese-bi-encoder (768d, PhoBERT)

## E2E golden chat eval (pipeline đầy đủ, không LLM)

Chạy `py -m evaluation.run_golden_chat_eval --split dev` — 234 golden case đi qua toàn bộ
pipeline production (constraint extraction, guardrails, menu grounding, fallback composer)
với `hybrid` + `e5_small`:

| Metric | Trước fix | Sau fix |
| --- | ---: | ---: |
| Safety flag recall | 0.256 | **1.000** |
| Forbidden suggestion rate | 0.030 | **0.000** |
| Source hit rate (file KB đúng trong retrieved) | — | 0.645 |
| Expected menu hit rate | 0.000 | 0.346 |

Fix chính từ E2E eval:
1. Thêm flag `ALLERGY_DISCLAIMER` khi phát hiện allergen + ngữ cảnh né tránh/dị ứng.
2. Loại món chứa allergen khỏi mọi gợi ý (`infer_allergen_excluded_menu_item_ids`).
3. Mở rộng `ORDER_CREATION_PATTERNS` (tiếng Anh: place order/submit cart/checkout; tiếng Việt: tính tiền, gửi bếp, bạn đặt).
4. Sửa nhãn dataset: `payment_faq` không còn yêu cầu `CUSTOMER_CONFIRMATION_REQUIRED` cho câu hỏi FAQ thuần túy; regenerate golden cases theo KB hiện tại (hết corpus drift).

Artifact: `ai/evaluation/results/golden_chat_e2e.json`

## E2E với LLM thật (Gemini)

Script: `py -m evaluation.run_golden_llm_eval --split dev --limit 30`

Metrics bổ sung so với E2E không LLM:

| Metric | Ý nghĩa |
| --- | --- |
| `llm_success_rate` | Gemini trả JSON hợp lệ (không timeout/429) |
| `grounding_pass_rate` | Không bịa món sau post-check |
| `faithfulness_mean` | Overlap câu trả lời ↔ context retrieve + menu |
| `composite_pass_rate` | Tổng hợp LLM + safety + grounding |
| `summary.llm_only` | Chỉ các case Gemini trả lời thành công |

So sánh retriever qua LLM (RQ5 pilot):

```bash
py -m evaluation.run_golden_llm_eval --split dev --limit 20 --compare-retrieval hybrid,bm25 --sleep-ms 2500
py scripts/report_golden_llm_e2e.py
```

Artifact: `ai/evaluation/results/golden_llm_eval.json`

Nếu gặp HTTP 429: tăng `--sleep-ms 2500` và `--max-retry 3`. Chỉ kết luận RQ5 khi `llm_success_rate ≥ 0.8`.

## Corpus changelog

| | v1 | v2/v3 |
| --- | --- | --- |
| Documents | 126 | 307 |
| menu.md | m_001–m_021 chi tiết, m_022+ sơ sài | Đủ 91 món, mô tả + tags + giá |
| Normalize | mỗi module tự normalize | `normalize_query_text()` dùng chung |
| Golden cases | sinh theo KB cũ (drift) | regenerate theo KB hiện tại |

## Protocol

- Artifact đầy đủ: `ai/evaluation/results/dev_retrieval_comparison.v3.json`
- Summary: `ai/evaluation/results/dev_retrieval_summary.v3.json`
- Notebook: `ai/notebooks/rag_retrieval_research.ipynb`
- Pairwise statistics: bootstrap + Wilcoxon + Holm trong JSON comparison
- Production env: `RAG_RETRIEVAL_METHOD=hybrid`, `AI_EMBEDDING_MODEL=e5_small`
- Eval menu cases áp dụng cùng bộ lọc category/rejection/allergen như production (`menu_query_filters`)
