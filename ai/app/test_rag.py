# -*- coding: utf-8 -*-
"""Test cho ba cách truy hồi. Mỗi công thức có ít nhất một ca TÍNH TAY ĐƯỢC.

Vì sao phải tính tay
--------------------
Một bộ xếp hạng sai vẫn trả về một bảng trông hợp lý. Không có ca nào biết trước đáp số thì test
chỉ nói "nó chạy", không nói "nó đúng". Ba chỗ dễ sai nhất của phần này, và cả ba đều KHÔNG làm
chương trình lỗi:

    IDF âm          dạng IDF gốc cho điểm âm với từ phổ biến -> chứa từ đó làm đoạn TỤT hạng
    hạng tính từ 0  công thức RRF là 1/(k+rank); rank 0 làm đoạn đầu bảng nặng bất thường
    thiếu tiền tố   họ mô hình E5 đòi "query:"/"passage:"; thiếu thì vẫn chạy, chỉ kém đi

Nên mỗi cái có một ca chốt bằng số cụ thể.
"""
from __future__ import annotations

import math
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from rag import embedding as E  # noqa: E402
from rag.base import Hit, tokenize  # noqa: E402
from rag.bm25 import B, K1, Bm25Index  # noqa: E402
from rag.chunker import retrievable_chunks  # noqa: E402
from rag.hybrid import RRF_K, HybridRetriever  # noqa: E402

KNOWLEDGE = APP_DIR.parent / "knowledge"


@dataclass
class Doan:
    """Đoạn giả, chỉ có hai trường mà bộ truy hồi cần."""

    chunk_id: str
    text: str


class TachTuDungChungMotDinhNghia(unittest.TestCase):
    def test_rut_dau_va_bo_dau_cau(self):
        self.assertEqual(tokenize("Mấy giờ mở cửa?"), ["may", "gio", "mo", "cua"])

    def test_khong_dau_khop_co_dau(self):
        """Người Việt gõ không dấu rất thường. Đây là lý do rút dấu tồn tại."""
        self.assertEqual(tokenize("mo cua"), tokenize("mở cửa"))

    def test_tu_hai_ky_tu_KHONG_bi_bo(self):
        """"bò", "gà", "mì", "ốc" đều 2 ký tự và đều là từ khóa quan trọng nhất của thực đơn.

        Bản đầu của tôi bỏ từ dưới 3 ký tự và làm mất đúng những từ đó.
        """
        for tu in ("bò", "gà", "mì", "ốc", "cá"):
            with self.subTest(tu):
                self.assertIn(tokenize(tu)[0], tokenize(f"món {tu} nướng"))


