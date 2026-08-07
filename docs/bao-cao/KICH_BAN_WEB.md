# Kịch bản thuyết trình — Công nghệ lập trình Web

Bản này sinh tự động từ phần **ghi chú** của `SLIDE_CONG_NGHE_LAP_TRINH_WEB.pptx` (`xuat_kich_ban.py`), nên luôn khớp với slide đang dùng. Trong lúc trình bày, mở **Presenter View** của PowerPoint là thấy đúng nội dung này.

**12 slide · 2213 từ · khoảng 17–21 phút** tùy tốc độ nói.

---

## Slide 1 — CMC Restaurant – Hệ thống quản lý nhà hàng, gọi món bằng QR và tư vấn…

[~40 giây]
Em chào thầy và các bạn. Nhóm em xin trình bày báo cáo môn Công nghệ lập trình
Web, đề tài CMC Restaurant — hệ thống quản lý nhà hàng, gọi món bằng mã QR và
tư vấn món ăn bằng AI.

Cách tiếp cận của nhóm là đi từ một sản phẩm thật thay vì trình bày lý thuyết
tách rời: phân tích toàn bộ công nghệ đã dùng để xây dựng hệ thống CMC Restaurant
— khoảng 97.400 dòng mã, đang chạy trên ba tên miền.

Nhờ vậy mọi khẳng định về công nghệ đều kiểm chứng được bằng mã nguồn cụ thể, và
mỗi lựa chọn kỹ thuật đều gắn với một ràng buộc có thật.

## Slide 2 — Bốn thế hệ kiến trúc ứng dụng web

[~1 phút 10]
Trước hết em xin đặt sản phẩm vào bối cảnh. Kiến trúc web đã đi qua bốn thế hệ,
mỗi thế hệ ra đời để giải một hạn chế của thế hệ trước.

Trang tĩnh chỉ trả về tệp có sẵn. Server-rendered sinh HTML động nhưng mỗi thao
tác phải tải lại cả trang. SPA cộng API giải quyết được điều đó — trình duyệt tự
dựng giao diện, dữ liệu lấy qua JSON.

Nhưng SPA vẫn có một hạn chế: máy chủ không chủ động gửi được dữ liệu. Thế hệ thứ
tư bổ sung một kênh đẩy.

Sản phẩm của nhóm thuộc thế hệ thứ tư, và lý do rất cụ thể: khi bếp đánh dấu một
món đã xong, màn hình của khách phải đổi ngay — mà khách thì không có lý do gì để
bấm tải lại trang.

## Slide 3 — Sáu tầng công nghệ của một ứng dụng web

[~1 phút]
Một ứng dụng web đầy đủ gồm sáu nhóm công nghệ, và báo cáo của nhóm đi lần lượt
từng nhóm.

Tầng giao diện: React 19 với TypeScript và Vite, tổ chức thành năm ứng dụng và
bảy thư viện dùng chung.

Tầng máy chủ: ASP.NET Core với Minimal API, 84 endpoint đi qua pipeline tám tầng
middleware.

Tầng dữ liệu: PostgreSQL 16 với Entity Framework Core, 24 bảng qua 22 migration.

Kênh thời gian thực dùng SignalR với bảy loại sự kiện.

Lớp bảo mật gồm HTTPS, JWT và capability token, bốn vai trò và bốn bộ quét tự động.

Cuối cùng là hạ tầng triển khai với Docker Compose và GitHub Actions.

Sáu tầng này chính là bố cục của phần trình bày tiếp theo.

## Slide 4 — Tầng giao diện: monorepo năm ứng dụng

[~1 phút 30]
Tầng giao diện là chỗ nhóm có một quyết định kiến trúc đáng nói.

Sản phẩm phục vụ bốn nhóm người dùng có hoàn cảnh khác hẳn nhau: khách dùng điện
thoại qua 4G, bếp dùng màn hình lớn đặt xa, quầy dùng máy tính thao tác nhanh,
quản trị làm việc với bảng nhiều cột.

