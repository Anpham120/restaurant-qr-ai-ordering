# -*- coding: utf-8 -*-
"""Test cho tập đánh giá truy hồi và bộ kiểm của nó — HAI CHIỀU.

Vì sao bộ kiểm cần test
-----------------------
`validate_retrieval_cases.py` là một thước đo, và **thước đo cũng phải chứng minh được mình
đúng**. Bài học đắt nhất của dự án là thước đo sai 3 lần trước khi hệ thống sai — và cả 3 lần đều
theo chiều **bịa ra lỗi không có**.

Nên mỗi loại lỗi có hai chiều:
    chiều 1   ca viết sai kiểu đó phải bị BẮT
    chiều 2   tập ca THẬT phải XANH — nếu bộ kiểm chấm đỏ mọi thứ thì chiều 1 vô nghĩa

    python -m unittest discover -s ai/evaluation -p "test_*.py"
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_retrieval_split import GATE_FAMILIES, build as build_split  # noqa: E402
from chunk_selectors import (  # noqa: E402
    SelectorError,
    corpus,
    select_chunk_ids,
    select_many,
    validate_selector,
)
from validate_retrieval_cases import check  # noqa: E402

CASES = json.loads((HERE / "retrieval_cases.json").read_text(encoding="utf-8-sig"))["cases"]
SPLIT = json.loads((HERE / "retrieval_split.json").read_text(encoding="utf-8-sig"))


def ca(**kwargs) -> dict:
    """Một ca hợp lệ, để test đổi đúng một chỗ rồi xem bộ kiểm có bắt không."""
    base = {
        "id": "thu-01",
        "family": "kb-thu",
        "query": "Món nướng có những gì?",
        "expected": [{"topic_keys_any": ["method_grilled"]}],
        "forbidden": [{"topic_keys_any": ["method_steamed"]}],
        "expect_nothing": False,
        "why": "Ca thử, cần đủ tám từ để qua phép kiểm độ dài của lời giải thích này.",
    }
    base.update(kwargs)
    return base


class TapCaTHATPhaiXANH(unittest.TestCase):
    """Chiều 2, và nó phải đứng đầu tệp: bộ kiểm chấm đỏ mọi thứ thì mọi test khác vô nghĩa."""

    def test_khong_van_de_nao(self):
        self.assertEqual(check(CASES), [])

    def test_ca_thu_hop_le_thi_xanh(self):
        self.assertEqual(check([ca()]), [])


class BoKiemBatDuocChinLoaiLoi(unittest.TestCase):
    def _bat(self, case: dict, cum: str) -> None:
        loi = check([case])
        self.assertTrue(loi, f"KHÔNG bắt được: {case.get('id')}")
        self.assertTrue(
            any(cum.lower() in l.lower() for l in loi),
            f"bắt được nhưng thông báo không nói {cum!r}: {loi}",
        )

    def test_1_thieu_truong(self):
        thieu = ca()
        del thieu["forbidden"]
        self._bat(thieu, "thiếu trường")

    def test_2_ma_ca_trung(self):
        loi = check([ca(), ca()])
        self.assertTrue(any("trùng" in l for l in loi))

    def test_3_cau_hoi_trung(self):
        loi = check([ca(id="a"), ca(id="b")])
        self.assertTrue(any("câu hỏi trùng" in l for l in loi))

    def test_4_expected_tro_vao_cho_khong_ton_tai(self):
        self._bat(ca(expected=[{"topic_keys_any": ["method_khong_co_that"]}]),
                  "không tồn tại")

    def test_5_forbidden_vo_nghia(self):
        self._bat(ca(forbidden=[{"topic_keys_any": ["khong_co_khoa_nay"]}]), "vô nghĩa")

    def test_6_expected_va_forbidden_giao_nhau(self):
        """Loại tinh nhất: hai điều kiện dùng cách chọn khác nhau mà trỏ cùng đoạn.

        Đọc bằng mắt thì không thấy — chỉ thấy khi GIẢI cả hai rồi so giao. Đây đúng lỗi đã có
        trong ca `kb-collision-02` bản đầu của tôi.
        """
        self._bat(
            ca(expected=[{"doc_id_prefix": "kb.method."}],
               forbidden=[{"topic_keys_any": ["method_grilled"]}]),
            "giao nhau",
        )

    def test_7_expect_nothing_mau_thuan(self):
        self._bat(ca(expect_nothing=True), "mâu thuẫn")
        self._bat(ca(expected=[], expect_nothing=False), "không đòi gì")

    def test_8_expected_qua_rong(self):
        """Ca đòi nửa kho là ca không phân biệt được gì — mọi bộ truy hồi đều 'đúng'."""
        self._bat(ca(expected=[{"doc_id_prefix": "kb."}], forbidden=[]), "quá nhiều")

    def test_9_why_qua_ngan(self):
        self._bat(ca(why="ngắn quá"), "why")


class DieuKienChonLaTRUYVANKhongPhaiDanhSach(unittest.TestCase):
    def test_khoa_dieu_kien_go_sai_thi_BAO_LOI(self):
        """KHÔNG bỏ qua khóa lạ. `topic_key_any` thiếu chữ `s` mà bị bỏ qua thì ca đó lặng lẽ
        đòi 'mọi đoạn' và nó XANH mãi mãi."""
        with self.assertRaises(SelectorError):
            validate_selector({"topic_key_any": ["method_grilled"]})

    def test_khoa_ghi_chu_bi_bo_qua(self):
        a = select_chunk_ids({"topic_keys_any": ["method_grilled"]})
        b = select_chunk_ids({"topic_keys_any": ["method_grilled"], "_why": "ghi chú"})
        self.assertEqual(a, b)

    def test_cac_khoa_ket_hop_bang_AND(self):
        ca_tai_lieu = select_chunk_ids({"topic_keys_any": ["method_grilled"]})
        mot_muc = select_chunk_ids(
            {"topic_keys_any": ["method_grilled"], "heading_any": ["Danh sách món"]}
        )
        self.assertTrue(mot_muc < ca_tai_lieu, "thêm điều kiện phải THU HẸP tập")
        self.assertEqual(len(mot_muc), 1)

    def test_HOP_cua_nhieu_dieu_kien(self):
        a = select_chunk_ids({"topic_keys_any": ["method_grilled"]})
        b = select_chunk_ids({"topic_keys_any": ["region_central"]})
        self.assertEqual(select_many([{"topic_keys_any": ["method_grilled"]},
                                      {"topic_keys_any": ["region_central"]}]), a | b)

    def test_chi_muc_KHONG_chua_doan_verbatim(self):
        """Nền tảng của ba họ `expect_nothing`. Nếu đoạn verbatim lọt vào chỉ mục thì ba họ đó
        đo một điều không còn đúng."""
        for c in corpus():
            self.assertEqual(c.answer_mode, "synthesize")


class PhepChiaBaNhom(unittest.TestCase):
    def test_moi_ho_thuoc_dung_MOT_nhom(self):
        g, d, t = (set(SPLIT[k]) for k in ("gate_families", "dev_families", "test_families"))
        self.assertEqual(g & d, set())
        self.assertEqual(g & t, set())
        self.assertEqual(d & t, set(), "họ ở cả phát triển và niêm phong = rò rỉ tập niêm phong")

    def test_moi_ho_deu_duoc_gan(self):
        tat_ca = {c["family"] for c in CASES}
        gan = set(SPLIT["gate_families"]) | set(SPLIT["dev_families"]) | set(SPLIT["test_families"])
        self.assertEqual(tat_ca, gan)

    def test_nhom_CHOT_dung_ba_ho_do_viec_biet_khi_nao_KHONG_tra_loi(self):
        """Ba họ này là chốt vì chúng là thứ DUY NHẤT bắt được một bộ truy hồi luôn trả 5 đoạn."""
        self.assertEqual(set(SPLIT["gate_families"]), GATE_FAMILIES)
        gate_cases = [c for c in CASES if c["family"] in GATE_FAMILIES]
        self.assertTrue(gate_cases)
        for c in gate_cases:
            self.assertTrue(
                c["expect_nothing"],
                f"{c['id']}: ca nhóm chốt phải là ca `expect_nothing` — nhóm chốt của tập này đo "
                "đúng việc biết KHI NÀO không trả lời",
            )

    def test_phep_chia_TAT_DINH_giua_hai_lan_goi(self):
        self.assertEqual(build_split(CASES), build_split(CASES))

    def test_khong_dung_random_shuffle(self):
        """`random.shuffle` với seed cũng tất định nhưng phụ thuộc PHIÊN BẢN Python — Python đổi
        thuật toán thì phép chia đổi theo và tập niêm phong lặng lẽ trộn vào tập phát triển.

        Kiểm bằng AST, KHÔNG quét chuỗi. Bản đầu quét chuỗi và nó đỏ vì `random.shuffle` xuất hiện
        trong chính chú thích giải thích VÌ SAO không dùng nó. Đây là lần thứ ba cùng lỗi đó trong
        dự án (test điểm vào Dockerfile, test tên trường trong schema), nên nó đáng thành nguyên
        tắc: **quét chuỗi trên mã nguồn thì luôn bắt cả phần giải thích.**
        """
        import ast

        tree = ast.parse((HERE / "build_retrieval_split.py").read_text(encoding="utf-8"))
        nhap = {
            n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
        } | {
            a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
        }
        self.assertNotIn("random", nhap, "phép chia không được phụ thuộc `random`")
        self.assertIn("hashlib", nhap, "phép chia phải dùng hash để tất định qua mọi phiên bản")

    def test_tap_niem_phong_chua_duoc_mo(self):
        """Khi mở, đặt `sealed_opened: true` VÀ ghi ngày. Tập 119 ca đã mất tính held-out vì được
        mở rồi sửa theo — test này để việc đó không lặp lại âm thầm."""
        self.assertIn("sealed_opened", SPLIT)
        if SPLIT["sealed_opened"]:
            self.skipTest("tập niêm phong đã mở — con số trên nó không còn là held-out")

    def test_tap_niem_phong_du_lon_de_con_so_co_nghia(self):
        t = set(SPLIT["test_families"])
        n = sum(1 for c in CASES if c["family"] in t)
        self.assertGreaterEqual(n, 20, f"tập niêm phong chỉ {n} ca — một ca lệch là quá nhiều %")


class TapCaPhanBietDuocHAIPhuongPhap(unittest.TestCase):
    """Tập đánh giá phải trả lời được câu 'BM25 hay embedding tốt hơn', không chỉ 'tốt bao nhiêu'."""

    def test_moi_chu_de_co_ca_dung_dung_TU_va_ca_dien_dat_KHAC(self):
        """Dạng A dùng đúng từ trong tài liệu (BM25 nên thắng); dạng B diễn đạt khác hoàn toàn
        (embedding nên thắng). Không có cả hai thì phép so chỉ xếp hạng, không giải thích."""
        theo_ho = {}
        for c in CASES:
            if c["expect_nothing"]:
                continue
            theo_ho.setdefault(c["family"], []).append(c)
        sinh_ra = [f for f in theo_ho if f.startswith("kb-") and f.split("-")[1] in (
            "region", "method", "ingredient", "flavour", "health", "occasion", "written")]
        self.assertTrue(sinh_ra)
        for f in sinh_ra:
            with self.subTest(f):
                self.assertEqual(
                    len(theo_ho[f]) % 2, 0,
                    f"họ {f} phải có SỐ CHẴN ca (mỗi chủ đề một cặp A/B)",
                )

    def test_co_ca_do_viec_KHONG_tra_loi(self):
        rong = [c for c in CASES if c["expect_nothing"]]
        self.assertGreaterEqual(
            len(rong), 8,
            "thiếu ca `expect_nothing` thì một bộ truy hồi LUÔN trả 5 đoạn cũng đạt điểm cao",
        )

    def test_moi_ca_co_forbidden_HOAC_la_ca_rong(self):
        """`forbidden@5` là chỉ số quan trọng nhất. Ca không có `forbidden` thì không góp gì cho nó."""
        thieu = [c["id"] for c in CASES if not c["forbidden"] and not c["expect_nothing"]]
        self.assertEqual(thieu, [], f"ca không có `forbidden` và không phải ca rỗng: {thieu[:5]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
