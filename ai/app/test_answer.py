# -*- coding: utf-8 -*-
"""Test phần trả lời — trọng tâm là thứ tự sắp món và ranh giới ràng buộc / ngữ cảnh.

Tệp này ra đời muộn hơn `answer.py`, và lý do đáng ghi: hành vi của `answer.py` trước đó chỉ được
kiểm qua 119 ca đánh giá. Điều đó đủ để bắt lỗi *câu trả lời sai*, nhưng KHÔNG đủ để bắt lỗi *câu
trả lời đúng theo tiêu chí mà vẫn tệ với khách* — và đúng một lỗi loại đó đã sống sót:

    "Món nào không cay?"  ->  sáu loại bia

13/119 ca khách hỏi "món" mà nhận toàn đồ uống, và **cả 13 đều QUA** vì khóa đáp án không cấm đồ
uống. Nó chỉ lộ ra khi tôi đọc đầu ra thật của thẻ giỏ hàng.

Bài học: **tập đánh giá đo điều nó được viết để đo.** Một hành vi không có ca thì không có gì canh,
kể cả khi tỷ lệ chung là 90,8%.

    python -m unittest test_answer      # trong ai/app
"""
from __future__ import annotations

import json
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
