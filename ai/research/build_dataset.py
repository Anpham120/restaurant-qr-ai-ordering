from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from app.text import normalize_text
from research.menu_seed import parse_restaurant_menu_seed, write_snapshot


AI_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = AI_ROOT.parent
DEFAULT_SEED = PROJECT_ROOT / "backend" / "src" / "RestaurantQrAiOrdering.Api" / "Data" / "RestaurantMenuSeed.cs"


def build_cases(seed_path: Path, manual_path: Path) -> tuple[list[dict], object]:
    snapshot = parse_restaurant_menu_seed(seed_path)
    try:
        source_label = seed_path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        source_label = seed_path.name
    snapshot = replace(snapshot, source=source_label)
    cases: list[dict] = []
    by_category: dict[str, list[str]] = {}

    for item in snapshot.items:
        split = _group_split(item.id)
        expected = f"menu:{item.id}"
        cases.append(
            {
                "id": f"exact_{item.id}",
                "group_id": item.id,
                "split": split,
                "slice": "exact_name",
                "question": f"Cho tôi thông tin về {item.name}",
                "expected_ids": expected,
                "expected_flags": "",
            }
        )
        cases.append(
            {
                "id": f"nodia_{item.id}",
                "group_id": item.id,
                "split": split,
                "slice": "no_diacritic",
                "question": f"quan co {normalize_text(item.name)} khong",
                "expected_ids": expected,
                "expected_flags": "",
            }
        )
        by_category.setdefault(item.category_id, []).append(expected)

    category_names = {item.category_id: item.category_name for item in snapshot.items}
    for category_id, expected_ids in sorted(by_category.items()):
        cases.append(
            {
                "id": f"category_{category_id}",
                "group_id": f"category:{category_id}",
                "split": _group_split(f"category:{category_id}"),
                "slice": "category_intent",
                "question": f"Gợi ý các món thuộc nhóm {category_names[category_id]}",
                "expected_ids": ";".join(expected_ids),
                "expected_flags": "",
            }
        )

    for item in json.loads(manual_path.read_text(encoding="utf-8")):
        cases.append(
            {
                "id": item["id"],
                "group_id": item["group_id"],
                # Split is derived centrally so every variant of one menu item
                # or policy remains on exactly one side of the experiment.
                "split": _group_split(item["group_id"]),
                "slice": item["slice"],
                "question": item["question"],
                "expected_ids": ";".join(item.get("expected_ids", [])),
                "expected_flags": ";".join(item.get("expected_flags", [])),
            }
        )

    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Evaluation case IDs must be unique")
    split_by_group: dict[str, set[str]] = {}
    for case in cases:
        split_by_group.setdefault(case["group_id"], set()).add(case["split"])
    leaking = {group: splits for group, splits in split_by_group.items() if len(splits) != 1}
    if leaking:
        raise ValueError(f"Group leakage across splits: {leaking}")
    return cases, snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--manual", type=Path, default=Path(__file__).with_name("manual_cases.json"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("queries.csv"))
    parser.add_argument("--snapshot", type=Path, default=Path(__file__).with_name("menu_snapshot.json"))
    args = parser.parse_args()

    cases, snapshot = build_cases(args.seed, args.manual)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "group_id", "split", "slice", "question", "expected_ids", "expected_flags"],
        )
        writer.writeheader()
        writer.writerows(cases)
    write_snapshot(snapshot, args.snapshot)
    summary = {
        "cases": len(cases),
        "dev": sum(case["split"] == "dev" for case in cases),
        "test": sum(case["split"] == "test" for case in cases),
        "menu_items": len(snapshot.items),
    }
    print(json.dumps(summary, ensure_ascii=False))


def _group_split(group_id: str) -> str:
    bucket = int(hashlib.sha256(group_id.encode("utf-8")).hexdigest()[:8], 16) % 5
    return "dev" if bucket == 0 else "test"


if __name__ == "__main__":
    main()
