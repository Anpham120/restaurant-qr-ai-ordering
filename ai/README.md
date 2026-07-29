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

Thứ tự này là thứ tự phụ thuộc, không phải thứ tự ưu tiên. Bước 0–4 đã xong.

| # | Bước | Câu hỏi cần trả lời trước khi viết mã | Kiểm chứng |
|---|---|---|---|
| 0 | ✅ [Phát biểu bài toán](docs/00-problem-statement.md) | Khách hỏi những gì? Cái gì AI được phép trả lời? | 3 loại câu hỏi, phạm vi hai chiều, 3 điều tuyệt đối không làm |
| 1 | ✅ [Từ điển dữ liệu](docs/01-data-dictionary.md) | Trường nào là sự thật, trường nào là nhãn người gán? Thiếu nhãn nghĩa là gì? | 84 nhãn → khóa có không gian tên; hợp nhất hai nguồn thực đơn (91/91 → 0/91 món lệch); 7 lỗ nhãn dị nguyên đã bổ sung; 8 test canh trôi dữ liệu, đã chứng minh bắt được lỗi thật |
| 2 | ✅ [Tập đánh giá](docs/02-evaluation-set.md) | Thế nào là trả lời đúng? | 80 ca / 27 họ; khóa đáp án là truy vấn trên thực đơn nên tự kiểm được; chia 3 nhóm (chốt 14 / phát triển 39 / niêm phong 27), tất định; bộ kiểm bắt 9/9 loại ca viết sai |
| 3 | ✅ [Thước đo](docs/03-answer-metric.md) | Làm sao biết câu trả lời tốt? | 35 test hai chiều; tự đọc tên món và giá ra khỏi câu trả lời nên hệ thống không khai gian được; bộ dò lỗ tìm 24 lỗ và bịt hết, sàn còn 12/80 |
| 4 | ✅ [Trả lời không cần mô hình](docs/04-answers-without-a-model.md) | Bao nhiêu câu chỉ cần tra thực đơn? | **23/27 (85,2%)** trên tập niêm phong lần mở đầu — con số held-out thật; sau khi sửa 3 lỗi nó chỉ ra thì 80/80 nhưng không còn là held-out. 9 cơ chế, cả 9 đều có ca chứng minh giá trị, 5 ngăn lỗi an toàn |
| 5 | Truy hồi tri thức | Câu chính sách lấy dữ liệu ở đâu? | So sánh phương pháp truy hồi trên tập ở bước 2 |
| 6 | Mô hình sinh | Còn lại câu nào cần mô hình? Prompt nào? | Đo trước/sau bằng thước đo bước 3 |
| 7 | Chốt an toàn | Điều gì tuyệt đối không được sai? | Kiểm chứng fail-closed cho dị ứng và trẻ em |

## Vẫn còn ngoài thư mục này

- `backend/data/menu-dataset.json` — danh mục 91 món, nguồn AI dùng. Bước 1 phát hiện
  khách **không** thấy tệp này: `/api/menu` đọc cơ sở dữ liệu, và cơ sở dữ liệu chỉ có
  1,7 nhãn/món so với 15 ở đây. **Đã hợp nhất** — hai nguồn nay mang đúng cùng bộ nhãn,
  có test canh. Xem `docs/01-data-dictionary.md` mục 1.
- `backend/data/menu-tags.json` — từ điển 84 nhãn / 16 nhóm (khóa, nhãn Việt, nhãn Anh,
  tên cũ), sinh bởi `scripts/build_tag_dictionary.py`. Nguồn sự thật duy nhất, dùng chung
  giữa AI, cơ sở dữ liệu và hai bảng nhãn ở frontend.
- Backend .NET gọi 6 endpoint (`/v1/chat`, `/v1/chat/stream`, `/ready`, `/health`,
  `/v1/rag/search`, `/v1/cache/invalidate`). Hợp đồng này sẽ được thiết kế lại và
  backend sửa theo, nên trong lúc dựng lại thì luồng chat trên nhánh này chưa chạy.
- `backend/tests/.../AiContractBoundaryTests.cs` — `ai/contracts/ai-chat-v1.schema.json`
  đã bị xóa cùng bản cũ, nên phép kiểm hình dạng hợp đồng nay **có điều kiện**: nó tự bật
  lại ngay khi tệp schema mới xuất hiện. Khi thiết kế lại hợp đồng, nhớ đối chiếu danh
  sách trường mà test đó đòi với hợp đồng mới — đừng để nó kiểm một hình dạng đã lạc hậu.
