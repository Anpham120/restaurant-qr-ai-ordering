# -*- coding: utf-8 -*-
"""Slide giới thiệu hệ thống — môn Học máy và Khai phá dữ liệu.

Viết lại từ đầu sau khi bản trước bị tràn khung. Hai thay đổi gốc:

1. NĂM BỐ CỤC CỐ ĐỊNH, không có bố cục tự chế.
   Bản trước đặt hộp bằng toạ độ cm cứng rồi nhồi chữ vào — chữ dài hơn dự tính
   là tràn, và không có gì báo. Nay mỗi slide chọn một trong năm hàm bố cục, mỗi
   hàm có vùng dành sẵn và `assert` chặn NGAY LÚC DỰNG: quá 4 dòng ý, một dòng
   quá 80 ký tự, hay bảng quá 4 hàng thì nổ, không xuất ra tệp.

2. CHỮ PHẢI CỤ THỂ, không phải ít chữ.
   Bản trước ít chữ nhưng khó hiểu, vì chữ toàn khái niệm nén — "độ phủ quyết
   định nhãn dùng được vào việc gì". Nay mỗi slide mở bằng **câu khách hỏi thật**
   hoặc **một con số có đơn vị**, rồi mới tới kết luận. Phần giải thích chuyển
   hết vào kịch bản nói ở Presenter View.

Chạy:  python xuat_slide_hoc_may.py
"""
from __future__ import annotations

from pathlib import Path

from pptx.dml.color import RGBColor
from pptx.util import Cm, Pt

from xuat_slide_pptx import (  # noqa: E402
    W, H, LE, RONG, DEN, XAM, NHAN, NEN, KE,
    Presentation, PP_ALIGN, MSO_ANCHOR,
    txt, anh, trang, bia, ghi_chu_noi, _luu,
)

HERE = Path(__file__).resolve().parent
BD = HERE / "_bieu_do"
SD = HERE / "output" / "_diagrams_BAO_CAO_HOC_MAY_KP"
FONT = "Times New Roman"
TRANG = RGBColor(0xFF, 0xFF, 0xFF)

# Vùng dành sẵn cho nội dung: dưới đường kẻ tiêu đề, trên chân slide.
Y_ND = Cm(3.9)
CAO_ND = H - Y_ND - Cm(1.5)

MAX_DONG, MAX_KY_TU, MAX_HANG = 4, 80, 4

# ── đo chữ bằng chính font slide dùng ────────────────────────────────
# Đếm ký tự là phép gần đúng tồi: "IIIIIIIIII" và "mmmmmmmmmm" cùng 10 ký tự
# nhưng rộng gấp ba lần nhau. Nên chỗ nào quyết định vừa/không vừa thì đo bằng
# bề rộng thật của Times New Roman, không đếm ký tự.
try:
    from PIL import ImageFont

    _TTF = {False: "C:/Windows/Fonts/times.ttf", True: "C:/Windows/Fonts/timesbd.ttf"}
    _kho: dict = {}

    def _font(pt: float, dam: bool):
        k = (round(pt, 1), dam)
        if k not in _kho:
            _kho[k] = ImageFont.truetype(_TTF[dam], max(int(pt * 96 / 72), 1))
        return _kho[k]

    def _so_dong(chu: str, rong_cm: float, pt: float, dam: bool = False) -> int:
        """Số dòng sau khi PowerPoint ngắt theo bề rộng hộp."""
        if not chu.strip():
            return 1
        gh = rong_cm / 2.54 * 96
        n, hien = 1, ""
        for tu in chu.split(" "):
            thu = (hien + " " + tu).strip()
            if _font(pt, dam).getlength(thu) <= gh or not hien:
                hien = thu
            else:
                n, hien = n + 1, tu
        return n

    DO_DUOC = True
except Exception:                                     # noqa: BLE001
    # Không có PIL hay không có font: bỏ phép đo, giữ nguyên các chốt đếm ký tự.
    DO_DUOC = False

    def _so_dong(chu, rong_cm, pt, dam=False):        # type: ignore[misc]
        return 1


