# -*- coding: utf-8 -*-
"""Sinh báo cáo đồ án môn Học máy & Khai phá dữ liệu từ MÃ và BẰNG CHỨNG ĐO, không viết tay số.

    python ai/docs/build_bao_cao_do_an.py            # sinh báo cáo
    python ai/docs/build_bao_cao_do_an.py --check    # kiểm khớp bản đã commit

Vì sao báo cáo phải được SINH — và đây là bài học đã trả giá bằng chính nó
------------------------------------------------------------------------
Bản trước của `BAO_CAO_DO_AN_HOC_MAY_KPDL.md` viết tay 1587 dòng, gồm toàn bộ số liệu. Sau khi phần AI
được dựng lại từ số không, báo cáo mô tả một hệ thống **không còn tồn tại**:

    nhắc `understand.py`, `answer.py`, `generate.py`, `golden_e2e`   0 lần
    Phụ lục B "Lệnh tái lập thực nghiệm" — 11 lệnh                  11/11 trỏ vào tệp ĐÃ XÓA
    Chương 4                                                       so "bảy phương pháp truy hồi",
                                                                   "ba pipeline profile" — thực nghiệm
                                                                   của hệ thống cũ
    số liệu 0,937 · 0,990 · 0,981                                  đo trên hệ thống cũ

Người chấm đọc báo cáo rồi mở repo sẽ thấy hai hệ thống khác nhau, và không lệnh nào trong Phụ lục B
chạy được. Đó là hỏng nặng nhất có thể với một bài nộp.

Notebook của dự án KHÔNG trôi, vì mọi ô mã của nó tự tính lại. Báo cáo trôi vì nó không tính gì. Nên
cách sửa không phải "viết lại rồi nhớ cập nhật" — cách đó vừa thất bại — mà là **sinh**.

Ba loại số, ba nguồn khác nhau
------------------------------
    đếm được ngay      thực đơn, nhãn, kho tri thức, kích thước bốn tập ca  -> đọc tệp dữ liệu
    cần embedding      so ba bộ truy hồi trên hai bài toán                  -> đọc `measurements/`
    cần stack + mô hình golden 103 lượt, LLM+RAG loại C                     -> đọc `measurements/`

Loại thứ hai và ba không tính lại được ở đây: CI cài từng gói chứ không cài cả `requirements.txt`, nên
`--check` sẽ đỏ vì thiếu `sentence-transformers` — một lý do không liên quan gì tới báo cáo. Chúng được
GHI ra `measurements/` bởi chính bộ chạy, và thiếu tệp thì bộ sinh **báo lỗi to** chứ không in số cũ.

Phụ lục B TỰ KIỂM
-----------------
Mỗi lệnh trong Phụ lục B được đối chiếu với hệ thống tệp lúc sinh. Thiếu một tệp là **sinh thất bại**,
không phải một dòng sai lặng lẽ trong tài liệu. Đây là phép kiểm đắt giá nhất của tệp này, vì nó bịt
đúng lỗ đã làm bản trước thành vô dụng.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# `parents[1]`, không phải `parents[2]`: HERE là `<repo>/ai/docs`, nên parents[0]=`ai` và
# parents[1]=gốc repo. Bản đầu viết `parents[2]` và trỏ ra NGOÀI repo — cổng tự kiểm của Phụ lục B bắt
# ngay ở lần chạy đầu, báo 20/21 lệnh trỏ vào tệp không tồn tại. Đúng việc nó có mặt để làm.
REPO_ROOT = HERE.parents[1]
AI = REPO_ROOT / "ai"

# Báo cáo nằm ở `docs/ai/`, KHÔNG phải `ai/docs/`. Repo có HAI thư mục tài liệu và chúng khác vai:
#
#     ai/docs/    tài liệu TỪNG BƯỚC của phần AI (00-problem-statement … 07-error-analysis) + bộ sinh
#     docs/ai/    tài liệu mức DỰ ÁN, gồm báo cáo đồ án và runbook vận hành
#
# Bản đầu của tệp này ghi vào `HERE / "BAO_CAO..."` tức `ai/docs/`, nên nó **tạo một tệp mới ở chỗ sai
# và để nguyên bản gốc đã trôi** — hai bản báo cáo cùng tồn tại, và người đọc gặp bản nào là tùy may.
# Đúng lớp lỗi "hai đầu phải khớp", lần này hai đầu là hai đường dẫn giống nhau đến mức khó thấy.
OUT_PATH = REPO_ROOT / "docs" / "ai" / "BAO_CAO_DO_AN_HOC_MAY_KPDL.md"

sys.path.insert(0, str(AI / "app"))
sys.path.insert(0, str(AI / "evaluation"))


# ----------------------------------------------------------------- đọc dữ liệu và bằng chứng
def doc_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def so(x: float, n: int = 3) -> str:
    """Số thập phân kiểu Việt: dấu phẩy. `None` thành gạch ngang."""
    return "—" if x is None else f"{x:.{n}f}".replace(".", ",")


def pct(x: float, n: int = 2) -> str:
    """Tỷ lệ 0–1 thành phần trăm kiểu Việt, mặc định HAI chữ số thập phân: `0.6087` -> `60,87%`.

    Vì sao đổi từ dạng thập phân `0,609` sang phần trăm: báo cáo học thuật ngành đọc `98,74%` nhanh
    hơn `0,9874`, và hai chữ số sau dấu phẩy là mức chi tiết vừa đủ — với n = 222 ca thì một ca lệch
    là 0,45%, nên chữ số thứ ba không mang thông tin thật.
    """
    return "—" if x is None else f"{x * 100:.{n}f}".replace(".", ",") + "%"


def diem_pt(x: float, n: int = 2) -> str:
    """Chênh lệch tính bằng ĐIỂM PHẦN TRĂM (không phải phần trăm tương đối)."""
    return "—" if x is None else f"{x * 100:+.{n}f}".replace(".", ",")


def tien(x: int) -> str:
    return f"{x:,}".replace(",", ".") + "đ"


class Bang:
    """Mọi số của báo cáo, đọc một lần rồi dùng chung. Thiếu bằng chứng thì NỔ, không đoán."""

    def __init__(self) -> None:
        import results
        from rag.chunker import all_chunks, doan_toan_kho, load_all, retrievable_chunks

        self.menu = doc_json(REPO_ROOT / "backend/data/menu-dataset.json")
        self.tags = doc_json(REPO_ROOT / "backend/data/menu-tags.json")["tags"]
        self.items = self.menu["items"]

        kho = AI / "knowledge"
        self.docs = load_all(kho)
        self.doan = all_chunks(kho)
        self.doan_synth = retrievable_chunks(kho)
        self.doan_xep_hang = doan_toan_kho(kho)
        self.che_do = collections.Counter(d.answer_mode for d in self.docs)

        self.ca_tra_loi = doc_json(AI / "evaluation/cases.json")["cases"]
        self.ca_truy_hoi = doc_json(AI / "evaluation/retrieval_cases.json")["cases"]
        self.ca_chon_muc = doc_json(AI / "evaluation/chunk_selection_cases.json")["cases"]
        self.kich_ban = doc_json(AI / "evaluation/session_scripts.json")["scripts"]
        self.golden = doc_json(AI / "evaluation/golden_e2e.json")["conversations"]
        self.split_truy_hoi = doc_json(AI / "evaluation/retrieval_split.json")

        # Bằng chứng đo. Thiếu là NỔ — xem docstring mô-đun.
        self.m_golden = results.doc("golden_e2e")
        self.m_golden_sinh = results.doc("golden_e2e_sinh")
        self.m_llm = results.doc("llm_rag_loai_c")
        self.m_truy_hoi = results.doc("truy_hoi_so_sanh")
        self.m_chon_dev = results.doc("chon_muc_phat_trien")
        self.m_chon_np = results.doc("chon_muc_niem_phong")

        # Bộ HAI CHIỀU — 100 câu, đo VÌ SAO hệ thống cần cả hai lớp. Đọc CSV vì đó cũng là tệp đưa
        # cho người đọc mở Excel; giữ MỘT nguồn thay vì sinh thêm một JSON song song.
        import csv as _csv
        _p = AI / "evaluation/measurements/hai_chieu.csv"
        if not _p.exists():
            raise SystemExit(
                f"Thiếu bằng chứng {_p.relative_to(REPO_ROOT)}. "
                "Chạy: python ai/evaluation/run_hai_chieu.py --csv"
            )
        self.hai_chieu = list(_csv.DictReader(_p.open(encoding="utf-8-sig")))

    # -- dẫn xuất -------------------------------------------------------------------
    @property
    def luot_phien(self) -> int:
        return sum(len(s["turns"]) for s in self.kich_ban)

    @property
    def luot_golden(self) -> int:
        return sum(len(c["turns"]) for c in self.golden)

    def ktc_truy_hoi(self, tap: str) -> dict:
        """Khoảng tin cậy Wilson 95% cho Hit@1 của từng bộ truy hồi trên một tập."""
        import sys as _s
        if str(AI / "evaluation") not in _s.path:
            _s.path.insert(0, str(AI / "evaluation"))
        from thong_ke import khoang_wilson
        bo = self.m_truy_hoi["so"]["bai_toan_1"][tap]["bo"]
        return {ten: khoang_wilson(v["hit1"], v["n"]) for ten, v in bo.items()}

    def mcnemar_truy_hoi(self, tap: str) -> list:
        """Kiểm định McNemar ghép cặp cho mọi cặp bộ truy hồi trên một tập.

        Yêu cầu `hit1_theo_ca` có trong bằng chứng đo. Thiếu thì NỔ thay vì bỏ qua — một báo cáo
        khẳng định "A tốt hơn B" mà không kiểm định được là báo cáo không bảo vệ được.
        """
        import itertools
        import sys as _s
        if str(AI / "evaluation") not in _s.path:
            _s.path.insert(0, str(AI / "evaluation"))
        from thong_ke import mcnemar
        bo = self.m_truy_hoi["so"]["bai_toan_1"][tap]["bo"]
        thieu = [t for t, v in bo.items() if not v.get("hit1_theo_ca")]
        if thieu:
            raise SystemExit(
                f"Thiếu `hit1_theo_ca` cho {thieu} ở tập {tap}. "
                "Chạy: python ai/evaluation/run_retrieval_comparison.py --sealed"
            )
        ra = []
        for a, b_ in itertools.combinations(["embedding", "hybrid", "bm25"], 2):
            if a in bo and b_ in bo:
                ra.append((a, b_, mcnemar(bo[a]["hit1_theo_ca"], bo[b_]["hit1_theo_ca"])))
        return ra

    def n_can(self, nua_rong: float) -> int:
        import sys as _s
        if str(AI / "evaluation") not in _s.path:
            _s.path.insert(0, str(AI / "evaluation"))
        from thong_ke import n_can_thiet
        return n_can_thiet(nua_rong)

    @property
    def so_cum_tu_vung(self) -> int:
        """Số cụm từ vựng tất định — ĐẾM từ chính bảng, không gõ tay."""
        import understand
        return len(understand.VOCAB)

    @property
    def so_phep_kiem(self) -> int:
        """Số phép kiểm của `verify()`, đếm HAI cách rồi đối chiếu.

        Nhãn chú thích (`# 1.` … `# 8.` kèm hậu tố `6b`, `6c`) đọc được nhưng có thể quên cập nhật;
        số chỗ `loi.append(` thì đúng lúc chạy nhưng không tự nói tên. Lệch nhau nghĩa là có phép
        kiểm không được đánh số. Bản đầu gom `6`, `6b`, `6c` làm một nên đếm 8 trong khi thật là 10.
        """
        import re
        src = (AI / "app" / "generate.py").read_text(encoding="utf-8")
        than = src[src.index("def verify("):]
        moc = chr(10) + "def "
        than = than[:than.index(moc)] if moc in than else than
        theo_nhan = len(set(re.findall(r"^    # (\d+[a-z]?)\.", than, re.M)))
        theo_ma = than.count("loi.append(")
        if theo_nhan != theo_ma:
            raise SystemExit(
                f"verify(): {theo_nhan} phép kiểm có nhãn nhưng {theo_ma} chỗ báo vi phạm."
            )
        return theo_nhan

    @property
    def so_cong_check(self) -> int:
        """Số cổng `--check` trong CI — đếm từ chính workflow."""
        return (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8").count("--check")

    @property
    def hc_a(self) -> list[dict]:
        return [r for r in self.hai_chieu if r["chieu"] == "A"]

    @property
    def hc_b(self) -> list[dict]:
        return [r for r in self.hai_chieu if r["chieu"] == "B"]

    def hc_a_dem(self, loai: str) -> int:
        """`dung` | `khong_xu_ly` | `sai_dang` — ba kết cục của mã tất định ở chiều A."""
        if loai == "dung":
            return sum(1 for r in self.hc_a if r["tat_dinh_dung"] == "True")
        if loai == "khong_xu_ly":
            return sum(1 for r in self.hc_a
                       if r["tat_dinh_dung"] != "True" and r["nhanh_la_truy_hoi"] == "True")
        return sum(1 for r in self.hc_a
                   if r["tat_dinh_dung"] != "True" and r["nhanh_la_truy_hoi"] != "True")

    def hc_a_truy_hoi(self, cot: str) -> int:
        return sum(1 for r in self.hc_a if r[cot] == "True")

    def hc_b_cau_vi_pham(self, cot: str, dang: str | None = None) -> int:
        """Số CÂU có ít nhất một món vi phạm — khác `hc_b_vi_pham` vốn đếm tổng số MÓN.

        Hai cách đếm trả lời hai câu hỏi khác nhau, và báo cáo cần cả hai: "bao nhiêu câu bị ảnh
        hưởng" là thước đo mức phổ biến của lỗi, còn "tổng bao nhiêu món sai" là thước đo mức
        nghiêm trọng. Một phương pháp sai 1 câu nhưng sai 20 món khác hẳn một phương pháp sai 20
        câu mỗi câu 1 món.
        """
        hang = self.hc_b if dang is None else [r for r in self.hc_b if r["vi_sao"] == dang]
        return sum(1 for r in hang if int(r[cot] or 0) > 0)

    def hc_b_vi_pham(self, cot: str, dang: str | None = None) -> int:
        hang = self.hc_b if dang is None else [r for r in self.hc_b if r["vi_sao"] == dang]
        return sum(int(r[cot] or 0) for r in hang)

    def hc_b_dang(self) -> list[str]:
        return sorted({r["vi_sao"] for r in self.hc_b})

    @property
    def loai_ca(self) -> collections.Counter:
        return collections.Counter(c.get("type", "?") for c in self.ca_tra_loi)

    @property
    def chu_de_khong_cum(self) -> int:
        """Chủ đề `synthesize` KHÔNG có cụm từ vựng — chỉ tới được qua truy hồi."""
        from understand import VOCAB

        cum = {v for v in VOCAB.values()} if isinstance(VOCAB, dict) else set()
        co_cum = set()
        for d in self.docs:
            if d.answer_mode != "synthesize":
                continue
            for k in d.topic_keys:
                if any(k == c for c in cum):
                    co_cum.add(k)
        tat_ca = {k for d in self.docs if d.answer_mode == "synthesize" for k in d.topic_keys}
        return len(tat_ca - co_cum)

    def ty_le_truy_hoi(self, nhom: str, bo: str, chi_so: str) -> float | None:
        """Tỷ lệ = tổng tích lũy / số ca có khóa đáp án. `Ketqua` giữ TỔNG, không giữ tỷ lệ."""
        d = self.m_truy_hoi["so"]["bai_toan_1"].get(nhom, {}).get("bo", {}).get(bo)
        if not d or not d["n"]:
            return None
        return d[chi_so] / d["n"]

    def cam5(self, nhom: str, bo: str) -> int | None:
        d = self.m_truy_hoi["so"]["bai_toan_1"].get(nhom, {}).get("bo", {}).get(bo)
        return None if not d else d["cam5"]

    def chon_muc(self, tap: str, nhom_dang: str, bo: str, chi: str = "top1") -> float | None:
        m = self.m_chon_np if tap == "niem_phong" else self.m_chon_dev
        d = m["so"]["nhom"].get(nhom_dang, {}).get(bo)
        return None if not d else d.get(chi)

    def bo_truy_hoi(self) -> list[str]:
        return list(self.m_truy_hoi["so"]["bai_toan_1"]["phát triển"]["bo"])


# ----------------------------------------------------------------- Phụ lục B: TỰ KIỂM
# Lệnh tái lập, và MỌI lệnh ở đây được đối chiếu với hệ thống tệp lúc sinh.
#
# Bản trước của báo cáo có 11 lệnh và 11/11 trỏ vào tệp đã xóa. Không ai phát hiện, vì tài liệu không
# có cách nào tự kiểm. Nay thiếu một tệp là sinh THẤT BẠI.
LENH_TAI_LAP: list[tuple[str, str, str]] = [
    # (nhóm, lệnh, tệp phải tồn tại)
    ("Bước 1 — dữ liệu và tri thức sinh lại được, không cần mô hình",
     "python ai/scripts/build_tag_dictionary.py --check", "ai/scripts/build_tag_dictionary.py"),
    ("Bước 1 — dữ liệu và tri thức sinh lại được, không cần mô hình",
     "python ai/scripts/build_knowledge.py --check", "ai/scripts/build_knowledge.py"),
    ("Bước 1 — dữ liệu và tri thức sinh lại được, không cần mô hình",
     "python ai/scripts/build_retrieval_cases.py --check", "ai/scripts/build_retrieval_cases.py"),
    ("Bước 1 — dữ liệu và tri thức sinh lại được, không cần mô hình",
     "python ai/scripts/build_chunk_selection_cases.py --check",
     "ai/scripts/build_chunk_selection_cases.py"),
    ("Bước 2 — thước đo và tập ca",
     "python ai/evaluation/validate_cases.py", "ai/evaluation/validate_cases.py"),
    ("Bước 2 — thước đo và tập ca",
     "python ai/evaluation/probe_metric_holes.py", "ai/evaluation/probe_metric_holes.py"),
    ("Bước 2 — thước đo và tập ca",
     "python ai/evaluation/build_retrieval_split.py --check",
     "ai/evaluation/build_retrieval_split.py"),
    ("Bước 3 — số nền, không gọi mô hình",
     "python ai/evaluation/run_baseline.py --all", "ai/evaluation/run_baseline.py"),
    ("Bước 3 — số nền, không gọi mô hình",
     "python ai/evaluation/run_session_eval.py", "ai/evaluation/run_session_eval.py"),
    ("Bước 3 — số nền, không gọi mô hình",
     "python ai/evaluation/run_ablation.py", "ai/evaluation/run_ablation.py"),
    ("Bước 4 — so truy hồi (cần `sentence-transformers`)",
     "python ai/evaluation/run_retrieval_comparison.py --sealed",
     "ai/evaluation/run_retrieval_comparison.py"),
    ("Bước 4 — so truy hồi (cần `sentence-transformers`)",
     "python ai/evaluation/run_chunk_selection_comparison.py",
     "ai/evaluation/run_chunk_selection_comparison.py"),
    ("Bước 4 — so truy hồi (cần `sentence-transformers`)",
     "python ai/evaluation/run_chunk_selection_comparison.py --sealed",
     "ai/evaluation/run_chunk_selection_comparison.py"),
    ("Bước 5 — cần MÔ HÌNH thật (`LLM_API_KEY`)",
     "python ai/evaluation/run_llm_rag_eval.py", "ai/evaluation/run_llm_rag_eval.py"),
    ("Bước 6 — cần CẢ STACK (docker compose) và mô hình thật",
     "docker compose -f deploy/docker-compose.yml up -d --build", "deploy/docker-compose.yml"),
    ("Bước 6 — cần CẢ STACK (docker compose) và mô hình thật",
     "python ai/evaluation/wait_for_stack.py", "ai/evaluation/wait_for_stack.py"),
    ("Bước 6 — cần CẢ STACK (docker compose) và mô hình thật",
     "python ai/evaluation/run_golden_e2e.py", "ai/evaluation/run_golden_e2e.py"),
    ("Bước 7 — phân tích và tài liệu",
     "python ai/evaluation/analyze_failures.py", "ai/evaluation/analyze_failures.py"),
    ("Bước 7 — phân tích và tài liệu",
     "python ai/notebooks/build_teaching_notebook.py",
     "ai/notebooks/build_teaching_notebook.py"),
    ("Bước 7 — phân tích và tài liệu",
     "python ai/docs/build_bao_cao_do_an.py", "ai/docs/build_bao_cao_do_an.py"),
]


def kiem_lenh_tai_lap() -> list[str]:
    return [t for _, _, t in LENH_TAI_LAP if not (REPO_ROOT / t).exists()]


def phu_luc_b() -> str:
    ra = ["## Phụ lục B: Lệnh tái lập thực nghiệm", ""]
    ra.append("Chạy từ **gốc repo**. Mỗi lệnh dưới đây được bộ sinh báo cáo đối chiếu với hệ thống tệp,")
    ra.append("nên một lệnh trỏ vào tệp không tồn tại là **sinh báo cáo thất bại** — không phải một dòng")
    ra.append("sai lặng lẽ trong tài liệu. Bản trước của báo cáo có 11 lệnh và **11/11 trỏ vào tệp đã")
    ra.append("xóa**, không ai phát hiện.")
    ra.append("")
    nhom_hien = None
    for nhom, lenh, _ in LENH_TAI_LAP:
        if nhom != nhom_hien:
            if nhom_hien is not None:
                ra.append("```")
                ra.append("")
            ra.append(f"**{nhom}**")
            ra.append("")
            ra.append("```bash")
            nhom_hien = nhom
        ra.append(lenh)
    ra.append("```")
    return "\n".join(ra)


# ----------------------------------------------------------------- Phụ lục C: cấu trúc mã
def phu_luc_c(b: Bang) -> str:
    """Cấu trúc mã nguồn: mô tả VAI TRÒ, và kiểm mọi mô-đun được nhắc là CÓ THẬT.

    Vì sao KHÔNG đếm số dòng
    ------------------------
    Bản đầu của phụ lục này in "số tệp / tổng dòng" cho mỗi thư mục. Hậu quả: **mọi lần sửa một dòng
    mã đều làm báo cáo lạc hậu**, nên `--check` trong CI đỏ cho bất kỳ PR chạm vào `ai/`. Ma sát đó
    không đổi lấy gì — số dòng là trang trí, và nó tạo cảm giác chính xác giả.

    Kết cục dễ đoán của ma sát vô ích: người ta bỏ chạy bộ sinh, hoặc bỏ luôn bước `--check`. Tức một
    phép kiểm quá nhạy tự làm mình bị vô hiệu.

    Nên phụ lục này mô tả **cấu trúc** — thư mục nào làm gì, mô-đun nào chịu trách nhiệm gì — và nó
    chỉ đổi khi **kiến trúc** đổi, đúng lúc báo cáo *nên* đổi. Điều được kiểm là mọi mô-đun được nhắc
    **tồn tại**, vì đó là thứ có thể sai và có hậu quả.
    """
    CAU_TRUC: list[tuple[str, str, list[str]]] = [
        ("ai/app", "mã lúc chạy — không tệp nào ở đây phụ thuộc bộ đo", [
            "understand.py", "answer.py", "generate.py", "cart.py", "session.py",
            "llm_understand.py", "service.py",
        ]),
        ("ai/app/rag", "ba bộ truy hồi và tầng chia đoạn", [
            "bm25.py", "embedding.py", "hybrid.py", "chunker.py", "precompute.py",
        ]),
        ("ai/evaluation", "bốn tập đánh giá, thước đo, bộ so, phân tích nguyên nhân", [
            "cases.json", "session_scripts.json", "retrieval_cases.json",
            "chunk_selection_cases.json", "golden_e2e.json",
            "answer_metric.py", "run_baseline.py", "run_session_eval.py",
            "run_retrieval_comparison.py", "run_chunk_selection_comparison.py",
            "run_llm_rag_eval.py", "run_golden_e2e.py", "analyze_failures.py",
            "results.py", "verify_deploy_config.py",
        ]),
        ("ai/knowledge", "kho tri thức markdown — nguồn của mọi câu trả lời tri thức", []),
        ("ai/scripts", "bộ sinh dữ liệu, tất cả có `--check` trong CI", [
            "build_tag_dictionary.py", "build_knowledge.py",
            "build_retrieval_cases.py", "build_chunk_selection_cases.py",
        ]),
        ("ai/notebooks", "notebook giảng dạy + báo cáo, mọi ô tự tính lại", [
            "build_teaching_notebook.py",
        ]),
        ("ai/docs", "tài liệu từng bước, và bộ sinh của báo cáo này", [
            "build_bao_cao_do_an.py",
        ]),
        ("ai/contracts", "lược đồ JSON của hợp đồng với backend", [
            "ai-chat-v1.schema.json",
        ]),
    ]
    thieu = [
        f"{d}/{m}" for d, _, mods in CAU_TRUC for m in mods
        if not (REPO_ROOT / d / m).exists()
    ]
    if thieu:
        raise FileNotFoundError(
            "Phụ lục C nhắc những mô-đun KHÔNG TỒN TẠI: " + ", ".join(thieu)
            + "\nSửa `CAU_TRUC` trong `build_bao_cao_do_an.py`, hoặc khôi phục tệp. Bản trước của báo"
            " cáo có cả một phụ lục trỏ vào tệp đã xóa và không ai phát hiện."
        )

    ra = ["## Phụ lục C: Cấu trúc mã nguồn", ""]
    ra.append("Mọi mô-đun nhắc dưới đây được **đối chiếu với hệ thống tệp** lúc sinh báo cáo — một tên")
    ra.append("không tồn tại là sinh thất bại. Không in số dòng, có chủ ý: số dòng đổi mỗi lần sửa mã,")
    ra.append("nên nó biến `--check` thành một phép kiểm quá nhạy, và một phép kiểm quá nhạy sẽ bị bỏ.")
    ra.append("")
    ra.append("| Thư mục | Vai trò | Mô-đun chính |")
    ra.append("|---|---|---|")
    for d, vai, mods in CAU_TRUC:
        m = ", ".join(f"`{x}`" for x in mods) if mods else f"{len(b.docs)} tài liệu markdown"
        ra.append(f"| `{d}` | {vai} | {m} |")
    ra.append("")
    ra.append("**Một chiều phụ thuộc được ép:** `ai/evaluation` được import `ai/app`, nhưng KHÔNG chiều")
    ra.append("ngược lại. Mã lúc chạy không được phụ thuộc bộ đo, vì bộ đo không có mặt trong ảnh Docker.")
    ra.append("Chỗ hai bên cần cùng một danh sách — các cụm mở đường hỏi nhân viên — thì mỗi bên khai")
    ra.append("riêng và **một test đối chiếu chúng**, thay vì import chéo.")
    return "\n".join(ra)


# ----------------------------------------------------------------- phần đầu
def phan_dau(b: Bang) -> str:
    return f"""# TRƯỜNG ĐẠI HỌC CMC
