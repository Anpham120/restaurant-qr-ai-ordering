# -*- coding: utf-8 -*-
"""Test phần trả lời — trọng tâm là thứ tự sắp món và ranh giới ràng buộc / ngữ cảnh.

Tệp này ra đời muộn hơn `answer.py`, và lý do đáng ghi: hành vi của `answer.py` trước đó chỉ được
kiểm qua 119 ca đánh giá. Điều đó đủ để bắt lỗi *câu trả lời sai*, nhưng KHÔNG đủ để bắt lỗi *câu
trả lời đúng theo tiêu chí mà vẫn tệ với khách* — và đúng một lỗi loại đó đã sống sót:

    "Món nào không cay?"  ->  sáu loại bia

13/119 ca khách hỏi "món" mà nhận toàn đồ uống, và **cả 13 đều QUA** vì khóa đáp án không cấm đồ
uống. Nó chỉ lộ ra khi tôi đọc đầu ra thật của thẻ giỏ hàng.

Bài học: **tập đánh giá đo điều nó được viết để đo.** Một hành vi không có ca thì không có gì canh,
kể cả khi tỷ lệ chung là 100%.

    python -m unittest test_answer      # trong ai/app
"""
from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from answer import respond, select  # noqa: E402
from understand import DRINK_CATEGORIES, FOOD_CATEGORIES, understand  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ITEMS = json.loads(
    (REPO_ROOT / "backend" / "data" / "menu-dataset.json").read_text(encoding="utf-8-sig")
)["items"]
BY_ID = {i["id"]: i for i in ITEMS}


def reply_for(question: str):
    request = understand(question, ITEMS)
    return request, respond(request, ITEMS)


def drinks_in(reply) -> list[str]:
    return [i for i in reply.items if BY_ID[i]["categoryId"] in DRINK_CATEGORIES]


class MonAnXepTruocDoUongKhiKhachChuaNoiRo(unittest.TestCase):
    """Ngữ cảnh, không phải ràng buộc: XẾP TRƯỚC nhưng KHÔNG lọc bỏ.

    Nguyên nhân gốc đo được: 5 món rẻ nhất thực đơn đều là đồ uống (12.000–30.000đ) còn món ăn rẻ
    nhất là 35.000đ. Sắp theo giá tăng dần làm đồ uống luôn đứng đầu.
    """

    def test_cau_hoi_mon_KHONG_tra_toan_do_uong(self):
        for cau in ("Món nào không cay?", "Có món nào dưới 50.000đ?",
                    "Tôi dị ứng đậu phộng, món nào tránh được?",
                    "Bé nhà mình dị ứng sữa, có món nào được không?",
                    "Cho mình món không hải sản", "Món nào không sữa"):
            _, reply = reply_for(cau)
            with self.subTest(cau):
                self.assertTrue(reply.items, "tiền đề: câu này phải nêu món")
                uong = drinks_in(reply)
                self.assertLess(
                    len(uong), len(reply.items),
                    f"{cau!r} trả TOÀN đồ uống ({len(uong)}/{len(reply.items)}) — khách hỏi món",
                )

    def test_KHONG_loai_bo_do_uong_khi_do_uong_la_cau_tra_loi_dung(self):
        """Chiều ngược, BẮT BUỘC. Lọc cứng ở đây sẽ hỏng đúng ca này.

        Không món ăn nào dưới 20.000đ, nên đồ uống là câu trả lời TRUNG THỰC. Trả rỗng hoặc nói
        "không có món nào phù hợp" mới là sai — khách hỏi thật và dữ liệu trả lời được.
        """
        _, reply = reply_for("Có món nào rẻ hơn 20 nghìn không?")
        self.assertTrue(reply.items, "không được trả rỗng khi dữ liệu có câu trả lời")
        self.assertEqual(
            len(drinks_in(reply)), len(reply.items),
            "dưới 20.000đ thì thực đơn CHỈ có đồ uống — đó là sự thật, không phải lỗi",
        )

    def test_khach_hoi_do_uong_thi_van_tra_do_uong(self):
        _, reply = reply_for("Nhà hàng có trà gì?")
        self.assertTrue(reply.items)
        for i in reply.items:
            self.assertEqual(BY_ID[i]["categoryId"], "cat_drink")

    def test_khach_hoi_mon_an_thi_KHONG_co_do_uong_nao(self):
        """Khi khách nói rõ "món ăn" thì đây là RÀNG BUỘC, lọc cứng — khác với trường hợp trên."""
        _, reply = reply_for("Gợi ý món ăn giúp mình")
        self.assertTrue(reply.items)
        self.assertEqual(drinks_in(reply), [])

    def test_thu_tu_tat_dinh_giua_hai_lan_chay(self):
        for cau in ("Món nào không cay?", "Cho mình món chay"):
            with self.subTest(cau):
                self.assertEqual(reply_for(cau)[1].items, reply_for(cau)[1].items)


