# HỎI ĐÁP KỸ THUẬT — CMC RESTAURANT

Bộ câu hỏi về **tính năng, công nghệ và cách hoạt động**. Không có câu hỏi về
quy trình làm việc hay số liệu commit — phần đó ở
[CHUAN_BI_VAN_DAP.md](CHUAN_BI_VAN_DAP.md).

Mỗi câu trả lời 2–5 dòng, số liệu trước, giải thích sau. Dòng **Chốt** là câu
duy nhất cần nói nếu thầy chỉ muốn nghe kết luận.

---

## A. Tính năng hoạt động ra sao

#### A1. Quét mã QR thì chuyện gì xảy ra?

Mã QR chứa `tableCode` và một `qrToken` cố định của bàn. Backend nhận `POST /api/tables/scan`,
kiểm bàn hợp lệ, rồi **mở phiên mới hoặc trả về phiên đang mở** của bàn đó, kèm một
**capability token cấp riêng cho lần quét này**.

**Chốt:** mã trong QR không phải thứ cấp quyền — nó chỉ để đổi lấy capability token.

#### A2. Bốn người cùng bàn cùng quét thì thành bốn phiên à?

Không, cả bốn vào **chung một phiên**. Ràng buộc nằm ở tầng cơ sở dữ liệu bằng
**unique index có điều kiện** trên `(RestaurantTableId)` khi `Status = Open`, không phải
bằng câu `if` ở tầng ứng dụng.

Migration: `EnforceSingleActiveTableSession`.

#### A3. Quét lại thì hệ thống biết đưa khách về đâu bằng cách nào?

Suy ra **sáu trạng thái tiếp tục** từ danh sách đơn và trạng thái hóa đơn:

| Trạng thái | Nghĩa | Vào màn hình nào |
|---|---|---|
| `New` | Chưa có gì trong giỏ, chưa đơn nào hiệu lực | Thực đơn |
| `CartPending` | Giỏ có món, chưa gửi bếp | Giỏ hàng |
| `OrderInProgress` | Có đơn ở `Draft`…`Ready` | Trang theo dõi đơn |
| `ReadyForPayment` | Mọi món đã phục vụ | Trang đơn, mở hóa đơn |
| `PaymentPending` | Đã yêu cầu thanh toán | Trang đơn, mở hóa đơn |
| `Paid` | Quầy đã xác nhận thu | Trang đơn, mở hóa đơn |

Hàm `deriveSessionHubState`, có test canh ở cả backend và frontend.

#### A4. Giỏ hàng lưu ở đâu?

**Phía máy chủ**, bảng `TableSessionCartItem` gắn với phiên bàn — không nằm trong `localStorage`.
Nên đóng tab hay đổi sang điện thoại khác vẫn còn giỏ.

#### A5. Gửi món lên bếp diễn ra thế nào?

`POST /api/orders` tạo lượt đơn mới **và** xóa giỏ dùng chung trong **cùng một transaction**.
Không có khoảnh khắc nào đơn đã lưu mà giỏ vẫn còn, hoặc ngược lại.

#### A6. Một đơn đi qua những trạng thái nào?

`Draft → Placed → Confirmed → Preparing → Ready → Served → Completed`, cộng nhánh `Cancelled`.
Mỗi lần đổi ghi một dòng vào `OrderStatusHistory` kèm `FromStatus`, `ToStatus`, `ChangedByRole`.

Ngoài ra **từng món** có trạng thái riêng: `Pending → Preparing → Ready → Served → Cancelled`,
nên bếp đánh dấu xong từng món chứ không phải cả đơn.

#### A7. Bếp và khách thấy cùng một trạng thái bằng cách nào?

SignalR. Bếp thao tác → backend ghi → hub đẩy sự kiện tới **cả** bảng bếp và màn hình khách.

Bảy sự kiện hệ thống phát:

```
order.created          order.statusChanged      order.itemStatusChanged
cart.updated           payment.requested        assistance.requested
menu.availabilityChanged
```

**Chốt:** hai bên không phải hai bản sao cần khớp nhau — chúng là **cùng một bản ghi**
hiển thị theo hai vai trò.

#### A8. Bếp bật "hết món" thì khách đang xem thực đơn có biết không?

Có, ngay lập tức. `MenuEndpoints` đổi `IsAvailable` rồi phát `menu.availabilityChanged`
kèm `menu_item_id`. Khách đang mở thực đơn nhận sự kiện và cập nhật, không phải tải lại trang.

