# Lịch sử quyết định của hệ thống AI

> **Một tài liệu cho toàn bộ mảng này.** Gộp từ 2 tệp: `AI_DECISION_HISTORY.md`, `ADR_RETRIEVER_SELECTION.md`.
>
> Biên bản chọn bộ truy hồi (ADR) là MỘT quyết định trong lịch sử quyết định — để riêng thì người đọc phải biết trước là nó tồn tại mới tìm ra.


---

## Lịch sử quyết định

*(gộp từ `docs/ai/AI_DECISION_HISTORY.md`)*

> **Đây là tài liệu lịch sử, không phải mô tả cấu hình hiện hành.** Mọi con số dưới đây là số đo
> **tại thời điểm được ghi**, giữ lại để giải thích *vì sao* hệ thống có hình dạng hôm nay. Cấu hình
> đang chạy nằm ở `ai/.env.example`, kiến trúc ở `docs/AI_RAG_ARCHITECTURE.md`, và số liệu hiện hành
> ở `ai/notebooks/rag_llm_system_research.ipynb` + `docs/ai/BAO_CAO_DO_AN_HOC_MAY_KPDL.md`.
>
> File này hợp nhất bốn tài liệu đã gỡ: `AI_ASSISTANT_QUALITY_FIX_REPORT.md`,
> `AI_EVALUATION_REPORT.md`, `AI_RETRIEVAL_DEV_RESULTS.md`, `AI_LLM_RAG_REFACTOR_PLAN.md`.

---

### 1. Mô hình sinh: bốn lần đổi

| Giai đoạn | Cấu hình | Vì sao rời khỏi nó |
|---|---|---|
| Đầu tiên | Gemini | Đổi sang gateway 9router OpenAI-compatible để chạy được nhiều mô hình trên cùng một giao diện |
| Nghiên cứu | GPT-5.5 và DeepSeek chạy song song để so sánh | Chỉ là giai đoạn đo, không phải cấu hình triển khai |
| Kế tiếp | DeepSeek làm mô hình chính, GPT-5.6 Luna làm fallback khi HTTP 429 | **Route DeepSeek trong 9router từ chối `response_format:json_object`.** Toàn bộ pipeline dựa vào structured output, nên một mô hình không nhận `json_object` là không dùng được — không phải vấn đề chất lượng |
| **Hiện hành** | `cx/gpt-5.6-luna-review`, một mô hình duy nhất, **không** fallback | — |

Cơ chế fallback theo HTTP 429 (`_PrimaryRateLimited`, `fallback_enabled` trong `app/clients/router.py`)
vẫn còn trong mã và không phụ thuộc mô hình cụ thể; nó chỉ đang tắt. Khi tắt, dịch vụ báo
`model_policy.fallback_model = null` — đây là hợp đồng mà `deploy/scripts/health-check.sh` kiểm tra.

### 2. Chọn phương pháp truy hồi (đo trên tập dev v3, 110 case)

So sánh **7 phương pháp**: BM25, ba encoder dense (`e5_small` 384d/120MB, `mpnet_base` 768d/420MB,
`vi_bi` PhoBERT 768d/540MB) và ba biến thể hybrid RRF tương ứng. Luật chọn được **đăng ký trước khi
xem số**, và bộ lọc thực đơn giống production được áp vào eval để không đo một hệ thống khác với
hệ thống chạy thật.

`hybrid_e5_small` được chọn:

- MRR@5 dev cao nhất (`0,8723`), Hit@10 dev `0,9909`, `forbidden@10 = 0`
- Encoder ~120 MB — vừa với VPS 4 vCPU / 8 GB RAM

Tập test đóng băng (235 case, **mở đúng một lần**) xác nhận `hybrid_e5_small` vẫn dẫn MRR@5
(`0,7883` sau khi áp bộ lọc thực đơn; `0,7744` trước đó) với `forbidden@10 = 0` và độ trễ thấp hơn
khoảng 2× so với `hybrid_vi_bi`.

| Phương pháp (test) | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | forbidden@10 | p95 |
|---|---:|---:|---:|---:|---:|---:|
| `hybrid_e5_small` | 0,7238 | 0,9048 | **0,7883** | **0,6664** | **0** | 27,8 ms |
| `hybrid_vi_bi` (chưa filter) | 0,6429 | 0,9381 | 0,7619 | 0,5848 | 0,048 | 60,0 ms |

