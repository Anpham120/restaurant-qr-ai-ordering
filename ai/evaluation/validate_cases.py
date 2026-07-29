# -*- coding: utf-8 -*-
"""Kiểm tập đánh giá — bắt ca viết sai trước khi nó chấm sai hệ thống.

Bản cũ có 96 khóa đáp án trỏ vào những đoạn văn bản dành cho AI đọc chứ không dành cho
khách, và không ai phát hiện trong nhiều tháng. Nguyên nhân không phải thiếu cẩn thận:
một danh sách mã món viết tay thì **không có cách nào kiểm**.

Ở đây khóa đáp án là điều kiện chọn trên thực đơn, nên kiểm được. Bộ kiểm này từ chối:

- điều kiện chọn ra 0 món (ca không thể qua được, hoặc điều kiện viết sai);
- nhãn không có trong từ điển (gõ sai `spice:hot` thành `spice:hott`);
- mã món không tồn tại, hoặc giá ghi trong ca khác giá trong thực đơn;
- `require_min` lớn hơn số món mà điều kiện chọn được;
- `allowed` và `forbid` chồng nhau — ca tự mâu thuẫn;
- ca thiếu trường `why`, vì một ca không giải thích được thì không ai xét lại được nó.

    python ai/evaluation/validate_cases.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from menu_selectors import (
    SelectorError,
    select_ids,
    selector_tags,
    validate_selector,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = Path(__file__).resolve().parent / "cases.json"
MENU_PATH = REPO_ROOT / "backend" / "data" / "menu-dataset.json"
DICT_PATH = REPO_ROOT / "backend" / "data" / "menu-tags.json"

VALID_KINDS = {"fact", "list", "compare", "no_data", "clarify", "refuse"}
VALID_TYPES = {"A", "B", "C"}
SELECTOR_FIELDS = ("allowed", "forbid", "require_from")


def resolve(value, named: dict) -> dict:
    """Cho phép `"$tên"` hoặc `{"$ref": "tên", ...thêm điều kiện}` để khỏi lặp."""
    if isinstance(value, str):
        if not value.startswith("$"):
            raise SelectorError(f"tham chiếu phải bắt đầu bằng $: {value!r}")
        name = value[1:]
        if name not in named:
            raise SelectorError(f"không có điều kiện tên {name!r}")
        return {k: v for k, v in named[name].items() if not k.startswith("_")}
    if isinstance(value, dict):
        merged: dict = {}
        ref = value.get("$ref")
        if ref is not None:
            if ref not in named:
                raise SelectorError(f"không có điều kiện tên {ref!r}")
            merged.update(
                {k: v for k, v in named[ref].items() if not k.startswith("_")}
            )
        for key, val in value.items():
            if key in ("$ref",) or key.startswith("_"):
                continue
            if key in merged and key.startswith("tags"):
                merged[key] = list({*merged[key], *val})
            else:
                merged[key] = val
        return merged
    raise SelectorError(f"điều kiện chọn phải là chuỗi $tên hoặc dict: {value!r}")


def check(problems: list[str], case_id: str, message: str, ok: bool) -> None:
    if not ok:
        problems.append(f"{case_id}: {message}")


def main() -> int:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8-sig"))
    menu = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
    dictionary = json.loads(DICT_PATH.read_text(encoding="utf-8-sig"))

    items = menu["items"]
    by_id = {item["id"]: item for item in items}
    known = set(dictionary["tags"])
    named = data["named_selectors"]
    problems: list[str] = []

    # Điều kiện có tên phải tự đúng trước khi ca nào dùng nó.
    for name, selector in named.items():
        clean = {k: v for k, v in selector.items() if not k.startswith("_")}
        try:
            validate_selector(clean)
            hit = select_ids(items, clean)
        except SelectorError as exc:
            problems.append(f"named_selectors.{name}: {exc}")
            continue
        check(problems, f"named_selectors.{name}", "chọn ra 0 món", bool(hit))
        stray = selector_tags(clean) - known
        check(problems, f"named_selectors.{name}", f"nhãn lạ: {stray}", not stray)
        check(
            problems,
            f"named_selectors.{name}",
            "thiếu `_why` giải thích tập này là gì",
            "_why" in selector,
        )

    seen_ids: set[str] = set()
    for case in data["cases"]:
        cid = case.get("id", "<thiếu id>")
        check(problems, cid, "mã ca bị trùng", cid not in seen_ids)
        seen_ids.add(cid)
        check(problems, cid, f"type lạ: {case.get('type')!r}", case.get("type") in VALID_TYPES)
        check(problems, cid, "thiếu family", bool(case.get("family")))
        check(problems, cid, "thiếu question", bool(case.get("question")))

        expect = case.get("expect") or {}
        kind = expect.get("kind")
        check(problems, cid, f"kind lạ: {kind!r}", kind in VALID_KINDS)
        check(
            problems,
            cid,
            "thiếu `why` — ca không giải thích được thì không xét lại được",
            bool(expect.get("why", "").strip()),
        )

        resolved: dict[str, dict] = {}
        for field in SELECTOR_FIELDS:
            if field not in expect:
                continue
            try:
                selector = resolve(expect[field], named)
                validate_selector(selector)
            except SelectorError as exc:
                problems.append(f"{cid}.{field}: {exc}")
                continue
            resolved[field] = selector
            stray = selector_tags(selector) - known
            check(problems, cid, f"{field} có nhãn lạ: {sorted(stray)}", not stray)
            hit = select_ids(items, selector)
            if field in ("allowed", "require_from"):
                check(problems, cid, f"{field} chọn ra 0 món", bool(hit))

        # `require_min` phải khả thi: không đòi 5 món khi điều kiện chỉ có 2.
        need = expect.get("require_min")
        if need is not None:
            source = resolved.get("require_from") or resolved.get("allowed")
            if source is not None:
                have = len(select_ids(items, source))
                check(
                    problems,
                    cid,
                    f"require_min={need} nhưng điều kiện chỉ chọn được {have} món",
                    have >= need,
                )
            check(problems, cid, f"require_min phải >= 1, nhận {need}", need >= 1)

        # Ca tự mâu thuẫn: món vừa được phép vừa bị cấm.
        if "allowed" in resolved and "forbid" in resolved:
            overlap = select_ids(items, resolved["allowed"]) & select_ids(
                items, resolved["forbid"]
            )
            check(
                problems,
                cid,
                f"allowed và forbid chồng nhau ở {len(overlap)} món: "
                f"{sorted(overlap)[:3]}",
                not overlap,
            )

        # Dữ kiện phải khớp thực đơn — đây là chỗ khóa đáp án viết tay từng sai.
        for item_id, facts in (expect.get("facts") or {}).items():
            item = by_id.get(item_id)
            if item is None:
                problems.append(f"{cid}: mã món không tồn tại: {item_id}")
                continue
            if "price" in facts:
                check(
                    problems,
                    cid,
                    f"{item_id} ghi giá {facts['price']:,} nhưng thực đơn là "
                    f"{item['price']:,}",
                    facts["price"] == item["price"],
                )
            for tag in facts.get("tags_include", []):
                check(problems, cid, f"{item_id} nhãn lạ {tag}", tag in known)
                check(
                    problems,
                    cid,
                    f"{item_id} phải có nhãn {tag} nhưng thực đơn không có",
                    tag in item["tags"],
                )
            for tag in facts.get("tags_exclude", []):
                check(problems, cid, f"{item_id} nhãn lạ {tag}", tag in known)
                check(
                    problems,
                    cid,
                    f"{item_id} phải KHÔNG có nhãn {tag} nhưng thực đơn lại có",
                    tag not in item["tags"],
                )

        # Ca dị ứng phải luôn mở đường hỏi nhân viên: nhãn dị nguyên chỉ phủ 44/91 nên
        # danh sách lọc ra không phải kết luận về an toàn.
        if case.get("family", "").startswith("allergen") or any(
            "allergen" in json.dumps(resolved.get(f, {}), ensure_ascii=False)
            for f in SELECTOR_FIELDS
        ):
            check(
                problems,
                cid,
                "ca có ràng buộc dị nguyên nhưng thiếu must_offer_staff",
                expect.get("must_offer_staff") is True,
            )

    cases = data["cases"]
    print(f"số ca            : {len(cases)}")
    print(f"điều kiện có tên : {len(named)}")
    by_type = Counter(c["type"] for c in cases)
    print("theo loại        : " + ", ".join(f"{k}={by_type[k]}" for k in sorted(by_type)))
    by_kind = Counter(c["expect"]["kind"] for c in cases)
    print("theo dạng đáp án : " + ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items())))
    families = Counter(c["family"] for c in cases)
    print(f"số họ câu hỏi    : {len(families)}")
    singles = [f for f, n in families.items() if n == 1]
    if singles:
        print(f"họ chỉ có 1 ca   : {len(singles)} — {', '.join(sorted(singles))}")

    if problems:
        print(f"\nVẤN ĐỀ TRONG TẬP ĐÁNH GIÁ ({len(problems)}):")
        for line in problems:
            print(f"  - {line}")
        return 1
    print("\nKhông có vấn đề.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
