# -*- coding: utf-8 -*-
"""Sinh bộ câu hỏi PHỦ HẾT tài liệu xếp hạng được — điều kiện để phép so truy hồi có nghĩa.

    python ai/evaluation/build_ca_phu_kho.py            # sinh lại
    python ai/evaluation/build_ca_phu_kho.py --check    # đỏ nếu tệp đã commit khác kết quả sinh

Vì sao bộ này tồn tại
---------------------
Chiều A của bộ hai chiều phủ **36/85** tài liệu `synthesize`. Nghĩa là mọi con số về truy hồi ở
Chương 4 được đo trên **43% kho** — và 49 tài liệu còn lại chưa có câu hỏi nào chạm tới.

Đó là lỗ hổng về hiệu lực: một bộ truy hồi có thể giỏi ở phần được đo và dở ở phần không được đo,
mà bảng kết quả vẫn đẹp. Với 49 tài liệu `derived` — nhóm có mức trùng lặp cao nhất (Jaccard trung
bình 0,408, cặp tệ nhất 0,921) — đó chính là phần KHÓ nhất, nên bỏ qua nó là tự cho điểm.

Thiết kế
--------
Mỗi tài liệu **hai câu hỏi**, và hai câu KHÁC NHAU CÓ CHỦ Ý:

    dạng A   dùng đúng từ có trong tài liệu    -> BM25 nên thắng
    dạng B   diễn đạt khác hoàn toàn            -> embedding nên thắng

Nhờ hai dạng mà tập **phân biệt được hai phương pháp** thay vì chỉ xếp hạng chúng. Một tập chỉ có
dạng A sẽ kết luận "BM25 đủ dùng"; một tập chỉ có dạng B sẽ kết luận ngược lại. Cả hai kết luận đều
là tạo tác của tập, không phải tính chất của phương pháp.

Vì sao SINH chứ không viết tay
------------------------------
49 tài liệu × 2 câu = 98 câu. Viết tay thì người viết vô thức viết câu mình biết hệ thống sẽ trả
lời được — và với chính người vừa xây hệ thống thì thiên lệch đó gần như chắc chắn.

Sinh từ **nhãn tiếng Việt** của từng giá trị thì danh sách câu do **dữ liệu** quyết định. Khuôn câu
là cố định; phần thay đổi giữa các câu là nhãn, nên không có chỗ cho việc chọn câu dễ.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

from rag.chunker import load_all  # noqa: E402

KHO = REPO_ROOT / "ai" / "knowledge"
DICT_PATH = REPO_ROOT / "backend" / "data" / "menu-tags.json"
OUT = REPO_ROOT / "ai" / "evaluation" / "ca_phu_kho.json"

# Khuôn câu hỏi cho từng nhóm nhãn.
#
#   dạng A — chứa nhãn tiếng Việt, đúng chữ tài liệu dùng
#   dạng B — mô tả bằng cảm giác hoặc tình huống, KHÔNG chứa nhãn
#
# Dạng B là phần khó viết và cũng là phần đáng giá nhất: nó đo được việc hiểu nghĩa. Với nhóm mà
# dạng B không viết được thành khuôn (`ingredient` — "món bò" thì diễn đạt khác kiểu gì?), bộ sinh
# dùng khuôn tình huống thay vì khuôn đồng nghĩa.
KHUON = {
    "method": ("Món {vi} có những gì?",
               "Mình muốn món chế biến kiểu {vi_thuong}, gợi ý giúp mình"),
    "region": ("Có món {vi} nào không?",
               "Mình nhớ vị quê {vi_thuong}, ăn gì cho giống?"),
    "ingredient": ("Món nào có {vi_thuong}?",
                   "Nhà mình thích ăn {vi_thuong}, quán có món nào không?"),
    "flavour": ("Món nào vị {vi_thuong}?",
                "Mình đang thèm cái gì đó {vi_thuong}, gợi ý đi"),
    "health": ("Món nào {vi_thuong}?",
               "Mình đang giữ dáng, muốn ăn kiểu {vi_thuong} thì chọn gì?"),
    "occasion": ("Món nào hợp {vi_thuong}?",
                 "Nhóm mình sắp đi {vi_thuong}, nên gọi món gì?"),
}


def nhan_vi() -> dict[str, str]:
    d = json.loads(DICT_PATH.read_text(encoding="utf-8-sig"))["tags"]
    return {k: v.get("label_vi", v.get("value", k)) for k, v in d.items()}


def dung() -> dict:
    docs = [d for d in load_all(KHO) if d.answer_mode == "synthesize"]
    vi = nhan_vi()
    ca: list[dict] = []

    for d in sorted(docs, key=lambda x: x.doc_id):
        phan = d.doc_id.split(".")
        if len(phan) < 3:
            continue
        nhom, gia_tri = phan[1], phan[2]
        if nhom not in KHUON:
            continue
        khoa_nhan = f"{nhom}:{gia_tri}"
        ten = vi.get(khoa_nhan)
        if not ten:
            continue
        khoa_chu_de = d.topic_keys[0] if d.topic_keys else d.doc_id
        a, b = KHUON[nhom]
        for i, khuon in enumerate((a, b), 1):
            cau = khuon.format(vi=ten, vi_thuong=ten.lower())
            ca.append({
                "id": f"phu-{nhom}-{gia_tri}-{i:02d}",
                "family": f"phu-{nhom}",
                "query": cau,
                "dang": "A" if i == 1 else "B",
                "doc_dich": d.doc_id,
                "topic_key": khoa_chu_de,
                "why": ("dùng đúng nhãn tiếng Việt — BM25 nên thắng" if i == 1
                        else "diễn đạt theo tình huống, không chứa nhãn — embedding nên thắng"),
            })

    return {
        "sinh_boi": "ai/evaluation/build_ca_phu_kho.py",
        "so_ca": len(ca),
        "so_tai_lieu": len({c["doc_dich"] for c in ca}),
        "cases": ca,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="kiểm, không ghi")
    a = ap.parse_args(argv)
    moi = json.dumps(dung(), ensure_ascii=False, indent=2) + "\n"
    if a.check:
        cu = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if cu != moi:
            print("TỆP ĐÃ COMMIT KHÁC KẾT QUẢ SINH LẠI.")
            print("Chạy: python ai/evaluation/build_ca_phu_kho.py")
            return 1
        print("--check: bộ ca phủ kho khớp kết quả sinh lại.")
        return 0
    OUT.write_text(moi, encoding="utf-8")
    d = json.loads(moi)
    print(f"Đã ghi {OUT.relative_to(REPO_ROOT)}")
    print(f"  {d['so_ca']} ca, phủ {d['so_tai_lieu']} tài liệu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
