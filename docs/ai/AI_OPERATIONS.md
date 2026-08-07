# Vận hành AI — production, staging, và runbook

> **Một tài liệu cho toàn bộ việc vận hành lớp AI.** Gộp từ ba tệp cũ
> (`AI_PRODUCTION_OPERATIONS`, `AI_STAGING_READINESS`, `VPS_STAGING_AI_RUNBOOK`)
> vì chúng cùng trả lời một câu hỏi — *"đưa lớp AI lên máy thật thế nào và canh nó ra sao"* —
> nhưng nằm ba chỗ nên mỗi lần đổi quy trình phải nhớ sửa ba nơi, và thực tế là chỉ sửa một.
>
> Nguồn sự thật cho **cách xây** lớp AI vẫn là `ai/docs/00`→`07`. Tệp này chỉ nói việc **vận hành**.


---

## Vận hành production

*(gộp từ `docs/ai/AI_PRODUCTION_OPERATIONS.md`)*

### Feature flag

- `CHAT_AI_PROVIDER=python-rag` (required on .NET backend)
- `AI_PIPELINE=v2` documents the LLM-first path (prompt lives only in Python)
- Python AI service LLM via **9router** (OpenAI-compatible):
  - `LLM_PROVIDER=9router`
  - `LLM_BASE_URL=http://localhost:20128/v1` (or deployed gateway URL)
  - `LLM_API_KEY=<9router gateway key>`
  - `LLM_MODEL=cx/gpt-5.6-luna-review` (production default; see
    `ai/app/config.py:DEFAULT_LLM_MODEL`)
  - Alternate quality gate: `LLM_MODEL=cx/gpt-5.5`
  - DeepSeek (`oc/deepseek-v4-flash-free`) is no longer the default — dropped
    after the 9router route serving it rejected `response_format:json_object`,
    which every real chat request requires. Historical research artifacts
    (`ai/evaluation/approved/pipeline_selection.json`) still reference it as the
    model tested at that time.
- `LLM_TIMEOUT_SECONDS=12` (Python-to-9router) and `BACKEND_AI_TIMEOUT_SECONDS=12` (.NET-to-Python)
- `AI_MAX_RETRY=0`–`1`

### Hard gates before canary

| Gate | Threshold |
|------|-----------|
| Menu ID validity | 100% |
| Unavailable suggestions | 0 |
| Duplicate auto-recommendations | 0 |
| Session history restore | 100% |
| Schema-valid responses | ≥ 99.5% |
| Fast-path catalog p95 | ≤ 100 ms |
| LLM TTFT p50 | ≤ 1.5 s |

### Rollout

1. Staging deploy with migration `AddsAiSessionLedgerAndServerCart`
2. Shadow evaluate Python responses offline for ≥ 1 week
3. Canary 10% tables via feature flag
4. Full production; keep rollback to previous image

### Rate limits

- 10 messages / minute / chat session
- 100 messages / chat session lifetime
- Max message length 2000 chars

### Observability

Log (no raw PII / message body):
- stage latency (retrieval, LLM, validate)
- validator rejection reason
- duplicate-blocked count
- fallback reason
- approximate token usage if provided by the LLM gateway

### Knowledge ownership

Restaurant manager owns KB domains with `expires_at`. Re-run `ai/scripts/build_index.py` after KB edits. Reject deploy if validation errors present.

---

## Chuẩn bị lên staging/production

*(gộp từ `docs/ai/AI_STAGING_READINESS.md`)*

Last updated: 2026-07-27.

**Current release status: NOT READY.** Historical `composite_pass` artifacts are
retained for provenance only; they do not satisfy the current evidence-first
release contract.

The release architecture is now selected by
`evaluation/results/pipeline_selection.json`, generated from a controlled
single-model comparison of all three pipeline profiles under the runtime's
primary model (`cx/gpt-5.6-luna-review`; DeepSeek was dropped after its
9router route rejected `response_format:json_object` — see
`docs/ai/AI_DECISION_HISTORY.md`). `planner_state_v3` may
remain in the codebase for research, but it cannot be enabled unless it is the
artifact winner. A missing winner, profile drift, commit drift, or failed
post-deploy semantic smoke blocks/rolls back the release.

