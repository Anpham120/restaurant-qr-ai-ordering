# BỘ CÂU HỎI PHẢN ỨNG — NHÓM TRƯỞNG (AI & DEVOPS)

Dành cho **nhóm trưởng**, phụ trách *dịch vụ AI/RAG · DevOps · kiến trúc · tích hợp*.
Trọng tâm tài liệu này là **AI (mục B)** và **DevOps (mục C)** — hai mảng thầy sẽ đào
sâu nhất vì chúng là phần bạn tự tay làm.

Bộ khác: [HOI_DAP_KY_THUAT.md](HOI_DAP_KY_THUAT.md) (65 câu về tính năng và công nghệ),
[CHUAN_BI_VAN_DAP.md](CHUAN_BI_VAN_DAP.md) (quy trình, CLO).

---

## Cách trả lời

Ba câu, đúng thứ tự, tổng 40–60 giây: **kết luận → bằng chứng → giới hạn**.

Bước giới hạn là bước ăn điểm. Riêng với AI, nó còn là bước **bắt buộc về mặt đạo đức**:
mọi phát biểu về an toàn dị nguyên phải kèm phạm vi, nếu không là nói quá.

**Khi bị hỏi cái không biết:** *"Chỗ đó bạn X phụ trách, em nắm ở mức hợp đồng: nhận vào
A, trả ra B."* Nhóm trưởng không cần biết mọi dòng mã, nhưng phải biết **ranh giới giữa
các mảng**.

---

## A. Số liệu phải thuộc

| Hạng mục | Số đúng |
|---|---|
| Nhãn dị nguyên đã phủ | **44 / 91 món** |
| Nhãn trong từ điển | 85 |
| Ca đánh giá AI | 80 ca |
| Lọc theo nhãn vs để mô hình chọn | **8/8** vs **1–2/8** |
| Hàng rào chặn câu vi phạm | **8/8** |
| Phép kiểm trong `verify()` | **8** |
| Độ chính xác truy hồi top-1 (embedding) | **0,921** |
| Độ trễ trợ lý | p50 **8,6 s** · p95 **13,5 s** |
| Ảnh Docker AI | **9,29 GB → 2,74 GB** |
| Khởi động dịch vụ AI | **97,3 s → 19,0 s** |
| Workflow GitHub Actions | **9** |
| Job bắt buộc trong `ci.yml` | **5** |
| Test AI / test backend | 388 / 84 |
| Bảng CSDL · migration · sự kiện realtime | 24 · **21** · **8** |

**Ba câu không được nói:** *"AI không bao giờ bịa"*, *"hệ thống an toàn cho người dị
ứng"*, *"đã kiểm thử đầy đủ"*. Cả ba đều sai và đều có phản chứng trong chính báo cáo.

---

## B. AI — phần hỏi sâu nhất

### B1. Hệ thống AI hoạt động theo mấy bước?

Bốn bước, và điểm mấu chốt là **mô hình ngôn ngữ không được làm bước 2**:

| Bước | Ai làm | Việc |
|---|---|---|
| **HIỂU** | Mô hình ngôn ngữ | Đọc câu hỏi, rút ra ràng buộc (dị ứng tôm, dưới 60 nghìn, không cay) |
| **CHỌN** | **Mã tất định** | Lọc thực đơn theo nhãn. Mô hình không tham gia |
| **VIẾT** | Mô hình ngôn ngữ | Diễn đạt lại danh sách đã được lọc |
| **CHẶN** | Mã tất định | 8 phép kiểm trên câu sinh; vi phạm thì bỏ câu, dùng khuôn mẫu |

**Bằng chứng cho việc tách bước CHỌN ra:** lọc theo nhãn đúng **8/8** ca; để mô hình tự
chọn chỉ đúng **1–2/8**. Đây không phải phỏng đoán thiết kế mà là số đo.

### B2. Vì sao mô hình không được chọn món?

Vì **chi phí của sai lầm ở hai bước không bằng nhau**. Viết câu sai thì đọc thấy ngay và
sửa được. Chọn nhầm một món chứa tôm cho người dị ứng tôm thì hậu quả không đảo ngược.

