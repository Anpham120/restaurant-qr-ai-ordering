# Thiết kế mở rộng notebook nghiên cứu AI nhà hàng

## Mục tiêu

Mở rộng `ai/notebooks/restaurant_ai_research_report.ipynb` để có chiều sâu
trình bày tương đương notebook cũ, trong khi giữ các ràng buộc mới: một
canonical catalogue duy nhất, số liệu có provenance, và production chỉ dùng
profile thắng trong artifact tương thích dữ liệu.

Notebook cũ `ai/notebooks/rag_retrieval_research.ipynb` được giữ làm tài liệu
tham khảo và không bị sửa/xóa trong phạm vi này.

## Nguyên tắc trình bày

Mỗi mục phải trả lời lần lượt: câu hỏi nghiên cứu, giả thuyết hoặc tiêu chí,
phương pháp, code tái lập, bảng/biểu đồ, nhận xét gồm quan sát–diễn giải–giới
hạn–quyết định kế tiếp. Chỉ số không có artifact hoặc hash tương thích phải
hiển thị `CHƯA ĐỦ BẰNG CHỨNG`, không được thay bằng số liệu minh họa.

Mọi view retrieval, single-turn, multi-turn, safety, availability đều lọc từ
`canonical_research_manifest.v1.json`. Các cell phải hiện version, số case và
hash KB/menu/catalogue trước khi tính metric.

## Khung báo cáo mở rộng

### Phần I — Bài toán và dữ liệu

1. Bài toán sản phẩm, rủi ro khi AI không hiểu ngữ nghĩa và câu hỏi nghiên cứu.
2. Khám phá KB: inventory 26 file, chủ đề, mục đích, câu hỏi khách, risk tier,
   chunking, ví dụ chunk/evidence thật.
3. Chuẩn hóa tiếng Việt: phân biệt normalize phục vụ BM25 với normalize phục vụ
   so khớp; demo before/after cho dấu, teencode, biến thể câu hỏi.
4. Canonical evaluation catalogue: cấu trúc case, taxonomy intent, view overlap,
   negative/adversarial/availability cases, hash và rule không thay tập test.

### Phần II — So sánh retrieval

5. Ba phương pháp: BM25, Dense E5-small, Hybrid RRF; trực giác, công thức,
   tham số cố định và điều kiện công bằng.
6. Đánh giá retrieval: Hit@1/Hit@5, MRR, nDCG, false positive, negative case,
   case study "BM25 cứu Dense" và ngược lại, error analysis, ablation normalize
   / variants, latency và heatmap. Chỉ đọc artifact cùng canonical hash.
7. Kết luận retrieval: quyết định retriever/evidence contract dùng ở pipeline.

### Phần III — Chatbot có ngữ cảnh

8. Evidence routing: menu factual, KB, recommendation, safe recovery;
   decision table và trace ba câu regression sản xuất.
9. Guardrails: prompt injection, fake ID, giá sai, món ngoài menu, dị ứng,
   state leakage; mapping guardrail → invariant → test.
10. Session memory: rolling summary vs typed state; ordinal, exclude, overwrite
    preference, đổi chủ đề, session isolation, state transition timeline.
11. Claim verifier: claim/evidence/ID resolution, unsupported claim và quy tắc
    không lưu AI text thành fact.
12. Ba pipeline nghiên cứu: `llm_first_v1`, `evidence_first_v2`,
    `planner_state_v3`; cùng dataset/model/budget, khác đúng thành phần cần đo.

### Phần IV — Thí nghiệm và lựa chọn

13. Giao thức tái lập: ba lượt với LLM, factual deterministic một lượt, hard
    gate và thứ tự tie-break.
14. Kết quả single-turn/multi-turn/safety/availability theo từng profile, có
    mẫu số/tử số, variance và error table.
15. So sánh model lịch sử được tách rõ với thí nghiệm kiến trúc hiện hành.
    DeepSeek primary; Luna là fallback duy nhất cho HTTP 429; biểu đồ model
    attempts/success/failure không lẫn availability với semantic quality.
16. Pipeline selection artifact: provenance, hash compatibility, winner/rejected
    safety, giải thích trade-off, trạng thái `RERUN REQUIRED` khi artifact cũ.

### Phần V — Production

17. Bản đồ notebook → runtime: `AI_PIPELINE_PROFILE`, DeepSeek/Luna policy,
    evidence ledger, typed state, log fields, CI gates.
18. Staging/production checklist, smoke ba câu regression, rollback, hạn chế,
    roadmap và kết luận cuối cùng.

## Biểu đồ và số liệu

Pandas Styler dùng cho inventory/trace/metric table; matplotlib+seaborn cho
distribution, latency, ablation, heatmap; Plotly dùng cho treemap, sunburst,
Sankey/parallel comparison; NetworkX dùng cho lineage/pipeline/state timeline.
Mỗi biểu đồ có ngay một markdown nhận xét bốn phần. Không dùng biểu đồ trang trí.

## Tương thích production

`run_pipeline_profile_eval.py` dùng catalogue chuẩn. `pipeline_selection.json`
phải có hash catalogue gồm manifest+KB+menu. `verify_pipeline_selection.py` và
workflow staging/production fail-closed nếu artifact, profile hoặc model policy
lệch. Artifact cũ không được chỉnh tay để khớp hash; phải chạy lại benchmark.

## Kiểm thử chấp nhận

- Notebook có tối thiểu 110 cell, ít nhất 60 markdown cell và đủ 18 mục.
- Mỗi Part có kết luận/chuyển tiếp; mỗi cell chart/table số liệu có nhận xét.
- Không có mojibake, fabricated metric, hay winner hardcode.
- Generator, canonical contract, workflow gate và notebook execute thành công.
- Legacy và canonical notebook là hai file `.ipynb` duy nhất cho đến khi chủ sở
  hữu phê duyệt cleanup.
