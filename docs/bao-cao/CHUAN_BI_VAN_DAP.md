# CHUẨN BỊ VẤN ĐÁP — CMC RESTAURANT

Tài liệu này hỗ trợ nhóm chuẩn bị cho phần vấn đáp 20% của học phần INFO2005. Nội dung trả lời phải
dựa trên mã nguồn và đóng góp thật của từng thành viên; không học thuộc nguyên văn. Mỗi câu nên
được trả lời trong 60–90 giây theo cấu trúc:

1. **Kết luận:** nhóm đã chọn hoặc đã làm gì.
2. **Căn cứ:** yêu cầu, số đo, issue, PR, kiểm thử hoặc release nào chứng minh.
3. **Giới hạn:** quyết định đó chưa giải quyết được điều gì.

## 1. Câu hỏi chung theo CLO

### CLO1 — Kỹ nghệ phần mềm hiện đại, Agile và DevOps

#### 1. Vì sao đây là một sản phẩm phần mềm thay vì một bài tập CRUD?

Hệ thống không chỉ lưu thực đơn và đơn hàng mà phải duy trì cùng một trạng thái phiên bàn giữa
khách, bếp và quầy. Các thao tác như tạo đơn, chuyển trạng thái và tất toán có bất biến nghiệp vụ,
phân quyền và hậu quả không thể xử lý chỉ bằng giao diện CRUD. Tuy nhiên, không nên trả lời rằng đề
tài “không phải CRUD” như một khẩu hiệu; cần nêu cụ thể máy trạng thái, transaction, SignalR và
kiểm thử liên quan.

**Minh chứng:** §2.3.3–2.3.4; `OrderLifecycleTests.cs`; `TableInvoiceTests.cs`.

#### 2. Một thay đổi đi từ yêu cầu tới production như thế nào?

Nhu cầu được ghi thành issue có nhãn, người phụ trách và milestone; thành viên phát triển trên
nhánh riêng, mở pull request, chạy năm nhóm kiểm tra CI, sau đó hợp nhất vào `develop`. Nhánh
`develop` triển khai staging; thay đổi được promote sang `main` để triển khai production. Health
check thất bại có thể kích hoạt rollback.

**Minh chứng:** §3.1; `.github/workflows/ci.yml`, `deploy-staging.yml`,
`promote-production.yml`, `rollback.yml`.

#### 3. 872 commit và 377 PR có tự chứng minh quy trình tốt không?

Không. Các con số chỉ cho thấy mức hoạt động. Chất lượng quy trình phải được đánh giá thêm qua sự
phân bố commit theo thời gian, liên kết issue, nội dung PR, kết quả CI, release và review. Dự án còn
thiếu human peer review chính thức, nên không được dùng số PR để khẳng định mọi thay đổi đã được
thành viên khác xem xét.

#### 4. Vì sao branch ruleset bật muộn vẫn được đưa vào báo cáo?

Vì đó là trạng thái thực của dự án. Trước khi bật ruleset, CI được tuân thủ theo quy ước nhóm nhưng
chưa được GitHub cưỡng chế. Ruleset chỉ bảo đảm các thay đổi sau thời điểm kích hoạt. Nêu rõ mốc
thời gian giúp tránh diễn giải quá mức bằng chứng.

### CLO2 — Phân tích nhu cầu và phạm vi sản phẩm

#### 5. Hãy phát biểu Product Vision trong một câu.

CMC Restaurant là hệ thống web dành cho nhà hàng ăn tại chỗ quy mô vừa, hỗ trợ khách gọi món bằng
QR và giúp khách, bếp, quầy duy trì trạng thái dùng chung của một phiên phục vụ; sản phẩm tập trung
vào dùng bữa tại bàn, không giải quyết giao hàng.

#### 6. Persona dựa trên bằng chứng nào?