def _kiem(muc: list[str]) -> None:
    """Tràn khung là lỗi của người viết nội dung — nên nó phải nổ ở đây, chứ
    không phải lộ ra lúc đứng trước hội đồng."""
    assert len(muc) <= MAX_DONG, f"{len(muc)} dòng ý, tối đa {MAX_DONG}"
    for d in muc:
        assert len(d) <= MAX_KY_TU, f"dòng {len(d)} ký tự (tối đa {MAX_KY_TU}): {d[:48]}…"


def _dong_y(sl, muc, y, co=19):
    # Chốt thật: đo chiều cao khối chữ rồi so với chỗ còn lại tới đáy slide.
    # Chốt đếm ký tự ở `_kiem` chỉ chặn dòng dài; chốt này chặn khối cao.
    if DO_DUOC:
        rong_cm = (RONG / 360000) - 1.2               # trừ lề hộp và dấu ▪
        cao = sum(_so_dong(d, rong_cm, co) * co * 1.25 / 28.35 + 13 / 28.35
                  for d in muc)
        con = (H - y) / 360000 - 1.0
        assert cao <= con, (
            f"khối ý cao {cao:.1f}cm, chỉ còn {con:.1f}cm tới đáy slide — "
            f"bớt dòng hoặc rút chữ")

    tb = sl.shapes.add_textbox(LE, y, RONG, H - y - Cm(1.2))
    tf = tb.text_frame
    tf.word_wrap = True
    for k, d in enumerate(muc):
        p = tf.paragraphs[0] if k == 0 else tf.add_paragraph()
        p.line_spacing = 1.25
        p.space_after = Pt(13)
        r = p.add_run(); r.text = "▪  "
        r.font.size = Pt(co); r.font.color.rgb = NHAN; r.font.name = FONT
        r = p.add_run(); r.text = d
        r.font.size = Pt(co); r.font.color.rgb = DEN; r.font.name = FONT


# ───────────────────────────────────────────── A · ba hoặc bốn thẻ số
def bo_cuc_A(prs, tieu_de, nhan, the_so, muc=()):
    sl = trang(prs, tieu_de, nhan)
    muc = list(muc); _kiem(muc)
    n = len(the_so)
    assert 3 <= n <= 4, "bố cục A nhận 3 hoặc 4 thẻ"
    khe, cao = Cm(0.5), Cm(5.4)
    w = (RONG - khe * (n - 1)) // n
    for i, (so, nh) in enumerate(the_so):
        assert len(nh) <= 48, f"nhãn thẻ quá dài: {nh}"
        o = sl.shapes.add_shape(5, LE + i * (w + khe), Y_ND, w, cao)
        o.fill.solid(); o.fill.fore_color.rgb = NEN
        o.line.color.rgb = KE; o.shadow.inherit = False
        tf = o.text_frame; tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        r = p.add_run(); r.text = so
        r.font.size = Pt(40); r.font.bold = True
        r.font.color.rgb = NHAN; r.font.name = FONT
        q = tf.add_paragraph(); q.alignment = PP_ALIGN.CENTER; q.line_spacing = 1.2
        rr = q.add_run(); rr.text = nh
        rr.font.size = Pt(15); rr.font.color.rgb = DEN; rr.font.name = FONT
    if muc:
        _dong_y(sl, muc, Y_ND + cao + Cm(0.9))
    return sl


# ───────────────────────────────────────────────── B · bốn dòng ý
def bo_cuc_B(prs, tieu_de, nhan, muc):
    sl = trang(prs, tieu_de, nhan)
    _kiem(muc)
    _dong_y(sl, muc, Y_ND + Cm(0.8), co=21)
    return sl