#### A9. Khách bấm "Gọi nhân viên" thì đi đâu?

`POST /api/chat/sessions/{id}/assistance` → phát sự kiện `assistance.requested` tới màn hình
quầy và nhân viên. Trên màn quầy có mục **"Khách cần hỗ trợ"** hiển thị các yêu cầu gần đây.

#### A10. Một phiên nhiều lượt gọi thì hóa đơn tính sao?

`TableSession` quan hệ **1 → nhiều** với `Order` nhưng **1 → 1** với `TableInvoice`.
Hóa đơn cộng toàn bộ lượt gọi thành `SubtotalAmount`, trừ `DiscountAmount`, ra tổng.

**Chốt:** khuyến mãi và tích điểm áp **một lần lúc tất toán** trên hóa đơn phiên, không áp theo từng lượt.

#### A11. Khuyến mãi hoạt động ra sao?

`PromotionCalculator.TryApplyAsync` nhận mã và `subtotalAmount`, tra bảng `Promotion`, rồi
**kiểm hiệu lực theo thời gian và theo giá trị đơn tối thiểu** trước khi tính giảm giá.
Mã sai hoặc hết hạn ném `PromotionInvalidException` với mã lỗi rõ ràng như `PROMOTION_NOT_FOUND`.

#### A12. Thanh toán có mấy phương thức, khác nhau ở đâu?

`Unselected`, `COD`, `VietQR`. Trạng thái thanh toán có tám mức:
`NotRequested → Unpaid → Pending → Paid → Confirmed`, cộng `Failed`, `Cancelled`, `Refunded`.

VietQR hiện **chỉ sinh mã**, quầy đối chiếu rồi bấm xác nhận thủ công. Mọi giao dịch ghi vào
`PaymentTransaction` kèm `Provider`, `ProviderTransactionId` và `IdempotencyKey`.

#### A13. Ca quầy hoạt động thế nào?

Mở ca khai báo `OpeningCashBalance`. Trong ca, mọi giao dịch ghi vào `CounterShiftTransaction`.
Đóng ca khai báo `ActualCashTotal` và ghi chú, hệ thống **đối soát tiền mặt thực tế với tiền
hệ thống ghi nhận**.

#### A14. Trợ lý AI xử lý một câu hỏi theo trình tự nào?

```
[HIỂU]  mô hình đọc tiếng Việt → ràng buộc dạng nhãn JSON
[CHỌN]  mã tất định lọc thực đơn theo nhãn   ← mô hình không chạm vào
[VIẾT]  mô hình diễn đạt trên tập món đã chốt
[CHẶN]  câu nhắc món/giá ngoài tập → lùi về khuôn mẫu
```

#### A15. "Fail-closed" nghĩa là gì ở đây?

Món **thiếu** nhãn dị nguyên thì bị **loại** khỏi gợi ý, không phải được giữ.
Khi dữ liệu không đủ, hệ thống thu hẹp và cảnh báo chứ không đoán.

#### A16. Hàng rào chặn hoạt động ra sao?

Sau khi mô hình viết câu, hệ thống kiểm **mọi tên món và số tiền** trong câu phải có thật
trong tập đã chốt ở bước CHỌN. Không có thì chặn, lùi về khuôn mẫu tất định.

Đo: 8/8 câu bị chặn đúng lý do. Trên 76 câu sinh — 68 dùng được, 8 chuyển khuôn mẫu,
**không ca nào bị giảm điểm**.

#### A17. Ràng buộc dị ứng có giữ qua nhiều lượt hội thoại không?

Có. Lưu ở `ChatSession.ConstraintsJson` và `RollingSummary`. Khách nói dị ứng ở lượt 1,
đến lượt 4 hỏi "còn món nào rẻ hơn" thì ràng buộc vẫn còn.

#### A18. Dịch vụ AI hỏng thì khách thấy gì?

Trả **HTTP 200 kèm câu chuyển nhân viên**, không phải màn hình lỗi. Chi tiết lỗi vào log
kèm mã tham chiếu 8 ký tự. Có kiểm thử **tiêm lỗi** đi đúng đường xử lý đó.

Ngân sách timeout phân tầng: AI **30 s** < backend **50 s**, để lỗi không dồn ngược lên khách.

#### A19. Kho tri thức của AI lấy từ đâu?

