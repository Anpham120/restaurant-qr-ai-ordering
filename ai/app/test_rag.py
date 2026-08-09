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

import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from rag import embedding as E  # noqa: E402
from rag.base import Hit, tokenize  # noqa: E402
from rag.bm25 import B, K1, Bm25Index  # noqa: E402
from rag.chunker import doan_toan_kho, retrievable_chunks  # noqa: E402
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

    def test_tien_to_KHOP_HO_MO_HINH_dang_dung(self):
        """Sai tiền tố thì mô hình VẪN CHẠY, chỉ kém đi — lỗi không có thông báo nào.

        Và nó hỏng theo CẢ HAI chiều: họ E5 thiếu tiền tố thì kém, họ BGE thừa tiền tố thì cũng
        kém. Nên phép kiểm không chốt một chuỗi cố định mà chốt **quan hệ giữa mô hình và tiền tố**
        — có vậy thì đổi mô hình mới không âm thầm giữ lại tiền tố của mô hình cũ.
        """
        self.assertIn(E.MODEL_NAME, E.TIEN_TO, "mô hình chưa khai trong bảng tiền tố")
        self.assertEqual((E.QUERY_PREFIX, E.PASSAGE_PREFIX), E.TIEN_TO[E.MODEL_NAME])

    def test_ho_BGE_khong_dung_tien_to_ho_E5_thi_co(self):
        """Chốt nội dung bảng, không chỉ chốt tính nhất quán của nó.

        Không có ca này thì một bảng sai đều (mọi mô hình đều `("", "")`) vẫn qua test trên.
        """
        self.assertEqual(E.TIEN_TO["BAAI/bge-m3"], ("", ""))
        for ten in ("intfloat/multilingual-e5-small", "intfloat/multilingual-e5-base"):
            self.assertEqual(E.TIEN_TO[ten], ("query: ", "passage: "))

    def test_chuan_hoa_L2_dung(self):
        vec = E.EmbeddingIndex._l2([3.0, 4.0])
        self.assertAlmostEqual(vec[0], 0.6, places=12)
        self.assertAlmostEqual(vec[1], 0.8, places=12)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in vec)), 1.0, places=12)

    def test_vector_khong_thi_khong_chia_cho_0(self):
        self.assertEqual(E.EmbeddingIndex._l2([0.0, 0.0]), [0.0, 0.0])


