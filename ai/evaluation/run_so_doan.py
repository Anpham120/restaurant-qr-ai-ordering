# -*- coding: utf-8 -*-
"""TRÍCH BAO NHIÊU ĐOẠN — đo trên ĐÚNG đường sản xuất, không đo thẳng bộ truy hồi.

    python ai/evaluation/run_so_doan.py           # in bảng
    python ai/evaluation/run_so_doan.py --csv     # thêm CSV cho báo cáo

Vì sao bộ này tồn tại, trong khi đã có bảng Hit@k
-------------------------------------------------
Hit@k đo BỘ XẾP HẠNG. Nó không nói câu trả lời gửi cho khách có chứa tài liệu đúng hay không, vì
giữa hai thứ đó còn một bước: `answer.doan_tri_thuc_lien_quan()` khử trùng theo tài liệu rồi cắt
còn `SO_DOAN_TRI_THUC` đoạn.

Khử trùng làm hai con số lệch nhau và lệch theo chiều KHÔNG đoán được: một tài liệu 9 đoạn có thể
chiếm cả ba suất của Hit@3, nên Hit@3 = 68,00% không có nghĩa là 68,00% câu trả lời chứa tài liệu
đúng. Bộ này gọi thẳng hàm sản xuất nên nó đo đúng thứ khách nhận.

Ba cột được đo cùng lúc, vì tăng số đoạn là một ĐÁNH ĐỔI chứ không phải một cải tiến thuần:

    trúng      câu trả lời có chứa tài liệu đúng không          -> lợi
    độ dài     bao nhiêu từ khách phải đọc                      -> giá
    lạc        bao nhiêu đoạn KHÔNG thuộc tài liệu đúng lọt vào -> giá, và là giá nguy hiểm hơn

Cột thứ ba quan trọng nhất: một đoạn lạc trong câu trả lời không chỉ làm câu dài, nó làm khách đọc
một thông tin đúng-về-chuyện-khác và tưởng đó là câu trả lời cho mình.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))
sys.path.insert(0, str(REPO_ROOT / "ai" / "evaluation"))

import answer as A  # noqa: E402
from rag.chunker import load_all  # noqa: E402

KHO = REPO_ROOT / "ai" / "knowledge"
OUT_CSV = REPO_ROOT / "ai" / "evaluation" / "measurements" / "so_doan.csv"
MUC = (1, 2, 3, 5)


def nap_ca() -> list[tuple[str, set[str]]]:
    """Chiều A — 50 câu tri thức khó nhất, mỗi câu một tập tài liệu đích."""
    import run_hai_chieu as H

    docs = load_all(KHO)

    def dich(khoa: str) -> set[str]:
        return {d.doc_id for d in docs if d.doc_id == khoa or khoa in d.topic_keys}

    return [(q, dich(k)) for q, k in H.CHIEU_A if dich(k)]


def do_mot_muc(ca: list[tuple[str, set[str]]], so_doan: int) -> dict:
    """Đặt `SO_DOAN_TRI_THUC` rồi gọi ĐÚNG phép chọn của bản chạy thật.

    Gọi `chon_doan_tri_thuc()` chứ không gọi hàm trả về chữ: bản đầu của bộ đo này so tám từ đầu
    của chữ đã định dạng với văn bản tài liệu, và báo mức 1 đoạn đạt 36,00% trong khi Hit@1 của
    cùng bộ truy hồi là 48,00%. `chu_cho_khach()` bỏ tiêu đề và dấu markdown nên chuỗi không còn
    khớp — chênh 12 điểm đó là lỗi của phép đo, không phải của hệ thống.
    """
    cu = A.SO_DOAN_TRI_THUC
    A.SO_DOAN_TRI_THUC = so_doan
    try:
        hang = []
        for cau, dich in ca:
            got = A.chon_doan_tri_thuc(cau)
            chon = got[0] if got else []
            co_dich = any(c.doc_id in dich for c in chon)
            so_tu = len(" ".join(A.chu_cho_khach(c) for c in chon).split())
            hang.append({"cau": cau, "so_doan_xin": so_doan, "so_doan_thuc": len(chon),
                         "trung": co_dich, "so_tu": so_tu,
                         "doan_lac": sum(c.doc_id not in dich for c in chon),
                         "tai_lieu": "|".join(c.doc_id for c in chon)})
    finally:
        A.SO_DOAN_TRI_THUC = cu
    return {"so_doan": so_doan, "hang": hang}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args(argv)

    ca = nap_ca()
    from thong_ke import khoang_wilson, mcnemar

    print("=" * 84)
    print(f"SỐ ĐOẠN TRÍCH — {len(ca)} câu tri thức, đo trên đường sản xuất")
    print("=" * 84)
    print(f"\n  {'xin':>4} {'thực':>6} {'trúng':>10} {'tỷ lệ':>8} {'KTC 95%':>17} "
          f"{'từ (TV)':>8} {'đoạn lạc':>9}")
    print("  " + "-" * 70)

    tat_ca = {}
    for k in MUC:
        kq = do_mot_muc(ca, k)
        h = kq["hang"]
        tat_ca[k] = [x["trung"] for x in h]
        w = khoang_wilson(sum(x["trung"] for x in h), len(h))
        print(f"  {k:>4} {statistics.mean(x['so_doan_thuc'] for x in h):6.2f} "
              f"{sum(x['trung'] for x in h):5}/{len(h):<4} {w.ty_le * 100:7.2f}% "
              f"{w.duoi * 100:7.2f}–{w.tren * 100:6.2f}% "
              f"{statistics.median(x['so_tu'] for x in h):8.0f} "
              f"{sum(x['doan_lac'] for x in h) / len(h):8.2f}")

    print("\n  KIỂM ĐỊNH GHÉP CẶP so với mức 1 đoạn")
    print("  " + "-" * 70)
    for k in MUC[1:]:
        r = mcnemar(tat_ca[k], tat_ca[1])
        print(f"    {k} đoạn: {r.ket_luan(f'{k} đoạn', '1 đoạn')}")

    print("\n  ĐÁNH ĐỔI")
    print("  " + "-" * 70)
    print("    Mỗi đoạn thêm vào là một đoạn khách phải đọc mà KHÔNG trả lời câu hỏi của họ.")
    print("    Cột `đoạn lạc` là số đó, trung bình mỗi câu — nó phải được cân với cột `trúng`.")

    if a.csv:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        rows = [x for k in MUC for x in do_mot_muc(ca, k)["hang"]]
        with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"\n  đã ghi {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
