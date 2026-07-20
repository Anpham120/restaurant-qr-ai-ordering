"""Print per-family breakdown of the golden E2E chat eval results."""

from __future__ import annotations

import collections
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

AI_ROOT = Path(__file__).resolve().parents[1]
RESULTS = AI_ROOT / "evaluation" / "results" / "golden_chat_e2e.json"


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = data["cases"]
    chunk = collections.defaultdict(lambda: [0, 0])
    menu = collections.defaultdict(lambda: [0, 0])
    for row in rows:
        family = row["family"]
        if row["expected_chunk_hit"] is not None:
            chunk[family][1] += 1
            if row["expected_chunk_hit"]:
                chunk[family][0] += 1
        if row["expected_menu_hit"] is not None:
            menu[family][1] += 1
            if row["expected_menu_hit"]:
                menu[family][0] += 1

    print(f"{'family':22s} {'chunk_hit':>10s} {'menu_hit':>10s}")
    for family in sorted(set(chunk) | set(menu)):
        chunk_text = f"{chunk[family][0]}/{chunk[family][1]}" if family in chunk else "-"
        menu_text = f"{menu[family][0]}/{menu[family][1]}" if family in menu else "-"
        print(f"{family:22s} {chunk_text:>10s} {menu_text:>10s}")

    print()
    print("safety failures:", len(data["failures"]["safety"]))
    print("forbidden failures:", len(data["failures"]["forbidden"]))


if __name__ == "__main__":
    main()