Nguyên tắc chung: **giao cho mô hình những việc mà sai còn cứu được, giữ lại cho mã tất
định những việc mà sai thì không**.

### B3. Tám phép kiểm trong `verify()` là gì?

Trả lời gọn — thầy chỉ cần thấy bạn biết chúng tồn tại và biết vì sao có từng cái:

1. Mã món mô hình khai đã dùng phải nằm trong danh sách đưa vào.
2. **Không được nhắc món thật nào ngoài danh sách đã lọc** — đây là phép kiểm quan trọng
   nhất: mô hình lôi một món thật khác vào, đúng tên đúng giá, nhưng món đó chưa qua bộ
   lọc nên **có thể mang nhãn khách cần tránh**.
3. Mọi số tiền phải là giá thật của một món trong danh sách, hoặc chính con số khách vừa nêu.
4. Không được nêu số lượng, trừ khi trùng số món trong danh sách.
5. Không được in khóa nhãn nội bộ (`spice:none`) vào chữ khách đọc.
6. Phải nhắc đủ mọi món trong danh sách.
7. Không nhắc lặp cùng một món.
8. Phải có cụm mở đường hỏi nhân viên khi khách nêu điều cần tránh.

Vi phạm **bất kỳ** phép nào thì câu sinh bị **bỏ hẳn** — không sửa, không thử lại — và
hệ thống dùng lại câu khuôn mẫu.

### B4. Phép kiểm số 3 có ngoại lệ. Vì sao? *(câu hay được hỏi vặn)*

Vì phép kiểm ban đầu **chặn oan** một hành vi đúng, và nhóm phát hiện điều đó trên stack
thật:

> khách: *"Có món chay nào dưới 60 nghìn không?"*
> câu sinh bị bỏ, lý do: *"số tiền 60.000đ không phải giá của món nào trong danh sách"*

Mô hình không bịa gì — nó nhắc lại đúng ngân sách khách vừa nói, mà nhắc lại ràng buộc là
điều một câu tư vấn tốt **nên** làm. Nhóm nới phép kiểm để chấp nhận thêm đúng một con
số: `budget_max`, con số duy nhất khách nêu mà hệ thống đọc được thành số.

**Bài học nên nói ra:** một phép kiểm quá chặt không làm hệ thống an toàn hơn, nó chỉ
làm đường tốt hơn không bao giờ được dùng.

### B5. Có loại bịa nào hệ thống KHÔNG bắt được không? *(phải trả lời thật)*

**Có.** Một tên món **hoàn toàn bịa** — không tồn tại trong thực đơn dưới bất kỳ dạng nào
— thì phép so chuỗi không phát hiện được. Ví dụ "Bò sốt tiêu đen Hoàng Gia".

Hệ thống bắt được ba thứ: món thật nằm ngoài danh sách đã lọc, giá không có trong thực
đơn, và món mang nhãn khách cần tránh. Không bắt được món bịa hoàn toàn.

**Giảm nhẹ, không xóa được:** thẻ giỏ hàng và danh sách món trả về đều **dựng từ dữ liệu
tất định chứ không từ chữ mô hình viết**, nên dù một câu bịa lọt qua, khách vẫn **không
đặt được món không tồn tại**. Ngoài ra `golden-e2e` có phép kiểm số tiền trên câu trả lời
thật.

Đây là câu nên chủ động kể. Thừa nhận một lỗ hổng kèm cơ chế giảm nhẹ thì mạnh hơn nhiều
so với bị hỏi rồi mới thừa nhận.

### B6. Mô hình sinh được bật ở những trường hợp nào?

**Chỉ hai nhánh**: `filter` và `compare` — tức loại C theo phân loại của đề bài (suy luận
và diễn đạt).

Không bật ở: tra cứu thực đơn (loại A, đề bài **cấm** dùng mô hình sinh), tri thức nhà
hàng (loại B, trả đoạn nguyên văn, mô hình không chạm chữ), và ba nhánh `no_data`,
`refuse`, `clarify`.

**Lý do không sinh ở nhánh từ chối:** chưa hiểu câu hỏi thì không có gì để viết hay hơn,
và **một câu từ chối do mô hình viết là chỗ dễ rò rỉ nhất**.