108 tài liệu / 449 đoạn, chia hai loại:

| Loại | Số | Nguồn |
|---|---|---|
| `derived` | 49 | Sinh từ `menu-dataset.json` — không thể lệch |
| `written` + `policy` | 36 + 24 | Người viết: chính sách, gợi ý kết hợp món |

`build_knowledge.py --check` chạy trong CI: thực đơn đổi mà tài liệu `derived` không đổi theo thì CI đỏ.

#### A20. Truy hồi dùng cơ chế gì?

Embedding `e5_small`, vector **tính sẵn lúc build** nên khởi động nhanh.
Không dùng vector database — với 449 đoạn thì một mảng trong bộ nhớ là đủ.

#### A21. Dữ liệu dị nguyên nằm ở đâu?

Bảng `MenuItemKnowledge`, các trường `Allergens`, `Ingredients`, `SpiceLevel`, `DietaryTags`,
quan hệ 1–1 với `MenuItem`. Đây là bảng mà mã tất định đọc ở bước CHỌN.

#### A22. Phân quyền hoạt động thế nào?

JWT + `RequireAuthorization` theo vai trò ở backend. Bốn vai trò: `Admin`, `CounterStaff`,
`Kitchen`, `Staff`. Vai trò trong frontend **chỉ phục vụ UX**.

Mật khẩu băm **PBKDF2-HMAC-SHA256 có salt**; khóa tài khoản sau nhiều lần đăng nhập sai.

#### A23. Capability token khác JWT ở chỗ nào?

JWT dành cho **nhân viên đã đăng nhập**, mang vai trò. Capability token dành cho **khách
không đăng nhập**, chỉ cho phép thao tác trong đúng một phiên bàn, cấp mới mỗi lần quét.

**Chốt:** `sessionId` chỉ là mã định danh, biết nó không đồng nghĩa với có quyền vào phiên.

#### A24. Chống hai người sửa cùng một đơn bằng gì?

Optimistic concurrency qua cột hệ thống `xmin` của PostgreSQL. Xung đột trả lỗi `CONFLICT_STALE`.

#### A25. Chống gửi trùng đơn khi mạng chập chờn?

`IdempotencyKey` trên `Order` và `PaymentTransaction`. Gửi lại cùng khóa thì không tạo bản ghi mới.

#### A26. Mã đơn có trùng không khi chạy nhiều máy chủ?

Không. Mã sinh bằng **PostgreSQL sequence**, không sinh phía ứng dụng.
Migration `AddXminAndOrderCodeSequence`.

#### A27. Sinh mã QR cho bàn thế nào?

Màn quản trị có tab **QR & link**: mỗi bàn một mã và một liên kết đặt món dạng
`order.cmcrestaurant.app/table/T01?qr=<token>`, tải về được để in.

#### A28. Pipeline CI/CD chạy ra sao?

```
PR → ci.yml (5 job song song) + security.yml
   → merge develop → deploy-staging + cổng verify_deploy_config
   → promote-production (develop→main) → deploy-production + health-check.sh
   → smoke hỏng → rollback.yml tự kích hoạt
```

Năm job: `frontend-build`, `backend-test`, `ai-data-and-eval`, `golden-e2e`, `docker-compose-config`.

#### A29. "Cổng kiểm tra hai đầu" là gì?

Hai script hỏi hai câu khác nhau, **lấy kỳ vọng từ cùng một hàm**:

- `verify_deploy_config.py` chạy trong CI: *"cấu hình sắp deploy có khớp bằng chứng đã đo không?"*
- `health-check.sh` chạy trên VPS: *"dịch vụ đang chạy có đúng cấu hình ấy không?"*

#### A30. Golden E2E kiểm cái gì?

Dựng **toàn bộ stack thật** — PostgreSQL, backend .NET, dịch vụ AI — rồi chạy chuỗi
quét QR → phiên bàn → phiên chat → câu trả lời → thẻ giỏ → giỏ hàng.

Kết quả: **103/103 lượt trên 29 hội thoại**, ở cả hai chế độ có và không có đường sinh.

---

## B. Tại sao dùng cái này mà không dùng cái kia

#### B1. Monolith thay vì microservices?

Đơn hàng, thanh toán và phiên bàn **luôn đổi cùng nhau** và cần nhất quán ngay.
Tách ra phải dựng saga để mô phỏng lại thứ một transaction vốn cho sẵn.