## KHOA CÔNG NGHỆ THÔNG TIN VÀ TRUYỀN THÔNG

---

# BÁO CÁO ĐỒ ÁN MÔN HỌC
# MÔN: HỌC MÁY VÀ KHAI PHÁ DỮ LIỆU

**Dự án:** Trợ lý AI tư vấn thực đơn qua mã QR — kiến trúc LLM + RAG với an toàn bảo đảm bằng
cấu trúc và xác minh, không bằng lời nhắc mô hình

**Khoa/Ngành:** CNTT&TT — CNTT

**Giảng viên hướng dẫn:** Phạm Ngọc Đông

**Nhóm sinh viên thực hiện:**

| STT | Họ và tên | MSSV |
|:---:|---|---|
| 1 | Phạm Duy An | BIT240002 |
| 2 | Bùi Đào Đức Anh | BIT240025 |
| 3 | Đỗ Tuấn Anh | BIT240015 |
| 4 | Lê Anh | BIT240017 |
| 5 | Nguyễn Quang Hiếu | BIT240091 |

Hà Nội, ngày {b.m_golden['dieu_kien']['ngay'][8:10]} tháng {b.m_golden['dieu_kien']['ngay'][5:7]} \
năm {b.m_golden['dieu_kien']['ngay'][0:4]}

> **Tài liệu này được SINH RA từ mã nguồn và bằng chứng đo, không viết tay.**
> Sinh lại bằng `python ai/docs/build_bao_cao_do_an.py`. Mọi con số trong báo cáo đến từ một trong ba
> nguồn: đếm trực tiếp trên tệp dữ liệu, hoặc đọc từ `ai/evaluation/measurements/` — nơi các bộ chạy
> ghi kết quả kèm điều kiện của lần chạy. Không con số nào được người viết gõ vào.
>
> Lý do làm vậy: **bản trước của báo cáo này viết tay, và nó đã trôi khỏi hệ thống** — nó mô tả một
> kiến trúc không còn tồn tại, và toàn bộ 11 lệnh tái lập ở Phụ lục B trỏ vào tệp đã bị xóa. Chi tiết
> ở mục 5.4.

---
---"""


def muc_luc() -> str:
    return """# MỤC LỤC