### B7. Vì sao chọn embedding mà không dùng hybrid? *(số liệu lật quyết định cũ)*

Vì đo lại thì kết quả trái với dự đoán ban đầu:

| Phân vùng | BM25 | Embedding | Hybrid |
|---|---|---|---|
| Phát triển (124 ca) | 0,803 | **0,921** | 0,908 |
| Phân vùng thứ hai (44 ca) | 0,750 | 0,864 | **0,886** |

Ở phân vùng phát triển, hybrid **thua** embedding đơn lẻ trong khi vẫn tốn thêm một tầng
xếp hạng. Tài liệu kiến trúc trước đó của nhóm đã chốt *"hybrid thắng"*; nhóm bỏ hybrid
và **giữ tài liệu cũ trong thư mục lưu trữ kèm ghi chú**, vì nó ghi lại điều kiện nào
từng làm kết luận đó đúng.

**Giới hạn phải nói:** phân vùng thứ hai ban đầu là tập niêm phong nhưng **đã bị mở hai
lần**, nên số trên nó chỉ có giá trị hồi quy, không phải ước lượng độc lập về khả năng
khái quát.

Câu này đáng chủ động kể: nó cho thấy nhóm sửa quyết định theo số đo chứ không bảo vệ
quyết định cũ.

### B8. Vì sao không fine-tune mô hình?

Vì **thực đơn thay đổi liên tục**. Fine-tune thì mỗi lần đổi món lại phải huấn luyện
lại; truy hồi thì chỉ cần cập nhật kho tri thức, và cập nhật đó kiểm chứng được bằng
`build_knowledge.py --check` trong CI.

Thêm nữa, fine-tune **không** giải quyết bài toán an toàn dị nguyên: mô hình được huấn
luyện vẫn là mô hình xác suất, vẫn không được phép quyết định món nào an toàn.

### B9. Kho tri thức tổ chức thế nào?

Ba nhóm: `written` (viết tay), `derived` (sinh từ dữ liệu thực đơn), `policy` (chính sách
nhà hàng). Chia đoạn bằng `chunker.py`, và **CI kiểm rằng kho sinh lại được**:
`build_knowledge.py --check` sẽ đỏ nếu file markdown và bản đã chia đoạn lệch nhau.

**Nguyên tắc:** văn xuôi kể lại dữ liệu thì luôn trôi khỏi dữ liệu. Nên phần `derived`
được sinh từ nguồn chứ không chép tay, và từ điển nhãn cũng vậy —
`build_tag_dictionary.py --check` bảo đảm 85 nhãn trong tài liệu khớp với thực đơn.

### B10. Bộ đánh giá AI thiết kế ra sao?

**80 ca** trong `cases.json`. Điểm khác thường: một ca **không** ghi "đáp án là m_008,
m_012" mà ghi **điều kiện** mà đáp án phải thỏa.

Bốn lợi ích của cách này:
1. Thực đơn đổi thì khóa đáp án tự đúng theo, không phải sửa tay 80 ca.
2. **Kiểm được chính tập ca** — điều kiện chọn ra 0 món là ca viết sai, và lộ ra ngay.
3. Chia nhóm tất định bằng `build_split.py`, chạy lại cho cùng kết quả.
4. Trường `why` là **bắt buộc** — ca nào không giải thích được thì không được nhận.

### B11. Làm sao chứng minh AI không gợi ý món chứa dị nguyên khách đã nêu?

Bằng **cấu trúc chứ không bằng lời hứa**: mô hình không có đường ghi vào bước CHỌN. Bộ
lọc chạy trên nhãn, và cơ chế là **fail-closed** — món **thiếu nhãn thì bị loại khỏi gợi
ý**, không được cho qua.

Nghĩa là rủi ro nghiêng về phía **thu hẹp gợi ý**, không phải gợi ý sai.

