# -*- coding: utf-8 -*-
"""Lớp Ý ĐỊNH — khách đang LÀM GÌ, trước khi hỏi khách MUỐN MÓN NÀO.

Vì sao lớp này tồn tại
======================
Ba lỗi tìm ra khi dùng thật trên production, và không lỗi nào bị 103 lượt golden + 140 ca + 87 lượt
phiên bắt được:

    "xin chào"                  -> hệ thống đổ ra một danh sách rượu và cà phê
    "tư vấn thêm đi"            -> y nguyên 6 món vừa nêu ở lượt trước
    "tôi không còn dị ứng nữa"  -> vẫn lọc theo dị nguyên cũ

Cả ba có chung một hình dạng: **hệ thống không hỏi "khách đang làm gì", nó chỉ hỏi "câu này có nhãn
lọc nào".** Câu nào không sinh nhãn thì rơi xuống nhánh cuối và nhận một đoạn tri thức gần nhất — kể
cả lời chào.

Vì sao KHÔNG chỉ gỡ chặn `llm_understand`
=========================================
`llm_understand` đã là một lớp mô hình đọc câu hỏi, nhưng nó bị chặn bởi 14 tín hiệu `already_understood`
và hợp đồng của nó chỉ cho **THÊM** nhãn, không cho xóa. Mỗi tín hiệu trong 14 cái đó được thêm sau
một ca đỏ THẬT, ghi ngay trong chú thích của nó:

    "Món đắt nhất menu là món nào?"  mã tất định đúng -> gọi mô hình -> TỤT
    "Nhãn 'ít calo' dựa trên gì?"    mô hình trả `prefer:health:low_calorie` -> đẩy sang nhánh LỌC

Kết luận đúng từ những ca đó không phải "mô hình vô dụng", mà là **mô hình làm hỏng khi được giao
việc gán nhãn lọc**. Nên lớp này giao cho nó việc KHÁC, và cấm đúng việc kia:

    lớp này          quyết định khách đang LÀM GÌ, và ràng buộc nào cần BỎ
    lớp này KHÔNG    gán nhãn lọc, không chọn món, không viết câu trả lời

Ba việc mô hình mạnh mà mã tất định yếu, và cả ba nằm gọn trong phạm vi trên: **nhận ý định, hiểu
tham chiếu, hiểu phủ định** ("không còn… nữa", "bỏ cái đó đi").

Mô hình KHÔNG được là điều kiện để chạy
=======================================
Có đường tất định cho mọi ý định, và nó chạy TRƯỚC. Mô hình chỉ được hỏi khi đường tất định không
chắc. Ba lý do, và lý do thứ ba mới là lý do thật:

    1. dịch vụ phải trả lời được khi mô hình hỏng — nguyên tắc có từ bước 4
    2. mỗi lần gọi tốn ~8,6 giây, còn "xin chào" thì không đáng chờ 8 giây
    3. **cụm chào hỏi tiếng Việt là tập ĐÓNG và nhỏ.** Dùng mô hình cho một việc mà một danh sách
       20 cụm giải quyết trọn là chọn công cụ sai, và làm phép đo phụ thuộc một thứ không tất định.

Nói cách khác: mô hình dùng cho phần ĐUÔI DÀI, không dùng cho phần đã biết.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from understand import fold

# ------------------------------------------------------------------------------------------------
# Ý định. Danh sách ĐÓNG, và đóng có chủ ý: mỗi ý định phải có một nhánh trả lời riêng, nên thêm một
# ý định mà không thêm nhánh là tạo ra một trạng thái không ai xử lý.
# ------------------------------------------------------------------------------------------------
CHAO_HOI = "chao_hoi"          # "xin chào", "hello", "chào bạn"
CAM_ON = "cam_on"              # "cảm ơn", "ok thanks"
XIN_THEM = "xin_them"          # "tư vấn thêm đi", "còn gì nữa không", "món khác đi"
XOA_RANG_BUOC = "xoa_rang_buoc"  # "tôi hết dị ứng rồi", "bỏ điều kiện đó đi"
HOI_MON = "hoi_mon"            # mọi câu về thực đơn — đường mặc định, mã tất định lo
NGOAI_PHAM_VI = "ngoai_pham_vi"  # tán gẫu ngoài nhà hàng


@dataclass
class YDinh:
    """Kết quả đọc ý định. `bo_rang_buoc` là thứ `llm_understand` KHÔNG diễn đạt được."""

    ten: str = HOI_MON
    # Nhóm ràng buộc khách muốn BỎ: "allergen" (dị nguyên), "budget" (ngân sách), "all" (tất cả).
    bo_rang_buoc: list[str] = field(default_factory=list)
    nguon: str = "tat_dinh"  # "tat_dinh" | "mo_hinh" | "mo_hinh_that_bai"
    cum_khop: str = ""

    @property
    def can_mo_hinh(self) -> bool:
        return self.ten == HOI_MON and self.nguon == "tat_dinh" and not self.cum_khop


# ------------------------------------------------------------------------------------------------
# Đường tất định.
#
# Khớp trên chuỗi ĐÃ RÚT DẤU và có đệm khoảng trắng hai đầu, giống `understand.VOCAB` — vì đúng lớp
# lỗi đụng chữ đã giết bản cũ bảy lần lại xuất hiện ở đây: cổng `thuoc_mien()` cho "xin chào" đi qua
# vì `chao` là từ đầu của món **"Cháo lòng Sài Gòn"**.
# ------------------------------------------------------------------------------------------------

# Chào hỏi. Tập đóng, nhỏ, và không cụm nào nằm trong tên món nào (đã kiểm bằng test).
_CHAO = (
    "xin chao", "chao ban", "chao shop", "chao em", "chao anh", "chao chi",
    "hello", "helo", "hi", "hey", "alo", "a lo",
    "chao buoi sang", "chao buoi trua", "chao buoi toi",
)

# Cảm ơn / kết thúc. Không phải câu hỏi, nên trả lời bằng một danh sách món là sai loại.
_CAM_ON = (
    "cam on", "cam on ban", "cam on nhe", "thanks", "thank you", "tks", "ok cam on",
    "minh cam on", "toi cam on",
)

# XIN THÊM — nhóm mà mã tất định đang thiếu, và là lỗi số 1 người dùng nêu.
#
# `understand.VOCAB` đã có `mon khac|cai khac|mon nao khac|thu khac|mon gi khac` -> cờ `similar`.
# Nhưng KHÔNG có "thêm", "còn gì nữa", "xem tiếp" — nên "tư vấn thêm đi" rơi vào nhánh lọc bình
# thường và trả lại **y nguyên** danh sách cũ. Đo được trên production: lượt 2 và lượt 4 của một hội
# thoại bốn lượt đều lặp lại đúng 6 món của lượt 1.
# `them mon` nằm trong danh sách này, và nó là cụm đã dạy tôi cơ chế ăn chữ sai chỗ nào:
#
#     "cho mình thêm món chay"   -> `them mon` khớp, ĂN -> còn "cho minh ___ ___ chay"
#                                -> `chay` một mình KHÔNG phải cụm từ vựng (nó được tách thành
#                                   `an chay` / `mon chay`) -> mất sạch ràng buộc chay
#
# Tôi đã thử hai cách sửa sai trước khi tìm ra cách đúng:
#
#     bỏ cụm `them mon`      -> "cho mình thêm món chay NỮA" không còn nhận ra là xin thêm,
#                               và nó trả lại y nguyên 6 món chay vừa xem
#     bỏ Ý ĐỊNH khi va chạm  -> cùng hậu quả, chỉ đổi chỗ
#
# Cách đúng: **giữ ý định, chỉ không ăn chữ.** Ăn chữ có đúng một mục đích — chặn chữ của chính cụm
# ý định sinh ra nhãn sai (`bo` của "bỏ hết điều kiện" là `ingredient:beef`). Khi việc ăn sẽ phá một
# cụm NẰM NGOÀI, không ăn là đủ; bỏ ý định là mất hẳn một cơ chế.
_XIN_THEM = (
    "them di", "tu van them", "tu van them di", "goi y them", "them nua", "them mon",
    "con gi nua", "con gi nua khong", "con mon nao khac", "con gi khac",
    "xem them", "xem tiep", "cho xem them", "nua di", "tiep di",
    "con nua khong", "the con gi", "gi nua",
    # "món mới" là XIN THÊM chứ không phải một ràng buộc: thực đơn không có nhãn "mới", nên câu này
    # chỉ có một nghĩa dùng được — món khác những món vừa nêu. Không có cụm nào ở trên bắt được nó,
    # và đo được là nó trả lại y nguyên 6 món của lượt trước.
    "mon moi", "mon nao moi", "cai moi", "do moi",
    # "đổi chủ đề khác đi" — khách nói rõ là muốn thứ khác, nhưng không cụm nào ở trên bắt được vì
    # câu không nhắc chữ "món". Đo được: nó trả lại y nguyên 6 món của lượt trước.
    "doi chu de", "chu de khac", "chuyen chu de", "noi chuyen khac", "hoi cai khac",
    # Cách khách hỏi tiếp khi đang xem một danh sách. Đo được trong hội thoại hỏi liên tục:
    #
    #   "hết chưa"              -> lặp Y NGUYÊN 6 món vừa nêu
    #   "vậy còn món gì không"  -> "Mình chưa có dữ liệu về việc này ạ."
    #
    # Câu thứ hai còn tệ hơn: nó rơi vào nhánh chính sách "còn hàng không" vì có cả "còn" lẫn
    # "không", nên khách xin thêm món mà nhận câu từ chối về tồn kho.
    "het chua", "con mon gi khong", "con mon gi nua", "con mon nao nua",
    "con gi de goi", "the con gi nua", "con bao nhieu mon",
)

# XÓA RÀNG BUỘC — nhóm mà hợp đồng của `llm_understand` KHÔNG diễn đạt được.
#
# `session.py` hợp nhất dị nguyên bằng phép HỢP và không bao giờ bỏ, có chủ ý: khách khai dị ứng ở
# lượt 1 thì lượt 5 vẫn phải được bảo vệ. Đó là bất biến an toàn quan trọng nhất của bộ nhớ phiên.
#
# Nhưng "không bao giờ bỏ" khác "không có đường bỏ". Khách nói rõ mình hết dị ứng — hoặc lời khai
# lúc nãy là của người bạn vừa về — thì phải có đường. Cách giữ cả hai:
#
#     xóa chỉ khi khách nói RÕ RÀNG   (cụm dưới đây, không suy diễn)
#     và câu trả lời NÓI RA điều vừa bỏ (xem `answer`), để khách sửa được nếu hệ thống hiểu sai
#
# Đây là chỗ khác biệt so với "im lặng bỏ ràng buộc": một hàng rào an toàn được hạ xuống thì khách
# phải THẤY nó được hạ.
_XOA_DI_NGUYEN = (
    "khong con di ung", "het di ung", "khong di ung nua", "khong bi di ung nua",
    "minh het di ung", "toi het di ung", "khong con di ung nua", "hoi nay het di ung",
    "bo di ung", "bo phan di ung", "khong can tranh nua", "an duoc het",
    "an duoc tat ca", "gio an duoc roi",
    # KHÁCH KHẲNG ĐỊNH MÌNH ĂN ĐƯỢC. Đo được trên bản chạy thật, và nó là NGÕ CỤT:
    #
    #     "Con tôi không ăn được tôm hãy tư vấn món hải sản khác"  -> chặn cả 26 món hải sản
    #     "tôi ăn được hải sản hãy tư vấn hải sản cho tôi"         -> "chưa tìm được món nào"
    #
    # Lượt hai vừa xin hải sản vừa nói rõ mình ăn được, mà bộ nhớ vẫn giữ `allergen:seafood` — nên
    # giao của "phải là hải sản" và "không được là hải sản" ra rỗng, và khách không có cách nào gỡ.
    #
    # Đây là dạng khẳng định NGƯỢC với `_XOA_DI_NGUYEN` cũ: cụm cũ đều là "hết/không còn dị ứng",
    # tức nói về việc dị ứng biến mất. Khách thật nói theo hướng dương — "tôi ăn được X".
    "an duoc hai san", "an duoc do bien", "toi an duoc", "minh an duoc", "an duoc binh thuong",
    "khong di ung gi", "khong di ung", "minh khong di ung", "toi khong di ung",
)
_XOA_TAT_CA = (
    "bo het dieu kien", "bo dieu kien", "bo rang buoc", "bo het rang buoc",
    "lam lai tu dau", "quen het di", "bo qua nhung gi minh noi",
)

# NỚI BỘ LỌC — khác `_XOA_TAT_CA` ở chỗ nó KHÔNG đụng dị nguyên.
#
# Khi không còn món nào thỏa, hệ thống hỏi: *"Bạn muốn mình bỏ bớt một điều kiện để có thêm lựa
# chọn không?"* Câu trả lời "có" phải nới **điều kiện lọc** (số người, độ cay, giá, chế độ ăn) —
# tuyệt đối KHÔNG nới dị nguyên. Khách đồng ý xem thêm lựa chọn không có nghĩa là họ hết dị ứng.
#
# Tách thành nhóm riêng chứ không dùng lại `all` chính vì điều đó: `all` bỏ cả dị nguyên, và dùng nó
# ở đây là hạ chốt an toàn dựa trên một câu "ừ".
_NOI_BO_LOC = (
    "bo bot dieu kien", "bo bot mot dieu kien", "bo bot rang buoc", "bo bot",
    "noi dieu kien", "noi bot dieu kien", "bo dieu kien do",
)

# Câu ĐỒNG Ý với đề nghị hệ thống vừa đưa ra.
#
# Vì sao cần: hệ thống hỏi một câu có/không rồi KHÔNG hiểu câu trả lời. Đo được trên production:
#
#     hệ thống: "Bạn muốn mình bỏ bớt một điều kiện để có thêm lựa chọn không?"
#     khách   : "bỏ và tư vấn thêm đi"
#     hệ thống: "Mình đã nêu hết 1 món thỏa điều bạn cần rồi ạ. Bạn muốn mình bỏ bớt…"  (lặp)
#
# Tệ hơn: chữ "bỏ" rút dấu thành `bo`, và `bo` là nhãn `ingredient:beef` — nên khách xin BỎ điều
# kiện lại bị THÊM ràng buộc thịt bò. Vụ đụng chữ thứ chín, lần thứ hai ở cùng một chữ.
#
# Vá thêm cụm là đánh chuột: mỗi cách nói "đồng ý" trong tiếng Việt là một cụm mới. Cách đúng là
# nhận diện theo NGỮ CẢNH — chỉ khi hệ thống VỪA hỏi một câu có/không thì mới đọc câu ngắn của khách
# là lời đồng ý. Xem `session.merge_into_request`.
_DONG_Y = (
    "co", "u", "um", "uh", "ok", "oke", "okie", "duoc", "dong y", "vang", "da",
    "co di", "u di", "lam di", "di", "the di", "vay di", "bo di", "bo",
)


def la_dong_y(cau: str) -> bool:
    """Câu này có phải lời ĐỒNG Ý với đề nghị vừa rồi không.

    CHỈ dùng khi hệ thống vừa hỏi một câu có/không — xem `SessionState.cho_doi`. Ngoài ngữ cảnh đó,
    "được" hay "đi" là chữ bình thường và đọc chúng thành lời đồng ý là đọc bừa.

    Đòi câu NGẮN (≤ 6 từ): "bỏ và tư vấn thêm đi" là đồng ý; "bỏ qua món bò, cho mình món gà" thì
    không — nó là một yêu cầu mới, và người viết câu dài là người đang nói điều cụ thể.
    """
    f = fold(cau)
    tu = f.split()
    if not tu or len(tu) > 6:
        return False
    return any(t in _DONG_Y for t in tu)

# Ngoài phạm vi — bắt tay với `understand`'s `off_topic`, không thay nó. Ở đây chỉ nhận nhóm TÁN GẪU
# về cảm xúc, thứ `off_topic` (thời tiết, tin tức, tỷ giá) không phủ.
_TAN_GAU = (
    "buon qua", "vui qua", "met qua", "chan qua", "toi buon", "minh buon",
    "hom nay the nao", "ban khoe khong", "ban la ai", "ban ten gi",
)

# "tôi hết dị ứng" phải thắng "dị ứng" của `understand`. Cụm dài khớp trước — cùng cơ chế với VOCAB.
_MOI_NHOM = (
    (_XOA_DI_NGUYEN, XOA_RANG_BUOC, "allergen"),
    (_XOA_TAT_CA, XOA_RANG_BUOC, "all"),
    (_NOI_BO_LOC, XOA_RANG_BUOC, "loc"),
    (_CHAO, CHAO_HOI, ""),
    (_CAM_ON, CAM_ON, ""),
    (_XIN_THEM, XIN_THEM, ""),
    (_TAN_GAU, NGOAI_PHAM_VI, ""),
)


# HỎI "ăn được gì" KHÁC KHẲNG ĐỊNH "tôi ăn được".
#
# Lỗi an toàn nặng nhất tìm được trong đợt rà độ phủ bộ đánh giá, và nó tồn tại im lặng:
#
#     lượt 1  "Con mình dị ứng hải sản"       ->  avoid = [allergen:seafood]        đúng
#     lượt 2  "Bé nhà mình ăn được món gì?"   ->  avoid = []                        XÓA MẤT
#     lượt 3  "Cho mình món khai vị"          ->  Gỏi cuốn tôm thịt, Súp măng cua,
#                                                 Nem rán Hà Nội, Bánh xèo miền Tây
#
# Bốn món hải sản mời cho phụ huynh vừa khai con dị ứng hải sản. Nguyên nhân: cụm `minh an duoc`
# trong `_XOA_DI_NGUYEN` khớp đoạn "bé nhà **mình ăn được** món gì".
#
# Cụm đó được thêm cho câu KHẲNG ĐỊNH ("tôi ăn được hải sản, tư vấn hải sản đi") — một bản sửa
# đúng. Nhưng cùng chuỗi chữ ấy nằm trong câu HỎI, và hai loại câu ngược nhau hoàn toàn: một bên
# nói ràng buộc không còn, một bên hỏi ràng buộc cho phép ăn gì.
#
# Hàng rào đặt ở `_khop` chứ không sửa từng cụm: mọi cụm xóa dị nguyên đều dính lớp lỗi này, và
# vá từng cụm là bỏ sót cụm sẽ thêm sau.
_LA_CAU_HOI_AN_DUOC = (
    "an duoc gi", "an duoc mon gi", "an duoc nhung gi", "an duoc mon nao",
    "an duoc nhung mon nao", "an duoc bao nhieu", "an duoc khong", "an duoc mon gi khong",
)


# PHỦ ĐỊNH đứng trước "ăn được" đảo ngược hoàn toàn nghĩa của câu.
#
# Lỗi an toàn nặng nhất tìm được khi rà 20 cách khai dị ứng:
#
#     "Mình KHÔNG ăn được hải sản"       ->  ý định `xoa_rang_buoc`, cụm khớp `an duoc hai san`
#     "Cả nhà KHÔNG AI ăn được hải sản"  ->  như trên
#
# Khách nói mình **không** ăn được, hệ thống đọc thành **có** ăn được và **gỡ** ràng buộc dị
# nguyên. Đây không phải bỏ sót — bỏ sót thì ràng buộc không được ghi; đây là **đảo nghĩa**, tức
# ràng buộc đang có cũng bị xóa.
#
# Và *"Mình không ăn được hải sản"* là một trong những cách khai dị ứng phổ biến nhất.
#
# Phủ định phải là ĐÚNG một hoặc hai từ liền ngay trước, không phải "ở đâu đó phía trước".
#
# Bản đầu của hàm này dùng cửa sổ 20 ký tự, và nó bắt nhầm ngay:
#
#     "bạn nói KHÔNG ĐÚNG, mình ăn được hải sản"
#         `khong` cách `an duoc hai san` 16 ký tự -> lọt cửa sổ -> chặn nhầm
#
# Câu đó là câu KHẲNG ĐỊNH mình ăn được, và chữ "không" thuộc mệnh đề khác. Chặn nó nghĩa là khách
# nói rõ mình hết kiêng mà hệ thống vẫn giữ ràng buộc — hướng an toàn, nhưng vẫn là hiểu sai.
#
# Đếm TỪ thay vì đếm ký tự thì ranh giới mệnh đề tự hiện ra: phủ định của một cụm động từ đứng
# ngay cạnh nó, không cách hai từ.
_PHU_DINH_TRUOC = ("khong", "chang", "chua", "chang the", "khong the", "khong ai", "chua bao gio")


def _co_phu_dinh_ngay_truoc(folded_padded: str, cum: str) -> bool:
    """Có từ phủ định đứng NGAY trước cụm `cum` không — xét đúng hai từ liền kề."""
    vt = folded_padded.find(f" {cum} ")
    if vt < 0:
        return False
    tu = folded_padded[:vt].split()
    if not tu:
        return False
    # "không ăn được" (1 từ) và "không ai ăn được" (2 từ) đều phải bắt.
    return tu[-1] in _PHU_DINH_TRUOC or " ".join(tu[-2:]) in _PHU_DINH_TRUOC


def _la_cau_hoi_chu_khong_phai_khang_dinh(folded_padded: str) -> bool:
    """Câu chứa "ăn được" nhưng đang HỎI, không phải khai mình hết kiêng."""
    return any(f" {c} " in folded_padded for c in _LA_CAU_HOI_AN_DUOC)


def _khop(folded_padded: str, cum: tuple[str, ...]) -> str:
    """Cụm DÀI NHẤT khớp, hoặc chuỗi rỗng.

    Dài nhất chứ không phải đầu tiên: "khong con di ung nua" chứa "khong con di ung", và chọn nhầm
    cụm ngắn không sai ở đây nhưng sẽ sai khi hai nhóm khác nhau chồng chữ. Cùng nguyên tắc với
    `VOCAB_ORDER`.
    """
    khop = [c for c in cum if f" {c} " in folded_padded]
    return max(khop, key=len) if khop else ""


def doc_y_dinh_tat_dinh(cau: str) -> YDinh:
    """Đọc ý định từ câu thô. Trả `HOI_MON` khi không chắc — mặc định an toàn nhất."""
    return doc_y_dinh_tu_chuoi_dem(f" {fold(cau)} ")


def doc_y_dinh_tu_chuoi_dem(folded_padded: str) -> YDinh:
    """Như trên, nhưng nhận chuỗi ĐÃ rút dấu và ĐÃ đệm khoảng trắng hai đầu.

    Tồn tại vì `understand()` cần khớp ý định TRƯỚC vòng khớp từ vựng rồi **ăn hết đoạn đã khớp** —
    và nó đang giữ sẵn chuỗi đệm đó.

    Vì sao phải ăn chữ: "bỏ hết điều kiện đi" rút dấu thành `bo het dieu kien di`, và `bo` là nhãn
    `ingredient:beef` ("bò"). Không ăn thì khách xin BỎ ràng buộc lại nhận thêm một ràng buộc **thịt
    bò**. Đây là vụ đụng chữ thứ chín của dự án, và nó xuất hiện ngay trong cơ chế vừa dựng để sửa
    một vụ khác.
    """
    f = folded_padded
    # Câu HỎI "ăn được gì" không bao giờ là câu xóa dị nguyên — xem `_LA_CAU_HOI_AN_DUOC`.
    hoi_an_duoc = _la_cau_hoi_chu_khong_phai_khang_dinh(f)
    tot_nhat: tuple[int, str, str, str] = (0, "", HOI_MON, "")
    for cum, ten, nhom in _MOI_NHOM:
        if hoi_an_duoc and nhom == "allergen":
            continue
        c = _khop(f, cum)
        # PHỦ ĐỊNH đứng trước đảo ngược nghĩa: "KHÔNG ăn được hải sản" là câu KHAI dị ứng, không
        # phải câu gỡ. Chỉ áp cho nhóm dị nguyên — nhóm nới bộ lọc không có cụm nào dạng khẳng
        # định-về-khả-năng-ăn nên không cần, và áp bừa sẽ chặn cả "bỏ hết điều kiện" hợp lệ.
        if c and nhom == "allergen" and _co_phu_dinh_ngay_truoc(f, c):
            continue
        if c and len(c) > tot_nhat[0]:
            tot_nhat = (len(c), c, ten, nhom)

    _, cum_khop, ten, nhom = tot_nhat
    if not cum_khop:
        return YDinh(ten=HOI_MON, nguon="tat_dinh")
    return YDinh(
        ten=ten,
        bo_rang_buoc=[nhom] if nhom else [],
        nguon="tat_dinh",
        cum_khop=cum_khop,
    )


# ------------------------------------------------------------------------------------------------
# ĐUÔI DÀI — chỗ duy nhất trong lớp này dùng mô hình.
#
# Danh sách cụm ở trên phủ phần ĐÃ BIẾT: chào hỏi, cảm ơn, xin thêm, xóa ràng buộc. Nó không phủ
# được phần đuôi, và đuôi thì vô hạn:
#
#     "nhà hàng đông không bạn"   -> hiện nhận về một đoạn tri thức về phạm vi trợ lý
#     "quán mình mở lâu chưa"     -> câu xã giao, không phải câu hỏi món
#     "bạn tư vấn có chuẩn không" -> nói về chính trợ lý
#
# Mô hình chỉ được hỏi khi danh sách cụm KHÔNG nhận ra và mã tất định cũng không rút được ràng buộc
# nào — tức đúng những câu mà hệ thống sắp trả lời bằng một đoạn tri thức gần nhất. Ba hệ quả:
#
#     độ trễ    câu đã hiểu không tốn thêm giây nào; chỉ phần đuôi mới chờ
#     an toàn   mô hình KHÔNG được gán nhãn lọc ở đây, nên nó không lặp lại được lớp lỗi cũ
#     thoái hóa mô hình hỏng -> trả `HOI_MON` -> hệ thống chạy y như trước
_PROMPT_Y_DINH = """Bạn đọc MỘT câu của khách trong nhà hàng Việt Nam và phân loại Ý ĐỊNH.