class RangBuocKhacNguCanh(unittest.TestCase):
    def test_dip_an_chi_xep_thu_tu_khong_loai_mon(self):
        request = understand("Mình đi hẹn hò, gợi ý món nào", ITEMS)
        self.assertTrue(request.prefer_tags, "tiền đề: câu này sinh nhãn ngữ cảnh")
        self.assertEqual(
            request.prefer_tags[0].split(":")[0], "occasion",
            "dịp ăn phải ở prefer_tags",
        )
        for tag in request.prefer_tags:
            self.assertNotIn(tag, request.require_tags, "ngữ cảnh KHÔNG được vào require_tags")

    def test_an_chay_la_rang_buoc_loc_cung(self):
        request = understand("Mình ăn chay", ITEMS)
        chosen = select(request, ITEMS)
        self.assertLess(len(chosen), len(ITEMS), "ăn chay phải LỌC, không chỉ xếp thứ tự")

    def test_di_nguyen_fail_closed_khong_bao_gio_noi(self):
        request = understand("Mình dị ứng hải sản, gợi ý món ăn giúp mình", ITEMS)
        chosen = select(request, ITEMS)
        sot = [i["id"] for i in chosen if "allergen:seafood" in i["tags"]]
        self.assertEqual(sot, [], "lọc dị nguyên phải fail-closed")

    def test_ket_qua_rong_thi_KHONG_noi_rang_buoc_di_nguyen(self):
        """Thà nói "không có món nào phù hợp" còn hơn mời món có thể gây dị ứng."""
        request = understand("Mình dị ứng hải sản, cho món hải sản", ITEMS)
        chosen = select(request, ITEMS)
        sot = [i["id"] for i in chosen if "allergen:seafood" in i["tags"]]
        self.assertEqual(sot, [])


class SauNhanhLoaiTruNhau(unittest.TestCase):
    def test_moi_cau_di_dung_mot_nhanh(self):
        mong_doi = (
            ("Hôm nay thời tiết thế nào?", "off_topic", "refuse"),
            ("Nhà hàng mấy giờ mở cửa?", "facts:hours", "fact"),
            ("Phở bò tái nạm bao nhiêu tiền?", "price_lookup", "fact"),
            ("Món nào rẻ nhất?", "extreme:cheapest", "fact"),
            ("Cho mình món chay", "filter", "list"),
            ("Gợi ý món đi", "clarify", "clarify"),
        )
        for cau, branch, kind in mong_doi:
            _, reply = reply_for(cau)
            with self.subTest(cau):
                self.assertEqual(reply.branch, branch)
                self.assertEqual(reply.kind, kind)

    def test_nhanh_hoi_lai_KHONG_neu_mon_nao(self):
        """Hỏi lại là câu trả lời ĐÚNG ở đó, nhưng nó không được kèm danh sách món —
        kèm danh sách thì nó không còn là câu hỏi lại."""
        _, reply = reply_for("Gợi ý món đi")
        self.assertTrue(reply.asks_back)
        self.assertEqual(reply.items, [])


