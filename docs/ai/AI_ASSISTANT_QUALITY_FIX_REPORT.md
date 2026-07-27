# BÁO CÁO: SỬA 3 VẤN ĐỀ CHẤT LƯỢNG AI ASSISTANT — CONTEXT, ABSTAIN, CART-SUGGESTION

> Phạm vi: rebuild có mục tiêu vào lớp ra quyết định của AI service (`ai/app/`) —
> giữ nguyên retrieval pipeline, typed contracts và test/eval harness đang chạy tốt.
> Nguyên tắc báo cáo: chỉ ghi "đã đo" khi có artifact thật (test/eval chạy thật);
> nội dung chưa đo được đánh dấu riêng. Nhịp trình bày mỗi mục theo đúng phong cách
> notebook nghiên cứu của dự án (`ai/notebooks/rag_retrieval_research.ipynb`):
> mục tiêu → nguyên lý → code thật → artifact thật → phân tích → quyết định.

---

## 1. Mục tiêu

Người vận hành báo cáo 3 vấn đề khi dùng chatbot thật:

1. AI gợi ý không hiểu ngữ cảnh câu hỏi.
2. AI dễ rơi vào trạng thái "không chắc chắn" khi trả lời (abstain).
3. AI tư vấn món ăn nhưng thường không hiện card "suggested cart" để khách thêm vào giỏ.

Mục tiêu của lần sửa này: xác định nguyên nhân gốc từng vấn đề bằng cách đọc trực
tiếp mã nguồn (không suy đoán), sửa đúng root cause, và kiểm chứng bằng test/eval
thật trước khi kết luận đã cải thiện.

---

## 2. Phương pháp chẩn đoán

Đọc trực tiếp `ai/app/services/assistant.py` (2319 dòng — orchestrator chính),
`ai/app/rag/conversation_policy.py`, `intent_routing_signals.py`,
`llm_intent_classifier.py`, `claim_verifier.py`, `menu_presence_fast_path.py`,
`prompts.py`, `content_grounding.py`, cùng artefact đã duyệt
`ai/evaluation/approved/pipeline_selection.json`. Mỗi giả thuyết nguyên nhân đều
được xác nhận bằng cách trích dẫn file:dòng cụ thể trước khi sửa, không phải suy
đoán chung chung.

**Phát hiện nền tảng quan trọng nhất trước khi sửa bất cứ gì**: production chạy
`AI_PIPELINE_PROFILE=evidence_first_v2` (`ai/app/config.py:12`), không phải
`planner_state_v3` — cơ chế hiểu ngữ cảnh mạnh nhất trong code (semantic planner,
referent resolution qua LLM ở `ai/app/rag/semantic_planner.py`) là dead code ở
production hiện tại, vì tiêu chí chọn profile (`selection_reason` trong
`pipeline_selection.json`) ưu tiên `strict_semantic_success` trước
`context_accuracy`.

---

## 3. Vấn đề 3 — Cart-suggestion rỗng dù đang tư vấn món

### 3.1 Nguyên lý (chẩn đoán)

Hai đường code liệt kê tên món + giá trong `content` nhưng hard-code
`suggested_cart_actions: []`:

- `ai/app/rag/menu_presence_fast_path.py` (trả lời "có món X không?") — tham số
  `wants_recommendations` được truyền vào hàm nhưng **không được dùng ở đâu cả**,
  dấu hiệu rõ đây là bug bỏ sót.
- `ai/app/services/assistant.py::_try_catalog_fast_path` (liệt kê món theo danh
  mục) — cũng hard-code `[]`, và **đang active ở production** vì
  `_should_use_evidence_first_menu_paths()` trả `True` với profile
  `evidence_first_v2`.

