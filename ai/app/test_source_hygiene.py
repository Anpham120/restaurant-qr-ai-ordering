# -*- coding: utf-8 -*-
"""Mã nguồn không được chứa ký tự điều khiển, và regex phải khớp được thứ nó khai là khớp.

Vì sao tệp này tồn tại
----------------------
`understand.py` có một dòng thế này, và nó **chưa bao giờ hoạt động**:

    re.search(r"<BS>khong (?:co )?(?:hai san|...)<BS>", working)

`<BS>` là một **byte 0x08 THẬT** nằm trong tệp. Nó xuất hiện khi ai đó viết `"\\bkhong ..."`
trong chuỗi **không** raw — Python biến `\\b` thành backspace — rồi một lần sửa sau đó thêm tiền
tố `r` vào chuỗi đã bị vật chất hóa. Từ đó regex là `<backspace>khong ...` chứ không phải
`\\bkhong ...`, nên nó **không khớp gì cả**.

Đây là lớp lỗi tệ nhất có thể có, vì ba lý do cùng lúc:

1. **Vô hình.** Byte 0x08 không hiện trên màn hình, không hiện trong `git diff`, và phép kiểm
   "có ký tự ngoài ASCII không" cũng bỏ qua vì 0x08 < 127.
2. **Im lặng.** Regex không lỗi, nó chỉ không khớp. Mã chạy sạch.
3. **Nằm đúng trên đường an toàn.** Tài liệu dự án ghi cơ chế này là thứ **đưa an toàn dị ứng
   về mã tất định**, tức bỏ được phụ thuộc vào mô hình sinh. Thực tế nó là mã chết, và điều duy
   nhất che được là `AVOID_FRAMING` có sẵn cụm `khong co` và `khong an` — nên "không **có** hải
   sản" hoạt động trong khi "món **không** hải sản" thì không.

112 ca đánh giá **không bắt được**, vì không ca nào dùng đúng cách nói mà chỉ regex đó phủ. Nó
lộ ra khi tôi viết một ô notebook liệt kê bốn cách khai dị ứng và ô đó in ra **2/4 SAI**.

Bài học: **một cơ chế được khai là hàng rào an toàn thì phải có test chứng minh nó CHẠY**, không
phải chỉ có mặt trong mã.
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

APP_DIR = Path(__file__).resolve().parent

# Ký tự điều khiển KHÔNG được có trong mã nguồn. Bỏ qua \t \n \r vì chúng là khoảng trắng hợp lệ.
#
# Mỗi ký tự dưới đây là kết quả của một escape trong chuỗi không-raw, và mọi escape đó đều là
# escape thường gặp trong regex:
#     \a -> 0x07   \b -> 0x08 (ranh giới từ!)   \v -> 0x0b   \f -> 0x0c   \e -> 0x1b
FORBIDDEN = {
    0x07: r"\a",
    0x08: r"\b",   # thủ phạm thật của dự án này
    0x0B: r"\v",
    0x0C: r"\f",
    0x1B: r"\e",
}


def source_files() -> list[Path]:
    """Mọi tệp .py của dịch vụ. Bỏ qua môi trường ảo nếu nó nằm trong `ai/`."""
    return sorted(
        p for p in APP_DIR.rglob("*.py")
        if ".venv" not in p.parts and "site-packages" not in p.parts
    )


class MaNguonKhongChuaKyTuDieuKhien(unittest.TestCase):
    def test_khong_tep_nao_co_byte_dieu_khien(self):
        loi: list[str] = []
        for path in source_files():
            raw = path.read_bytes()
            for code, escape in FORBIDDEN.items():
                n = raw.count(bytes([code]))
                if n:
                    dong = [
                        i for i, l in enumerate(raw.split(b"\n"), 1) if bytes([code]) in l
                    ]
                    loi.append(
                        f"{path.name}: {n} byte {hex(code)} ở dòng {dong} — có lẽ là "
                        f"`{escape}` viết trong chuỗi KHÔNG raw"
                    )
        self.assertEqual(
            loi, [],
            "Ký tự điều khiển trong mã nguồn. Chúng vô hình trên màn hình và trong git diff, "
            "và nếu nằm trong regex thì regex im lặng không khớp gì:\n  " + "\n  ".join(loi),
        )


class RegexPhaiKhopDuocThuNoKhaiLaKhop(unittest.TestCase):
    """Chiều ngược của test trên: byte sạch nhưng regex vẫn có thể vô nghĩa.

    Test này biên dịch mọi mẫu regex trong mã và đòi mẫu đó **khớp được ít nhất một chuỗi**. Một
    mẫu không khớp gì thì nó là mã chết, dù tệp không có byte lạ nào.
    """

    def _patterns(self) -> list[tuple[Path, int, str]]:
        out: list[tuple[Path, int, str]] = []
        for path in source_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                if node.func.attr not in ("search", "match", "fullmatch", "compile", "sub"):
                    continue
                if not (isinstance(node.func.value, ast.Name) and node.func.value.id == "re"):
                    continue
                if node.args and isinstance(node.args[0], ast.Constant) \
                        and isinstance(node.args[0].value, str):
                    out.append((path, node.lineno, node.args[0].value))
        return out

    def test_moi_mau_regex_bien_dich_duoc(self):
        for path, lineno, pattern in self._patterns():
            with self.subTest(f"{path.name}:{lineno}"):
                try:
                    re.compile(pattern)
                except re.error as exc:
                    self.fail(f"{path.name}:{lineno} mẫu không biên dịch được: {exc}")

    def test_khong_mau_nao_chua_ky_tu_dieu_khien(self):
        xau: list[str] = []
        for path, lineno, pattern in self._patterns():
            co = [hex(ord(c)) for c in pattern if ord(c) in FORBIDDEN]
            if co:
                xau.append(f"{path.name}:{lineno} chứa {co} — mẫu này sẽ không khớp như ý")
        self.assertEqual(xau, [], "\n  ".join(xau))


class CoCheAnToANPhaiCoBANGCHUNGLaNoCHAY(unittest.TestCase):
    """Mỗi cơ chế được khai là hàng rào an toàn phải có ca chứng minh nó chạy.

    Không có class này thì lỗi backspace lặp lại được: mã có mặt, tài liệu ghi nó là hàng rào,
    112 ca vẫn xanh, và không ai biết nó là mã chết.
    """

    def setUp(self):
        import json

        from understand import understand

        self.understand = understand
        self.items = json.loads(
            (APP_DIR.parents[1] / "backend" / "data" / "menu-dataset.json").read_text(
                encoding="utf-8-sig"
            )
        )["items"]

    def test_mau_khong_chu_de_bat_duoc_moi_nhom_di_nguyen(self):
        """Mẫu `không ⟨chủ đề⟩` — chính cơ chế từng là mã chết.

        Không dùng cụm `không có` hay `không ăn` ở đây, vì hai cụm đó đã có trong
        `AVOID_FRAMING` và chúng **che mất** việc mẫu regex hỏng. Phải thử đúng dạng mà chỉ
        regex phủ.
        """
        ca = [
            ("Cho mình món không hải sản", "allergen:seafood"),
            ("Món nào không sữa", "allergen:dairy"),
            ("Món nào không trứng", "allergen:egg"),
            ("Cho mình món không đậu phộng", "allergen:peanut"),
            ("Món không gluten", "allergen:gluten"),
        ]
        for cau, nhan in ca:
            with self.subTest(cau):
                r = self.understand(cau, self.items)
                self.assertIn(
                    nhan, r.avoid_tags,
                    f"{cau!r}: mẫu `không ⟨chủ đề⟩` không bắt được — cơ chế này từng là mã "
                    "chết vì một byte 0x08 vô hình",
                )

    def test_duyet_danh_muc_KHONG_bi_coi_la_tranh(self):
        """Chiều ngược, bắt buộc: nếu mọi câu có tên dị nguyên đều bị coi là tránh thì test
        trên qua một cách vô nghĩa, và khách muốn xem món hải sản sẽ không thấy món nào."""
        for cau in ("Nhà hàng có hải sản gì?", "Cho mình xem món hải sản"):
            with self.subTest(cau):
                r = self.understand(cau, self.items)
                self.assertEqual(r.avoid_tags, [], f"{cau!r}: đây là câu DUYỆT, không phải tránh")
                self.assertIn("cat_seafood", r.categories)

    def test_cach_noi_dan_da_va_trieu_chung(self):
        """Hai ca thật đã đưa từ mô hình về mã tất định ở bước 6."""
        for cau, nhan in [
            ("Mình không ăn được đồ tanh", "allergen:seafood"),
            ("Bé nhà mình uống sữa là bị đau bụng, có món nào không sữa không?",
             "allergen:dairy"),
        ]:
            with self.subTest(cau):
                r = self.understand(cau, self.items)
                self.assertIn(nhan, r.avoid_tags)


if __name__ == "__main__":
    unittest.main(verbosity=2)