Nhóm quan sát hai nhà hàng quy mô vừa tại Hà Nội trong bốn buổi trưa và trao đổi không cấu trúc với
nhân viên phục vụ, nhân viên quầy. Persona khách và bếp được suy luận một phần vì nhóm chưa phỏng
vấn trực tiếp hai vai trò này. Do đó persona là giả thuyết làm việc có cơ sở quan sát, không phải
kết luận nghiên cứu người dùng.

#### 7. Vì sao loại giao hàng và mang về khỏi MVP?

Vì product vision tập trung vào trạng thái của một phiên dùng bữa tại bàn. Giao hàng tạo thêm địa
chỉ, vận chuyển và vòng đời giao nhận nhưng không giúp kiểm chứng bài toán phiên bàn. Nhóm đã loại
chúng bằng migration thay vì chỉ ghi “ngoài phạm vi”.

**Minh chứng:** `RemoveDeliveryAndBindTableSession`; PB-09; §1.3.

#### 8. Quan hệ giữa persona, user story, FR/NFR và kiểm thử là gì?

Persona cung cấp mục tiêu và ràng buộc; scenario mô tả tình huống; user story biến nhu cầu thành
giá trị cần cung cấp; acceptance criteria xác định điều kiện đạt; FR/NFR đặc tả hành vi và chất
lượng; ma trận truy vết nối chúng tới kiểm thử. Ví dụ, dị ứng của persona Minh dẫn tới US-03,
NFR-01 và bộ đánh giá fail-closed.

### CLO3 — Kiến trúc sản phẩm

#### 9. Vì sao chọn modular monolith thay vì microservices?

Đơn hàng, phiên bàn, hóa đơn và thanh toán chia sẻ transaction và thay đổi cùng nhịp trong một nhóm
nhỏ. Tách chúng sớm làm tăng giao tiếp mạng, distributed transaction, quan sát và triển khai mà
chưa có yêu cầu phát hành độc lập. Modular monolith giữ transaction cục bộ nhưng vẫn chia module.
Dịch vụ AI được tách vì dùng Python, thư viện và vòng đời tài nguyên khác backend .NET.

#### 10. Vì sao dùng REST kết hợp SignalR?

REST phù hợp với thao tác tài nguyên có hợp đồng rõ như tạo đơn, lấy thực đơn và thanh toán.
SignalR được dùng cho trạng thái cần đẩy từ bếp tới khách và quầy. Không dùng SignalR cho toàn bộ
API vì phần lớn thao tác vẫn là request–response; không dùng polling cho realtime vì tạo độ trễ và
yêu cầu lặp không cần thiết.

#### 11. Bất biến quan trọng nào được đặt ở cơ sở dữ liệu?

Một bàn chỉ có một phiên đang mở được bảo vệ bằng unique index có điều kiện; mã đơn dùng sequence;
concurrency dùng `xmin`; tạo lượt đơn và xóa giỏ nằm trong cùng transaction. Các ràng buộc này nằm
ở cơ sở dữ liệu vì nhiều request hoặc instance backend có thể vượt qua một kiểm tra `if` ở ứng
dụng.

#### 12. Triển khai VPS chứng minh điều gì và không chứng minh điều gì?

Nó chứng minh các thành phần có thể tích hợp và chạy ngoài máy phát triển với HTTPS và PostgreSQL.
Nó không chứng minh hệ thống chịu tải tốt, dễ dùng, giảm thời gian chờ hoặc phù hợp vận hành thương
mại vì chưa có kiểm thử tải và thử nghiệm dài hạn tại nhà hàng.

### CLO4 — Bảo mật, tin cậy, kiểm thử và quản lý mã

#### 13. Làm sao hạn chế AI gợi ý sai về dị nguyên?

Mô hình ngôn ngữ chỉ hiểu câu hỏi và diễn đạt. Việc chọn món được mã tất định lọc theo nhãn; thiếu
nhãn thì loại món. Câu sinh ra được kiểm tra lại tên món và giá; không hợp lệ thì chuyển sang khuôn
mẫu. AI không có quyền ghi giỏ hoặc tạo đơn. Kết luận đúng phải là “không ghi nhận lỗi trên tập ca
đã công bố, trong phạm vi dữ liệu nhãn hiện có”, không phải “AI an toàn tuyệt đối”.

