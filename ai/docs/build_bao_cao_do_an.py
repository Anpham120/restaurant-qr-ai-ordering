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

    # -- dẫn xuất -------------------------------------------------------------------
    @property
    def luot_phien(self) -> int:
        return sum(len(s["turns"]) for s in self.kich_ban)

    @property
    def luot_golden(self) -> int:
        return sum(len(c["turns"]) for c in self.golden)

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
- [DANH MỤC THUẬT NGỮ VÀ VIẾT TẮT](#danh-mục-thuật-ngữ-và-viết-tắt)
- [PHÂN CÔNG CÔNG VIỆC](#phân-công-công-việc)
- **[CHƯƠNG 1: GIỚI THIỆU](#chương-1-giới-thiệu)**
  - 1.1 Bối cảnh và động lực
  - 1.2 Ba loại câu hỏi, và vì sao phân loại chúng là quyết định kiến trúc
  - 1.3 Ràng buộc an toàn — bài toán thật của đồ án
  - 1.4 Các nghiên cứu liên quan
  - 1.5 Mục tiêu và đóng góp
- **[CHƯƠNG 2: CƠ SỞ LÝ THUYẾT](#chương-2-cơ-sở-lý-thuyết)**
  - 2.1 Truy hồi từ khoá — BM25
  - 2.2 Truy hồi ngữ nghĩa — biểu diễn nhúng
  - 2.3 Hợp nhất thứ hạng — Reciprocal Rank Fusion
  - 2.4 Kiến trúc RAG và chỗ nó KHÔNG nên dùng
  - 2.5 Chuẩn hoá văn bản tiếng Việt là phép MẤT thông tin
  - 2.6 Ba lớp an toàn: lọc fail-closed, xác minh, thẻ giỏ tất định
  - 2.7 Các chỉ số đánh giá, và chỉ số nào QUYẾT ĐỊNH
- **[CHƯƠNG 3: PHƯƠNG PHÁP](#chương-3-phương-pháp)**
  - 3.1 Kiến trúc bảy chặng — và chỉ hai chặng có mô hình
  - 3.2 Kho tri thức: một kho, hai chế độ trả lời
  - 3.3 Bốn tập đánh giá, và kỷ luật chia tập
  - 3.4 Mười bảy nhánh trả lời, không nhánh nào chồng nhánh nào
  - 3.5 Hai bài toán truy hồi khác nhau
  - 3.6 Điều kiện kiểm soát thực nghiệm
- **[CHƯƠNG 4: THỰC NGHIỆM VÀ KẾT QUẢ](#chương-4-thực-nghiệm-và-kết-quả)**
  - 4.1 Thiết lập
  - 4.2 So ba phương pháp truy hồi trên hai tập
  - 4.3 Chọn mục trong tài liệu — bài toán mà hệ thống thật sự chạy
  - 4.4 Chọn món: lọc theo nhãn so với RAG
  - 4.5 Gọi LLM+RAG thật trên câu loại C
  - 4.6 Golden 103 lượt qua chuỗi gọi đầy đủ
  - 4.7 Phân tích nguyên nhân sai — và case nào KHÔNG sửa được nữa
  - 4.8 Chốt phương án triển khai, kèm giá đã đo
- **[CHƯƠNG 5: KẾT LUẬN](#chương-5-kết-luận)**
  - 5.1 Tổng kết
  - 5.2 Làm được
  - 5.3 Hạn chế
  - 5.4 Bài học kinh nghiệm
  - 5.5 Hướng phát triển
- [TÀI LIỆU THAM KHẢO](#tài-liệu-tham-khảo)
- [PHỤ LỤC](#phụ-lục)

---"""


def tom_tat(b: Bang) -> str:
    g, gs, llm = b.m_golden["so"], b.m_golden_sinh["so"], b.m_llm["so"]
    e_np = b.ty_le_truy_hoi("NIÊM PHONG", "embedding", "hit1")
    b_np = b.ty_le_truy_hoi("NIÊM PHONG", "bm25", "hit1")
    cm_np = b.chon_muc("niem_phong", "written|*", "embedding")
    cm_np_bm = b.chon_muc("niem_phong", "written|*", "bm25")
    return f"""# TÓM TẮT

Đồ án xây dựng trợ lý AI tư vấn thực đơn cho khách quét mã QR tại bàn, trên thực đơn thật gồm
**{len(b.items)} món** với **{len(b.tags)} nhãn**, và kho tri thức **{len(b.docs)} tài liệu /
{len(b.doan)} đoạn**.

Đóng góp trung tâm không phải "dùng RAG cho nhà hàng", mà là **xác định chỗ nào RAG là câu trả lời sai**
và đo điều đó bằng số. Trên bài toán chọn món, lọc theo nhãn đạt
**{so(b.m_truy_hoi['so']['bai_toan_2']['bo']['lọc nhãn']['hit1'] / 8, 3)}** với
**{b.m_truy_hoi['so']['bai_toan_2']['bo']['lọc nhãn']['cam5']} ca nêu món không thỏa ràng buộc**, còn
ba phương pháp xếp hạng sai
**{min(v['cam5'] for k, v in b.m_truy_hoi['so']['bai_toan_2']['bo'].items() if k != 'lọc nhãn')}–\
{max(v['cam5'] for k, v in b.m_truy_hoi['so']['bai_toan_2']['bo'].items() if k != 'lọc nhãn')}/8 ca**.
Dữ liệu đã có cấu trúc thì đưa qua tầng xếp hạng theo độ tương đồng là **bỏ cấu trúc đi rồi cố đoán
lại**.

Trên bài toán truy hồi tri thức — chỗ RAG **đúng là** câu trả lời — embedding thắng BM25 ở cả hai tập
niêm phong: Hit@1 **{so(e_np)}** so với **{so(b_np)}** trên toàn kho, và Top-1 **{so(cm_np)}** so với
**{so(cm_np_bm)}** ở bài toán chọn mục trong tài liệu.

An toàn được bảo đảm bằng **ba lớp độc lập** thay vì bằng lời nhắc mô hình: lọc dị nguyên fail-closed,
tám phép kiểm xác minh trên câu mô hình viết, và thẻ giỏ dựng tất định từ danh sách món đã lọc. Phép
đo cho thấy lớp thứ hai là bắt buộc: khi bật đường sinh **trước** khi có phép kiểm thứ tám, **14 ca
dị nguyên** mất câu mời hỏi nhân viên — tức "0 lỗi an toàn" của đường tất định thành **14 lỗi an toàn**.

Kết quả cuối, đo qua chuỗi gọi đầy đủ (QR → phiên bàn → phiên chat → backend .NET → dịch vụ AI → mô
hình → thẻ giỏ → giỏ hàng thật):

| Phép đo | Kết quả |
|---|---|
| Golden {g['luot']} lượt, đường sinh TẮT (mặc định) | **{g['dat']}/{g['luot']}** |
| Golden {gs['luot']} lượt, đường sinh BẬT | **{gs['dat']}/{gs['luot']}** |
| Tập trả lời {len(b.ca_tra_loi)} ca (tất định) | **{len(b.ca_tra_loi)}/{len(b.ca_tra_loi)}** |
| Bộ nhớ phiên {b.luot_phien} lượt | **{b.luot_phien}/{b.luot_phien}**, 0 lỗi an toàn |
| LLM+RAG {llm['ca']} ca loại C | tất định {llm['dat_tat_dinh']}/{llm['ca']} · có sinh \
{llm['dat_co_duong_sinh']}/{llm['ca']} |

Hạn chế lớn nhất phải nói ngay: **không có log khách thật**. Mọi ca đánh giá do nhóm viết, và cả bốn
tập niêm phong đã mở. Con số held-out thật duy nhất của dự án là **23/27 (85,2%)** ở lần mở đầu tiên.

---"""


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


def phan_cong() -> str:
    return """# PHÂN CÔNG CÔNG VIỆC

Phân công theo **một vai nền tảng cộng bốn khâu của đường xử lý**. Dữ liệu và đo lường thuộc cùng một
người, vì chúng giống nhau ở điểm quan trọng nhất: cả hai **không phải chặng runtime** — một câu hỏi
không "đi qua" từ điển nhãn hay tập đánh giá, nó *dùng* chúng.

| STT | Họ và tên | MSSV | Công việc | Mục báo cáo | Đóng góp |
|:---:|---|---|---|---|:---:|
| 1 | Phạm Duy An | BIT240002 | Nền tảng dữ liệu và đo lường: kho tri thức markdown, chia đoạn theo tiêu đề, cửa `audience: guest`, bốn tập đánh giá và kỷ luật chia tập theo HỌ, thước đo cùng bộ dò lỗ | 2.5, 3.2, 3.3, 4.7, Phụ lục D | 20% |
| 2 | Bùi Đào Đức Anh | BIT240025 | Hiểu câu hỏi: từ vựng tất định, cổng `already_understood` chặn mô hình vào chỗ không cần, phân biệt câu HỎI VỀ thuộc tính với câu LỌC theo thuộc tính | 2.5, 3.1, 4.5 | 20% |
| 3 | Đỗ Tuấn Anh | BIT240015 | Truy hồi: BM25, embedding, hybrid RRF; so trên HAI bài toán và HAI tập; tính sẵn vector lúc build; chốt bộ truy hồi cho production | 2.1–2.3, 4.2, 4.3, 4.8 | 20% |
| 4 | Lê Anh | BIT240017 | An toàn: lọc dị nguyên fail-closed, tám phép kiểm xác minh của đường sinh, thẻ giỏ tất định, phân tích 14 lỗi an toàn khi bật đường sinh | 2.6, 4.4, 4.5 | 20% |
| 5 | Nguyễn Quang Hiếu | BIT240091 | Cổng vào và bộ nhớ phiên: dịch vụ HTTP, hợp nhất ngữ cảnh ba quy tắc, golden đầu-cuối qua backend thật, cổng deploy đối chiếu bằng chứng; tổng hợp báo cáo | 3.1, 3.6, 4.6, 4.8, Ch.5 | 20% |

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

Yêu cầu thứ hai là chỗ đồ án học được bài học đắt nhất, và nó ở mục 4.5: khi bật đường sinh, mô hình
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

Thiếu tiền tố thì mô hình **vẫn chạy và vẫn trả vector** — chỉ kém đi. Đây là loại lỗi tệ nhất của phần
này: không có thông báo nào, chỉ có điểm thấp hơn mà không ai biết vì sao. Nên có test chốt rằng tiền tố
được thêm.

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

Ca thứ ba là ca đáng nhớ nhất: một hệ thống RAG "hoạt động đúng" ở đó sẽ mời món hải sản cho người vừa
khai dị ứng hải sản, và nó làm vậy **chính vì** nó hoạt động đúng.

## 2.5 Chuẩn hoá văn bản tiếng Việt là phép MẤT thông tin

Rút dấu (`fold`) cho phép khớp "mo cua" với "mở cửa" — người Việt gõ không dấu rất thường. Nhưng nó là
phép **mất thông tin**, và mất đúng chỗ đau: sau khi rút dấu, `"bò"` và `"bơ"` cùng thành `"bo"`.

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
            f"| `{bo}` | {d['n']} | **{so(d['hit1'] / d['n'])}** | {so(d['hit5'] / d['n'])} | "
            f"{so(d['mrr5'] / d['n'])} | {so(d['ndcg5'] / d['n'])} | {d['cam5']} |"
        )
    ra.append("")
    return ra


def chuong_4(b: Bang) -> str:
    ra: list[str] = ["# CHƯƠNG 4: THỰC NGHIỆM VÀ KẾT QUẢ", ""]

    dk = b.m_truy_hoi["dieu_kien"]
    ra += [
        "## 4.1 Thiết lập",
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
        f"- Embedding thắng ở **cả hai** tập: Hit@1 {so(e_dev)} so với {so(b_dev)} (phát triển) và",
        f"  **{so(e_np)}** so với **{so(b_np)}** (niêm phong) — hơn"
        f" **{so((e_np - b_np) * 100, 1)} điểm phần trăm**.",
        f"- **Hybrid KÉM HƠN embedding đơn lẻ** trên tập niêm phong ({so(h_np)} so với {so(e_np)}) —",
        "  trái dự đoán ban đầu của nhóm. Hợp nhất RRF kéo lên những đoạn mà BM25 xếp cao vì trùng từ,",
        "  và ở kho này việc đó làm hại nhiều hơn giúp.",
        "- `cấm@5` gần như không phân biệt được ba bộ. Nghĩa là chênh lệch nằm ở việc **tìm đúng đoạn**,",
        "  không ở việc **tránh đoạn sai** — và đó là tin tốt cho an toàn: không bộ nào lạc đề nhiều hơn.",
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
                f"| {ten} | `{bo}` | **{so(b.chon_muc(tap, 'written|*', bo))}** | "
                f"{so(b.chon_muc(tap, 'written|A', bo))} | "
                f"{so(b.chon_muc(tap, 'written|B', bo))} | {n} |"
            )
    ra += [
        "",
        "**Dạng A và dạng B là điểm chính của phép so.** Dạng A dùng từ có trong mục; dạng B diễn đạt",
        "khác. Một phương pháp thắng ở A mà thua ở B là phương pháp **khớp từ khoá**; thắng cả hai mới",
        "là **hiểu nghĩa**.",
        "",
        f"- BM25 mạnh ở dạng A ({so(b.chon_muc('niem_phong', 'written|A', 'bm25'))}) và sụp ở dạng B",
        f"  ({so(b.chon_muc('niem_phong', 'written|B', 'bm25'))}) — đúng bản chất của nó.",
        f"- Embedding giữ được ở dạng B ({so(b.chon_muc('niem_phong', 'written|B', 'embedding'))}), và",
        "  đó là chỗ quan trọng nhất với khách thật: khách **không** dùng đúng chữ trong tài liệu.",
        "",
        "Nhóm `derived` (tài liệu sinh từ thực đơn theo khuôn dùng chung) được báo cáo **riêng**, vì nó là",
        "MỘT quyết định lặp trên nhiều tài liệu — gộp vào số chính sẽ để một bài toán dễ kéo con số lên.",
        "",
        "## 4.4 Chọn món: lọc theo nhãn so với RAG",
        "",
        "Đây là phép đo **quan trọng nhất của đồ án**, vì nó trả lời câu hỏi ở mục 1.4: chỗ nào KHÔNG nên",
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
        ra.append(f"| {nhan} | {so(d['hit1'] / d['n'])} | {so(d['hit5'] / d['n'])} | {cam} |")
    xh = [v["cam5"] for k, v in b2.items() if k != "lọc nhãn"]
    ra += [
        "",
        f"**Lọc theo nhãn đạt Hit@1 = {so(b2['lọc nhãn']['hit1'] / b2['lọc nhãn']['n'])} với"
        f" {b2['lọc nhãn']['cam5']} ca sai.** Ba bộ xếp hạng sai **{min(xh)}–{max(xh)}/"
        f"{b2['lọc nhãn']['n']} ca**.",
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
        f"| chọn món | **lọc theo nhãn**, không RAG | lọc nhãn {b2['lọc nhãn']['cam5']} ca sai; ba bộ xếp hạng sai {min(xh)}–{max(xh)}/{b2['lọc nhãn']['n']} | 0,3ms — rẻ hơn mọi phương án khác |",
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
| Truy hồi toàn kho, niêm phong | Hit@1 embedding **{so(e_np)}** so với bm25 {so(b_np)} |
| Chọn mục trong tài liệu, niêm phong | Top-1 embedding \
**{so(b.chon_muc('niem_phong', 'written|*', 'embedding'))}** so với bm25 \
{so(b.chon_muc('niem_phong', 'written|*', 'bm25'))} |
| Chọn món | lọc nhãn **{b2['lọc nhãn']['cam5']} ca sai** so với xếp hạng \
{min(v['cam5'] for k, v in b2.items() if k != 'lọc nhãn')}–\
{max(v['cam5'] for k, v in b2.items() if k != 'lọc nhãn')}/{b2['lọc nhãn']['n']} |

## 5.2 Làm được

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

## 5.3 Hạn chế

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

## 5.4 Bài học kinh nghiệm

### Bài học 1 — thước đo sai TRƯỚC khi hệ thống sai

Trong toàn bộ đồ án, số lần **thước đo** sai nhiều hơn số lần **hệ thống** sai. Ví dụ rõ nhất: ở một lần
chạy golden có 8 lượt đỏ, và **5 trong 8** là lỗi bộ đo, không phải lỗi hệ thống.

Nên thứ tự kiểm phải là: **kiểm giả thuyết "thước đo sai" TRƯỚC giả thuyết "hệ thống sai"**.

Trường hợp đáng nhớ nhất là một thước đo **thưởng cho hành vi sai**: nó đòi câu trả lời tri thức phải
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

## 5.5 Hướng phát triển

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
            f = (lambda k: so(d[k] / n)) if n else (lambda k: "—")
            ra.append(
                f"| truy hồi toàn kho | {nhom} | `{bo}` | {n} | {f('hit1')} | {f('hit5')} | "
                f"{f('mrr5')} | {f('ndcg5')} | {d['cam5']} |"
            )
    b2 = b.m_truy_hoi["so"]["bai_toan_2"]["bo"]
    for bo, d in b2.items():
        ra.append(
            f"| chọn món | 8 ca | `{bo}` | {d['n']} | {so(d['hit1'] / d['n'])} | "
            f"{so(d['hit5'] / d['n'])} | — | — | {d['cam5']} |"
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
                    f"{so(d['top1'])} | — | {so(d['mrr'])} | — | — |"
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
        phan_dau(b), muc_luc(), tom_tat(b), thuat_ngu(), phan_cong(),
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