Một giao diện duy nhất phục vụ cả bốn sẽ hoặc quá nặng cho khách, hoặc quá sơ
sài cho quản trị. Nên nhóm tách thành năm ứng dụng, mỗi ứng dụng một bundle
riêng. Lý do trực tiếp: khách dùng 4G, không có lý do bắt họ tải cả mã của trang
quản trị.

Cái giá phải trả là nguy cơ lặp mã giữa năm ứng dụng. Nhóm giải bằng monorepo với
bảy thư viện dùng chung.

Đáng chú ý nhất là shared-types: kiểu dữ liệu khai báo một lần, cả năm ứng dụng
cùng dùng. Nên khi hợp đồng API đổi, TypeScript báo lỗi biên dịch ở mọi nơi bị
ảnh hưởng — thay vì để lỗi lộ ra lúc chạy, ở đúng màn hình khách đang dùng.

## Slide 5 — Tầng máy chủ: pipeline xử lý một request

[~1 phút 40]
Middleware pipeline là khái niệm trung tâm của ASP.NET Core. Mỗi yêu cầu HTTP đi
qua một chuỗi thành phần; mỗi thành phần xử lý rồi chuyển tiếp cho thành phần kế
tiếp.

Đây là tám tầng thật trong dự án. Em xin nhấn hai điểm.

Thứ nhất, thứ tự là một phần của thiết kế, không phải ngẫu nhiên.
UseAuthentication phải đứng trước UseAuthorization, vì không thể quyết định một
người được làm gì khi chưa biết họ là ai.

Thứ hai, tầng được tô đậm là middleware nhóm tự viết. Nó bắt mọi ngoại lệ chưa
xử lý, ghi log đầy đủ, nhưng chỉ trả ra ngoài một mã tham chiếu tám ký tự. Người
vận hành tra được log bằng mã đó, còn người dùng — kể cả kẻ tấn công — không đọc
được cấu trúc nội bộ.

Về Dependency Injection, dự án đăng ký dịch vụ theo mô-đun nghiệp vụ thay vì liệt
kê phẳng. Nhờ vậy tệp khởi động chỉ 273 dòng dù hệ thống có 84 endpoint.

## Slide 6 — Thiết kế REST API

[~1 phút 30]
Về thiết kế API, dự án theo REST: mỗi đường dẫn đại diện một tài nguyên, động từ
HTTP cho biết thao tác.

Điểm đáng nói thứ nhất: dự án dùng Minimal API, không có tệp nào kế thừa
ControllerBase. Lý do là tầng máy chủ không kết xuất giao diện — nó chỉ trả JSON
cho năm ứng dụng React. Toàn bộ bộ máy View, Razor, HTML Helper của MVC vì vậy
không dùng đến.

Em xin nói rõ để tránh hiểu nhầm: MVC Controller không hề lỗi thời. Nếu ứng dụng
cần kết xuất HTML phía máy chủ hoặc tối ưu SEO thì MVC với Razor là lựa chọn tự
nhiên hơn.

Điểm thứ hai là khóa idempotency. Mạng di động chập chờn dẫn tới vấn đề thực tế:
khách bấm gửi món, mạng ngắt, ứng dụng gửi lại, và bếp nhận hai đơn giống nhau.
Mỗi yêu cầu mang một khóa duy nhất; máy chủ nhận lại đúng khóa đó thì trả kết quả
cũ thay vì tạo bản ghi mới. Đây là kỹ thuật bắt buộc với ứng dụng có liên quan
tới tiền.

## Slide 7 — Tầng dữ liệu và ba bất biến

[~1 phút 40]
Tầng dữ liệu dùng PostgreSQL 16 với Entity Framework Core: 24 bảng hình thành
qua 22 migration.

Lựa chọn PostgreSQL không phải mặc định mà xuất phát từ ba yêu cầu cụ thể — ba
bất biến bên phải.

Thứ nhất, một bàn chỉ được có một phiên đang mở. Nếu kiểm ở tầng ứng dụng thì
khi bốn người quét cùng lúc, bốn tiến trình cùng đọc thấy "chưa có phiên" rồi
cùng tạo. Chỉ unique index có điều kiện ở cơ sở dữ liệu mới chặn được.