class DemVectorPhaiTU_CHOI_Khi_KhongKhopKho(unittest.TestCase):
    """Bộ đệm vector: sai chỗ nào cũng phải dẫn tới TÍNH LẠI, không bao giờ tới vector lệch.

    Vì sao lớp này tồn tại
    ----------------------
    Đệm vector cắt thời gian khởi động container từ 97,3 giây xuống 19,0 giây (đo thật: 61,7 giây là
    mã hóa 425 đoạn). Nhưng nó mở ra đúng một lỗi mới, và lỗi đó là loại nặng nhất có thể ở đây:

        vector không khớp kho -> hệ thống VẪN trả 5 đoạn, VẪN có điểm, chỉ trả SAI đoạn.
        Không lỗi, không log, không cách nào biết trừ khi so từng câu trả lời.

    Nên mọi test dưới đây kiểm cùng một bất biến: **không chắc chắn thì trả `None`** (tức tính lại).
    Chậm là hậu quả chấp nhận được; trả sai thì không.

    Không cần `sentence-transformers`: `doc_dem` là phép so hàm băm và đọc JSON thuần.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "vectors.json"
        self.cu = os.environ.get(E._DEM_PATH_ENV)
        os.environ[E._DEM_PATH_ENV] = str(self.path)

    def tearDown(self):
        if self.cu is None:
            os.environ.pop(E._DEM_PATH_ENV, None)
        else:
            os.environ[E._DEM_PATH_ENV] = self.cu
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _ghi(self, texts, vectors, *, normalize=True, use_prefix=True, khoa=None):
        self.path.write_text(
            json.dumps({
                "khoa": khoa or E._khoa(texts, normalize=normalize, use_prefix=use_prefix),
                "vectors": vectors,
            }),
            encoding="utf-8",
        )

    def test_khop_thi_dung_dem(self):
        texts = ["passage: a", "passage: b"]
        self._ghi(texts, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(
            E.doc_dem(texts, normalize=True, use_prefix=True), [[1.0, 0.0], [0.0, 1.0]]
        )

    def test_doi_MOT_ky_tu_trong_kho_thi_TU_CHOI(self):
        """Khóa là hàm băm NỘI DUNG, nên sửa một chữ trong một tài liệu là đủ để vô hiệu đệm."""
        self._ghi(["passage: a", "passage: b"], [[1.0, 0.0], [0.0, 1.0]])
        self.assertIsNone(E.doc_dem(["passage: a", "passage: B"],
                                    normalize=True, use_prefix=True))

    def test_them_doan_thi_TU_CHOI(self):
        self._ghi(["passage: a"], [[1.0, 0.0]])
        self.assertIsNone(E.doc_dem(["passage: a", "passage: b"],
                                    normalize=True, use_prefix=True))

    def test_doi_co_normalize_thi_TU_CHOI(self):
        """Hai cờ này ĐỔI vector, nên chúng phải nằm trong khóa.

        Thiếu chúng thì phép ablation "tắt chuẩn hóa" lặng lẽ đọc lại vector ĐÃ chuẩn hóa và báo
        rằng tắt nó không mất gì — một phép đo tự bác bỏ chính nó.
        """
        texts = ["passage: a"]
        self._ghi(texts, [[1.0, 0.0]], normalize=True)
        self.assertIsNone(E.doc_dem(texts, normalize=False, use_prefix=True))
        self.assertIsNone(E.doc_dem(texts, normalize=True, use_prefix=False))

    def test_tep_hong_thi_TU_CHOI_chu_khong_nem(self):
        self.path.write_text("{khong phai json", encoding="utf-8")
        self.assertIsNone(E.doc_dem(["passage: a"], normalize=True, use_prefix=True))

    def test_so_vector_lech_so_doan_thi_TU_CHOI(self):
        """Khóa khớp mà số vector lệch: chỉ xảy ra khi tệp bị sửa tay, và vẫn phải từ chối."""
        texts = ["passage: a", "passage: b"]
        self._ghi(texts, [[1.0, 0.0]])          # khóa đúng, thiếu một vector
        self.assertIsNone(E.doc_dem(texts, normalize=True, use_prefix=True))

    def test_khong_dat_bien_moi_truong_thi_KHONG_doc_va_KHONG_ghi(self):
        """Không có đường dẫn mặc định, có chủ ý.

        Mã tự đoán một đường dẫn thì lúc build ghi chỗ này và lúc chạy đọc chỗ khác — hậu quả là
        im lặng tính lại 61 giây mỗi lần khởi động trong khi mọi người tin là đã có đệm.
        """
        os.environ.pop(E._DEM_PATH_ENV, None)
        self.assertIsNone(E.doc_dem(["passage: a"], normalize=True, use_prefix=True))
        with self.assertRaises(RuntimeError):
            E.ghi_dem([])

    def test_dem_tinh_theo_doan_toan_kho_thi_luc_chay_DUNG_DUOC(self):
        """Bất biến ĐÃ BỊ VI PHẠM một lần, và đây là test lẽ ra phải có trước.

        Bước build tính vector cho `retrievable_chunks(...)` — 425 đoạn. Lúc chạy `answer.py` xếp
        hạng `doan_toan_kho(...)` — tập đã lọc `heading`. Hai tập khác nhau nên hàm băm khác nhau,
        đệm KHÔNG khớp, và container mã hóa lại toàn bộ mỗi lần khởi động: 60 giây.

        Không có gì báo, vì đệm làm ĐÚNG thiết kế: khóa lệch thì tính lại. Nó im lặng làm điều đúng
        và che mất việc nó chưa từng được dùng. Phát hiện được chỉ vì đo thời gian khởi động thật
        rồi thấy nó không giảm.

        Test này ép đúng chuỗi đó: ghi đệm theo tập của `doan_toan_kho`, rồi hỏi `doc_dem` bằng đúng
        cách `EmbeddingIndex.build` hỏi. Nó KHÔNG cần mô hình — chỉ cần hàm băm khớp, mà đó chính là
        thứ đã lệch.
        """
        doan = doan_toan_kho(KNOWLEDGE)
        self.assertTrue(doan, "kho rỗng thì test này không kiểm được gì")
        texts = [E.PASSAGE_PREFIX + c.text for c in doan]
        self._ghi(texts, [[0.0] * 3 for _ in texts])

        self.assertIsNotNone(
            E.doc_dem(texts, normalize=True, use_prefix=True),
            "đệm ghi theo `doan_toan_kho` mà `doc_dem` không nhận — hai bên đã lệch lại",
        )

        # Và chiều ngược lại: tập KHÔNG lọc `heading` phải bị từ chối, vì đó đúng là lỗi đã xảy ra.
        khong_loc = [E.PASSAGE_PREFIX + c.text for c in retrievable_chunks(KNOWLEDGE)]
        if len(khong_loc) != len(texts):
            self.assertIsNone(
                E.doc_dem(khong_loc, normalize=True, use_prefix=True),
                "đệm của tập đã lọc lại khớp tập chưa lọc — hàm băm không phân biệt được hai tập",
            )

    def test_Dockerfile_goi_rag_precompute_chu_khong_viet_lai_phep_loc(self):
        """Dockerfile phải gọi `rag.precompute`, không viết lại phép lọc đoạn.

        Viết lại phép lọc là chính xác cách hai bên đã lệch nhau. Một điểm vào dùng chung là cách sửa
        bằng cấu trúc; nhớ sửa hai chỗ thì không phải cách sửa.
        """
        text = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")
        if "sentence_transformers" not in text:
            self.skipTest("ảnh không có tầng embedding")
        self.assertIn("python -m rag.precompute", text)

        # Chỉ kiểm dòng LỆNH, không kiểm chú thích. Bản đầu của test này kiểm cả tệp, nên nó báo đỏ
        # vì chú thích GIẢI THÍCH lỗi cũ có nhắc tên hàm — tức test chặn đúng việc ghi lại lý do.
        # Một phép kiểm không phân biệt mã với văn xuôi sẽ dạy người sau xóa chú thích cho test xanh.
        lenh = [
            line for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        pham = [line for line in lenh if "retrievable_chunks" in line]
        self.assertEqual(
            pham, [],
            "dòng lệnh Dockerfile gọi `retrievable_chunks` — tức nó lại tự chọn tập đoạn thay vì "
            f"để `rag.precompute` dùng cùng `doan_toan_kho()` mà answer.py dùng: {pham}",
        )

    def test_Dockerfile_dat_dung_ten_bien_ma_ma_doc(self):
        """Tên biến ở Dockerfile phải TRÙNG tên mã đọc — lệch nhau là lỗi im lặng.

        Đây là bất biến hai-đầu, cùng loại với `COPY backend/data` và với tên mô hình embedding:
        một bên ghi, một bên đọc, và không có gì báo khi hai bên ghi khác tên.
        """
        text = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")
        if "sentence_transformers" not in text:
            self.skipTest("ảnh không có tầng embedding")
        self.assertIn(
            f"ENV {E._DEM_PATH_ENV}=",
            text,
            f"Dockerfile không đặt {E._DEM_PATH_ENV}, nên lúc chạy KHÔNG có đệm và container mất "
            "thêm ~62 giây mã hóa mỗi lần khởi động — im lặng.",
        )


class ChayThatTrenKhoTriThuc(unittest.TestCase):
    """BM25 trên kho thật — không cần thư viện ngoài nào."""

    @classmethod
    def setUpClass(cls):
        cls.chunks = retrievable_chunks(KNOWLEDGE)
        cls.index = Bm25Index.build(cls.chunks)

    def test_chi_muc_phu_het_doan(self):
        self.assertEqual(len(self.index.chunk_ids), len(self.chunks))
        # 180 sau khi bỏ 49 tài liệu sinh-theo-nhãn (chúng đóng góp 190 đoạn gần-trùng nhau).
        # Lý do đầy đủ ở `test_chunker.test_kho_du_lon_de_so_sanh_truy_hoi_co_nghia`.
        self.assertGreater(len(self.chunks), 180, "kho nhỏ hơn kỳ vọng — kiểm bộ nạp")

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
