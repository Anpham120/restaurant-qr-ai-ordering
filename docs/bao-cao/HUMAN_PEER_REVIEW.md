# Quy trình và bằng chứng human peer review

Tài liệu này quy định cách nhóm thực hiện peer review cho pull request hoàn thiện báo cáo học phần.
Mục tiêu là tạo bằng chứng rằng thay đổi đã được thành viên khác đọc và phản hồi trên GitHub, thay
vì chỉ dựa vào kiểm tra tự động hoặc nhận xét do công cụ AI tạo ra.

## Bài học từ lần thực hiện đầu tiên

[Pull request #424](https://github.com/Anpham120/restaurant-qr-ai-ordering/pull/424) ghi nhận bốn
review `APPROVED` từ `Tanh2k8-123`, `buidaoducanh1210`, `quanghieu1605` và
`totototototoads`. Tuy nhiên, workflow auto-merge đã hợp nhất PR lúc 20:48 ngày 04/08/2026
(UTC+7), trước khi các review được gửi trong khoảng 21:27–21:31. Các review này chứng minh thành
viên đã để lại nhận xét chính thức nhưng **không chứng minh thay đổi được review trước khi merge**.

Nhóm vì vậy thực hiện một pull request bổ sung với auto-merge bị tắt. PR chỉ được hợp nhất sau khi:

1. tác giả là `Anpham120` và không tự phê duyệt;
2. bốn thành viên còn lại gửi review có nội dung cụ thể;
3. các review có trạng thái `APPROVED` trước thời điểm merge;
4. các status check bắt buộc hoàn thành.

Việc công khai cả lần thực hiện chưa đúng thứ tự và biện pháp sửa là một phần của bằng chứng quy
trình: nhóm không dùng review sau merge để thay cho cổng kiểm soát trước merge.

## Kết quả thực hiện bổ sung

[Pull request #426](https://github.com/Anpham120/restaurant-qr-ai-ordering/pull/426) là lần thực
hiện lại đúng thứ tự. Tác giả `Anpham120` mở PR ở trạng thái Draft và không tự phê duyệt. Bốn
reviewer còn lại gửi review `APPROVED` có nội dung cụ thể trong khoảng 21:39:23–21:40:17 ngày
04/08/2026 (UTC+7):

- `Tanh2k8-123`: kiểm tra cách phân biệt review sau merge ở PR #424 với review-before-merge;
- `buidaoducanh1210`: kiểm tra nguyên tắc tác giả không tự phê duyệt và bốn thành viên còn lại
  review độc lập;
- `quanghieu1605`: đối chiếu thứ tự thời gian và yêu cầu nhận xét phải xuất hiện trước hợp nhất;
- `totototototoads`: kiểm tra sự phân biệt giữa review tự động, review sau merge và review của
  thành viên trước merge.

Sau khi toàn bộ CI và kiểm tra an ninh đạt, PR được chuyển sang Ready rồi hợp nhất lúc 22:28:20
cùng ngày, tức **sau cả bốn phê duyệt**. Merge commit là
[`e419d1b`](https://github.com/Anpham120/restaurant-qr-ai-ordering/commit/e419d1b29e4290816d3865944dbc01dfdc7ae2a7).
PR #426 vì vậy là bằng chứng human peer review trước merge; PR #424 chỉ được giữ như bài học về
một lần thực hiện sai thứ tự.

## Nguyên tắc

1. Tác giả pull request không tự phê duyệt thay đổi của mình.
2. Mỗi reviewer đăng nhập bằng tài khoản GitHub cá nhân và tự đọc phần được phân công.
3. Review phải có nhận xét kỹ thuật hoặc nhận xét nội dung cụ thể. Chỉ bấm `Approve` mà không chỉ ra
   nội dung đã kiểm tra không được coi là bằng chứng mạnh.
4. Nếu phát hiện vấn đề, reviewer dùng `Request changes`; tác giả sửa và yêu cầu review lại.
5. Pull request chỉ được merge sau khi các nhận xét bắt buộc đã được xử lý và có đủ phê duyệt theo
   quy tắc của nhóm.

## Phân công review

| Tài khoản | Vai trò trong đợt review | Nội dung cần kiểm tra |
|---|---|---|
| `Anpham120` | Tác giả PR, tổng hợp và sửa | Phạm vi thay đổi, tính nhất quán toàn báo cáo, phản hồi các nhận xét; không tự approve |
| `Tanh2k8-123` | Reviewer trải nghiệm khách | Luồng quét QR, nhận diện bàn/phiên, chọn món, gọi nhiều lượt và theo dõi trạng thái đơn |
| `buidaoducanh1210` | Reviewer backend phiên và thanh toán | Xác thực, capability token, vòng đời phiên bàn, hóa đơn và đóng phiên |
| `quanghieu1605` | Reviewer dữ liệu và realtime | Đơn hàng, lịch sử trạng thái, SignalR, luồng dữ liệu giữa khách và bếp |
| `totototototoads` | Reviewer vận hành nhà hàng | Bảng bếp, quầy thu ngân, quản trị, phân quyền và tính đầy đủ của bài toán vận hành |

## Checklist chung cho reviewer

- [ ] Đọc phần Đặt vấn đề, Bài toán cần giải quyết và Product Vision.
- [ ] Kiểm tra QR gọi món và theo dõi trạng thái đơn tại bàn là trục chính.
- [ ] Kiểm tra báo cáo không bỏ sót bếp, phục vụ, quầy thu ngân, thanh toán và quản trị.
- [ ] Kiểm tra AI chỉ là lớp hỗ trợ tư vấn, không tự sửa giỏ hàng hoặc tự đặt món.
- [ ] Kiểm tra nội dung thuộc mảng phụ trách khớp với mã nguồn hoặc hiện vật GitHub.
- [ ] Ghi ít nhất một nhận xét cụ thể trên pull request hoặc xác nhận rõ các tệp/phần đã kiểm tra.
- [ ] Chọn `Approve` khi đạt, hoặc `Request changes` nếu còn vấn đề phải sửa.

## Mẫu nhận xét

Reviewer cần sửa nội dung trong ngoặc vuông bằng kết quả kiểm tra thực tế, không sao chép nguyên mẫu:

> Tôi đã kiểm tra [tệp/mục] theo mảng [mảng phụ trách]. Luồng [nội dung đã kiểm tra] được mô tả
> nhất quán với [mã nguồn, kiểm thử hoặc hiện vật đối chiếu]. [Không phát hiện vấn đề bắt buộc sửa /
> Tôi yêu cầu sửa nội dung ... vì ...].

## Cách thực hiện bằng GitHub CLI

Mỗi thành viên tự đăng nhập hoặc chuyển sang tài khoản của mình, đọc diff và gửi review:

```powershell
gh auth switch --hostname github.com --user <tai-khoan-cua-minh>
gh pr diff <so-pr> --repo Anpham120/restaurant-qr-ai-ordering
gh pr review <so-pr> --repo Anpham120/restaurant-qr-ai-ordering --comment --body "<nhan-xet-cu-the>"
gh pr review <so-pr> --repo Anpham120/restaurant-qr-ai-ordering --approve --body "<ket-luan-sau-khi-da-doc>"
```

Nếu có lỗi bắt buộc sửa, thay lệnh `--approve` bằng:

```powershell
gh pr review <so-pr> --repo Anpham120/restaurant-qr-ai-ordering --request-changes --body "<van-de-va-cach-sua>"
```

## Bằng chứng cần lưu sau khi hoàn tất

- URL của pull request.
- Danh sách reviewer và trạng thái `APPROVED` hoặc `CHANGES_REQUESTED`.
- Các nhận xét cụ thể và phản hồi của tác giả.
- Commit sửa sau review, nếu có.
- Ảnh chụp mục `Reviews` hoặc kết quả truy vấn:

```powershell
gh pr view <so-pr> --repo Anpham120/restaurant-qr-ai-ordering `
  --json author,reviewRequests,reviews,commits,url
```

Điều kiện trên đã được đáp ứng tại PR #426. Báo cáo vì vậy ghi nhận “đã có bằng chứng human peer
review trước merge”, đồng thời nêu rõ bằng chứng này được bổ sung ở giai đoạn cuối và không được
dùng để suy diễn rằng toàn bộ lịch sử 377 pull request đều đã qua review của thành viên.