class MoiMonNeuRaPhaiCoThatVaDungGia(unittest.TestCase):
    def test_moi_ma_mon_ton_tai(self):
        for cau in ("Cho mình món chay", "Món nào không cay?", "Món nào rẻ nhất?",
                    "So sánh Phở bò tái nạm và Bún bò Huế"):
            _, reply = reply_for(cau)
            for i in reply.items:
                with self.subTest(f"{cau} / {i}"):
                    self.assertIn(i, BY_ID)

    def test_gia_neu_trong_cau_tra_loi_khop_thuc_don(self):
        import re

        _, reply = reply_for("Phở bò tái nạm bao nhiêu tiền?")
        gia_that = {BY_ID[i]["price"] for i in reply.items}
        gia_neu = {
            int(m.replace(".", ""))
            for m in re.findall(r"(\d{1,3}(?:\.\d{3})+)đ", reply.text)
        }
        self.assertTrue(gia_neu, "câu hỏi giá phải nêu giá")
        self.assertTrue(
            gia_neu <= gia_that,
            f"nêu giá {sorted(gia_neu - gia_that)} không có trong thực đơn",
        )


class BangTenNhanPhaiPhuDU(unittest.TestCase):
    """`_ALLERGEN_VI` và `_SPICE_VI` phải phủ ĐỦ nhãn của nhóm tương ứng trong từ điển.

    Hai bảng này viết tay trong `answer.py`, nên chúng trôi được: thêm một nhãn dị nguyên vào từ
    điển mà quên thêm ở đây thì câu trả lời gọi nó bằng phần sau dấu hai chấm — "CÓ shellfish" —
    và khách đọc thấy chữ tiếng Anh giữa câu tiếng Việt.

    Test này biến việc trôi thành lỗi thấy được. Không đọc thẳng `label_vi` trong `answer.py` là có
    chủ ý: `label_vi` là nhãn hiển thị trên chip ("Có hải sản"), còn câu trả lời cần tên thuộc tính
    để ghép vào câu ("hải sản") — hai dạng khác nhau, nên bảng riêng là đúng, chỉ cần chống trôi.
    """

    @classmethod
    def setUpClass(cls):
        cls.tags = json.loads(
            (REPO_ROOT / "backend" / "data" / "menu-tags.json").read_text(encoding="utf-8-sig")
        )["tags"]

    def test_moi_nhan_di_nguyen_co_ten_tieng_viet(self):
        from answer import _ALLERGEN_VI

        thieu = sorted(t for t in self.tags if t.startswith("allergen:") and t not in _ALLERGEN_VI)
        self.assertEqual(thieu, [], f"thiếu tên tiếng Việt cho {thieu} trong `_ALLERGEN_VI`")

    def test_moi_muc_cay_co_ten_tieng_viet(self):
        from answer import _SPICE_VI

        thieu = sorted(t for t in self.tags if t.startswith("spice:") and t not in _SPICE_VI)
        self.assertEqual(thieu, [], f"thiếu tên tiếng Việt cho {thieu} trong `_SPICE_VI`")

    def test_khong_ten_nao_du(self):
        """Chiều ngược: bảng có nhãn mà từ điển không có nghĩa là nhãn đã bị bỏ khỏi thực đơn."""
        from answer import _ALLERGEN_VI, _SPICE_VI

        du = sorted(set(_ALLERGEN_VI) | set(_SPICE_VI) - set(self.tags))
        du = [t for t in du if t not in self.tags]
        self.assertEqual(du, [], f"bảng còn nhãn không có trong từ điển: {du}")

    def test_cau_tra_loi_di_nguyen_NEU_TEN_thanh_phan(self):
        """Khách hỏi về sữa thì câu trả lời phải nói 'sữa', không nói 'thành phần bạn cần tránh'.

        Ở câu về dị ứng, bắt khách tự suy ra thành phần nào là chỗ tệ nhất để tiết kiệm chữ.
        """
        r = understand("Ốc hương rang bơ tỏi có sữa không? Mình không dung nạp lactose", ITEMS)
        reply = respond(r, ITEMS)
        self.assertIn("sữa", reply.text.lower())

    def test_cau_so_sanh_NEU_DO_CAY_khong_chi_gia(self):
        """Câu "món nào cay hơn?" từng nhận về so sánh GIÁ — đúng dữ liệu, sai câu hỏi."""
        r = understand("Gà nướng mật ong và gà nướng muối ớt xanh, món nào cay hơn?", ITEMS)
        reply = respond(r, ITEMS)
        self.assertIn("cay", reply.text.lower())
        self.assertIn("cay vừa", reply.text.lower())


