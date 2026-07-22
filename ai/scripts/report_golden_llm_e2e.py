"""Summarize golden LLM eval artifact by family."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path


AI_ROOT = Path(__file__).resolve().parents[1]
RESULTS = AI_ROOT / "evaluation" / "results" / "golden_llm_eval_cx_gpt55_v3_full_v3b.json"


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    if "cases" in data:
        _print_single(data)
        return
    for method, payload in data.get("comparison", {}).items():
        print(f"\n=== {method} ===")
        _print_single(payload)


def _print_single(payload: dict) -> None:
    print(json.dumps(payload.get("summary", {}), ensure_ascii=False, indent=2))
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in payload.get("cases", []):
        by_family[str(row.get("family") or "?")].append(row)

    print("\nPer-family composite pass:")
    for family, rows in sorted(by_family.items()):
        rate = sum(1 for row in rows if row.get("composite_pass")) / len(rows)
        faith = sum(row.get("faithfulness_score", 0) for row in rows) / len(rows)
        print(f"  {family:20s} n={len(rows):3d} composite={rate:.2f} faithfulness={faith:.3f}")


if __name__ == "__main__":
    main()