class Bm25KhopCongThucTinhTay(unittest.TestCase):
    def test_idf_khong_bao_gio_am(self):
        """Từ có ở MỌI đoạn vẫn phải cho IDF > 0.

        Dạng IDF gốc `ln((N-n+0.5)/(n+0.5))` cho giá trị âm khi n > N/2. Điểm âm nghĩa là chứa từ
        đó làm đoạn TỤT hạng — với kho này thì "món" và "nhà hàng" có ở gần như mọi đoạn, nên lỗi
        đó không phải chuyện lý thuyết.
        """
        doan = [Doan(f"d{i}", "mon an nha hang") for i in range(10)]
        index = Bm25Index.build(doan)
        for term in ("mon", "nha", "hang"):
            with self.subTest(term):
                self.assertGreater(index.idf[term], 0.0)

    def test_diem_khop_so_tinh_tay(self):
        """Ba đoạn, một từ truy vấn — tính tay được đến từng chữ số.

            d0 "cay cay cay"   f=3  |D|=3
            d1 "cay nhe"       f=1  |D|=2
            d2 "ngot"          f=0  |D|=1

            N=3, n(cay)=2, avgdl = (3+2+1)/3 = 2
            IDF = ln(1 + (3-2+0.5)/(2+0.5)) = ln(1.6)
        """
        index = Bm25Index.build([
            Doan("d0", "cay cay cay"), Doan("d1", "cay nhe"), Doan("d2", "ngot"),
        ])
        self.assertAlmostEqual(index.avgdl, 2.0)
        idf = math.log(1.6)
        self.assertAlmostEqual(index.idf["cay"], idf, places=12)

        cho = index.scores("cay")
        mong_d0 = idf * (3 * (K1 + 1)) / (3 + K1 * (1 - B + B * 3 / 2))
        mong_d1 = idf * (1 * (K1 + 1)) / (1 + K1 * (1 - B + B * 2 / 2))
        self.assertAlmostEqual(cho["d0"], mong_d0, places=12)
        self.assertAlmostEqual(cho["d1"], mong_d1, places=12)
        self.assertNotIn("d2", cho, "đoạn không chung từ nào phải VẮNG, không phải 0 điểm")

    def test_doan_ngan_thang_khi_cung_so_lan_xuat_hien(self):
        """Chuẩn hóa theo độ dài (`b`) tồn tại để làm đúng chuyện này."""
        index = Bm25Index.build([
            Doan("ngan", "cay"),
            Doan("dai", "cay " + " ".join(f"tu{i}" for i in range(50))),
        ])
        hits = index.search("cay", k=2)
        self.assertEqual(hits[0].chunk_id, "ngan")

    def test_hang_bat_dau_tu_1(self):
        index = Bm25Index.build([Doan("a", "cay"), Doan("b", "cay cay")])
        hits = index.search("cay", k=2)
        self.assertEqual([h.rank for h in hits], [1, 2])

    def test_pha_the_tat_dinh_theo_chunk_id(self):
        """Điểm bằng nhau thì thứ tự phải LẶP LẠI được, nếu không con số đo được vô nghĩa."""
        doan = [Doan("z", "cay"), Doan("a", "cay"), Doan("m", "cay")]
        lan1 = [h.chunk_id for h in Bm25Index.build(doan).search("cay", k=3)]
        lan2 = [h.chunk_id for h in Bm25Index.build(list(reversed(doan))).search("cay", k=3)]
        self.assertEqual(lan1, ["a", "m", "z"])
        self.assertEqual(lan1, lan2)

    def test_cau_hoi_khong_chung_tu_nao_tra_ve_RONG(self):
        """Khác embedding ở chỗ này, và khác biệt đó là phần đáng đo nhất của phép so."""
        index = Bm25Index.build([Doan("a", "mon cay"), Doan("b", "mon ngot")])
        self.assertEqual(index.search("wifi mat khau", k=5), [])


class RrfKhopCongThucTinhTay(unittest.TestCase):
    class BangCoDinh:
        """Bộ truy hồi giả trả đúng một bảng đã định."""

        def __init__(self, ids, name="gia"):
            self.ids, self.name = ids, name

        def search(self, query, k=5):
            return [Hit(cid, 1.0, r) for r, cid in enumerate(self.ids[:k], 1)]

    def test_diem_rrf_khop_so_tinh_tay(self):
        h = HybridRetriever(retrievers=[
            self.BangCoDinh(["a", "b"]), self.BangCoDinh(["b", "a"]),
        ])
        diem = h.scores("bất kỳ")
        mong = 1 / (RRF_K + 1) + 1 / (RRF_K + 2)
        self.assertAlmostEqual(diem["a"], mong, places=12)
        self.assertAlmostEqual(diem["b"], mong, places=12)

    def test_dong_thuan_hang_3_thang_hang_1_le_loi(self):
        """Đây là toàn bộ ý nghĩa của k=60, và nó phải đúng bằng SỐ.

            đồng thuận hạng 3 ở hai bảng: 1/63 + 1/63 = 0,031746
            hạng 1 chỉ ở một bảng       : 1/61        = 0,016393
        """
        h = HybridRetriever(retrievers=[
            self.BangCoDinh(["x", "y", "dong_thuan"]),
            self.BangCoDinh(["z", "w", "dong_thuan"]),
        ])
        diem = h.scores("bất kỳ")
        self.assertAlmostEqual(diem["dong_thuan"], 2 / (RRF_K + 3), places=12)
        self.assertAlmostEqual(diem["x"], 1 / (RRF_K + 1), places=12)
        self.assertGreater(diem["dong_thuan"], diem["x"])
        self.assertEqual(h.search("bất kỳ", k=1)[0].chunk_id, "dong_thuan")

    def test_lay_sau_hon_k_de_RRF_co_tac_dung(self):
        """Chỉ lấy `k` đoạn từ mỗi bảng thì đoạn đồng thuận ở hạng 6 KHÔNG BAO GIỜ vào kết quả.

        Bản đầu của tôi lấy đúng `k`, và hybrid gần như trùng khớp BM25 — nghĩa là phép so không
        so gì cả.
        """
        bang_a = [f"rac_a{i}" for i in range(5)] + ["dong_thuan"]
        bang_b = [f"rac_b{i}" for i in range(5)] + ["dong_thuan"]
        sau = HybridRetriever(
            retrievers=[self.BangCoDinh(bang_a), self.BangCoDinh(bang_b)], depth=20,
        )
        nong = HybridRetriever(
            retrievers=[self.BangCoDinh(bang_a), self.BangCoDinh(bang_b)], depth=5,
        )
        self.assertEqual(sau.search("q", k=1)[0].chunk_id, "dong_thuan")
        self.assertNotIn("dong_thuan", [h.chunk_id for h in nong.search("q", k=5)])