class CauChuKHACHDOCTHAY(unittest.TestCase):
    """Lỗi CHỮ trong câu trả lời — thứ thước đo nội dung không bắt được.

    Thước đo chấm ĐÚNG/SAI về dữ liệu: món có thật không, giá đúng không, có lọt món cần tránh
    không. Nó không chấm câu có đọc được không. Nên một câu như:

        "Mình chỉ đọc được phần thực đơn ghi, nên Bạn nhắc nhân viên…"

    qua được mọi ca đánh giá, dù khách đọc thấy ngay chữ B hoa giữa câu. Lỗi này chỉ hiện ra khi
    ĐỌC câu trả lời thật qua backend, và nó đã hiện ra đúng như vậy.

    Ba phép kiểm dưới đây quét TOÀN BỘ câu trả lời của 119 ca, không chỉ vài ca mẫu — vì lỗi chữ
    nằm ở nhánh nào thì chỉ ca đi qua nhánh đó mới lộ.
    """

    @classmethod
    def setUpClass(cls):
        cases = json.loads(
            (REPO_ROOT / "ai" / "evaluation" / "cases.json").read_text(encoding="utf-8-sig")
        )["cases"]
        cls.tra_loi = [
            (c["id"], respond(understand(c["question"], ITEMS), ITEMS).text) for c in cases
        ]

    def test_khong_chu_hoa_giua_cau(self):
        """Chữ hoa sau dấu phẩy hoặc sau một từ nối là dấu hiệu ghép chuỗi sai chỗ."""
        xau = []
        for cid, text in self.tra_loi:
            for noi in (", nên ", ", và ", ", rồi ", ", thì ", " nên ", " và "):
                vi_tri = text.find(noi)
                while vi_tri >= 0:
                    sau = text[vi_tri + len(noi):]
                    if sau[:1].isupper() and not sau.startswith(("Mình", "Bạn nhé")):
                        # Tên món viết hoa là hợp lệ — bỏ qua nếu ngay sau đó là một tên món.
                        if not any(sau.startswith(i["name"]) for i in ITEMS):
                            xau.append(f"{cid}: …{noi}{sau[:34]}…")
                            break
                    vi_tri = text.find(noi, vi_tri + 1)
        self.assertEqual(xau, [], f"{len(xau)} câu có chữ hoa giữa câu: {xau[:6]}")

    def test_khong_hai_dau_cach_hoac_dau_cau_lien_tiep(self):
        xau = [
            f"{cid}: {text[:60]!r}" for cid, text in self.tra_loi
            if "  " in text or ".." in text or " ." in text or " ," in text
        ]
        self.assertEqual(xau, [], f"{len(xau)} câu có khoảng trắng/dấu câu lặp: {xau[:4]}")

    def test_moi_cau_ket_thuc_bang_dau_cau(self):
        xau = [
            f"{cid}: {text[-30:]!r}" for cid, text in self.tra_loi
            if text and text.rstrip()[-1] not in ".?!"
        ]
        self.assertEqual(xau, [], f"{len(xau)} câu không có dấu kết: {xau[:4]}")