### Pre-canary gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Critical hallucination = 0 on frozen release set | **CHƯA ĐO** | Frozen test chỉ được mở sau config lock |
| Retrieval Hit@5 ≥ 95% | **PASS — 109/110 (99,09%)** | `dev_retrieval_summary.v3.json`, `hybrid_e5_small`, dev |
| Retrieval nDCG@5 ≥ 0,75 | **PASS — 0,8332** | Cùng artifact; 7-method screening. Dense E5 = 0,8401 nhưng chênh với Hybrid E5 chưa có ý nghĩa thống kê |
| Hybrid E5 p95 retrieval | **PASS CỤC BỘ — 29,34 ms** | `dev_hybrid_e5_release_candidate.v1.json`, 110 case × 7 lần đo/query; staging load test vẫn chưa chạy |
| Current paired GPT-5.5/DeepSeek run | **PASS PROTOCOL, CHƯA PASS QUALITY RELEASE** | `dual_model/20260723-9router-paired-18-final/comparison.json`: 11/11 exact input hashes khớp, cùng retriever/no fallback; availability 11/11 mỗi model; quality GPT 2/11, DeepSeek 3/11 |
| Human overall ≥ 95%, safety = 100% | **CHƯA ĐO** | Auto-score không thay human review; cần 50–100 câu, ít nhất 20% chấm đôi |
| Context retention ≥ 98% | **PASS OFFLINE — 1200/1200** | `session_e2e_eval.json`; deterministic templated regression, không phải bằng chứng free-form LLM |

#### Historical LLM baseline — không dùng làm release headline

- `golden_llm_eval_cx_gpt55_v3_full_v3b.json` và
  `golden_llm_eval_deepseek_v4_full.json` là artifact trước truth-reset.
- Có thể trích dẫn chúng như baseline lịch sử nếu nêu rõ availability,
  faithfulness/adequacy và giới hạn metric; không dùng `composite_pass=100%` để
  kết luận hệ thống hiện tại không bịa.

### Staging load test

**Requires staging env** — not run locally.

| Target | Threshold | Next steps |
| --- | --- | --- |
| p95 retrieval | ≤ 150 ms after warm-up | Deploy AI service to staging; replay the locked retrieval cases after warm-up |
| p95 E2E | ≤ 6 s with 9router GPT-5.6 Luna | Load-test `/chat` with `LLM_MODEL=cx/gpt-5.6-luna-review`; **sau `AI_LLM_FIRST=true` p95 E2E có thể cao hơn** (mọi lượt gợi ý gọi LLM); report TTFT separately from end-to-end p50/p95 |
| Fast-path catalog p95 | ≤ 100 ms | Chỉ áp dụng khi `AI_LLM_FIRST=false`; replay catalog/tag/category queries from golden dev subset |

### Rollout

**Requires staging env** — do not fake results.

