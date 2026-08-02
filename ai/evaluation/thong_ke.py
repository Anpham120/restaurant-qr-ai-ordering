# -*- coding: utf-8 -*-
"""Khoảng tin cậy và kiểm định ý nghĩa — để mọi con số trong báo cáo có thể bảo vệ được.

Vì sao mô-đun này tồn tại
-------------------------
Báo cáo trước ghi *"embedding 60,87% so với BM25 39,13%"* và kết luận embedding tốt hơn. Người đọc
có quyền vặn lại hai câu, và cả hai đều đúng:

    "n bao nhiêu?"                  -> 46 ca. Nửa khoảng tin cậy 95% là ±13,9 điểm phần trăm.
    "chênh lệch đó có ý nghĩa không?" -> báo cáo không trả lời được, vì chưa kiểm định.

Một con số không kèm khoảng tin cậy thì không nói được gì về tổng thể; một phép so sánh không kèm
kiểm định thì không phân biệt được "thật sự khác nhau" với "khác nhau do may rủi".

Hai công cụ ở đây
-----------------
    khoang_wilson   khoảng tin cậy cho MỘT tỷ lệ
    mcnemar         kiểm định cho HAI phương pháp chạy trên CÙNG một tập ca

Vì sao Wilson chứ không phải công thức chuẩn thường gặp
-------------------------------------------------------
Công thức `p ± 1,96·√(p(1−p)/n)` (khoảng Wald) sai nặng khi `p` gần 0 hoặc 1, và khi `n` nhỏ. Ở đây
cả hai điều kiện đều xảy ra: nhiều phép đo cho tỷ lệ 100,00% hoặc 0,00%, và có tập chỉ 46 ca. Với
`p = 1,0` thì Wald cho khoảng rộng bằng 0 — tức khẳng định chắc chắn tuyệt đối từ một mẫu hữu hạn,
điều không đúng. Wilson không mắc lỗi đó.

Vì sao McNemar chứ không phải kiểm định t hai mẫu
--------------------------------------------------
Hai bộ truy hồi chạy trên **cùng một danh sách câu hỏi**, nên hai kết quả **không độc lập** — chúng
cùng dễ ở những câu dễ và cùng khó ở những câu khó. Kiểm định hai mẫu độc lập bỏ qua sự ghép cặp
này và cho kết quả kém nhạy. McNemar dùng đúng thông tin đó: nó chỉ đếm những câu mà **hai bên khác
nhau**, và hỏi liệu tỷ lệ giữa hai chiều lệch có khác 50/50 hay không.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Khoang:
    """Một tỷ lệ kèm khoảng tin cậy."""

    ty_le: float
    duoi: float
    tren: float
    n: int

    @property
    def nua_rong(self) -> float:
        """Nửa độ rộng, tính bằng điểm phần trăm — con số người đọc quan tâm nhất."""
        return (self.tren - self.duoi) / 2

    def __str__(self) -> str:
        return (f"{self.ty_le * 100:.2f}% "
                f"(KTC 95%: {self.duoi * 100:.2f}–{self.tren * 100:.2f}%, n = {self.n})")


def khoang_wilson(so_dung: float, n: int, z: float = 1.96) -> Khoang:
    """Khoảng tin cậy Wilson cho một tỷ lệ. `z = 1,96` là mức 95%.

    Ví dụ kiểm được bằng tay: 8/8 ca đúng cho khoảng 67,56–100,00%, KHÔNG phải 100–100%. Nói cách
    khác, tám ca đúng liên tiếp vẫn tương thích với một tỷ lệ thật thấp tới 67,56%.
    """
    if n <= 0:
        return Khoang(0.0, 0.0, 0.0, 0)
    p = so_dung / n
    den = 1 + z * z / n
    tam = (p + z * z / (2 * n)) / den
    nua = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return Khoang(p, max(0.0, tam - nua), min(1.0, tam + nua), n)


@dataclass(frozen=True)
class KetQuaMcNemar:
    """Kết quả kiểm định McNemar giữa hai phương pháp trên cùng tập ca."""

    chi_a_dung: int      # số ca A đúng, B sai
    chi_b_dung: int      # số ca B đúng, A sai
    ca_hai_dung: int
    ca_hai_sai: int
    p: float

    @property
    def n(self) -> int:
        return self.chi_a_dung + self.chi_b_dung + self.ca_hai_dung + self.ca_hai_sai

    @property
    def n_lech(self) -> int:
        """Số ca hai bên KHÁC nhau — đây là toàn bộ thông tin kiểm định dùng."""
        return self.chi_a_dung + self.chi_b_dung

    @property
    def co_y_nghia(self) -> bool:
        return self.p < 0.05

    def ket_luan(self, ten_a: str, ten_b: str) -> str:
        if self.n_lech == 0:
            return f"{ten_a} và {ten_b} cho kết quả GIỐNG HỆT trên cả {self.n} ca."
        manh = ten_a if self.chi_a_dung > self.chi_b_dung else ten_b
        if self.co_y_nghia:
            return (f"{manh} tốt hơn, và chênh lệch **có ý nghĩa thống kê** "
                    f"(McNemar p = {self.p:.4f} < 0,05; {self.n_lech}/{self.n} ca hai bên khác nhau).")
        return (f"{manh} nhỉnh hơn, nhưng chênh lệch **CHƯA đủ ý nghĩa thống kê** "
                f"(McNemar p = {self.p:.4f} ≥ 0,05; chỉ {self.n_lech}/{self.n} ca hai bên khác nhau).")


def _nhi_thuc_hai_phia(k: int, n: int) -> float:
    """Xác suất hai phía của kiểm định dấu nhị thức với p = 0,5.

    Dùng bản chính xác thay vì xấp xỉ chi-bình-phương vì `n_lech` ở đây thường nhỏ (dưới 25), mức
    mà xấp xỉ không còn tin được.
    """
    if n == 0:
        return 1.0
    k = min(k, n - k)
    duoi = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * duoi)


def mcnemar(dung_a: list[bool], dung_b: list[bool]) -> KetQuaMcNemar:
    """Kiểm định McNemar chính xác. Hai danh sách phải CÙNG thứ tự ca."""
    if len(dung_a) != len(dung_b):
        raise ValueError("hai danh sách phải cùng độ dài — đây là kiểm định GHÉP CẶP")
    a = sum(1 for x, y in zip(dung_a, dung_b) if x and not y)
    b = sum(1 for x, y in zip(dung_a, dung_b) if y and not x)
    ca_hai = sum(1 for x, y in zip(dung_a, dung_b) if x and y)
    khong = sum(1 for x, y in zip(dung_a, dung_b) if not x and not y)
    return KetQuaMcNemar(a, b, ca_hai, khong, _nhi_thuc_hai_phia(a, a + b))


def n_can_thiet(nua_rong_muon: float, p_uoc: float = 0.5) -> int:
    """Cần bao nhiêu ca để khoảng tin cậy 95% hẹp tới mức mong muốn.

    Dùng để trả lời "tập này cần lớn bao nhiêu" bằng SỐ thay vì bằng cảm giác. `p_uoc = 0,5` là
    trường hợp xấu nhất (khoảng rộng nhất), nên kết quả là cận trên an toàn.
    """
    z = 1.96
    return math.ceil(z * z * p_uoc * (1 - p_uoc) / (nua_rong_muon ** 2))