**Điểm đáng giữ về phương pháp:** phương án tốt nhất về chất lượng thuần tuý không trùng phương án
nên triển khai. `dense_e5_small` và `hybrid_vi_bi` dẫn đầu Hit@5, nhưng `hybrid_e5_small` được chọn
vì ràng buộc bộ nhớ và độ trễ trên VPS thật.

### 3. Vòng sửa chất lượng trợ lý — ba lỗi và một kết quả âm tính

Ba lỗi được chẩn đoán bằng cách in ra chính khối ngữ cảnh gửi cho mô hình, để loại giả thuyết
cạnh tranh "mô hình sai vì thiếu dữ liệu":

1. **Thẻ gợi ý giỏ hàng rỗng** dù đang tư vấn món — thẻ được dựng từ một danh sách khác với danh
   sách đã dùng để tạo claim; sửa bằng cách dựng thẻ từ chính danh sách `matched`.
2. **Quá dễ rơi vào "không chắc chắn"** — cổng abstain siết quá chặt.
3. **Ý định bị che bởi danh sách từ khóa chặn** — nhánh early-return theo keyword chạy bất kể độ
   tin cậy của bộ phân loại.

**Kết quả âm tính quan trọng — đã loại bỏ:** thay kiểm chứng khẳng định bằng **độ tương đồng nhúng**
là không khả thi. Dải cosine của nhóm khẳng định *bịa* chồng lấn hoàn toàn với nhóm diễn đạt *đúng*
(dải nén khoảng 0,82–0,95), và với lỗi sai số liệu thì khẳng định bịa còn xếp điểm **cao hơn** diễn
đạt đúng. Kiểm tra số học tất định được giữ lại.

**Nguyên tắc rút ra, vẫn đang áp dụng:** thuộc tính nào cần đảm bảo chắc chắn thì phải được thực thi
bằng cơ chế tất định. Các cơ chế "mềm" — chỉ dẫn trong prompt, độ tương đồng ngữ nghĩa — phù hợp để
cải thiện trải nghiệm, không phù hợp làm chốt chặn. Điều này được kiểm chứng lại nhiều lần: các thay
đổi prompt nhằm giảm hành vi hỏi lại quá mức của Luna cho hiệu quả bằng không và đã bị hoàn lại.

### 4. Chính sách đọc số liệu

- **Không dùng `composite_pass = 100%` làm kết luận.** `composite_pass` là phép AND của nhiều cổng;
  một con số 100% trên tập dev không nói gì về availability, faithfulness, mức đầy đủ của câu trả
  lời, human review hay tập test đóng băng.
- Chỉ số an toàn là **recall trên tập kiểm thử có chủ đích**, không phải precision trên lưu lượng
  thật.
- Độ trễ screening (1 lần đo/query) và độ trễ release-candidate (7 lần đo/query) **không so sánh
  trực tiếp** được với nhau.

### 5. Ranh giới kiến trúc đã chốt và vẫn giữ

- Backend .NET giữ quyền điều phối; dịch vụ AI Python có **một** pipeline duy nhất.
- **Hai chỉ mục tách biệt:** tri thức (FAQ, chính sách) và thực đơn trực tiếp. Thực đơn từ backend là
  nguồn sự thật duy nhất cho tên món, giá, tình trạng còn hàng, nhóm và nhãn. RAG chỉ truy hồi tri
  thức hỗ trợ; mô hình sinh chỉ diễn đạt trên tập ngữ cảnh đã được kiểm soát.
- AI **không** tự tạo đơn, không tự thêm giỏ, không tự xác nhận thanh toán. Mọi thẻ gợi ý mang cờ
  yêu cầu khách xác nhận.

### 6. Artifact lịch sử không còn trên đĩa

`ai/evaluation/results/` nằm trong `.gitignore`, nên artifact là **cục bộ và tái sinh được**, không
phải nội dung repo. Các tài liệu cũ từng trỏ tới những file sau, nay không còn tồn tại:

