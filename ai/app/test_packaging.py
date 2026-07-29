# -*- coding: utf-8 -*-
"""Mọi tệp dữ liệu mà mã lúc chạy đọc phải nằm TRONG thư mục Docker copy vào ảnh.

Vì sao có tệp này
-----------------
`ai/Dockerfile` copy đúng một thứ:

    COPY --chown=app:app ai ./ai      # chỉ có ai/, KHÔNG có backend/
    WORKDIR /app/ai

Nhưng mã lúc chạy từng đọc kho tri thức bằng đường dẫn ra ngoài `ai/`:

    FACTS_PATH = Path(__file__).parents[2] / "backend" / "data" / "restaurant-facts.json"
    #            /app/ai/app/answer.py → parents[2] = /app → /app/backend/data/...

`/app/backend/` không tồn tại trong ảnh. Và `load_facts()` xử lý thiếu tệp bằng `return {}`,
nên trong container **cả 24 chủ đề chính sách trả "chưa có dữ liệu"** — không lỗi, không log,
không ai biết. Khách hỏi giờ mở cửa và AI nói không biết, dù dữ liệu nằm trong repo.

Chỗ đọc đó nay đã hết: kho tri thức gộp về `ai/knowledge/`, tức NẰM TRONG phạm vi `COPY`. Đó
là cách sửa số 1 dưới đây — sửa cấu trúc. `menu-dataset.json` và `menu-tags.json` thì vẫn thuộc
backend thật (chúng seed cơ sở dữ liệu qua migration EF) nên chúng đi theo cách sửa số 2.

Đây đúng loại thoái hóa im lặng đã bắt được hai lần trong dự án này (`Request` nằm ngoài `try`
làm mọi lần gọi mô hình sập thay vì giữ câu trả lời tất định; kho tri thức bản cũ trích đoạn
nội bộ cho khách). Cả hai đều **không** bị test nào bắt, vì test chạy từ mã nguồn nơi mọi tệp
đều có mặt. **Ảnh Docker là môi trường duy nhất tệp bị thiếu, và không ai test ở đó.**

Test này thay chỗ đó: nó không dựng container (đắt và chậm), nó **đọc Dockerfile** và đối chiếu
với các đường dẫn mã thật sự dùng.

Cách sửa khi test đỏ — theo thứ tự ưu tiên:
  1. **Chuyển dữ liệu vào `ai/`.** Sửa cấu trúc, lỗi không quay lại được. Với kho tri thức thì
     đây là hướng đúng: `ai/knowledge/` đã nằm trong `ai/`.
  2. Thêm đường dẫn đó vào `COPY` của Dockerfile. Được, nhưng phải nhớ, nên yếu hơn cách 1.
  3. Nới danh sách miễn trong test. Chỉ khi tệp đó **không** cần lúc chạy (ví dụ tệp chỉ test
     dùng) — và phải ghi lý do.
"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parents[1]
DOCKERFILE = REPO_ROOT / "ai" / "Dockerfile"

# Mô-đun chỉ dùng khi test/khi phát triển, không nằm trên đường trả lời khách. Đường dẫn ra
# ngoài `ai/` trong các tệp này là chấp nhận được, vì chúng không bao giờ chạy trong container.
DEV_ONLY_PREFIXES = ("test_",)


def runtime_modules() -> list[Path]:
    """Các mô-đun THẬT SỰ chạy trong container (loại tệp test)."""
    return sorted(
        p
        for p in APP_DIR.rglob("*.py")
        if not p.name.startswith(DEV_ONLY_PREFIXES) and p.name != "__init__.py"
    )


def docker_copied_roots(dockerfile: Path | None = None) -> set[str]:
    """Đường dẫn nguồn mà Dockerfile copy vào ảnh, đọc TỪ Dockerfile.

    Đọc tệp thật thay vì viết cứng `{"ai"}`, để khi ai đó sửa Dockerfile thì test đi theo —
    một test viết cứng sẽ tiếp tục xanh sau khi Dockerfile đã đổi, và đó là test dối.

    Giữ **nguyên đường dẫn đầy đủ** (`backend/data`, không rút về `backend`), để `COPY
    backend/data` không vô tình hợp lệ hóa một chỗ đọc `backend/src`.
    """
    roots: set[str] = set()
    for line in (dockerfile or DOCKERFILE).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.upper().startswith("COPY "):
            continue
        parts = [p for p in stripped.split()[1:] if not p.startswith("--")]
        for src in parts[:-1]:  # phần tử cuối là đích
            roots.add(src.strip("./").rstrip("/"))
    return roots


def _flatten_div_chain(node: ast.BinOp) -> tuple[ast.AST, list[str]]:
    """`ROOT / "backend" / "data" / "x.json"` → (nút ROOT, ["backend", "data", "x.json"]).

    Cần ghép lại cả chuỗi vì chỉ mắt đầu (`"backend"`) là không đủ để so với `COPY backend/data`.
    """
    parts: list[str] = []
    cur: ast.AST = node
    while (
        isinstance(cur, ast.BinOp)
        and isinstance(cur.op, ast.Div)
        and isinstance(cur.right, ast.Constant)
        and isinstance(cur.right.value, str)
    ):
        parts.append(cur.right.value.strip("/"))
        cur = cur.left
    return cur, list(reversed(parts))


def _is_escape_root(node: ast.AST) -> bool:
    """`<gì đó>.parents[N]` với N ≥ 2 — tức đã leo ra ngoài `ai/`.

    `parents[0]` là `ai/app`, `parents[1]` là `ai/`; cả hai vẫn nằm trong ảnh nên không sao.
    """
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "parents"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, int)
        and node.slice.value >= 2
    )


def outside_paths(module: Path, dockerfile: Path | None = None) -> list[tuple[int, str]]:
    """Tìm chỗ mã leo ra ngoài `ai/` rồi ghép tên một thư mục gốc repo.

    Dò bằng AST chứ không bằng chuỗi, vì `grep "backend"` khớp cả chú thích và thông báo lỗi —
    báo động giả rồi người ta tắt test.

    Phải xử lý HAI dạng viết, vì mã thật có cả hai:

        answer.py         Path(__file__).resolve().parents[2] / "backend" / ...   (trực tiếp)
        llm_understand.py REPO_ROOT = ...parents[2]                               (qua biến)
                          DICT_PATH = REPO_ROOT / "backend" / ...

    Bản dò đầu tiên tôi viết chỉ bắt dạng một, và nó báo XANH trên cả hai vi phạm thật đang có
    trong mã. Một bộ dò báo xanh sai còn tệ hơn không có bộ dò, nên chỗ này phải có test tự
    kiểm ở dưới (`BoDoPhaiThatSuBatDuoc`).
    """
    tree = ast.parse(module.read_text(encoding="utf-8"))
    copied = docker_copied_roots(dockerfile)

    # Dạng 2: tên biến nào được gán từ một biểu thức đã leo ra ngoài `ai/`.
    escaped_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(_is_escape_root(sub) for sub in ast.walk(node.value)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                escaped_names.add(target.id)

    # Chỉ xét mắt NGOÀI CÙNG của mỗi chuỗi `/`, để đọc được đường dẫn đầy đủ chứ không chỉ mắt
    # đầu. Mắt ngoài cùng là mắt không làm `left` cho một mắt `/` nào khác.
    inner = {
        node.left
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
    }

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        if node in inner:
            continue
        base, parts = _flatten_div_chain(node)
        if not parts:
            continue
        if not (
            _is_escape_root(base)
            or (isinstance(base, ast.Name) and base.id in escaped_names)
        ):
            continue
        # Bỏ mắt cuối nếu nó là tên tệp — ta so THƯ MỤC với `COPY`.
        dirs = parts[:-1] if "." in parts[-1] else parts
        path = "/".join(dirs)
        if path and not any(path == c or path.startswith(c + "/") for c in copied):
            found.append((node.lineno, path))
    return found


class DuLieuLucChayPhaiNamTrongAnhDocker(unittest.TestCase):
    def test_dockerfile_van_chi_copy_thu_muc_ai(self):
        # Nếu Dockerfile bắt đầu copy thêm thư mục khác thì test dưới nới ra theo, nên phép
        # kiểm này chỉ để lời giải thích trong docstring không lạc hậu âm thầm.
        self.assertIn("ai", docker_copied_roots())

    def test_khong_mo_dun_luc_chay_nao_doc_ra_ngoai_ai(self):
        offenders: list[str] = []
        for module in runtime_modules():
            for lineno, path in outside_paths(module):
                rel = module.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{rel}:{lineno} đọc {path}")
        self.assertEqual(
            offenders, [],
            "Các chỗ sau đọc dữ liệu NGOÀI `ai/`, mà Dockerfile chỉ copy `ai/` — trong "
            "container tệp sẽ thiếu và mã thoái hóa im lặng:\n  "
            + "\n  ".join(offenders)
            + "\nCách sửa tốt nhất: chuyển dữ liệu vào `ai/`. Xem docstring tệp này.",
        )


class BoDoPhaiThatSuBatDuoc(unittest.TestCase):
    """Test cho bộ dò, không cho hệ thống. Có vì bộ dò bản đầu đã báo xanh sai.

    Bản đầu chỉ bắt dạng `parents[2] / "backend"` viết liền, nên nó bỏ qua cả hai vi phạm thật
    đang có trong mã và báo OK. Test hai chiều là bắt buộc ở đây: một bộ dò luôn báo rỗng thì
    phép kiểm ở trên vô nghĩa, và một bộ dò báo bừa thì người ta sẽ tắt nó.
    """

    def _probe(self, source: str) -> list[tuple[int, str]]:
        """Dò trên một Dockerfile GIẢ chỉ copy `ai/`.

        Không được dùng Dockerfile thật ở đây. Nếu dùng, thì ngày ai đó thêm `COPY backend/data`
        vào Dockerfile, mấy test dưới sẽ tự trở thành rỗng nghĩa — chúng vẫn xanh nhưng không
        còn kiểm gì cả. Đó đúng là loại test dối mà cả tệp này tồn tại để chống.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "probe.py"
            path.write_text(source, encoding="utf-8")
            docker = Path(tmp) / "Dockerfile"
            docker.write_text("FROM x\nCOPY ai ./ai\n", encoding="utf-8")
            return outside_paths(path, docker)

    def test_bat_duoc_dang_viet_lien(self):
        hits = self._probe(
            "from pathlib import Path\n"
            'P = Path(__file__).resolve().parents[2] / "backend" / "data" / "x.json"\n'
        )
        self.assertEqual([h[1] for h in hits], ["backend/data"])

    def test_bat_duoc_dang_qua_bien(self):
        hits = self._probe(
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            'P = ROOT / "backend" / "data" / "x.json"\n'
        )
        self.assertEqual([h[1] for h in hits], ["backend/data"])

    def test_khong_bao_dong_gia_voi_duong_dan_trong_ai(self):
        # `parents[1]` là `ai/` — vẫn trong ảnh Docker, không được báo.
        hits = self._probe(
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            'P = ROOT / "knowledge"\n'
        )
        self.assertEqual(hits, [])

    def test_khong_bao_dong_gia_voi_thu_muc_dockerfile_co_copy(self):
        hits = self._probe(
            "from pathlib import Path\n"
            'P = Path(__file__).resolve().parents[2] / "ai" / "knowledge"\n'
        )
        self.assertEqual(hits, [])

    def test_copy_backend_data_khong_hop_le_hoa_backend_src(self):
        """Phần chính xác: `COPY backend/data` chỉ hợp lệ hóa đúng `backend/data`.

        Bản trước rút đường dẫn về tên thư mục gốc (`backend`), nên thêm một dòng `COPY
        backend/data` sẽ làm mọi chỗ đọc `backend/` bất kỳ đều xanh — kể cả `backend/src`, thứ
        vẫn không có trong ảnh.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            docker = Path(tmp) / "Dockerfile"
            docker.write_text(
                "FROM x\nCOPY ai ./ai\nCOPY backend/data ./backend/data\n", encoding="utf-8"
            )
            copied = docker_copied_roots(docker)
        self.assertEqual(copied, {"ai", "backend/data"})

        def allowed(path: str) -> bool:
            return any(path == c or path.startswith(c + "/") for c in copied)

        self.assertTrue(allowed("backend/data"), "backend/data phải được coi là có trong ảnh")
        self.assertFalse(allowed("backend/src"), "backend/src KHÔNG có trong ảnh, phải bị báo")

    def test_khong_bao_dong_gia_voi_chu_thich_va_thong_bao_loi(self):
        # Chuỗi "backend" trong chú thích và trong thông báo lỗi không phải đường dẫn.
        hits = self._probe(
            "# đọc từ backend/data nếu có\n"
            'MSG = "thiếu tệp ở backend/data"\n'
        )
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
