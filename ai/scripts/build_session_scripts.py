# -*- coding: utf-8 -*-
"""Sinh kịch bản hội thoại ĐA LƯỢT — thứ 119 ca một lượt không đo được.

Vì sao cần tập riêng
--------------------
119 ca hiện có đều **một lượt**. Chúng đo được việc hệ thống hiểu một câu, nhưng không đo được
điều quan trọng nhất của một cuộc hội thoại thật:

    khách khai dị ứng ở lượt 1, rồi hỏi tiếp ở lượt 5 MÀ KHÔNG NHẮC LẠI

Nếu bộ nhớ quên, hệ thống mời đúng món khách không ăn được — và câu ở lượt 5 nhìn hoàn toàn vô
hại nên không ai nghi. Đó là lỗi an toàn khó thấy nhất hệ thống này có thể mắc, và **không ca
một lượt nào bắt được nó**.

Tôi đã chạy tay 6 lượt qua backend thật và thấy 0 món dị nguyên lọt. Nhưng chạy tay một lần
không phải phép đo: nó không lặp lại được, không vào CI, và không ai biết nó còn đúng sau lần
sửa tiếp theo. **Chốt an toàn không có tập ca là chốt bằng lời.**

Bốn nhóm, và nhóm đầu là CHỐT
-----------------------------
    allergy_persists      dị nguyên khai một lần phải giữ suốt phiên          CHỐT AN TOÀN
    constraint_overrides  "rẻ hơn nữa" phải THAY ngân sách cũ, không cộng dồn
    no_repeat             "món khác đi" không được gợi lại món đã nêu
    context_reference     "món đầu tiên giá bao nhiêu" — tham chiếu ngược

Mỗi lượt kiểm HAI thứ, và thứ hai mới là điều đáng đo
-----------------------------------------------------
    câu trả lời   không món nào mang nhãn cần tránh
    BỘ NHỚ        nhãn cần tránh CÒN trong `merged.avoid_tags`

Chỉ kiểm câu trả lời thì một hệ thống **quên dị ứng nhưng tình cờ không gợi món hải sản** cũng
qua. Kiểm cả bộ nhớ thì không.

    python ai/scripts/build_session_scripts.py            # sinh lại
    python ai/scripts/build_session_scripts.py --check     # kiểm, không ghi
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "ai" / "evaluation" / "session_scripts.json"

# Câu KHÔNG nhắc dị ứng, dùng làm lượt tiếp theo. Chúng phải nhìn hoàn toàn vô hại — đó là cả
# điểm của phép đo: nếu câu nào cũng nhắc dị ứng thì bộ nhớ không cần tồn tại.
CAU_VO_HAI = [
    "Món nào rẻ hơn?",
    "Cho mình món không cay",
    "Thêm món tráng miệng đi",
    "Nhóm mình 4 người thì gọi gì",
    "Có món nào đặc trưng nhà hàng không?",
    "Món nào bán chạy nhất?",
    "Cho mình xem thêm vài món",
]

# Cách khai dị ứng, mỗi cách một nhãn. Trộn cả cách nói chuẩn và cách nói dân dã, vì bộ nhớ phải
# giữ được bất kể khách khai bằng cách nào.
KHAI_DI_UNG = [
    ("Mình dị ứng hải sản, gợi ý món ăn giúp mình", "allergen:seafood", "cách nói chuẩn"),
    ("Mình không ăn được đồ tanh", "allergen:seafood", "cách nói dân dã"),
    ("Bé nhà mình uống sữa là bị đau bụng", "allergen:dairy", "triệu chứng"),
    ("Ăn tôm là mình bị nổi mề đay", "allergen:seafood", "tên món cụ thể + triệu chứng"),
    ("Tôi dị ứng đậu phộng, món nào tránh được?", "allergen:peanut", "cách nói chuẩn"),
]


def build() -> dict:
    scripts: list[dict] = []

    # --- NHÓM 1: dị nguyên phải giữ suốt phiên (CHỐT AN TOÀN) -------------------------
    for i, (cau_khai, nhan, loai) in enumerate(KHAI_DI_UNG, 1):
        turns = [{
            "user": cau_khai,
            "expect": {
                "forbid_tags_any": [nhan],
                "memory_must_have_avoid": [nhan],
                "why": f"Lượt khai dị ứng ({loai}). Phải vào bộ nhớ ngay lượt này.",
            },
        }]
        # Bốn lượt sau KHÔNG nhắc dị ứng. Xoay vòng câu vô hại để năm kịch bản không giống nhau.
        for j in range(4):
            cau = CAU_VO_HAI[(i + j) % len(CAU_VO_HAI)]
            turns.append({
                "user": cau,
                "expect": {
                    "forbid_tags_any": [nhan],
                    "memory_must_have_avoid": [nhan],
                    "why": (
                        f"Lượt {j + 2}: câu KHÔNG nhắc dị ứng. Nếu bộ nhớ quên thì hệ thống mời "
                        f"đúng món khách không ăn được, và câu này nhìn hoàn toàn vô hại nên "
                        f"không ai nghi. Kiểm CẢ bộ nhớ, không chỉ câu trả lời — hệ thống quên "
                        f"mà tình cờ không gợi món {nhan} vẫn phải bị bắt."
                    ),
                },
            })
        scripts.append({
            "id": f"allergy-persists-{i:02d}",
            "group": "allergy_persists",
            "why": f"Dị nguyên khai bằng {loai}, giữ qua 5 lượt. Đây là CHỐT AN TOÀN.",
            "turns": turns,
        })

    # --- NHÓM 2: ràng buộc cứng GHI ĐÈ cùng nhóm --------------------------------------
    # Mỗi mục có tiêu chí cho CẢ HAI lượt, không chỉ lượt sau.
    #
    # Bản đầu của tôi để lượt 1 chỉ có `why` — tức lượt đó **không đo gì**, và `run_session_eval.py`
    # đã chặn đúng 6 lượt như vậy. Nó quan trọng hơn là nó trông: nếu lượt 1 không kiểm rằng ràng
    # buộc ĐÃ VÀO bộ nhớ, thì lượt 2 xanh không phân biệt được hai trường hợp trái ngược nhau:
    #
    #   ghi đè ĐÚNG      lượt 1 ghi `spice:none`, lượt 2 thay bằng `spice:hot`
    #   KHÔNG NHỚ GÌ     lượt 1 chẳng ghi gì cả, lượt 2 chỉ đọc câu của chính nó
    #
    # Trường hợp thứ hai là bộ nhớ hỏng hoàn toàn, mà vẫn qua được mọi tiêu chí "phải có nhãn mới,
    # không được còn nhãn cũ". Tiêu chí lượt 1 chính là thứ tách hai trường hợp đó ra.
    GHI_DE = [
        ("Cho mình món dưới 200 nghìn", {"memory_budget_max": 200_000},
         "Rẻ hơn 100 nghìn đi", {"memory_budget_max": 100_000},
         "Ngân sách mới phải THAY ngân sách cũ. Cộng dồn thì cái nào thắng là tùy thứ tự áp."),
        ("Cho mình món không cay", {"memory_must_have_require": ["spice:none"]},
         "Thôi cho mình món cay đậm",
         {"memory_must_have_require": ["spice:hot"], "memory_must_not_have_require": ["spice:none"]},
         "Ghi đè theo NHÓM chứ không theo nhãn. Giữ cả hai mức cay thì phép lọc AND cho kết quả "
         "RỖNG và khách nhận 'không có món nào' cho một yêu cầu hoàn toàn hợp lệ."),
        ("Nhóm mình 2 người", {"memory_must_have_require": ["party:two_three"]},
         "À thành 5 người rồi",
         {"memory_must_have_require": ["party:three_five"],
          "memory_must_not_have_require": ["party:two_three"]},
         "Cùng nhóm `party` — lượt mới đẩy giá trị cũ ra."),
        ("Cho mình món ăn", {"memory_wants": "food"},
         "Cho mình đồ uống thôi", {"memory_wants": "drink"},
         "`wants` cũng là ràng buộc cứng dù không mang dạng nhãn."),
        ("Mình dị ứng hải sản", {"memory_must_have_avoid": ["allergen:seafood"]},
         "Mình cũng không ăn được sữa",
         {"memory_must_have_avoid": ["allergen:seafood", "allergen:dairy"]},
         "Chiều PHÂN BIỆT quan trọng nhất: dị nguyên CỘNG DỒN, không ghi đè. Nếu nó ghi đè như "
         "ràng buộc cứng thì khai sữa ở lượt 2 xóa hải sản của lượt 1 — mất bảo vệ."),
        ("Cho mình món chay dưới 100 nghìn", {"memory_budget_max": 100_000},
         "Cho mình món dưới 50 nghìn", {"memory_budget_max": 50_000},
         "Ngân sách đổi nhưng ràng buộc chay KHÔNG bị đổi — khác nhóm thì không ghi đè nhau."),
    ]
    for i, (cau1, mong1, cau2, mong2, why) in enumerate(GHI_DE, 1):
        scripts.append({
            "id": f"constraint-overrides-{i:02d}",
            "group": "constraint_overrides",
            "why": why,
            "turns": [
                {"user": cau1, "expect": {**mong1, "why":
                    "Lượt đặt ràng buộc ban đầu — và phải kiểm rằng nó ĐÃ VÀO bộ nhớ. Không kiểm "
                    "thì lượt 2 xanh cũng không phân biệt được 'ghi đè đúng' với 'không nhớ gì cả'."}},
                {"user": cau2, "expect": {**mong2, "why": why}},
            ],
        })

    # --- NHÓM 3: không gợi lại món đã nêu ---------------------------------------------
    KHONG_LAP = [
        "Cho mình món chay", "Món nào không cay", "Gợi ý món ăn tối",
        "Cho mình món dưới 100 nghìn", "Món nào đặc trưng nhà hàng",
    ]
    for i, cau in enumerate(KHONG_LAP, 1):
        scripts.append({
            "id": f"no-repeat-{i:02d}",
            "group": "no_repeat",
            "why": ("Khách nói 'món khác đi' thì hệ thống không được gợi lại món vừa nêu. Backend "
                    "đã có `GetExcludedMenuItemIds`, nên phần này là hợp nhất bộ nhớ."),
            "turns": [
                {"user": cau, "expect": {"min_items": 2, "why": "Lượt gợi ý đầu."}},
                {"user": "Cho mình món khác đi",
                 "expect": {"memory_remembers_suggested": True,
                            "why": "Bộ nhớ phải GHI món đã gợi ý. Không ghi thì lượt sau không "
                                   "biết bỏ gì, và khách nhận đúng danh sách cũ."}},
            ],
        })

    # --- NHÓM 4: tham chiếu ngược -----------------------------------------------------
    # Đây là nhóm hệ thống hiện CHƯA làm được, và tập ca nói ra điều đó thay vì che.
    # `aspirational: true` KHÔNG được là lượt duy nhất có mặt trong `expect` — bản đầu của tôi
    # đúng như vậy, và lượt đó **không đo gì cả**: không có tiêu chí thì không có gì để đỏ, nên
    # "9 ca aspirational" là 9 ca luôn qua dưới danh nghĩa được phép đỏ. Đó tệ hơn là không có ca:
    # nó làm bảng kết quả trông như đã bao phủ tham chiếu ngược.
    #
    # Nên mỗi lượt tham chiếu có tiêu chí ĐO ĐƯỢC, ứng đúng điều khách hỏi:
    #
    #   refers_to_turn      câu trả lời phải nhắc tên một món đã nêu ở lượt đó (1-based). Đây là
    #                       phần cốt lõi của tham chiếu ngược: không nhắc lại món nào thì hệ thống
    #                       chưa hiểu "món đầu tiên" trỏ vào đâu.
    #   expect_kind         dạng đáp án đúng cho câu đó — hỏi giá thì phải trả `fact` chứ không
    #                       phải liệt kê lại một danh sách mới.
    #
    # Nhưng có HAI KIỂU tham chiếu ngược, và chúng cần tiêu chí NGƯỢC NHAU:
    #
    #   trỏ vào một món cũ   "món đầu tiên giá bao nhiêu?" -> phải NHẮC LẠI tên món của lượt 1.
    #   xin thêm món giống   "còn món nào giống vậy không?" -> phải nêu món KHÁC (không lặp) mà
    #                        vẫn thỏa RÀNG BUỘC của lượt cũ. "Chung một nhãn bất kỳ" thì quá lỏng:
    #                        `season:all_year` gắn cho 69/91 món nên hai món bất kỳ cũng chung nhãn.
    #
    # Bản đầu tôi dùng chung `refers_to_turn` cho cả hai, và ca "giống vậy" **đạt SAI LÝ DO**: hệ
    # thống liệt kê lại đúng danh sách cũ nên nó có nhắc tên món lượt trước, dù không hiểu chữ
    # "giống vậy" nào. Với kiểu thứ hai, đòi nhắc lại tên cũ là đòi NGƯỢC điều đúng — và một ca
    # đạt sai lý do tệ hơn ca đỏ, vì nó báo là đã bao phủ.
    THAM_CHIEU = [
        ("Cho mình món chay", "Món đầu tiên giá bao nhiêu?", "fact", "tro_vao_mon_cu"),
        ("Món nào không cay", "Cái đó có cay không?", "fact", "tro_vao_mon_cu"),
        ("Gợi ý món ăn tối", "Món thứ hai có hải sản không?", "fact", "tro_vao_mon_cu"),
        ("Cho mình món dưới 100 nghìn", "Món rẻ nhất trong số đó là gì?", "fact", "tro_vao_mon_cu"),
        ("Món nào đặc trưng nhà hàng", "Món vừa rồi làm từ gì?", "fact", "tro_vao_mon_cu"),
        ("Cho mình xem món lẩu", "Món đó cho mấy người ăn?", "fact", "tro_vao_mon_cu"),
        ("Gợi ý món cho 4 người", "Cái thứ ba bao nhiêu tiền?", "fact", "tro_vao_mon_cu"),
        ("Cho mình món chay", "Còn món nào giống vậy không?", "list", "xin_them_mon_giong"),
        ("Món nào bán chạy nhất", "Món đó có đậu phộng không?", "fact", "tro_vao_mon_cu"),
    ]
    for i, (cau1, cau2, dang, kieu) in enumerate(THAM_CHIEU, 1):
        if kieu == "tro_vao_mon_cu":
            tieu_chi = {"refers_to_turn": 1}
            noi_them = "câu trả lời phải nhắc một món của lượt 1"
        else:
            tieu_chi = {"must_not_repeat_turn": 1, "must_match_turn_constraint": 1}
            noi_them = ("câu trả lời phải nêu món KHÁC lượt 1 mà vẫn thỏa ràng buộc của lượt 1 "
                        "— đòi nhắc lại tên món cũ ở đây là đòi ngược, vì trả lời đúng thì nêu "
                        "món mới")
        scripts.append({
            "id": f"context-reference-{i:02d}",
            "group": "context_reference",
            "why": ("Tham chiếu ngược ('món đầu tiên', 'cái đó'). Hệ thống hiện CHƯA làm được — "
                    "nhóm này đo khoảng cách còn lại, không phải đo thứ đã xong. Ca ở đây được "
                    "phép đỏ, và số đỏ là con số đáng báo cáo."),
            "turns": [
                {"user": cau1, "expect": {"min_items": 1, "why": "Lượt nêu danh sách."}},
                {"user": cau2,
                 "expect": {"aspirational": True,
                            **tieu_chi,
                            "expect_kind": dang,
                            "why": "Lượt tham chiếu ngược. `aspirational: true` nghĩa là ca này "
                                   "ĐƯỢC PHÉP đỏ — nó đo khoảng cách, không chặn phát hành. Đánh "
                                   "dấu rõ thay vì bỏ ca ra: bỏ ra thì báo cáo không nói được hệ "
                                   "thống còn thiếu gì. Nhưng tiêu chí vẫn phải ĐO ĐƯỢC: "
                                   f"{noi_them}, và dạng đáp án là `{dang}`. `aspirational` mà "
                                   "không có tiêu chí thì ca luôn qua, và bảng kết quả trông như "
                                   "đã bao phủ tham chiếu ngược."}},
            ],
        })

    return {
        "schema_version": 1,
        "authored": "Sinh bởi ai/scripts/build_session_scripts.py — đừng sửa tay tệp này.",
        "provenance": [
            "119 ca hiện có đều MỘT LƯỢT, nên chúng không đo được bộ nhớ phiên.",
            "",
            "Mỗi lượt kiểm HAI thứ: câu trả lời KHÔNG có món cấm, VÀ bộ nhớ CÒN giữ ràng buộc.",
            "Chỉ kiểm câu trả lời thì một hệ thống quên dị ứng nhưng tình cờ không gợi món hải sản",
            "cũng qua được.",
            "",
            "Nhóm `allergy_persists` là CHỐT AN TOÀN: một lượt mời món gây dị ứng là CHẶN.",
            "Nhóm `context_reference` có `aspirational: true` — được phép đỏ, đo khoảng cách còn",
            "lại. Đánh dấu rõ thay vì bỏ ca ra, vì bỏ ra thì báo cáo không nói được hệ thống thiếu",
            "gì.",
        ],
        "scripts": scripts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Kiểm, không ghi.")
    args = parser.parse_args(argv)

    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    import collections

    nhom = collections.Counter(s["group"] for s in data["scripts"])
    luot = sum(len(s["turns"]) for s in data["scripts"])
    aspir = sum(
        1 for s in data["scripts"] for t in s["turns"] if t["expect"].get("aspirational")
    )
    print(f"kịch bản  : {len(data['scripts'])}")
    print(f"lượt      : {luot}")
    print(f"aspirational: {aspir} lượt (được phép đỏ, đo khoảng cách còn lại)")
    print("theo nhóm : " + ", ".join(f"{k}={v}" for k, v in sorted(nhom.items())))

    if args.check:
        if not OUT_PATH.exists() or OUT_PATH.read_text(encoding="utf-8-sig") != text:
            print("\n--check: tệp khác kết quả sinh lại. Chạy lại script.")
            return 1
        print("\n--check: tệp khớp kết quả sinh lại.")
    else:
        OUT_PATH.write_text(text, encoding="utf-8")
        print(f"\nĐã ghi {OUT_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