class RONG_VI_LOAI_TRU_KHAC_RONG_VI_RANG_BUOC(unittest.TestCase):
    """Hai nguyên nhân làm kết quả rỗng, và chúng phải cho hai câu trả lời khác nhau.

    Golden qua stack thật bắt được: khách xem ba lượt danh sách rồi nói "Cho mình món khác đi", và
    nhận "Mình chưa tìm được món nào thỏa hết những điều bạn nêu ạ" — trong khi CÓ món thỏa ràng
    buộc, chỉ là chúng đã được nêu ở ba lượt trước.

    Ranh giới không được nhòe, và đó là lý do lớp test này tồn tại:

        loại trừ món đã gợi ý   phép LỊCH SỰ    -> nới được, và phải nới thay vì trả rỗng
        dị nguyên · cay · giá   ràng buộc AN TOÀN -> KHÔNG BAO GIỜ nới, kể cả khi rỗng

    Nới nhóm thứ nhất dẫn tới việc nhắc lại một món khách đã thấy. Nới nhóm thứ hai dẫn tới việc mời
    khách một món có thể gây hại. Nên test cuối cùng của lớp này quan trọng hơn ba test đầu.
    """

    def _req(self, **kw):
        r = understand("Gợi ý món ăn cho mình với", ITEMS)
        for k, v in kw.items():
            setattr(r, k, v)
        return r

    def test_rong_vi_loai_tru_thi_NOI_va_noi_ro(self):
        mon_an = [i["id"] for i in ITEMS if i["categoryId"] in FOOD_CATEGORIES]
        rep = respond(self._req(exclude_item_ids=mon_an), ITEMS)
        self.assertEqual(rep.branch, "exhausted_after_exclusions")
        self.assertIn("đã nêu hết", rep.text)
        # KHÔNG nêu lại danh sách: khách vừa nói "cho mình món khác đi". Bản đầu của nhánh này nêu
        # lại đúng những món khách vừa từ chối, và golden bắt được bằng `must_not_repeat_turn`.
        self.assertEqual(rep.items, [], "không được gợi lại món khách vừa từ chối")
        self.assertTrue(rep.asks_back, "phải mời khách bỏ bớt điều kiện — còn đường đi tiếp")

    def test_khong_bi_loai_tru_thi_khong_vao_nhanh_do(self):
        """Nhánh mới KHÔNG được lấy ca của nhánh lọc bình thường."""
        rep = respond(self._req(), ITEMS)
        self.assertEqual(rep.branch, "filter")

    def test_rong_vi_RANG_BUOC_thi_van_la_empty_result(self):
        """Ràng buộc không thỏa được thì câu trả lời đúng vẫn là "chưa tìm được món nào"."""
        rep = respond(self._req(require_tags=["spice:hot"], avoid_tags=["spice:hot"]), ITEMS)
        self.assertEqual(rep.branch, "empty_result")
        self.assertEqual(rep.items, [])

    def test_KHONG_noi_rang_buoc_DI_NGUYEN_de_lap_cho_trong(self):
        """Bất biến an toàn: nới loại trừ thì được, nới dị nguyên thì KHÔNG.

        Dựng đúng tình huống dễ nhầm nhất: loại trừ ĐÃ ăn hết tập ứng viên, VÀ khách có dị nguyên.
        Nhánh mới bỏ loại trừ rồi lọc lại — nếu nó bỏ luôn `avoid_tags` thì món dị nguyên quay lại.
        """
        seafood = [i for i in ITEMS if "allergen:seafood" in i["tags"]]
        self.assertTrue(seafood, "thực đơn phải có món hải sản để test này có nghĩa")
        khong_hai_san = [i["id"] for i in ITEMS if "allergen:seafood" not in i["tags"]]
        rep = respond(
            self._req(avoid_tags=["allergen:seafood"], exclude_item_ids=khong_hai_san), ITEMS
        )
        ten = {i["id"]: i for i in ITEMS}
        xau = [ten[i]["name"] for i in rep.items if "allergen:seafood" in ten[i]["tags"]]
        self.assertEqual(
            xau, [],
            "nhánh nới loại trừ đã nới luôn ràng buộc dị nguyên — đây là lỗi AN TOÀN, "
            f"món lọt: {xau}",
        )