# ─────────────────────────────────────────── C · một hình toàn khung
def bo_cuc_C(prs, tieu_de, nhan, duong, chu_thich=""):
    sl = trang(prs, tieu_de, nhan)
    assert len(chu_thich) <= 108, "chú thích quá dài"
    cao = CAO_ND - (Cm(1.2) if chu_thich else Cm(0))
    anh(sl, duong, LE, Y_ND, RONG, cao, vien=False)
    if chu_thich:
        txt(sl, LE, Y_ND + cao + Cm(0.25), RONG, Cm(0.9),
            chu_thich, 15, False, XAM, PP_ALIGN.CENTER)
    return sl


# ─────────────────────────────────────────────── D · bảng ≤ 4 hàng
def bo_cuc_D(prs, tieu_de, nhan, cot, hang, rong_cot=None, co=17):
    sl = trang(prs, tieu_de, nhan)
    assert len(hang) <= MAX_HANG, f"{len(hang)} hàng, tối đa {MAX_HANG}"
    for h in hang:
        for o in h:
            assert len(o) <= 72, f"ô quá dài ({len(o)} ký tự): {o[:44]}…"
    cao_hang = Cm(2.1)
    t = sl.shapes.add_table(len(hang) + 1, len(cot), LE, Y_ND, RONG,
                            cao_hang * (len(hang) + 1)).table
    if rong_cot:
        for i, c in enumerate(rong_cot):
            t.columns[i].width = int(RONG * c)

    # Chốt quan trọng nhất của bố cục này. PowerPoint TỰ NỚI chiều cao hàng lúc
    # dựng hình nếu chữ trong ô cần nhiều dòng hơn — nó không cắt chữ, và nó
    # KHÔNG sửa lại con số trong XML. Nên mọi phép đo đọc XML đều thấy bảng vừa
    # khung trong khi màn chiếu thấy nó chạy khỏi mép dưới. Đây là kiểu tràn
    # không thể phát hiện bằng cách mở tệp ra đo.
    if DO_DUOC:
        ty = rong_cot or [1 / len(cot)] * len(cot)
        that = 0.0
        for h in [cot] + list(hang):
            cao_o = []
            for i, x in enumerate(h):
                w = (RONG / 360000) * ty[i] - 0.5
                cao_o.append(0.26 + _so_dong(x, w, co) * co * 1.2 / 28.35)
            that += max(max(cao_o), cao_hang / 360000)
        day = (Y_ND / 360000) + that
        gh = (H / 360000) - 0.8
        assert day <= gh, (
            f"bảng nở tới {that:.1f}cm, đáy ở {day:.1f}cm > {gh:.1f}cm — "
            f"rút chữ trong ô hoặc bớt hàng")
    for i, x in enumerate(cot):
        c = t.cell(0, i); c.text = x
        c.fill.solid(); c.fill.fore_color.rgb = NEN
        for p in c.text_frame.paragraphs:
            for r in p.runs:
                r.font.size = Pt(co); r.font.bold = True
                r.font.color.rgb = NHAN; r.font.name = FONT
    for j, h in enumerate(hang, 1):
        for i, x in enumerate(h):
            c = t.cell(j, i); c.text = x
            c.fill.solid(); c.fill.fore_color.rgb = TRANG
            for p in c.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(co - 1)
                    r.font.bold = (i == 0)
                    r.font.color.rgb = DEN if i == 0 else XAM
                    r.font.name = FONT
    return sl


# ───────────────────────────────────────────────── E · một câu lớn
def bo_cuc_E(prs, tieu_de, nhan, cau_lon, muc=()):
    sl = trang(prs, tieu_de, nhan)
    muc = list(muc); _kiem(muc)
    assert len(cau_lon) <= 140, "câu lớn quá dài"
    o = sl.shapes.add_shape(5, LE, Y_ND + Cm(0.5), RONG, Cm(3.2))
    o.fill.solid(); o.fill.fore_color.rgb = NEN
    o.line.color.rgb = NHAN; o.shadow.inherit = False
    tf = o.text_frame; tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; p.line_spacing = 1.3
    r = p.add_run(); r.text = cau_lon
    r.font.size = Pt(23); r.font.bold = True
    r.font.color.rgb = NHAN; r.font.name = FONT
    if muc:
        _dong_y(sl, muc, Y_ND + Cm(4.6))
    return sl