Ba bất biến của hệ thống — một bàn một phiên mở, mã đơn không trùng, `xmin` chống ghi đè —
đều cần **một cơ sở dữ liệu duy nhất** mới cưỡng chế được.

**Chốt:** nhưng đây là *modular* monolith, ranh giới module theo miền đã sẵn để cắt sau.

#### B2. Thế vì sao AI lại được tách ra?

| | Backend | Dịch vụ AI |
|---|---|---|
| Ngôn ngữ | C# | Python |
| Ảnh Docker | ~200 MB | **2,74 GB** |
| Nhịp đổi | Theo tính năng nhà hàng | Theo phép đo chất lượng |
| Scale khi | Nhiều bàn gọi món | Nhiều câu hỏi cùng lúc |

Gộp chung thì mỗi lần sửa một endpoint thực đơn phải build lại cả tầng embedding.

**Chốt:** tiêu chí tách dịch vụ là **khác biệt vòng đời**, không phải sự gọn gàng của sơ đồ.

#### B3. REST thay vì GraphQL?

Cái nhóm thiếu là **hợp đồng ổn định cho 5 người làm song song trên 3 tầng**, không phải
sự linh hoạt truy vấn. Thêm một tầng schema linh hoạt lúc đó làm vấn đề tệ hơn.

#### B4. PostgreSQL thay vì MySQL hay MongoDB?

Ba bất biến cần đúng ba tính năng: **unique index có điều kiện**, **sequence**, và **cột `xmin`**.
MySQL không đủ cả ba. MongoDB sai bản chất — dữ liệu quan hệ chặt và cần ACID.

#### B5. SignalR thay vì WebSocket thuần hay polling?

Polling không đủ cho bảng bếp. SignalR hơn WebSocket thuần ở chỗ **tự lùi về long-polling**
khi WebSocket bị chặn — có ích khi wifi nhà hàng đi qua proxy.

#### B6. Năm app riêng thay vì một SPA?

Khách tại bàn dùng **mạng 4G**. Không có lý do bắt họ tải cả bundle quản trị.
Mã dùng chung chia sẻ qua `packages/`.

#### B7. Embedding thay vì BM25 hay hybrid?

**Đo, không đoán.** ADR trước đó của nhóm đã chốt "hybrid thắng", rồi phép đo lật lại:

| Tập | BM25 | **Embedding** | Hybrid |
|---|---|---|---|
| Phát triển — 124 ca / 9 họ | 0,803 | **0,921** | 0,908 |
| Phân vùng 2 — 44 ca / 4 họ | 0,750 | 0,864 | 0,886 |

Hybrid thua ở tập phát triển mà tốn thêm một tầng xếp hạng → bỏ.

#### B8. RAG thay vì fine-tune?

| | Fine-tune | RAG + lọc nhãn |
|---|---|---|
| Thực đơn đổi giá | Train lại | Có hiệu lực ngay |
| Chứng minh không bịa giá | Rất khó | Hàng rào chặn, đo được |
| Truy vết câu trả lời | Không | Về một dòng dữ liệu |

**Chốt:** thực đơn và giá nhà hàng đổi thường xuyên — đó là yếu tố quyết định.

#### B9. Vì sao mã tất định chọn món chứ không để mô hình chọn?

Nếu mô hình chọn, **không có cách nào chứng minh** nó luôn loại món có tôm cho khách dị ứng tôm —
thử bao nhiêu câu cũng không đủ. Khi chọn là phép lọc trên bảng nhãn, câu hỏi thành
*"bảng nhãn có đúng không"* — tra được, kiểm được, có test canh.

Đo: lọc nhãn **8/8**, RAG chọn **1–2/8**.

#### B10. Docker Compose thay vì Kubernetes?

Một nhà hàng, một VPS. K8s là độ phức tạp không đổi lấy được gì, và đủ đơn giản để cả năm
thành viên hiểu toàn bộ đường đi từ mã nguồn tới máy chủ.

#### B11. Vì sao không blue-green hay canary?

Một VPS, một nhà hàng, vài giây gián đoạn khi khởi động lại là chấp nhận được.

#### B12. Vì sao ghim bản CPU-only của thư viện embedding?

Cài mặc định thì pip kéo về bản CUDA → ảnh **9,29 GB** trong khi VPS không có GPU.
Ghim CPU-only → **2,74 GB**. Cộng tính sẵn vector: khởi động **97,3 s → 19,0 s**.