Thêm một nguyên nhân độc lập: `conversation_policy.py` (dòng 292-297, bản gốc)
gán `wants_recommendations=False` cho bất kỳ câu nào khớp `is_category_listing_query`
(ví dụ chứa "co mon"), **không kiểm tra** liệu câu đó cũng chứa tín hiệu xin gợi ý
(`RECOMMENDATION_TERMS` như "nao ngon", "goi y"). Câu thật như "có món hải sản nào
ngon không" vừa khớp category-listing vừa có "nao ngon" — nhưng logic cũ chỉ nhìn
điều kiện đầu, khiến prompt ép model trả `suggested_cart_actions: []`
(`prompts.py:231-235` bản gốc).

### 3.2 Code thật

```python
# ai/app/rag/menu_presence_fast_path.py — trước
"suggested_cart_actions": [],

# sau — build từ chính danh sách "matched" đã dùng để tạo claims/lines
suggested_cart_actions = []
for item in cited_items[:MAX_CART_SUGGESTIONS]:
    ...
    suggested_cart_actions.append({
        "menu_item_id": item_id, "name": ..., "price_vnd": ...,
        "quantity": 1, "reason": build_suggestion_reason(item, seed=item_id),
        "requires_customer_confirmation": True,
    })
```

```python
# ai/app/rag/conversation_policy.py — thêm guard
elif (
    category
    and is_category_listing_query(normalized_message)
    and not _is_explicit_order(normalized_message)
    and not any(_contains_term(normalized_message, term) for term in RECOMMENDATION_TERMS)
    and not any(_contains_term(normalized_message, term) for term in GROUP_RECOMMENDATION_TERMS)
):
    wants_recommendations = False
```

`_try_catalog_fast_path` trong `assistant.py` được sửa tương tự, tái sử dụng
helper `build_suggestion_reason()` đã có sẵn trong `menu_exclusions.py` (cùng
pattern với `build_prior_suggestion_actions()` đang dùng trong production).

### 3.3 Artifact thật

- `ai/tests/test_menu_presence_policy.py`, `test_catalog_listing_path.py`: thêm
  assertion `suggested_cart_actions` không rỗng, `menu_item_id` đúng món đã liệt kê.
- `ai/tests/test_conversation_policy.py::test_category_listing_with_recommendation_cue_still_wants_recommendations`:
  test case đúng bug gốc ("có món hải sản nào ngon không" → `wants_recommendations=True`).
- Toàn bộ test suite (§6) pass sau khi sửa.

### 3.4 Phân tích

Vấn đề 3 nối trực tiếp với Vấn đề 2: biến `candidate_menu_items` dùng để vừa điền
card vừa làm evidence cho claim verifier (`assistant.py:1326-1330`) — sửa cart-
suggestion cũng gián tiếp giảm tần suất abstain, vì cơ chế "cứu" abstain hiện có
(`_apply_parsed_response`, dòng 1345-1353) chỉ hoạt động khi đã có card.

---

## 4. Vấn đề 2 — Dễ rơi vào "không chắc chắn"

### 4.1 Nguyên lý (chẩn đoán)

`ai/app/rag/claim_verifier.py::_verify_one` yêu cầu overlap từ vựng thô (Jaccard)
≥ 25% giữa `claims[].text` và evidence. Điều này **mâu thuẫn trực tiếp** với chỉ
dẫn ở `prompts.py:28-29` (bản gốc): "RAG context là TÀI LIỆU THAM KHẢO... hãy DIỄN
ĐẠT LẠI... KHÔNG copy-paste nguyên văn". Câu trả lời paraphrase tự nhiên (đúng theo
prompt) dễ tụt dưới ngưỡng 25% vì dùng từ đồng nghĩa/cách diễn đạt khác.

### 4.2 Thử nghiệm đã làm và bị loại bỏ (artifact thật — kết quả âm tính quan trọng)

Giả thuyết sửa ban đầu: thêm tầng "OR" — nếu lexical overlap thất bại, chấp nhận
claim khi embedding cosine similarity (multilingual-e5-small, đã có sẵn trong
`ai/app/rag/embedding_retriever.py`) vượt ngưỡng calibrate.

