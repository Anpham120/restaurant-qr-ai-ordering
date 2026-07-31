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
    SYNTHESIZE,
    KnowledgeError,
    all_chunks,
    load_all,
    load_doc,
    retrievable_chunks,
    verbatim_answers,
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
    "audience: guest\n"
    "answer_mode: synthesize"
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
        body = "# Tài liệu thử\n\n## Mục đầu\n\n" + " ".join(["từ"] * 40)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(Path(tmp), "gop.md", GOOD_FM, body)
            doc = load_doc(path)
        self.assertEqual(len(doc.chunks), 1, "đoạn tiêu đề phải được gộp, không đứng riêng")
        self.assertTrue(doc.chunks[0].text.startswith(doc.title))

    def test_tieu_de_tai_lieu_chi_xuat_hien_MOT_lan_trong_doan(self):
        """Dòng `# H1` phải bị bỏ khỏi thân, vì tiền tố đã mang tiêu đề.

        Không phải chuyện thẩm mỹ: trùng tiêu đề **thổi phồng tần số từ** của đúng những từ
        trong tiêu đề, và BM25 xếp hạng theo tần số từ. Nó làm lệch chính phép so
        BM25/embedding/hybrid ở bước sau — một thiên lệch nằm trong DỮ LIỆU, nên đọc kết quả
        sẽ không thấy nó.

        Chạy trên kho thật, vì lỗi này xảy ra ở kho thật: 108/108 tài liệu đều mở đầu bằng `# H1`
        trùng với `title` trong frontmatter.

        Kiểm **dòng H1**, không kiểm "chuỗi tiêu đề có xuất hiện lại". Bản đầu của test này kiểm
        chuỗi và nó **bịa ra một lỗi không có**: tài liệu tiêu đề "Món chay" có câu nội dung
        "Nhóm Món chay riêng có 7 món" — tiêu đề xuất hiện lại một cách hoàn toàn hợp lệ. Một
        thước đo chấm đỏ câu đúng thì tệ hơn không có thước đo, vì nó khiến người ta sửa thứ
        vốn đã đúng.
        """
        for chunk in all_chunks(KNOWLEDGE):
            h1 = [
                line for line in chunk.text.splitlines()[1:]  # dòng 0 là tiền tố tiêu đề
                if line.startswith("# ")
            ]
            self.assertEqual(
                h1, [],
                f"{chunk.chunk_id}: còn dòng H1 {h1} trong thân đoạn — tiêu đề đếm hai lần "
                "sẽ làm lệch tần số từ khi xếp hạng BM25",
            )


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


class MotChuDeMotTaiLieu(unittest.TestCase):
    """Mỗi chủ đề đúng một tài liệu phụ trách, và mỗi tài liệu đúng một chủ đề.

    Bất biến này từng là chuyện khó hơn nhiều. Kho tri thức trước đây nằm ở **hai chỗ**
    (`restaurant-facts.json` tra khóa, và `ai/knowledge/*.md` truy hồi), nên bất biến là "hai
    kho không được trùng chủ đề" — một phép kiểm phải nhớ đối chiếu hai nguồn khác định dạng.
    Nó cần thiết vì `answer.py` tra kho thứ nhất trước: chủ đề có ở cả hai thì tài liệu ở kho
    thứ hai không bao giờ tới lượt mà vẫn chiếm chỗ trong chỉ mục truy hồi.

    Gộp về một kho làm nó thành phép kiểm trùng lặp bình thường, và **đó là cả điểm của việc
    gộp**: lớp lỗi bị chặn bằng cấu trúc thay vì bằng việc ai đó nhớ kiểm. Ranh giới thật giữa
    hai loại nội dung không mất đi — nó chuyển thành trường `answer_mode` trong cùng một kho.
    """

    def test_khoa_chu_de_khong_trung_trong_ca_kho(self):
        owner: dict[str, str] = {}
        for doc in load_all(KNOWLEDGE):
            for key in doc.topic_keys:
                self.assertNotIn(
                    key, owner,
                    f"khóa {key!r} có ở cả {owner.get(key)!r} và {doc.doc_id!r} — tài liệu tra "
                    "sau không bao giờ tới lượt mà vẫn chiếm chỗ trong chỉ mục",
                )
                owner[key] = doc.doc_id

    def test_moi_tai_lieu_dung_mot_khoa_chu_de(self):
        for doc in load_all(KNOWLEDGE):
            self.assertEqual(
                len(doc.topic_keys), 1,
                f"{doc.doc_id}: có {len(doc.topic_keys)} khóa chủ đề, phải đúng 1",
            )