#### B13. Vì sao không dùng vector database?

449 đoạn tri thức. Một mảng trong bộ nhớ là đủ — thêm một hệ thống nữa để vận hành mà không đổi lấy gì.

#### B14. Vì sao EF Core chứ không viết SQL tay?

Cần **migration có phiên bản** để lược đồ tiến hóa kiểm chứng được — 22 migration hiện tại
là dấu vết của quá trình đó. EF Core cũng ánh xạ sẵn cột `xmin` của PostgreSQL làm
concurrency token.

---

## C. Vì sao lại xây dựng như vậy

#### C1. Vì sao chọn QR làm điểm vào?

Khách dùng ngay trình duyệt, không cài ứng dụng, và QR **mang theo định danh bàn** từ điểm vào.

**Chốt:** giá trị kỹ thuật không nằm ở việc quét mã, mà ở phần xử lý **sau** lần quét —
xác thực bàn, mở hoặc tiếp tục phiên, giữ trạng thái qua nhiều lượt.

#### C2. Vì sao cần AI, bộ lọc thường không đủ à?

Thực đơn là dữ liệu có cấu trúc nhưng **câu hỏi của khách thì không**.
*"Hai người dưới 300 nghìn nên chọn gì"* — phải suy ra tổng ngân sách, số người, và đó là
yêu cầu gợi ý chứ không phải lọc.

Bỏ mô hình thì khách phải tự dịch nhu cầu thành checkbox — mất lý do có trợ lý.

#### C3. Nhưng LLM chỉ phục vụ mã tất định thôi à?

Không. Mô hình gánh **hai đầu** của cuộc hội thoại: hiểu đầu vào và diễn đạt đầu ra.
Chia theo **chi phí của sai lầm** — việc nào sai mà khách tự phát hiện được thì giao mô hình;
việc nào sai mà khách không phát hiện được thì giao mã.

Nói thẳng: có đo, **23/27 câu (85,2 %)** trả lời được chỉ bằng tra thực đơn. Mô hình đóng góp
ở phần đuôi và ở chất lượng diễn đạt. Chính vì tỷ lệ đó mà đường tất định được giữ làm
**đường lùi thật** khi gateway hỏng.

#### C4. Vì sao trạng thái phiên bàn được suy ra chứ không lưu?

Vì bản đầu lưu sẵn và bị lệch: một luồng cập nhật quên ghi vào cột trạng thái.
Tính lại chậm hơn chút nhưng **không thể lệch khỏi dữ liệu thật**.

#### C5. Vì sao ba bất biến đặt ở cơ sở dữ liệu chứ không ở ứng dụng?

Vì tầng ứng dụng có lỗi. Đặt ở cơ sở dữ liệu thì chúng **vẫn đúng ngay cả khi có lỗi lập trình
ở tầng trên**.

#### C6. Vì sao golden E2E ra đời?

Vì một lỗi thật: dịch vụ AI phát SSE **thiếu dòng `event:`**, backend bỏ qua stream và trả câu
dự phòng — trong khi **test riêng của cả hai dịch vụ đều xanh**, vì mỗi bên dùng một giả định
khung dữ liệu khác nhau.

**Chốt:** đó là loại lỗi không tầng kiểm thử thành phần nào bắt được.

#### C7. Vì sao phải kiểm chính bộ thước đo?

Phần AI không so được đầu ra với một giá trị cố định, nó cần hàm chấm điểm — mà hàm chấm điểm
cũng là mã, và mã thì có lỗi. Bộ dò `probe_metric_holes.py` đưa câu trả lời **cố ý vô nghĩa**
vào thước đo và đòi thước đo cho trượt: tìm ra **24 trường hợp chấp nhận sai**, đã khắc phục cả 24.

#### C8. Vì sao cổng deploy phải có hai đầu?

Vì cấu hình chết. Biến `RAG_RETRIEVAL_METHOD=hybrid` tồn tại lâu trong cấu hình trong khi bộ
truy hồi thật chạy là `embedding`. **Không mô-đun nào đọc nó** nên nó không gây lỗi — nhưng ai
đọc cấu hình cũng tin nó.

**Chốt:** cấu hình chết nguy hiểm hơn thiếu tài liệu, vì thiếu tài liệu khiến người ta đi hỏi,
còn cấu hình chết khiến người ta tin chắc một điều sai.

