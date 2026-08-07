# Kịch bản thuyết trình — CMC Restaurant

Bản này khớp với từng slide trong tệp `SLIDE_GIOI_THIEU_SAN_PHAM.pptx`. Nội dung cũng nằm sẵn ở phần **ghi chú** của mỗi slide, xem được trong chế độ Presenter View của PowerPoint.

**Tổng 2364 từ, ước khoảng 17–21 phút nói tùy tốc độ.**

## Slide 1 — TRƯỜNG ĐẠI HỌC CMC · KHOA CNTT & TT

[~40 giây]
Em chào thầy và các bạn. Nhóm em xin trình bày đồ án học phần Công nghệ phần
mềm: CMC Restaurant — hệ thống gọi món và theo dõi trạng thái đơn tại bàn bằng
mã QR, có tích hợp trợ lý AI tư vấn thực đơn.

Sản phẩm hiện đang chạy thật trên ba tên miền ghi ở dưới, nên trong phần trình
bày em sẽ dùng ảnh chụp trực tiếp từ hệ thống đang vận hành chứ không phải bản
dựng trên máy cá nhân.

Nội dung gồm bốn phần: bài toán và lý do chọn đề tài, giới thiệu sản phẩm và
chức năng, kiến trúc công nghệ, và cuối cùng là hạn chế cùng hướng phát triển.

---

## Slide 2 — ĐẶT VẤN ĐỀ

[~1 phút 30]
Trước hết là bài toán. Một yêu cầu gọi món nghe rất đơn giản, nhưng thực tế nó
đi qua bốn chủ thể: khách chọn món, nhân viên tiếp nhận, bếp chế biến, quầy lập
hóa đơn.

Điều đáng nói là mỗi bên chỉ cần một mảnh thông tin, nhưng cả bốn phải cùng
tham chiếu đúng một bàn, đúng một phiên và đúng một trạng thái.

Khi thông tin đi bằng lời nói và phiếu giấy thì trạng thái ấy không được ghi lại
ở một nơi chung. Hệ quả là khách phải chờ nhân viên mới hỏi được món tới đâu;
thông tin từ bàn phải qua nhiều người mới đến bếp; và đến lúc thanh toán, quầy
phải cộng tay nhiều lượt gọi của cùng một bàn.

Còn một khó khăn thứ hai xuất hiện ngay lúc chọn món: tên món không đủ để khách
biết nguyên liệu hay mức giá. Câu hỏi thật của khách không phải là một từ khóa,
mà là "hai người dưới ba trăm nghìn nên chọn gì", hay "món nào không có tôm".

Đây là quan sát của nhóm tại hai nhà hàng ở Hà Nội trong tuần đầu dự án. Nhóm
ghi rõ đây là cơ sở định hướng, không phải khảo sát có tính đại diện.

---

## Slide 3 — LÝ DO CHỌN ĐỀ TÀI

[~1 phút 30]
Từ bài toán đó, nhóm chọn hai điểm vào.

Thứ nhất là mã QR. Lý do bề mặt thì ai cũng thấy: khách dùng ngay trình duyệt,
không phải cài ứng dụng. Nhưng lý do quan trọng hơn là mã QR mang theo định danh
bàn ngay từ điểm vào. Em muốn nhấn mạnh một ý: giá trị kỹ thuật của đề tài không
nằm ở việc quét mã — quét mã thì công nghệ đã có sẵn — mà nằm ở phần xử lý sau
lần quét: xác thực bàn, mở hoặc tiếp tục đúng phiên, và giữ trạng thái qua nhiều
lượt tương tác.

Thứ hai là AI. Thực đơn là dữ liệu có cấu trúc, nhưng câu hỏi của khách thì
không. Một bộ lọc thông thường xử lý tốt điều kiện rõ ràng, nhưng khách diễn đạt
nhu cầu bằng rất nhiều cách. Mô hình ngôn ngữ hợp với bước hiểu câu hỏi và diễn
đạt câu trả lời; còn quyết định về món, giá và dị nguyên thì phải giao cho dữ
liệu chứ không giao cho mô hình.

