# Vận hành lớp AI — triển khai, cấu hình, và runbook

> **Nguồn sự thật cho cách XÂY lớp AI** là `ai/docs/00`→`07` và
> [BAO_CAO_DO_AN_HOC_MAY_KPDL.md](BAO_CAO_DO_AN_HOC_MAY_KPDL.md). Tệp này chỉ nói việc **vận hành**.
>
> **Bản này viết lại toàn bộ ngày 2026-08-08.** Bản trước mô tả một hệ thống không còn tồn tại: nó
> nêu `evaluation/approved/pipeline_selection.json`, `evaluation/results/dev_retrieval_summary.v3.json`,
> `ai/scripts/build_index.py`, `ai/app/config.py` — **không đường dẫn nào trong số đó có thật**. Nó
> cũng ghi `hybrid_e5_small` Hit@5 99,09% là kết quả hiện hành, trong khi hybrid đã bị loại sau ba
> phép đo độc lập và `e5-small` đã bị thay.
>
> Một tài liệu vận hành sai không im lặng — nó **được tin**. Đó là lý do bản này chỉ ghi điều kiểm
> lại được bằng cách mở đúng tệp nêu kèm.

---

## 1. Hình dạng triển khai

`deploy/docker-compose.yml` dựng bốn dịch vụ, cộng một `migrate` chạy một lần:

| dịch vụ | vai trò |
|---|---|
| `postgres` | dữ liệu đơn, giỏ, và bộ nhớ chat theo phiên bàn |
| `api` | backend .NET — **chủ sở hữu giỏ hàng và đơn** |
| `ai-service` | FastAPI, Python — chỉ trả lời và **gợi ý** |
| `frontend` | giao diện khách quét QR |

`ai-service` và `api` dùng `network_mode: host`.

**Ranh giới quyền, và đây là điều quan trọng nhất của cả trang này:** AI **không có quyền ghi**. Nó
không chạm cơ sở dữ liệu, không đặt món, không sửa giỏ. Nó trả về **thẻ gợi ý** với
`requires_customer_confirmation` luôn `true` — không nhánh nào đặt `false`. Nếu lớp AI hỏng hoàn
toàn, luồng đặt món vẫn chạy.

### Sáu cổng vào

`GET /health` · `GET /ready` · `POST /v1/chat` · `POST /v1/chat/stream` ·
`POST /v1/cache/invalidate` · `POST /v1/model-check`

`/ready` báo **bộ truy hồi đang dùng** (`embedding` hay đã lùi về `bm25`), số đoạn đã nạp, và số
vector lấy từ đệm. Trường đó tồn tại vì hệ thống từng âm thầm lùi về BM25 mà không ai biết.

---

## 2. Cấu hình

Xem `ai/.env.example` — nó chỉ liệt kê **biến mà mã thật sự đọc**.

| biến | bắt buộc | ghi chú |
|---|---|---|
| `AI_INTERNAL_TOKEN` | **có** | backend gửi kèm mọi lượt; thiếu → 401 |
| `AI_EMBEDDING_CACHE` | nên có | không có mặc định trong mã, có chủ ý |
| `LLM_BASE_URL` · `LLM_API_KEY` · `LLM_MODEL` | không | thiếu thì dịch vụ **vẫn chạy** bằng đường tất định |
| `AI_ENABLE_GENERATION` | không | mặc định tắt |

**`AI_EMBEDDING_CACHE` không có giá trị mặc định là quyết định, không phải thiếu sót.** Mã tự đoán
một đường dẫn thì lúc chạy đọc chỗ khác, và hậu quả là **im lặng mã hóa lại toàn kho mỗi lần khởi
động** — 492 giây với `bge-m3`. Ảnh Docker tự đặt biến này và chạy `python -m rag.precompute` lúc
build.

Khóa của bộ đệm chứa **tên mô hình**, nên đổi mô hình làm đệm cũ tự bị từ chối thay vì bị dùng nhầm.

---

## 3. Con số cần biết trước khi triển khai

Đo thật, không ước:

| | giá trị |
|---|---:|
| mô hình nhúng | `BAAI/bge-m3`, 1024 chiều |
| trọng số | 2.271 MB |
| RAM khi chạy | **1.234 MB** (`mem_limit: 3g`) |
| nạp mô hình | **20,6 s** |
| mã hóa lần đầu | 4,8 s |
| độ trễ mỗi truy vấn | **271,7 ms** — chỉ với câu tri thức |
| mã hóa lại toàn kho | 492 s — **lúc build**, không lúc khởi động |

**`start_period` của healthcheck là 90s, không phải 20s.** Nạp mô hình 20,6 s cộng mã hóa lần đầu
4,8 s là ~25,4 s; với 20s cũ, lần thăm dò đầu rơi đúng lúc mô hình còn đang nạp và
`depends_on: service_healthy` giữ dịch vụ phụ thuộc chờ thêm một chu kỳ 30 giây. Không hỏng hẳn,
nhưng chậm mà không có lý do nhìn thấy được.

Độ trễ 271,7 ms chỉ rơi vào **câu tri thức** — câu chọn món đi nhánh lọc nhãn và không chạm truy hồi.

---

## 4. Giới hạn phía backend

| | |
|---|---|
| 10 tin nhắn / phút / phiên chat | `ChatRateLimiter.PerMinuteLimit` |
| 100 tin nhắn / vòng đời phiên | `ChatRateLimiter.PerSessionLimit` |
| tối đa 2000 ký tự mỗi tin | `ChatEndpoints.cs` |

Bộ nhớ chat bị **xóa** khi đóng phiên bàn, khi phiên hết hạn, và khi thanh toán —
`IChatStore.DeleteSessionsByTableSession`.

---

## 5. Sửa kho tri thức xong thì chạy gì

```bash
python ai/scripts/build_knowledge.py          # sinh lại phần `derived` từ thực đơn
python ai/scripts/build_knowledge.py --check  # cổng CI: phải khớp, và mọi số tiền phải truy được
```

Cổng `--check` kiểm ba bất biến: tài liệu `derived` khớp kết quả sinh lại, mọi tài liệu khai
`audience: guest`, và **mọi số tiền trong kho truy được về `menu-dataset.json`**. Bất biến thứ ba
đóng một hố thật: 36 tài liệu `written` là văn xuôi viết tay có số tiền của thực đơn, và chúng
**trôi im lặng** khi thực đơn đổi giá.

Đổi kho xong phải **dựng lại ảnh** để tính lại đệm vector, hoặc chạy `POST /v1/cache/invalidate`.

---

## 6. Cổng phải xanh trước khi phát hành

```bash
python -m unittest discover -s ai/app -p "test_*.py"
python -m unittest discover -s ai/evaluation -p "test_*.py"
python ai/evaluation/run_baseline.py --all        # ca trả lời
python ai/evaluation/run_session_eval.py          # bộ nhớ phiên — CÓ chốt an toàn
python ai/evaluation/run_golden_e2e.py            # qua stack thật, cần GOLDEN_QR_TOKEN
python ai/evaluation/run_khai_di_ung.py           # nhận diện khai dị ứng
```

Và các cổng `--check` của tệp sinh: `build_tag_dictionary` · `build_knowledge` ·
`build_session_scripts` · `build_chunk_selection_cases` · `build_retrieval_cases` ·
`build_ca_phu_kho` · `build_bao_cao_do_an` · `build_teaching_notebook` · `build_docs_index` ·
`build_api_inventory` · `build_system_facts`.

**Chốt an toàn:** một lượt mời món gây dị ứng là **chặn phát hành**, không phải trừ điểm.

---

## 7. Giới hạn đã biết — nói ra thay vì giấu

| | |
|---|---|
| **Nhận diện khai dị ứng 75,00%** | đo trên tập niêm phong 20 câu; 5 cách nói vẫn bỏ sót |
| **Không còn tập held-out** | mọi tập niêm phong đã mở; số liệu là số trên tập đã nhìn thấy |
| **Không có log khách thật** | mọi bộ đánh giá do nhóm viết |
| Nhãn dị nguyên phủ 44/91 món | nên câu trả lời **luôn** kèm lời mời hỏi nhân viên |

Ba dòng đầu là giới hạn **phương pháp**, không sửa được bằng mã. Dòng cuối là giới hạn **dữ liệu**,
và hệ thống đã xử lý bằng cách không bao giờ khẳng định một món an toàn.