**Calibrate bằng script thật** (evidence: "Nhà hàng mở cửa lúc 08:00 mỗi ngày."):

| Claim | Lexical ratio | Cosine similarity |
|---|---:|---:|
| Paraphrase đúng: "Quý khách hoàn toàn có thể ghé quán dùng bữa ngay từ đầu buổi sáng." | 0,071 | **0,8729** |
| Bịa, mâu thuẫn: "Nhà hàng đóng cửa vào lúc nửa đêm mỗi ngày." | 0,667 | **0,9104** |
| Bịa, không liên quan: "Nhà hàng có chương trình miễn phí bánh sinh nhật..." | 0,250 | 0,8499 |
| Bịa, lexical thấp: "Buổi tối muộn quán sẽ không tiếp đón thực khách nữa." | 0,000 | 0,8658 |

**Kết luận (đã đo, không suy đoán)**: claim bịa "đóng cửa lúc nửa đêm" có cosine
similarity (0,9104) **cao hơn** paraphrase đúng (0,8729) — không có ngưỡng nào
tách được đúng/sai cho cặp câu ngắn tiếng Việt này với e5-small. Cơ chế semantic
fallback bị **loại bỏ** vì sẽ làm yếu bộ lọc chống bịa, rủi ro hơn cả lỗi ban đầu.

### 4.3 Root cause fix thật (đã áp dụng)

Xác minh trước khi sửa: `claims[].text` là **hoàn toàn nội bộ** — backend .NET
(`ChatAssistantReply` trong `ChatContracts.cs`) không có field `Claims`, tầng
`ChatAiProvider.BuildAssistantReply` loại bỏ nó trước khi trả cho frontend.
Frontend (`ChatbotPage.tsx`) chỉ đọc `content` và `suggestedCartActions`.

→ Vì khách không bao giờ thấy `claims[].text`, sửa đúng root cause ở tầng sinh
câu trả lời (`prompts.py`): tách rõ 2 quy tắc —
- `content` (khách đọc): tiếp tục diễn đạt tự nhiên như cũ.
- `claims[].text` (nội bộ, dùng để verify): phải **bám sát từ ngữ và số liệu
  trong evidence**, không diễn đạt lại.

```python
# ai/app/rag/prompts.py — thêm vào SYSTEM_POLICY
"- Quy tắc diễn đạt lại này áp dụng cho \"content\" (câu khách sẽ đọc). "
"\"claims[].text\" KHÔNG áp dụng quy tắc này — xem hướng dẫn riêng cho claims..."
...
"claims[].text KHÔNG hiển thị cho khách — chỉ dùng để hệ thống kiểm chứng nội bộ. "
"Viết claims[].text BÁM SÁT từ ngữ và số liệu trong evidence được trích..."
```

`claim_verifier.py` giữ nguyên logic lexical-only ban đầu (không nới lỏng) —
kèm ghi chú trong code giải thích vì sao semantic fallback bị loại, để tránh ai
đó thử lại cùng cách tiếp cận mà không biết đã calibrate và thất bại.

### 4.4 Artifact thật

- `ai/tests/test_claim_verifier.py`: giữ 3 test gốc pass nguyên; đổi 1 test
  (`test_loose_paraphrase_is_rejected_by_design`) để ghi lại quyết định thiết kế
  thay vì coi là "bug".
- `ai/tests/test_claim_text_policy.py` (mới): smoke test đảm bảo hướng dẫn mới
  trong `SYSTEM_POLICY` không bị xoá nhầm trong tương lai.
- **Giới hạn quan trọng**: liệu model có tuân thủ hướng dẫn mới hay không (viết
  `claims[].text` sát evidence) chỉ kiểm chứng được bằng LLM thật — xem §7 (C3).

### 4.5 Phân tích

