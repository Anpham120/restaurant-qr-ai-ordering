# Kết quả của những phép đo KHÔNG tính lại được trong notebook

Notebook tính lại được gần hết số của nó ngay trong ô mã: nạp thực đơn, chấm tập trả lời, dựng chỉ
mục, so ba bộ truy hồi. Hai phép đo thì không:

| Tệp | Cần gì | Vì sao notebook không tính lại được |
|---|---|---|
| `golden_e2e.json` | backend + Postgres + dịch vụ AI đang chạy | notebook chạy trên host, không có stack |
| `llm_rag_loai_c.json` | `LLM_API_KEY` thật | mỗi lần chạy tốn tiền và vài phút |

## Vì sao thư mục này tồn tại

Trước khi có nó, hai con số trên bị **viết tay** vào notebook. Và đúng những chỗ viết tay là chỗ đã
trôi — notebook từng in:

| Notebook in | Thực tế lúc phát hiện |
|---|---|
| `tất định 122/122` | tập đã lên 140 ca |
| `kho 84 tài liệu / 303 đoạn` | 108 tài liệu / 449 đoạn |
| `embedding Hit@5 0,921` | số của kho cũ 303 đoạn; kho mới là 0,674 |

Ba con số, cả ba từng đúng, cả ba sai đi lặng lẽ. Quy tắc số 3 của chính notebook viết: *"Không viết
số vào tài liệu — số phải tính được, nếu không nó sẽ trôi."*

Cách sửa không phải "nhớ cập nhật" — đó là cách đã thất bại ba lần. Bộ chạy **ghi** ra đây, notebook
**đọc** từ đây, và `results.doc()` **báo lỗi to** khi thiếu tệp thay vì in số cũ.

## Mỗi tệp mang cả ĐIỀU KIỆN của lần chạy

`84/103` không so được với `67/103` nếu không biết lần nào bật đường sinh, lần nào dùng bộ truy hồi
nào, và mỗi lần chạy mã của ngày nào. Nên `dieu_kien` là tham số **bắt buộc** của `results.ghi()`,
và với golden nó chứa nguyên phản hồi `/ready` của dịch vụ đang được đo.

## Sinh lại

```bash
# 1. Dựng stack. `--build` là bắt buộc khi mã AI đã đổi: `docker compose cp` KHÔNG nạp lại
#    uvicorn đang chạy, và `up -d` sau đó xóa luôn tệp đã cp vào.
docker compose -f deploy/docker-compose.yml up -d --build
python ai/evaluation/wait_for_stack.py

# 2. Một mã QR cho bước thêm vào giỏ thật (dùng lại được qua nhiều lần chạy)
export GOLDEN_QR_TOKEN=$(docker compose -f deploy/docker-compose.yml exec -T postgres \
  psql -U restaurant_user -d restaurant_qr -t -A \
  -c "select qr_token from restaurant_tables order by table_code limit 1;")

# 3. golden qua HTTP thật -> results/golden_e2e.json
python ai/evaluation/run_golden_e2e.py

# 4. LLM+RAG loại C -> results/llm_rag_loai_c.json
python ai/evaluation/run_llm_rag_eval.py
```

Cả hai bộ chạy **chỉ ghi khi chạy đầy đủ**: `--chi` (golden) và `--gioi-han` (LLM+RAG) không ghi.
Một lần chạy 6 lượt ghi đè kết quả 103 lượt sẽ làm notebook in `6/6 = 100%` — đúng số, sai điều đang
được nói.

## Tệp ở đây CÓ vào git

Chúng là bằng chứng của phép đo. CI không dựng nổi stack có `LLM_API_KEY` thật để sinh lại chúng,
nên nếu không commit thì notebook không có số nào để đọc.