#### C9. Vì sao AI không được ghi vào giỏ hàng?

Dịch vụ AI **cố ý không trả về** `accepted_menu_item_ids` / `added_to_cart_menu_item_ids`.
Khách bấm thêm món là một lời gọi API riêng tới backend.

Cho mô hình tự thêm món thì tiết kiệm cho khách một cú chạm, nhưng mọi sai sót của mô hình
trở thành **món ăn có thật trên bàn**.

#### C10. Vì sao tài liệu tri thức phải sinh lại được?

Vì một tài liệu viết tay ghi *"hơn 90 món"* trong khi thực đơn có **đúng 91 món**.
Văn xuôi kể lại dữ liệu thì luôn trôi khỏi dữ liệu.

**Chốt:** lời giải không phải siết kỷ luật cập nhật, mà là **đổi loại hiện vật** — sinh từ
dữ liệu, có `--check` trong CI.

#### C11. Vì sao ruleset không chừa ngoại lệ cho quản trị viên?

Vì một cổng chặn có ngoại lệ cho người quyền cao nhất thì **đúng vào lúc nguy hiểm nhất** —
lúc gấp, lúc muộn, lúc "chỉ sửa một dòng" — nó sẽ không chặn.

#### C12. Vì sao migration bị loại khỏi auto-merge?

Migration **không hoàn tác được bằng một lần revert**. PR thường sai thì lùi lại là xong;
migration đã chạy trên production đã kịp đổi dữ liệu thật, và `Down()` hầu như không khôi phục
được thứ đã bị xóa.

**Chốt:** mức độ tự động hóa nên **tỉ lệ nghịch với chi phí của sai lầm**.

#### C13. Vì sao mỗi món có trạng thái riêng, không chỉ trạng thái đơn?

Vì bếp làm xong từng món chứ không xong cả đơn một lúc. Khách nhìn thấy món nào đã sẵn sàng,
và nhân viên biết mang món nào ra trước.

---

## D. Giới hạn kỹ thuật — nên thuộc

#### D1. Nhóm có dám nói hệ thống an toàn cho người dị ứng không?

**Không.** Con số "không ghi nhận lỗi trên 140 ca" có nghĩa chính xác là:
*không ghi nhận lỗi trên tập ca đã công bố, với bảng nhãn hiện tại*.

Ba lý do chưa kết luận được: nhãn mới phủ **44/91 món**, bảng nhãn **chưa được bếp xác nhận**,
và một tập ca hữu hạn không chứng minh được tính chất phổ quát.

#### D2. Tập niêm phong của nhóm có còn giá trị không?

Nó **đã bị mở hai lần** — 30/07 trên kho 303 đoạn và 31/07 trên kho 425 đoạn, ghi trong
`retrieval_split.json` trường `sealed_opened`.

Kể từ lần mở thứ nhất nó **không còn là held-out**. Số đo sau đó chỉ có giá trị **hồi quy**.
Nhóm giữ số liệu nhưng ghi rõ giới hạn thay vì bỏ đi.

#### D3. Thực đơn 91 món là thật hay dữ liệu mẫu?

**Dữ liệu mẫu.** Cấu trúc cố ý đều — 13 danh mục × đúng 7 món — trong khi thực đơn thật không
bao giờ đều như vậy. Kết quả đo trên thực đơn cân đối có thể **lạc quan hơn** thực tế.

Hạ tầng, HTTPS và PostgreSQL thì là thật.

#### D4. p95 13,5 giây có chấp nhận được không?

Chưa tốt. Phần lớn là thời gian gọi mô hình qua gateway bên ngoài. Đã có ngân sách timeout
phân tầng AI 30 s < backend 50 s để lỗi không dồn ngược lên khách.
Giảm p95 xuống dưới 8 s nằm trong hướng phát triển trung hạn.

#### D5. Hệ thống chịu được bao nhiêu bàn cùng lúc?

**Chưa biết** — nhóm chưa kiểm thử tải. Số p50 8,6 s và p95 13,5 s đo trên **một máy, một
người dùng**. Kiểm thử tải trên staging nằm trong hướng phát triển ngắn hạn.

#### D6. VietQR đã tự động đối soát chưa?

Chưa. Hiện chỉ **sinh mã**, quầy đối chiếu rồi bấm xác nhận thủ công. Cần hợp đồng và webhook
với ngân hàng. Rủi ro còn lại là thao tác người ở bước xác nhận tiền.

