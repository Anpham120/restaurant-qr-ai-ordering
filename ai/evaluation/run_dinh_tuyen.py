# -*- coding: utf-8 -*-
"""CHẤT LƯỢNG ĐỊNH TUYẾN — luồng có đưa câu hỏi vào đúng lớp không, và sai thì mất bao nhiêu.

    python ai/evaluation/run_dinh_tuyen.py           # in bảng
    python ai/evaluation/run_dinh_tuyen.py --csv     # thêm CSV cho báo cáo

Vì sao thước đo này là thước đo CUỐI CÙNG của kiến trúc hai lớp
---------------------------------------------------------------
Ba phép đo trước trả lời "lớp nào tốt hơn ở loại câu nào":

    câu chọn món     lọc nhãn 100,00%  ·  truy hồi 58–68%      (mục 4.4)
    câu tri thức     tất định 12,00%   ·  truy hồi 44,00%      (mục 4.9.4)
    câu phân loại    tất định 53,06%   ·  truy hồi 73,47%      (bộ phủ kho)

Ba dòng này nói **khoảng cách giữa hai lớp phụ thuộc LOẠI CÂU HỎI, không phải hằng số**. Và điều đó
dẫn thẳng tới câu hỏi kiến trúc cuối cùng:

    Hệ thống có nhận ra loại câu hỏi trước khi chọn lớp không?

Nếu không, thì việc mỗi lớp mạnh ở đâu là **vô nghĩa về mặt thực dụng** — vì câu hỏi sẽ vào nhầm lớp
và mất phần lợi thế đó.

Ba con số bộ này tính
---------------------
    độ chính xác định tuyến   % câu đi đúng lớp
    trần oracle               kết quả NẾU mọi câu đều đi đúng lớp — chặn trên của kiến trúc
    chi phí sai định tuyến    trần oracle − kết quả thật

Con số thứ ba là con số đáng đưa vào báo cáo: nó tách **lỗi của lớp** khỏi **lỗi của bộ định tuyến**.
Cải thiện một bộ truy hồi đang bị định tuyến sai thì không cứu được gì.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))
sys.path.insert(0, str(REPO_ROOT / "ai" / "evaluation"))

from answer import respond  # noqa: E402
from understand import understand  # noqa: E402

MENU = json.loads(
    (REPO_ROOT / "backend" / "data" / "menu-dataset.json").read_text(encoding="utf-8-sig")
)["items"]
OUT_CSV = REPO_ROOT / "ai" / "evaluation" / "measurements" / "dinh_tuyen.csv"

# Ba LỚP mà một câu hỏi có thể cần. Tên ngắn để bảng đọc được.
LOC = "lọc nhãn"
TRUY = "truy hồi"
KHOA = "tra khóa"


def lop_cua_nhanh(branch: str) -> str:
    """Nhánh `respond()` chọn thuộc lớp nào."""
    goc = branch.split(":", 1)[0]
    if goc in ("knowledge_corpus",):
        return TRUY
    if goc in ("facts", "policy", "knowledge", "knowledge_missing"):
        return KHOA
    if goc in ("filter", "compare", "item_detail", "extreme", "price_lookup", "combo",
               "empty_result", "empty_result_offer_drop", "exhausted_after_exclusions",
               "allergen_named_dish", "serving_named_dish", "no_size", "price_assertion",
               "unknown_item", "da_bo_rang_buoc"):
        return LOC
    return f"khác:{goc}"


def nap_ca() -> list[dict]:
    """Ba tập, mỗi tập biết LỚP ĐÚNG của nó theo thiết kế.

    Lớp đúng KHÔNG suy từ hành vi hệ thống — nó suy từ **bản chất câu hỏi**, đặt lúc viết tập:

        chiều B (chọn món có ràng buộc)  -> CHỈ lọc nhãn, vì chỉ nó kiểm được điều kiện
        chiều A (tri thức văn xuôi)      -> CHỈ truy hồi, vì đáp án nằm trong đoạn văn
        bộ phủ kho (phân loại)           -> CẢ HAI đều hợp lệ

    Vì sao nhóm phân loại chấp nhận CẢ HAI — và đây là chỗ bản đầu của bộ đo này SAI
    ---------------------------------------------------------------------------------
    Bản đầu gán nhóm phân loại là "chỉ truy hồi", vì mỗi câu có một tài liệu đích. Đo ra 32,65%
    định tuyến đúng và 32,47 điểm chi phí — con số nghe rất tệ.

    Nhưng kiểm lại hành vi thật thì câu phân loại đi vào `filter` trả về **đúng món**:

        "Món nướng có những gì?"   -> filter, 6 món, 6/6 mang `method:grilled`
        "Có món Huế nào không?"    -> filter, 3 món, 3/3 mang `region:hue`

    Khách hỏi "món nướng có những gì" thì một danh sách món nướng **là** câu trả lời đúng. Tài liệu
    `kb.method.grilled` giàu thông tin hơn (tổng quan, dị nguyên, gợi ý chọn), nhưng danh sách món
    không sai.

    Nên với nhóm này, **cả hai lớp đều cho câu trả lời hợp lệ**, và gán một lớp làm "đúng" là áp
    một ý kiến lên phép đo. Bản này chấp nhận cả hai, và con số 32,47 điểm ở bản đầu là **tạo tác
    của khóa đáp án sai**, không phải lỗi của hệ thống.
    """
    ra: list[dict] = []
    import run_hai_chieu as H
    for cau, khoa in H.CHIEU_A:
        ra.append({"cau": cau, "tap": "tri thức", "lop_dung": TRUY, "dich": khoa})
    for cau, loc, dang in H.CHIEU_B:
        ra.append({"cau": cau, "tap": "chọn món", "lop_dung": LOC, "dich": dang})
    p = REPO_ROOT / "ai" / "evaluation" / "ca_phu_kho.json"
    if p.exists():
        for c in json.loads(p.read_text(encoding="utf-8"))["cases"]:
            ra.append({"cau": c["query"], "tap": "phân loại", "lop_dung": f"{LOC} hoặc {TRUY}",
                       "dich": c["topic_key"]})
    return ra


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", action="store_true")
    a = ap.parse_args(argv)

    ca = nap_ca()
    hang = []
    for c in ca:
        r = understand(c["cau"], MENU)
        p = respond(r, MENU)
        lop = lop_cua_nhanh(p.branch)
        chap_nhan = {x.strip() for x in c["lop_dung"].split("hoặc")}
        hang.append({**c, "nhanh": p.branch, "lop_thuc_te": lop,
                     "dung_lop": lop in chap_nhan})

    print("=" * 96)
    print(f"CHẤT LƯỢNG ĐỊNH TUYẾN — {len(ca)} câu hỏi, ba tập")
    print("=" * 96)

    print(f"\n{'tập':12} {'n':>4}  {'lớp ĐÚNG':12}  {'đi đúng':>9}  {'tỷ lệ':>8}")
    print("-" * 60)
    from thong_ke import khoang_wilson
    for tap in ("chọn món", "tri thức", "phân loại"):
        g = [h for h in hang if h["tap"] == tap]
        if not g:
            continue
        d = sum(h["dung_lop"] for h in g)
        k = khoang_wilson(d, len(g))
        print(f"{tap:12} {len(g):4}  {g[0]['lop_dung']:12}  {d:6}/{len(g):<3} "
              f"{k.ty_le * 100:7.2f}%")
    tong_dung = sum(h["dung_lop"] for h in hang)
    kt = khoang_wilson(tong_dung, len(hang))
    print("-" * 60)
    print(f"{'TỔNG':12} {len(hang):4}  {'':12}  {tong_dung:6}/{len(hang):<3} "
          f"{kt.ty_le * 100:7.2f}%   KTC {kt.duoi * 100:.2f}–{kt.tren * 100:.2f}%")

    print("\nSAI ĐỊNH TUYẾN ĐI ĐÂU")
    print("-" * 60)
    sai = [h for h in hang if not h["dung_lop"]]
    c = collections.Counter((h["lop_dung"], h["lop_thuc_te"]) for h in sai)
    for (dung, thuc), n in c.most_common():
        print(f"  cần {dung:10} -> vào {thuc:14} {n:4} câu")

    print("\nVÍ DỤ SAI ĐỊNH TUYẾN")
    print("-" * 60)
    for h in sai[:5]:
        print(f"  {h['cau'][:58]!r}")
        print(f"      cần {h['lop_dung']}, vào `{h['nhanh']}`")

    print("\nCHI PHÍ SAI ĐỊNH TUYẾN")
    print("-" * 60)
    print("  Ba phép đo trước cho biết mỗi lớp làm được bao nhiêu KHI ĐI ĐÚNG LỚP:")
    print("     câu chọn món  -> lọc nhãn 100,00%")
    print("     câu tri thức  -> truy hồi  44,00%")
    print("     câu phân loại -> truy hồi  73,47%")
    print()
    # Trần của nhóm phân loại lấy theo lớp TỐT HƠN trong hai lớp hợp lệ.
    tran = {"chọn món": 1.0000, "tri thức": 0.4400, "phân loại": 0.7347}
    tong_tran = tong_that = 0.0
    for tap, t in tran.items():
        g = [h for h in hang if h["tap"] == tap]
        if not g:
            continue
        ty_dung = sum(h["dung_lop"] for h in g) / len(g)
        tong_tran += t * len(g)
        # Câu đi nhầm lớp coi như hỏng — lớp kia không được thiết kế cho loại câu đó.
        tong_that += t * ty_dung * len(g)
        print(f"  {tap:12} trần {t * 100:6.2f}%  ×  định tuyến đúng {ty_dung * 100:6.2f}%"
              f"  =  {t * ty_dung * 100:6.2f}%")
    n = len(hang)
    print("-" * 60)
    print(f"  TRẦN ORACLE (định tuyến hoàn hảo) : {tong_tran / n * 100:6.2f}%")
    print(f"  ƯỚC LƯỢNG THẬT                    : {tong_that / n * 100:6.2f}%")
    print(f"  CHI PHÍ SAI ĐỊNH TUYẾN            : {(tong_tran - tong_that) / n * 100:6.2f} điểm")
    print()
    print("  Con số cuối tách LỖI CỦA LỚP khỏi LỖI CỦA BỘ ĐỊNH TUYẾN. Cải thiện một bộ truy hồi")
    print("  đang bị định tuyến sai thì không cứu được gì.")

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