# ══════════════════════════════════════════════════════════ nội dung
def dung() -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    # 1 ─────────────────────────────────────────────────────────── bìa
    sl = bia(prs, "ĐỒ ÁN MÔN HỌC", "Học máy và Khai phá dữ liệu",
             "Hệ thống AI tư vấn gọi món cho nhà hàng",
             "Nhóm 05  ·  GVHD: Phạm Ngọc Đông")
    ghi_chu_noi(sl, """
[~30 giây]
Em chào thầy và các bạn. Nhóm em trình bày hệ thống AI tư vấn gọi món cho nhà
hàng. Khách quét mã QR ở bàn, hỏi bằng tiếng Việt, hệ thống tư vấn món và gợi ý
vào giỏ để khách tự bấm.
""")

    # 2 ──────────────────────────────────────── hệ thống làm gì
    sl = bo_cuc_A(prs, "Khách quét mã QR ở bàn rồi hỏi, hệ thống trả lời", "HỆ THỐNG",
                  [("91", "món trong thực đơn"),
                   ("13", "danh mục món"),
                   ("0", "lần AI tự đặt món")],
                  ["AI chỉ GỢI Ý món — nút thêm vào giỏ luôn do khách bấm"])
    ghi_chu_noi(sl, """
[~50 giây]
Trước hết là hệ thống làm gì.

Khách ngồi xuống bàn, quét mã QR, mở giao diện chat rồi hỏi bằng tiếng Việt bình
thường. Hệ thống trả lời và gợi ý món.

Thực đơn có 91 món chia 13 danh mục.

Con số thứ ba là ranh giới quyền nhóm đặt ra từ đầu: AI KHÔNG bao giờ tự đặt món.
Nó chỉ gợi ý, nút thêm vào giỏ luôn do khách bấm. Đây không phải một lời hứa
trong tài liệu — nó là một hằng số trong mã, không nhánh nào đặt khác được.
""")

    # 3 ────────────────────────── hai câu khách hỏi, hai cách giải
    sl = bo_cuc_D(prs, "Khách hỏi hai kiểu câu, và chúng cần hai cách giải",
                  "BÀI TOÁN",
                  ["Khách hỏi", "Đáp án nằm ở đâu", "Cách giải đúng"],
                  [['"Món nào dưới 100 nghìn, không cay?"',
                    "Ở cột giá và cột nhãn của món",
                    "Lọc bảng — đúng 100%"],
                   ['"Gọi khai vị trước có làm no bụng không?"',
                    "Trong một đoạn văn người viết",
                    "Đi tìm đúng đoạn văn đó"]],
                  rong_cot=[0.36, 0.32, 0.32], co=17)
    ghi_chu_noi(sl, """
[~60 giây]
Đây là bài toán, và em xin trình bày bằng hai câu khách hỏi thật.

Câu thứ nhất: "món nào dưới 100 nghìn, không cay". Đáp án nằm ở cột giá và cột
nhãn. Chỉ cần duyệt 91 món, giữ món thoả điều kiện. Đúng 100 phần trăm, vì "giá
nhỏ hơn 100 nghìn" là một phép so sánh chứ không phải một phép đoán.

Câu thứ hai: "gọi khai vị trước có làm no bụng không". Câu này không có cột nào
để lọc. Đáp án nằm trong một đoạn văn do người viết, và việc phải làm là đi tìm
đúng đoạn văn đó.

Hai câu nghe rất giống nhau — cùng là khách hỏi về món. Nhưng chúng cần hai cách
giải khác hẳn nhau, và đó là điều quyết định toàn bộ thiết kế.
""")

    # 4 ────────────────────────────────────── ba thứ đã dựng
    sl = bo_cuc_A(prs, "Ba thứ nhóm dựng trước khi viết dòng mã trả lời nào", "DỮ LIỆU",
                  [("91", "món — giá, mô tả, danh mục"),
                   ("85", "nhãn dán lên món\nvd: không cay · có hải sản"),
                   ("60", "tài liệu, cắt thành 213 đoạn")],
                  ["Nhãn cho phép TRA BẢNG, thay vì để AI đoán từ mô tả món"])
    ghi_chu_noi(sl, """
[~65 giây]
Phần dữ liệu. Nhóm dựng ba thứ trước khi viết dòng mã trả lời nào.

Thứ nhất là thực đơn 91 món với giá, mô tả, danh mục.
Thứ hai là 85 nhãn dán lên món — ví dụ "không cay", "có hải sản", "món chay".
Thứ ba là kho tri thức 60 tài liệu, cắt thành 213 đoạn.

Điều đáng nói là vì sao phải có nhãn. Mô tả món là câu giới thiệu, ví dụ "Phở bò
tái nạm, nước dùng ninh xương tám tiếng". Từ câu đó AI CÓ THỂ ĐOÁN món này có
gluten. Nhưng "có thể đoán" không dùng được cho câu hỏi "món nào không có gluten"
— vì sai một món là khách dị ứng ăn nhầm.

Nhãn biến phép đoán thành phép tra bảng: có hoặc không, và truy được về đúng một
ô dữ liệu.
""")

    # 5 ──────────────────── nhãn nào dùng để lọc, nhãn nào không
    sl = bo_cuc_D(prs, "Nhãn chỉ được dùng để LỌC khi nó đủ trên cả 91 món", "DỮ LIỆU",
                  ["Nhãn dán được", "Món thiếu nhãn nghĩa là", "Nên dùng để"],
                  [["Đủ 91/91 món", "Dữ liệu ghi sót — phải sửa",
                    "LỌC BỎ món không hợp"],
                   ["Chỉ một phần", "Chưa ai ghi, không phải là không có",
                    "Chỉ XẾP LÊN TRƯỚC"]],
                  rong_cot=[0.24, 0.42, 0.34], co=17)
    ghi_chu_noi(sl, """
[~65 giây]
Đây là nguyên tắc quan trọng nhất của khâu dữ liệu, và nó rất đơn giản.

Nếu một loại nhãn đã dán đủ trên cả 91 món — ví dụ độ cay, mức giá — thì món nào
thiếu nhãn là do ghi sót và phải sửa. Loại nhãn đó dùng được để LỌC BỎ món không
hợp.

Nếu một loại nhãn chỉ dán được một phần — ví dụ dịp ăn, vị — thì món thiếu nhãn
KHÔNG có nghĩa là món đó không hợp. Nó chỉ có nghĩa chưa ai ghi. Loại nhãn đó chỉ
được dùng để xếp món hợp lên trước, tuyệt đối không được dùng để loại món.

Nhầm hai loại này là lỗi hay gặp nhất. Ví dụ nhãn "hẹn hò" chỉ có trên 4 món. Nếu
dùng nó để lọc thì câu "em đi hẹn hò nên gọi gì" chỉ còn đúng một món tôm hùm 890
nghìn — và khách nghĩ nhà hàng chỉ có thế.
""")

    # 6 ────────────────────────────────── giới hạn an toàn
    sl = bo_cuc_E(prs, "Chỗ hệ thống KHÔNG dám hứa", "AN TOÀN",
                  "Nhãn dị ứng mới dán được trên 44 trong 91 món",
                  ["47 món kia: chưa ai ghi — KHÔNG phải là không có dị nguyên",
                   "Nên câu trả lời luôn mời khách nhắc nhân viên để bếp xác nhận",
                   "Có một phép kiểm tự động bắt buộc câu đó phải xuất hiện"])
    ghi_chu_noi(sl, """
[~70 giây]
Slide này nói về chỗ hệ thống KHÔNG dám hứa, và em nghĩ nó là slide quan trọng
nhất phần dữ liệu.

Nhãn dị ứng mới dán được trên 44 trong 91 món. Bốn mươi bảy món còn lại chưa ai
ghi dị nguyên gì cả — và "chưa ai ghi" không có nghĩa là "không có".

Nghĩa là khi khách nói "em dị ứng hải sản", danh sách hệ thống lọc ra KHÔNG phải
một lời bảo đảm an toàn. Nó chỉ là danh sách những món mà dữ liệu hiện có không
ghi nhận hải sản.

Nên mọi câu trả lời loại này đều mời khách nhắc nhân viên để bếp xác nhận. Và câu
đó không phải câu khách sáo — nhóm có một phép kiểm tự động bắt buộc nó phải xuất
hiện. Thiếu câu đó thì câu trả lời bị bỏ, dùng lại câu mẫu.
""")

    # 7 ──────────────────────────────────── bốn đường trả lời
    sl = bo_cuc_C(prs, "Câu hỏi đi đường nào? Bốn đường, chọn theo loại câu",
                  "KIẾN TRÚC", SD / "so-do-2.png",
                  "Ba đường đầu KHÔNG cho AI viết chữ — chỉ đường cuối mới phải đi tìm.")
    ghi_chu_noi(sl, """
[~70 giây]
Đây là kiến trúc. Hệ thống có bốn đường trả lời, và câu hỏi được chọn đường theo
loại của nó.

Đường một, lọc nhãn: dùng cho câu chọn món. Đọc thẳng bảng thực đơn, không đụng
tới kho tri thức.

Đường hai, tra khoá: dùng cho câu chính sách như "mấy giờ đóng cửa". Trả nguyên
văn tài liệu, AI không sửa một chữ nào.

Đường ba, chọn mục: khi đã biết câu hỏi thuộc chủ đề nào rồi, chỉ cần chọn đúng
mục trong tài liệu đó.

Đường bốn, truy hồi: khi không biết chủ đề, phải đi tìm trong toàn bộ 182 đoạn.

Điều đáng chú ý ở dòng dưới: ba đường đầu không cho AI viết chữ — chúng trả về dữ
liệu có sẵn hoặc văn bản có sẵn. Chỉ đường cuối mới thật sự là bài toán tìm kiếm.
""")

    # 8 ──────────────────────────────────── bốn lớp chặn
    sl = bo_cuc_A(prs, "Bốn lớp chặn để AI không nói sai về món ăn", "AN TOÀN",
                  [("1", "Lọc món gây dị ứng\nTRƯỚC khi AI nhìn thấy"),
                   ("2", "AI chỉ được viết chữ\nở 2 trong 19 nhánh"),
                   ("3", "10 phép kiểm câu AI viết\nsai một phép là BỎ câu"),
                   ("4", "Nút đặt món dựng từ\ndanh sách đã lọc")],
                  ["Dặn AI trong lời nhắc chỉ là ĐỀ NGHỊ — phép kiểm sau đó mới là CHẶN"])
    ghi_chu_noi(sl, """
[~75 giây]
Bốn lớp chặn để AI không nói sai về món ăn.

Lớp một: món gây dị ứng bị lọc bỏ TRƯỚC khi AI nhìn thấy danh sách. Nên AI không
có gì để nhắc sai.

Lớp hai: AI chỉ được viết chữ ở hai trong mười chín nhánh trả lời. Mười bảy nhánh
còn lại không có đường nào cho AI ghi chữ.

Lớp ba: mười phép kiểm câu AI viết. Sai một phép là bỏ cả câu, dùng lại câu mẫu —
không sửa, không thử lại.

Lớp bốn: nút đặt món dựng từ danh sách đã lọc, không đọc chữ AI viết. Nên kể cả
khi AI viết nhầm tên món, khách cũng không đặt được món không tồn tại.

Dòng dưới cùng là bài học nhóm trả giá để có. Ban đầu nhóm chỉ dặn AI trong lời
nhắc rằng đừng nhắc món gây dị ứng. Nhưng dặn chỉ là đề nghị — AI bỏ qua được và
không có gì báo. Chỉ phép kiểm chạy SAU khi AI viết mới là chặn thật.
""")

    # 9 ──────────────────────────────── so ba cách đi tìm
    sl = bo_cuc_C(prs, "Ba cách đi tìm đoạn văn — nhóm chọn cách nào, và vì sao",
                  "KẾT QUẢ", BD / "bd1-truy-hoi.png",
                  "Cột tô đậm là cột hệ thống thật sự dùng — mỗi lần nó lấy 2 đoạn.")
    ghi_chu_noi(sl, """
[~75 giây]
Phần kết quả. Nhóm thử ba cách đi tìm đoạn văn, đo trên 66 câu hỏi.

Cách một, BM25: đếm từ chung giữa câu hỏi và đoạn văn. Rất nhanh, một phần nghìn
giây. Nhưng khách hỏi "đồ biển" mà tài liệu viết "hải sản" thì không có từ nào
chung, và nó không tìm được.

Cách hai, embedding: so nghĩa bằng vector. Hiểu được "đồ biển" gần nghĩa "hải sản".

Cách ba, hybrid: trộn hai cách trên.

Nhóm chọn embedding. Nhưng lý do nằm ở cột được tô đậm, và đây là chỗ suýt chọn
sai.

Nếu nhìn cột đầu, Hit@1, thì hybrid cao hơn. Nhưng hệ thống lúc chạy lấy HAI đoạn
mỗi lần, nên cột đúng phải nhìn là Hit@2. Ở cột đó embedding đạt 0,879 còn hybrid
chỉ 0,803.

Nếu nhóm chốt theo cột đầu thì đã chọn cách kém hơn cho chính hệ thống của mình,
mà bảng số vẫn trông đúng.
""")

    # 10 ──────────────────────────────────────── kết quả cuối
    sl = bo_cuc_E(prs, "Kết quả cuối", "KẾT LUẬN",
                  "161/161 câu trả lời đúng  ·  103/103 lượt chạy thật tới giỏ hàng",
                  ["Không lỗi an toàn nào trên 175 lượt hội thoại nhiều lượt",
                   "Bốn thứ nhóm thử thêm rồi bỏ, vì đo được là không giúp gì",
                   "Hệ thống cuối GỌN HƠN bản đầu — đó là kết quả của đo lường"])
    ghi_chu_noi(sl, """
[~70 giây]
Kết quả cuối.

161 trên 161 câu trả lời đúng. Trong đó có 14 câu đi qua đường truy hồi — nhóm mới
bổ sung, vì trước đó tập đánh giá không có câu nào hỏi tới đường đó.

103 trên 103 lượt chạy thật, đi đủ chuỗi từ quét mã QR, qua backend, qua dịch vụ
AI, tới giỏ hàng thật. Đo ở cả hai cấu hình, trên stack dựng lại từ số không.

Không lỗi an toàn nào trên toàn bộ 175 lượt hội thoại nhiều lượt.

Và điều em muốn kết: nhóm thử thêm bốn thứ — trộn hai cách tìm, xếp hạng lại bằng
mô hình thứ hai, gộp tài liệu, và giữ lại nhóm tài liệu cũ. Cả bốn đều đo được là
không giúp gì, và nhóm bỏ hết.

Nên hệ thống cuối gọn hơn bản đầu. Đó là kết quả của đo lường, không phải của việc
cắt bớt cho kịp hạn.

Em xin hết. Nhóm em sẵn sàng nhận câu hỏi của thầy.
""")

    return _luu(prs, HERE / "output" / "SLIDE_HOC_MAY_KPDL.pptx")


if __name__ == "__main__":
    print(dung())
