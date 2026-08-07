# Kịch bản thuyết trình — Đồ án chuyên ngành

Bản này sinh tự động từ phần **ghi chú** của `SLIDE_DO_AN_CHUYEN_NGANH.pptx` (`xuat_kich_ban.py`), nên luôn khớp với slide đang dùng. Trong lúc trình bày, mở **Presenter View** của PowerPoint là thấy đúng nội dung này.

**11 slide · 1840 từ · khoảng 14–18 phút** tùy tốc độ nói.

---

## Slide 1 — CMC Restaurant – Hệ thống quản lý nhà hàng, gọi món bằng QR và tư vấn…

[~40 giây]
Em chào thầy và các bạn. Nhóm em xin trình bày đồ án chuyên ngành, đề tài CMC
Restaurant — hệ thống quản lý nhà hàng, gọi món bằng mã QR và tư vấn món ăn
bằng AI.

Sản phẩm đang chạy thật trên ba tên miền ghi ở dưới, nên phần trình bày sẽ dùng
ảnh chụp trực tiếp từ hệ thống đang vận hành.

## Slide 2 — Nội dung trình bày

[~30 giây]
Phần trình bày gồm bảy phần. Em bắt đầu từ bài toán thực tế, sau đó là mục tiêu
và phạm vi, rồi giới thiệu sản phẩm và các chức năng chính. Phần kiến trúc và
thiết kế là phần kỹ thuật trọng tâm. Cuối cùng là kết quả đo, hạn chế và hướng
phát triển.

## Slide 3 — Một yêu cầu gọi món đi qua bốn chủ thể

[~1 phút 20]
Một yêu cầu gọi món nghe đơn giản nhưng thực tế đi qua bốn chủ thể: khách chọn
món, nhân viên tiếp nhận, bếp chế biến, quầy lập hóa đơn.

Mỗi bên chỉ cần một mảnh thông tin, nhưng cả bốn phải cùng tham chiếu đúng một
bàn, đúng một phiên và đúng một trạng thái.

Khi thông tin đi bằng lời nói và phiếu giấy thì trạng thái ấy không được ghi lại
ở một nơi chung. Hệ quả là khách phải chờ nhân viên mới hỏi được món tới đâu;
thông tin từ bàn phải qua nhiều người mới đến bếp; và lúc thanh toán, quầy phải
cộng tay nhiều lượt gọi.

Còn khó khăn thứ hai xuất hiện ngay lúc chọn món: tên món không đủ để khách biết
nguyên liệu hay mức giá. Câu hỏi thật của khách là "hai người dưới ba trăm nghìn
nên chọn gì", chứ không phải một từ khóa.

## Slide 4 — Mục tiêu và phạm vi

[~1 phút]
Từ bài toán đó, nhóm đặt sáu mục tiêu, sắp theo đúng thứ tự ưu tiên.

Ba mục tiêu đầu là luồng nghiệp vụ chính: điểm vào bằng QR, luồng gọi món, và
chuỗi vận hành phía nhà hàng.

Mục tiêu thứ tư là điều kiện kỹ thuật cho ba mục tiêu trên: một nguồn trạng thái
nhất quán giữa mọi vai trò.

Mục tiêu thứ năm là trợ lý AI, và em xin nhấn: nó là lớp hỗ trợ, không phải trung
tâm điều khiển.

Mục tiêu thứ sáu là kiểm thử và triển khai — thứ quyết định sản phẩm có kiểm
chứng được hay không.

Bên phải là bốn thứ nhóm cố ý để ngoài phạm vi, ghi rõ để không bị hiểu là thiếu sót.

## Slide 5 — Sản phẩm và bốn vai trò sử dụng

[~1 phút]
Đây là sản phẩm. Một hệ thống web cho nhà hàng ăn tại chỗ, phục vụ bốn vai trò,
mỗi vai trò một giao diện riêng nhưng chung một backend.

Về quy mô: năm ứng dụng web, tám mươi tư endpoint, hai mươi tư bảng dữ liệu,
khoảng chín mươi bảy nghìn dòng mã, thực đơn chín mươi mốt món.

Hai điều em xin nói rõ để thầy đánh giá đúng phạm vi. Thứ nhất, sản phẩm chạy
thật trên máy chủ, sau HTTPS, không phải bản dựng trên máy cá nhân. Thứ hai,
thực đơn hiện tại là dữ liệu mẫu, chưa phải thực đơn vận hành của nhà hàng
thương mại.