1. Deploy staging with 9router env (`LLM_PROVIDER=9router`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL=cx/gpt-5.6-luna-review`, **`AI_LLM_FIRST=true`**)
2. Shadow evaluate ≥ 1 week (log queries, compare shadow vs production responses)
3. Canary 10% tables
4. Full rollout with rollback image pinned

### Research artifacts

| Artifact | Status |
| --- | --- |
| Retrieval ablation | `py -m evaluation.run_retrieval_ablation` → `retrieval_ablation_summary.json` |
| Dev retrieval comparison | `evaluation/results/dev_retrieval_summary.v3.json` (7 phương pháp; latency screening-only 1 lần/query; `hybrid_e5_small`: Hit@5 109/110 = 99,09%; nDCG@5 0,8332) |
| Hybrid E5 release-candidate latency | `evaluation/results/dev_hybrid_e5_release_candidate.v1.json` (7 lần/query; p95 29,34 ms) |
| Workspace audit | `py scripts/audit_ai_workspace.py` — stale_present=0 |

See also [`VPS_STAGING_AI_RUNBOOK.md`](AI_OPERATIONS.md).

---

## Runbook VPS staging

*(gộp từ `docs/ai/VPS_STAGING_AI_RUNBOOK.md`)*

Runbook deploy staging qua `.github/workflows/deploy-staging.yml`. Kiến trúc
production không được chọn thủ công: workflow phải chạy thí nghiệm ba profile,
tạo `ai/evaluation/results/pipeline_selection.json`, rồi bind
`AI_PIPELINE_PROFILE` vào winner.

### Điều kiện trước khi deploy

#### 1. GPT-5.6 Luna qua 9router

`ai-service` dùng `network_mode: host`. `LLM_BASE_URL` phải trỏ tới 9router trên
cùng VPS (mặc định `http://127.0.0.1:20128/v1`).

- GitHub secret: `NINE_ROUTER_API_KEY`.
- Model cố định cho thí nghiệm và runtime:
  `cx/gpt-5.6-luna-review`.
- Không cấu hình fallback (single-model; DeepSeek đã bị bỏ vì route của nó
  trong 9router từ chối `response_format:json_object` — xem
  `docs/ai/AI_DECISION_HISTORY.md`).

#### 2. GitHub Environment `staging`

| Biến | Nguồn |
| --- | --- |
| `STAGING_HOST`, `STAGING_SSH_USER`, `STAGING_SSH_KEY` | Secrets |
| `JWT_SIGNING_KEY`, `AI_INTERNAL_TOKEN`, `STAGING_POSTGRES_PASSWORD` | Secrets |
| `NINE_ROUTER_API_KEY` | Secret |
| `NINE_ROUTER_BASE_URL` | Variable, tùy chọn |
| `AI_PIPELINE_PROFILE` | Variable, tùy chọn nhưng nếu đặt phải trùng winner |
| VietQR `PAYMENTS__VIETQR__*` | Secrets |

Nếu `AI_PIPELINE_PROFILE` đã cấu hình nhưng khác winner, workflow dừng trước
deploy. Nếu không cấu hình, workflow lấy winner từ artifact và export vào môi
trường deploy.

### Quy trình deploy

1. Push `develop` hoặc chạy **Actions → Deploy Staging**.
2. CI chạy unit/integration/notebook/golden gates.
3. Job deploy chạy `run_pipeline_profile_eval.py` trên đúng commit:
   `llm_first_v1`, `evidence_first_v2`, `planner_state_v3`.
4. `verify_pipeline_selection.py` kiểm tra model, commit, dataset hash và safety
   hard gate; không có winner thì dừng.
5. `deploy-vps.sh` truyền winner thành `AI_PIPELINE_PROFILE`.
6. `health-check.sh` xác minh readiness và ba câu semantic smoke.

Artifact được upload với tên chứa commit SHA và được đóng gói cùng release.

### Semantic smoke bắt buộc

Health check gửi menu thật trong `backend/data/menu-dataset.json` và kiểm tra:

1. “Nhà hàng mình có những món phở gì nhỉ?”
2. “Gợi ý cho mình món phở tại nhà hàng đi”
3. “Mình có món nhậu không?”

Mỗi response phải:

- ghi đúng `pipeline_profile` và model `cx/gpt-5.6-luna-review`;
- không trả fallback “Mình chưa đủ bằng chứng…”;
- có `resolved_menu_item_ids` và `evidence`;
- không có claim chưa verify;
- có `verifier_result != failed`.

Nếu bất kỳ điều kiện nào sai, deployment thất bại. Production workflow sẽ
dispatch rollback theo cơ chế hiện có.

### Kiểm tra multi-turn qua UI staging

- “Gợi ý hai món phở” → “Món thứ hai giá bao nhiêu?”
- “Loại món vừa gợi ý” → món đó không được gợi ý lại.
- “Gợi ý cho 2 người” → “Đổi thành 4 người”.
- “Tôi dị ứng đậu phộng” → đổi chủ đề → gợi ý món; dị ứng vẫn phải được duy trì.
- Mở phiên bàn khác và xác minh state không rò rỉ.

Đối chiếu log nội bộ: `pipeline_profile`, model, route,
`resolved_menu_item_ids`, `verifier_result`.

### Rollback

Production tự dispatch `.github/workflows/rollback.yml` khi deploy hoặc smoke
thất bại. Staging có thể chạy workflow rollback hoặc
`deploy/scripts/rollback-vps.sh`.