Bạn KHÔNG chọn món, KHÔNG gán nhãn, KHÔNG viết câu trả lời. Chỉ phân loại.

Trả về JSON đúng dạng này, không thêm chữ nào ngoài JSON:
{"y_dinh": "...", "bo": []}

"y_dinh" nhận ĐÚNG một trong các giá trị sau:
- "chao_hoi"       khách chào, mở lời
- "cam_on"         khách cảm ơn, kết thúc
- "xin_them"       khách xin gợi ý THÊM hoặc gợi ý KHÁC với những gì vừa nêu
- "xoa_rang_buoc"  khách nói không còn một điều kiện đã nêu trước đó (hết dị ứng, bỏ điều kiện)
- "ngoai_pham_vi"  khách nói chuyện không liên quan món ăn, đồ uống của nhà hàng
- "hoi_mon"        MỌI trường hợp còn lại: hỏi về món, về thực đơn, về nhà hàng

"bo" chỉ dùng khi y_dinh là "xoa_rang_buoc", nhận "allergen" hoặc "all". Còn lại để mảng rỗng.

Không chắc thì trả "hoi_mon". Đó là mặc định an toàn: nó để phần còn lại của hệ thống xử lý.

Ví dụ:
Khách: "nhà hàng đông không bạn"
{"y_dinh": "ngoai_pham_vi", "bo": []}