Cột thứ ba là vì sao đề tài hợp với học phần. Bài toán cho phép vận dụng gần như
toàn bộ nội dung môn học. Riêng thành phần AI làm phát sinh thêm một yêu cầu mà
phần mềm thông thường không có: làm sao kiểm soát một thành phần có đầu ra xác
suất, đặt trong một hệ thống toàn quy tắc nghiệp vụ tất định.

Ngay từ đầu nhóm cũng đặt ranh giới: sản phẩm không nhằm thay thế nhân viên, và
AI không được tự quyết định thay khách.

---

## Slide 4 — GIỚI THIỆU SẢN PHẨM

[~1 phút 20]
Đây là sản phẩm. Một hệ thống web cho nhà hàng ăn tại chỗ: khách quét mã QR trên
bàn để xem thực đơn, hỏi trợ lý AI, gọi món nhiều lượt và theo dõi trạng thái
đơn cho tới lúc thanh toán. Cùng lúc đó bếp, quầy và quản trị viên làm việc trên
cùng một nguồn dữ liệu.

Có bốn vai trò, mỗi vai trò một giao diện riêng nhưng chung một backend. Khách
tại bàn, bếp, quầy thu ngân và quản trị viên.

Về quy mô: ba ứng dụng web, tám mươi tư endpoint REST, hai mươi tư bảng cơ sở dữ
liệu, khoảng chín mươi bảy nghìn dòng mã trên ba trăm bảy bảy tệp, và một thực
đơn chín mươi mốt món.

Hai điều em xin nói rõ để thầy đánh giá đúng phạm vi. Thứ nhất, sản phẩm chạy
thật trên VPS, sau HTTPS, với PostgreSQL — không phải bản dựng trên máy cá nhân.
Thứ hai, thực đơn hiện tại là dữ liệu mẫu do nhóm dựng để phát triển và đánh
giá, chưa phải thực đơn vận hành của một nhà hàng thương mại.

---

## Slide 5 — CHỨC NĂNG

[~2 phút]
Đi vào chức năng, bắt đầu từ phía khách.

Khách quét mã QR trên bàn. Hệ thống mở phiên mới hoặc tiếp tục phiên đang mở của
đúng bàn đó. Nếu bốn người cùng bàn cùng quét thì cả bốn vào chung một phiên chứ
không tạo ra bốn phiên.

Giỏ hàng nằm phía máy chủ chứ không nằm trong trình duyệt. Nên khách đóng tab
rồi quét lại vẫn còn giỏ, đổi sang điện thoại khác cũng vậy.

Khách gọi món nhiều lượt trong cùng một phiên. Lượt thứ hai không phải một đơn
rời — nó thuộc cùng phiên và cuối cùng gộp chung một hóa đơn.

Ảnh giữa là màn hình khách theo dõi trạng thái, với thanh bốn bước: gọi món, chế
biến, phục vụ, thanh toán. Thanh này cập nhật ngay khi bếp thao tác, khách không
phải bấm tải lại.

Ảnh bên phải là trợ lý AI. Ở đây khách vừa nói bị dị ứng với tôm, và danh sách
gợi ý thu từ sáu món xuống còn ba. Điều em muốn thầy chú ý là câu trả lời của
trợ lý: nó nói thẳng rằng thực đơn chưa ghi nhận chi tiết thành phần hải sản cho
những món này, và đề nghị khách hỏi lại nhân viên. Tức là khi dữ liệu chưa đủ,
hệ thống thu hẹp gợi ý và cảnh báo chứ không suy đoán.

---

## Slide 6 — CHỨC NĂNG

[~1 phút 40]
Phía nhà hàng có ba màn hình.

Bảng bếp, ảnh thứ nhất, chia món theo bốn trạng thái và cập nhật theo thời gian
thực. Bếp thao tác bằng vài chạm vì tay bận và màn hình đặt xa. Trên bảng này
bếp cũng bật tắt được tình trạng hết món, và thay đổi đó có hiệu lực ngay với
khách đang xem thực đơn.

