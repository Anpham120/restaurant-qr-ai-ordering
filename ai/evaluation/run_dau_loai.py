# -*- coding: utf-8 -*-
"""ĐẤU LOẠI ba bộ truy hồi trên bộ ca PHỦ HẾT KHO, rồi so quán quân với mã tất định.

    python ai/evaluation/run_dau_loai.py           # in bảng
    python ai/evaluation/run_dau_loai.py --csv     # thêm CSV cho báo cáo

Vì sao chạy riêng thay vì dùng lại bảng ở mục 4.2
--------------------------------------------------
Bảng 4.2 đo trên tập truy hồi 222 ca, và tập đó phủ **36/85** tài liệu `synthesize`. Bộ này phủ
**49 tài liệu còn lại** — chính là nhóm `derived` có mức trùng lặp cao nhất (Jaccard trung bình
0,408; cặp tệ nhất 0,921).

Nói cách khác: bảng 4.2 đo phần dễ, bộ này đo phần khó. Một bộ truy hồi thắng ở phần dễ mà thua ở
phần khó thì bảng 4.2 một mình sẽ dẫn tới quyết định sai.

Ba câu hỏi bộ này trả lời, theo đúng thứ tự
-------------------------------------------
    1. Trong BA bộ truy hồi, bộ nào tốt nhất?      -> đấu loại, chọn quán quân
    2. Quán quân so với mã tất định thì sao?       -> cùng câu hỏi, hai đường
    3. Chênh lệch có ý nghĩa thống kê không?       -> McNemar ghép cặp

Thứ tự này quan trọng. So cả bốn cùng lúc thì không biết bộ truy hồi thua vì bản thân nó kém hay vì
chọn nhầm bộ. Chọn quán quân trước rồi mới so là loại được khả năng thứ hai.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))
sys.path.insert(0, str(REPO_ROOT / "ai" / "evaluation"))

from rag.chunker import doan_toan_kho  # noqa: E402

KHO = REPO_ROOT / "ai" / "knowledge"
CA = REPO_ROOT / "ai" / "evaluation" / "ca_phu_kho.json"
OUT_CSV = REPO_ROOT / "ai" / "evaluation" / "measurements" / "dau_loai.csv"
K = 5


def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", s)


def dung_bo(doan):
    """Ba bộ truy hồi. Bộ nào thiếu thư viện thì báo và bỏ, không giả vờ đo."""
    from rag.bm25 import Bm25Index
    from rag.hybrid import HybridRetriever
    bm = Bm25Index.build(doan)
    ra = {"bm25": bm}
    try:
        import rag.embedding as EMB
        emb = EMB.EmbeddingIndex.build(doan, normalize=True, use_prefix=True)
        ra["embedding"] = emb
        ra["hybrid"] = HybridRetriever(retrievers=[bm, emb])
    except Exception as loi:
        print(f"  !! embedding và hybrid BỊ BỎ QUA: {type(loi).__name__}: {loi}")
    return ra


def tat_dinh(cau: str, tra: dict[str, list[str]]) -> str | None:
    """Mã tất định: khớp cụm từ vựng DÀI NHẤT. Cùng cách bảng từ vựng thật làm."""
    f = fold(cau)
    tot, dai = None, 0
    for khoa, cums in tra.items():
        for c in cums:
            if re.search(rf"(?<![a-z]){re.escape(c)}(?![a-z])", f) and len(c) > dai:
                tot, dai = khoa, len(c)
    return tot


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args(argv)

    ca = json.loads(CA.read_text(encoding="utf-8"))["cases"]
    doan = doan_toan_kho(KHO)
    bo = dung_bo(doan)
    theo_doc = {}
    for c in doan:
        theo_doc.setdefault(c.doc_id, []).append(c.chunk_id)

    print("=" * 96)
    print(f"ĐẤU LOẠI TRÊN BỘ PHỦ KHO — {len(ca)} câu hỏi, {len({c['doc_dich'] for c in ca})} tài liệu")
    print("=" * 96)

    # ---------- vòng 1: ba bộ truy hồi ----------
    ket: dict[str, list[bool]] = {}
    tre: dict[str, float] = {}
    for ten, r in bo.items():
        dung, t0 = [], time.perf_counter()
        for c in ca:
            hits = r.search(c["query"], k=K)
            ids = [h.chunk_id for h in hits]
            dich = set(theo_doc.get(c["doc_dich"], []))
            dung.append(bool(ids) and ids[0] in dich)
        tre[ten] = (time.perf_counter() - t0) * 1000 / len(ca)
        ket[ten] = dung

    from thong_ke import khoang_wilson, mcnemar
    print("\nVÒNG 1 — ba bộ truy hồi (Hit@1)")
    print(f"  {'bộ':12} {'đúng':>8} {'tỷ lệ':>9}  {'KTC 95%':>18}  {'ms/câu':>8}")
    print("  " + "-" * 62)
    for ten, d in sorted(ket.items(), key=lambda x: -sum(x[1])):
        k = khoang_wilson(sum(d), len(d))
        print(f"  {ten:12} {sum(d):4}/{len(d):<3} {k.ty_le * 100:8.2f}%  "
              f"{k.duoi * 100:7.2f}–{k.tren * 100:6.2f}%  {tre[ten]:7.1f}")

    quan_quan = max(ket, key=lambda t: sum(ket[t]))
    print(f"\n  QUÁN QUÂN: {quan_quan}")
    for t in ket:
        if t != quan_quan:
            r = mcnemar(ket[quan_quan], ket[t])
            print(f"    so với {t:10}: {r.ket_luan(quan_quan, t)}")

    # ---------- vòng 2: quán quân vs mã tất định ----------
    print("\nVÒNG 2 — quán quân so với MÃ TẤT ĐỊNH (cùng câu hỏi)")
    import understand as U
    tra: dict[str, list[str]] = {}
    for cum, (loai, gt) in U.VOCAB.items():
        if loai in ("knowledge", "policy"):
            tra.setdefault(str(gt), []).append(fold(cum))
    td = [tat_dinh(c["query"], tra) == c["topic_key"] for c in ca]

    # Nhánh CÔNG BẰNG: mã tất định với từ vựng SINH ĐỦ cho cả 49 tài liệu.
    #
    # Dòng `td` ở trên cho 0/98, nhưng con số đó nói về ĐỘ PHỦ TỪ VỰNG chứ không nói về cách tiếp
    # cận: 49 tài liệu này không có cụm nào trong bảng từ vựng thật. So như vậy là so một bên có
    # công cụ với một bên không, và kết luận rút ra từ đó không đứng vững.
    #
    # Nhánh này sinh cụm từ TIÊU ĐỀ TÀI LIỆU và TIÊU ĐỀ MỤC — cùng quy tắc với `run_phu_tu_vung.py`
    # — rồi đo lại trên đúng 98 câu đó.
    import run_phu_tu_vung as PT
    bang_du = PT.dung_bang_tu_vung()
    td_du = [PT.tra_khoa(c["query"], bang_du) == c["topic_key"] for c in ca]

    kq = khoang_wilson(sum(td), len(td))
    kr = khoang_wilson(sum(ket[quan_quan]), len(ca))
    print(f"  {'mã tất định':16} {sum(td):4}/{len(ca):<3} {kq.ty_le * 100:8.2f}%  "
          f"KTC {kq.duoi * 100:.2f}–{kq.tren * 100:.2f}%")
    print(f"  {quan_quan:16} {sum(ket[quan_quan]):4}/{len(ca):<3} {kr.ty_le * 100:8.2f}%  "
          f"KTC {kr.duoi * 100:.2f}–{kr.tren * 100:.2f}%")
    kd = khoang_wilson(sum(td_du), len(td_du))
    print(f"  {'tất định + từ vựng đủ':16} {sum(td_du):4}/{len(ca):<3} {kd.ty_le * 100:8.2f}%  "
          f"KTC {kd.duoi * 100:.2f}–{kd.tren * 100:.2f}%")
    print()
    print("  Dòng đầu nói về ĐỘ PHỦ TỪ VỰNG — 49 tài liệu này không có cụm nào trong bảng thật.")
    print("  Dòng thứ ba mới nói về CÁCH TIẾP CẬN.")
    r = mcnemar(ket[quan_quan], td_du)
    print(f"\n  {r.ket_luan(quan_quan, 'tất định + từ vựng đủ')}")

    # ---------- theo dạng câu ----------
    print("\nTHEO DẠNG CÂU — chỗ hai phương pháp mạnh khác nhau")
    print(f"  {'dạng':6} {'n':>4}  {'tất định+':>10}  {'bm25':>8}  {'embedding':>10}  {'hybrid':>8}")
    print("  " + "-" * 60)
    for dang in ("A", "B"):
        idx = [i for i, c in enumerate(ca) if c["dang"] == dang]
        cot = [f"{sum(td_du[i] for i in idx) / len(idx) * 100:9.2f}%"]
        for t in ("bm25", "embedding", "hybrid"):
            cot.append(f"{sum(ket[t][i] for i in idx) / len(idx) * 100:9.2f}%"
                       if t in ket else "        —")
        print(f"  {dang:6} {len(idx):4}  {cot[0]}  {cot[1]:>8}  {cot[2]:>10}  {cot[3]:>8}")
    print("\n  dạng A = dùng đúng nhãn tiếng Việt · dạng B = diễn đạt theo tình huống")

    if a.csv:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            cot = ["id", "dang", "query", "topic_key", "tat_dinh", "tat_dinh_du_tu_vung"] + list(ket)
            w = csv.DictWriter(f, fieldnames=cot)
            w.writeheader()
            for i, c in enumerate(ca):
                w.writerow({"id": c["id"], "dang": c["dang"], "query": c["query"],
                            "topic_key": c["topic_key"], "tat_dinh": td[i], "tat_dinh_du_tu_vung": td_du[i],
                            **{t: ket[t][i] for t in ket}})
        print(f"\nđã ghi {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
