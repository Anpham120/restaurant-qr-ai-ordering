# -*- coding: utf-8 -*-
"""Test lớp XÁC MINH của đường sinh — chỗ bảo đảm "không bịa" nay nằm.

Vì sao những test này quan trọng hơn test thường
------------------------------------------------
Khi mô hình không viết chữ cho khách, "không bịa món, không bịa giá" là bảo đảm CẤU TRÚC — không có
đường cho lỗi đó tồn tại. Cho mô hình viết thì bảo đảm chuyển sang lớp `verify()`, và lúc đó **những
test này LÀ bảo đảm**. Một lỗ ở đây là một lỗ trong điều dự án hứa với khách.

Dùng mô hình GIẢ, không gọi mạng — cùng cách `test_llm_understand.py` làm, và vì cùng lý do: phép
kiểm về an toàn phải tất định.

    python -m unittest discover -s ai/app -p "test_*.py"
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate import BRANCHES_ALLOWED, verify, write_reply  # noqa: E402
from understand import understand  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ITEMS = json.loads(
    (REPO_ROOT / "backend" / "data" / "menu-dataset.json").read_text(encoding="utf-8-sig")
)["items"]
BY_NAME = {i["name"]: i for i in ITEMS}
PHO = BY_NAME["Phở bò tái nạm"]          # 75.000đ, không ghi nhận dị nguyên
GA = BY_NAME["Phở gà ta"]                # 70.000đ, không ghi nhận dị nguyên
TOM = BY_NAME["Tôm hùm nướng mỡ hành"]   # 890.000đ, ghi nhận hải sản
ENV = {"LLM_BASE_URL": "http://x/v1", "LLM_API_KEY": "k", "LLM_MODEL": "m"}


def gia_lap(text: str, used: list[str] | None = None):
    """Mô hình giả trả về đúng những gì test muốn kiểm."""
    def call(_prompt, _env):
        return {"text": text, "used_item_ids": used if used is not None else []}
    return call


class BonPhepKiemXacMinh(unittest.TestCase):
    """Mỗi phép kiểm một test phá đúng nó, và một test chiều đúng."""

    def test_cau_sinh_dung_thi_khong_vi_pham(self):
        text = ("Mình gợi ý Phở bò tái nạm (75.000đ) và Phở gà ta (70.000đ) — cả hai đều không cay "
                "và trong tầm giá bạn nêu.")
        self.assertEqual(verify(text, [PHO["id"], GA["id"]], [PHO, GA], ITEMS, []), [])

    def test_khai_dung_mon_NGOAI_danh_sach(self):
        loi = verify("Phở bò tái nạm (75.000đ) rất phù hợp.", [PHO["id"], TOM["id"]],
                     [PHO], ITEMS, [])
        self.assertTrue(any("ngoài danh sách" in x for x in loi), loi)

    def test_nhac_mon_that_NHUNG_ngoai_danh_sach_da_loc(self):
        """Kiểu sai nguy hiểm nhất mà so chuỗi bắt được.

        Mô hình lôi một món THẬT khác vào — đúng tên, đúng giá, nên hai phép kiểm về mã món và về
        số tiền đều không bắt. Nhưng món đó **không qua bộ lọc**, nên nó có thể mang nhãn khách cần
        tránh. Đây là lý do phép kiểm số 2 tồn tại.
        """
        text = "Phở bò tái nạm (75.000đ) hoặc Tôm hùm nướng mỡ hành (890.000đ) đều ngon."
        loi = verify(text, [PHO["id"]], [PHO], ITEMS, [])
        self.assertTrue(any("ngoài danh sách đã lọc" in x for x in loi), loi)

    def test_bia_gia(self):
        loi = verify("Phở bò tái nạm chỉ 49.000đ thôi ạ.", [PHO["id"]], [PHO], ITEMS, [])
        self.assertTrue(any("không phải giá" in x for x in loi), loi)

    def test_gia_dung_cua_mon_KHAC_trong_danh_sach_thi_khong_vi_pham(self):
        """Chiều chống chặt quá: 70.000đ là giá của Phở gà ta, và Phở gà ta có trong danh sách."""
        text = "Hai món trong tầm 70.000đ đến 75.000đ ạ."
        self.assertEqual(verify(text, [], [PHO, GA], ITEMS, []), [])

    def test_nhac_mon_mang_nhan_khach_can_tranh_la_loi_AN_TOAN(self):
        """Chốt an toàn, và nó LẶP LẠI điều bộ lọc đã làm — lặp có chủ ý.

        Bộ lọc chọn món; phép này kiểm CHỮ. Hai thứ đó lệch nhau được, và chỗ lệch là chỗ khách dị
        ứng đọc thấy tên một món họ không ăn được.
        """
        text = "Bạn thử Tôm hùm nướng mỡ hành (890.000đ) nhé."
        loi = verify(text, [], [TOM], ITEMS, ["allergen:seafood"])
        self.assertTrue(any(x.startswith("AN TOÀN") for x in loi), loi)

    def test_so_nho_khong_phai_tien_thi_bo_qua(self):
        """"đi 2 người" không phải số tiền. Bắt oan ở đây làm mọi câu sinh bị bỏ."""
        self.assertEqual(verify("Hai món này đủ cho 2 người ạ.", [], [PHO, GA], ITEMS, []), [])


class ChiSinhChoLoaiC(unittest.TestCase):
    """Đề bài cấm sinh ở loại A. Danh sách nhánh được phép là chỗ điều đó được thực thi."""

    def test_danh_sach_nhanh_dung_hai_nhanh(self):
        self.assertEqual(BRANCHES_ALLOWED, {"filter", "compare"})

    def test_nhanh_ngoai_danh_sach_KHONG_goi_mo_hinh(self):
        r = understand("Phở bò tái nạm bao nhiêu tiền?", ITEMS)
        for nhanh in ("price_lookup", "item_detail", "off_topic", "clarify", "no_data",
                      "knowledge:portion_timing"):
            ra = write_reply(r, [PHO], ITEMS, nhanh, ENV, call=gia_lap("gì cũng được"))
            self.assertFalse(ra.called, f"nhánh {nhanh} đã gọi mô hình")
            self.assertIsNone(ra.text)

    def test_khong_co_mon_thi_khong_goi(self):
        r = understand("Gợi ý món ăn", ITEMS)
        ra = write_reply(r, [], ITEMS, "filter", ENV, call=gia_lap("x"))
        self.assertFalse(ra.called)


class ViPhamThiBO_KHONG_SUA(unittest.TestCase):
    """Câu sinh vi phạm thì bị BỎ và hệ thống dùng lại câu khuôn mẫu."""

    def test_vi_pham_thi_text_la_None_va_co_ly_do(self):
        r = understand("Gợi ý món ăn dưới 100.000đ", ITEMS)
        ra = write_reply(r, [PHO], ITEMS, "filter", ENV,
                         call=gia_lap("Phở bò tái nạm chỉ 49.000đ ạ.", [PHO["id"]]))
        self.assertIsNone(ra.text)
        self.assertTrue(ra.called)
        self.assertEqual(ra.reason, "không qua xác minh")
        self.assertTrue(ra.violations)

    def test_cau_sinh_dung_thi_duoc_dung(self):
        r = understand("Gợi ý món ăn dưới 100.000đ", ITEMS)
        cau = "Phở bò tái nạm (75.000đ) không cay và trong tầm giá bạn nêu ạ."
        ra = write_reply(r, [PHO], ITEMS, "filter", ENV, call=gia_lap(cau, [PHO["id"]]))
        self.assertEqual(ra.text, cau)
        self.assertEqual(ra.used, [PHO["id"]])

    def test_mo_hinh_tra_ve_None_thi_lui_ve_khuon(self):
        r = understand("Gợi ý món ăn", ITEMS)
        ra = write_reply(r, [PHO], ITEMS, "filter", ENV, call=lambda p, e: None)
        self.assertIsNone(ra.text)
        self.assertTrue(ra.called)

    def test_text_rong_hoac_sai_kieu_thi_lui_ve_khuon(self):
        r = understand("Gợi ý món ăn", ITEMS)
        for xau in ({"text": "", "used_item_ids": []}, {"text": 5, "used_item_ids": []},
                    {"used_item_ids": []}, {"text": "ok", "used_item_ids": "m_008"}):
            ra = write_reply(r, [PHO], ITEMS, "filter", ENV, call=lambda p, e, x=xau: x)
            self.assertIsNone(ra.text, xau)

    def test_KHONG_thu_lai_sau_khi_vi_pham(self):
        """Thử lại là để một câu sai có cơ hội thứ hai trong lúc khách đang chờ.

        Đếm số lần gọi: đúng một lần, bất kể kết quả.
        """
        dem = {"n": 0}

        def call(_p, _e):
            dem["n"] += 1
            return {"text": "Phở bò tái nạm 1.000đ", "used_item_ids": [PHO["id"]]}

        r = understand("Gợi ý món ăn", ITEMS)
        write_reply(r, [PHO], ITEMS, "filter", ENV, call=call)
        self.assertEqual(dem["n"], 1)


class LyDoKHONG_VAO_CAU_KHACH_DOC(unittest.TestCase):
    def test_ly_do_va_vi_pham_khong_nam_trong_text(self):
        """Chi tiết lỗi là của người vận hành, không phải của khách — cùng nguyên tắc `decision.error`."""
        r = understand("Gợi ý món ăn", ITEMS)
        ra = write_reply(r, [PHO], ITEMS, "filter", ENV,
                         call=gia_lap("Phở bò tái nạm 1.000đ", [PHO["id"]]))
        self.assertIsNone(ra.text)
        self.assertNotIn("xác minh", ra.text or "")


class GioiHanDaBiet(unittest.TestCase):
    def test_ten_mon_HOAN_TOAN_bia_thi_lop_nay_KHONG_bat_duoc(self):
        """Giới hạn đã biết, chốt lại để không ai tưởng lớp này bắt được mọi thứ.

        Phép so chuỗi với thực đơn bắt được: món thật ngoài danh sách, giá không có thật, món mang
        nhãn cần tránh. Nó KHÔNG bắt được một cái tên không tồn tại dưới bất kỳ dạng nào.

        Giảm nhẹ: `reply.items` và thẻ giỏ vẫn tất định, nên món bịa không đặt được. Test này đỏ khi
        có ai làm lớp này mạnh hơn — và đó là tin tốt, cập nhật test.
        """
        text = "Mình gợi ý Bò sốt tiêu đen Hoàng Gia (75.000đ) ạ."
        self.assertEqual(verify(text, [PHO["id"]], [PHO], ITEMS, []), [])


if __name__ == "__main__":
    unittest.main()