Quầy thu ngân, ảnh thứ hai. Thẻ "Phiên hai lượt gọi" là minh chứng cho khái niệm
hóa đơn phiên bàn: khách gọi hai lần trong một lượt ngồi, hệ thống gộp thành một
hóa đơn chứ không phải hai. Khuyến mãi và tích điểm áp một lần lúc tất toán.

Hai ảnh còn lại là phần quản trị: quản lý thực đơn và sinh mã QR theo từng bàn.
Đây là lớp làm cho toàn bộ vòng đời phía trên chạy được — có thực đơn thì trợ lý
mới có dữ liệu để tư vấn, có mã QR theo bàn thì khách mới vào đúng phiên.

Một điểm thiết kế em xin nêu: mã nằm trong QR không phải thứ cấp quyền thao tác.
Khi khách quét, backend đổi nó lấy một capability token cấp riêng cho lần quét
đó. Nên một mã QR bị chụp lại vẫn chỉ mở được phiên của đúng bàn ấy.

---

## Slide 7 — KIẾN TRÚC

[~2 phút]
Về kiến trúc, nhóm chọn modular monolith cho phần nghiệp vụ và chỉ tách riêng
đúng một thứ là dịch vụ AI.

Lý do không dùng microservices: đơn hàng, thanh toán và tồn kho ở bài toán này
luôn thay đổi cùng nhau và cần nhất quán ngay. Tách chúng ra thì phải dựng saga
để mô phỏng lại thứ mà một transaction cơ sở dữ liệu vốn cho sẵn — tức là tự tạo
ra vấn đề rồi tự giải nó.

Nhưng dịch vụ AI thì được tách, theo một tiêu chí khác hẳn: khác ngôn ngữ, ảnh
Docker 2,74 GB so với khoảng 200 MB của backend, và nhịp thay đổi khác — nó đổi
theo phép đo chất lượng chứ không theo tính năng nhà hàng. Kết luận nhóm rút ra
là tiêu chí tách dịch vụ nên là sự khác biệt về vòng đời, không phải sự gọn gàng
của sơ đồ.

Nguyên tắc giữ nhất quán từ đầu tới cuối: mọi đường đi của dữ liệu đều qua
backend. Ba ứng dụng trình duyệt không bao giờ gọi thẳng dịch vụ AI, và dịch vụ
AI không bao giờ chạm vào cơ sở dữ liệu. Nhờ vậy backend là nơi duy nhất có thẩm
quyền về quyền và dữ liệu.

Bảng bên phải là các công nghệ đã chọn, mỗi dòng kèm lý do gắn với bài toán này
chứ không phải lý do chung chung.

---

## Slide 8 — ĐIỂM KỸ THUẬT

[~2 phút]
Hai điểm kỹ thuật nhóm cho là cốt lõi.

Thứ nhất, bên trái, là máy trạng thái của phiên bàn. Nó trả lời câu hỏi: khi một
người quét mã của bàn T07, hệ thống lấy gì để quyết định đưa họ tới màn hình
nào? Câu trả lời cố tình không dựa vào thiết bị hay lịch sử trình duyệt, vì hai
thứ đó mất khi khách đổi máy hoặc đóng tab. Nó dựa vào trạng thái của chính phiên
bàn trên máy chủ.

Sáu trạng thái này được suy ra chứ không lưu sẵn. Hệ thống không có cột
resume_state để cập nhật; nó tính lại từ danh sách đơn và trạng thái hóa đơn mỗi
lần khách quét. Cách này chậm hơn một chút nhưng loại bỏ hẳn một lớp lỗi mà nhóm
đã gặp ở bản đầu: cột trạng thái lưu sẵn bị lệch khỏi dữ liệu thật.

Thứ hai, bên phải, là ranh giới quyền của AI. Mô hình được HIỂU câu hỏi và VIẾT
câu trả lời, nhưng bước CHỌN món thì mô hình không được chạm vào — đó là mã tất
định lọc thực đơn theo bảng nhãn.