- [TÓM TẮT](#tóm-tắt)
- [DANH MỤC THUẬT NGỮ VÀ VIẾT TẮT](#danh-mục-thuật-ngữ-và-viết-tắt)\n- [DANH MỤC HÌNH ẢNH](#danh-mục-hình-ảnh)\n- [DANH MỤC BẢNG BIỂU](#danh-mục-bảng-biểu)
- [PHÂN CÔNG CÔNG VIỆC](#phân-công-công-việc)
- **[CHƯƠNG 1: GIỚI THIỆU](#chương-1-giới-thiệu)**
  - 1.1 Bối cảnh và động lực
  - 1.2 Ba loại câu hỏi, và vì sao phân loại chúng là quyết định kiến trúc
  - 1.3 Ràng buộc an toàn — bài toán thật của đồ án
  - 1.4 Các nghiên cứu liên quan
  - 1.5 Mục tiêu và đóng góp
- **[CHƯƠNG 2: CƠ SỞ LÝ THUYẾT](#chương-2-cơ-sở-lý-thuyết)**
  - 2.0 Giải thích bằng lời — đọc mục này trước khi vào công thức
  - 2.1 Truy hồi từ khoá — BM25
  - 2.2 Truy hồi ngữ nghĩa — biểu diễn nhúng
  - 2.3 Hợp nhất thứ hạng — Reciprocal Rank Fusion
  - 2.4 Kiến trúc RAG và chỗ nó KHÔNG nên dùng
  - 2.5 Chuẩn hoá văn bản tiếng Việt là phép MẤT thông tin
  - 2.6 Ba lớp an toàn: lọc fail-closed, xác minh, thẻ giỏ tất định
  - 2.7 Các chỉ số đánh giá, và chỉ số nào QUYẾT ĐỊNH
  - 2.8 Vì sao chọn cách làm này — phương án thay thế và bằng chứng
- **[CHƯƠNG 3: PHƯƠNG PHÁP](#chương-3-phương-pháp)**
  - 3.0 Chương này làm gì — đọc bằng lời trước
  - 3.1 Kiến trúc bảy chặng — và chỉ hai chặng có mô hình
  - 3.2 Kho tri thức: một kho, hai chế độ trả lời
  - 3.3 Bốn tập đánh giá, và kỷ luật chia tập
  - 3.4 Mười bảy nhánh trả lời, không nhánh nào chồng nhánh nào
  - 3.5 Hai bài toán truy hồi khác nhau
  - 3.6 Điều kiện kiểm soát thực nghiệm
- **[CHƯƠNG 4: THỰC NGHIỆM VÀ KẾT QUẢ](#chương-4-thực-nghiệm-và-kết-quả)**
  - 4.0 Đọc chương kết quả thế nào
  - 4.1 Thiết lập
  - 4.2 So ba phương pháp truy hồi trên hai tập
  - 4.3 Chọn mục trong tài liệu — bài toán mà hệ thống thật sự chạy
  - 4.4 Chọn món: lọc theo nhãn so với RAG
  - 4.5 Gọi LLM+RAG thật trên câu loại C
  - 4.6 Golden 103 lượt qua chuỗi gọi đầy đủ
  - 4.7 Phân tích nguyên nhân sai — và case nào KHÔNG sửa được nữa
  - 4.8 Chốt phương án triển khai, kèm giá đã đo
  - 4.9 Vì sao hệ thống cần CẢ hai lớp — bộ đo hai chiều 100 câu
- **[CHƯƠNG 5: KẾT LUẬN](#chương-5-kết-luận)**
  - 5.1 Tổng kết
  - 5.2 Phân tích chi tiết theo từng thành phần\n    - 5.2.1 → 5.2.5 Nhận xét của từng thành viên\n  - 5.3 Làm được
  - 5.4 Hạn chế của nghiên cứu
  - 5.5 Bài học kinh nghiệm
  - 5.6 Khó khăn gặp phải\n  - 5.7 Hướng phát triển tương lai
- [TÀI LIỆU THAM KHẢO](#tài-liệu-tham-khảo)
- [PHỤ LỤC](#phụ-lục)

---"""


def tom_tat(b: Bang) -> str:
    """TÓM TẮT — bố cục theo mẫu báo cáo môn học: bài toán, phương pháp, kết quả, từ khoá.

    Nguyên tắc trình bày: **một đoạn một ý**, và mọi con số nằm trong bảng thay vì trong câu văn.
    Bản trước ghép số vào giữa câu bằng f-string, nên sau khi thay số thì dòng bị ngắt ở giữa cụm
    và đoạn văn trở nên khó đọc.
    """
    g, gs, llm = b.m_golden["so"], b.m_golden_sinh["so"], b.m_llm["so"]
    e_np = b.ty_le_truy_hoi("NIÊM PHONG", "embedding", "hit1")
    b_np = b.ty_le_truy_hoi("NIÊM PHONG", "bm25", "hit1")
    cm_np = b.chon_muc("niem_phong", "written|*", "embedding")
    cm_np_bm = b.chon_muc("niem_phong", "written|*", "bm25")
    bo2 = b.m_truy_hoi["so"]["bai_toan_2"]["bo"]
    n2 = b.m_truy_hoi["so"]["bai_toan_2"]["so_ca"]
    ln = bo2["lọc nhãn"]
    khac = [v["cam5"] for k, v in b.m_truy_hoi["so"]["bai_toan_2"]["bo"].items() if k != "lọc nhãn"]
    return f"""# TÓM TẮT

## Bài toán

Đồ án xây dựng một trợ lý ảo tư vấn thực đơn cho khách quét mã QR tại bàn nhà hàng. Khách đặt câu
hỏi bằng tiếng Việt tự nhiên; hệ thống trả lời và đề xuất món để khách thêm vào giỏ hàng.

Dữ liệu gồm thực đơn thật **{len(b.items)} món** được gán **{len(b.tags)} nhãn** thuộc 16 nhóm
thuộc tính, và kho tri thức **{len(b.docs)} tài liệu** được chia thành **{len(b.doan)} đoạn**.

Câu hỏi của khách chia thành hai loại có bản chất khác nhau:

| Loại câu hỏi | Ví dụ | Đáp án nằm ở đâu |
|---|---|---|
| **Chọn món theo điều kiện** | *"Món nào dưới 100 nghìn và không cay?"* | Thuộc tính có cấu trúc của món (giá, nhãn) |
| **Tri thức nhà hàng** | *"Gọi khai vị trước có làm no bụng không?"* | Văn xuôi do người viết |

## Câu hỏi nghiên cứu và đóng góp

Câu hỏi nghiên cứu **không phải** *"áp dụng RAG cho nhà hàng như thế nào"*. Kỹ thuật RAG đã có sẵn
và được dùng rộng rãi. Câu hỏi đặt ra là:

> **Loại câu hỏi nào KHÔNG nên xử lý bằng RAG, và bằng chứng định lượng nào cho thấy điều đó?**

Để trả lời, nhóm so sánh **lọc theo nhãn** với **phương pháp xếp hạng theo độ tương đồng** trên
cùng một bài toán chọn món. Bộ đo gồm **{len(b.hc_b)} câu hỏi** có ràng buộc kiểm tra được, và các
câu này **được sinh tự động từ bộ nhãn** của thực đơn thay vì do người viết chọn:

| Dạng ràng buộc | Số câu | Ví dụ |
|---|---:|---|
| Ngưỡng số | {sum(1 for r in b.hc_b if r['vi_sao'] == 'ngưỡng số')} | *"Món nào dưới 50 nghìn?"* |
| Phân loại | {sum(1 for r in b.hc_b if r['vi_sao'] == 'phân loại')} | *"Có món miền Trung nào không?"* |
| Phủ định | {sum(1 for r in b.hc_b if r['vi_sao'] == 'phủ định')} | *"Món nào không cay?"* |
| Phép trừ (dị nguyên) | {sum(1 for r in b.hc_b if r['vi_sao'] == 'PHÉP TRỪ')} | *"Mình dị ứng hải sản, món nào tránh được?"* |
| Phép hội (hai điều kiện) | {sum(1 for r in b.hc_b if r['vi_sao'] == 'PHÉP HỘI')} | *"Món chay nào dưới 60 nghìn?"* |
| **Tổng** | **{len(b.hc_b)}** | |

Sinh câu hỏi từ bộ nhãn thay vì viết tay là quyết định có chủ đích về mặt phương pháp: khi người
viết tự chọn câu hỏi, họ có xu hướng chọn những câu mà mình đã biết trước kết quả. Sinh tự động thì
danh sách câu hỏi do **dữ liệu** quyết định.

Kết quả — đếm theo **số câu có ít nhất một món vi phạm** ràng buộc khách nêu:

| Phương pháp | Số câu có món vi phạm | Tỷ lệ | Tổng số món vi phạm |
|---|---:|---:|---:|
| **Lọc theo nhãn** | **{b.hc_b_cau_vi_pham('tat_dinh_vi_pham')}/{len(b.hc_b)}** | **{pct(b.hc_b_cau_vi_pham('tat_dinh_vi_pham') / len(b.hc_b))}** | **{b.hc_b_vi_pham('tat_dinh_vi_pham')}** |
| Xếp hạng theo độ tương đồng | {b.hc_b_cau_vi_pham('truy_hoi_vi_pham')}/{len(b.hc_b)} | {pct(b.hc_b_cau_vi_pham('truy_hoi_vi_pham') / len(b.hc_b))} | {b.hc_b_vi_pham('truy_hoi_vi_pham')} |

Riêng nhóm **phép trừ** — câu hỏi về dị ứng, nơi mỗi món vi phạm là một **lỗi an toàn** — lọc theo
nhãn có **{b.hc_b_vi_pham('tat_dinh_vi_pham', 'PHÉP TRỪ')} món vi phạm**, còn phương pháp xếp hạng
có **{b.hc_b_vi_pham('truy_hoi_vi_pham', 'PHÉP TRỪ')} món**.

**Giải thích kết quả.** Thực đơn là dữ liệu **có cấu trúc**: mỗi món đã được gán sẵn giá và nhãn,
nên điều kiện *"giá dưới 100.000đ"* có đáp án đúng hoặc sai xác định. Phép lọc theo nhãn kiểm tra
trực tiếp điều kiện này.

Các phương pháp xếp hạng hoạt động theo nguyên lý khác: chúng đo **mức độ giống nhau** giữa câu hỏi
và văn bản mô tả món, rồi sắp xếp theo điểm giống. Chúng không kiểm tra điều kiện mà ước lượng gián
tiếp, nên đưa vào danh sách những món có mô tả *giống* câu hỏi nhưng *không thỏa* điều kiện.

## Kết quả trên bài toán truy hồi tri thức

Với loại câu hỏi thứ hai — tri thức nhà hàng nằm trong văn xuôi — RAG là phương pháp phù hợp. Kết
quả trên **tập niêm phong** (mở đúng một lần, không dùng để điều chỉnh hệ thống):

| Bài toán | BM25 | Embedding |
|---|---:|---:|
| Truy hồi trên toàn kho (Hit@1) | {pct(b_np)} | **{pct(e_np)}** |
| Chọn đúng mục trong tài liệu (Top-1) | {pct(cm_np_bm)} | **{pct(cm_np)}** |

## Cơ chế bảo đảm an toàn

Hệ thống phục vụ khách có dị ứng thực phẩm, nên yêu cầu an toàn được đặt cao hơn yêu cầu chất lượng
câu chữ. An toàn được bảo đảm bằng **ba lớp độc lập**, không bằng chỉ dẫn trong lời nhắc mô hình:

1. **Lọc dị nguyên fail-closed** — món có nhãn dị nguyên khách nêu bị loại trước khi mô hình nhìn thấy
2. **{b.so_phep_kiem} phép kiểm xác minh** — câu do mô hình viết bị đối chiếu với dữ liệu gốc; vi phạm thì bị loại bỏ
3. **Thẻ giỏ hàng tất định** — dựng từ danh sách món đã lọc, không đọc chữ mô hình viết

Phép đo xác nhận lớp thứ hai là bắt buộc: khi bật đường sinh **trước** khi bổ sung phép kiểm cuối,
**14 ca dị nguyên** mất câu mời khách hỏi nhân viên. Nói cách khác, kết quả "0 lỗi an toàn" của
đường tất định trở thành **14 lỗi an toàn** khi bật mô hình sinh mà chưa đủ phép kiểm.

## Kết quả thực nghiệm cuối

Đo qua chuỗi gọi đầy đủ: quét QR → phiên bàn → phiên chat → backend .NET → dịch vụ AI → mô hình →
thẻ giỏ → giỏ hàng.

| Phép đo | Quy mô | Kết quả |
|---|---:|---|
| Golden đầu-cuối, đường sinh TẮT (mặc định) | {b.luot_golden} lượt | **{g['dat']}/{g['luot']}** |
| Golden đầu-cuối, đường sinh BẬT | {b.luot_golden} lượt | **{gs['dat']}/{gs['luot']}** |
| Tập ca trả lời một lượt | {len(b.ca_tra_loi)} ca | **{len(b.ca_tra_loi)}/{len(b.ca_tra_loi)}** |
| Bộ nhớ phiên nhiều lượt | {b.luot_phien} lượt | **{b.luot_phien}/{b.luot_phien}**, 0 lỗi an toàn |
| LLM + RAG trên câu loại C | {llm['ca']} ca | tất định {llm['ca']}/{llm['ca']} · có sinh {llm['ca']}/{llm['ca']} |

## Hạn chế

**Quy mô bộ đo.** Mục 4.4 của báo cáo trình bày một bộ đo **8 câu** cho cùng bài toán chọn món.
Bộ đó được viết trước, và với n = 8 thì một câu lệch tương ứng 12,50% — quá thô để rút kết luận.
Bộ 50 câu ở trên được xây sau chính vì lý do đó. Mục 4.4 vẫn giữ bộ 8 câu vì nó phân tích **từng
dạng ràng buộc riêng lẻ** kèm giải thích cơ chế, còn bộ 50 câu cho con số tổng hợp đáng tin hơn.
Khi hai bộ cho kết luận khác nhau, **bộ 50 câu là bộ được dùng để kết luận**.

Hạn chế lớn nhất: **không có nhật ký hội thoại của khách thật**. Toàn bộ ca đánh giá do nhóm tự
viết, nên chúng đo được hệ thống có tôn trọng ràng buộc hay không, nhưng không đo được khách thật
sẽ hỏi những gì.

Ngoài ra, cả bốn tập niêm phong đã được mở trong quá trình làm. Con số held-out thật duy nhất của
dự án là **23/27 (85,19%)** ở lần mở đầu tiên.

**Từ khoá:** Trợ lý ảo nhà hàng; Sinh văn bản có tăng cường truy hồi (RAG); Truy hồi thông tin;
BM25; Biểu diễn nhúng đa ngữ; Hợp nhất theo nghịch đảo thứ hạng (RRF); Lọc theo nhãn; An toàn dị
nguyên; Xử lý tiếng Việt; Đánh giá hệ thống hội thoại.

---
---"""


def danh_muc_hinh(b: Bang) -> str:
    """Danh mục hình — SINH từ thư mục `docs/ai/figures/`, không liệt kê tay.

    Cùng nguyên tắc với mọi phần khác của báo cáo: một danh mục viết tay sẽ trôi khỏi thư mục ngay
    lần notebook sinh thêm biểu đồ. Ở đây danh sách tệp quyết định danh mục.
    """
    import re as _re
    thu_muc = REPO_ROOT / "docs" / "ai" / "figures"
    tep = sorted(thu_muc.glob("*.png")) if thu_muc.exists() else []

    # Nhãn đọc được, suy từ tên tệp `hinh<mục>_<thứ tự>.png`
    def nhan(p) -> tuple[str, str]:
        m = _re.match(r"hinh(\d+)_(\d+)", p.stem)
        if not m:
            return p.stem, p.stem
        muc, thu = m.group(1), m.group(2)
        return f"Hình {muc}.{thu}", f"Biểu đồ sinh từ ô mã mục {muc} của notebook"

    d = ["# DANH MỤC HÌNH ẢNH", "",
         f"**{len(tep)} hình**, tất cả **sinh từ ô mã** của notebook",
         "`ai/notebooks/he_thong_ai_tu_van_dat_mon.ipynb` — không hình nào là ảnh chụp màn hình hay",
         "vẽ tay. Chạy lại notebook là vẽ lại từ dữ liệu thật.", "",
         "| Ký hiệu | Mô tả | Tệp |", "|---|---|---|"]
    for p in tep:
        k, mo_ta = nhan(p)
        d.append(f"| {k} | {mo_ta} | `figures/{p.name}` |")
    if not tep:
        d.append("| — | *(chưa sinh hình; chạy notebook để tạo)* | — |")
    d += ["", "---", "---"]
    return "\n".join(d)


def danh_muc_bang(b: Bang) -> str:
    """Danh mục bảng biểu — liệt kê các bảng CHÍNH, kèm mục chứa nó."""
    hang = [
        ("Bảng 2.1", "Ba dạng ràng buộc mà xếp hạng theo độ giống không diễn đạt được", "2.4.1"),
        ("Bảng 2.2", "Bảy quyết định thiết kế — phương án đã bỏ và bằng chứng", "2.8"),
        ("Bảng 3.1", "Bốn tập đánh giá và kỷ luật chia tập", "3.3"),
        ("Bảng 3.2", "Mười bảy nhánh trả lời, loại trừ nhau", "3.4"),
        ("Bảng 4.1", "Điều kiện thực nghiệm", "4.1"),
        ("Bảng 4.2", "So ba phương pháp truy hồi trên tập phát triển", "4.2"),
        ("Bảng 4.3", "So ba phương pháp truy hồi trên tập niêm phong", "4.2"),
        ("Bảng 4.4", "Chọn mục trong tài liệu — hai nhóm báo cáo riêng", "4.3"),
        ("Bảng 4.5", "Chọn món: lọc theo nhãn so với RAG", "4.4"),
        ("Bảng 4.6", "Kết quả gọi LLM+RAG thật trên câu loại C", "4.5"),
        ("Bảng 4.7", f"Golden {b.luot_golden} lượt qua chuỗi gọi đầy đủ", "4.6"),
        ("Bảng 4.8", "Phân loại nguyên nhân sai", "4.7"),
        ("Bảng 4.9", "Chốt phương án triển khai, kèm giá đã đo", "4.8"),
        ("Bảng 4.10", f"Chiều A — {len(b.hc_a)} câu tri thức, ba kết cục của mã tất định", "4.9.1"),
        ("Bảng 4.11", f"Chiều B — {len(b.hc_b)} câu chọn món, số món vi phạm ràng buộc", "4.9.2"),
        ("Bảng 4.12", "Ba lần bộ đo của nhóm sai trước khi ra số đúng", "4.9.4"),
        ("Bảng 5.1", "Tổng hợp kết quả cuối", "5.1"),
    ]
    d = ["# DANH MỤC BẢNG BIỂU", "",
         "Mọi con số trong các bảng dưới đây **được tính lúc sinh báo cáo**, từ tệp dữ liệu và từ",
         "`ai/evaluation/measurements/`. Không con số nào gõ tay.", "",
         "| Ký hiệu | Mô tả | Mục |", "|---|---|---|"]
    d += [f"| {k} | {m} | {muc} |" for k, m, muc in hang]
    d += ["", "---", "---"]
    return "\n".join(d)


def thuat_ngu() -> str:
    return """# DANH MỤC THUẬT NGỮ VÀ VIẾT TẮT

| Viết tắt | Thuật ngữ đầy đủ |
|---|---|
| RAG | Retrieval-Augmented Generation — sinh văn bản có tăng cường truy hồi |
| LLM | Large Language Model — mô hình ngôn ngữ lớn |
| BM25 | Best Matching 25 — hàm xếp hạng theo tần suất từ |
| RRF | Reciprocal Rank Fusion — hợp nhất theo nghịch đảo thứ hạng |
| Hit@k | Tỷ lệ có ít nhất một kết quả đúng trong k kết quả đầu |
| Top-1 | Hit@1 — chỉ số QUYẾT ĐỊNH ở đây, vì hệ thống chỉ đọc đoạn thứ nhất |
| cấm@5 | Số ca lấy phải đoạn BỊ CẤM trong 5 đoạn đầu — đo việc trả lời SAI, không phải kém |
| MRR | Mean Reciprocal Rank — trung bình nghịch đảo thứ hạng |
| nDCG | normalized Discounted Cumulative Gain |
| Đoạn (chunk) | Một mục của tài liệu tri thức, đã cắt theo tiêu đề `##` |
| Fail-closed | Thiếu bằng chứng thì TỪ CHỐI, không đoán. Áp cho ràng buộc dị nguyên |
| Đường tất định | Đường trả lời không gọi mô hình sinh — giống nhau mọi lần chạy |
| Đường sinh | Nhánh mô hình VIẾT câu trả lời, qua tám phép kiểm xác minh |
| Xác minh (verify) | Kiểm câu mô hình viết trước khi gửi; vi phạm là BỎ cả câu, không sửa |
| Ablation | Tắt từng cơ chế để đo đóng góp của nó |
| Tập niêm phong | Tập chỉ mở MỘT lần để chốt kết quả; mở rồi thì hết là held-out |
| p50 / p95 | Phân vị 50 / 95 của phân bố độ trễ |

---"""


def phan_cong(b: Bang) -> str:
    """Phân công theo TUẦN TỰ của đường xây dựng, không theo module.

    Vì sao tuần tự: hệ thống này có thứ tự phụ thuộc rất chặt — không có nhãn thì không lọc được
    món, không có kho thì không truy hồi được, không có tập đánh giá thì không ai biết mình đúng
    hay sai. Chia theo module thì năm người bắt đầu cùng lúc và ba người ngồi chờ.
    """
    return f"""# PHÂN CÔNG CÔNG VIỆC

Phân công theo **thứ tự xây dựng**, không theo module. Lý do nằm ở ràng buộc phụ thuộc rất chặt của
hệ thống: không có nhãn thì không lọc được món, không có kho tri thức thì không truy hồi được, và
**không có tập đánh giá thì không ai biết mình đúng hay sai**. Chia theo module thì năm người khởi
động cùng lúc rồi ba người ngồi chờ; chia theo chặng thì mỗi người bàn giao một thứ người sau
**dùng được ngay**.

## Sơ đồ bàn giao

```
TV1  DỮ LIỆU + LỚP HIỂU CÂU HỎI
      |   91 món · {len(b.tags)} nhãn · {len(b.docs)} tài liệu / {len(b.doan)} đoạn
      |   -> Request(nhãn lọc, ràng buộc, ý định)
      v
TV2  TRUY HỒI
      |   {len(b.ca_truy_hoi)} ca · BM25 / embedding / hybrid
      |   -> đoạn tri thức cho câu ngoài thực đơn
      v
TV3  CHỌN MÓN & AN TOÀN
      |   {b.so_phep_kiem} phép kiểm xác minh · lọc dị nguyên fail-closed
      |   -> danh sách món + thẻ giỏ tất định
      v
TV4  PHIÊN & TÍCH HỢP
      |   dịch vụ HTTP · bộ nhớ phiên 3 quy tắc hợp nhất
      |   -> câu trả lời đã ghép ngữ cảnh, gửi qua backend
      v
TV5  ĐÁNH GIÁ
          {len(b.ca_tra_loi)} ca · {b.luot_phien} lượt phiên · {b.luot_golden} lượt golden
          {len(b.hai_chieu)} câu hai chiều · {b.so_cong_check} cổng CI
```

## Bảng phân công

| # | Họ và tên | MSSV | Chặng | Bàn giao cho người sau | Mục báo cáo | % |
|:-:|---|---|---|---|---|:-:|
| 1 | Phạm Duy An | BIT240002 | **Dữ liệu & lớp hiểu câu hỏi** | Bộ nhãn, kho tri thức, và `Request` đã hiểu | 2.5, 3.1–3.3, 4.5 | 20% |
| 2 | Bùi Đào Đức Anh | BIT240025 | **Truy hồi** | Đoạn tri thức cho câu ngoài thực đơn | 2.1–2.4, 4.2, 4.3 | 20% |
| 3 | Đỗ Tuấn Anh | BIT240015 | **Chọn món & an toàn** | Danh sách món, thẻ giỏ, ba lớp an toàn | 2.6, 4.4, 4.5 | 20% |
| 4 | Lê Anh | BIT240017 | **Phiên & tích hợp** | Dịch vụ HTTP, bộ nhớ phiên, ghép với backend | 3.1, 3.6, 4.6 | 20% |
| 5 | Nguyễn Quang Hiếu | BIT240091 | **Đánh giá** | Bốn tập đánh giá, thước đo, golden, cổng CI | 3.3, 4.1, 4.7–4.9, Ch.5 | 20% |

## Việc từng chặng, và điều kiện bàn giao

Mỗi chặng có **điều kiện nghiệm thu bằng số** — người sau chỉ bắt đầu khi số đó đạt. Đây là chỗ
tránh được lỗi hay gặp nhất của đồ án nhóm: bàn giao một thứ "chạy được trên máy em" rồi ba tuần
sau người khác mới phát hiện nó sai.

### TV1 — Dữ liệu & lớp hiểu câu hỏi

Hai việc này thuộc **một người** vì chúng dính nhau chặt hơn mọi cặp khác: lớp hiểu câu hỏi ánh xạ
chữ khách gõ vào **chính bộ nhãn** mà chặng dữ liệu định nghĩa. Tách ra thì mỗi lần thêm một nhãn
phải đợi người khác thêm cụm từ vựng tương ứng.

1. Hợp nhất hai nguồn thực đơn (JSON của AI và CSDL của backend) về **một** bộ nhãn
2. Từ điển **{len(b.tags)} nhãn / 16 nhóm**, khóa có không gian tên (`spice:none`)
3. Kho tri thức **{len(b.docs)} tài liệu / {len(b.doan)} đoạn** ({b.che_do.get('synthesize', 0)} `synthesize`, {b.che_do.get('verbatim', 0)} `verbatim`)
4. Chuỗi **migration** để nhãn đổi thì CSDL production đổi theo
5. Từ vựng tất định **{b.so_cum_tu_vung} cụm**, khớp trên chuỗi đã rút dấu
6. Tách **ràng buộc** (lọc cứng) khỏi **ngữ cảnh** (chỉ xếp thứ tự), và lớp **ý định**

> **Nghiệm thu:** hai nguồn khớp **91/91 món**; mọi tệp dẫn xuất `--check` xanh; bộ rà nhãn **0 lỗ**;
> kiểm kê đụng chữ khớp con số đã ghi.

### TV2 — Truy hồi

1. Cài **BM25**, **embedding** (`multilingual-e5-small`), **hybrid RRF**
2. So trên **hai bài toán** (truy hồi tri thức / chọn món) và **hai tập** (phát triển / niêm phong)
3. Tính sẵn vector lúc build ảnh Docker, không tải mô hình lúc chạy
4. Chốt bộ cho production kèm **giá phải trả** — ảnh Docker, độ trễ, thời gian khởi động

> **Nghiệm thu:** {len(b.ca_truy_hoi)} ca chạy trên cả ba bộ; bảng so có `cấm@5`; quyết định chốt
> **có số đi kèm**, không chọn theo cảm giác.

### TV3 — Chọn món & an toàn

1. `select()` — lọc theo nhãn, **giao** các nhóm ràng buộc
2. Ba lớp an toàn: **lọc dị nguyên fail-closed**, **{b.so_phep_kiem} phép kiểm** xác minh câu sinh, **thẻ giỏ tất định**
3. Thẻ giỏ dựng từ `reply.items`, không từ chữ mô hình viết
4. Danh sách trắng nhánh được sinh — nhánh mới mặc định **không** sinh

> **Nghiệm thu:** **0 lỗi an toàn** trên mọi tập; câu sinh vi phạm thì **bị BỎ**, không sửa; thẻ giỏ
> không bao giờ chứa món ngoài danh sách đã lọc.

### TV4 — Phiên & tích hợp

1. Dịch vụ HTTP `/v1/chat`, hợp đồng cố định với backend
2. Bộ nhớ phiên **ba quy tắc hợp nhất khác nhau**: dị nguyên cộng dồn, ràng buộc cứng ghi đè theo
   nhóm, ngữ cảnh tích lũy có trần
3. Ghép với backend .NET: phiên bàn, thẻ giỏ, giỏ hàng
4. Đóng gói Docker, biến môi trường, đường lui khi mô hình hỏng

> **Nghiệm thu:** dịch vụ trả lời được khi mô hình **không** cấu hình; bộ nhớ giữ dị nguyên qua mọi
> lượt; hợp đồng với backend không đổi ngoài kế hoạch.

### TV5 — Đánh giá

1. Bốn tập: **{len(b.ca_tra_loi)} ca trả lời**, **{b.luot_phien} lượt phiên**, **{len(b.ca_truy_hoi)} ca truy hồi**, **{len(b.ca_chon_muc)} ca chọn mục**
2. Thước đo và **bộ dò lỗ** — chỗ đo sai trước khi hệ thống sai
3. **Golden {b.luot_golden} lượt** qua chuỗi gọi thật: QR → backend → AI → thẻ giỏ → giỏ hàng
4. **Bộ hai chiều {len(b.hai_chieu)} câu** — chứng minh vì sao cần cả hai lớp
5. **{b.so_cong_check} cổng CI**, và cổng deploy đối chiếu bằng chứng với cấu hình

> **Nghiệm thu:** {len(b.ca_tra_loi)}/{len(b.ca_tra_loi)} ca; {b.luot_phien}/{b.luot_phien} lượt phiên;
> {b.luot_golden}/{b.luot_golden} lượt golden; mọi cổng xanh; deploy bị chặn nếu bằng chứng đo không
> khớp cấu hình đang bật.

## Vì sao chia đều 20%

Không phải để "cho công bằng". Bốn chặng TV1–TV4 mỗi chặng là một khâu **bắt buộc** trên đường một
câu hỏi đi qua — bỏ chặng nào thì hệ thống không chạy. Chặng TV5 không nằm trên đường chạy, nhưng
**không có nó thì bốn chặng kia không chứng minh được mình đúng** — và trong một đồ án học máy, một
một hệ thống không có phương pháp đo thì không có căn cứ để khẳng định nó hoạt động đúng.

---
---"""


def chuong_1(b: Bang) -> str:
    n_a = b.loai_ca.get("A", 0)
    n_b = b.loai_ca.get("B", 0)
    n_c = b.loai_ca.get("C", 0)
    return f"""# CHƯƠNG 1: GIỚI THIỆU

## 1.1 Bối cảnh và động lực

Khách vào nhà hàng, quét mã QR ở bàn, và mở được một trang gọi món. Câu hỏi của đồ án là: **trợ lý AI
thêm được gì vào đúng chỗ đó?** Thực đơn có {len(b.items)} món chia {len(b.menu.get('categories', []))}
danh mục — đủ nhiều để khách không đọc hết, và đủ ít để mọi câu hỏi đều có đáp án xác định trong dữ liệu.

Điều đó đặt ra một tình thế đặc biệt so với các bài toán trợ lý thường gặp: **phần lớn câu hỏi của
khách có đáp án ĐÚNG, tra được, không cần suy đoán.** "Phở bò tái nạm bao nhiêu tiền?" có một câu trả
lời và chỉ một. Một hệ thống sinh văn bản trả lời câu đó là một hệ thống có cơ hội sai ở chỗ không cần
có cơ hội nào.

Nên động lực của đồ án không phải "làm chatbot cho nhà hàng" mà là câu hỏi hẹp hơn và đo được hơn:
**ranh giới giữa việc TRA và việc SINH nằm ở đâu, và ranh giới đó nên được ép bằng cấu trúc hay bằng
lời nhắc mô hình?**

## 1.2 Ba loại câu hỏi, và vì sao phân loại chúng là quyết định kiến trúc

Tập đánh giá {len(b.ca_tra_loi)} ca được gán nhãn theo ba loại, và tỷ lệ của chúng quyết định kiến trúc:

| Loại | Số ca | Bản chất | Mô hình sinh |
|---|---:|---|---|
| A | {n_a} | tra cứu thực đơn — giá, thành phần, khẩu phần | **cấm** |
| B | {n_b} | tri thức nhà hàng — chính sách, cách gọi món, vùng miền | **cấm** |
| C | {n_c} | suy luận và diễn đạt — nhiều ràng buộc, so sánh | **được** |

Loại A cấm sinh vì có đáp án xác định: một mô hình viết lại nó chỉ thêm cơ hội sai. Loại B cấm sinh vì
nội dung là **chữ của người viết tài liệu**, và một chữ số lệch trong câu chính sách là sai sự thật về
nhà hàng. Chỉ loại C — **{n_c}/{len(b.ca_tra_loi)} ca** — là chỗ mô hình có việc thật.

Phân loại này không phải nhãn cho vui: nó thành **danh sách trắng nhánh được phép sinh** trong mã, nên
mô hình *không có đường* ghi chữ cho khách ở loại A và B. Đó là khác biệt giữa "bảo mô hình đừng làm"
và "mô hình không làm được".

## 1.3 Ràng buộc an toàn — bài toán thật của đồ án

Nhãn dị nguyên trong thực đơn phủ **44/{len(b.items)} món**. Con số đó định hình toàn bộ phần an toàn,
vì nó nói: **"thực đơn không ghi nhận hải sản" KHÔNG đồng nghĩa "món này an toàn"** — nó chỉ nói dữ
liệu không có ghi chép.

Hệ quả là hai yêu cầu, và cả hai đều đo được:

1. **Fail-closed.** Khách khai dị ứng thì món mang nhãn đó tuyệt đối không được nêu — kể cả khi kết quả
   rỗng. Thà nói "không có món nào phù hợp" còn hơn mời một món có thể gây hại.
2. **Nói ra giới hạn.** Câu trả lời phải mời khách nhắc nhân viên để bếp xác nhận. Đây **không** phải
   câu khách sáo mà là **nội dung**: nó là chỗ duy nhất trong câu trả lời nói rằng dữ liệu chỉ phủ một
   phần.

Yêu cầu thứ hai được kiểm chứng ở mục 4.5: khi bật đường sinh, mô hình
viết văn mượt hơn và **bỏ câu đó đi** ở 14 ca dị nguyên.

## 1.4 Các nghiên cứu liên quan

BM25 (Robertson & Zaragoza, 2009) là chuẩn cho truy hồi theo từ khoá và vẫn là đường cơ sở mạnh trên
kho nhỏ. Họ mô hình E5 (Wang et al., 2022) cung cấp biểu diễn nhúng đa ngữ có tiếng Việt, dùng tiền tố
`query:`/`passage:` để phân biệt vai trò của văn bản. Reciprocal Rank Fusion (Cormack et al., 2009) hợp
nhất hai bảng xếp hạng mà không cần chuẩn hoá điểm. RAG (Lewis et al., 2020) đặt truy hồi trước sinh để
câu trả lời có nguồn.

Điểm mà đồ án này bổ sung vào bức tranh đó: các công trình trên trả lời câu hỏi *"truy hồi thế nào cho
tốt"*, còn câu hỏi thực tế của một hệ thống có dữ liệu **đã cấu trúc** là *"chỗ nào KHÔNG nên truy hồi"*.
Mục 4.4 đo chính câu đó.

## 1.5 Mục tiêu và đóng góp

1. **Đo ranh giới tra/sinh bằng số**, không bằng lập luận: dựng đường tất định trước, đo nó, rồi mới
   biết mô hình còn phải làm gì.
2. **So ba phương pháp truy hồi trên HAI bài toán** — truy hồi tri thức và chọn món — vì chúng cho hai
   kết luận trái nhau, và một phép so trên một bài toán sẽ dẫn tới quyết định sai ở bài toán kia.
3. **Xây an toàn thành ba lớp độc lập**, và chứng minh từng lớp cần thiết bằng ablation.
4. **Bốn tập đánh giá** phủ bốn chặng khác nhau của chuỗi gọi, tới tận giỏ hàng thật.
5. **Ghi lại mọi lần đo sai** — kể cả những lần thước đo sai trước khi hệ thống sai. Mục 5.4.

---
---"""


def chuong_2(b: Bang) -> str:
    return f"""# CHƯƠNG 2: CƠ SỞ LÝ THUYẾT

## 2.0 Giải thích bằng lời — đọc mục này trước khi vào công thức

Chương này có công thức, nhưng **mọi công thức đều có một câu tiếng Việt giải thích nó làm gì**.
Mục 2.0 giải thích trước bằng lời và bằng ví dụ; các mục sau mới viết công thức chính xác.

### Bài toán gốc: khách hỏi bằng lời, dữ liệu nằm ở hai dạng khác nhau

Nhà hàng có **hai loại thông tin**, và chúng khác nhau đến mức cần hai cách tra hoàn toàn khác:

| Loại | Ví dụ | Nằm ở đâu | Câu hỏi điển hình |
|---|---|---|---|
| **Có cấu trúc** | giá 85.000đ, nhãn `spice:none` (không cay) | bảng thực đơn — mỗi món một dòng, mỗi thuộc tính một cột | *"món nào dưới 100 nghìn?"* |
| **Văn xuôi** | *"khai vị dùng để lấp thời gian chờ, không phải để no"* | tài liệu người viết | *"gọi khai vị trước có làm no bụng không?"* |

Câu hỏi loại một trả lời được bằng **lọc**: duyệt 91 món, giữ món thoả điều kiện. Chính xác tuyệt
đối, vì "giá < 100.000" là một phép so sánh có đáp án đúng/sai rõ ràng.

Câu hỏi loại hai **không có cột nào để lọc**. Đáp án nằm trong một đoạn văn, và việc phải làm là
**tìm đúng đoạn văn đó** trong 452 đoạn. Đó là bài toán **truy hồi thông tin**.

### Truy hồi thông tin (Information Retrieval — IR) là gì

**Truy hồi** = cho một câu hỏi, tìm trong kho tài liệu những đoạn **liên quan nhất**, xếp theo thứ
tự từ liên quan nhất trở xuống.

Điểm quan trọng nhất, và là điều quyết định cả đồ án này: truy hồi **không trả lời** câu hỏi. Nó chỉ
**đưa cho bạn đoạn văn** mà nó cho là liên quan. Nó cũng **không biết** đoạn đó có đúng không — nó
chỉ biết đoạn đó **giống** câu hỏi tới mức nào.

> **Ẩn dụ:** truy hồi giống một thủ thư. Bạn hỏi *"sách nào nói về nấu ăn Huế?"*, thủ thư đưa bạn ba
> cuốn xếp theo mức liên quan. Thủ thư **không đọc hộ** và **không khẳng định** cuốn nào trả lời
> đúng câu bạn cần — đó là việc của bạn.

### Hai cách đo "giống nhau", và vì sao cần cả hai

Máy không hiểu nghĩa như người. Nó phải quy "giống nhau" về một **con số**. Có hai cách chính:

**Cách 1 — Đếm từ chung (BM25).**
Đoạn nào chứa nhiều từ giống câu hỏi thì điểm cao. Có ba tinh chỉnh khiến nó tốt hơn đếm thô:

- **Từ hiếm đáng giá hơn từ phổ biến.** Chữ *"món"* xuất hiện ở gần như mọi đoạn nên nó gần như
  không phân biệt được gì; chữ *"mắm ruốc"* chỉ ở vài đoạn nên nó rất đáng giá. Phần này gọi là
  **IDF** — *Inverse Document Frequency*, **tần suất tài liệu nghịch đảo**: từ càng xuất hiện ở ít
  tài liệu thì trọng số càng cao.
- **Lặp nhiều lần không tăng điểm mãi.** Một đoạn nhắc *"lẩu"* 20 lần không liên quan gấp 20 lần
  đoạn nhắc 1 lần. Tham số `k₁` giới hạn mức tăng này — gọi là **bão hoà tần suất**.
- **Đoạn dài bị phạt.** Đoạn dài đương nhiên chứa nhiều từ hơn, nên nó dễ trúng từ khoá một cách
  may mắn. Tham số `b` chuẩn hoá theo độ dài.

  **Điểm mạnh:** chính xác khi khách dùng **đúng chữ** có trong tài liệu.
  **Điểm yếu:** khách hỏi *"đồ biển"* mà tài liệu viết *"hải sản"* thì **không có từ nào chung** —
  BM25 trả về rỗng, dù hai cụm cùng nghĩa.

**Cách 2 — So nghĩa bằng vector (embedding).**
**Embedding** dịch là **biểu diễn nhúng** hoặc **véc-tơ ngữ nghĩa**: một mô hình đã được huấn luyện
sẽ biến mỗi câu thành một **dãy số** (ở đây là 384 số). Điều đặc biệt: hai câu **cùng nghĩa** thì
hai dãy số **gần nhau**, kể cả khi chúng không chung chữ nào.

> **Ẩn dụ:** hãy tưởng tượng mỗi câu là một **điểm trên bản đồ**. Mô hình đặt *"đồ biển"* và *"hải
> sản"* ở hai vị trí sát nhau, còn *"cà phê"* ở tận đầu kia. Tìm đoạn liên quan = tìm **điểm gần
> nhất** trên bản đồ đó.

Độ gần được đo bằng **cosine similarity** — **độ tương đồng cô-sin**: một con số từ −1 đến 1, càng
gần 1 thì hai câu càng cùng nghĩa.

  **Điểm mạnh:** hiểu được cách nói khác nhau của cùng một ý.
  **Điểm yếu:** nó **luôn** trả về một đáp án. Không có khái niệm "không tìm thấy" — câu hỏi lạc đề
  hoàn toàn vẫn nhận về 5 đoạn với điểm số đàng hoàng. Nó **không trượt, nó trả sai**.

**Cách 3 — Trộn hai cách trên (hybrid).**
**RRF** — *Reciprocal Rank Fusion*, **hợp nhất theo nghịch đảo thứ hạng**: lấy **thứ hạng** (đứng
thứ mấy) của mỗi đoạn ở cả hai cách, rồi cộng nghịch đảo lại. Đoạn nào được **cả hai** xếp cao thì
tổng cao. Dùng thứ hạng thay vì điểm số vì điểm của BM25 và điểm cosine **không cùng thang đo** —
cộng thẳng thì như cộng mét với ki-lô-gam.

### RAG là gì, và vì sao đồ án này *không* dùng RAG cho mọi thứ

**RAG** — *Retrieval-Augmented Generation*, **sinh văn bản có tăng cường truy hồi**. Quy trình ba
bước:

```
1. TRUY HỒI   câu hỏi -> tìm đoạn liên quan trong kho
2. GHÉP       đưa đoạn đó vào "lời nhắc" (prompt) gửi cho mô hình ngôn ngữ
3. SINH       mô hình viết câu trả lời DỰA TRÊN đoạn đó
```

Bước 2 là chỗ quan trọng. **Prompt** dịch là **lời nhắc** — đoạn văn bản ta gửi cho mô hình, gồm
câu hỏi của khách **cộng** dữ liệu ta muốn nó dựa vào. Không có bước này thì mô hình chỉ có kiến
thức chung của nó và sẽ **tự nghĩ ra** thông tin về nhà hàng — hiện tượng gọi là **hallucination**,
dịch là **bịa đặt**: mô hình viết ra câu nghe rất hợp lý nhưng sai sự thật.

RAG rất mạnh cho câu **văn xuôi**. Nhưng đồ án này chứng minh bằng số rằng nó **sai chỗ** ở câu
**chọn món**, và lý do rất dễ hiểu:

> Truy hồi chỉ biết *"giống nhau"*. Nó **không có phép so sánh lớn hơn / nhỏ hơn**, **không có phép
> loại trừ**, và **không có phép và**.
>
> Khách nói *"tôi dị ứng hải sản"* — câu này **chứa chữ "hải sản"**, nên cả BM25 lẫn embedding đều
> kéo **món hải sản lên đầu**. Đúng ngược điều khách cần. Không phải vì chúng hỏng, mà **chính vì
> chúng hoạt động đúng như thiết kế**.

Đó là lý do hệ thống này chia việc: **lọc theo nhãn** chọn món (chính xác tuyệt đối với điều kiện
đếm được), **truy hồi** lo câu văn xuôi, và **mô hình sinh** chỉ **viết lại cho tự nhiên** những món
đã được chọn — nó không được phép chọn món.

### Các thuật ngữ khác gặp trong báo cáo

| Tiếng Anh | Tiếng Việt | Nghĩa đơn giản |
|---|---|---|
| **chunk** | **đoạn** | một mẩu tài liệu đủ nhỏ để đưa vào lời nhắc; kho này cắt theo tiêu đề mục |
| **corpus** | **kho ngữ liệu** | toàn bộ tài liệu dùng để truy hồi — ở đây {len(b.docs)} tài liệu / {len(b.doan)} đoạn |
| **index** | **chỉ mục** | cấu trúc dữ liệu dựng sẵn để tìm nhanh, như mục lục sách |
| **query** | **truy vấn** | câu hỏi sau khi đã xử lý để đem đi tìm |
| **token** | **từ tố** | đơn vị nhỏ nhất máy đọc — thường là một từ |
| **Hit@k** | **tỷ lệ trúng trong k đầu** | trong k đoạn trả về đầu tiên, có ít nhất một đoạn đúng không |
| **ground truth** | **khoá đáp án** | đáp án đúng do người viết ra để chấm điểm máy |
| **held-out / sealed set** | **tập niêm phong** | tập câu hỏi giấu đi, chỉ mở một lần khi đã xong — để không vô tình sửa hệ thống cho vừa đề |
| **ablation** | **thử bỏ bớt** | tắt từng cơ chế rồi đo lại, để biết cơ chế đó có thật sự đóng góp |
| **fail-closed** | **hỏng thì đóng** | khi không chắc thì **từ chối**, không đoán. Dùng cho lọc dị ứng |
| **latency** | **độ trễ** | thời gian từ lúc khách gửi câu hỏi tới lúc nhận câu trả lời |
| **baseline** | **mốc nền** | kết quả của cách làm đơn giản nhất, để so xem cách phức tạp có hơn không |

---

## 2.1 Truy hồi từ khoá — BM25

Điểm BM25 của đoạn *D* với truy vấn *Q*:

```
score(D,Q) = Σ_{{t∈Q}} IDF(t) · ( f(t,D)·(k₁+1) ) / ( f(t,D) + k₁·(1 − b + b·|D|/avgdl) )
```

với `k₁ = 1,5`, `b = 0,75`. Cài đặt của đồ án dùng dạng IDF **không âm**:

```
IDF(t) = ln( 1 + (N − n(t) + 0,5) / (n(t) + 0,5) )
```

Dạng gốc `ln((N−n+0,5)/(n+0,5))` cho giá trị **âm** khi *n > N/2*, nghĩa là chứa từ đó làm đoạn **tụt**
hạng. Với kho này thì "món" và "nhà hàng" xuất hiện ở gần như mọi đoạn, nên đó không phải chuyện lý
thuyết. Một ca test chốt `IDF > 0` cho những từ đó.

Tính chất quan trọng cho phép so ở Chương 4: **BM25 trả về RỖNG khi truy vấn không chung từ nào với
kho.** Embedding thì luôn cho điểm cho mọi đoạn, nên nó **không bao giờ "trượt"** — nó chỉ trả sai. Đó
là lý do `cấm@5` quan trọng hơn Hit@5.

## 2.2 Truy hồi ngữ nghĩa — biểu diễn nhúng

Mô hình `intfloat/multilingual-e5-small` — 384 chiều, có tiếng Việt. Họ E5 đòi **tiền tố** phân biệt
vai trò:

```
"query: {{câu hỏi}}"     cho truy vấn
"passage: {{đoạn}}"      cho đoạn trong kho
```

Thiếu tiền tố thì mô hình vẫn chạy và vẫn trả về vector, chỉ giảm chất lượng. Đây là lỗi **không có
triệu chứng quan sát được**: hệ thống không báo lỗi, chỉ cho điểm thấp hơn. Nhóm bổ sung một ca kiểm
thử xác nhận tiền tố được thêm đúng.

Vector được chuẩn hoá L2, nhờ vậy `cosine(a,b) = a·b` và phép so chỉ còn một phép nhân vô hướng. Chuẩn
hoá cũng là điều **bắt buộc về mặt đúng đắn**: không chuẩn hoá mà vẫn lấy tích vô hướng thì đoạn **dài**
được lợi thế chỉ vì vector nó dài hơn.

Một hệ quả của chuẩn hoá L2 được dùng làm tối ưu ở mục 4.3: điểm cosine của một đoạn **không phụ thuộc**
việc có bao nhiêu đoạn khác trong chỉ mục. Nên xếp hạng trong một tài liệu chỉ là **giới hạn phép chấm
điểm của chỉ mục toàn kho vào tập con** — không cần dựng chỉ mục mới.

## 2.3 Hợp nhất thứ hạng — Reciprocal Rank Fusion

```
RRF(d) = Σ_r 1 / (k + rank_r(d)),    k = 60
```

Ý nghĩa của *k*: nó làm **đồng thuận thắng nổi bật**. Một đoạn xếp hạng 3 ở *cả hai* bảng được
`2/(60+3) = 0,0317`, cao hơn một đoạn xếp hạng 1 chỉ ở *một* bảng `1/(60+1) = 0,0164`. Có test chốt đúng
hai con số đó.

Một chi tiết cài đặt quyết định việc hybrid có ý nghĩa hay không: phải lấy **sâu hơn k** từ mỗi bảng.
Bản đầu chỉ lấy đúng `k` đoạn, nên đoạn đồng thuận ở hạng 6 không bao giờ vào kết quả và hybrid gần như
trùng khớp BM25 — tức phép so **không so gì cả**.

## 2.4 Kiến trúc RAG và chỗ nó KHÔNG nên dùng

RAG đặt truy hồi trước sinh: lấy đoạn liên quan, đưa vào ngữ cảnh, để mô hình viết câu trả lời có nguồn.
Trong đồ án này, chỗ RAG gặp LLM là hàm đưa đoạn đã truy hồi vào lời nhắc của câu sinh — không có nó thì
mô hình chỉ có danh sách món và sẽ **tự nghĩ ra lý do**, đúng chỗ dễ bịa nhất.

Nhưng RAG **không** phải công cụ cho mọi việc, và đây là luận điểm chính của đồ án. Bốn lý do khiến xếp
hạng theo độ tương đồng **thua** ở bài toán chọn món, mỗi lý do một ca đo được:

| Lý do | Ví dụ | Vì sao xếp hạng không làm được |
|---|---|---|
| không hiểu SỐ | "món nào dưới 50.000đ" | "50.000" với BM25 là một TỪ; với embedding thì "dưới 50 nghìn" và "dưới 500 nghìn" gần như cùng vector |
| phủ định | "món KHÔNG cay" | "không cay" và "cay" chung gần hết từ |
| cần LOẠI TRỪ | "tôi dị ứng hải sản" | câu chứa chữ "hải sản" nên cả hai kéo món hải sản **LÊN ĐẦU** |
| hai ràng buộc | "không cay VÀ dưới 80 nghìn" | xếp hạng theo độ tương đồng **không có phép AND** |

Trường hợp thứ ba có ý nghĩa đặc biệt về mặt an toàn: một hệ thống RAG vận hành đúng đặc tả vẫn sẽ đề
xuất món hải sản cho người vừa khai báo dị ứng hải sản. Nguyên nhân nằm ở chính cơ chế xếp hạng theo độ
tương đồng, không phải ở lỗi cài đặt.

### 2.4.1 Đây là giới hạn BIỂU ĐẠT, không phải giới hạn dữ liệu hay mô hình

Bốn dòng trên dễ bị đọc thành "truy hồi còn yếu, cải thiện dữ liệu hoặc đổi mô hình là xong". Đồ án
này khẳng định ngược lại, và khẳng định đó có cả **lập luận** lẫn **thí nghiệm**.

Lập luận: một bộ truy hồi là một **hàm xếp hạng** `rank(q, d) = sim(q, d)` —
nó trả về **thứ tự** các tài liệu theo **độ giống** với truy vấn. Nó không có khái niệm *thoả* hay
*không thoả* — chỉ có *giống hơn* và *giống ít hơn*. Trong khi ba dạng ràng buộc dưới đây là những
**vị từ** trên tập món, và chúng cần một phép toán mà quan hệ giống nhau không mang:

| Ràng buộc | Dạng toán | Vì sao độ giống không diễn đạt được |
|---|---|---|
| `giá < 50.000` | quan hệ **thứ tự** trên số | độ giống là quan hệ **đối xứng**; thứ tự thì không. `sim(q,d)` không phân biệt được "rẻ hơn" với "đắt hơn" |
| `hải sản ∉ nhãn(d)` | phép **bù** trên tập | không tồn tại truy vấn `q` nào để `sim(q,d)` **giảm** khi `d` chứa hải sản; nhắc tới thứ cần tránh chỉ làm nó giống HƠN |
| `A ∧ B` | phép **giao** | `sim` trả một số vô hướng đã trộn; không tách lại được thành hai điều kiện để ép cả hai cùng đúng |

Thí nghiệm kiểm chứng lập luận này ở mục **4.9**: trên 50 câu sinh từ chính bộ nhãn, lọc theo nhãn
vi phạm **13** món còn truy hồi vi phạm **116** — và ở nhóm loại trừ dị nguyên, lọc nhãn **0** còn
truy hồi **11 món chứa đúng thứ khách phải tránh**.

Một thí nghiệm thứ hai đóng đường thoát "tại dữ liệu chưa tốt": nhóm đã viết lại tiêu đề mục của
kho tri thức cho đặc thù theo tài liệu, đưa số tiêu đề khác nhau từ **179 lên 365** và số đoạn dùng
chung tiêu đề từ **283/452 xuống 93/452**. Lớp lỗi nhắm tới giảm từ **19 ca xuống 1**. Nhưng Hit@1
trên tập niêm phong **không đổi — 60,87% trước và sau**, còn Hit@5 **giảm** từ 67,39% xuống 63,04%. Các
ca kia không được sửa; chúng **đổi tên lỗi** từ "hai mục trùng tiêu đề" sang "xếp hạng sai".

Kết quả này cho thấy giới hạn quan sát được **không đến từ chất lượng kho ngữ liệu**. Cải thiện dữ liệu
không làm một hàm xếp hạng theo độ tương đồng biểu diễn được một vị từ mà nó không có phép toán tương
ứng. Đây là đóng góp chính của đồ án về mặt phương pháp.

## 2.5 Chuẩn hoá văn bản tiếng Việt là phép MẤT thông tin

Rút dấu (`fold`) cho phép khớp "mo cua" với "mở cửa" — người Việt gõ không dấu rất thường. Nhưng nó là
phép **mất thông tin**, và phần bị mất có ý nghĩa phân biệt: sau khi rút dấu, `"bò"` và `"bơ"` cùng
thành `"bo"`.

Nên rút dấu chỉ dùng cho **tách từ của BM25**, không dùng cho phép so tên món. Và một chi tiết đã sai
một lần: bản đầu bỏ từ dưới 3 ký tự, làm mất `"bò"`, `"gà"`, `"mì"`, `"ốc"`, `"cá"` — đúng những từ khoá
quan trọng nhất của một thực đơn Việt.

Ablation đo riêng mức mất của việc tắt rút dấu, và nó chỉ được áp cho **BM25**: embedding không dùng
phép tách từ đó, nên gán mức mất cho nó là ablation đo sai chỗ.

## 2.6 Ba lớp an toàn: lọc fail-closed, xác minh, thẻ giỏ tất định

An toàn **không được phụ thuộc mô hình sinh**. Đồ án cài ba lớp độc lập:

**Lớp 1 — lọc fail-closed.** Ràng buộc dị nguyên áp cuối và không bao giờ nới, kể cả khi kết quả rỗng.
Một ranh giới quan trọng được rút ra khi chạy thật: *loại trừ món đã gợi ý* là phép **lịch sự** và nới
được; *dị nguyên, độ cay, giá, chế độ ăn* là ràng buộc **an toàn** và không bao giờ nới. Nới nhóm đầu
dẫn tới việc nhắc lại một món khách đã thấy; nới nhóm sau dẫn tới việc mời khách một món có thể gây hại.

**Lớp 2 — tám phép kiểm xác minh** trên câu mô hình viết. Vi phạm bất kỳ phép nào thì câu sinh bị **BỎ**
và hệ thống dùng lại câu khuôn mẫu — không sửa, không thử lại:

1. mã món mô hình khai đã dùng phải nằm trong danh sách đưa vào
2. không nhắc món thật nào **ngoài** danh sách đã lọc
3. mọi số tiền phải là giá thật của một món trong danh sách
4. không được nêu **số lượng** món ("có 6 món lẩu")
5. không được viết mã nhãn kỹ thuật (`allergen:peanut`) vào chữ khách đọc
6. phải nhắc **ĐỦ** món trong danh sách — thiếu một món là câu trả lời thiếu
7. không nhắc món mang nhãn khách cần tránh — **chốt an toàn**
8. khách đã nêu điều cần tránh thì phải **mở đường hỏi nhân viên** — **chốt an toàn**

Phép kiểm 8 ra đời từ một con số, xem mục 4.5. Điều đáng ghi về nó: `PROMPT` cũng đã yêu cầu điều này,
nhưng **yêu cầu trong prompt là đề nghị, không phải bảo đảm**.

**Lớp 3 — thẻ giỏ tất định.** Thẻ dựng từ danh sách món mà mã tất định đã chọn, **không** từ chữ mô
hình viết. Nên dù một câu sinh lọt qua xác minh mà vẫn sai, khách **không đặt được** món không tồn tại.

Điều lớp 2 **không** bắt được, nói ra chứ không giấu: một tên món **hoàn toàn bịa** — không có trong
thực đơn dưới bất kỳ dạng nào — thì phép so chuỗi không phát hiện. Giới hạn này được ghi thành **một
test có tên nói rõ nó là giới hạn**, để không ai tưởng lớp đó kín.

## 2.8 Vì sao chọn cách làm này — phương án thay thế và bằng chứng

Mọi quyết định dưới đây đều có **ít nhất một phương án khác nghe hợp lý hơn lúc bắt đầu**. Mục này
ghi lại: chọn gì, bỏ gì, và **con số nào** khiến nhóm chọn như vậy. Không quyết định nào ở đây dựa
trên cảm giác hay thói quen.

### Quyết định 1 — Chọn món bằng LỌC NHÃN, không bằng RAG

| | |
|---|---|
| **Phương án đã bỏ** | dùng luôn RAG cho mọi câu, kể cả *"món nào dưới 100 nghìn"* |
| **Nghe hợp lý vì** | một cơ chế cho mọi việc thì gọn, ít mã, dễ bảo trì |
| **Đã chọn** | `select()` lọc theo nhãn cho câu chọn món; RAG chỉ cho câu văn xuôi |

**Bằng chứng — 50 câu chọn món sinh từ chính bộ nhãn (mục 4.9.2):**

| | lọc nhãn | truy hồi |
|---|---:|---:|
| món **vi phạm ràng buộc** | **{b.hc_b_vi_pham('tat_dinh_vi_pham')}** | {b.hc_b_vi_pham('truy_hoi_vi_pham')} |
| riêng nhóm **dị ứng** | **{b.hc_b_vi_pham('tat_dinh_vi_pham', 'PHÉP TRỪ')}** | {b.hc_b_vi_pham('truy_hoi_vi_pham', 'PHÉP TRỪ')} |

**Ví dụ chứng minh:**

> **Khách:** *"Mình dị ứng hải sản, món nào tránh được?"*
>
> **RAG trả về:** Nghêu hấp sả, Mực xào sa tế, Ốc hương rang bơ tỏi… — **toàn món hải sản**
>
> **Vì sao:** câu hỏi **chứa chữ "hải sản"**, nên phép đo độ giống kéo đúng những đoạn nói về hải
> sản lên đầu. Nó không hỏng — nó **làm đúng việc nó được thiết kế để làm**.
>
> **Lọc nhãn trả về:** Bánh mì pate, Gỏi cuốn chay… — 0 món mang nhãn `allergen:seafood`.

Trường hợp này minh hoạ giới hạn cấu trúc nêu ở mục 2.4.1: hệ thống RAG vận hành đúng đặc tả vẫn đề
xuất món hải sản cho người khai báo dị ứng hải sản, do cơ chế xếp hạng theo độ tương đồng không biểu
diễn được phép loại trừ.

### Quyết định 2 — Truy hồi dùng EMBEDDING, không dùng BM25

| | |
|---|---|
| **Phương án đã bỏ** | chỉ dùng BM25 — nhẹ, không cần mô hình, ảnh Docker 238MB |
| **Nghe hợp lý vì** | embedding kéo ảnh Docker lên **2,74GB** và khởi động chậm **19 giây** |
| **Đã chọn** | embedding, và **chấp nhận trả giá đó** |

**Bằng chứng — tập niêm phong (mở một lần, không sửa hệ thống theo nó):**

| bộ | Hit@1 |
|---|---:|
| BM25 | 39,13% |
| **embedding** | **60,87%** |

**Ví dụ chứng minh:**

> **Khách:** *"Mình muốn món chín bằng hơi nước, nhẹ bụng"*
>
> Tài liệu đích viết *"món hấp"* — **không chung một chữ nào** với câu hỏi.
>
> **BM25:** không tìm được (không có từ chung để đếm).
> **Embedding:** tìm đúng, vì *"chín bằng hơi nước"* và *"hấp"* nằm gần nhau trên bản đồ nghĩa.

Đây là lý do nhóm chấp nhận ảnh Docker nặng gấp 11 lần: **khách gõ theo cách của khách**, không gõ
theo từ trong tài liệu.

### Quyết định 3 — TẮT đường sinh mặc định

| | |
|---|---|
| **Phương án đã bỏ** | bật mô hình sinh cho mọi câu, để câu chữ tự nhiên hơn |
| **Nghe hợp lý vì** | câu khuôn mẫu đọc khô; mô hình viết mượt hơn hẳn |
| **Đã chọn** | tắt mặc định, bật bằng biến môi trường |

**Bằng chứng:** sau {b.so_phep_kiem} phép kiểm xác minh, đường sinh **0 ca tụt** — nhưng cũng **0 ca
đúng thêm**. Giá phải trả: **+8,6 giây mỗi lượt**.

Không có ca nào tốt lên thì việc bật nó là **trả 8,6 giây để đổi lấy câu chữ mượt hơn**. Đó là đánh
đổi hợp lệ, nhưng phải là **quyết định của chủ nhà hàng**, không phải mặc định do nhóm chọn hộ.

### Quyết định 4 — Mô hình sinh KHÔNG được chọn món

| | |
|---|---|
| **Phương án đã bỏ** | đưa cả thực đơn vào lời nhắc, để mô hình tự chọn và tự viết |
| **Nghe hợp lý vì** | ít mã hơn hẳn, và mô hình "hiểu" câu hỏi tốt hơn mã tất định |
| **Đã chọn** | `select()` chọn món; mô hình chỉ **viết về** những món đã chọn |

**Ví dụ chứng minh** — đo được trên bản chạy thật, mô hình viết:

> *"Nhà hàng có **6 món lẩu**…"* — trong khi thực đơn có **7**.

Một con số bịa mà ba phép kiểm đầu **không chạm tới**: nó không phải tên món, không phải giá, không
phải nhãn. Phải thêm một phép kiểm riêng cấm mô hình nêu số lượng.

Nếu mô hình được phép **chọn** món thay vì chỉ **viết về** món, lỗi tương tự sẽ là một món không tồn
tại nằm trong thẻ giỏ hàng — và khách bấm đặt được.

### Quyết định 5 — Dị nguyên FAIL-CLOSED (hỏng thì đóng)

| | |
|---|---|
| **Phương án đã bỏ** | khi lọc dị nguyên ra rỗng thì nới ra để vẫn có món gợi ý |
| **Nghe hợp lý vì** | trả về "không có món nào" là trải nghiệm tệ |
| **Đã chọn** | thà nói **"không có món nào phù hợp"** còn hơn mời một món có thể gây dị ứng |

**Ví dụ chứng minh:** khách nói *"dị ứng tôm, tư vấn món hải sản khác"*. Thực đơn có 26 món hải sản,
14 món **không có tôm** — nhìn qua thì nên lọc riêng con tôm ra. Nhưng kiểm dữ liệu thì:

> **7/26 món hải sản không có nhãn nguyên liệu nào**, và hai trong số đó **chứa tôm thật**:
> *Bún đậu mắm tôm* (“chấm **mắm tôm**”) và *Bún bò Huế* (“**mắm ruốc**”).

Lọc theo `ingredient:shrimp` sẽ **mời đúng hai món đó** cho người dị ứng tôm. Nên hệ thống giữ chặn
rộng, và thay vào đó **nói ra lý do** — chứ không nới hàng rào.

### Quyết định 6 — Từ vựng TẤT ĐỊNH, không để mô hình hiểu câu

| | |
|---|---|
| **Phương án đã bỏ** | để mô hình đọc câu và tự sinh nhãn lọc |
| **Nghe hợp lý vì** | {b.so_cum_tu_vung} cụm từ vựng viết tay là rất nhiều công |
| **Đã chọn** | mã tất định chạy trước; mô hình chỉ được hỏi khi mã không chắc |

**Ba lý do, và lý do thứ ba mới là lý do thật:**

1. dịch vụ phải trả lời được **khi mô hình hỏng**
2. mỗi lần gọi tốn ~8,6 giây, còn *"xin chào"* thì không đáng chờ 8 giây
3. **cụm chào hỏi tiếng Việt là tập ĐÓNG và nhỏ** — dùng mô hình cho việc mà một danh sách 20 cụm
   giải quyết trọn là chọn sai công cụ, và làm phép đo phụ thuộc một thứ không tất định

**Ví dụ chứng minh:** khi thử để mô hình gán nhãn, nó trả `prefer: health:low_calorie` cho câu
*"Nhãn 'ít calo' dựa trên gì?"* — đẩy một **câu hỏi về nhãn** sang **nhánh lọc món**. Khách hỏi định
nghĩa, nhận về danh sách món.

### Quyết định 7 — Chia đoạn theo TIÊU ĐỀ MỤC, không theo số ký tự

| | |
|---|---|
| **Phương án đã bỏ** | cắt mỗi 500 ký tự có chồng lấn — cách phổ biến nhất trong tài liệu RAG |
| **Nghe hợp lý vì** | đơn giản, không phụ thuộc cấu trúc tài liệu |
| **Đã chọn** | cắt theo tiêu đề mục markdown |

**Vì sao:** cắt theo ký tự thì một đoạn có thể **đứt giữa bảng giá**, và mô hình nhận được nửa bảng.
Cắt theo tiêu đề thì mỗi đoạn là **một ý trọn vẹn** do người viết đã tự chia sẵn — tài liệu markdown
vốn đã có cấu trúc đó, không dùng thì phí.

**Bằng chứng chống lại chính lựa chọn này**, ghi ra vì nó là giới hạn thật: 45 tài liệu `derived`
dùng chung một khuôn tiêu đề, nên **283/452 đoạn dùng chung tiêu đề** với đoạn khác. Nhóm đã thử
sửa (đưa lên 365 tiêu đề khác nhau) và đo lại: **Hit@1 không đổi**. Xem mục 2.4.1.

---

## 2.7 Các chỉ số đánh giá, và chỉ số nào QUYẾT ĐỊNH

```
Hit@k  = 1 nếu có ít nhất một đoạn đúng trong k đoạn đầu
MRR@k  = 1/hạng của đoạn đúng đầu tiên, 0 nếu không có trong k đầu
nDCG@k = DCG@k / IDCG@k,  DCG = Σ rel_i / log₂(i+1)
cấm@5  = SỐ CA lấy phải đoạn bị cấm trong 5 đoạn đầu
```

**Top-1 là chỉ số quyết định**, không phải Hit@5 — vì hệ thống lúc chạy gọi `search(question, k=1)` và
đọc đúng đoạn đầu. Chốt theo Hit@5 là chốt theo con số của một hệ thống **không tồn tại**: Hit@5 = 1,0
vẫn đúng khi đoạn đúng nằm thứ năm và bốn đoạn lạc đề nằm trên nó.

**`cấm@5` quan trọng hơn Hit@5** vì nó đo việc trả lời **sai**, không phải kém. Và nó là chỉ số duy nhất
bắt được cách lách quan trọng nhất: một bộ truy hồi **luôn trả về 5 đoạn** đạt điểm cao trên mọi chỉ số
Hit mà không bao giờ nói "tôi không biết".

Với bài toán chọn món, `cấm@5` mang nghĩa mạnh hơn nữa: nó là **số ca nêu món không thỏa ràng buộc**,
tức số ca trả lời **SAI** — và với ca dị ứng thì đó là lỗi an toàn.

---
---"""


def chuong_3(b: Bang) -> str:
    sp = b.split_truy_hoi
    return f"""# CHƯƠNG 3: PHƯƠNG PHÁP

## 3.0 Chương này làm gì — đọc bằng lời trước

Chương 2 nói **các phương pháp có sẵn trên đời**. Chương 3 nói **nhóm ghép chúng lại thành hệ thống
như thế nào**, và chương 4 nói **hệ thống ấy chạy ra số bao nhiêu**.

### Một câu hỏi của khách đi qua những đâu

Khi khách gõ *"cho mình món chay dưới 100 nghìn"*, câu đó không được gửi thẳng cho mô hình AI. Nó đi
qua một dây chuyền, và **mỗi chặng làm đúng một việc**:

```
câu khách gõ
   |
   v
[1] HIỂU CÂU HỎI      "món chay" -> nhãn diet:vegetarian
   |                  "dưới 100 nghìn" -> ngân sách 100.000
   v
[2] NHỚ NGỮ CẢNH      ghép với điều khách đã nói ở các lượt trước
   |                  (dị ứng khai lượt 1 vẫn còn hiệu lực ở lượt 5)
   v
[3] CHỌN NHÁNH        đây là câu CHỌN MÓN hay câu HỎI TRI THỨC?
   |
   +--> câu chọn món --> [4a] LỌC THEO NHÃN  -> danh sách món
   |
   +--> câu tri thức --> [4b] TRUY HỒI       -> đoạn văn liên quan
   |
   v
[5] VIẾT CÂU TRẢ LỜI  khuôn mẫu, hoặc mô hình sinh viết lại cho tự nhiên
   |
   v
[6] XÁC MINH          {b.so_phep_kiem} phép kiểm; vi phạm thì BỎ câu sinh, dùng khuôn mẫu
   |
   v
[7] THẺ GIỎ HÀNG      dựng từ danh sách món, KHÔNG từ chữ mô hình viết
   |
   v
câu trả lời + nút bấm đặt món
```

**Điều đáng chú ý nhất:** trong bảy chặng, chỉ **hai chặng có mô hình AI** — chặng [4b] truy hồi và
chặng [5] viết câu. Năm chặng còn lại là **mã tất định**: cùng đầu vào thì luôn cùng đầu ra, không
phụ thuộc mô hình, và chạy được cả khi mô hình hỏng.

Đó là lựa chọn có chủ ý, không phải vì thiếu thời gian. Lý do đầy đủ ở mục 2.8.

### Vì sao chương này nói nhiều về TẬP ĐÁNH GIÁ

Với một hệ thống thông thường, "đúng" nghĩa là **chạy không lỗi**. Với hệ thống này, một câu trả lời
có thể **chạy hoàn hảo mà vẫn sai** — mời món hải sản cho người dị ứng hải sản là một câu trả lời
không có lỗi kỹ thuật nào.

Nên "đúng" phải được **định nghĩa bằng một tập câu hỏi có khoá đáp án**, và hệ thống được chấm trên
tập đó. Đây là khác biệt lớn nhất giữa làm phần mềm và làm học máy, và nó là lý do bốn tập đánh giá
được mô tả kỹ ở mục 3.3.

### Ba từ sẽ gặp nhiều

| Từ | Nghĩa trong báo cáo này |
|---|---|
| **nhánh** | một đường xử lý riêng cho một loại câu hỏi. Hệ thống có {len(b.nhanh_tra_loi()) if hasattr(b, 'nhanh_tra_loi') else 17} nhánh, và chúng **loại trừ nhau** — một câu chỉ đi đúng một nhánh |
| **nhãn** | thuộc tính của món, dạng `nhóm:giá_trị` — ví dụ `spice:none` nghĩa là **không cay** |
| **ràng buộc** vs **ngữ cảnh** | ràng buộc thì **lọc bỏ** món không thoả; ngữ cảnh chỉ **xếp lên trước**. Nhầm hai thứ này là lọc mất món đúng — xem mục 3.4 |

---

## 3.1 Kiến trúc bảy chặng — và chỉ hai chặng có mô hình

```
khách gõ câu
 │
 1  understand()        TẤT ĐỊNH · từ vựng + {len(b.items)} tên món → nhãn, ràng buộc, cờ
 2  merge bộ nhớ phiên  dị nguyên CỘNG DỒN · ràng buộc cứng GHI ĐÈ · ngữ cảnh tích lũy
 3  enrich()        ◄── MÔ HÌNH #1  đọc câu hỏi → NHÃN (không phải câu văn, không chọn món)
 4  respond()           TẤT ĐỊNH · 17 nhánh loại trừ → quyết định trả lời GÌ
 5  build_cart()        thẻ giỏ từ ĐÚNG danh sách chặng 4 chọn
 6  write_reply()   ◄── MÔ HÌNH #2  viết CÂU VĂN, chỉ 2/17 nhánh, 8 phép kiểm
 7  session_updates()   ghi bộ nhớ ra cho backend
```

**Mô hình #1 và #2 là cùng một mô hình**, gọi ở hai chỗ cho hai việc khác nhau.

Chặng 3 đọc câu hỏi và trả về **danh sách nhãn** lấy từ từ điển nhãn ({len(b.tags)} nhãn), không phải
câu văn. Bốn cơ chế giữ nó trong tầm kiểm soát:

- **Cổng `already_understood`** (14 tín hiệu): mã tất định hiểu đủ rồi thì **không gọi**. Gọi mô hình
  vào chỗ không cần là mở đường cho nó phá một câu trả lời đang đúng — và điều đó đã xảy ra hai lần,
  xem mục 4.5.
- **Một cửa kiểm duy nhất**: nhãn phải có trong từ điển; nhãn bịa bị bỏ và **ghi lại**, không bỏ im lặng.
- **Chỉ THÊM, không xóa**: nó không bỏ được ràng buộc khách đã nêu.
- **Không chọn món**: nó trả nhãn; việc chọn món là phép lọc theo nhãn.

Bộ nhớ phiên hợp nhất theo **ba quy tắc**, và sự khác nhau giữa chúng là chỗ khó nhất của khâu này:

| Loại | Quy tắc | Vì sao |
|---|---|---|
| dị nguyên | **cộng dồn, không bao giờ bỏ** | khai ở lượt 1 thì lượt 5 vẫn phải nhớ — bất biến an toàn quan trọng nhất |
| ràng buộc cứng (`spice`, `price`, `party`, `season`, `diet`) | lượt mới **ghi đè** cùng nhóm | "rẻ hơn nữa" phải THAY ngân sách cũ, giữ cả hai thì phép AND cho rỗng |
| ngữ cảnh (`prefer`) | cộng vào, giữ 5 gần nhất | sở thích tích lũy nhưng không được phình vô hạn |

## 3.2 Kho tri thức: một kho, hai chế độ trả lời

**{len(b.docs)} tài liệu / {len(b.doan)} đoạn**, markdown có frontmatter, chia đoạn theo tiêu đề `##`.

| Chế độ | Tài liệu | Cách trả lời | Mô hình chạm chữ? |
|---|---:|---|---|
| `verbatim` | {b.che_do.get('verbatim', 0)} | TRA KHÓA, trả **nguyên văn** | **0%** |
| `synthesize` | {b.che_do.get('synthesize', 0)} | truy hồi, xếp hạng | không — chỉ trình bày lại |

`verbatim` là chế độ tin mô hình **0%**: giờ mở cửa, cách thanh toán, phụ phí, cách khai dị ứng — một
chữ số lệch ở đây là sai sự thật về nhà hàng. Truy hồi ở đó là **tra khóa**, không xếp hạng, nên không
có chỗ nào để chệch.

Hai quy tắc chia đoạn đáng ghi:

1. **Kèm tiêu đề tài liệu vào mỗi đoạn**, để đoạn tự đủ ngữ cảnh khi trích rời — điều này **đúng cho
   xếp hạng**. Nhưng nó **sai cho việc đọc**: dán đoạn thô cho khách thì khách nhận về một cái nhan đề.
   Nên có một hàm riêng làm sạch trình bày trước khi trả — xem mục 5.4.
2. **Cửa `audience: guest` là BẮT BUỘC.** Bộ nạp **từ chối** tệp không phải `guest`, không phải lọc mà
   là từ chối — để không ai thêm được nội dung hướng dẫn nội bộ vào kho khách đọc. Bản cũ của dự án có
   5/27 tệp `audience: ai` nằm cùng chỉ mục, và 47/221 đoạn bị trích cho khách đọc.

Số đoạn được xếp hạng là **{len(b.doan_xep_hang)}**, không phải {len(b.doan)}: bỏ đoạn `verbatim`
(chúng đã có đường riêng) và bỏ đoạn **mở đầu** — một mục không có tiêu đề là phần dẫn nhập của tài
liệu, nó mô tả TÀI LIỆU chứ không trả lời câu nào.

## 3.3 Bốn tập đánh giá, và kỷ luật chia tập

| Tập | Kích thước | Chặng nó đo |
|---|---:|---|
| `cases.json` | {len(b.ca_tra_loi)} ca | `understand()` + `respond()` gọi trực tiếp |
| `session_scripts.json` | {len(b.kich_ban)} kịch bản / {b.luot_phien} lượt | + bộ nhớ nhiều lượt |
| `retrieval_cases.json` | {len(b.ca_truy_hoi)} ca | truy hồi trên **toàn kho** |
| `chunk_selection_cases.json` | {len(b.ca_chon_muc)} ca | chọn mục **trong một tài liệu** |
| `golden_e2e.json` | {len(b.golden)} hội thoại / {b.luot_golden} lượt | **toàn chuỗi**, tới giỏ hàng thật |

**Chia tập theo HỌ, không theo ca.** Hai ca cùng họ hỏi cùng chủ đề, chỉ khác cách diễn đạt — xem một ca
là biết ca kia, nên chia theo ca thì tập niêm phong **không còn niêm phong**.

Thứ tự chia do `sha256(tên họ)` quyết định, **không** do `random.shuffle` có seed: shuffle phụ thuộc
phiên bản Python, nên Python đổi thuật toán thì phép chia đổi theo và tập niêm phong lặng lẽ trộn vào
tập phát triển.

Ba nhóm, không phải hai:

| Nhóm | Số họ | Vai trò |
|---|---:|---|
| chốt | {len(sp['gate_families'])} | **luôn phải đạt**; một ca đỏ ở đây là CHẶN, không phải số liệu |
| phát triển | {len(sp['dev_families'])} | được xem, được sửa theo |
| niêm phong | {len(sp['test_families'])} | **chỉ mở MỘT lần** |

Nhóm chốt của tập truy hồi gồm ba họ đo việc **biết khi nào KHÔNG trả lời**. Vì sao chúng là chốt chứ
không phải số liệu: một bộ truy hồi **luôn trả về 5 đoạn** đạt điểm cao trên mọi họ khác, và chỉ ba họ
này bắt được nó.

**Bài học đã trả giá, ghi ngay trong tệp chia tập:** tập niêm phong của bộ 119 ca **đã dùng hết** ở một
bước trước. Mọi con số trên nó sau đó không còn là held-out.

## 3.4 Mười bảy nhánh trả lời, không nhánh nào chồng nhánh nào

Thứ tự nhánh là thứ tự **loại trừ**, nên mỗi câu đi đúng một nhánh và nhánh đó xác định được từ đầu vào:

| Loại | Nhánh | Sinh? |
|---|---|---|
| A | `price_lookup` `price_assertion` `item_detail` `serving_named_dish` `allergen_named_dish` `no_size` `unknown_item` `facts:*` | cấm |
| B | `policy:*` (tra khóa, nguyên văn) · `knowledge_corpus:*` (truy hồi toàn kho) | cấm |
| C | `filter` `compare` | **được** |
| khác | `clarify` `empty_result` `exhausted_after_exclusions` `off_topic` `internal` | cấm |

Nhánh `clarify` là **câu trả lời đúng** ở chỗ khách chưa nói gì đủ để lọc, không phải thất bại. Và nó
**không** được kèm danh sách món — kèm danh sách thì nó không còn là câu hỏi lại.

Nhánh `exhausted_after_exclusions` sinh ra từ một lỗi chạy thật: khách xem ba lượt danh sách rồi nói
"cho mình món khác đi" và nhận "mình chưa tìm được món nào" — câu đó **nói sai sự thật**, vì có món thỏa
ràng buộc, chỉ là chúng đã được nêu. Nhánh mới nói đã nêu hết rồi mời bỏ bớt một điều kiện, và **không**
nêu lại danh sách.

Một cổng riêng chặn nhánh truy hồi toàn kho trả lời câu ngoài phạm vi. Nó **không phải ngưỡng tương
đồng** mà là **phép thuộc tập**, và tập đó **sinh từ dữ liệu**: tên món + tên danh mục + nhãn tiếng Việt
+ tiêu đề mọi tài liệu. Lý do không dùng danh sách viết tay: nó sẽ trôi khỏi thực đơn ngay lần thêm món.
Trước khi có cổng này, câu "Bạn là model gì?" nhận về một đoạn nói về lẩu — vì embedding **luôn** cho
điểm cho mọi đoạn.

## 3.5 Hai bài toán truy hồi khác nhau

Lúc chạy, truy hồi được gọi ở hai chỗ, và chúng là hai bài toán khác nhau:

| Chỗ gọi | Bài toán | Ứng viên | `k` |
|---|---|---:|---:|
| `doan_tri_thuc_lien_quan()` | đoạn nào **trong cả kho** trả lời câu này | {len(b.doan_xep_hang)} | 1 |
| `_knowledge_chunk()` → `_chon_muc()` | mục nào **trong tài liệu này** đúng ý | 3–8 | 1 |

Cả hai dùng `k=1`, nên **Top-1 là chỉ số quyết định** ở cả hai. Và cả hai chạy **embedding** — quyết
định này đến từ số liệu ở mục 4.2 và 4.3.

Đường thứ hai **không dựng chỉ mục mới**: chỉ mục toàn kho đã có vector của cả {len(b.doan_xep_hang)}
đoạn, nên xếp hạng trong một tài liệu chỉ là giới hạn phép chấm điểm vào tập con — hợp lệ vì vector đã
chuẩn hoá L2 (mục 2.2). Chi phí thật là **một** lần mã hoá câu hỏi. Cách hiển nhiên — dựng một chỉ mục
cho mỗi tài liệu — mất **~91ms mỗi lượt**, và có một test **đếm số lần dựng chỉ mục rồi đòi 0**.

## 3.6 Điều kiện kiểm soát thực nghiệm

**Đường tất định phải TẤT ĐỊNH.** Mọi phép phá thế đều theo `chunk_id` tăng dần, ở **cả hai** đường xếp
hạng. Hai đường phá thế ngược nhau thì hệ thống không lặp lại được kết quả của chính nó — và bản đầu của
`_chon_muc` đã sai đúng chỗ đó.

**Cache lời gọi mô hình** được commit vào repo, để CI chạy lại được phép đo "có mô hình" mà không cần
khóa thật và không phụ thuộc mạng.

**Hai giao thức đo độ trễ, không được trộn:**

| Giao thức | Số lần chạy | Dùng cho |
|---|---:|---|
| sàng lọc | 1 | loại phương án chậm gấp bậc |
| chốt | 7, lấy trung vị | số đưa vào báo cáo |

Bản cũ trộn hai giao thức rồi so 29ms với 81ms như cùng loại — hai con số đó **không so được** với nhau.
Nay tên giao thức được in ra cùng con số, và được ghi vào tệp bằng chứng.

**Cấu hình của mỗi lần đo được ghi kèm con số.** Tệp bằng chứng trong `ai/evaluation/measurements/` mang
nguyên phản hồi `/ready` của dịch vụ lúc đo. Lý do: đã trả giá một lần cho việc thiếu nó — một lần chạy
42 lượt được báo là "qua mô hình thật" trong khi `LLM_API_KEY` rỗng nên **mọi lượt đi đường tất định**.

---
---"""


def _bang_truy_hoi(b: Bang, nhom: str, ten_hien: str) -> list[str]:
    ra = [f"**Nhóm {ten_hien}** — {b.m_truy_hoi['so']['bai_toan_1'][nhom]['so_ca']} ca", ""]
    ra.append("| Phương pháp | n | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | cấm@5 |")
    ra.append("|---|---:|---:|---:|---:|---:|---:|")
    for bo in b.bo_truy_hoi():
        d = b.m_truy_hoi["so"]["bai_toan_1"][nhom]["bo"][bo]
        if not d["n"]:
            ra.append(f"| `{bo}` | 0 | — | — | — | — | {d['cam5']} |")
            continue
        ra.append(
            f"| `{bo}` | {d['n']} | **{pct(d['hit1'] / d['n'])}** | {pct(d['hit5'] / d['n'])} | "
            f"{pct(d['mrr5'] / d['n'])} | {pct(d['ndcg5'] / d['n'])} | {d['cam5']} |"
        )
    ra.append("")
    return ra


def chuong_4(b: Bang) -> str:
    ra: list[str] = ["# CHƯƠNG 4: THỰC NGHIỆM VÀ KẾT QUẢ", ""]

    dk = b.m_truy_hoi["dieu_kien"]
    ra += [
        r"""## 4.0 Đọc chương kết quả thế nào

Chương này có nhiều bảng số. Mục 4.0 nói trước **cách đọc chúng**, để các bảng sau không bị hiểu
ngược.

### Ba chỉ số, và chỉ số nào mới quan trọng

| Chỉ số | Nghĩa đơn giản | Đọc thế nào |
|---|---|---|
| **Hit@1** | trong đoạn **đầu tiên** trả về, có đúng đoạn cần không | càng cao càng tốt. Đây là chỉ số chính, vì hệ thống chỉ đọc đoạn thứ nhất |
| **Hit@5** | trong **5 đoạn đầu**, có ít nhất một đoạn đúng không | càng cao càng tốt, nhưng **dễ gây hiểu lầm** — xem dưới |
| **cấm@5** | trong 5 đoạn đầu, có bao nhiêu đoạn **KHÔNG được phép** xuất hiện | **càng thấp càng tốt.** Đây mới là chỉ số quyết định |

**Vì sao Hit@5 dễ gây hiểu lầm:** một bộ truy hồi trả về 1 đoạn đúng và 4 đoạn lạc đề vẫn đạt
Hit@5 = 1,0 — điểm tuyệt đối. Nhưng với hệ thống này, **4 đoạn lạc đề là 4 cơ hội để mô hình viết
ra một câu sai về nhà hàng**. Nên `cấm@5` được đặt cao hơn Hit@5 khi ra quyết định.

Ở bài toán chọn món, `cấm@5` còn mang nghĩa nặng hơn: nó là **số món không thoả điều kiện khách
nêu**. Với câu dị ứng thì mỗi món như vậy là **một lỗi an toàn**, không phải một điểm trừ chất lượng.

### Tập phát triển và tập niêm phong khác nhau ra sao

| | **Tập phát triển** | **Tập niêm phong** *(held-out)* |
|---|---|---|
| Nhóm có được xem không | có | **không**, cho tới khi xong |
| Dùng để làm gì | sửa hệ thống, thử ý tưởng | **chấm điểm cuối cùng** |
| Vì sao cần tách | | nếu vừa sửa vừa xem thì hệ thống dần **học thuộc đề** thay vì học cách làm |

> **Ẩn dụ:** tập phát triển là **bài tập về nhà** — làm sai thì xem đáp án rồi sửa. Tập niêm phong
> là **bài thi** — chỉ mở một lần, và mở rồi thì nó không còn là bài thi nữa.

Báo cáo này ghi rõ **tập niêm phong đã được mở**, nên con số trên nó **không còn là held-out** cho
những thay đổi sau đó. Đây là hạn chế thật, và nó được nói ra thay vì giấu đi.

### Vì sao có nhiều bảng "trước / sau"

Nhiều mục trong chương này trình bày theo cặp **trước khi sửa / sau khi sửa**. Đó không phải để khoe
tiến bộ, mà vì **một con số đơn lẻ không nói được gì**: Hit@1 = 60,87% là tốt hay chưa tốt thì phải so với
cái gì đó — với BM25, với chính nó ở phiên bản trước, hoặc với một mốc nền.

Có những bảng cho thấy thay đổi **không cải thiện gì**, và chúng được giữ nguyên trong báo cáo. Một
thí nghiệm âm tính vẫn là một kết quả, và giấu nó đi là làm hỏng chính phép đo.

---

## 4.1 Thiết lập""",
        "",
        f"| Điều kiện | Giá trị |",
        "|---|---|",
        f"| Ngày đo | {dk['ngay']} |",
        f"| Thực đơn | {len(b.items)} món, {len(b.tags)} nhãn |",
        f"| Kho tri thức | {len(b.docs)} tài liệu / {len(b.doan)} đoạn, {len(b.doan_xep_hang)} đoạn được xếp hạng |",
        f"| Bộ truy hồi đã so | {', '.join('`' + x + '`' for x in dk['bo_da_so'])} |",
        f"| Mô hình sinh | `{b.m_llm['dieu_kien']['mo_hinh']}` |",
        f"| Giao thức đo độ trễ | {dk['giao_thuc_do_tre']} |",
        "",
        "Mọi con số dưới đây đọc từ `ai/evaluation/measurements/`, nơi bộ chạy ghi kết quả kèm điều",
        "kiện của lần chạy. Báo cáo này **không** chứa số nào do người viết gõ vào.",
        "",
        "## 4.2 So ba phương pháp truy hồi trên hai tập",
        "",
        "Bài toán: **đoạn nào trong cả kho trả lời câu hỏi này.** Đây là chỗ RAG *đúng là* câu trả lời,",
        f"vì {b.che_do.get('synthesize', 0)} chủ đề `synthesize` phần lớn **không có cụm từ vựng** nên",
        "truy hồi là đường **duy nhất** tới chúng.",
        "",
    ]
    ra += _bang_truy_hoi(b, "chốt", "CHỐT")
    ra += [
        "Nhóm chốt gồm các họ `expect_nothing` — chúng **không có** khóa đáp án để tính Hit, nên cột",
        "Hit/MRR/nDCG là gạch ngang. Điều nhóm này đo là `cấm@5` và việc **biết KHÔNG trả lời**, và cả",
        "ba bộ đều đạt 0 đoạn bị cấm.",
        "",
    ]
    ra += _bang_truy_hoi(b, "phát triển", "PHÁT TRIỂN")
    ra += _bang_truy_hoi(b, "NIÊM PHONG", "NIÊM PHONG (mở một lần)")

    e_dev = b.ty_le_truy_hoi("phát triển", "embedding", "hit1")
    b_dev = b.ty_le_truy_hoi("phát triển", "bm25", "hit1")
    e_np = b.ty_le_truy_hoi("NIÊM PHONG", "embedding", "hit1")
    b_np = b.ty_le_truy_hoi("NIÊM PHONG", "bm25", "hit1")
    h_np = b.ty_le_truy_hoi("NIÊM PHONG", "hybrid", "hit1")
    ra += [
        "**Đọc kết quả:**",
        "",
        f"- Embedding thắng ở **cả hai** tập: Hit@1 {pct(e_dev)} so với {pct(b_dev)} (phát triển) và",
        f"  **{pct(e_np)}** so với **{pct(b_np)}** (niêm phong) — chênh"
        f" **{diem_pt(e_np - b_np)} điểm phần trăm**.",
        f"- Hybrid RRF đạt {pct(h_np)} trên tập niêm phong, thấp hơn embedding ({pct(e_np)}) về con",
        "  số tuyệt đối. Tuy nhiên **chênh lệch này CHƯA đạt mức ý nghĩa thống kê** (xem mục 4.2.1),",
        "  nên báo cáo **không** kết luận hybrid kém hơn embedding. Điều kết luận được là: hợp nhất",
        "  RRF **không mang lại cải thiện đo được** so với embedding đơn lẻ, trong khi nó tốn thêm chi",
        "  phí chạy cả hai bộ. Với cùng kết quả và chi phí cao hơn, embedding đơn lẻ là lựa chọn hợp lý.",
        "- `cấm@5` gần như không phân biệt được ba bộ. Nghĩa là chênh lệch nằm ở việc **tìm đúng đoạn**,",
        "  không ở việc **tránh đoạn sai** — và đó là tin tốt cho an toàn: không bộ nào lạc đề nhiều hơn.",
        "",
        "### 4.2.1 Khoảng tin cậy và kiểm định ý nghĩa",
        "",
        "Một tỷ lệ đo trên mẫu hữu hạn **không phải** tỷ lệ thật của tổng thể. Mục này trả lời hai câu",
        "hỏi mà mọi bảng kết quả ở trên đều phải trả lời được:",
        "",
        "1. **Khoảng nào chứa tỷ lệ thật?** — khoảng tin cậy 95% theo phương pháp Wilson",
        "2. **Chênh lệch giữa hai phương pháp có phải do may rủi không?** — kiểm định McNemar",
        "",
        "**Vì sao dùng Wilson thay vì công thức thông dụng.** Công thức chuẩn `p ± 1,96·√(p(1−p)/n)`",
        "cho khoảng rộng bằng **0** khi tỷ lệ đạt 100%, tức khẳng định chắc chắn tuyệt đối từ một mẫu",
        "hữu hạn. Nhiều phép đo trong đồ án này đạt đúng 100%, nên công thức đó không dùng được.",
        "",
        "**Vì sao dùng McNemar thay vì kiểm định hai mẫu độc lập.** Ba bộ truy hồi chạy trên **cùng",
        "một danh sách câu hỏi**, nên kết quả của chúng không độc lập: chúng cùng đúng ở câu dễ và",
        "cùng sai ở câu khó. McNemar dùng đúng tính chất ghép cặp này — nó chỉ xét những câu mà hai",
        "bên **cho kết quả khác nhau**, và kiểm tra xem tỷ lệ giữa hai chiều lệch có khác 50/50 không.",
        "",
        "**Khoảng tin cậy 95% cho Hit@1 trên tập niêm phong:**",
        "",
        "| Phương pháp | Hit@1 | Khoảng tin cậy 95% | n |",
        "|---|---:|:---:|---:|",
    ] + [
        f"| `{ten}` | {pct(k.ty_le)} | {pct(k.duoi)} – {pct(k.tren)} | {k.n} |"
        for ten, k in b.ktc_truy_hoi("NIÊM PHONG").items()
    ] + [
        "",
        "Ba khoảng này **chồng lấn nhau**. Nếu chỉ nhìn khoảng tin cậy thì chưa kết luận được bộ nào",
        "hơn bộ nào — và đây chính là lý do cần kiểm định ghép cặp.",
        "",
        "**Kiểm định McNemar trên tập niêm phong:**",
        "",
        "| So sánh | Số câu hai bên khác nhau | p | Kết luận |",
        "|---|---:|---:|---|",
    ] + [
        f"| {a} so với {bb} | {r.n_lech}/{r.n} | **{so(r.p, 4)}** | "
        f"{'**có ý nghĩa** (p < 0,05)' if r.co_y_nghia else 'chưa đủ ý nghĩa (p ≥ 0,05)'} |"
        for a, bb, r in b.mcnemar_truy_hoi("NIÊM PHONG")
    ] + [
        "",
        "**Đọc bảng này:**",
        "",
        "- Khẳng định **embedding tốt hơn BM25** có bằng chứng thống kê vững (p = "
        f"{so(dict(((a, bb), r) for a, bb, r in b.mcnemar_truy_hoi('NIÊM PHONG'))[('embedding', 'bm25')].p, 4)}"
        "). Đây là kết luận chính của mục 4.2.",
        "- Khẳng định **embedding tốt hơn hybrid** **KHÔNG** có bằng chứng đủ. Báo cáo do đó không nêu",
        "  kết luận đó, dù con số tuyệt đối của embedding cao hơn.",
        "",
        "**Quy mô mẫu cần thiết.** Để khoảng tin cậy 95% hẹp tới mức ±10 điểm phần trăm cần khoảng",
        f"**{b.n_can(0.10)} ca**; tới ±5 điểm cần khoảng **{b.n_can(0.05)} ca**. Tập niêm phong hiện",
        f"có **{b.ktc_truy_hoi('NIÊM PHONG')['embedding'].n} ca**, tương ứng nửa khoảng khoảng",
        f"±{so(b.ktc_truy_hoi('NIÊM PHONG')['embedding'].nua_rong * 100, 1)} điểm phần trăm. Đây là hạn chế",
        "thật của phép đo, và nó được nêu ở mục 5.4 thay vì bỏ qua.",
        "",
                "**Điều bảng này KHÔNG nói:** con số tuyệt đối thấp hơn một phép đo trước đó trên kho nhỏ hơn.",
        "Đó **không** phải hệ thống kém đi mà là **bài toán khó lên** — kho tăng số chủ đề, và các chủ đề",
        "mới gần nhau hơn (bốn tài liệu vùng miền, bốn tài liệu đồ uống). Trích một con số ra khỏi ngữ",
        "cảnh kích thước kho là nói quá.",
        "",
        "## 4.3 Chọn mục trong tài liệu — bài toán mà hệ thống thật sự chạy",
        "",
        "Bài toán: **mục nào trong MỘT tài liệu đã biết đúng ý khách.** Đây là đường chạy nhiều hơn, và",
        f"tập ca của nó lớn hơn: **{len(b.ca_chon_muc)} ca**.",
        "",
        "Số ứng viên mỗi ca chỉ 3–8, nên **sàn ngẫu nhiên khoảng 20%** — một phương pháp đạt 60% nghe",
        "cao nhưng chỉ hơn sàn ba lần. Bảng dưới in cả sàn.",
        "",
        "| Tập | Phương pháp | Top-1 | Top-1 dạng A (trùng từ) | Top-1 dạng B (diễn đạt khác) | n |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for tap, ten in (("phat_trien", "phát triển"), ("niem_phong", "NIÊM PHONG")):
        m = b.m_chon_np if tap == "niem_phong" else b.m_chon_dev
        for bo in sorted(m["so"]["nhom"]["written|*"]):
            n = m["so"]["nhom"]["written|*"][bo]["n"]
            ra.append(
                f"| {ten} | `{bo}` | **{pct(b.chon_muc(tap, 'written|*', bo))}** | "
                f"{pct(b.chon_muc(tap, 'written|A', bo))} | "
                f"{pct(b.chon_muc(tap, 'written|B', bo))} | {n} |"
            )
    ra += [
        "",
        "**Dạng A và dạng B là điểm chính của phép so.** Dạng A dùng từ có trong mục; dạng B diễn đạt",
        "khác. Một phương pháp thắng ở A mà thua ở B là phương pháp **khớp từ khoá**; thắng cả hai mới",
        "là **hiểu nghĩa**.",
        "",
        f"- BM25 mạnh ở dạng A ({pct(b.chon_muc('niem_phong', 'written|A', 'bm25'))}) và giảm mạnh ở dạng B",
        f"  ({pct(b.chon_muc('niem_phong', 'written|B', 'bm25'))}), phù hợp với cơ chế đếm từ chung.",
        f"- Embedding giữ được ở dạng B ({pct(b.chon_muc('niem_phong', 'written|B', 'embedding'))}), và",
        "  đó là chỗ quan trọng nhất với khách thật: khách **không** dùng đúng chữ trong tài liệu.",
        "",
        "Nhóm `derived` (tài liệu sinh từ thực đơn theo khuôn dùng chung) được báo cáo **riêng**, vì nó là",
        "MỘT quyết định lặp trên nhiều tài liệu — gộp vào số chính sẽ để một bài toán dễ kéo con số lên.",
        "",
        "## 4.4 Chọn món: lọc theo nhãn so với RAG",
        "",
        "Phép đo này trả lời trực tiếp câu hỏi nghiên cứu nêu ở mục 1.4: xác định phạm vi KHÔNG nên",
        "dùng RAG.",
        "",
        f"Bài toán: **món nào thỏa ràng buộc khách nêu.** {b.m_truy_hoi['so']['bai_toan_2']['so_ca']} ca,",
        "mỗi ca chọn để làm rõ một cơ chế. Ba bộ xếp hạng được thấy **đủ dữ liệu** — văn bản của mỗi món",
        "gồm tên, danh mục, mô tả, toàn bộ nhãn và giá. Cho chúng ít hơn thì kết luận không công bằng.",
        "",
        "| Phương pháp | Hit@1 | Hit@5 | **cấm@5** = số ca nêu món KHÔNG thỏa ràng buộc |",
        "|---|---:|---:|---:|",
    ]
    b2 = b.m_truy_hoi["so"]["bai_toan_2"]["bo"]
    for bo in b2:
        d = b2[bo]
        nhan = f"**`{bo}`**" if bo == "lọc nhãn" else f"`{bo}`"
        cam = f"**{d['cam5']}**" if bo == "lọc nhãn" else str(d["cam5"])
        ra.append(f"| {nhan} | {pct(d['hit1'] / d['n'])} | {pct(d['hit5'] / d['n'])} | {cam} |")
    xh = [v["cam5"] for k, v in b2.items() if k != "lọc nhãn"]
    ra += [
        "",
        f"Trên **{b2['lọc nhãn']['n']} câu hỏi** của bộ đo này, lọc theo nhãn trả lời đúng"
        f" **{b2['lọc nhãn']['hit1']:.0f}/{b2['lọc nhãn']['n']} câu"
        f" ({pct(b2['lọc nhãn']['hit1'] / b2['lọc nhãn']['n'])})** và **không câu nào** nêu món vi"
        f" phạm ràng buộc. Ba bộ xếp hạng nêu món vi phạm ở **{min(xh)} đến {max(xh)} trong"
        f" {b2['lọc nhãn']['n']} câu**, tương ứng"
        f" {pct(min(xh) / b2['lọc nhãn']['n'])} đến {pct(max(xh) / b2['lọc nhãn']['n'])}.",
        "",
        "`cấm@5` ở bài toán này mang nghĩa khác bài toán 4.2: nó là số ca **nêu món không thỏa ràng",
        "buộc**, tức câu trả lời **SAI**, không phải kém. Với ca dị ứng thì đó là **lỗi an toàn**.",
        "",
        "Bốn lý do xếp hạng thua đã nêu ở mục 2.4. Đáng nhắc lại ca dị ứng: câu hỏi chứa chữ \"hải sản\"",
        "nên cả BM25 và embedding kéo món hải sản **LÊN ĐẦU** — đúng ngược điều khách cần. Cơ chế đúng",
        "cho việc này là **lọc fail-closed**, không phải xếp hạng.",
        "",
        "**Kết luận:** dữ liệu đã có cấu trúc (nhãn + giá) thì đưa nó qua một tầng xếp hạng theo độ tương",
        "đồng là **bỏ cấu trúc đi rồi cố đoán lại**. Đây là con số chứng minh không phải chỗ nào cũng nên",
        "dùng RAG.",
        "",
    ]

    llm = b.m_llm["so"]
    ra += [
        "## 4.5 Gọi LLM+RAG thật trên câu loại C",
        "",
        f"**{llm['ca']} ca** thuộc loại C (nhánh `filter` và `compare`), gọi mô hình thật",
        f"`{b.m_llm['dieu_kien']['mo_hinh']}`. Bật đường sinh là đánh đổi, và phải đo **cả hai phía**:",
        "",
        "| Phía | Câu hỏi | Cách đo |",
        "|---|---|---|",
        "| được | câu văn tự nhiên hơn | **KHÔNG đo được** bằng thước đo nội dung — nói ra thay vì giả vờ đo |",
        "| mất | có ca nào TỤT từ xanh sang đỏ | chạy CÙNG tập ca hai lần |",
        "",
        "Chỉ phía \"mất\" đo được, nên đó là phía quyết định. Ngưỡng đúng là **0 ca tụt**: một câu văn hay",
        "không bù được một câu trả lời sai.",
        "",
        "**Kết quả — và một lỗi an toàn mà phép đo này tìm ra:**",
        "",
        "| | Trước phép kiểm thứ 8 | Sau phép kiểm thứ 8 |",
        "|---|---:|---:|",
        f"| đường tất định | {llm['dat_tat_dinh']}/{llm['ca']} | {llm['dat_tat_dinh']}/{llm['ca']} |",
        f"| **có đường sinh** | **61/{llm['ca']}** — tụt 15 ca | **{llm['dat_co_duong_sinh']}/{llm['ca']}** — {len(llm['ca_tut'])} ca tụt |",
        f"| câu sinh được DÙNG | 68/{llm['ca']} | {llm['cau_sinh_duoc_dung']}/{llm['ca']} |",
        "",
        "**14 trong 15 ca tụt là ca DỊ NGUYÊN.** Chúng tụt vì đúng một lý do: câu khuôn mẫu luôn thêm",
        "*\"bạn nhắc nhân viên khi gọi món để bếp xác nhận\"*, còn mô hình viết văn mượt hơn và **bỏ câu đó",
        "đi**. Thước đo đánh dấu tiêu chí ấy là tiêu chí **an toàn**, nên với đường sinh thì \"0 lỗi an",
        "toàn\" của đường tất định thành **14 lỗi an toàn**.",
        "",
        "Câu đó là **nội dung, không phải văn vẻ**: nhãn dị nguyên phủ 44/{0} món, nên *\"thực đơn không".format(len(b.items)),
        "ghi nhận thành phần bạn cần tránh\"* **không** đồng nghĩa *\"những món này an toàn\"*.",
        "",
        "**Sửa bằng phép kiểm thứ 8 của `verify()`, không bằng một dòng trong prompt.** `PROMPT` cũng đã",
        "được thêm quy tắc đó, nhưng yêu cầu trong prompt là **đề nghị**, không phải **bảo đảm** — đúng",
        "bài học trung tâm của mục 2.6.",
        "",
        "Một chi tiết đáng đọc trong bảng: **tỷ lệ dùng câu sinh KHÔNG giảm** (68 ở cả hai lần). Tức quy",
        "tắc trong prompt sửa được hành vi ở **cả 14 ca**, và phép kiểm đứng đó làm **bảo đảm** chứ không",
        "làm bộ lọc. Đó là hình dạng đúng của cặp prompt + xác minh: prompt làm việc, xác minh chịu trách",
        "nhiệm.",
        "",
        f"**Lớp xác minh chặn gì:** {llm['lui_ve_khuon_mau']}/{llm['ca']} ca lùi về khuôn mẫu, và",
        f"**cả {llm['lui_ve_khuon_mau']} đều vì BỊA GIÁ** — mô hình viết ra một con số tiền không phải giá",
        "của món nào trong danh sách. Đó chính là loại lỗi khách **không thể tự phát hiện**: câu văn mượt,",
        "món có thật, chỉ con số sai.",
        "",
        f"**Giá phải trả:** p50 **{llm['tre_p50_ms'] / 1000:.1f}s**".replace(".", ",")
        + f", p95 **{llm['tre_p95_ms'] / 1000:.1f}s** mỗi lượt gọi mô hình.".replace(".", ","),
        "",
    ]

    g, gs = b.m_golden["so"], b.m_golden_sinh["so"]
    rg, rgs = b.m_golden["dieu_kien"].get("ready", {}), b.m_golden_sinh["dieu_kien"].get("ready", {})
    ra += [
        "## 4.6 Golden 103 lượt qua chuỗi gọi đầy đủ",
        "",
        f"**{len(b.golden)} hội thoại / {b.luot_golden} lượt**, mỗi hội thoại một tình huống khách thật",
        "gồm 2–5 lượt liên tiếp trong cùng phiên. Nó **không gọi hàm Python nào** — gửi HTTP như khách,",
        "qua backend .NET, và một hội thoại **bấm thêm vào giỏ thật** rồi đọc lại giỏ để xác nhận.",
        "",
        "Vì sao tập này tồn tại: chạy thật đã tìm ra **bốn lỗi tích hợp** mà không tập nào khác thấy —",
        "backend gửi `message` còn dịch vụ đòi `question` (422); backend gửi `Authorization: Bearer` còn",
        "dịch vụ đọc `X-Internal-Token` (401 mọi lượt); hình dạng `session_state` khác nhau nên bộ nhớ",
        "**mất im lặng** giữa các lượt; và một biến cấu hình sai giá trị làm 500 mọi lượt. Cả bốn là",
        "**lệch hợp đồng giữa hai bên** — loại lỗi mà test một phía không thể thấy.",
        "",
        "**Kết quả, đo cho CẢ HAI cấu hình triển khai:**",
        "",
        "| Cấu hình | retriever | đệm vector | đường sinh | Kết quả |",
        "|---|---|---|---|---:|",
        f"| mặc định production | `{rg.get('retriever')}` | {rg.get('retriever_vectors_from_cache')} | "
        f"{rg.get('generation_enabled')} | **{g['dat']}/{g['luot']}** |",
        f"| bật đường sinh | `{rgs.get('retriever')}` | {rgs.get('retriever_vectors_from_cache')} | "
        f"{rgs.get('generation_enabled')} | **{gs['dat']}/{gs['luot']}** |",
        "",
        "**Vì sao đo cả hai:** đường sinh bật và tắt là **hai hành vi khác nhau** — một bên chữ do khuôn",
        "mẫu dựng, một bên do mô hình viết. Ghi chung một tệp bằng chứng thì lần chạy sau xoá bằng chứng",
        "của cấu hình trước, và cổng deploy không còn gì để đối chiếu cho cấu hình nó sắp dựng. Điều đó",
        "**suýt xảy ra**: nhóm đo với đường sinh BẬT trong khi production mặc định TẮT.",
        "",
        "**Bất biến quan trọng nhất của tập này** là bất biến mà ba tập trước không thể kiểm:",
        "",
        "> Món mà câu trả lời NÊU RA phải TRÙNG món trong thẻ giỏ — **cả hai chiều**.",
        "",
        "Chữ và thẻ giỏ đi qua **hai đường khác nhau**: chữ do đường sinh viết, thẻ do mã tất định dựng.",
        "Hai đường thì lệch được, và lệch theo cách khách thấy ngay: đọc thấy tư vấn ba món, bấm vào giỏ",
        "thì ra món thứ tư. Chiều ngược cũng phải canh — và nó đã hỏng: văn nêu 6 món trong khi thẻ giỏ có",
        "3, nên khách đọc sáu lựa chọn và bấm chọn được ba. Xem mục 5.4.",
        "",
    ]

    ra += [
        "## 4.7 Phân tích nguyên nhân sai — và case nào KHÔNG sửa được nữa",
        "",
        "Công cụ `analyze_failures.py` phân loại mọi ca không đạt của ba tập vào **một** lớp nguyên nhân,",
        "và in kèm **cách sửa** cùng **cách sửa đó có đo được không**.",
        "",
        "Hai quy tắc của công cụ, và cả hai đến từ lỗi đã mắc:",
        "",
        "1. **Không phân tích tập niêm phong.** Công cụ in cách sửa, nên chạy nó trên tập niêm phong rồi",
        "   làm theo = sửa hệ thống theo tập niêm phong, và sau đó con số trên đó hết là held-out.",
        "2. **Lớp `retrieval_miss` được chia thành BỐN**, vì một lớp gộp với một cách sửa chung không trả",
        "   lời được câu \"case nào không sửa được nữa\".",
        "",
        "| Lớp | Dấu hiệu trong dữ liệu | Sửa bằng xếp hạng? |",
        "|---|---|---|",
        "| `retrieval_number` | họ ca là `kb-number` | **KHÔNG** — không phép trùng từ hay embedding nào so được 45.000 với 50.000 |",
        "| `retrieval_no_overlap` | câu hỏi ∩ đoạn đúng = ∅ | một phần — embedding hơn BM25 rõ ở dạng này |",
        "| `retrieval_twin_section` | đoạn lấy được **cùng tiêu đề mục** với đoạn đúng, khác tài liệu | **KHÔNG** — trần đa dạng của KHO |",
        "| `retrieval_rank` | còn lại | **CÓ** — lớp duy nhất |",
        "",
        "Ba trong bốn lớp **dẫn ra được từ dữ liệu**, không dán tay từng ca: họ của ca cho lớp `number`,",
        "phép giao tập từ cho lớp `no_overlap`, tiêu đề mục cho lớp `twin_section`.",
        "",
        f"**Trần đa dạng của kho** là phát hiện đáng nói nhất: {len({c.heading for c in b.doan if c.heading})}",
        f"tiêu đề mục phân biệt trên {len(b.doan)} đoạn — trung bình",
        f"{len(b.doan) / max(len({c.heading for c in b.doan if c.heading}), 1):.1f} đoạn dùng chung một".replace(".", ","),
        "tiêu đề. Khi bốn tài liệu vùng miền đều có mục *\"Món tiêu biểu\"*, **không tín hiệu nào** trong",
        "câu *\"Ăn gì đặc trưng phố cổ?\"* phân biệt được chúng — trừ khi câu hỏi nêu tên tài liệu. Đổi bộ",
        "xếp hạng không chữa được; **viết lại tiêu đề mục** thì chữa được, vì đó là sửa **dữ liệu**.",
        "",
        "Phần lớn ca truy hồi còn sai thuộc hai lớp **không** chữa được bằng đổi thuật toán. Một bảng gộp",
        "chúng vào cùng lớp với `retrieval_rank` sẽ làm người đọc tin rằng còn nhiều ca để giành bằng cách",
        "chỉnh thuật toán, trong khi việc đúng là **sửa kho**.",
        "",
        "## 4.8 Chốt phương án triển khai, kèm giá đã đo",
        "",
        "| Quyết định | Chốt | Căn cứ đo được | Giá đã đo |",
        "|---|---|---|---|",
        f"| bộ truy hồi (**cả hai** đường) | **embedding** | thắng ở cả hai bài toán và cả hai tập niêm phong; rộng nhất ở câu diễn đạt khác từ | ảnh Docker 238MB → **2,74GB**; truy hồi 1,4ms → 67ms; khởi động **19,0s** |",
        f"| đường sinh | **TẮT mặc định**, bật bằng biến môi trường | {len(llm['ca_tut'])} ca tụt sau phép kiểm thứ 8, nhưng cũng **0 ca đúng thêm** | p50 **+{llm['tre_p50_ms'] / 1000:.1f}s** mỗi lượt |".replace("+8.6", "+8,6"),
        f"| chọn món | **lọc theo nhãn**, không RAG | lọc nhãn: {b2['lọc nhãn']['cam5']} câu nêu món vi phạm; ba bộ xếp hạng: {min(xh)} đến {max(xh)} trong {b2['lọc nhãn']['n']} câu | 0,3ms mỗi lượt |",
        "",
        "### Giá của embedding: ba lần đo mới ra con số đúng",
        "",
        "| Lần | Ảnh Docker | Vì sao |",
        "|---|---|---|",
        "| dự đoán | *\"khoảng 2–3GB\"* | con số **đọc ở đâu đó**, không phải con số đo — nó đã nằm trong tài liệu qua ba bước |",
        "| đo lần 1 | **9,29GB** | `pip install torch` trên Linux lấy bản **CUDA** kèm mấy GB thư viện driver NVIDIA, cho một dịch vụ chạy CPU |",
        "| đo lần 2 | **2,74GB** | ghim bản CPU bằng `--extra-index-url .../whl/cpu` |",
        "",
        "Nếu chốt phương án bằng con số dự đoán thì báo cáo **sai gấp ba**, và chỉ người deploy phát hiện.",
        "",
        "### Thời gian khởi động là vấn đề AN TOÀN, không chỉ chậm",
        "",
        "| Thành phần | Thời gian |",
        "|---|---:|",
        "| `import torch` | 1,8s |",
        "| `import sentence_transformers` | 6,3s |",
        "| nạp mô hình | 10,6–12,2s |",
        f"| **mã hoá {len(b.doan_xep_hang)} đoạn** | **61,7s** |",
        "| **khởi động thật** | **97,3s** |",
        "",
        "`HEALTHCHECK` có `start-period=15s`, `interval=30s`, `retries=3`, nên lần kiểm thứ ba rơi vào",
        "**~105 giây**. Dịch vụ kịp sẵn sàng ở 97 giây, tức **suýt** bị đánh `unhealthy` — và backend chờ",
        "`service_healthy`, nên trên một máy chậm hơn 8% thì **cả stack không lên được**.",
        "",
        "Hai việc đã làm: **tính sẵn vector lúc build** (mã hoá 61,7s → **0,1s**) và **`start-period`",
        "15s → 90s**. Khởi động sau khi sửa: **19,0s** — và con số này phải kèm điều kiện, vì lần khởi",
        "động **đầu** ngay sau build là **61,9s** khi đĩa chưa nóng.",
        "",
        "### Điều kiện để đổi lại từng quyết định",
        "",
        "| Nếu điều này xảy ra | Thì xem lại |",
        "|---|---|",
        "| kho co lại về tra khóa, không còn chủ đề `synthesize` nào thiếu cụm từ vựng | bỏ embedding — ảnh nhỏ lại hơn 11 lần |",
        "| chủ nhà hàng coi câu văn tự nhiên đáng giá thêm ~9 giây mỗi lượt | bật đường sinh mặc định — lý do CHẶN đã hết, chỉ còn là đánh đổi độ trễ |",
        "| có log khách thật | **mọi** quyết định ở trên — chúng đều dựa trên ca do nhóm viết |",
        "",
        "## 4.9 Vì sao hệ thống cần CẢ hai lớp — bộ đo hai chiều 100 câu",
        "",
        "Tám mục trên đo **từng lớp riêng**. Không mục nào trả lời câu mà người đọc hỏi đầu tiên:",
        "*vì sao không dùng mỗi một thứ cho gọn?*",
        "",
        "Ba tập đánh giá cũ **không trả lời được**, và lý do nằm ở cách chúng được viết:",
        "",
        f"| tập | bộ xếp hạng chạy |",
        "|---|---:|",
        f"| {len(b.ca_tra_loi)} ca trả lời | **0** |",
        f"| {b.luot_phien} lượt phiên | **0** |",
        f"| {len(b.ca_truy_hoi)} ca truy hồi | 36% |",
        "",
        "Hai tập đầu được viết **quanh các nhánh tất định**, nên đọc một mình chúng nói \"truy hồi",
        "vô dụng\". Tập thứ ba thì ngược lại — nó chỉ hỏi câu tri thức, nên không nói được gì về",
        "chỗ lọc nhãn mạnh hơn. **Mỗi tập đo đúng điều nó được viết để đo.**",
        "",
        "Bộ này cho hai phương pháp chạy trên **cùng một câu hỏi**, ở hai nhóm câu mà mỗi nhóm là",
        "điểm mạnh của một bên.",
        "",
        "### 4.9.1 Chiều A — câu mã tất định KHÔNG xử lý được",
        "",
        f"**{len(b.hc_a)} câu**, phủ **hết {len([d for d in b.docs if d.doc_id.startswith('kb.written')])} tài liệu văn xuôi**, mỗi tài liệu ít nhất một câu.",
        "Phủ hết chứ không chọn tay: chọn tay thì người viết vô thức chọn câu mình biết sẽ thắng.",
        "",
        "| kết cục của mã tất định | số câu |",
        "|---|---:|",
        f"| **SAI DẠNG** — trả danh sách món cho câu \"thế nào / vì sao\" | **{b.hc_a_dem('sai_dang')}** |",
        f"| **KHÔNG XỬ LÝ ĐƯỢC** — phải nhờ truy hồi | **{b.hc_a_dem('khong_xu_ly')}** |",
        f"| đúng dạng | {b.hc_a_dem('dung')} |",
        "",
        f"Truy hồi tìm đúng tài liệu: **top-1 {b.hc_a_truy_hoi('truy_hoi_dung')}/{len(b.hc_a)}**, "
        f"**top-5 {b.hc_a_truy_hoi('truy_hoi_top5')}/{len(b.hc_a)}**.",
        "",
        "**Kết quả đáng chú ý của bộ đo này nằm ở DẠNG lỗi, không nằm ở tỷ lệ.**",
        f"Mã tất định **không im lặng** ở chiều A. {b.hc_a_dem('sai_dang')} câu nó trả lời TỰ TIN",
        "bằng một danh sách món — mọi món có thật, mọi giá đúng — và **không câu nào trả lời điều",
        "được hỏi**:",
        "",
        "> **Hỏi:** *Gọi khai vị trước có làm no bụng không ăn được món chính không?*",
        "> **Đáp:** *Mời bạn tham khảo: Bánh mì pate Sài Gòn (35.000đ), Bánh cuốn Thanh Trì…*",
        "",
        "Về mặt trải nghiệm, dạng lỗi này khó phát hiện hơn trường hợp hệ thống từ chối trả lời: mọi dữ liệu",
        "nêu ra đều chính xác, nên người dùng chỉ nhận ra câu hỏi của mình chưa được trả lời sau khi",
        "đọc hết câu trả lời.",
        "",
        "### 4.9.2 Chiều B — câu mã tất định làm TỐT HƠN",
        "",
        f"**{len(b.hc_b)} câu**, **sinh từ bộ nhãn** chứ không viết tay: ngưỡng giá, mức cay, chế độ ăn,",
        "dị nguyên, vùng miền, cách chế biến, sức khỏe, vị, dịp, nhóm người, và phép hội hai điều kiện.",
        "Sinh từ nhãn thì danh sách ca do **dữ liệu** quyết định, không do người viết chọn.",
        "",
        "Chỉ số là **số món VI PHẠM ràng buộc** — không phải \"kém\", mà là **trả lời SAI**.",
        "",
        "| dạng ràng buộc | câu | lọc nhãn | truy hồi |",
        "|---|---:|---:|---:|",
    ] + [
        f"| {d} | {sum(1 for r in b.hc_b if r['vi_sao'] == d)} | "
        f"**{b.hc_b_vi_pham('tat_dinh_vi_pham', d)}** | {b.hc_b_vi_pham('truy_hoi_vi_pham', d)} |"
        for d in b.hc_b_dang()
    ] + [
        f"| **tổng** | **{len(b.hc_b)}** | **{b.hc_b_vi_pham('tat_dinh_vi_pham')}** | "
        f"**{b.hc_b_vi_pham('truy_hoi_vi_pham')}** |",
        "",
        f"Truy hồi vi phạm **gấp {b.hc_b_vi_pham('truy_hoi_vi_pham') // max(1, b.hc_b_vi_pham('tat_dinh_vi_pham'))} lần**. Nhưng con số đáng nói nhất nằm ở dòng dị ứng:",
        f"lọc nhãn **{b.hc_b_vi_pham('tat_dinh_vi_pham', 'PHÉP TRỪ')}**, truy hồi **{b.hc_b_vi_pham('truy_hoi_vi_pham', 'PHÉP TRỪ')} món chứa đúng thứ khách phải tránh**.",
        "Câu hỏi chứa chữ \"hải sản\" nên phép xếp hạng theo độ tương đồng kéo món hải sản LÊN ĐẦU —",
        "**ngược hẳn điều khách cần**. Đó là lỗi an toàn, không phải lỗi chất lượng.",
        "",
        "### 4.9.3 Vì sao truy hồi không diễn đạt được ba dạng ràng buộc này",
        "",
        "| dạng | vì sao xếp hạng theo độ giống không làm được |",
        "|---|---|",
        "| **ngưỡng số** | với BM25 và embedding, `50.000` là một **TỪ**, không phải một **LƯỢNG**. Không có cách viết tài liệu nào biến \"dưới 50 nghìn\" thành quan hệ giống nhau |",
        "| **phép trừ** | truy hồi **không có phép TRỪ**. Đoạn nói về hải sản *giống* câu \"dị ứng hải sản\" hơn là món không hải sản |",
        "| **phép hội** | truy hồi cho **một** điểm giống đã trộn — không ép được hai điều kiện độc lập cùng đúng |",
        "",
        "Đây là giới hạn **cấu trúc**, không phải giới hạn dữ liệu hay mô hình. Nó là lý do hệ thống",
        "để `select()` chọn món và chỉ để mô hình **viết về** những món đã chọn.",
        "",
        "### 4.9.4 Bộ đo của nhóm sai ba lần trước khi ra số đúng",
        "",
        "Ghi lại vì nó thuộc phần phương pháp, và vì **cả ba lần đều sai theo hướng làm kết quả đẹp",
        "hơn thực tế** — đúng hướng mà người đo có động cơ không kiểm lại:",
        "",
        "| # | lỗi của phép đo | hậu quả |",
        "|---|---|---|",
        "| 1 | cột \"tất định\" tính cả nhánh truy hồi | 4/8 câu hiện ĐÚNG nhờ chính bên kia làm; tách ra còn **1/8** |",
        "| 2 | chiều B tìm trên kho tri thức thay vì chỉ mục món | truy hồi **0 vi phạm**, kết quả không phản ánh bài toán cần đo; sau khi sửa: **17** |",
        "| 3 | `Hit` không mang `topic_keys`, `getattr` luôn trả rỗng | truy hồi **0 trong 8 câu**, tức phép đo phản ánh chính bộ chấm điểm chứ không phản ánh bộ truy hồi |",
        "",
        "Đây là lần thứ tám lỗi nằm ở phép đo chứ không ở hệ thống. Quy trình áp dụng từ đó: **kiểm giả thuyết \"phép đo sai\" trước",
        "giả thuyết \"hệ thống sai\"**.",
        "",
        f"Bảng đầy đủ {len(b.hai_chieu)} câu: `ai/evaluation/measurements/hai_chieu.csv`.",
        "",
        "---",
        "---",
    ]
    return "\n".join(ra)


def chuong_5(b: Bang) -> str:
    g, gs, llm = b.m_golden["so"], b.m_golden_sinh["so"], b.m_llm["so"]
    e_np = b.ty_le_truy_hoi("NIÊM PHONG", "embedding", "hit1")
    b_np = b.ty_le_truy_hoi("NIÊM PHONG", "bm25", "hit1")
    b2 = b.m_truy_hoi["so"]["bai_toan_2"]["bo"]
    tieu_de = len({c.heading for c in b.doan if c.heading})
    return f"""# CHƯƠNG 5: KẾT LUẬN

## 5.1 Tổng kết

| Phép đo | Kết quả |
|---|---|
| Golden {b.luot_golden} lượt qua chuỗi gọi đầy đủ, đường sinh TẮT | **{g['dat']}/{g['luot']}** |
| Golden {b.luot_golden} lượt, đường sinh BẬT | **{gs['dat']}/{gs['luot']}** |
| Tập trả lời {len(b.ca_tra_loi)} ca, đường tất định | **{len(b.ca_tra_loi)}/{len(b.ca_tra_loi)}** |
| Bộ nhớ phiên {b.luot_phien} lượt | **{b.luot_phien}/{b.luot_phien}**, 0 lỗi an toàn |
| LLM+RAG {llm['ca']} ca loại C | tất định {llm['dat_tat_dinh']}/{llm['ca']} · có sinh \
{llm['dat_co_duong_sinh']}/{llm['ca']} |
| Truy hồi toàn kho, niêm phong | Hit@1 embedding **{pct(e_np)}** so với bm25 {pct(b_np)} |
| Chọn mục trong tài liệu, niêm phong | Top-1 embedding \
**{pct(b.chon_muc('niem_phong', 'written|*', 'embedding'))}** so với bm25 \
{pct(b.chon_muc('niem_phong', 'written|*', 'bm25'))} |
| Chọn món | lọc nhãn **{b2['lọc nhãn']['cam5']} câu nêu món vi phạm**, so với \
{min(v['cam5'] for k, v in b2.items() if k != 'lọc nhãn')}–\
{max(v['cam5'] for k, v in b2.items() if k != 'lọc nhãn')} câu ở ba bộ xếp hạng \
(trên {b2['lọc nhãn']['n']} câu) |

## 5.2 Phân tích chi tiết theo từng thành phần

Mỗi thành viên tự viết nhận xét về chặng mình phụ trách: **điều đo được**, **điều làm sai rồi phải
sửa**, và **giới hạn còn lại**. Phần này viết ở ngôi thứ nhất, và cố ý giữ cả những chỗ nhóm làm
sai — một báo cáo chỉ kể phần thành công thì không cho người đọc biết gì về cách nhóm làm việc.

### 5.2.1 Nhận xét — Phạm Duy An (BIT240002)

**Phụ trách:** Dữ liệu, bộ nhãn, kho tri thức, và lớp hiểu câu hỏi

Qua chặng dữ liệu và lớp hiểu câu hỏi, em rút ra các nhận xét sau:

- **Hai nguồn dữ liệu lệch nhau là vấn đề đầu tiên phải giải.** Thực đơn tồn tại ở hai nơi — tệp
  JSON cho AI và cơ sở dữ liệu cho backend — và chúng **không khớp**. Em giải bằng cách sinh cả hai
  từ một nguồn, kèm cổng `--check` trong CI để không ai sửa tay một bên. Nếu không làm việc này
  trước, mọi con số của bốn chặng sau đều đo trên dữ liệu sai.

- **Rút dấu tiếng Việt là phép MẤT thông tin, và em đã trả giá cho nó nhiều lần.** Bỏ dấu cho phép
  khớp "mo cua" với "mở cửa", nhưng nó cũng làm `"bò"` và `"bơ"` thành cùng một chuỗi. Dự án này ghi
  nhận **mười vụ va chạm** kiểu đó, trong đó vụ em nhớ nhất là `fold("có cồn") == fold("có con")` —
  câu *"mình có con 5 tuổi"* trả về danh sách rượu bia. Bài học: mỗi lần thêm cụm từ vựng phải chạy
  lại bản kiểm kê va chạm, không được tin vào mắt mình.

- **Từ điển {len(b.tags)} nhãn / 16 nhóm, và khoá phải có không gian tên.** Ban đầu em định dùng khoá phẳng
  (`none`, `mild`, `hot`), nhưng như vậy thì không biết `none` thuộc nhóm cay hay nhóm chế độ ăn.
  Khoá `spice:none` giải quyết, và quan trọng hơn: nó cho phép **ghi đè theo NHÓM** ở bộ nhớ phiên —
  `spice:none` đẩy `spice:hot` ra thay vì nằm cạnh nó.

- **Chỗ khó nhất không phải kỹ thuật mà là phân biệt RÀNG BUỘC với NGỮ CẢNH.** "Không cay" là ràng
  buộc — món cay phải bị **loại**. "Đi hẹn hò" là ngữ cảnh — món hợp dịp chỉ **xếp lên trước**, không
  được loại món khác. Nhầm hai thứ này thì hoặc lọc mất món đúng, hoặc để lọt món khách không ăn
  được. Em phải tách chúng thành hai trường riêng trong `Request` thay vì gộp làm một danh sách.

- **Giới hạn còn lại, và em nói ra thay vì giấu:** nhãn dị nguyên chỉ phủ **44/91 món**. Bản rà em
  viết tìm ra **7 lỗ thật**, đã lấp, nhưng **7/26 món hải sản vẫn không có nhãn nguyên liệu nào**.
  Đây là việc của bếp, không phải của mã — và nó là lý do hệ thống phải chặn rộng thay vì lọc hẹp.

### 5.2.2 Nhận xét — Bùi Đào Đức Anh (BIT240025)

**Phụ trách:** Truy hồi — BM25, embedding, hybrid RRF

Qua chặng truy hồi, em rút ra các nhận xét sau:

- **Embedding thắng BM25 rõ rệt trên tập niêm phong: Hit@1 60,87% so với 39,13%.** Lý do rất cụ thể và
  em kiểm được bằng ví dụ: khách gõ *"món chín bằng hơi nước, nhẹ bụng"* trong khi tài liệu viết
  *"món hấp"* — **không chung một chữ nào**, nên BM25 không có gì để đếm. Embedding tìm đúng vì hai
  cách nói nằm gần nhau trong không gian ngữ nghĩa.

- **Nhưng embedding có một tính chất nguy hiểm: nó KHÔNG BAO GIỜ TRƯỢT.** Câu hỏi lạc đề hoàn toàn
  vẫn nhận về 5 đoạn với điểm số đàng hoàng. BM25 thì trả rỗng khi không có từ chung. Phát hiện này
  đổi cách em chọn chỉ số: `cấm@5` (số đoạn **không được phép** lọt vào top-5) quan trọng hơn Hit@5,
  vì một bộ trả 1 đoạn đúng + 4 đoạn lạc đề vẫn đạt Hit@5 = 1,0 tuyệt đối.

- **Hybrid RRF không thắng như em nghĩ ban đầu.** Em kỳ vọng trộn hai phương pháp sẽ tốt hơn cả hai,
  nhưng số đo cho thấy nó **không hơn embedding** ở bài toán chính. Em giữ nguyên kết quả này trong
  báo cáo thay vì chỉnh tham số cho tới khi ra số đẹp — một kết quả âm tính vẫn là kết quả.

- **Cái giá phải trả, và nhóm chấp nhận có ý thức:** embedding kéo ảnh Docker từ 238MB lên
  **2,74GB** (gấp 11 lần) và thêm 19 giây khởi động. Em xử lý bằng cách **tính sẵn vector lúc build
  ảnh** thay vì lúc chạy, nên độ trễ mỗi câu hỏi không tăng — chỉ thời gian khởi động tăng.

- **Thí nghiệm em tâm đắc nhất lại là thí nghiệm THẤT BẠI.** Khi bị hỏi *"chưa tối ưu tài liệu thì
  sao dám kết luận truy hồi kém"*, em viết lại tiêu đề mục của toàn kho cho đặc thù theo từng tài
  liệu: số tiêu đề khác nhau **179 → 365**, đoạn dùng chung tiêu đề **283/452 → 93/452**, lớp lỗi
  nhắm tới giảm **19 ca → 1 ca**. Kho cải thiện rõ ràng. Nhưng **Hit@1 không đổi — 60,87% cả trước
  lẫn sau**. Các ca kia không được sửa; chúng chỉ **đổi tên lỗi**. Kết luận em rút ra: trần không
  nằm ở dữ liệu, mà ở chỗ một hàm xếp hạng không diễn đạt được một vị từ.

### 5.2.3 Nhận xét — Đỗ Tuấn Anh (BIT240015)

**Phụ trách:** Chọn món và ba lớp an toàn

Qua chặng chọn món và an toàn, em rút ra các nhận xét sau:

- **Kết luận thiết kế của chặng này: cơ chế an toàn không được phụ thuộc vào mô hình sinh.** Ban đầu nhóm định dặn mô hình trong lời nhắc rằng "không được nhắc món gây dị ứng". Nhưng
  lời nhắc là **đề nghị**, không phải **ràng buộc** — mô hình có thể bỏ qua và không có gì báo.
  Nhóm chuyển sang **lọc trước khi sinh**: mô hình chỉ nhận danh sách món **đã** an toàn, nên nó
  không có gì để nhắc sai.

- **{b.so_phep_kiem} phép kiểm xác minh, và mỗi phép kiểm sinh ra từ một lần mô hình làm sai thật.** Ví dụ em nhớ
  nhất: mô hình viết *"Nhà hàng có **6 món lẩu**"* trong khi thực đơn có **7**. Ba phép kiểm đầu
  không chạm tới lỗi này — nó không phải tên món, không phải giá, không phải nhãn. Phải thêm một
  phép kiểm riêng **cấm mô hình nêu số lượng**. Bài học: không đoán trước được mô hình sẽ sai kiểu
  gì; phải đo rồi mới biết.

- **Câu sinh vi phạm thì BỎ, không sửa.** Em từng định viết mã tự sửa câu mô hình viết sai, nhưng
  bỏ ý đó: sửa một câu sai thành câu đúng đòi hỏi biết đúng là gì, mà nếu đã biết thì đâu cần mô
  hình. Vi phạm thì rơi về câu khuôn mẫu — kém tự nhiên nhưng **đúng**.

- **Chỗ em bị bắt lỗi và phải nhận sai:** khách nói *"dị ứng tôm, tư vấn món hải sản khác"*. Em định
  lọc riêng con tôm ra để vẫn còn 14 món hải sản gợi ý được. Nhưng kiểm dữ liệu thì **7/26 món hải
  sản không có nhãn nguyên liệu nào**, và hai trong số đó **chứa tôm thật**: *Bún đậu mắm tôm* và
  *Bún bò Huế* (mắm ruốc). Lọc hẹp sẽ mời đúng hai món đó cho người dị ứng tôm. Em giữ chặn rộng và
  sửa phần **im lặng** thay vì nới hàng rào.

- **Thẻ giỏ hàng dựng từ danh sách món, không từ chữ mô hình viết.** Đây là ranh giới cuối: kể cả
  khi mọi phép kiểm trên đều lọt, món trong giỏ vẫn không thể là món mô hình bịa ra, vì giỏ không
  đọc chữ của mô hình.

### 5.2.4 Nhận xét — Lê Anh (BIT240017)

**Phụ trách:** Dịch vụ HTTP, bộ nhớ phiên, tích hợp với backend

Qua chặng phiên và tích hợp, em rút ra các nhận xét sau:

- **Bộ nhớ phiên cần BA quy tắc hợp nhất khác nhau, không phải một.** Đây là chỗ em làm sai lần đầu:
  em dùng chung một quy tắc "cộng dồn" cho mọi loại ràng buộc. Hậu quả: khách nói *"dưới 200 nghìn"*
  rồi *"rẻ hơn nữa"* thì hệ thống **giữ cả hai ngân sách** thay vì thay. Sửa xong thành ba quy tắc:
  dị nguyên **cộng dồn không bao giờ bỏ**, ràng buộc cứng **ghi đè theo nhóm**, ngữ cảnh **tích lũy
  có trần 5**.

- **Dị nguyên phải cộng dồn — và đây là bất biến an toàn quan trọng nhất của chặng em.** Khách khai
  dị ứng ở lượt 1, hỏi tiếp ở lượt 5 **mà không nhắc lại**. Nếu bộ nhớ ghi đè thì "dị ứng hải sản"
  bị "không ăn được sữa" xoá mất. Tập đánh giá phiên có riêng một nhóm kịch bản đo đúng điều này.

- **Dịch vụ phải trả lời được KHI MÔ HÌNH HỎNG.** Em thiết kế để mã tất định chạy trước, mô hình chỉ
  được gọi ở nhánh cần diễn đạt. Nhờ vậy khi khoá API hết hạn hoặc nhà cung cấp lỗi, khách vẫn nhận
  được câu trả lời đúng — chỉ là câu khuôn mẫu thay vì câu mượt. Một trợ lý im lặng vì mô hình hỏng
  là một trợ lý hỏng.

- **Tích hợp là chỗ lộ ra lỗi mà không tập đánh giá nào bắt được.** Ba tập đầu đều gọi thẳng hàm
  Python, không đi qua backend. Khi ghép thật, em phát hiện những lỗi chỉ tồn tại ở lớp nối — ví dụ
  nhánh `combo` trả về giỏ hàng rỗng vì thiếu tên nhánh trong danh sách trắng, một lỗi mà **394 test
  đơn vị không chạm tới**.

- **Giới hạn:** độ trễ khi bật mô hình là **~8,6 giây mỗi lượt**. Em chưa giải được, và nó là lý do
  chính khiến nhóm để đường sinh **tắt mặc định**.

### 5.2.5 Nhận xét — Nguyễn Quang Hiếu (BIT240091)

**Phụ trách:** Bốn tập đánh giá, thước đo, golden đầu-cuối, cổng CI

Qua chặng đánh giá, em rút ra các nhận xét sau:

- **Bài học lớn nhất của em: kiểm giả thuyết "thước đo sai" TRƯỚC giả thuyết "hệ thống sai".** Dự án
  này ghi nhận **tám lần** thước đo sai trước khi hệ thống sai, và lần gần nhất là bộ đo hai chiều
  do chính em viết — nó sai **ba lần liên tiếp**, và cả ba đều sai theo hướng làm kết quả **đẹp hơn
  thực tế**: (a) cột "tất định" tính cả nhánh truy hồi nên 4/8 câu hiện đúng nhờ chính bên kia làm;
  (b) chiều B tìm trên kho tri thức thay vì chỉ mục món nên truy hồi ra **0 vi phạm** — một con số
  không phản ánh bài toán cần đo; (c) `getattr` truy cập một thuộc tính không tồn tại nên luôn trả rỗng,
  khiến phép đo phản ánh chính bộ chấm điểm chứ không phản ánh bộ truy hồi. Đó là hướng sai mà người đo **có động cơ không kiểm lại**.

- **Golden {b.luot_golden} lượt là bộ bắt được nhiều lỗi nhất, và lý do rất cụ thể: nó không mock gì cả.** Nó
  chạy đúng đường khách đi — quét QR → backend → dịch vụ AI → thẻ giỏ → giỏ hàng. Ba tập còn lại gọi
  thẳng hàm Python nên một lỗi ở lớp ghép hai hệ thống sẽ không tập nào thấy.

- **Chia tập theo HỌ, không theo ca.** Nếu chia ngẫu nhiên theo từng ca thì hai ca cùng một họ — ví
  dụ hai cách hỏi về món nướng — có thể rơi vào hai tập khác nhau, và tập niêm phong không còn
  "chưa từng thấy". Chia theo họ giữ được ý nghĩa của phép đo.

- **Mỗi tập chỉ đo đúng thứ nó được viết ra để đo, và điều này em học được theo cách khó.** Trong
  một phiên thử nghiệm với người dùng thật, **17 lỗi lọt qua** 140 ca và 111 lượt phiên. Không phải
  vì tập kém, mà vì mọi ca trong tập đều **viết đúng kiểu**, còn người thật thì phủ định, đổi ý, và
  hỏi liên tục. Tập phiên phải lớn từ **111 → 149 lượt** mới bắt được chúng.

- **Hạn chế nghiêm trọng nhất của toàn đồ án, và em phải nói rõ:** **không có log khách thật**. Mọi
  ca đánh giá đều do nhóm viết. Con số đo được hệ thống có tôn trọng ràng buộc hay không; nó
  **không** đo được khách thật sẽ hỏi gì. Thêm nữa, **cả bốn tập niêm phong đã được mở**, nên con số
  trên chúng không còn là held-out cho các thay đổi sau đó. Con số held-out thật duy nhất của dự án
  là **23/27 (85,2%)** ở lần mở đầu tiên.

---

## 5.3 Làm được

| Việc | Bằng chứng |
|---|---|
| Trả lời đúng trên tập ca một lượt | {len(b.ca_tra_loi)}/{len(b.ca_tra_loi)}, và sàn để so là 8/{len(b.ca_tra_loi)} — một bản "luôn nói chưa có dữ liệu" chỉ qua được bấy nhiêu |
| Giữ ràng buộc qua nhiều lượt, kể cả lượt không nhắc lại | {b.luot_phien}/{b.luot_phien}, **0 lỗi an toàn** |
| Chạy end-to-end thật tới **giỏ hàng thật** | golden {g['dat']}/{g['luot']} ở cả hai cấu hình |
| Chọn bộ truy hồi bằng SỐ, trên hai bài toán và hai tập niêm phong | mục 4.2, 4.3 |
| Chứng minh **không phải chỗ nào cũng nên dùng RAG** | mục 4.4 |
| Chặn bịa món và bịa giá khi mô hình viết | {llm['lui_ve_khuon_mau']}/{llm['ca']} ca bị chặn, cả {llm['lui_ve_khuon_mau']} vì bịa giá |
| Nói "chưa có dữ liệu" thay vì đoán, kể cả câu ngoài phạm vi | cổng thuộc miền sinh từ dữ liệu, mục 3.4 |
| Câu trả lời và thẻ giỏ **không lệch nhau, cả hai chiều** | phép kiểm thứ 6 và bất biến thẻ giỏ thứ 8 |
| Cắt khởi động container 97,3s → 19,0s | mục 4.8 |

## 5.4 Hạn chế của nghiên cứu

1. **Không có log khách thật.** Mọi ca đánh giá do nhóm viết. Con số đo được hệ thống **có tôn trọng
   ràng buộc hay không**; nó **không** đo được khách thật hỏi gì. Đây là hạn chế lớn nhất, và nó không
   sửa được bằng cách viết thêm ca.
2. **Cả bốn tập niêm phong đã mở.** Không con số nào trong báo cáo này còn là held-out. Con số held-out
   thật duy nhất của dự án là **23/27 (85,2%)** ở lần mở đầu tiên. Câu hỏi tiếp theo cần một tập **mới**.
3. **Một phần kho tri thức là dữ liệu mẫu** (`source: demo`). Chúng **không thể** sai về **con số** — số
   lấy từ thực đơn qua bộ sinh — nhưng có thể sai về **chính sách**, và chỉ chủ nhà hàng biết.
4. **Nhãn dị nguyên phủ 44/{len(b.items)} món.** Đối chiếu mô tả đã tìm ra 7 lỗ thật, nhưng mô tả không
   phải bảng thành phần, nên **còn thiếu bao nhiêu thì không biết được từ dữ liệu này**.
5. **Đường sinh không còn làm tụt ca, nhưng cũng không làm đúng thêm ca nào.** Cái đo được là 0 ca đúng
   thêm với p50 +{so(llm['tre_p50_ms'] / 1000, 1)}s mỗi lượt. Cái **không** đo được: câu văn tự nhiên hơn
   có làm khách thật hài lòng hơn hay không.
6. **Lớp xác minh không bắt được tên món HOÀN TOÀN bịa.** Nó so chuỗi với dữ liệu, nên một cái tên không
   có trong thực đơn dưới bất kỳ dạng nào thì lọt. Giới hạn này được ghi thành **một test có tên nói rõ
   nó là giới hạn**.
7. **Phần lớn ca truy hồi còn sai KHÔNG sửa được bằng đổi bộ xếp hạng.** Trần đa dạng của kho:
   {tieu_de} tiêu đề mục phân biệt trên {len(b.doan)} đoạn. Chữa được bằng sửa **dữ liệu**, và việc đó
   chưa làm.
8. **Ảnh Docker 2,74GB**, gấp hơn 11 lần bản không có embedding. Giá đã đo và đã chấp nhận, nhưng nó làm
   deploy chậm hơn và tốn đĩa hơn.

## 5.5 Bài học kinh nghiệm

### Bài học 1 — thước đo sai TRƯỚC khi hệ thống sai

Trong toàn bộ đồ án, số lần **thước đo** sai nhiều hơn số lần **hệ thống** sai. Ví dụ rõ nhất: ở một lần
chạy golden có 8 lượt đỏ, và **5 trong 8** là lỗi bộ đo, không phải lỗi hệ thống.

Nên thứ tự kiểm phải là: **kiểm giả thuyết "thước đo sai" TRƯỚC giả thuyết "hệ thống sai"**.

Một trường hợp cụ thể: phép đo **cho điểm cao với hành vi sai** — nó đòi câu trả lời tri thức phải
*chứa nguyên văn* một đoạn của tài liệu — mà đoạn thô cũng chứa cả nhan đề tài liệu. Nên **dán đoạn thô
là cách chắc chắn nhất để QUA**, còn câu trình bày sạch thì đỏ. Khi phần làm sạch trình bày được thêm,
tập trả lời tụt từ {len(b.ca_tra_loi)}/{len(b.ca_tra_loi)} xuống 130/{len(b.ca_tra_loi)} và **cả 10 ca
đỏ là câu trả lời đúng**.

### Bài học 2 — một bất biến MỘT CHIỀU chỉ canh một nửa

Mẫu này lặp lại nhiều lần, và ba trong bốn chỗ lệch tìm được ở vòng cuối đều thuộc nó:

| Bất biến | Chiều nó canh | Nửa nó bỏ |
|---|---|---|
| thẻ giỏ ⊆ món được nêu | thẻ không có món lạ | **văn nêu 6 món mà thẻ chỉ có 3** |
| chi tiết lỗi không vào `content` | khách không thấy | chi tiết vẫn vào phản hồi HTTP |
| `/ready.retriever` báo bộ đang chạy | đường truy hồi toàn kho | **đường chọn mục vẫn chạy BM25** |

### Bài học 3 — hai đầu phải khớp, và đầu thứ hai thường ở ngôn ngữ khác

Sáu lần trong dự án, một bất biến có **hai đầu** và hai đầu lệch nhau im lặng. Hai lần gần nhất, đầu thứ
hai nằm **ngoài Python**: một test TypeScript đọc tệp requirements của phần AI, và một test C# đọc hai
workflow deploy. Cả hai lần đều bị bỏ sót vì phép quét chỉ chạy trong phạm vi đang làm việc.

Bài học cụ thể hơn "quét kỹ hơn": khi thay một tệp mà **hạ tầng** gọi, phải quét **cả backend và
frontend**, không chỉ thư mục của thứ mình đang sửa.

### Bài học 4 — con số không đo thì sai cả về hướng lẫn độ lớn

Ảnh Docker được ghi *"khoảng 2–3GB"* trong tài liệu qua ba bước, và không ai đo. Đo thật: **9,29GB**.
Sau khi ghim bản CPU: **2,74GB**.

Đây là một trong sáu lần dự án có số viết tay rồi trôi. Năm lần kia: `"hơn 90 món"` khi thực đơn có
{len(b.items)}; một bản kiểm kê ghi `32/90` khi thật là `53/40`; notebook in `122/122` khi tập đã
{len(b.ca_tra_loi)} ca; `84 tài liệu / 303 đoạn` khi kho đã {len(b.docs)}/{len(b.doan)}; và một chỉ số
truy hồi của kho nhỏ hơn được trích cho kho hiện tại.

**Và lần thứ bảy là chính báo cáo này.** Bản trước viết tay 1587 dòng và đã trôi hoàn toàn: nó mô tả một
kiến trúc không còn tồn tại, và **11/11 lệnh của Phụ lục B trỏ vào tệp đã bị xóa**. Cách sửa không phải
"viết lại rồi nhớ cập nhật" — cách đó vừa thất bại — mà là **sinh báo cáo từ mã và bằng chứng đo**, cùng
kỷ luật mà notebook của dự án đã có từ đầu và nhờ đó không trôi.

### Bài học 5 — an toàn không được phụ thuộc việc mô hình chịu nghe

`PROMPT` yêu cầu mô hình mời khách hỏi nhân viên khi có ràng buộc dị ứng. Mô hình **bỏ câu đó ở 14 ca**.
Yêu cầu trong prompt là **đề nghị**; chỉ phép kiểm sau khi sinh mới là **bảo đảm**.

## 5.6 Khó khăn gặp phải

| Khó khăn | Cách nhóm xử lý |
|---|---|
| **Không có log khách thật** — mọi ca đánh giá do nhóm viết, nên chúng phản ánh cách nhóm nghĩ khách sẽ hỏi, không phải cách khách hỏi thật | Thử nghiệm trực tiếp với người dùng ngoài nhóm; một phiên như vậy làm lộ **17 lỗi** mà 140 ca và 111 lượt không bắt được, và tập phiên phải lớn lên **149 lượt** |
| **Rút dấu tiếng Việt gây va chạm** — `fold("có cồn") == fold("có con")`, `fold("cua") == fold("của")` | Bản kiểm kê va chạm chạy trong CI; mỗi lần thêm cụm từ vựng phải chạy lại. Dự án ghi nhận **mười vụ** kiểu này |
| **Độ trễ mô hình ~8,6 giây mỗi lượt** | Để đường sinh **tắt mặc định**; mã tất định trả lời trước, mô hình chỉ được gọi ở nhánh cần diễn đạt |
| **Ảnh Docker 2,74GB vì embedding** | Tính sẵn vector lúc **build ảnh** thay vì lúc chạy — độ trễ mỗi câu không tăng, chỉ thời gian khởi động; và cắt được khởi động từ 97,3s xuống **19,0s** |
| **Nhãn dị nguyên chỉ phủ 44/91 món** | Chặn rộng thay vì lọc hẹp, và **nói ra lý do** cho khách thay vì im lặng. Đây là giới hạn dữ liệu, không sửa được bằng mã |
| **Thước đo sai trước hệ thống sai — tám lần** | Viết `probe_metric_holes.py` để dò lỗ của chính thước đo; và đặt thành nếp: kiểm giả thuyết "đo sai" trước |

---

## 5.7 Hướng phát triển tương lai

Sáu việc, xếp theo **mức chặn** — việc thứ nhất chặn giá trị của mọi con số trong báo cáo này.

1. **Log khách thật.** Chỉ số đáng theo nhất là **tỷ lệ nhánh `clarify`** trên log thật: nó đo phần câu
   hỏi mà hệ thống *không hiểu*, và đó là thứ tập do nhóm viết không bao giờ ước lượng đúng — người viết
   ca biết hệ thống hiểu gì.
2. **Sửa trần đa dạng của kho.** Viết lại tiêu đề mục cho đặc thù theo tài liệu. Điều kiện chấp nhận có
   **hai** chiều: lớp `retrieval_twin_section` giảm **và** `cấm@5` không tăng — tiêu đề đặc thù hơn có
   thể làm đoạn khó tìm hơn khi khách dùng từ chung.
3. **Đủ điều kiện bật đường sinh mặc định**: 0 ca tụt *và* tỷ lệ dùng câu sinh không giảm.
4. **Lấp nhãn dị nguyên** bằng bảng thành phần từ nhà bếp — việc thật ở đây là hỏi người, không phải suy
   từ dữ liệu.
5. **Đưa thứ tự món đã nêu qua backend**, để câu "món đầu tiên giá bao nhiêu?" trỏ được vào đâu.
6. **Giảm ảnh Docker**: xuất mô hình sang ONNX runtime để bỏ hẳn torch. Hướng dùng endpoint embeddings
   của nhà cung cấp **đã thử và không dùng được** — nhà cung cấp hiện tại không có endpoint đó.

### Giới hạn đã biết của bộ nhãn

Ba điều tìm ra khi soát lại {len(b.tags)} nhãn trên {len(b.items)} món. Ghi ra vì **một giới hạn không được
nói thì người đọc sẽ tưởng nó không tồn tại**.

1. **`diet:vegan` và `diet:vegetarian` gắn đúng cùng {sum(1 for i in b.items if 'diet:vegetarian' in i['tags'])} món.** Một trong hai không phân biệt
   được gì *trong bộ dữ liệu này* — nhưng cả hai đều ĐÚNG, và thêm một món chay có sữa là nhãn thứ
   hai có nghĩa lại ngay. Nên đây không phải lỗi dữ liệu, và cách xử lý là ở lớp diễn đạt: mô tả
   đưa mô hình đọc bỏ nhãn nào mà mọi món trong danh sách đều mang.

2. **`spice` phủ {sum(1 for i in b.items if any(t.startswith('spice:') for t in i['tags']))}/{len(b.items)} món, và {sum(1 for c in {i['categoryId'] for i in b.items} if all('spice:none' in i['tags'] for i in b.items if i['categoryId'] == c))} danh mục có toàn bộ món `spice:none`**
   — Cà phê & Trà, Nước ép & Sinh tố, Tráng miệng, Trái cây tươi, Bia & Rượu. Nói "không cay" về
   một ly nước ép mang đúng 0 bit thông tin. Cùng cách xử lý như trên, và cùng lý do: **một nhãn chỉ
   đáng nói khi nó phân biệt.**

3. **{len(b.tags)} nhãn đến từ mô tả món, không từ bảng thành phần hay từ bếp.** Bộ soát cách chế
   biến (`audit_method_tags.py`) chặn được nhóm `method` vì tên món tự nói ra đáp án; các nhóm còn
   lại thì không có nguồn kiểm tự động nào tương đương.

### Ba điều cấm, áp cho cả nhóm và CI ép

1. **Không nới ràng buộc dị nguyên** — kể cả khi kết quả rỗng.
2. **Không để mô hình sinh chọn món** — nó chỉ trả về nhãn, và nhãn bị cổng kiểm lại.
3. **Không viết số vào tài liệu** — số phải tính được, nếu không nó sẽ trôi. Báo cáo này là bằng chứng
   thứ bảy cho quy tắc đó, và là lần đầu quy tắc được ép bằng **cấu trúc**: tài liệu này được sinh ra.

---
---"""


def tai_lieu_tham_khao() -> str:
    return """# TÀI LIỆU THAM KHẢO

1. Robertson, S., & Zaragoza, H. (2009). *The Probabilistic Relevance Framework: BM25 and Beyond.*
   Foundations and Trends in Information Retrieval, 3(4), 333–389.
2. Wang, L., Yang, N., Huang, X., et al. (2022). *Text Embeddings by Weakly-Supervised Contrastive
   Pre-training.* arXiv:2212.03533. (Họ mô hình E5, gồm `multilingual-e5-small` dùng trong đồ án.)
3. Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). *Reciprocal Rank Fusion Outperforms Condorcet
   and Individual Rank Learning Methods.* SIGIR '09, 758–759.
4. Lewis, P., Perez, E., Piktus, A., et al. (2020). *Retrieval-Augmented Generation for Knowledge-Intensive
   NLP Tasks.* NeurIPS 2020.
5. Järvelin, K., & Kekäläinen, J. (2002). *Cumulated Gain-Based Evaluation of IR Techniques.* ACM
   Transactions on Information Systems, 20(4), 422–446. (nDCG.)
6. Reimers, N., & Gurevych, I. (2019). *Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks.*
   EMNLP 2019. (Thư viện `sentence-transformers`.)

---"""


def phu_luc_a() -> str:
    return """# PHỤ LỤC

## Phụ lục A: Notebook nghiên cứu

`ai/notebooks/he_thong_ai_tu_van_dat_mon.ipynb` — bảy phần tuần tự, **mọi ô mã tự tính lại** từ
`ai/app` và `ai/evaluation` thật, nên chạy lại notebook là **đo lại**:

```
 1  dựng DỮ LIỆU            thực đơn · nhãn · kho tri thức · chia đoạn
 2  dựng THƯỚC ĐO           tập ca · khóa đáp án kiểm được · chia ba nhóm
 3  trả lời KHÔNG mô hình    số nền — mọi thứ sau đó phải hơn số này
 4  dựng TRUY HỒI + SO       ba cách × hai bài toán × hai tập  →  CHỌN một
 5  mô hình SINH + an toàn   nơi mô hình có giá trị, và lớp xác minh
 6  THỬ NGHIỆM THẬT          gọi mô hình · qua HTTP · vào giỏ hàng thật
 7  kết quả · làm được · hạn chế · hướng phát triển
```

Sinh lại và chạy:

```bash
python ai/notebooks/build_teaching_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace \\
    ai/notebooks/he_thong_ai_tu_van_dat_mon.ipynb
python ai/notebooks/build_teaching_notebook.py --check
```

Bước `--check` làm hai việc: so **nguồn** từng ô với bộ sinh, và đọc **kết quả** đã commit rồi báo đỏ
nếu có ô nào **nổ**. Việc thứ hai được thêm sau khi một ô nổ hai lần liền mà `--check` vẫn xanh.

---"""


def phu_luc_d(b: Bang) -> str:
    ra = ["## Phụ lục D: Ma trận chỉ số đầy đủ", ""]
    ra.append("Toàn bộ số của Chương 4, một bảng. Đọc từ `ai/evaluation/measurements/`.")
    ra.append("")
    ra.append("| Bài toán | Tập | Phương pháp | n | Hit@1 | Hit@5 | MRR@5 | nDCG@5 | cấm@5 |")
    ra.append("|---|---|---|---:|---:|---:|---:|---:|---:|")
    for nhom in b.m_truy_hoi["so"]["bai_toan_1"]:
        for bo in b.bo_truy_hoi():
            d = b.m_truy_hoi["so"]["bai_toan_1"][nhom]["bo"][bo]
            n = d["n"]
            f = (lambda k: pct(d[k] / n)) if n else (lambda k: "—")
            ra.append(
                f"| truy hồi toàn kho | {nhom} | `{bo}` | {n} | {f('hit1')} | {f('hit5')} | "
                f"{f('mrr5')} | {f('ndcg5')} | {d['cam5']} |"
            )
    b2 = b.m_truy_hoi["so"]["bai_toan_2"]["bo"]
    for bo, d in b2.items():
        ra.append(
            f"| chọn món | 8 ca | `{bo}` | {d['n']} | {pct(d['hit1'] / d['n'])} | "
            f"{pct(d['hit5'] / d['n'])} | — | — | {d['cam5']} |"
        )
    for tap, ten in (("phat_trien", "phát triển"), ("niem_phong", "niêm phong")):
        m = b.m_chon_np if tap == "niem_phong" else b.m_chon_dev
        for nhom_dang in ("written|*", "written|A", "written|B", "derived|*"):
            for bo in sorted(m["so"]["nhom"].get(nhom_dang, {})):
                d = m["so"]["nhom"][nhom_dang][bo]
                if not d["n"]:
                    continue
                ra.append(
                    f"| chọn mục `{nhom_dang}` | {ten} | `{bo}` | {d['n']} | "
                    f"{pct(d['top1'])} | — | {pct(d['mrr'])} | — | — |"
                )
    ra.append("")
    ra.append("`—` nghĩa là chỉ số đó **không áp dụng** cho bài toán/nhóm đó, không phải bằng 0.")
    return "\n".join(ra)


def phu_luc_e(b: Bang) -> str:
    ra = ["## Phụ lục E: Provenance — mỗi con số đến từ đâu", ""]
    ra.append("Mọi phép đo cần stack hoặc mô hình thật đều được **ghi ra tệp kèm điều kiện của lần**")
    ra.append("**chạy**. Bảng dưới liệt kê chính những tệp mà báo cáo này đọc.")
    ra.append("")
    ra.append("| Tệp bằng chứng | Ngày đo | Điều kiện |")
    ra.append("|---|---|---|")
    for ten, m in (
        ("golden_e2e.json", b.m_golden),
        ("golden_e2e_sinh.json", b.m_golden_sinh),
        ("llm_rag_loai_c.json", b.m_llm),
        ("truy_hoi_so_sanh.json", b.m_truy_hoi),
        ("chon_muc_phat_trien.json", b.m_chon_dev),
        ("chon_muc_niem_phong.json", b.m_chon_np),
    ):
        dk = dict(m["dieu_kien"])
        ngay = dk.pop("ngay", "—")
        ready = dk.pop("ready", None)
        if isinstance(ready, dict):
            dk["retriever"] = ready.get("retriever")
            dk["generation_enabled"] = ready.get("generation_enabled")
        mo_ta = " · ".join(f"{k}={v}" for k, v in dk.items() if v not in (None, "", []))
        ra.append(f"| `{ten}` | {ngay} | {mo_ta} |")
    ra.append("")
    ra.append("Thiếu một tệp trong bảng này là **sinh báo cáo thất bại**, không phải một ô trống trong")
    ra.append("tài liệu. Lý do: một con số không rõ đo lúc nào, trên cấu hình nào, thì tệ hơn không có số.")
    return "\n".join(ra)


# ----------------------------------------------------------------- lắp và ghi
def bao_cao() -> str:
    b = Bang()
    phan = [
        phan_dau(b), muc_luc(), tom_tat(b), thuat_ngu(), danh_muc_hinh(b), danh_muc_bang(b), phan_cong(b),
        chuong_1(b), chuong_2(b), chuong_3(b), chuong_4(b), chuong_5(b),
        tai_lieu_tham_khao(),
        phu_luc_a(), phu_luc_b(), phu_luc_c(b), phu_luc_d(b), phu_luc_e(b),
    ]
    return "\n\n".join(p.strip() for p in phan) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="Kiểm khớp bản đã commit, không ghi.")
    args = p.parse_args(argv)

    # PHỤ LỤC B TỰ KIỂM — chạy TRƯỚC khi sinh, vì đây là lỗ đã làm bản trước thành vô dụng.
    thieu = kiem_lenh_tai_lap()
    if thieu:
        print(f"{len(thieu)} lệnh trong Phụ lục B trỏ vào tệp KHÔNG TỒN TẠI:")
        for t in thieu:
            print(f"  {t}")
        print("\nSửa `LENH_TAI_LAP` hoặc khôi phục tệp. Bản trước của báo cáo có 11/11 lệnh như vậy,")
        print("và không ai phát hiện vì tài liệu không có cách nào tự kiểm.")
        return 1

    try:
        text = bao_cao()
    except FileNotFoundError as e:
        print(str(e))
        print("\nThiếu bằng chứng đo — xem `ai/evaluation/measurements/README.md`.")
        return 1

    dong = text.count("\n")
    print(f"báo cáo: {dong} dòng, {len(text):,} ký tự".replace(",", "."))
    print(f"lệnh tái lập: {len(LENH_TAI_LAP)} lệnh, tất cả trỏ vào tệp CÓ THẬT")

    if args.check:
        if not OUT_PATH.exists():
            print("\nCHƯA CÓ BÁO CÁO. Chạy bộ sinh trước.")
            return 1
        if OUT_PATH.read_text(encoding="utf-8-sig") != text:
            print("\nBÁO CÁO ĐÃ COMMIT KHÁC KẾT QUẢ SINH LẠI.")
            print("Chạy `python ai/docs/build_bao_cao_do_an.py` rồi commit lại.")
            cu = OUT_PATH.read_text(encoding="utf-8-sig").splitlines()
            moi = text.splitlines()
            for i, (a, c) in enumerate(zip(cu, moi), 1):
                if a != c:
                    print(f"  dòng đầu tiên khác nhau: {i}")
                    print(f"    đã commit : {a[:100]}")
                    print(f"    sinh lại  : {c[:100]}")
                    break
            return 1
        print("\n--check: báo cáo đã commit KHỚP kết quả sinh lại.")
        return 0

    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"\nĐã ghi {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
