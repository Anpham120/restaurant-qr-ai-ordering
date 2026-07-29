# -*- coding: utf-8 -*-
"""Đo hiệu quả từng cơ chế: tắt một cái, chạy lại, so với bản đầy đủ.

Vì sao cần
----------
Bản cũ có 8 đường xử lý tất định mà không ai chứng minh được đường nào có giá trị — hai
đường bị một cờ legacy tắt mà hệ thống vẫn hoạt động đúng, tức chúng là dư. Một cơ chế
không đo được thì không nên có.

Bộ này tắt từng cơ chế bằng cách thay hàm/hằng số, chạy lại toàn bộ 80 ca, và báo:

- số ca mất đi khi thiếu cơ chế đó;
- **số lỗi an toàn** phát sinh — cột này quan trọng hơn cột trên, vì một cơ chế chỉ cứu
  vài ca nhưng ngăn được lỗi dị ứng thì vẫn phải giữ.

Cơ chế nào tắt mà không mất gì thì hoặc là dư, hoặc là tập đánh giá chưa có ca cho nó —
và bộ này in ra cả hai khả năng chứ không tự kết luận.

    python ai/evaluation/run_ablation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "ai" / "app"))

import answer as answer_mod           # noqa: E402
import understand as und              # noqa: E402
from answer_metric import Answer, score   # noqa: E402

MENU = json.loads(
    (REPO_ROOT / "backend" / "data" / "menu-dataset.json").read_text(encoding="utf-8-sig")
)
DATA = json.loads((HERE / "cases.json").read_text(encoding="utf-8-sig"))
CASES = DATA["cases"]
NAMED = DATA["named_selectors"]
ITEMS = MENU["items"]


def measure() -> tuple[int, int]:
    """(số ca qua, số ca lỗi an toàn)"""
    ok = unsafe = 0
    for case in CASES:
        request = und.understand(case["question"], ITEMS)
        reply = answer_mod.respond(request, ITEMS)
        verdict = score(
            case,
            Answer(text=reply.text, items=reply.items, kind=reply.kind,
                   asks_back=reply.asks_back),
            MENU,
            NAMED,
        )
        ok += verdict.passed
        unsafe += verdict.safety_failed
    return ok, unsafe


# --- Các cách tắt cơ chế -------------------------------------------------------------


def off_span_consumption():
    """Tắt việc ăn hết đoạn đã khớp — quay về so từng cụm độc lập như bản cũ.

    Đây là cơ chế chống đụng chữ. Không có nó, `ban chay` lại khớp `chay`.
    """
    original = und.understand

    def naive(question: str, menu_items: list[dict]):
        request = original(question, menu_items)
        # Khớp lại toàn bộ từ vựng trên chữ GỐC, không trừ đoạn nào — đúng cách bản cũ làm.
        folded = f" {und.fold(question)} "
        for phrase, (kind, value) in und.VOCAB.items():
            if f" {phrase} " not in folded:
                continue
            if kind == "require" and value not in request.require_tags:
                request.require_tags.append(str(value))
            elif kind == "category" and value not in request.categories:
                request.categories.append(str(value))
        return request

    und.understand = naive
    return lambda: setattr(und, "understand", original)


def off_unique_prefix():
    """Tắt việc nhận tên món rút gọn — chỉ nhận tên đầy đủ."""
    original = und._name_candidates
    und._NAME_CACHE.clear()

    def full_only(menu_items: list[dict]):
        out = [(f" {und.fold(m['name'])} ", m["id"], m["name"]) for m in menu_items]
        out.sort(key=lambda c: (-len(c[0]), c[0]))
        return out

    und._name_candidates = full_only
    def restore():
        und._name_candidates = original
        und._NAME_CACHE.clear()
    return restore


def off_allergen_framing():
    """Tắt việc phân biệt chủ đề dị nguyên với cách hỏi.

    Quay về bản đầu của tôi: chỉ nhận đúng cụm cố định "dị ứng X".
    """
    original = und.AVOID_FRAMING
    und.AVOID_FRAMING = ("di ung",)
    return lambda: setattr(und, "AVOID_FRAMING", original)


def off_occasion_as_preference():
    """Tắt việc coi dịp ăn là ngữ cảnh — dùng nó làm bộ lọc cứng."""
    original = answer_mod.respond

    def hard_filter(request, items):
        request.require_tags = request.require_tags + request.prefer_tags
        request.prefer_tags = []
        return original(request, items)

    answer_mod.respond = hard_filter
    return lambda: setattr(answer_mod, "respond", original)


def off_strict_budget():
    """Tắt phân biệt 'rẻ hơn X' với 'tầm X trở xuống' — luôn dùng <=."""
    original = und.STRICT_BUDGET_FRAMING
    und.STRICT_BUDGET_FRAMING = ()
    return lambda: setattr(und, "STRICT_BUDGET_FRAMING", original)


def off_food_drink_split():
    """Tắt phân biệt món ăn với đồ uống — chính lỗi 'tư vấn món mà đưa bia vào'."""
    original = answer_mod.select

    def ignore_wants(request, items):
        saved = request.wants
        request.wants = "any"
        try:
            return original(request, items)
        finally:
            request.wants = saved

    answer_mod.select = ignore_wants
    return lambda: setattr(answer_mod, "select", original)


def off_allergen_filter():
    """Tắt hẳn việc loại món theo dị nguyên. Cột lỗi an toàn phải nổ."""
    original = answer_mod.select

    def no_avoid(request, items):
        saved = request.avoid_tags
        request.avoid_tags = []
        try:
            return original(request, items)
        finally:
            request.avoid_tags = saved

    answer_mod.select = no_avoid
    return lambda: setattr(answer_mod, "select", original)


def off_unknown_item_list():
    """Tắt danh sách món nhà hàng không bán."""
    original = und.NOT_ON_MENU
    und.NOT_ON_MENU = ()
    return lambda: setattr(und, "NOT_ON_MENU", original)


def off_punctuation_stripping():
    """Tắt việc bỏ dấu câu trong bước chuẩn hóa."""
    original = und.fold

    def keep_punct(text: str) -> str:
        import re
        import unicodedata
        lowered = unicodedata.normalize("NFD", text.lower())
        without = "".join(c for c in lowered if unicodedata.category(c) != "Mn")
        return re.sub(r"\s+", " ", without.replace("đ", "d")).strip()

    und.fold = keep_punct
    und._NAME_CACHE.clear()
    def restore():
        und.fold = original
        und._NAME_CACHE.clear()
    return restore


ABLATIONS = [
    ("ăn hết đoạn đã khớp (chống đụng chữ)", off_span_consumption),
    ("bỏ dấu câu khi chuẩn hóa", off_punctuation_stripping),
    ("nhận tên món rút gọn (tiền tố duy nhất)", off_unique_prefix),
    ("phân biệt chủ đề dị nguyên với cách hỏi", off_allergen_framing),
    ("lọc theo dị nguyên (fail-closed)", off_allergen_filter),
    ("phân biệt món ăn với đồ uống", off_food_drink_split),
    ("dịp ăn là ngữ cảnh, không phải ràng buộc", off_occasion_as_preference),
    ("phân biệt 'rẻ hơn X' với 'tầm X'", off_strict_budget),
    ("danh sách món nhà hàng không bán", off_unknown_item_list),
]


def main() -> int:
    base_ok, base_unsafe = measure()
    print(f"bản đầy đủ: {base_ok}/{len(CASES)} ca qua, {base_unsafe} lỗi an toàn\n")
    print(f"{'cơ chế bị tắt':44} {'qua':>7} {'mất':>5} {'lỗi an toàn':>12}")
    print("-" * 72)

    rows = []
    for label, disable in ABLATIONS:
        restore = disable()
        try:
            ok, unsafe = measure()
        finally:
            restore()
        rows.append((label, ok, base_ok - ok, unsafe))

    rows.sort(key=lambda r: (-r[3], -r[2]))
    for label, ok, lost, unsafe in rows:
        mark = "  <-- lỗi an toàn" if unsafe else ""
        print(f"{label:44} {ok:3}/{len(CASES):<3} {lost:5} {unsafe:12}{mark}")

    useless = [r for r in rows if r[2] == 0 and r[3] == 0]
    print()
    if useless:
        print("Cơ chế tắt mà KHÔNG mất ca nào và không sinh lỗi an toàn:")
        for label, _ok, _lost, _unsafe in useless:
            print(f"  - {label}")
        print(
            "  Hai khả năng, và bộ này không tự kết luận: cơ chế đó là dư, HOẶC tập đánh\n"
            "  giá chưa có ca nào phân biệt được nó. Phải xét từng cái."
        )
    else:
        print("Mọi cơ chế đều có ít nhất một ca chứng minh giá trị của nó.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