Đây là ví dụ cụ thể về nguyên tắc "không bịa số" của dự án áp dụng vào chính quá
trình sửa lỗi: giả thuyết ban đầu (embedding similarity) trông hợp lý nhưng calibrate
thật cho thấy sai; quyết định đúng là loại bỏ nó thay vì hạ ngưỡng cho "vừa đủ pass"
2-3 test tự chọn.

---

## 5. Vấn đề 1 — AI không hiểu ngữ cảnh / intent kém

### 5.1 Nguyên lý (chẩn đoán)

`ai/app/rag/llm_intent_classifier.py::is_ambiguous` có các early-return theo
keyword-blacklist (`INFO_MARKER_TERMS`, `CATALOG_TERMS`, `RECOMMENDATION_TERMS`):
chỉ cần câu hỏi chứa **một** từ khoá chung (vd "wifi", "gio") là hàm coi rule-based
classifier "chắc chắn đúng" và bỏ qua LLM-assist — bất kể rule classifier có
confidence thấp hay không. Đây không phải kiểm tra độ tin cậy thật, mà là danh
sách loại trừ.

### 5.2 Code thật

```python
# trước: early-return theo keyword bất kể confidence
if any(term in normalized for term in INFO_MARKER_TERMS):
    return False
if any(term in normalized for term in CATALOG_TERMS):
    return False
if any(term in normalized for term in RECOMMENDATION_TERMS):
    return False

# sau: bỏ hẳn 3 early-return theo keyword; giữ EXPLICIT_PARTY_PATTERN
# (tín hiệu cấu trúc thật, không phải keyword chung) và dựa vào
# AMBIGUITY_CONFIDENCE_THRESHOLD làm tín hiệu chính
```

### 5.3 Artifact thật — phát hiện cụ thể khi chạy test thật

`classify_intent_with_history("wifi mat khau gi", [])` trả về
`intent='restaurant_info', confidence=0.3` — **đúng intent** nhưng confidence
(0.3) **thấp hơn** ngưỡng `AMBIGUITY_CONFIDENCE_THRESHOLD=0.35`. Trước đây câu này
"không ambiguous" chỉ vì khớp từ khoá "wifi" trong blacklist, không phải vì rule
classifier tự tin. Sau khi bỏ blacklist, câu này đúng ra được gắn cờ ambiguous và
nhận thêm một lượt LLM-assist rẻ (max_tokens=180, temperature=0) để xác nhận —
đúng như thiết kế ban đầu của cơ chế `is_ambiguous`.

→ Cập nhật 2 test phản ánh hành vi mới:
`test_llm_intent_classifier.py::test_wifi_query_with_borderline_confidence_gets_llm_assist`,
`test_intent_eval_scoring.py::test_wifi_borderline_confidence_now_routes_to_llm_assist`.

### 5.4 Phân tích

Đây là ví dụ ngược lại với §4: cùng một nguyên tắc "bỏ shortcut, dựa vào tín hiệu
thật" áp dụng đúng ở đây (confidence-based gating hoạt động tốt hơn keyword
blacklist), trong khi ở §4 (embedding similarity) áp dụng sai vì tín hiệu thay
thế (cosine similarity) không đủ tin cậy. Bài học: mỗi cơ chế thay thế phải được
calibrate riêng bằng dữ liệu thật, không suy diễn từ nguyên tắc chung.

**Chưa sửa trong lần này** (để dành đo bằng §7): promotion `planner_state_v3` lên
production — vì Workstream A/B/C1 sửa code dùng chung bởi cả 3 profile
(`conversation_policy.py` đặc biệt), số liệu `context_accuracy`/
`strict_semantic_success` trong `pipeline_selection.json` (đo trước khi sửa) đã
lỗi thời và cần đo lại trước khi quyết định đổi profile mặc định.

---

## 6. Kiểm thử tổng hợp (offline, đã chạy thật)