## Slide 6 — Luồng khách tại bàn và trợ lý AI

[~1 phút 40]
Bắt đầu từ phía khách. Khách quét mã QR trên bàn; hệ thống mở phiên mới hoặc
tiếp tục phiên đang mở của đúng bàn đó. Bốn người cùng bàn cùng quét thì vào
chung một phiên chứ không tạo ra bốn phiên.

Giỏ hàng nằm phía máy chủ chứ không trong trình duyệt, nên đóng tab rồi quét lại
vẫn còn giỏ.

Khách gọi món nhiều lượt trong cùng phiên; lượt thứ hai không phải đơn rời mà
gộp chung một hóa đơn.

Ảnh giữa là màn hình theo dõi trạng thái với thanh bốn bước, cập nhật ngay khi
bếp thao tác.

Ảnh bên phải là trợ lý AI. Khách vừa nói dị ứng tôm và danh sách gợi ý thu từ
sáu món xuống ba. Điều đáng chú ý là trợ lý nói thẳng rằng thực đơn chưa ghi
nhận chi tiết thành phần hải sản và đề nghị khách hỏi lại nhân viên — tức là khi
dữ liệu chưa đủ, hệ thống thu hẹp và cảnh báo chứ không đoán.

## Slide 7 — Vận hành nhà hàng và quản trị

[~1 phút 20]
Phía nhà hàng có bốn màn hình.

Bảng bếp chia món theo bốn trạng thái, cập nhật thời gian thực. Bếp thao tác vài
chạm vì tay bận và màn hình đặt xa. Trên bảng này bếp cũng bật tắt được tình
trạng hết món, và thay đổi đó có hiệu lực ngay với khách đang xem thực đơn.

Quầy thu ngân gộp mọi lượt gọi của phiên thành một hóa đơn. Khuyến mãi và tích
điểm áp một lần lúc tất toán chứ không áp theo từng lượt.

Hai ảnh còn lại là phần quản trị: quản lý thực đơn và sinh mã QR theo bàn. Đây
là lớp làm cho toàn bộ vòng đời phía trên chạy được.

## Slide 8 — Kiến trúc hệ thống

[~1 phút 30]
Về kiến trúc, nhóm chọn modular monolith cho phần nghiệp vụ và chỉ tách riêng
đúng một thứ là dịch vụ AI.

Lý do không dùng microservices: đơn hàng, thanh toán và phiên bàn ở bài toán này
luôn thay đổi cùng nhau và cần nhất quán ngay. Tách ra thì phải dựng saga để mô
phỏng lại thứ mà một transaction vốn cho sẵn.

Nhưng dịch vụ AI được tách, theo tiêu chí khác hẳn: khác ngôn ngữ, ảnh Docker
2,74 GB so với khoảng 200 MB của backend, và nhịp thay đổi khác. Kết luận nhóm
rút ra: tiêu chí tách dịch vụ là khác biệt về vòng đời, không phải sự gọn gàng
của sơ đồ.

Nguyên tắc giữ nhất quán: mọi đường đi của dữ liệu đều qua backend. Nhờ vậy
backend là nơi duy nhất có thẩm quyền về quyền và dữ liệu.

## Slide 9 — Hai điểm kỹ thuật cốt lõi

[~1 phút 50]
Hai điểm kỹ thuật nhóm cho là cốt lõi.

Bên trái là máy trạng thái phiên bàn. Nó trả lời câu hỏi: khi một người quét mã
của bàn T07, hệ thống lấy gì để quyết định đưa họ tới màn hình nào? Câu trả lời
cố tình không dựa vào thiết bị hay lịch sử trình duyệt, vì hai thứ đó mất khi
khách đổi máy. Nó dựa vào trạng thái của chính phiên bàn trên máy chủ.

Sáu trạng thái này được suy ra chứ không lưu sẵn — tính lại từ danh sách đơn và
trạng thái hóa đơn mỗi lần quét. Cách này chậm hơn chút nhưng loại bỏ hẳn lớp
lỗi mà nhóm đã gặp ở bản đầu: cột trạng thái lưu sẵn bị lệch khỏi dữ liệu thật.

Bên phải là ranh giới quyền của AI. Mô hình được HIỂU câu hỏi và VIẾT câu trả
lời, nhưng bước CHỌN món thì không được chạm vào — đó là mã tất định lọc theo
bảng nhãn.