class CHU_CHO_KHACH_DOC(unittest.TestCase):
    """`chu_cho_khach` — đoạn tri thức trình bày cho khách, KHÔNG đổi nội dung.

    Vì sao có lớp này: hỏi stack thật "Phở với bún khác nhau thế nào?" và khách nhận về

        Phở, bún, mì, hủ tiếu — khác nhau thế nào — Khác nhau ở SỢI... là **sợi**: - **Phở** — sợi dẹt

    Nội dung ĐÚNG, trình bày sai ba chỗ: nhan đề dính đầu câu, `**` markdown lọt nguyên, gạch đầu dòng
    nối thành đoạn dài. Cả ba đến từ `" ".join(text.split())`.

    Test cuối là test quan trọng nhất: hàm này **không được làm mất chữ nào**. Nếu nó cắt nội dung thì
    nó thành một dạng tóm tắt — và tóm tắt tri thức nhà hàng là đúng điều đường này tồn tại để tránh.
    """

    @dataclass
    class Doan:
        chunk_id: str = "kb.x#1"
        heading: str = "Khác nhau ở SỢI"
        text: str = (
            "Phở, bún, mì — khác nhau thế nào — Khác nhau ở SỢI\n"
            "Điều phân biệt chúng là **sợi**:\n"
            "- **Phở** — sợi dẹt, mềm.\n"
            "- **Bún** — sợi tròn nhỏ.\n"
        )

    def test_bo_nhan_de_o_dau_cau(self):
        from answer import chu_cho_khach

        ra = chu_cho_khach(self.Doan())
        self.assertFalse(ra.startswith("Phở, bún, mì —"), f"còn nhan đề: {ra[:60]!r}")
        self.assertTrue(ra.startswith("Điều phân biệt"), ra[:60])

    def test_bo_dau_markdown(self):
        from answer import chu_cho_khach

        ra = chu_cho_khach(self.Doan())
        for dau in ("**", "__", "`"):
            self.assertNotIn(dau, ra, f"còn {dau!r} trong chữ khách đọc")

    def test_gach_dau_dong_thanh_dau_liet_ke_doc_duoc(self):
        from answer import chu_cho_khach

        ra = chu_cho_khach(self.Doan())
        self.assertIn("• Phở — sợi dẹt", ra)
        self.assertNotIn("- **Phở**", ra)

    def test_KHONG_lam_mat_chu_nao(self):
        """Bất biến quan trọng nhất: đây là làm sạch TRÌNH BÀY, không phải tóm tắt.

        So theo TỪ, bỏ những ký tự trình bày mà hàm này có quyền bỏ. Một chữ nội dung bị mất là hàm
        này đã thành một dạng tóm tắt — và tóm tắt tri thức nhà hàng là đúng điều đường này tránh.
        """
        import re

        from answer import chu_cho_khach

        d = self.Doan()
        than = d.text.split("\n", 1)[1]

        def tu(s):
            # So TỪ CÓ NGHĨA, bỏ hết dấu câu và ký tự trình bày.
            #
            # Bản đầu của phép tách này thay `*` bằng khoảng trắng rồi `split()`, nên `**sợi**:` cho
            # hai token `sợi` và `:`, còn bản đã làm sạch cho một token `sợi:` — test đỏ vì CÁCH TÁCH
            # TỪ, không vì mất chữ. Đúng lớp lỗi "phép kiểm sai trước khi hệ thống sai", và lần này
            # nó xảy ra trong chính test tôi vừa viết.
            return re.findall(r"\w+", s, re.UNICODE)

        self.assertEqual(tu(than), tu(chu_cho_khach(d)))

    def test_doan_khong_co_dong_nao_ngoai_tien_to_thi_van_tra_chu(self):
        """Đoạn chỉ có một dòng: không được trả rỗng vì "bỏ dòng đầu"."""
        from answer import chu_cho_khach

        ra = chu_cho_khach(self.Doan(text="Chỉ một dòng duy nhất, không có nội dung sau."))
        self.assertTrue(ra.strip(), "trả rỗng thì khách nhận một câu trắng")


