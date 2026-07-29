# -*- coding: utf-8 -*-
"""Test cho bộ nạp và chia đoạn tri thức.

Trọng tâm là **hai bất biến của khâu dữ liệu**, và cả hai đều có test hai chiều:

1. **Bộ nạp TỪ CHỐI nội dung không dành cho khách.** Bản cũ có 5/27 tài liệu mang
   `audience: ai` nằm cùng chỉ mục truy hồi, và 47/221 đoạn bị trích cho khách đọc. Test phải
   chứng minh việc từ chối thật sự xảy ra — chứ không phải tin vào lời khẳng định.

2. **Mã đoạn tất định và liên tục.** Tập đánh giá truy hồi trỏ vào `chunk_id`, nên mã đổi giữa
   hai lần sinh là mọi ca đánh giá trỏ sai chỗ.

    python -m unittest discover -s ai/app -p "test_*.py"
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag.chunker import (  # noqa: E402
    MIN_WORDS_PER_CHUNK,
    KnowledgeError,
    all_chunks,
    load_all,
    load_doc,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE = REPO_ROOT / "ai" / "knowledge"


def write_doc(directory: Path, name: str, frontmatter: str, body: str) -> Path:
    path = directory / name
    path.write_text(f"---\n{frontmatter}\n---\n\n{body}\n", encoding="utf-8")
    return path


GOOD_FM = (
    "id: kb.test.doc.v1\n"
    "title: Tài liệu thử\n"
    "topic_keys: [test_topic]\n"
    "source: demo\n"
    "audience: guest"
)
GOOD_BODY = (
    "# Tài liệu thử\n\n"
    "## Mục một\n\n"
    "Đoạn này đủ dài để không bị gộp vào đoạn sau, nên nó tồn tại riêng như một đoạn.\n\n"
    "## Mục hai\n\n"
    "Đoạn thứ hai cũng đủ dài để đứng riêng, và nó nói về một ý khác hẳn mục một ở trên."
)


class BoNapTuChoiNoiDungKhongDanhChoKhach(unittest.TestCase):
    """Bất biến quan trọng nhất. Từ chối, không phải lọc."""

    def test_tu_choi_audience_ai(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(
                Path(tmp), "noi-bo.md", GOOD_FM.replace("audience: guest", "audience: ai"),
                GOOD_BODY,
            )
            with self.assertRaises(KnowledgeError) as ctx:
                load_doc(path)
        # Thông báo phải nói LÝ DO, không chỉ "không hợp lệ" — người thêm tệp cần hiểu vì sao.
        self.assertIn("audience", str(ctx.exception))
        self.assertIn("truy hồi", str(ctx.exception))

    def test_tu_choi_thieu_audience(self):
        with tempfile.TemporaryDirectory() as tmp:
            fm = "\n".join(l for l in GOOD_FM.splitlines() if not l.startswith("audience"))
            path = write_doc(Path(tmp), "thieu.md", fm, GOOD_BODY)
            with self.assertRaises(KnowledgeError):
                load_doc(path)

    def test_nhan_audience_guest(self):
        """Chiều ngược: nếu bộ nạp từ chối mọi thứ thì bất biến trên vô nghĩa."""
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(Path(tmp), "khach.md", GOOD_FM, GOOD_BODY)
            doc = load_doc(path)
        self.assertEqual(doc.doc_id, "kb.test.doc.v1")
        self.assertEqual(doc.topic_keys, ("test_topic",))
        self.assertEqual(len(doc.chunks), 2)

    def test_tu_choi_source_la(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(
                Path(tmp), "la.md", GOOD_FM.replace("source: demo", "source: guessed"),
                GOOD_BODY,
            )
            with self.assertRaises(KnowledgeError):
                load_doc(path)

    def test_tu_choi_thieu_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "khong-fm.md"
            path.write_text("# Không có frontmatter\n\nNội dung.\n", encoding="utf-8")
            with self.assertRaises(KnowledgeError):
                load_doc(path)


class MaDoanTatDinhVaLienTuc(unittest.TestCase):
    def test_ma_doan_lien_tuc_tu_0(self):
        for doc in load_all(KNOWLEDGE):
            indexes = [int(c.chunk_id.split("#")[1]) for c in doc.chunks]
            self.assertEqual(
                indexes, list(range(len(indexes))),
                f"{doc.doc_id}: mã đoạn khuyết — tập đánh giá truy hồi sẽ trỏ sai chỗ",
            )

    def test_nap_hai_lan_cho_cung_ma_doan(self):
        first = [c.chunk_id for c in all_chunks(KNOWLEDGE)]
        second = [c.chunk_id for c in all_chunks(KNOWLEDGE)]
        self.assertEqual(first, second)

    def test_ma_doan_khong_trung(self):
        ids = [c.chunk_id for c in all_chunks(KNOWLEDGE)]
        self.assertEqual(len(ids), len(set(ids)))


class DoanTuDuNghiaKhiTrichRoi(unittest.TestCase):
    def test_moi_doan_kem_tieu_de_tai_lieu(self):
        for chunk in all_chunks(KNOWLEDGE):
            self.assertTrue(
                chunk.text.startswith(chunk.title),
                f"{chunk.chunk_id}: thiếu tiêu đề tài liệu, đoạn không tự đủ nghĩa",
            )

    def test_khong_con_doan_qua_ngan(self):
        short = [c.chunk_id for c in all_chunks(KNOWLEDGE) if c.word_count < MIN_WORDS_PER_CHUNK]
        self.assertEqual(short, [], "đoạn quá ngắn chiếm chỗ trong top-k mà không mang tín hiệu")

    def test_doan_mo_dau_chi_co_tieu_de_thi_bi_gop(self):
        # Đây là ca thật đã xảy ra: 3 tài liệu mở đầu bằng `# Tiêu đề` rồi vào ngay `##`, nên
        # đoạn #0 chỉ có dòng tiêu đề.
        body = "# Tiêu đề ngắn\n\n## Mục đầu\n\n" + " ".join(["từ"] * 40)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(Path(tmp), "gop.md", GOOD_FM, body)
            doc = load_doc(path)
        self.assertEqual(len(doc.chunks), 1, "đoạn tiêu đề phải được gộp, không đứng riêng")
        self.assertIn("Tiêu đề ngắn", doc.chunks[0].text)


class KhoTriThucThatPhaiHopLe(unittest.TestCase):
    """Chạy trên kho thật, không phải tệp giả — bắt lỗi nội dung khi ai đó thêm tài liệu."""

    def test_khong_trung_doc_id(self):
        docs = load_all(KNOWLEDGE)
        ids = [d.doc_id for d in docs]
        self.assertEqual(len(ids), len(set(ids)))

    def test_moi_tai_lieu_co_topic_keys(self):
        for doc in load_all(KNOWLEDGE):
            self.assertTrue(doc.topic_keys, f"{doc.doc_id}: thiếu topic_keys nên không ai tới được")

    def test_kho_du_lon_de_so_sanh_truy_hoi_co_nghia(self):
        # Với ~40 đoạn thì BM25 và embedding hòa nhau tầm thường và kết luận không nói được gì.
        chunks = all_chunks(KNOWLEDGE)
        self.assertGreaterEqual(
            len(chunks), 250,
            "kho quá nhỏ để phép so BM25/embedding/hybrid có ý nghĩa thống kê",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