Thứ hai, mã đơn không được trùng khi chạy nhiều máy chủ. Sinh mã phía ứng dụng
thì hai máy chủ có thể sinh cùng một số, nên dùng sequence của PostgreSQL.

Thứ ba, hai người sửa cùng một đơn không được ghi đè nhau. Dự án dùng cột hệ
thống xmin của PostgreSQL làm concurrency token: khi lưu, EF Core thêm điều kiện
kiểm tra phiên bản. Nếu dòng đã bị người khác sửa thì câu lệnh không khớp và hệ
thống trả lỗi thay vì làm mất dữ liệu.

Nguyên tắc chung rút ra: tầng ứng dụng có lỗi, tầng cơ sở dữ liệu thì không.
Ràng buộc nào quan trọng tới mức không được phép sai thì nên đặt ở nơi thấp nhất
có thể.

## Slide 8 — Giao tiếp thời gian thực

[~1 phút 30]
Mô hình HTTP truyền thống là client hỏi, server trả lời — máy chủ không chủ động
gửi được. Với bài toán này thì đó là hạn chế chí mạng: khi bếp đánh dấu món đã
xong, màn hình khách phải đổi ngay.

Có ba cơ chế. Polling thì đơn giản nhưng trễ và tốn băng thông. Server-Sent
Events nhẹ nhưng một chiều. WebSocket độ trễ thấp và hai chiều nhưng có thể bị
proxy chặn.

Dự án dùng SignalR, thư viện trừu tượng hóa cả ba. Điểm mạnh quyết định là cơ
chế lùi tự động: ưu tiên WebSocket, nếu bị chặn thì chuyển sang SSE, rồi
long-polling — mà mã ứng dụng không phải thay đổi gì. Điều này quan trọng vì
mạng wifi nhà hàng thường đi qua proxy và không biết trước proxy có cho WebSocket
đi qua hay không.

Hệ thống có bảy loại sự kiện, và chúng được gửi theo nhóm chứ không phát rộng —
sự kiện của bàn T07 chỉ tới thiết bị đang mở phiên bàn T07.

Điểm cần nhấn: trạng thái khách thấy và trạng thái bếp thao tác không phải hai
bản sao cần đồng bộ. Chúng là cùng một bản ghi, hiển thị theo hai vai trò.

## Slide 9 — Kiến trúc nhiều dịch vụ và truyền luồng

[~1 phút 30]
Khi hệ thống có nhiều dịch vụ, câu hỏi kỹ thuật là: khi nào thì tách?

Dự án giữ toàn bộ nghiệp vụ trong một tiến trình và chỉ tách đúng một thứ là dịch
vụ tư vấn. Tiêu chí không phải sự gọn gàng của sơ đồ mà là khác biệt về vòng đời:
khác ngôn ngữ, ảnh Docker 2,74 GB so với 200 MB, nhịp thay đổi khác. Gộp chung
thì mỗi lần sửa một endpoint thực đơn cũng phải đóng gói lại toàn bộ thư viện xử
lý ngôn ngữ.

Khi hai dịch vụ nói chuyện, nhóm đặt ba ràng buộc: trình duyệt không bao giờ gọi
thẳng dịch vụ thứ hai; mọi lời gọi nội bộ có token xác thực riêng; và dịch vụ đó
không có kết nối tới cơ sở dữ liệu.

Về truyền luồng: câu trả lời mất vài giây để sinh. Nếu chờ xong mới trả thì màn
hình trống, dễ tưởng treo. Server-Sent Events cho phép gửi từng phần ngay khi có.

Bên phải là ngân sách thời gian chờ, giảm dần từ ngoài vào trong. Nếu đặt ngược
lại — tầng trong chờ lâu hơn tầng ngoài — thì tầng ngoài bỏ cuộc trước, tài
nguyên bị chiếm vô ích và thông báo lỗi không phản ánh đúng nguyên nhân.