class CHON_MUC_TRONG_TAI_LIEU(unittest.TestCase):
    """`_chon_muc` — xếp hạng mục TRONG một tài liệu, nay bằng embedding.

    Vì sao đổi: bộ so 168 ca (`chunk_selection_cases.json`) đo ĐÚNG đường này, và trên tập niêm phong
    embedding đạt Top-1 0,864 so với BM25 0,750 — riêng câu diễn đạt khác từ là 0,818 so với 0,636.
    Docstring của `_knowledge_chunk` từ trước đã ghi điều kiện: *"Nếu phép đo cho thấy embedding chọn
    đoạn tốt hơn thì đổi — nhưng phải đổi vì SỐ"*, và *"điều kiện để xét lại là có tập ca ĐỦ LỚN"*.
    Cả hai đã có.

    Ba bất biến, và bất biến thứ nhất là bảo đảm CHI PHÍ — không phải chi tiết tối ưu:
    dựng một `EmbeddingIndex` cho mỗi tài liệu mất ~91ms MỖI LƯỢT, tức đắt hơn BM25 gần 1000 lần cho
    cùng một việc. Cách ở đây dùng lại vector của chỉ mục toàn kho đã nạp sẵn.
    """

    def _doan_co_muc(self, topic: str):
        from answer import KNOWLEDGE_PATH
        from rag.chunker import retrievable_chunks

        return [c for c in retrievable_chunks(KNOWLEDGE_PATH) if topic in c.topic_keys and c.heading]

    def test_KHONG_dung_chi_muc_embedding_moi(self):
        """Bảo đảm chi phí: mỗi lượt chat không được trả giá mã hóa 3–8 đoạn."""
        from rag import embedding as EMB

        if not EMB.available():
            self.skipTest("không có sentence-transformers")
        cand = self._doan_co_muc("ordering_guide")
        self.assertTrue(cand, "tiền đề: chủ đề này phải có mục")

        from answer import _bo_truy_hoi_toan_kho, _chon_muc

        _bo_truy_hoi_toan_kho()          # hâm nóng trước khi đếm, như lúc chạy thật
        goc = EMB.EmbeddingIndex.build
        dem = {"n": 0}

        def dem_lai(*a, **kw):
            dem["n"] += 1
            return goc(*a, **kw)

        EMB.EmbeddingIndex.build = staticmethod(dem_lai)
        try:
            _chon_muc(cand, "Gọi bao nhiêu món cho nhóm đông?")
        finally:
            EMB.EmbeddingIndex.build = goc
        self.assertEqual(
            dem["n"], 0,
            "đã dựng chỉ mục embedding mới — mỗi lượt chat sẽ mất thêm ~91ms cho việc đã làm sẵn",
        )

    def test_pha_the_theo_chunk_id_TANG_DAN(self):
        """Cùng luật phá thế với `Bm25Index.search` và với bộ so.

        Hai đường xếp hạng phá thế ngược nhau thì hệ thống không lặp lại được kết quả của chính nó —
        và bản đầu của hàm này dùng `max((điểm, chunk_id))`, tức chọn id LỚN nhất khi hòa.
        """
        from answer import _chon_muc

        @dataclass
        class Doan:
            chunk_id: str
            text: str
            heading: str = "x"

        # Ba đoạn văn bản GIỐNG NHAU -> mọi bộ xếp hạng cho điểm bằng nhau -> chỉ còn luật phá thế.
        doan = [Doan("z#1", "cay"), Doan("a#1", "cay"), Doan("m#1", "cay")]
        self.assertEqual(_chon_muc(doan, "cay").chunk_id, "a#1")

    def test_doan_MO_DAU_thi_lui_ve_bm25_chu_khong_bo_no(self):
        """Đoạn mở đầu không có vector (chỉ mục toàn kho lọc `heading` rỗng).

        Chấm điểm trên tập con thiếu vài đoạn là lặng lẽ LOẠI chúng khỏi cuộc thi — và đoạn bị loại
        có thể là đoạn đúng. Nên thiếu vector cho BẤT KỲ ứng viên nào thì cả lượt lùi về BM25.
        """
        from answer import _chon_muc

        @dataclass
        class Doan:
            chunk_id: str
            text: str
            heading: str = ""

        doan = [Doan("kb.gia#0", "phần dẫn nhập của tài liệu", "")]
        chon = _chon_muc(doan, "bất kỳ")
        self.assertEqual(chon.chunk_id, "kb.gia#0", "phải trả đoạn duy nhất, không được trả None")