**Giới hạn bắt buộc nói, không được bỏ:** nhãn dị nguyên mới phủ **44/91 món** và **chưa
được bếp xác nhận**. Kết luận đúng phải là: *"không ghi nhận lỗi trên tập ca đã công bố,
với bảng nhãn hiện tại"*. Chưa đủ căn cứ kết luận an toàn về mặt y tế trong vận hành thật,
vì ba lý do: nhãn chưa phủ hết, nhãn chưa ai có chuyên môn đối chiếu, và một tập ca hữu
hạn không bao giờ chứng minh được tính chất phổ quát.

### B12. Nếu dịch vụ AI chết thì khách có dùng được nữa không?

**Có.** Suy giảm êm là một yêu cầu phi chức năng có kiểm thử: lỗi nội bộ của AI **không**
thành màn hình lỗi cho khách. Dịch vụ bắt exception rộng, trả HTTP 200 kèm câu chuyển
nhân viên.

Ba chỗ được bảo vệ riêng: kho tri thức hỏng **không** làm dịch vụ không khởi động được;
`/ready` phải trả lời được cả khi kho hỏng; và truy hồi hỏng **không** làm sập luồng trả
lời khách.

**Quan trọng hơn:** AI là **lớp hỗ trợ**, không nằm trên đường gọi món. Khách vẫn xem
thực đơn, thêm giỏ, gửi bếp bình thường khi AI chết.

### B13. AI có được sửa giỏ hàng không?

**Không.** Thêm món vào giỏ là **một lời gọi API hoàn toàn riêng** do người dùng bấm;
dịch vụ AI không tham gia và cũng không được thông báo.

Ranh giới cố ý: đầu ra xác suất không được ghi vào dữ liệu tiền bạc.

### B14. Vì sao tách dịch vụ AI ra riêng?

Tiêu chí **không phải** cho sơ đồ gọn mà là **khác biệt về vòng đời**. Thư viện xử lý
ngôn ngữ làm ảnh Docker phồng gần 3 GB, và mỗi lần sửa một endpoint thực đơn lại phải
đóng gói lại toàn bộ thư viện đó — biến thay đổi năm phút thành quy trình mười lăm phút.

Hai phần có nhịp thay đổi và nhu cầu tài nguyên khác nhau, nên tách. Các mô-đun nghiệp vụ
còn lại đều thay đổi cùng nhau theo một luồng gọi món, nên không tách.

### B15. Độ trễ p95 13,5 giây có chấp nhận được không?

**Chấp nhận được nhưng chưa tốt**, và phần lớn là thời gian gọi mô hình qua gateway bên
ngoài chứ không phải xử lý của nhóm.

Hướng giảm: cache câu hỏi lặp, rút ngắn prompt, cân nhắc mô hình nhỏ hơn cho bước HIỂU.
Mục tiêu trung hạn là dưới 8 giây.

**Giới hạn:** số này đo trên **một máy, một người dùng**. Chưa kiểm thử tải nên chưa biết
p95 ở nhiều phiên đồng thời.

### B16. Em có tự viết phần AI không hay dùng thư viện có sẵn?

Nói rõ ranh giới: nhóm **không** huấn luyện mô hình. Nhóm dùng mô hình embedding có sẵn
và một mô hình ngôn ngữ qua gateway.

Phần nhóm tự xây là **kiến trúc quanh mô hình**: kho tri thức ba nhóm, bước lọc tất định
theo nhãn, tám phép kiểm ở đường sinh, bộ 80 ca đánh giá, và cơ chế suy giảm êm. Đó cũng
chính là phần quyết định hệ thống có an toàn hay không — mô hình chỉ là một thành phần
thay thế được.

---

## C. DevOps — phần hỏi sâu thứ hai

### C1. Pipeline gồm những gì?

**9 workflow**, chia bốn nhóm:

| Nhóm | Workflow |
|---|---|
| Kiểm tra | `ci.yml` |
| Bảo mật | `security.yml`, `dependency-review.yml` |
| Triển khai | `deploy-staging.yml`, `promote-production.yml`, `deploy-production.yml`, `rollback.yml` |
| Tự động hóa | `auto-merge.yml`, `recover-9router.yml` |

### C2. `ci.yml` có mấy job, làm gì?

**5 job chạy song song**, và cả 5 đều là status check bắt buộc:

