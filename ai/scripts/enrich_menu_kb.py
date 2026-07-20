"""Generate enriched menu sections for ai/knowledge-base/menu.md from menu-dataset.json."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MENU_JSON = PROJECT_ROOT / "backend" / "data" / "menu-dataset.json"
MENU_MD = PROJECT_ROOT / "ai" / "knowledge-base" / "menu.md"

SECTION_ORDER = [
    "cat_hải_sản",
    "cat_lẩu",
    "cat_món_gà",
    "cat_đặc_sản_vùng_miền",
    "cat_món_chay",
    "cat_cà_phê_trà",
    "cat_nước_ép_sinh_tố",
    "cat_tráng_miệng",
    "cat_trái_cây_tươi",
    "cat_alcohol",
]

SECTION_TITLES = {
    "cat_hải_sản": "Hải Sản",
    "cat_lẩu": "Lẩu",
    "cat_món_gà": "Món Gà",
    "cat_đặc_sản_vùng_miền": "Đặc Sản Vùng Miền",
    "cat_món_chay": "Món Chay",
    "cat_cà_phê_trà": "Cà Phê & Trà",
    "cat_nước_ép_sinh_tố": "Nước Ép & Sinh Tố",
    "cat_tráng_miệng": "Tráng Miệng",
    "cat_trái_cây_tươi": "Trái Cây Tươi",
    "cat_alcohol": "Bia & Rượu",
}


def short_desc(description: str, max_len: int = 120) -> str:
    compact = " ".join(description.split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3].rsplit(" ", 1)[0] + "..."


def build_sections() -> str:
    data = json.loads(MENU_JSON.read_text(encoding="utf-8-sig"))
    by_category: dict[str, list[dict]] = defaultdict(list)
    for item in data["items"]:
        by_category[item["categoryId"]].append(item)

    lines: list[str] = []
    for category_id in SECTION_ORDER:
        title = SECTION_TITLES[category_id]
        lines.append(f"## {title}")
        lines.append("")
        items = sorted(by_category[category_id], key=lambda row: row["id"])
        for item in items:
            tags = ", ".join(item.get("tags", [])[:6])
            desc = short_desc(item["description"])
            lines.append(
                f"- **{item['name']}** (menu_item_id: {item['id']}): {desc} Tags: {tags}."
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def patch_menu_md() -> None:
    raw = MENU_MD.read_text(encoding="utf-8")
    marker_start = "## Hải Sản, Lẩu, Món Gà, Đặc Sản, Món Chay"
    marker_end = "## Quy Tắc Gợi Ý Món"
    start = raw.index(marker_start)
    end = raw.index(marker_end)
    new_sections = build_sections()
    updated = raw[:start] + new_sections + "\n" + raw[end:]
    MENU_MD.write_text(updated, encoding="utf-8")
    print(f"Updated {MENU_MD}")


if __name__ == "__main__":
    patch_menu_md()
