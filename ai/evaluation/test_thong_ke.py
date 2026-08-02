# -*- coding: utf-8 -*-
"""Kiểm `thong_ke.py` bằng những giá trị TÍNH ĐƯỢC BẰNG TAY hoặc tra được ở sách.

Vì sao bộ kiểm này quan trọng hơn vẻ ngoài của nó: mọi kết luận so sánh trong Chương 4 đều đi qua
hai hàm ở đây. Công thức sai thì báo cáo khẳng định sai mà không có gì báo — và đó đúng là lớp lỗi
"thước đo sai trước hệ thống sai" đã xảy ra tám lần trong dự án.
"""
import unittest

from thong_ke import khoang_wilson, mcnemar, n_can_thiet


class KhoangWilson(unittest.TestCase):
    def test_gia_tri_tra_duoc_o_sach(self):
        """Wilson cho 8/8 với z = 1,96: cận dưới 0,6306, cận trên 1,0.

        Đây là ví dụ chuẩn hay gặp khi giới thiệu Wilson, dùng để chốt công thức.
        """
        k = khoang_wilson(8, 8)
        self.assertAlmostEqual(k.ty_le, 1.0)
        self.assertAlmostEqual(k.duoi, 0.6756, places=3)
        self.assertAlmostEqual(k.tren, 1.0)

    def test_ty_le_100_KHONG_cho_khoang_rong_bang_khong(self):
        """Đây là lý do dùng Wilson thay vì Wald.

        Công thức Wald `p ± z·√(p(1−p)/n)` cho nửa khoảng = 0 khi p = 1, tức khẳng định chắc chắn
        tuyệt đối từ 8 quan sát. Wilson phải cho khoảng có bề rộng thật.
        """
        k = khoang_wilson(8, 8)
        self.assertGreater(k.tren - k.duoi, 0.30,
                           "8/8 phải cho khoảng RỘNG, không phải khoảng điểm")

    def test_ty_le_0_cung_khong_suy_bien(self):
        k = khoang_wilson(0, 20)
        self.assertEqual(k.ty_le, 0.0)
        self.assertEqual(k.duoi, 0.0)
        self.assertGreater(k.tren, 0.0, "0/20 vẫn tương thích với tỷ lệ thật > 0")

    def test_n_lon_thi_khoang_hep_lai(self):
        hep = khoang_wilson(500, 1000).nua_rong
        rong = khoang_wilson(5, 10).nua_rong
        self.assertLess(hep, rong / 5)

    def test_n_bang_khong_khong_no(self):
        k = khoang_wilson(0, 0)
        self.assertEqual((k.ty_le, k.duoi, k.tren, k.n), (0.0, 0.0, 0.0, 0))


class KiemDinhMcNemar(unittest.TestCase):
    def test_hai_ben_giong_het_thi_p_bang_1(self):
        a = [True, False, True, True]
        r = mcnemar(a, list(a))
        self.assertEqual(r.n_lech, 0)
        self.assertEqual(r.p, 1.0)
        self.assertFalse(r.co_y_nghia)

    def test_chi_dem_o_nhung_ca_HAI_BEN_KHAC_NHAU(self):
        """Ca hai bên cùng đúng hoặc cùng sai KHÔNG mang thông tin so sánh.

        Đây là điểm cốt lõi của kiểm định ghép cặp, và là lý do nó nhạy hơn kiểm định hai mẫu độc
        lập trên cùng dữ liệu.
        """
        a = [True] * 90 + [True, True, False, False]
        b = [True] * 90 + [False, False, True, True]
        r = mcnemar(a, b)
        self.assertEqual(r.ca_hai_dung, 90)
        self.assertEqual(r.n_lech, 4, "chỉ 4 ca hai bên khác nhau")
        self.assertEqual(r.n, 94)

    def test_lech_han_mot_chieu_thi_co_y_nghia(self):
        """10 ca lệch, cả 10 cùng một chiều: p = 2/2^10 = 0,00195."""
        a = [True] * 10 + [True] * 20
        b = [False] * 10 + [True] * 20
        r = mcnemar(a, b)
        self.assertEqual((r.chi_a_dung, r.chi_b_dung), (10, 0))
        self.assertAlmostEqual(r.p, 2 / 1024, places=6)
        self.assertTrue(r.co_y_nghia)

    def test_lech_can_bang_thi_KHONG_co_y_nghia(self):
        a = [True] * 5 + [False] * 5
        b = [False] * 5 + [True] * 5
        r = mcnemar(a, b)
        self.assertEqual((r.chi_a_dung, r.chi_b_dung), (5, 5))
        self.assertEqual(r.p, 1.0)
        self.assertFalse(r.co_y_nghia)

    def test_it_ca_lech_thi_khong_ket_luan_duoc_du_lech_han_mot_chieu(self):
        """3 ca lệch cùng chiều cho p = 0,25 — chưa đủ.

        Ca này chốt rằng kiểm định KHÔNG bị đánh lừa bởi "toàn thắng" khi mẫu quá nhỏ.
        """
        a = [True] * 3 + [True] * 40
        b = [False] * 3 + [True] * 40
        r = mcnemar(a, b)
        self.assertAlmostEqual(r.p, 0.25, places=6)
        self.assertFalse(r.co_y_nghia)

    def test_hai_danh_sach_khac_do_dai_thi_NO(self):
        with self.assertRaises(ValueError):
            mcnemar([True, False], [True])

    def test_ket_luan_neu_dung_ten_ben_manh_hon(self):
        r = mcnemar([True] * 10 + [True] * 20, [False] * 10 + [True] * 20)
        self.assertIn("A", r.ket_luan("A", "B"))
        self.assertIn("có ý nghĩa", r.ket_luan("A", "B"))


class QuyMoMauCanThiet(unittest.TestCase):
    def test_khop_cong_thuc_chuan(self):
        """n = z²·p(1−p)/e². Với z = 1,96, p = 0,5, e = 0,05 -> 385."""
        self.assertEqual(n_can_thiet(0.05), 385)
        self.assertEqual(n_can_thiet(0.10), 97)

    def test_muon_hep_hon_thi_can_nhieu_hon(self):
        self.assertGreater(n_can_thiet(0.02), n_can_thiet(0.05))


class SoKhopBaoCao(unittest.TestCase):
    """Chốt rằng con số trong báo cáo khớp bằng chứng đo — không phải chép tay."""

    def test_mcnemar_tren_bang_chung_that(self):
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parent / "measurements" / "truy_hoi_so_sanh.json"
        if not p.exists():
            self.skipTest("chưa có bằng chứng đo")
        bo = json.loads(p.read_text(encoding="utf-8"))["so"]["bai_toan_1"]["NIÊM PHONG"]["bo"]
        if not bo.get("embedding", {}).get("hit1_theo_ca"):
            self.skipTest("bằng chứng chưa có hit1_theo_ca — chạy lại với --sealed")
        r = mcnemar(bo["embedding"]["hit1_theo_ca"], bo["bm25"]["hit1_theo_ca"])
        self.assertEqual(r.n, bo["embedding"]["n"], "n phải khớp số ca đã chấm")
        self.assertTrue(r.co_y_nghia,
                        "embedding vs bm25 phải có ý nghĩa — đây là kết luận chính của mục 4.2")


if __name__ == "__main__":
    unittest.main()