#### 14. 118 frontend, 84 backend và 386 AI test chứng minh điều gì?

Chúng chứng minh các hành vi được mã hóa trong các test hiện có đạt tại môi trường đo. Chúng không
chứng minh toàn bộ mã đã được kiểm thử vì chưa có báo cáo coverage thống nhất; cũng không chứng
minh khả năng chịu tải, a11y hoặc chất lượng cảm nhận của người dùng.

#### 15. Golden E2E tìm ra lỗi gì mà test thành phần bỏ sót?

Dịch vụ AI phát SSE thiếu dòng `event:`; backend dùng giả định khác nên bỏ qua stream và trả câu dự
phòng. Test riêng của từng dịch vụ vẫn đạt vì mỗi bên mô phỏng hợp đồng theo giả định của mình.
Golden E2E dựng stack thật nên phát hiện lỗi tại ranh giới tích hợp.

#### 16. Code review đã tạo ra thay đổi nào?

CodeQL phát hiện lộ thông tin qua exception. Nhóm thay nội dung trả cho client bằng loại lỗi và mã
tham chiếu tám ký tự, giữ chi tiết trong log và bổ sung kiểm thử hồi quy. Cần nói rõ đây là review
tự động; lịch sử chưa ghi nhận peer review chính thức của thành viên khác.

**Minh chứng:** PR #256, PR #377; `test_service.py`.

### CLO5 — Làm việc nhóm, MVP và sử dụng AI có trách nhiệm

#### 17. Nhóm sử dụng tác tử AI như thế nào?

AI được dùng để đề xuất mã, test, kiến trúc và phân tích. Nhóm không chấp nhận đầu ra chỉ vì chạy
được; mỗi đề xuất được đối chiếu bằng test, số đo hoặc review. Ví dụ AI đề xuất hybrid retrieval,
nhưng phép đo cho thấy embedding đơn tốt hơn nên nhóm bác bỏ đề xuất và thay ADR.

#### 18. Làm sao kiểm chứng đóng góp cá nhân?

Đối chiếu issue được giao, PR do thành viên tạo, commit không phải merge commit và hiện vật cụ thể.
Không sử dụng tổng số commit duy nhất để kết luận đóng góp vì kích thước và giá trị commit khác
nhau.

#### 19. Quyết định nào của nhóm thay đổi sau khi có số đo?

Hai ví dụ: hybrid retrieval bị thay bằng embedding sau khi đo; chọn món bằng RAG bị thay bằng lọc
nhãn tất định vì RAG chỉ đúng 1–2/8 trong khi lọc nhãn đạt 8/8 trên tập ca tương ứng. Đây là bằng
chứng nhóm tự quyết sau kiểm chứng, không phụ thuộc đề xuất ban đầu của AI.

#### 20. Nếu có thêm hai tuần, việc nào cần làm trước?

Ưu tiên hoàn tất và xác nhận nhãn dị nguyên, tạo tập đánh giá mới chưa từng mở, bổ sung human peer
review và kiểm thử tải. Đây là các khoảng trống ảnh hưởng trực tiếp tới độ tin cậy của kết luận,
quan trọng hơn việc bổ sung chức năng mới.

## 2. Câu hỏi theo thành viên

### Phạm Duy An — Kiến trúc, AI/RAG, DevOps

- Vì sao chỉ tách dịch vụ AI nhưng giữ nghiệp vụ trong modular monolith?
- Phép đo nào khiến nhóm bỏ hybrid retrieval và bỏ RAG cho bước chọn món?
- Cổng kiểm tra cấu hình trước và sau deploy dùng chung nguồn kỳ vọng như thế nào?
- Vì sao tập niêm phong hiện tại chỉ còn giá trị hồi quy?