#### D7. Độ phủ mã nguồn là bao nhiêu?

**Không có số.** Nhóm chưa thiết lập cách thu thập nhất quán cho cả ba stack, và không muốn ghi
một con số không tự đo được. Tổng số test và số ca đạt **không** được diễn giải thay cho độ phủ.

#### D8. Nếu có thêm hai tuần thì làm gì trước?

Theo thứ tự: hoàn tất nhãn dị nguyên 47 món còn lại và **đưa bếp xác nhận** →
lập **tập niêm phong mới chưa từng mở** → mở nút hủy món cho khách (rẻ nhất, không đổi
cơ sở dữ liệu) → kiểm thử tải trên staging.

#### D9. Khách có biết còn bao lâu nữa thì món lên không?

**Không.** Khách thấy được trạng thái — *đang chuẩn bị* / *đã sẵn sàng* — nhưng không có
con số thời gian. Đây là hạn chế đã ghi trong báo cáo.

Lý do không phải vì khó về kỹ thuật mà vì **thiếu dữ liệu**: ước lượng đáng tin cần thời
gian chế biến thực tế của từng món do bếp cung cấp, và cần mốc thời gian đo theo từng món,
trong khi bảng lịch sử hiện chỉ ghi mốc ở **cấp lượt gọi**. Nhóm chọn không hiển thị một
con số tự đặt: giao diện cập nhật theo thời gian thực nên ước lượng sai sẽ lộ ra ngay
trước mắt khách, và điều đó hại lòng tin hơn là không hiển thị gì.

Cách làm đúng khi có thời gian: **đo trước, hiển thị sau** — thu mốc theo từng món, đối
chiếu với thời gian bếp tự khai, tính cả độ sâu hàng đợi (cùng một món sẽ lâu hơn khi có
mười phiếu đang chờ), rồi mới hiển thị khi sai số đủ nhỏ.

#### D10. Khách đặt nhầm thì hủy món thế nào?

Hiện tại khách **gọi nhân viên**, nhân viên hoặc bếp bấm hủy. Cần phân biệt rõ hai chuyện:

| | Trạng thái |
|---|---|
| Quy tắc hủy ở tầng nghiệp vụ | ✅ Đã có — món chỉ hủy được khi còn `Pending` hoặc `Preparing`; cả lượt gọi bị **khóa hủy** ngay khi một món vào `Preparing`; hủy bị chặn nếu hóa đơn bàn đang chờ thanh toán |
| Nút hủy trên màn hình bếp / phục vụ / quản trị | ✅ Đã có |
| Nút hủy trên màn hình khách | ❌ Chưa có |

Phần thiếu nằm ở **lớp xác thực**, không phải nghiệp vụ: endpoint đổi trạng thái món hiện
yêu cầu vai trò nhân viên, trong khi khách đi theo cơ chế **thẻ truy cập theo lượt gọi**
chứ không có vai trò trong hệ thống. Muốn mở cho khách chỉ cần thêm nhánh xác thực theo
thẻ đó và giới hạn khách chỉ hủy được món còn `Pending` — không đụng tới lược đồ cơ sở dữ
liệu. Đây là việc rẻ nhất trong danh sách ngắn hạn.

Vì sao khách không nên hủy được món đang `Preparing`: bếp đã tốn nguyên liệu và công, nên
quyết định đó phải có người của nhà hàng tham gia.

---

## Sáu câu không được nói

| Đừng nói | Nói thay bằng |
|---|---|
| "Hệ thống an toàn tuyệt đối cho người dị ứng" | "Không ghi nhận lỗi trên tập ca đã công bố, với bảng nhãn hiện tại" |
| "AI không bao giờ bịa" | "Hàng rào chặn 8/8 câu vi phạm trên tập đã đo" |
| "Đã kiểm thử đầy đủ" | "Bốn tầng kiểm thử; chưa có kiểm thử tải và chưa có báo cáo độ phủ" |
| "Tập niêm phong cho thấy khả năng khái quát" | "Tập đã mở hai lần nên chỉ còn giá trị hồi quy" |
| "Hệ thống chịu được nhiều bàn cùng lúc" | "Chưa đo — số hiện tại là một máy, một người dùng" |
| "Sản phẩm giảm thời gian phục vụ" | "Chưa đo được; báo cáo chỉ kết luận về mức hoàn thành kỹ thuật" |