| Job | Kiểm gì |
|---|---|
| `frontend-build` | 5 ứng dụng build được |
| `backend-test` | 84 test, có PostgreSQL thật làm service container |
| `ai-data-and-eval` | Từ điển nhãn, migration nhãn, kho tri thức **sinh lại được**; dữ liệu lúc chạy có trong ảnh Docker; cơ chế an toàn **có chạy** |
| `golden-e2e` | Dựng **toàn bộ stack thật** rồi chạy chuỗi nghiệp vụ đầu cuối |
| `docker-compose-config` | Cấu hình compose hợp lệ |

Điểm đáng nói ở `ai-data-and-eval`: nó không chỉ chạy test mà **kiểm rằng dữ liệu sinh
lại được**. Nếu ai sửa tay file nhãn mà không sửa nguồn, CI đỏ.

### C3. Vì sao có job `golden-e2e` mà không dừng ở test đơn vị?

Vì một sự cố thật. Hai dịch vụ hiểu khác nhau về khuôn dạng khung dữ liệu SSE, làm luồng
hỏng — **trong khi kiểm thử riêng của cả hai dịch vụ đều đạt**, vì mỗi bên tự kiểm theo
giả định khuôn dạng của chính mình.

Không tầng kiểm thử thành phần nào bắt được loại lỗi này. Nên nhóm bổ sung một job dựng
toàn bộ stack thật rồi chạy chuỗi nghiệp vụ đầu cuối.

**Bài học:** test đơn vị chứng minh mỗi bên đúng theo giả định của mình; nó không chứng
minh hai giả định khớp nhau.

### C4. Cổng kiểm tra triển khai hai đầu là gì?

Hai script hỏi hai câu khác nhau nhưng **lấy kỳ vọng từ cùng một hàm**:

- `verify_deploy_config.py` chạy trong CI: *"cấu hình sắp triển khai có khớp bằng chứng
  đã đo không?"*
- `health-check.sh` chạy trên máy chủ: *"dịch vụ đang chạy có đúng cấu hình ấy không?"*

Lấy chung một nguồn kỳ vọng là điều bắt buộc — nếu hai bên tự định nghĩa thì lại đúng lớp
lỗi mà `golden-e2e` sinh ra để chống.

**Sinh ra từ sự cố thật:** nhóm phát hiện một biến môi trường **mô tả sai bộ truy hồi
đang chạy**. Biến đó không mô-đun nào đọc nên không gây lỗi — nhưng ai đọc cấu hình cũng
tin nó.

**Bài học đáng nói:** cấu hình sai còn nguy hiểm hơn thiếu tài liệu, vì thiếu tài liệu
khiến người ta đi hỏi, còn cấu hình sai khiến người ta tin chắc vào điều sai.

### C5. Đường đi từ merge tới production?

```
PR → ci.yml (5 job bắt buộc) → merge vào develop
   → deploy-staging.yml  + cổng verify_deploy_config
   → promote-production.yml  (mở PR develop → main)
   → deploy-production.yml  → smoke test
   → smoke đỏ → rollback.yml TỰ chạy
```

Bước tự quay lui nằm ngay trong `deploy-production.yml`: một bước `if: failure()` gọi
`gh workflow run rollback.yml -f environment=production`. **Không chờ người bấm.**

Mỗi lần deploy còn tải lên một artifact bằng chứng đo, để lần deploy nào cũng truy được
số liệu của chính nó.

### C6. Rollback có quay lui được cơ sở dữ liệu không? *(câu vặn hay gặp)*

**Không.** Rollback đưa mã về bản trước, nhưng **migration cơ sở dữ liệu không hoàn tác
được bằng một lần revert** — revert mã xong thì lược đồ vẫn đã đổi, và dữ liệu thật có
thể đã đổi theo.

Vì vậy nhóm bật tự động hợp nhất khi CI đạt, **trừ khi pull request đụng vào migration**
— khi đó bắt buộc có người xem.

**Nguyên tắc rút ra:** mức độ tự động hóa nên **tỉ lệ nghịch với chi phí của sai lầm**.

### C7. Branch ruleset bật khi nào? *(phải chủ động nói giới hạn)*