## Slide 10 — Bảo mật ứng dụng web

[~1 phút 30]
Bảo mật không nằm ở một cơ chế duy nhất mà ở nhiều lớp bổ trợ nhau.

Em xin nhấn hai điểm.

Thứ nhất là bài toán riêng của sản phẩm: khách tại bàn không có tài khoản, họ chỉ
quét mã QR. Vậy dựa vào đâu để cho phép họ thao tác? Cách ngây thơ là dùng chính
sessionId làm chứng chỉ — ai biết mã phiên thì được thao tác. Cách này sai, vì mã
phiên xuất hiện trên thanh địa chỉ.

Nhóm tách bạch hai khái niệm: mã định danh không phải chứng chỉ ủy quyền. Mã trong
QR được in và dán công khai tại bàn, nên nó chỉ dùng để đổi lấy một capability
token cấp riêng cho từng lần quét.

Thứ hai là nguyên tắc không tin client. Vai trò trong ứng dụng React chỉ dùng để
quyết định hiển thị gì cho gọn mắt, không phải cơ chế phân quyền. Ẩn một nút
không ngăn được ai đó gọi thẳng API bằng công cụ khác.

Về quét tự động: CodeQL đã báo một lỗ hổng thật tại ba vị trí mà không thành viên
nào nhận ra khi đọc lại mã. Bài học: con người rà soát theo ý định, còn công cụ
rà soát theo luồng dữ liệu.

## Slide 11 — CI/CD và triển khai

[~1 phút 30]
Cuối cùng là triển khai. Em xin phân biệt rõ hai khái niệm hay bị dùng lẫn.

CI — tích hợp liên tục — là mỗi thay đổi mã nguồn được tự động kiểm tra ngay khi
đưa lên: biên dịch được không, test có đạt không, cấu hình có hợp lệ không. Mục
đích là phát hiện lỗi trong vài phút thay vì vài ngày.

CD — triển khai liên tục — là sau khi CI đạt thì phiên bản mới tự động lên môi
trường chạy. Điều này loại bỏ lớp lỗi do triển khai thủ công: quên một bước, chép
nhầm tệp cấu hình, hoặc mỗi lần làm một kiểu.

Dự án có chín workflow và 2.468 lần chạy.

Điểm em muốn nhấn: một pipeline CI chỉ có giá trị khi nó ngăn được mã lỗi vào
nhánh chính. Nếu nó chỉ báo đỏ mà vẫn merge được thì nó là bảng thông báo, không
phải cổng kiểm soát. Nên năm job được khai báo là status check bắt buộc, và danh
sách ngoại lệ để rỗng — kể cả chủ repository cũng không bỏ qua được.

Nếu kiểm tra sức khỏe sau triển khai thất bại, hệ thống tự động quay về phiên bản
trước, không chờ người bấm.

## Slide 12 — Tổng kết

[~1 phút]
Ba bài học nhóm rút ra sau khi xây dựng hệ thống này.

Thứ nhất, mỗi lựa chọn công nghệ nên xuất phát từ một ràng buộc có thật. Nhóm
tách năm ứng dụng vì khách dùng 4G; chọn PostgreSQL vì cần đúng ba tính năng cụ
thể; chọn SignalR vì mạng nhà hàng có thể chặn WebSocket. Ngược lại, nhóm không
dùng Kubernetes, không dùng cơ sở dữ liệu vector chuyên dụng — vì không có ràng
buộc nào đòi hỏi chúng.

Thứ hai, tầng thấp nhất có thể là nơi tốt nhất để đặt ràng buộc quan trọng. Tầng
ứng dụng có lỗi; tầng cơ sở dữ liệu thì không.

Thứ ba, không tin dữ liệu từ phía client. Giao diện có thể bị sửa bằng công cụ
phát triển của trình duyệt, nên mọi kiểm tra quan trọng phải lặp lại ở máy chủ.

Phần trình bày của nhóm em đến đây là hết. Em xin cảm ơn và sẵn sàng nhận câu hỏi ạ.