| Artifact được trích dẫn | Trạng thái |
|---|---|
| `dev_hybrid_e5_release_candidate.v1.json` | không còn; tái sinh bằng `run_retrieval_ablation.py` |
| `dual_model/20260723-9router-paired-18-final/comparison.json` | không còn; bản Luna vs GPT-5.5 hiện hành ở `dual_model/20260727T153207Z/` |
| `golden_llm_eval_cx_gpt55_v3_full_v3b.json` | không còn — artifact trước truth-reset |
| `golden_llm_eval_deepseek_v4_full.json` | không còn — artifact trước truth-reset |
| `test_hybrid_e5_small_filtered.json` | không còn; số ở mục 2 là bản ghi cuối |
| `golden_questions.csv` | đã gỡ khỏi repo |

Số liệu trong tài liệu này được giữ lại như **bản ghi**, không phải bằng chứng có thể xác minh lại
từ đĩa. Bằng chứng xác minh được của hệ thống hiện hành nằm trong 12 artifact còn lại và trong
notebook đã thực thi.

---

## ADR — chọn bộ truy hồi

*(gộp từ `docs/ai/ADR_RETRIEVER_SELECTION.md`)*

**Status:** Accepted (confirmed on frozen test, 2026-07-17)

**Date:** 2026-07-14 (updated 2026-07-17)

**Decision owners:** AI/RAG engineering
**Related history:** `docs/ai/AI_DECISION_HISTORY.md` §2 (luật chọn đăng ký trước)

### Context

Phase 3 evaluation required a registered, reproducible retriever choice before the
frozen test split was opened. Dev experiments on the selector-backed golden set
(`ai/evaluation/golden/cases.jsonl`) compared 7 methods (BM25, 3 dense encoders,
3 hybrid RRF variants) with paired statistical tests
(`docs/ai/AI_DECISION_HISTORY.md` §2).

The original 17-section notebook protocol (`llm_rag_retrieval_study.ipynb`) and its
successor (`rag_retrieval_research.ipynb`) were both retired; the retrieval
comparison now lives in Part II of `ai/notebooks/rag_llm_system_research.ipynb`,
executed end-to-end against the v3 artifacts.

### Decision

**Production retrieval method is `hybrid` (BM25 + dense `e5_small` via RRF)** as
implemented in `app.rag.retrieval_factory.build_retriever_stack`, confirmed by a
single frozen-test run with production menu filters applied
(`ai/evaluation/results/test_hybrid_e5_small_filtered.json`).

### Decision rule (Plan §5.5)

1. Eliminate any method that violates hard safety/grounding gates (§2.2).
2. Among survivors, select highest **nDCG@5 on dev**.
3. If 95% CIs overlap and McNemar/Wilcoxon show no significant difference, prefer lower
   p95 latency and simpler operations.
4. Lock configuration; run **frozen test exactly once**.
5. Ship to production only if test confirms hard gates and no significant regression vs
   BM25 baseline.

### Current state

| Item | Value |
| --- | --- |
| Production method | `hybrid` (BM25 + multilingual E5 small via RRF) |
| Encoder env | `AI_EMBEDDING_MODEL=e5_small` |
| Frozen test opened | Yes — one run, forbidden@10 = 0 |
| Phase 3 golden set | `ai/evaluation/golden/cases.jsonl` |
| Split manifest | `ai/evaluation/split_manifest.json` |
| Experiment entrypoint | `ai/evaluation/run_retrieval_experiment.py` |
| E2E behavior eval | `ai/evaluation/run_golden_chat_eval.py` |
| Legacy smoke eval | `ai/evaluation/run_evaluation.py` (hybrid default) |
| Research notebook | `ai/notebooks/rag_llm_system_research.ipynb` |

### Consequences

- Integration and assistant code default to hybrid retrieval with `e5_small`.
- Claims about retrieval quality reference the v3 artifacts:
  `ai/evaluation/results/dev_retrieval_summary.v3.json` and
  `ai/evaluation/results/test_hybrid_e5_small_filtered.json`.
- If future dev results reverse the ranking or fail gates, revert production default
  to BM25 per §5.5 step 5.

### Revisit triggers

- Frozen test regression vs BM25 on Hit@5, MRR@5, or nDCG@5 after corpus changes.
- Corpus hash change without re-benchmark (`split_manifest.json` SHA mismatch).
- New hard safety gate failure on adversarial set (`adversarial_injection_cases.jsonl`).