**Chỉ ở giai đoạn cuối**, và đây là hạn chế số 8 trong báo cáo.

Nói thẳng: 377 pull request trước đó qua CI **nhờ kỷ luật của nhóm chứ chưa nhờ cơ chế
bắt buộc**. Ruleset chỉ bảo đảm cho các thay đổi sau thời điểm kích hoạt. Lý do bật muộn
là cần quyền admin repository, thu xếp được muộn.

Nếu làm lại thì bật từ tuần đầu.

### C8. Các kiểm tra bảo mật có chặn merge không?

**Chưa.** CodeQL, secret-scan, trivy-fs, dependency-review **có chạy trên mọi pull
request nhưng chưa nằm trong danh sách status check bắt buộc**, nên một cảnh báo vẫn có
thể bị bỏ qua nếu người review không để ý.

Đưa bốn kiểm tra này vào ruleset là việc ngắn hạn số 8 trong hướng phát triển.

Đây là câu **nên tự nêu** thay vì để thầy phát hiện.

### C9. Ảnh Docker giảm bằng cách nào?

Từ **9,29 GB xuống 2,74 GB**, khởi động từ **97,3 giây xuống 19,0 giây**, bằng cách dùng
bản thư viện dành cho CPU thay vì bản kèm toàn bộ hỗ trợ GPU — hệ thống không chạy trên
GPU nên phần đó là trọng lượng chết.

**Giới hạn:** 2,74 GB vẫn lớn, và đó là hạn chế số 6. Đánh đổi có chủ đích để giữ chất
lượng embedding.

### C10. Ba môi trường tổ chức thế nào?

Staging, production, và đường quay lại. Ba tên miền cấu hình sau HTTPS. Staging nhận
merge vào `develop`; production chỉ nhận từ `main` qua PR do `promote-production.yml` mở.

**Giới hạn:** chưa có khả năng quan sát vận hành đầy đủ — chưa log tập trung, chưa
tracing, chưa cảnh báo khi tỷ lệ trả lời dự phòng tăng bất thường. Đó là việc trung hạn.

### C11. Vì sao kiểm cả "dữ liệu lúc chạy có trong ảnh Docker"?

Vì lớp lỗi kinh điển: chạy trên máy phát triển thì có file dữ liệu, đóng gói vào ảnh thì
`.dockerignore` loại mất, và lỗi chỉ lộ ra trên production. `test_packaging` kiểm điều đó
trong CI, trước khi ảnh được dựng.

### C12. Nhóm trưởng kiểm soát chất lượng phần không tự viết bằng cách nào?

Ba lớp: **CI chặn** (5 job bắt buộc), **quét tự động** (4 công cụ bảo mật), và **review
pull request**.

**Giới hạn phải thừa nhận:** human peer review chỉ được thiết lập ở giai đoạn cuối. PR
#426 có bốn lượt `APPROVED` trước khi merge, nhưng 377 PR trước đó chủ yếu dựa vào tự
kiểm tra và công cụ. Nhóm có bằng chứng review người cho quy trình bổ sung, nhưng không
chứng minh được toàn bộ lịch sử thay đổi đã có người phản biện.

---

## D. Quản trị nhóm

### D1. Vì sao nhóm trưởng chiếm phần lớn commit? *(câu dễ mất điểm nhất)*

**Không né, không bao biện.** Ba bước:

> Đúng là chênh lệch lớn — trên lịch sử git, phần em chiếm khoảng 90 % số commit của
> người thật. Có ba nguyên nhân, và một trong ba là lỗi điều hành của em.
>
> **Thứ nhất**, bốn mảng em nhận đều sinh nhiều commit: hạ tầng, CI/CD, kho tri thức AI
> và tài liệu — riêng chỉnh pipeline và dựng lại kho tri thức đã tạo rất nhiều commit nhỏ.
>
> **Thứ hai**, phần tích hợp giữa các mảng rơi vào em, mà tích hợp thì chạm nhiều tệp của
> nhiều người.
>
> **Thứ ba, và đây là chỗ em làm chưa tốt:** khi tiến độ gấp, em tự làm cho nhanh thay vì
> hướng dẫn để bạn khác làm. Việc đó đẩy tiến độ lên nhưng làm hỏng mục tiêu học tập của
> nhóm. Nếu làm lại, em sẽ chốt hạn "không tự làm thay" ngay từ tuần đầu.