### Bùi Đào Đức Anh — Xác thực, phiên bàn, thanh toán

- JWT, vai trò và capability token giải quyết ba vấn đề khác nhau như thế nào?
- Vì sao biết `sessionId` không đồng nghĩa có quyền thao tác phiên?
- Luồng COD và VietQR khác nhau ở đâu; vì sao VietQR vẫn cần quầy xác nhận?
- Làm sao bảo đảm tất toán không đóng sai hoặc đóng lặp phiên bàn?

### Nguyễn Quang Hiếu — Cơ sở dữ liệu, đơn hàng, thời gian thực

- Vì sao một bàn chỉ có một phiên mở phải được bảo vệ ở cơ sở dữ liệu?
- Transaction tạo lượt đơn và xóa giỏ ngăn trạng thái dở dang nào?
- SignalR truyền sự kiện gì và hệ thống xử lý thế nào khi client kết nối lại?
- PostgreSQL sequence và `xmin` được dùng để xử lý loại cạnh tranh nào?

### Đỗ Tuấn Anh — Giao diện khách hàng

- Khi quét lại QR, frontend xác định màn hình tiếp tục bằng những trạng thái nào?
- Vì sao giỏ được lưu phía máy chủ thay vì `localStorage`?
- Giao diện thể hiện giới hạn của gợi ý AI và quyền quyết định của khách như thế nào?
- Luồng khách phản ứng ra sao khi SignalR mất kết nối hoặc thanh toán thay đổi trạng thái?

### Lê Anh — Giao diện vận hành

- Bảng bếp ưu tiên thông tin nào để giảm thao tác trong giờ cao điểm?
- Trạng thái món và trạng thái đơn khác nhau như thế nào trên giao diện bếp?
- Cơ chế phân vai admin, quầy và bếp được kiểm tra ở frontend và backend ra sao?
- Làm sao trạng thái “hết món” ở bếp ảnh hưởng tới thực đơn khách?

## 3. Sáu phát biểu không được nói quá

| Không nên nói | Cách nói có căn cứ |
|---|---|
| “AI bảo đảm an toàn dị ứng 100%.” | “Không ghi nhận lỗi trên tập ca đã công bố, trong phạm vi 44/91 món có nhãn hiện tại; chưa đủ để kết luận an toàn y tế.” |
| “Tập niêm phong chứng minh khả năng khái quát.” | “Tập đã được mở hai lần nên hiện chỉ dùng cho hồi quy; cần một tập mới chưa từng mở.” |
| “377 PR đều được code review.” | “377 PR đều đi qua quy trình PR; review được ghi nhận là review tự động, chưa có human peer review chính thức.” |
| “Đã chạy production nên sản phẩm hiệu quả.” | “Triển khai chứng minh khả năng tích hợp kỹ thuật; hiệu quả vận hành chưa được đo tại nhà hàng.” |
| “Có hơn 700 test nên coverage cao.” | “Các test hiện có đạt; dự án chưa thu thập coverage thống nhất.” |
| “Mô hình AI chọn món.” | “Mã tất định chọn món theo nhãn; mô hình hỗ trợ hiểu yêu cầu và diễn đạt.” |

## 4. Checklist trước buổi bảo vệ

- Mỗi thành viên mở được issue, PR và tệp mã chính do mình phụ trách.
- Mỗi thành viên demo được ít nhất một luồng và giải thích một trường hợp lỗi.
- Nhóm thống nhất các số liệu chốt: 46 issue, 872 commit, 377 PR, ba release và kết quả kiểm thử.
- Không dùng con số tổng nếu không giải thích được phương pháp đếm.
- Có sẵn phương án demo dự phòng khi dịch vụ AI hoặc mạng ngoài gặp lỗi.
- Thực hiện ít nhất một human peer review thật trên thay đổi còn mở và cập nhật báo cáo nếu hoàn tất.