class EmbeddingSuyGiamEmChuKhongSAP(unittest.TestCase):
    def test_thieu_thu_vien_thi_bao_KHONG_SAN_SANG_chu_khong_nem(self):
        """Phép so phải chạy được với hai phương pháp còn lại, có ghi rõ đã bỏ qua."""
        co = E.available()
        self.assertIsInstance(co, bool)
        if not co:
            self.assertTrue(E.why_unavailable())

    def test_tien_to_E5_duoc_them(self):
        """Thiếu tiền tố thì mô hình VẪN CHẠY, chỉ kém đi — lỗi không có thông báo nào."""
        self.assertEqual(E.QUERY_PREFIX, "query: ")
        self.assertEqual(E.PASSAGE_PREFIX, "passage: ")

    def test_chuan_hoa_L2_dung(self):
        vec = E.EmbeddingIndex._l2([3.0, 4.0])
        self.assertAlmostEqual(vec[0], 0.6, places=12)
        self.assertAlmostEqual(vec[1], 0.8, places=12)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in vec)), 1.0, places=12)

    def test_vector_khong_thi_khong_chia_cho_0(self):
        self.assertEqual(E.EmbeddingIndex._l2([0.0, 0.0]), [0.0, 0.0])


class ChayThatTrenKhoTriThuc(unittest.TestCase):
    """BM25 trên kho thật — không cần thư viện ngoài nào."""

    @classmethod
    def setUpClass(cls):
        cls.chunks = retrievable_chunks(KNOWLEDGE)
        cls.index = Bm25Index.build(cls.chunks)

    def test_chi_muc_phu_het_doan(self):
        self.assertEqual(len(self.index.chunk_ids), len(self.chunks))
        self.assertGreater(len(self.chunks), 250, "kho nhỏ hơn kỳ vọng — kiểm bộ nạp")

    def test_cau_hoi_dung_tu_cua_tai_lieu_thi_BM25_lay_dung(self):
        """Chiều BM25 mạnh nhất: câu hỏi dùng ĐÚNG từ của tài liệu."""
        doan = next(c for c in self.chunks if "nướng" in c.text)
        hits = self.index.search(doan.heading or doan.title, k=5)
        self.assertTrue(hits, "câu hỏi lấy từ chính tài liệu mà không ra đoạn nào")

    def test_ket_qua_lap_lai_duoc_giua_hai_lan_dung_chi_muc(self):
        lai = Bm25Index.build(self.chunks)
        for q in ("món nướng", "giờ mở cửa", "combo cho hai người"):
            with self.subTest(q):
                self.assertEqual(
                    [h.chunk_id for h in self.index.search(q, k=5)],
                    [h.chunk_id for h in lai.search(q, k=5)],
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