class HOI_VE_THUOC_TINH_KHAC_LOC_THEO_THUOC_TINH(unittest.TestCase):
    """Cờ `asks_about_attribute` — cổng chặn lớp mô hình đổi nhánh mà mã tất định đã chọn đúng.

    Golden qua stack thật bắt được hai lượt, và cả hai do LỚP MÔ HÌNH làm sai:

        "Nhãn 'ít calo' dựa trên gì?"   mô hình trả `prefer: health:low_calorie` -> nhánh filter
        "Món này có bột ngọt không?"    mô hình trả `prefer: health:no_msg`      -> nhánh filter

    Khách nhận về "Mời bạn tham khảo: Cơm chiên chay ngũ sắc (50.000đ), …" cho một câu hỏi có/không
    về MỘT món — sai loại câu trả lời, kèm thẻ giỏ cho một câu không hỏi mua gì.

    Phép loại trừ `CANDIDATE_FRAMING` là phần bắt buộc, và test thứ ba ép nó: thiếu nó thì
    "Có món nào không cay không?" — một câu lọc THẬT — cũng bị coi là câu hỏi về thuộc tính, và đó là
    hỏng nặng hơn lỗi đang sửa.
    """

    def test_hoi_dinh_nghia_nhan(self):
        self.assertTrue(understand("Nhãn 'ít calo' dựa trên gì?", ITEMS).asks_about_attribute)

    def test_hoi_thuoc_tinh_cua_mon_dang_noi(self):
        for cau in ("Món này có bột ngọt không?", "Món đó có hành không?",
                    "Cái này có sữa không?"):
            with self.subTest(cau):
                self.assertTrue(understand(cau, ITEMS).asks_about_attribute, cau)

    def test_cau_DOI_UNG_VIEN_thi_KHONG_bat_co(self):
        for cau in ("Có món nào không cay không?", "Món nào không có bột ngọt?",
                    "Gợi ý món ăn cho mình với", "Cho mình món gì ít dầu"):
            with self.subTest(cau):
                self.assertFalse(understand(cau, ITEMS).asks_about_attribute, cau)

    def test_co_nay_KHONG_tu_doi_nhanh_nao(self):
        """Cờ này chỉ NGĂN mô hình đổi nhánh; nó không được tự đổi nhánh nào.

        Nếu nó đổi nhánh thì nó thành một luật định tuyến thứ hai chạy song song với sáu nhánh, và
        không ai đoán được nhánh nào thắng.
        """
        cau = "Món này có bột ngọt không?"
        co = understand(cau, ITEMS)
        khong = understand(cau, ITEMS)
        khong.asks_about_attribute = False
        self.assertEqual(respond(co, ITEMS).branch, respond(khong, ITEMS).branch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