Khách: "còn món nào nữa không"
{"y_dinh": "xin_them", "bo": []}

Khách: "giờ mình ăn hải sản được rồi"
{"y_dinh": "xoa_rang_buoc", "bo": ["allergen"]}

Khách: "có món nào không cay không"
{"y_dinh": "hoi_mon", "bo": []}
"""

_HOP_LE = {CHAO_HOI, CAM_ON, XIN_THEM, XOA_RANG_BUOC, NGOAI_PHAM_VI, HOI_MON}
_NHOM_HOP_LE = {"allergen", "all"}


def doc_y_dinh_bang_mo_hinh(cau: str, env: dict, *, use_cache: bool = True) -> YDinh:
    """Hỏi mô hình khi danh sách cụm không nhận ra. Thất bại thì trả `HOI_MON`.

    Mọi giá trị lạ bị BỎ, không được sửa thành giá trị gần nhất: một ý định đoán bừa sẽ định tuyến
    khách sang một nhánh sai, và nhánh sai ở đây nghĩa là câu trả lời sai loại. `HOI_MON` là mặc
    định đúng vì nó chuyển việc lại cho phần đã đo được.
    """
    from llm_understand import call_model

    parsed = call_model(
        cau, env, use_cache=use_cache, prompt=_PROMPT_Y_DINH, nhan="y_dinh", max_tokens=80
    )
    if not isinstance(parsed, dict):
        return YDinh(nguon="mo_hinh_that_bai")

    ten = str(parsed.get("y_dinh") or "").strip()
    if ten not in _HOP_LE:
        return YDinh(nguon="mo_hinh_that_bai")

    bo = [str(x).strip() for x in (parsed.get("bo") or []) if isinstance(x, str)]
    bo = [x for x in bo if x in _NHOM_HOP_LE]
    # Nói "xóa" mà không nói xóa GÌ thì không xóa gì — chốt an toàn, không đoán hộ khách.
    if ten == XOA_RANG_BUOC and not bo:
        return YDinh(nguon="mo_hinh_that_bai")
    return YDinh(ten=ten, bo_rang_buoc=bo, nguon="mo_hinh", cum_khop="")


# ------------------------------------------------------------------------------------------------
# Câu trả lời cho các ý định KHÔNG phải hỏi món.
#
# Viết sẵn, không nhờ mô hình: chúng là câu xã giao, và một lời chào thì không cần 8,6 giây chờ.
# Chúng cũng phải NÊU PHẠM VI, vì lượt đầu tiên là chỗ khách học được trợ lý này làm gì.
# ------------------------------------------------------------------------------------------------
LOI_CHAO = (
    "Dạ em chào anh/chị. Em tư vấn món ăn và đồ uống của nhà hàng mình ạ. "
    "Anh/chị cho em biết đi mấy người, thích ăn gì, hoặc có gì cần tránh — em gợi ý ngay."
)

LOI_CAM_ON = (
    "Dạ em cảm ơn anh/chị. Anh/chị cần thêm gợi ý món nào thì nhắn em nhé."
)

LOI_TAN_GAU = (
    "Dạ em chỉ tư vấn được món ăn và đồ uống của nhà hàng mình thôi ạ. "
    "Anh/chị muốn em gợi ý gì cho bữa hôm nay không?"
)


def cau_tra_loi_xa_giao(request) -> str | None:
    """Câu cho ý định xã giao, hoặc None nếu lượt này cần đi tiếp xuống tầng chọn món.

    Nhận `Request` chứ không nhận `YDinh`: ý định đã được `understand()` đọc và đặt lên `Request`
    (kèm phép chặn "câu này còn nêu thứ khác"), nên đọc lại ở đây là tạo ra một đường quyết định thứ
    hai — và hai đường sẽ lệch nhau.
    """
    return {CHAO_HOI: LOI_CHAO, CAM_ON: LOI_CAM_ON, NGOAI_PHAM_VI: LOI_TAN_GAU}.get(
        getattr(request, "y_dinh", HOI_MON)
    )


# Tên tiếng Việt của nhãn, để câu xác nhận NÓI RA thứ vừa bỏ.
#
# Chỉ nhóm nào khách có thể tự khai mới cần ở đây. Nhãn không có trong bảng thì nêu nguyên khóa —
# xấu nhưng thật, và tốt hơn là im lặng bỏ qua nó.
_TEN_VI = {
    "allergen:seafood": "hải sản",
    "allergen:peanut": "đậu phộng",
    "allergen:egg": "trứng",
    "allergen:dairy": "sữa",
    "allergen:gluten": "gluten",
    "spice:none": "không cay",
    "spice:mild": "cay nhẹ",
    "spice:medium": "cay vừa",
    "spice:hot": "cay đậm",
    "diet:vegetarian": "món chay",
    "party:solo": "một người",
    "party:two_three": "2–3 người",
    "party:three_five": "3–5 người",
}


def cau_xac_nhan_da_bo(da_bo: list[str]) -> str:
    """Câu NÓI RA những ràng buộc vừa bị bỏ, ghép vào đầu câu trả lời.

    Đây là điều phân biệt "có đường bỏ ràng buộc" với "im lặng bỏ ràng buộc". Hạ một hàng rào an
    toàn mà không nói thì khách không có cách nào biết để sửa nếu hệ thống hiểu sai câu của họ —
    và với dị nguyên, hiểu sai theo hướng này là lỗi nguy hiểm nhất hệ thống có thể mắc.
    """
    if not da_bo:
        return ""
    ten = [_TEN_VI.get(t, t) for t in da_bo]
    if len(ten) == 1:
        return f"Dạ em đã bỏ điều kiện {ten[0]} theo yêu cầu của anh/chị. "
    return f"Dạ em đã bỏ các điều kiện: {', '.join(ten)}. "