**Bẫy phải tránh:** đừng nói *"các bạn ấy cũng làm nhiều lắm ạ"* mà không có bằng chứng —
thầy mở GitHub Insights ngay tại chỗ.

**Chi tiết kỹ thuật nên biết trước:** trong lịch sử git, tên tác giả của bạn bị tách làm
hai định danh (`Anpham120` và `Phạm Duy An`) do `user.email` khác nhau giữa hai máy. Nếu
biểu đồ contributor hiện số lệch với báo cáo thì đó là lý do. **Kiểm tra GitHub →
Insights → Contributors trước buổi bảo vệ.**

### D2. Nhóm chia việc theo nguyên tắc nào?

Chia **theo mô-đun, không theo lớp kỹ thuật** — không phải "một người làm hết backend"
mà mỗi người sở hữu trọn một mảng nghiệp vụ, để người đó trả lời được vì sao mảng của
mình thiết kế như vậy. Mỗi đầu việc mở một issue, gán người, đóng bằng một pull request.

### D3. Nếu làm lại thì làm khác chỗ nào?

1. **Không tự làm thay khi gấp** — chênh lệch đóng góp là hệ quả trực tiếp.
2. **Bật branch ruleset từ tuần đầu**, để CI là cổng chặn thật.
3. **Phủ đủ nhãn dị nguyên 91 món trước khi xây tính năng lọc**, thay vì xây trước phủ
   sau, khiến kết luận an toàn bị treo tới giờ.

---

## E. Bốn câu khó nhất

**E1. "Dự án có gì mới so với app đặt món đã có?"**
Không tuyên bố mới về thị trường. Khác biệt ở **cách kiểm soát AI**: mô hình chỉ HIỂU và
VIẾT, còn **CHỌN thì mã tất định làm**. Đó là lý do lọc dị nguyên đúng 8/8 thay vì 1–2/8.

**E2. "Sản phẩm có giảm thời gian phục vụ không?"**
**Chưa đo được.** Chưa thử ở nhà hàng thật nên không có số trước–sau. Báo cáo chỉ kết
luận về mức hoàn thành kỹ thuật.

**E3. "Em dám cho người dị ứng dùng hệ thống này chưa?"**
**Chưa.** Trước khi phục vụ khách thật phải làm ba việc: phủ nhãn đủ 91 món, đưa bảng
nhãn cho người có chuyên môn về nguyên liệu xác nhận, và giao diện phải nêu rõ trợ lý chỉ
mang tính tham khảo. Hiện tại cơ chế fail-closed khiến rủi ro nghiêng về thu hẹp gợi ý,
nhưng đó **không** phải bằng chứng an toàn y tế.

**E4. "Nếu mô hình ngôn ngữ ngừng hoạt động thì sao?"**
Hệ thống vẫn chạy. AI là lớp hỗ trợ chứ không nằm trên đường gọi món; dịch vụ trả câu
chuyển nhân viên và khách vẫn gọi món bình thường. Kiến trúc cũng cho phép **thay mô
hình** — phần giá trị nhóm tự xây là kho tri thức, bộ lọc và tám phép kiểm, không phụ
thuộc vào một mô hình cụ thể.

---

## Checklist trước khi vào phòng

- [ ] Mở sẵn repo, biết đường tới `ai/app/generate.py` (8 phép kiểm) và `.github/workflows/`
- [ ] Mở sẵn tab **GitHub → Actions** để chỉ được 9 workflow và lần chạy gần nhất
- [ ] Mở sẵn **Insights → Contributors**, biết con số đang hiển thị
- [ ] Thuộc mục A, đặc biệt **44/91 nhãn**, **8/8 vs 1–2/8**, **21 migration**, **8 sự kiện**
- [ ] Đọc lại **B5** (loại bịa không bắt được), **C7–C8** (giới hạn ruleset), **D1** — ba
      chỗ nên tự nêu trước khi bị hỏi