class HaiCheDoTraLoiTrongMOTKho(unittest.TestCase):
    """`answer_mode` là ranh giới an toàn của kho, nên nó phải được ép chặt.

    Số **kho** gộp được và đã gộp. Số **chế độ trả lời** thì không, vì hai chiều gộp đều mất:

        gộp về synthesize → "mấy giờ đóng cửa" do mô hình viết, và nó CÓ THỂ viết 22h30
        gộp về verbatim   → phải nén danh sách 12 món kèm ghi chú dị nguyên vào một câu

    Nên trường này bắt buộc, không có giá trị mặc định, và chỉ nhận đúng hai giá trị.
    """

    def test_tu_choi_thieu_answer_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            fm = "\n".join(l for l in GOOD_FM.splitlines() if not l.startswith("answer_mode"))
            path = write_doc(Path(tmp), "thieu-mode.md", fm, GOOD_BODY)
            with self.assertRaises(KnowledgeError) as ctx:
                load_doc(path)
        self.assertIn("answer_mode", str(ctx.exception))

    def test_tu_choi_answer_mode_la(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(
                Path(tmp), "la-mode.md",
                GOOD_FM.replace("answer_mode: synthesize", "answer_mode: paraphrase"), GOOD_BODY,
            )
            with self.assertRaises(KnowledgeError):
                load_doc(path)

    def test_verbatim_khong_duoc_co_muc(self):
        # Có mục `##` thì không xác định được phần nào đi tới khách nguyên văn.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(
                Path(tmp), "verbatim-nhieu-muc.md",
                GOOD_FM.replace("answer_mode: synthesize", "answer_mode: verbatim"), GOOD_BODY,
            )
            with self.assertRaises(KnowledgeError) as ctx:
                load_doc(path)
        self.assertIn("##", str(ctx.exception))

    def test_verbatim_tra_dung_chuoi_bat_ke_ngat_dong(self):
        """Ngắt dòng trong tài liệu KHÔNG được làm đổi chuỗi tới khách.

        Đây là chiều dễ bỏ sót: một câu trả lời 68 từ thì người sửa sẽ ngắt dòng cho dễ đọc, và
        nếu ngắt dòng lọt vào chuỗi thì câu tới khách có ký tự xuống dòng ở giữa.
        """
        fm = GOOD_FM.replace("answer_mode: synthesize", "answer_mode: verbatim")
        want = "Nhà hàng mở 10h00–22h00 tất cả các ngày, kể cả cuối tuần và ngày lễ."
        with tempfile.TemporaryDirectory() as tmp:
            one_line = write_doc(Path(tmp), "mot-dong.md", fm, f"# Giờ mở cửa\n\n{want}")
            wrapped = write_doc(
                Path(tmp), "nhieu-dong.md", fm,
                "# Giờ mở cửa\n\nNhà hàng mở 10h00–22h00 tất cả các ngày,\n"
                "kể cả cuối tuần và ngày lễ.",
            )
            self.assertEqual(load_doc(one_line).verbatim_answer, want)
            self.assertEqual(load_doc(wrapped).verbatim_answer, want)

    def test_synthesize_khong_co_cau_tra_loi_nguyen_van(self):
        # Gọi `verbatim_answer` trên tài liệu `synthesize` phải LỖI, không phải trả về gì đó.
        # Trả về im lặng thì một chỗ dùng sai sẽ đưa nửa tài liệu ra cho khách nguyên văn.
        with tempfile.TemporaryDirectory() as tmp:
            path = write_doc(Path(tmp), "tong-hop.md", GOOD_FM, GOOD_BODY)
            with self.assertRaises(KnowledgeError):
                _ = load_doc(path).verbatim_answer

    def test_chi_doan_synthesize_duoc_xep_hang(self):
        """Đoạn `verbatim` bị loại khỏi chỉ mục truy hồi.

        Chúng đã có đường tới khách riêng (tra khóa, trả nguyên văn). Để trong chỉ mục thì có
        hai đường tới cùng nội dung, và đường xếp hạng có thể trích một câu chính sách ra giữa
        câu tư vấn món.
        """
        every = all_chunks(KNOWLEDGE)
        ranked = retrievable_chunks(KNOWLEDGE)
        self.assertTrue(all(c.answer_mode == SYNTHESIZE for c in ranked))
        self.assertLess(len(ranked), len(every), "phải có đoạn verbatim bị loại, nếu không thì "
                                                 "phép lọc này không kiểm được gì")
        self.assertGreaterEqual(len(ranked), 250, "còn đủ đoạn để so BM25/embedding có nghĩa")

    def test_moi_chu_de_verbatim_tra_ra_mot_chuoi_khong_rong(self):
        answers = verbatim_answers(KNOWLEDGE)
        self.assertTrue(answers, "kho phải có tài liệu verbatim — đó là đường trả lời chính sách")
        for topic, text in answers.items():
            self.assertTrue(text.strip(), f"{topic}: câu trả lời nguyên văn rỗng")
            self.assertNotIn("\n", text, f"{topic}: chuỗi tới khách không được có xuống dòng")


if __name__ == "__main__":
    unittest.main(verbosity=2)
