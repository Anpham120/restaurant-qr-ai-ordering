# -*- coding: utf-8 -*-
"""Vẽ biểu đồ số liệu cho báo cáo Học máy và Khai phá dữ liệu.

Vì sao có tệp này: báo cáo có 54 bảng và 9 sơ đồ kiến trúc, nhưng **không có
biểu đồ số liệu nào**. Bảng đọc được từng con số; biểu đồ cho thấy *hình dạng*
của kết quả — thứ mà một bảng 4 dòng không nói ra được. Với môn học máy thì
hình dạng mới là thứ đáng nhìn: chỗ hai phương pháp cắt nhau, chỗ đường lợi ích
gãy, chỗ một cơ chế đóng góp lệch hẳn phần còn lại.

Số trong tệp này **chép từ kết quả đã chạy**, không tự tính lại. Lý do: bốn phép
đo dưới đây cần mô hình nhúng và mất vài phút mỗi lần; vẽ lại biểu đồ thì không
nên phải chạy lại chúng. Mỗi khối số có ghi lệnh sinh ra nó để đối chiếu.

Chạy:  python ve_bieu_do.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
RA = HERE / "_bieu_do"
RA.mkdir(exist_ok=True)

# Times New Roman cho khớp chữ trong báo cáo; máy nào thiếu thì lùi về DejaVu,
# vốn cũng đủ dấu tiếng Việt.
_co = {f.name for f in font_manager.fontManager.ttflist}
plt.rcParams["font.family"] = ("Times New Roman" if "Times New Roman" in _co
                               else "DejaVu Sans")
plt.rcParams["font.size"] = 11
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

XANH = "#0A6B6B"      # phương pháp được chọn
XAM = "#9AA5A5"       # phương pháp không được chọn
DO = "#962F24"        # chi phí, lỗi an toàn
VANG = "#8A6108"      # cảnh báo


def luu(fig, ten: str) -> None:
    duong = RA / ten
    fig.savefig(duong, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  {ten}")


# ---------------------------------------------------------------------------
# 1 · So ba phương pháp truy hồi trên nhóm `written`
#     nguồn: python ai/evaluation/run_retrieval_comparison.py
# ---------------------------------------------------------------------------
def truy_hoi() -> None:
    chi_so = ["Hit@1", "Hit@2", "Hit@5", "nDCG@5"]
    bm25 = [0.545, 0.712, 0.773, 0.463]
    emb = [0.697, 0.879, 0.939, 0.636]
    hyb = [0.712, 0.803, 0.864, 0.563]

    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    x = range(len(chi_so))
    r = 0.26
    ax.bar([i - r for i in x], bm25, r, label="BM25", color=XAM)
    ax.bar(list(x), emb, r, label="Embedding bge-m3", color=XANH)
    ax.bar([i + r for i in x], hyb, r, label="Hybrid RRF", color=XAM, alpha=0.55)

    for i, (a, b, c) in enumerate(zip(bm25, emb, hyb)):
        for dx, v in ((-r, a), (0, b), (r, c)):
            ax.text(i + dx, v + 0.012, f"{v:.3f}".replace(".", ","),
                    ha="center", fontsize=8.5)

    # Hit@2 là chỉ số hệ thống thật sự dùng — đánh dấu để người đọc không chốt
    # theo Hit@1, nơi hybrid nhỉnh hơn.
    ax.axvspan(0.62, 1.38, color=XANH, alpha=0.07, zorder=0)
    ax.text(1, 1.02, "chỉ số QUYẾT ĐỊNH\n(hệ thống trích 2 đoạn)",
            ha="center", fontsize=9, color=XANH)

    ax.set_xticks(list(x))
    ax.set_xticklabels(chi_so)
    ax.set_ylim(0, 1.14)
    ax.set_ylabel("tỉ lệ")
    ax.set_title("So ba phương pháp truy hồi — 66 ca văn xuôi viết tay",
                 pad=26, fontweight="bold")
    ax.legend(frameon=False, ncol=3, loc="lower center",
              bbox_to_anchor=(0.5, -0.24))
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    luu(fig, "bd1-truy-hoi.png")


# ---------------------------------------------------------------------------
# 2 · Đánh đổi số đoạn trích
#     nguồn: python ai/evaluation/run_so_doan.py --csv
# ---------------------------------------------------------------------------
def so_doan() -> None:
    k = [1, 2, 3, 5]
    trung = [53.95, 70.39, 76.32, 80.92]
    cam = [1.97, 7.24, 9.87, 15.79]

    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.plot(k, trung, "o-", color=XANH, lw=2.2, ms=7, label="trúng tài liệu đúng")
    ax.plot(k, cam, "s--", color=DO, lw=2.2, ms=6, label="CẤM@k — chạm chủ đề cấm")

    for a, b in zip(k, trung):
        ax.annotate(f"{b:.2f}".replace(".", ",") + "%", (a, b),
                    textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9, color=XANH)
    for a, b in zip(k, cam):
        ax.annotate(f"{b:.2f}".replace(".", ",") + "%", (a, b),
                    textcoords="offset points", xytext=(0, -16),
                    ha="center", fontsize=9, color=DO)

    ax.axvline(2, color=XANH, ls=":", lw=1.4)
    ax.text(2.06, 40, "CHỐT k = 2", color=XANH, fontsize=10, fontweight="bold")
    # Đoạn 3→5 là đoạn LỖ: được 4,60 điểm đúng, trả 5,92 điểm nhiễm.
    ax.axvspan(3, 5, color=DO, alpha=0.06, zorder=0)
    ax.text(4, 88, "đoạn LỖ\n+4,60 đúng / +5,92 cấm", ha="center",
            fontsize=9, color=DO)

    ax.set_xticks(k)
    ax.set_xlabel("số đoạn trích cho mỗi câu trả lời (k)")
    ax.set_ylabel("%")
    ax.set_ylim(-4, 100)
    ax.set_title("Tăng số đoạn thì trúng nhiều hơn — và nhiễm cũng nhiều hơn",
                 pad=12, fontweight="bold")
    ax.legend(frameon=False, loc="center right")
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    luu(fig, "bd2-so-doan.png")


# ---------------------------------------------------------------------------
# 3 · Ablation — tắt từng cơ chế rồi đo lại
#     nguồn: python ai/evaluation/run_ablation.py
# ---------------------------------------------------------------------------
def ablation() -> None:
    ten = ["bỏ dấu câu khi chuẩn hoá",
           "phân biệt món ăn với đồ uống",
           "lọc dị nguyên (fail-closed)",
           "ăn hết đoạn đã khớp",
           "phân biệt chủ đề dị nguyên\nvới cách hỏi",
           "danh sách món không bán",
           "phân biệt 'rẻ hơn X' với 'tầm X'",
           "nhận tên món rút gọn",
           "dịp ăn là ngữ cảnh"]
    mat = [27, 14, 5, 4, 3, 2, 1, 1, 1]
    an_toan = [9, 7, 5, 0, 1, 0, 1, 0, 0]

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    y = list(range(len(ten)))[::-1]
    ax.barh(y, mat, 0.62, color=XAM, label="số ca mất")
    ax.barh(y, an_toan, 0.62, color=DO, label="trong đó là LỖI AN TOÀN")

    for yy, m, a in zip(y, mat, an_toan):
        ax.text(m + 0.45, yy, str(m), va="center", fontsize=9.5)
        if a:
            ax.text(a / 2, yy, str(a), va="center", ha="center",
                    fontsize=9, color="white", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(ten, fontsize=9.5)
    ax.set_xlabel("số ca đỏ trên 147 ca khi TẮT cơ chế")
    ax.set_xlim(0, 30)
    ax.set_title("Mỗi cơ chế đều có ít nhất một ca chứng minh giá trị",
                 pad=12, fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(axis="x", alpha=0.25)
    ax.set_axisbelow(True)
    luu(fig, "bd3-ablation.png")


# ---------------------------------------------------------------------------
# 4 · Đường nào thật sự chạy trong một phiên
#     nguồn: bộ đo phân bố đường đi trên 147 ca và 163 lượt phiên
# ---------------------------------------------------------------------------
def duong_di() -> None:
    nhan = ["Lọc nhãn\n(không đọc kho)", "Tra khoá\nnguyên văn",
            "Chọn mục\ntrong 1 tài liệu", "TRUY HỒI\ntoàn kho",
            "Xã giao / ngoài\nphạm vi / hỏi lại"]
    ca = [63.3, 19.7, 6.8, 0.0, 10.2]
    luot = [96.9, 0.6, 0.0, 0.0, 2.5]

    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = range(len(nhan))
    r = 0.36
    ax.bar([i - r / 2 for i in x], ca, r, label="147 ca trả lời", color=XAM)
    ax.bar([i + r / 2 for i in x], luot, r, label="163 lượt phiên (có bộ nhớ)",
           color=XANH)

    for i, (a, b) in enumerate(zip(ca, luot)):
        ax.text(i - r / 2, a + 1.6, f"{a:.1f}".replace(".", ",") + "%",
                ha="center", fontsize=9)
        ax.text(i + r / 2, b + 1.6, f"{b:.1f}".replace(".", ",") + "%",
                ha="center", fontsize=9, fontweight="bold" if b > 50 else "normal")

    # Cột đáng nhìn nhất là cột 0% — nó là kết quả trung tâm của đồ án.
    ax.annotate("RAG chạy 0/310 lượt\ntrên hai tập này",
                xy=(3, 2), xytext=(3.05, 42), fontsize=9.5, color=DO,
                ha="center",
                arrowprops=dict(arrowstyle="->", color=DO, lw=1.3))

    ax.set_xticks(list(x))
    ax.set_xticklabels(nhan, fontsize=9)
    ax.set_ylabel("% lượt đi qua đường này")
    ax.set_ylim(0, 112)
    ax.set_title("Đường nào thật sự chạy trong một phiên hội thoại",
                 pad=12, fontweight="bold")
    ax.legend(frameon=False, loc="upper center", ncol=2,
              bbox_to_anchor=(0.62, 1.0))
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    luu(fig, "bd4-duong-di.png")


if __name__ == "__main__":
    print(f"vẽ vào {RA}")
    truy_hoi()
    so_doan()
    ablation()
    duong_di()
    print("xong")