| Kiểm tra | Trước | Sau |
|---|---|---|
| `python -m unittest discover -s tests` | *(không đo được — môi trường chưa có Python khi bắt đầu, xem §9)* | **397 passed, 0 failed** |
| `run_session_e2e_eval.py` (offline, không gọi LLM) | báo cáo cũ: context 1200/1200, referent 150/150, no-dup 50/50, allergy 50/50 | **context 1200/1200, referent 150/150, no-dup 50/50, valid-action 50/50, allergy fail-closed 50/50** — không regression |

---

## 7. C3 — So sánh lại 3 pipeline profile bằng LLM thật

### 7.1 Mục tiêu và giới hạn quan trọng cần đọc trước

Đo lại `context_accuracy`/`strict_semantic_success`/latency cho 3 profile sau khi
Workstream A/B/C1 sửa code dùng chung (`conversation_policy.py`,
`llm_intent_classifier.py`, `prompts.py`). **Route DeepSeek
(`oc/deepseek-v4-flash-free`) trong tài khoản 9router test trả lỗi `400 Upstream
request failed`** khi gửi kèm `response_format:json_object` (field mà mọi request
thật của hệ thống đều cần) — đã cô lập bằng 3 lần test payload tăng dần, xác nhận
chính field này là nguyên nhân, không phải bug trong `RouterClient`. Đã xác nhận
với người vận hành: đây là tài khoản/route **test riêng**, không phải production
(production dùng key và 9router instance khác trên VPS).

→ Chạy bằng **`cx/gpt-5.6-luna-review`** thay cho DeepSeek (script gốc
`run_pipeline_profile_eval.py` hard-code `DEEPSEEK_MODEL`; đã monkey-patch hằng số
này ở một script driver riêng, không sửa file gốc, ghi output ra file riêng
`pipeline_selection.luna_probe.json` — không đụng tới artefact đã duyệt).

**Vì đổi model, số liệu dưới đây KHÔNG so sánh trực tiếp về giá trị tuyệt đối
được với `ai/evaluation/approved/pipeline_selection.json` gốc (đo bằng
DeepSeek).** Sự khác biệt giữa 2 lần đo có thể đến từ (a) code đã sửa, hoặc (b)
model khác hoàn toàn (GPT-5.6 Luna vs DeepSeek) — không tách được hai nguồn này
trong lần chạy này.

### 7.2 Artifact thật

Nguồn: `ai/evaluation/results/pipeline_selection.luna_probe.json` (19 test case,
model=`cx/gpt-5.6-luna-review`, `working_tree_dirty=true` — đúng thực tế vì có
thay đổi chưa commit).

| Profile | strict_semantic_success | context_accuracy | p95 latency (ms) | mean LLM calls | Safety gates |
|---|---:|---:|---:|---:|---|
| `llm_first_v1` | 0,8627 | 0,8529 | 18.225,7 | 2,12 | ✅ pass hết |
| `evidence_first_v2` | 0,9388 | 0,8469 | 20.041,1 | 2,08 | ✅ pass hết |
| `planner_state_v3` | **0,9623** | **0,9151** | 47.502,4 | 2,38 | ✅ pass hết |

`winner` (theo tiêu chí `safety_gate_then_strict_quality_then_context_then_p95_latency_then_llm_calls`):
**`planner_state_v3`** — lần chạy DeepSeek gốc trước đây chọn `evidence_first_v2`.

Mọi safety gate (`allergy_passed`, `id_price_passed`, `session_isolation_passed`,
`assistant_text_not_persisted`, `availability_passed`, `safety_passed`) đều
**pass** cho cả 3 profile, và `unsupported_claims=0` cho cả 3 — claim verifier
(§4) không để lọt claim nào kể cả sau khi đổi model và đổi prompt.

### 7.3 Phân tích

- `context_accuracy` của `planner_state_v3` (0,9151) vẫn cách biệt rõ so với
  `evidence_first_v2` (0,8469) — khoảng cách tương tự lần đo gốc bằng DeepSeek
  (0,9340 vs 0,8404). Vì Workstream A/B/C1 không đụng vào `semantic_planner.py`,
  kết quả này đúng như kỳ vọng — không phải bằng chứng các fix "cải thiện" context,
  mà là bằng chứng các fix **không phá vỡ** lợi thế context sẵn có của
  `planner_state_v3`.