Vì sao phải tách? Vì nếu để mô hình chọn thì không có cách nào chứng minh nó
luôn loại món có tôm cho khách dị ứng tôm — thử bao nhiêu câu cũng không đủ. Khi
chọn là phép lọc trên bảng nhãn, câu hỏi chuyển thành "bảng nhãn có đúng không",
và điều đó tra được, kiểm được.

Số đo xác nhận: lọc theo nhãn đúng tám trên tám, còn để RAG chọn chỉ đúng một
đến hai trên tám.

## Slide 10 — Kiểm thử và kết quả đo

[~1 phút 20]
Về bảo đảm chất lượng, nhóm có bốn tầng kiểm thử: 118 test frontend, 84 test
backend, 386 test cho mã dịch vụ AI, và 128 test cho chính bộ thước đo. Ngoài ra
có bộ kiểm thử đầu-cuối chạy trên stack thật, đạt 103 trên 103 lượt.

Tầng thứ năm là thứ ít ai làm: kiểm chính bộ thước đo. Phần AI không so được đầu
ra với một giá trị cố định, nó cần hàm chấm điểm — mà hàm chấm điểm cũng là mã,
và mã thì có lỗi. Nhóm viết một bộ dò đưa những câu trả lời cố ý vô nghĩa vào
thước đo và đòi thước đo phải cho trượt. Bộ dò tìm ra 24 trường hợp chấp nhận
sai, và cả 24 đã được khắc phục. Nếu bỏ qua bước này thì mọi con số đều đáng nghi.

Bộ kiểm thử đầu-cuối cũng ra đời từ một sự cố thật: hai dịch vụ trao đổi dữ liệu
theo hai giả định khác nhau về khuôn dạng, khiến luồng hỏng — trong khi kiểm thử
riêng của cả hai đều xanh.

## Slide 11 — Hạn chế và hướng phát triển

[~1 phút 30]
Cuối cùng là hạn chế và hướng phát triển.

Về hạn chế, quan trọng nhất là nhãn dị nguyên mới phủ 44 trên 91 món và bảng
nhãn chưa được bếp xác nhận. Cơ chế fail-closed khiến rủi ro nghiêng về phía thu
hẹp gợi ý, nhưng em xin nói rõ: điều đó chưa đủ để kết luận hệ thống an toàn về
mặt y tế.

VietQR mới dừng ở mức sinh mã. Độ trễ trợ lý p95 còn 13,5 giây.

Hai hạn chế tiếp theo nằm ở trải nghiệm của khách. Thứ nhất, hệ thống chưa ước
lượng được còn bao lâu thì món lên. Khách thấy được trạng thái đang chuẩn bị hay
đã sẵn sàng, nhưng không biết phải chờ bao lâu. Nhóm có cân nhắc gắn một con số
ước lượng, nhưng đã quyết định không làm, vì muốn ước lượng đáng tin thì cần
thời gian chế biến thật của từng món do bếp cung cấp, mà nhóm chưa có. Hiển thị
một con số tự đặt rồi để khách thấy sai thì hại hơn là không hiển thị gì.

Thứ hai, khách chưa tự hủy món được. Ở đây em xin nói rõ để tránh hiểu nhầm:
quy tắc hủy thì đã có đầy đủ ở tầng nghiệp vụ — món chỉ hủy được khi bếp chưa
làm xong, và cả lượt gọi bị khóa hủy ngay khi một món vào bếp — và màn hình
bếp, phục vụ, quản trị đều đã có nút hủy. Phần còn thiếu chỉ là nút phía khách,
vì endpoint hiện chỉ mở cho tài khoản nhân viên còn khách thì đi bằng thẻ truy
cập theo lượt gọi. Đây là việc rẻ nhất trong danh sách hướng phát triển vì
không phải đổi cơ sở dữ liệu.

Ngoài ra nhóm chưa kiểm thử tải, chưa có báo cáo độ phủ mã nguồn.

Hướng phát triển chia ba giai đoạn, trong đó ngắn hạn tập trung đóng lại chính
những hạn chế vừa nêu.

Kết lại, kết quả nhóm coi trọng nhất không phải số tính năng đã làm, mà là khả
năng truy vết: từ nhu cầu người dùng tới thiết kế, mã nguồn, kiểm thử và số đo.
Mọi con số trong báo cáo đều kèm lệnh chạy lại được.

Phần trình bày của nhóm em đến đây là hết. Em xin cảm ơn và sẵn sàng nhận câu hỏi ạ.