Vì sao phải tách như vậy? Vì nếu để mô hình chọn món thì không có cách nào chứng
minh nó sẽ luôn loại món có tôm cho khách dị ứng tôm — thử bao nhiêu câu cũng
không đủ. Khi việc chọn là một phép lọc trên bảng nhãn, câu hỏi chuyển thành
"bảng nhãn có đúng không", và điều đó thì tra được, kiểm được, có test canh.

Số đo xác nhận: lọc theo nhãn đúng tám trên tám ca chọn món, còn để RAG chọn thì
chỉ đúng một đến hai trên tám.

---

## Slide 9 — BẢO ĐẢM CHẤT LƯỢNG

[~1 phút 40]
Về bảo đảm chất lượng, nhóm có bốn tầng kiểm thử: một trăm mười tám test
frontend, tám mươi tư test backend, ba trăm tám sáu test cho mã dịch vụ AI, và
một trăm hai tám test cho chính bộ thước đo. Ngoài ra có bộ golden đầu-cuối chạy
trên stack thật, đạt một trăm linh ba trên một trăm linh ba lượt.

Sơ đồ bên trái là dòng chảy CI/CD. Điểm em muốn nhấn: năm job CI không chỉ chạy
để báo cáo, chúng là điều kiện bắt buộc để merge, khai báo trong branch ruleset
của nhánh main và develop. Và danh sách ngoại lệ để rỗng — kể cả chủ repository
cũng không bỏ qua được. Nhóm bỏ hẳn cửa ngoại lệ vì một cổng chặn có ngoại lệ
cho người quyền cao nhất thì đúng lúc nguy hiểm nhất nó sẽ không chặn.

Nhóm cũng không dừng ở tích hợp liên tục: develop tự động triển khai lên staging,
main tự động lên production, và rollback tự kích hoạt khi kiểm tra khói sau
triển khai thất bại.

Cuối cùng là một câu hỏi nhóm tự đặt thêm mà sách không nêu: ai kiểm chính thước
đo dùng để chấm đầu ra AI? Nhóm viết một bộ dò đưa những câu trả lời cố ý vô
nghĩa vào thước đo và đòi thước đo phải cho trượt. Bộ dò tìm ra hai mươi tư
trường hợp chấp nhận sai, và cả hai mươi tư đã được khắc phục. Nếu bỏ qua bước
này thì mọi con số do thước đo tạo ra đều đáng nghi.

---

## Slide 10 — KẾT LUẬN

[~1 phút 40]
Cuối cùng là hạn chế và hướng phát triển.

Về hạn chế, nhóm nêu thẳng sáu điểm. Quan trọng nhất là nhãn dị nguyên mới phủ
bốn mươi bốn trên chín mươi mốt món, và bảng nhãn chưa được bếp xác nhận. Cơ chế
fail-closed khiến rủi ro nghiêng về phía thu hẹp gợi ý chứ không phải gợi ý sai,
nhưng em xin nói rõ: điều đó chưa đủ để kết luận hệ thống an toàn về mặt y tế.

VietQR mới dừng ở mức sinh mã, quầy vẫn xác nhận thủ công. Độ trễ trợ lý còn
cao, p95 mười ba phẩy năm giây. Và nhóm chưa kiểm thử tải, chưa có báo cáo độ
phủ mã nguồn, chưa kiểm thử khả năng tiếp cận.

Hướng phát triển bên phải chia ba giai đoạn. Ngắn hạn tập trung đóng lại chính
những hạn chế vừa nêu, vì đó là cách rẻ nhất để nâng độ tin cậy. Trung hạn là
giảm độ trễ và tích hợp webhook ngân hàng. Dài hạn là nhiều chi nhánh và học từ
phản hồi khách.

Kết lại, kết quả nhóm coi trọng nhất không phải số tính năng đã làm, mà là khả
năng truy vết: từ nhu cầu người dùng tới user story, tới yêu cầu, tới kiến trúc,
tới mã nguồn, tới kiểm thử và số đo. Mọi con số trong báo cáo đều kèm lệnh chạy
lại được ở phụ lục.

Phần trình bày của nhóm em đến đây là hết. Em xin cảm ơn thầy và các bạn đã lắng
nghe, và sẵn sàng nhận câu hỏi ạ.

---