- `planner_state_v3` thắng ở lần chạy này chủ yếu vì `strict_semantic_success`
  tăng mạnh so với lần đo gốc (0,9057 → 0,9623) — nhiều khả năng do GPT-5.6 Luna
  tuân thủ structured-output/JSON schema tốt hơn DeepSeek cho luồng 2-lệnh-gọi của
  `planner_state_v3` (semantic planner + generation), chứ không chắc chắn do các
  fix trong lần này. **Không đủ căn cứ để kết luận thứ hạng sẽ đảo ngược tương tự
  khi chạy lại bằng DeepSeek thật.**
- `p95_latency_ms` của `planner_state_v3` tăng vọt lên 47.502ms (gần gấp đôi lần
  đo gốc 25.936ms) — phù hợp với việc GPT-5.6 Luna có latency cao hơn DeepSeek
  (đã ghi nhận trong so sánh dual-model cũ: p50 GPT-5.5 ≈ 7.351ms vs DeepSeek ≈
  5.511ms) nhân với 2 lệnh gọi LLM mỗi lượt của profile này. Đây là rủi ro thật
  cần cân nhắc nếu có ý định promote `planner_state_v3`, độc lập với việc dùng
  model nào.
- Field tên `deepseek_call_success_rate` trong artifact **gây hiểu nhầm** cho lần
  chạy này — thực chất đo tỉ lệ gọi thành công của `cx/gpt-5.6-luna-review` (do
  monkey-patch `DEEPSEEK_MODEL`), không phải DeepSeek thật. Không sửa tên field
  trong script gốc vì đây là driver tạm thời, không phải thay đổi chính thức.

### 7.4 Quyết định

**Chưa** đủ căn cứ để đổi `AI_PIPELINE_PROFILE` mặc định sang `planner_state_v3`
dựa trên lần chạy này — do nhiễu bởi việc đổi model. Khuyến nghị cụ thể: chạy lại
đúng `ai/evaluation/run_pipeline_profile_eval.py` **không sửa gì** (dùng DeepSeek
thật) sau khi route DeepSeek trong 9router được khắc phục, rồi so sánh trực tiếp
với `pipeline_selection.json` đã duyệt hiện tại. Nếu `context_accuracy` của
`planner_state_v3` vẫn vượt trội và `strict_semantic_success` không còn thua kém
`evidence_first_v2` bằng DeepSeek thật, đó mới là căn cứ đủ để cân nhắc đổi profile
— cùng với việc đánh giá đánh đổi latency (p95 ~26-47s tuỳ model là khá cao cho
chat UX thời gian thực, cần thêm dữ liệu SLO trước khi quyết định).

---

## 8. Kết luận & quyết định

Đã merge (uncommitted, chờ review):

1. Cart-suggestion không còn rỗng khi liệt kê món (`menu_presence_fast_path.py`,
   `_try_catalog_fast_path`).
2. Câu vừa hỏi danh mục vừa xin gợi ý không còn bị tắt nhầm gợi ý
   (`conversation_policy.py`).
3. Root cause mâu thuẫn "diễn đạt lại vs. verify" được sửa ở tầng prompt
   (`prompts.py`), không làm yếu `claim_verifier.py`.
4. `is_ambiguous` không còn bị keyword blacklist che giấu confidence thấp
   (`llm_intent_classifier.py`).
