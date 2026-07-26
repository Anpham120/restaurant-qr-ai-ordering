# VPS staging — AI và chat thật

Runbook deploy staging qua `.github/workflows/deploy-staging.yml`. Kiến trúc
production không được chọn thủ công: workflow phải chạy thí nghiệm ba profile,
tạo `ai/evaluation/results/pipeline_selection.json`, rồi bind
`AI_PIPELINE_PROFILE` vào winner.

## Điều kiện trước khi deploy

### 1. DeepSeek qua 9router

`ai-service` dùng `network_mode: host`. `LLM_BASE_URL` phải trỏ tới 9router trên
cùng VPS (mặc định `http://127.0.0.1:20128/v1`).

- GitHub secret: `NINE_ROUTER_API_KEY`.
- Model cố định cho thí nghiệm và runtime:
  `oc/deepseek-v4-flash-free`.
- Không cấu hình GPT fallback.

### 2. GitHub Environment `staging`

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

## Quy trình deploy

1. Push `develop` hoặc chạy **Actions → Deploy Staging**.
2. CI chạy unit/integration/notebook/golden gates.
3. Job deploy chạy `run_pipeline_profile_eval.py` trên đúng commit:
   `llm_first_v1`, `evidence_first_v2`, `planner_state_v3`.
4. `verify_pipeline_selection.py` kiểm tra model, commit, dataset hash và safety
   hard gate; không có winner thì dừng.
5. `deploy-vps.sh` truyền winner thành `AI_PIPELINE_PROFILE`.
6. `health-check.sh` xác minh readiness và ba câu semantic smoke.

Artifact được upload với tên chứa commit SHA và được đóng gói cùng release.

## Semantic smoke bắt buộc

Health check gửi menu thật trong `backend/data/menu-dataset.json` và kiểm tra:

1. “Nhà hàng mình có những món phở gì nhỉ?”
2. “Gợi ý cho mình món phở tại nhà hàng đi”
3. “Mình có món nhậu không?”

Mỗi response phải:

- ghi đúng `pipeline_profile` và model `oc/deepseek-v4-flash-free`;
- không trả fallback “Mình chưa đủ bằng chứng…”;
- có `resolved_menu_item_ids` và `evidence`;
- không có claim chưa verify;
- có `verifier_result != failed`.

Nếu bất kỳ điều kiện nào sai, deployment thất bại. Production workflow sẽ
dispatch rollback theo cơ chế hiện có.

## Kiểm tra multi-turn qua UI staging

- “Gợi ý hai món phở” → “Món thứ hai giá bao nhiêu?”
- “Loại món vừa gợi ý” → món đó không được gợi ý lại.
- “Gợi ý cho 2 người” → “Đổi thành 4 người”.
- “Tôi dị ứng đậu phộng” → đổi chủ đề → gợi ý món; dị ứng vẫn phải được duy trì.
- Mở phiên bàn khác và xác minh state không rò rỉ.

Đối chiếu log nội bộ: `pipeline_profile`, model, route,
`resolved_menu_item_ids`, `verifier_result`.

## Rollback

Production tự dispatch `.github/workflows/rollback.yml` khi deploy hoặc smoke
thất bại. Staging có thể chạy workflow rollback hoặc
`deploy/scripts/rollback-vps.sh`.
