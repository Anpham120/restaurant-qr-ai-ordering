"""Đích của ca truy hồi phải là đoạn mà hệ thống THẬT SỰ xếp hạng.

Vì sao có tệp này. Bộ đo và runtime đếm kho theo hai hàm khác nhau:

    doan_toan_kho()   182 đoạn   ← runtime xếp hạng đúng ngần này
    CS.corpus()       189 đoạn   ← bộ chọn của tập đánh giá thấy ngần này

Chênh đúng **7 đoạn mở đầu** (`#0`, mục không có tiêu đề). `doan_toan_kho()` bỏ
chúng có chủ ý: một mục không tiêu đề là phần dẫn nhập, nó mô tả TÀI LIỆU chứ
không trả lời câu nào.

Hậu quả nếu không ai canh: một ca có `expected` trỏ **chỉ** vào một trong bảy
đoạn đó thì **không bao giờ đạt được** — hệ thống không có đường trả về nó. Và
một ca có `forbidden` trỏ chỉ vào chúng thì tiêu chí đó **vô hiệu**: nó cấm một
thứ vốn không thể xuất hiện.

Cả hai đều là lỗi IM LẶNG. Ca thứ nhất trông như hệ thống kém; ca thứ hai trông
như hệ thống an toàn. Không cái nào làm test đỏ.

Hôm kiểm lần đầu: **0 ca dính cả hai kiểu**. Tệp này giữ cho con số đó ở 0.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

GOC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(GOC / "ai" / "app"))
sys.path.insert(0, str(Path(__file__).parent))

from rag.chunker import doan_toan_kho   # noqa: E402
import chunk_selectors as CS            # noqa: E402


def _ca() -> list[dict]:
    duong = Path(__file__).parent / "retrieval_cases.json"
    return json.loads(duong.read_text(encoding="utf-8-sig"))["cases"]


class DichPhaiXepHangDuoc(unittest.TestCase):
    """Ba khẳng định, và khẳng định thứ ba là khẳng định thật sự cần."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.xep_hang = {c.chunk_id for c in doan_toan_kho(GOC / "ai" / "knowledge")}
        cls.bo_do = {c.chunk_id for c in CS.corpus()}
        cls.ca = _ca()

    def test_bo_do_khong_thieu_doan_nao_runtime_co(self):
        """Chiều này mới là chiều nguy hiểm hơn: bộ đo KHÔNG được hẹp hơn runtime.

        Bộ đo rộng hơn thì có đích không với tới được — thấy bằng test dưới. Bộ
        đo hẹp hơn thì có đoạn runtime trả về mà bộ đo không biết tên, và mọi ca
        chạm nó bị chấm sai mà không ai truy được.
        """
        thieu = sorted(self.xep_hang - self.bo_do)
        self.assertEqual(thieu, [], f"bộ đo thiếu {len(thieu)} đoạn runtime có: {thieu[:5]}")

    def test_chenh_lech_dung_bang_doan_mo_dau(self):
        """Chênh lệch phải giải thích được, không phải một con số lạ.

        Nếu chênh lệch chứa thứ khác `#0` thì `doan_toan_kho()` đang bỏ một loại
        đoạn mà không ai biết, và đó là lúc phải đọc lại chunker.
        """
        thua = sorted(self.bo_do - self.xep_hang)
        khong_phai_mo_dau = [x for x in thua if not x.endswith("#0")]
        self.assertEqual(
            khong_phai_mo_dau, [],
            f"bộ đo thừa đoạn KHÔNG phải đoạn mở đầu: {khong_phai_mo_dau}")

    def test_khong_ca_nao_co_dich_ngoai_tam_xep_hang(self):
        """Khẳng định chính: mọi ca phải ĐẠT ĐƯỢC, và mọi tiêu chí cấm phải CÓ HIỆU LỰC."""
        khong_the, cam_vo_hieu = [], []
        for c in self.ca:
            ten = c.get("case_id") or c.get("family") or c.get("query", "")[:30]
            if c.get("expected"):
                dich = CS.select_many(c["expected"])
                if dich and not (dich & self.xep_hang):
                    khong_the.append(ten)
            if c.get("forbidden"):
                cam = CS.select_many(c["forbidden"])
                if cam and not (cam & self.xep_hang):
                    cam_vo_hieu.append(ten)

        self.assertEqual(
            khong_the, [],
            f"{len(khong_the)} ca có ĐÍCH nằm ngoài tầm xếp hạng nên KHÔNG BAO GIỜ đạt được: "
            f"{khong_the[:5]}")
        self.assertEqual(
            cam_vo_hieu, [],
            f"{len(cam_vo_hieu)} ca có tiêu chí CẤM vô hiệu — cấm một thứ không thể xuất hiện: "
            f"{cam_vo_hieu[:5]}")


if __name__ == "__main__":
    unittest.main()