5. **Đổi model chính thức của dự án từ DeepSeek sang `cx/gpt-5.6-luna-review`**
   (`ai/app/config.py::DEFAULT_LLM_MODEL`, `.env.example`, `ai/.env`,
   `scripts/smoke_9router.py`) — quyết định của người vận hành sau khi xác nhận
   route DeepSeek không dùng được. Tắt luôn 429-failover (`LLM_RATE_LIMIT_FALLBACK_ENABLED=false`)
   vì không còn model phụ để fallback tới; validation cứng "DeepSeek primary +
   Luna fallback" trong `load_config()` được giữ nguyên (không xoá) nên nếu ai
   bật lại fallback mà không cấu hình đúng cặp model sẽ luôn bị chặn bằng lỗi rõ
   ràng, thay vì âm thầm sai. Đã cập nhật `docs/ai/AI_PRODUCTION_OPERATIONS.md`
   phần model; các tài liệu spec/plan lịch sử (`docs/superpowers/specs/…`,
   `AI_RAG_RESEARCH_PROTOCOL.md`...) và script thực nghiệm
   (`run_pipeline_profile_eval.py`'s `DEEPSEEK_MODEL` constant) **không đổi** —
   đó là bản ghi lịch sử/biến thực nghiệm cố định, không phải cấu hình runtime.
   Test suite (396 test, giảm 1 do bỏ `test_load_config_enables_exact_luna_429_fallback`
   — test này kiểm tra đúng cặp DEFAULT_LLM_MODEL/DEFAULT_RATE_LIMIT_FALLBACK_MODEL
   là "hợp lệ", premise này không còn đúng sau khi 2 hằng số này trùng giá trị)
   pass toàn bộ sau khi đổi.

Chưa quyết định (đã có dữ liệu thăm dò ở §7 nhưng nhiễu bởi đổi model, cần đo lại
bằng DeepSeek thật trước khi chốt):

- Có nên đổi `AI_PIPELINE_PROFILE` mặc định sang `planner_state_v3` hay không.
  §7 (chạy bằng GPT-5.6 Luna) cho thấy `planner_state_v3` thắng cả
  `strict_semantic_success` lẫn `context_accuracy`, nhưng p95 latency 47,5s và
  việc đổi model đồng thời với đổi code khiến kết quả này chưa đủ tin cậy để
  quyết định — cần chạy lại nguyên bản `run_pipeline_profile_eval.py` bằng
  DeepSeek thật.
- Ngưỡng `AMBIGUITY_CONFIDENCE_THRESHOLD` (0.35) có cần điều chỉnh sau khi tăng
  tần suất gọi LLM-assist hay không — cần đo latency/cost thật.

## 9. Giới hạn

- Baseline test suite **trước khi sửa** không đo được bằng công cụ (`python -m
  unittest`) vì máy không có Python cài sẵn tại thời điểm bắt đầu — Python 3.12 +
  virtualenv được cài mới trong quá trình này. Con số so sánh ở §6 dùng báo cáo
  trước đó (`docs/ai/AI_SYSTEM_IMPLEMENTATION_SUMMARY.md`) làm tham chiếu, không
  phải một lần chạy `unittest` thật trước/sau trên cùng máy.
- §7 (so sánh 3 profile) chạy bằng model thay thế (`cx/gpt-5.6-luna-review`) vì
  route DeepSeek (`oc/deepseek-v4-flash-free`) trong tài khoản 9router test trả
  lỗi `400 Upstream request failed` khi gửi kèm `response_format:json_object` —
  đã xác nhận đây là vấn đề riêng của tài khoản/route test, không phải production
  (production dùng key và 9router instance khác trên VPS). Số liệu §7 vì vậy
  **không so sánh trực tiếp về giá trị tuyệt đối** được với
  `ai/evaluation/approved/pipeline_selection.json` gốc (đo bằng DeepSeek) — chỉ
  thứ hạng/so sánh tương đối giữa 3 profile trong cùng lần chạy này có giá trị
  tham khảo.
- Compliance thật của model với hướng dẫn "claims[].text bám evidence" (§4.3)
  chưa được đo bằng LLM thật trong báo cáo này — cần bổ sung vào lần chạy
  `run_golden_llm_eval.py`/`run_dual_llm_eval.py` tiếp theo.
