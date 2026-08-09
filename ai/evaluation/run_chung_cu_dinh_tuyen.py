# -*- coding: utf-8 -*-
"""BẢNG CHỨNG CỨ định tuyến — in ra TỪNG câu đi sai, nhánh nào lấy, và nó trả về gì.

    python ai/evaluation/run_chung_cu_dinh_tuyen.py
    python ai/evaluation/run_chung_cu_dinh_tuyen.py --md    # bảng markdown cho báo cáo

Vì sao cần bộ này khi đã có `run_dinh_tuyen.py`
------------------------------------------------
`run_dinh_tuyen` in ra TỶ LỆ: "câu tri thức, định tuyến đúng 64,00%". Con số đó đúng nhưng không
kiểm chứng được — người đọc không có cách nào biết 36% còn lại sai kiểu gì, hay chúng có thật sự
sai không.

Và đó không phải lo xa. Chính bộ đo ấy từng báo nhóm `phân loại` sai 67,35% với **32,47 điểm chi
phí** — một con số nghe rất tệ mà hoá ra là **tạo tác của khoá đáp án sai**: những câu bị chấm sai
thực ra đi vào nhánh lọc và trả về đúng món. Không ai phát hiện được điều đó từ bảng tỷ lệ; phải
đọc từng câu mới thấy.

Nên bộ này in **dữ liệu thô**: câu hỏi, nhánh thực tế, ràng buộc bước hiểu đọc ra, và ba món đầu
trả về. Người chấm tự phán xét từng dòng thay vì tin một con số.

Ba nhóm kết quả, và ranh giới giữa chúng là điều đáng tranh luận nhất
---------------------------------------------------------------------
    ĐÚNG ĐÍCH   đi truy hồi như thiết kế
    CHẤP NHẬN   đi nhánh khác nhưng câu trả lời DÙNG ĐƯỢC — "Mình người Bắc, ăn gì cho hợp khẩu
                vị quê?" đi nhánh lọc và trả về Xôi gà Hà Nội, Bánh cuốn Thanh Trì, Phở gà ta.
                Đó **là** câu trả lời đúng, dù khoá đáp án nói phải đi truy hồi.
    SAI THẬT    câu trả lời không dùng được

Phân loại `CHẤP NHẬN` / `SAI THẬT` do **người** đặt trong bảng `PHAN_XU` bên dưới, không phải máy
suy ra — và nó được ghi thành mã để ai không đồng ý thì sửa đúng một chỗ, thay vì tranh luận suông.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))
sys.path.insert(0, str(HERE))

from answer import respond          # noqa: E402
from understand import understand   # noqa: E402
from run_dinh_tuyen import MENU     # noqa: E402

# Phán xử của NGƯỜI cho từng câu tri thức không đi truy hồi.
#
# Ghi thành mã chứ không để trong đầu: một con số như "64% định tuyến đúng" chỉ có nghĩa khi ranh
# giới đúng/sai được viết ra và cãi được. Ai thấy một dòng xếp sai thì sửa ở đây.
PHAN_XU: dict[str, tuple[str, str]] = {
    "Mình người Bắc, ăn gì cho hợp khẩu vị quê?":
        ("CHẤP NHẬN", "lọc `region:north` trả đúng món miền Bắc — đó LÀ câu trả lời"),
    "Mình vừa đi Tây Nguyên về, thèm vị đó thì gọi gì?":
        ("CHẤP NHẬN", "lọc `region:highlands` trả đúng đặc sản vùng"),
    "Mình thích vị ngọt kiểu trong Nam, gọi gì?":
        ("CHẤP NHẬN", "lọc `region:south` + `flavour:sweet`, cả hai ràng buộc đều đúng ý"),
    "Toàn món cơm mà không biết chọn cái nào cho no":
        ("CHẤP NHẬN", "lọc `cat_main` trả các món cơm — khách đang xin danh sách"),
    "Mình lái xe nên không dám uống gì có cồn, quán tính sao?":
        ("CHẤP NHẬN", "trả đồ uống không cồn; tài liệu `beer_and_alcohol` giàu hơn nhưng không sai"),
    "Ăn xong mà miệng vẫn cay xè thì uống gì cho dịu?":
        ("CHẤP NHẬN", "trả đồ uống mát — đúng thứ khách xin"),
    "Sau bữa nhiều dầu mỡ nên uống gì?":
        ("CHẤP NHẬN", "trả đồ uống — đúng loại"),
    "Gọi mấy món mà ăn cùng nhau cho hợp vị?":
        ("CHẤP NHẬN", "tra khoá `ordering_guide` — đúng chủ đề, và CHÍNH XÁC HƠN truy hồi"),
    "Lần đầu tới đây, gọi kiểu gì cho khỏi bỡ ngỡ?":
        ("CHẤP NHẬN", "tra khoá `first_visit` — đúng chủ đề"),
    "Quán biết món nào còn món nào hết không?":
        ("CHẤP NHẬN", "tra khoá `time_or_availability` — đúng chủ đề"),
    "Đặt bàn đông người thì cần báo trước bao lâu?":
        ("CHẤP NHẬN", "tra khoá `booking` — đúng chủ đề"),
    "Món nào hợp mang về nhà ăn?":
        ("CHẤP NHẬN", "tra khoá `delivery` — đúng chủ đề"),
    "Mình ăn cay giỏi, muốn thử vị miền Trung thật đậm":
        ("SAI THẬT", "lọc theo vùng nhưng BỎ QUA mức cay; trả cả Mì Quảng chay, Bún chay Huế"),
    "Ăn lẩu thì nên gọi thêm gì cho đủ bữa?":
        ("SAI THẬT", "khách hỏi gọi thêm gì NGOÀI lẩu, hệ thống trả về lẩu"),
    "Muốn cái gì mát mà rẻ, không phải trà sữa":
        ("SAI THẬT", "khách xin đồ uống mát, nhận về bánh mì và cháo lòng"),
    "Nhà có người dị ứng tôm mà vẫn muốn ăn đồ biển thì sao?":
        ("SAI THẬT", "câu về xử lý dị ứng, nhận về ba món không liên quan"),
    "Mình chỉ có ba mươi phút, kịp ăn gì không?":
        ("SAI THẬT", "không ràng buộc nào đọc ra được; ba món trả về là danh sách MẶC ĐỊNH"),
    "Ăn xong muốn cái gì mát mát tự nhiên thì có không?":
        ("CHẤP NHẬN", "lọc `season:cooling` trả món mát — 'có không?' là câu hỏi thực đơn, "
                      "và danh sách trả lời đúng nó"),
}


def ba_mon(reply, by_id) -> str:
    ten = [by_id[i]["name"] for i in reply.items if i in by_id][:3]
    return " · ".join(ten) if ten else "(không nêu món)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--md", action="store_true", help="in bảng markdown cho báo cáo")
    a = ap.parse_args(argv)

    import run_hai_chieu as H

    by_id = {i["id"]: i for i in MENU}
    hang = []
    for cau, _ in H.CHIEU_A:
        r = understand(cau, MENU)
        p = respond(r, MENU)
        if p.branch.startswith("knowledge_corpus:"):
            xu, vi_sao = "ĐÚNG ĐÍCH", "đi truy hồi như thiết kế"
        else:
            xu, vi_sao = PHAN_XU.get(cau, ("CHƯA PHÂN XỬ", "thêm dòng vào `PHAN_XU`"))
        hang.append({
            "cau": cau, "nhanh": p.branch, "xu": xu, "vi_sao": vi_sao,
            "rang_buoc": r.require_tags or r.categories or [],
            "mon": ba_mon(p, by_id),
        })

    dem = {k: sum(1 for h in hang if h["xu"] == k)
           for k in ("ĐÚNG ĐÍCH", "CHẤP NHẬN", "SAI THẬT", "CHƯA PHÂN XỬ")}
    n = len(hang)

    if a.md:
        print("| # | Câu hỏi | Nhánh thực tế | Phán xử | Vì sao |")
        print("|---:|---|---|---|---|")
        for i, h in enumerate(sorted(hang, key=lambda x: x["xu"]), 1):
            if h["xu"] == "ĐÚNG ĐÍCH":
                continue
            print(f"| {i} | {h['cau']} | `{h['nhanh']}` | **{h['xu']}** | {h['vi_sao']} |")
        print()
    else:
        print("=" * 100)
        print(f"CHỨNG CỨ ĐỊNH TUYẾN — {n} câu tri thức, in từng câu KHÔNG đi truy hồi")
        print("=" * 100)
        for h in sorted(hang, key=lambda x: (x["xu"] != "SAI THẬT", x["cau"])):
            if h["xu"] == "ĐÚNG ĐÍCH":
                continue
            print(f"\n  [{h['xu']}] {h['cau']}")
            print(f"      nhánh     : {h['nhanh']}")
            print(f"      ràng buộc : {h['rang_buoc'] or '(không đọc ra được)'}")
            print(f"      trả về    : {h['mon']}")
            print(f"      vì sao    : {h['vi_sao']}")

    print("\n" + "-" * 100)
    for k, v in dem.items():
        if v:
            print(f"  {k:16} {v:3}/{n}  = {v/n*100:5.1f}%")
    dung_that = dem["ĐÚNG ĐÍCH"] + dem["CHẤP NHẬN"]
    print(f"\n  Khoá đáp án NGHIÊM NGẶT (chỉ ĐÚNG ĐÍCH mới tính) : "
          f"{dem['ĐÚNG ĐÍCH']}/{n} = {dem['ĐÚNG ĐÍCH']/n*100:.2f}%")
    print(f"  Chấm theo CÂU TRẢ LỜI CÓ DÙNG ĐƯỢC KHÔNG          : "
          f"{dung_that}/{n} = {dung_that/n*100:.2f}%")
    print("\n  Hai con số này đo hai thứ khác nhau, và cả hai đều phải nêu. Con số thứ nhất là con")
    print("  số so sánh được giữa các bản; con số thứ hai là thứ khách thật cảm nhận.")
    if dem["CHƯA PHÂN XỬ"]:
        print(f"\n  CẢNH BÁO: {dem['CHƯA PHÂN XỬ']} câu chưa có phán xử — thêm vào `PHAN_XU`.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
