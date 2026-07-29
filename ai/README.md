# Trợ lý AI tư vấn đặt món — dựng lại từ đầu

Thư mục này vừa được xóa trắng. Bản cũ (250 tệp, ~116.500 dòng) vẫn còn nguyên trong
git history và đang chạy trên production ở nhánh `main`; nhánh này dựng lại từ số
không để mỗi cơ chế đều được hiểu trước khi được viết.

## Vì sao dựng lại

Bản cũ hoạt động được nhưng không còn giải thích được. Đo trên tập 338 câu hỏi:

| Quan sát | Số liệu |
|---|---|
| Đường xử lý tất định chồng lên nhau | 8 đường, 2 trong số đó bị một cờ legacy tắt mà vẫn hoạt động tốt |
| Câu trả lời do mã tất định sinh ra | 33% — phần còn lại phụ thuộc mô hình sinh |
| Một lớp lỗi lặp lại | 7 lần: rút dấu tiếng Việt làm hai từ khác nghĩa trùng nhau |
| Thước đo chất lượng | sai 3 lần trước khi hệ thống sai |

Bài học lớn nhất: **thước đo cũng là một phương pháp và cũng phải chứng minh được
mình đúng.** Bản dựng lại vì thế bắt đầu từ dữ liệu và thước đo, không từ mô hình.

## Nguyên tắc cho bản dựng lại

1. **Không thêm cơ chế nào chưa đo được.** Mỗi bước phải kèm cách kiểm chứng và một
   con số trước/sau.
2. **Ít cơ chế, mỗi cơ chế một việc.** Bản cũ có 8 đường tất định che nhau; nếu hai
   cơ chế cùng trả lời một loại câu hỏi thì một trong hai là dư.
3. **Rút dấu để khớp cách khách gõ, không để quyết định nội dung.** Đây là gốc của
   7 lỗi trong bản cũ (`cua`/`của`, `chay`/`chạy`, `trứng`/`Trung`, `bơ`/`bò`,
   `mực`/`mức`, `lạc`/`lắc`, `trà`/`tráng`).
4. **Nguồn có thẩm quyền phải rõ ràng.** Thực đơn trực tiếp là sự thật về món; kho
   tri thức là sự thật về chính sách. Không trộn hai loại.
5. **Việc gì tra được thì không đoán.** Món nào có dị nguyên là tra bảng, không phải
   suy luận.

## Lộ trình — mỗi bước có kiểm chứng riêng

Thứ tự này là thứ tự phụ thuộc, không phải thứ tự ưu tiên. Bước 0 và 1 đã xong.

| # | Bước | Câu hỏi cần trả lời trước khi viết mã | Kiểm chứng |
|---|---|---|---|
| 0 | ✅ [Phát biểu bài toán](docs/00-problem-statement.md) | Khách hỏi những gì? Cái gì AI được phép trả lời? | 3 loại câu hỏi, phạm vi hai chiều, 3 điều tuyệt đối không làm |
| 1 | ✅ [Từ điển dữ liệu](docs/01-data-dictionary.md) | Trường nào là sự thật, trường nào là nhãn người gán? Thiếu nhãn nghĩa là gì? | 80 nhãn → khóa có không gian tên; 7 lỗ nhãn dị nguyên đã bổ sung; 7 test canh trôi dữ liệu, đã chứng minh bắt được lỗi thật |
| 2 | Tập đánh giá | Câu hỏi thật của khách trông thế nào? Thế nào là trả lời đúng? | Mỗi ca có tiêu chí đúng/sai rõ ràng, chia dev/test theo tầng để dev dự báo được test |
| 3 | Thước đo | Làm sao biết câu trả lời tốt? | Thước đo tự có test hai chiều: bắt được lỗi thật, không bịa lỗi |
| 4 | Trả lời không cần AI | Bao nhiêu câu chỉ cần tra thực đơn? | Số nền: tỷ lệ trả lời được mà chưa dùng mô hình nào |
| 5 | Truy hồi tri thức | Câu chính sách lấy dữ liệu ở đâu? | So sánh phương pháp truy hồi trên tập ở bước 2 |
| 6 | Mô hình sinh | Còn lại câu nào cần mô hình? Prompt nào? | Đo trước/sau bằng thước đo bước 3 |
| 7 | Chốt an toàn | Điều gì tuyệt đối không được sai? | Kiểm chứng fail-closed cho dị ứng và trẻ em |

## Vẫn còn ngoài thư mục này

- `backend/data/menu-dataset.json` — danh mục 91 món, **nguồn AI dùng**. Bước 1 đã đọc
  lại từ đầu và phát hiện: khách **không** thấy tệp này. `/api/menu` đọc cơ sở dữ liệu,
  chỉ có 1,7 nhãn/món so với 15 ở đây. Hai nguồn lệch nhau, chưa hợp nhất — xem
  `docs/01-data-dictionary.md` mục 1.
- `backend/data/menu-tags.json` — từ điển 80 nhãn (khóa, nhãn Việt, nhãn Anh, tên cũ),
  sinh bởi `scripts/build_tag_dictionary.py`. Nguồn sự thật duy nhất, dùng chung với hai
  bảng nhãn ở frontend.
- Backend .NET gọi 6 endpoint (`/v1/chat`, `/v1/chat/stream`, `/ready`, `/health`,
  `/v1/rag/search`, `/v1/cache/invalidate`). Hợp đồng này sẽ được thiết kế lại và
  backend sửa theo, nên trong lúc dựng lại thì luồng chat trên nhánh này chưa chạy.
