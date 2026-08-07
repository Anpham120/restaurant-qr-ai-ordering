# -*- coding: utf-8 -*-
"""SO SÁNH CÔNG BẰNG — cho mã tất định phủ TỪ VỰNG ĐẦY ĐỦ, rồi so với truy hồi.

    python ai/evaluation/run_phu_tu_vung.py           # in bảng
    python ai/evaluation/run_phu_tu_vung.py --csv     # thêm CSV cho báo cáo

Vì sao thí nghiệm này tồn tại
-----------------------------
Bộ đo hai chiều (mục 4.9) so mã tất định với truy hồi trên 50 câu tri thức, và mã tất định thua rõ.
Nhưng phép so đó **không công bằng**, và đây là chỗ người đọc báo cáo có quyền vặn:

    74/109 tài liệu trong kho KHÔNG có cụm từ vựng nào.

Nghĩa là mã tất định thua vì nó **chưa được cho công cụ**, không phải vì cách tiếp cận của nó kém.
Kết luận "cần lớp truy hồi" rút ra từ một phép so lệch thì không đứng vững.

Thí nghiệm này sửa điều đó: **sinh cụm từ vựng cho cả 109 tài liệu**, rồi đo lại trên **cùng 50 câu**.

Thiết kế
--------
Biến số duy nhất là **độ phủ từ vựng**. Kho không đổi, câu hỏi không đổi, chỉ khác đường tới:

    nhánh A   từ vựng đầy đủ (sinh từ tiêu đề tài liệu và tiêu đề mục) -> tra khóa
    nhánh B   embedding trên cùng kho                                  -> xếp hạng

SINH CỤM CÓ QUY TẮC, KHÔNG VIẾT TAY
------------------------------------
Cụm được sinh từ **tiêu đề tài liệu** và **tiêu đề mục**, theo quy tắc cố định. Viết tay thì tôi có
cơ hội chọn đúng cụm mình biết sẽ trúng 50 câu kia — và đó là cách chắc chắn nhất để ra một con số
đẹp mà vô nghĩa. Sinh theo quy tắc thì **tài liệu quyết định cụm**, không phải người đo.

Quy tắc rộng rãi có chủ ý — nó cho nhánh tất định **lợi thế**, không phải bất lợi:

    tiêu đề "Món ít dầu mỡ"  ->  "mon it dau mo", "it dau mo", "dau mo"
    mục "Gợi ý chọn món"     ->  "goi y chon mon", "chon mon"

CHẠY NGOẠI TUYẾN, KHÔNG ĐẨY VÀO PRODUCTION
-------------------------------------------
Bộ này **không** sửa `understand.VOCAB`. Thêm ~300 cụm rộng vào hệ thống thật sẽ nuốt câu của các
nhánh khác — ví dụ cụm `mon ga` sẽ bắt cả câu *"cho mình món gà"* vốn phải đi nhánh lọc. Rủi ro đó
là một kết quả riêng, và mục "Giá phải trả" ở cuối đo nó.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))
sys.path.insert(0, str(REPO_ROOT / "ai" / "evaluation"))

from rag.chunker import all_chunks, load_all  # noqa: E402

KHO = REPO_ROOT / "ai" / "knowledge"
OUT_CSV = REPO_ROOT / "ai" / "evaluation" / "measurements" / "phu_tu_vung.csv"

# Từ quá phổ biến — cụm chỉ gồm chúng thì khớp gần như mọi câu, và nhánh tất định sẽ "thắng" bằng
# cách trả lời bừa. Loại chúng là giữ cho phép đo có nghĩa, không phải làm khó nhánh tất định.
QUA_CHUNG = {
    "mon", "cac", "va", "cua", "cho", "voi", "trong", "nhung", "la", "co", "khong",
    "nha", "hang", "quan", "an", "uong", "gi", "nao", "the", "nay", "do", "tai", "lieu",
}


def fold(s: str) -> str:
    """Rút dấu — cùng phép biến đổi với `understand.fold`."""
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9\s]", " ", s)


def sinh_cum(tieu_de: str, tieu_de_muc: list[str]) -> set[str]:
    """Sinh cụm khớp cho một tài liệu, từ tiêu đề của chính nó.

    Sinh cả cụm ĐẦY ĐỦ lẫn cụm ĐUÔI: "mon it dau mo" và "it dau mo" và "dau mo". Cụm đuôi làm
    nhánh tất định bắt được nhiều cách hỏi hơn — cố ý cho nó lợi thế, để nếu nó vẫn thua thì kết
    luận mới đứng vững.
    """
    ra: set[str] = set()
    for nguon in [tieu_de, *tieu_de_muc]:
        tu = [t for t in fold(nguon).split() if t and t not in QUA_CHUNG]
        if not tu:
            continue
        # cụm đầy đủ, rồi bỏ dần từ đầu
        for i in range(len(tu)):
            cum = " ".join(tu[i:])
            if len(cum) >= 4:          # cụm quá ngắn khớp bừa
                ra.add(cum)
    return ra


def dung_bang_tu_vung() -> dict[str, list[str]]:
    """{topic_key: [cụm]} cho TOÀN BỘ tài liệu trong kho."""
    docs = load_all(KHO)
    doan = all_chunks(KHO)
    muc_theo_doc: dict[str, list[str]] = {}
    for c in doan:
        if c.heading:
            muc_theo_doc.setdefault(c.doc_id, []).append(c.heading)

    bang: dict[str, list[str]] = {}
    for d in docs:
        khoa = d.topic_keys[0] if d.topic_keys else d.doc_id
        cum = sinh_cum(d.title, muc_theo_doc.get(d.doc_id, []))
        bang[khoa] = sorted(cum)
    return bang


def tra_khoa(cau: str, bang: dict[str, list[str]]) -> str | None:
    """Tra khóa như lớp tất định làm: khớp cụm DÀI NHẤT trong câu."""
    f = fold(cau)
    tot_nhat, do_dai = None, 0
    for khoa, cums in bang.items():
        for c in cums:
            if re.search(rf"(?<![a-z]){re.escape(c)}(?![a-z])", f) and len(c) > do_dai:
                tot_nhat, do_dai = khoa, len(c)
    return tot_nhat


def doc_chieu_a() -> list[tuple[str, str]]:
    """50 câu chiều A và khóa chủ đề đúng — dùng lại nguyên tập của mục 4.9."""
    import run_hai_chieu
    return [(c, f"written_{k}" if not k.startswith("written_") else k)
            for c, k in run_hai_chieu.CHIEU_A]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true", help="ghi CSV cho báo cáo")
    a = ap.parse_args(argv)

    bang = dung_bang_tu_vung()
    tong_cum = sum(len(v) for v in bang.values())
    docs = load_all(KHO)

    print("=" * 92)
    print("SO SÁNH CÔNG BẰNG — mã tất định có TỪ VỰNG ĐẦY ĐỦ so với truy hồi")
    print("=" * 92)
    print(f"  kho              : {len(docs)} tài liệu")
    print(f"  cụm sinh ra      : {tong_cum} (trung bình {tong_cum / len(bang):.1f} cụm/tài liệu)")
    print(f"  phủ              : {len(bang)}/{len(docs)} tài liệu — 100%")
    print()

    import run_hai_chieu
    ca = run_hai_chieu.CHIEU_A
    hang = []
    dung_td = 0
    for cau, khoa_dung in ca:
        got = tra_khoa(cau, bang)
        ok = got is not None and khoa_dung in got
        dung_td += ok
        hang.append({"cau_hoi": cau, "khoa_dung": khoa_dung,
                     "tat_dinh_tra_ve": got or "", "tat_dinh_dung": ok})

    print(f"NHÁNH A — tất định có từ vựng đầy đủ : {dung_td}/{len(ca)} "
          f"({dung_td / len(ca) * 100:.2f}%)")

    # Nhánh B lấy từ bằng chứng đã đo của mục 4.9 — cùng 50 câu, không chạy lại.
    p = REPO_ROOT / "ai" / "evaluation" / "measurements" / "hai_chieu.csv"
    if p.exists():
        r = [x for x in csv.DictReader(p.open(encoding="utf-8-sig")) if x["chieu"] == "A"]
        t1 = sum(1 for x in r if x["truy_hoi_dung"] == "True")
        t5 = sum(1 for x in r if x["truy_hoi_top5"] == "True")
        print(f"NHÁNH B — truy hồi (embedding)       : top-1 {t1}/{len(r)} "
              f"({t1 / len(r) * 100:.2f}%) · top-5 {t5}/{len(r)} ({t5 / len(r) * 100:.2f}%)")
        print()
        try:
            from thong_ke import khoang_wilson, mcnemar
            ka = khoang_wilson(dung_td, len(ca))
            kb = khoang_wilson(t1, len(r))
            print(f"  KTC 95% tất định : {ka}")
            print(f"  KTC 95% truy hồi : {kb}")
            dung_b = [x["truy_hoi_dung"] == "True" for x in r]
            dung_a = [h["tat_dinh_dung"] for h in hang]
            if len(dung_a) == len(dung_b):
                kq = mcnemar(dung_a, dung_b)
                print(f"  {kq.ket_luan('tất định', 'truy hồi')}")
        except ImportError:
            pass

    print()
    print("GIÁ PHẢI TRẢ — cụm rộng nuốt câu của nhánh khác")
    print("-" * 92)
    nuot = []
    for cau in ("Món nào không cay?", "Cho mình món gà", "Có món chay nào không?",
                "Món nướng nào dưới 200 nghìn?", "Gợi ý món khai vị đi",
                "Mình dị ứng hải sản, món nào tránh được?"):
        got = tra_khoa(cau, bang)
        if got:
            nuot.append((cau, got))
    for cau, khoa in nuot:
        print(f"  {cau!r:44} -> bị đẩy sang chủ đề {khoa!r}")
    print(f"  {len(nuot)}/6 câu LỌC MÓN bị từ vựng mở rộng nuốt mất.")

    if a.csv:
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(hang[0]))
            w.writeheader()
            w.writerows(hang)
        print(f"\nđã ghi {OUT_CSV.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
