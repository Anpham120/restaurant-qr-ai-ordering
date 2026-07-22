"""Export failure taxonomy from golden LLM eval artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def export_error_analysis(artifact_paths: list[Path], output_csv: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    by_family: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "fail": 0})
    for path in artifact_paths:
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for case in payload.get("cases") or []:
            family = str(case.get("family") or "unknown")
            composite_pass = bool(case.get("composite_pass"))
            by_family[family]["total"] += 1
            if not composite_pass:
                by_family[family]["fail"] += 1
            rows.append(
                {
                    "artifact": path.name,
                    "case_id": str(case.get("case_id") or case.get("id") or ""),
                    "family": family,
                    "composite_pass": str(composite_pass),
                    "grounding_pass": str(case.get("grounding_pass")),
                    "llm_success": str(case.get("llm_success")),
                }
            )
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["artifact", "case_id", "family", "composite_pass", "grounding_pass", "llm_success"],
        )
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        family: {
            "total": stats["total"],
            "fail": stats["fail"],
            "fail_rate": stats["fail"] / stats["total"] if stats["total"] else 0,
        }
        for family, stats in sorted(by_family.items())
    }
    return {"rows": len(rows), "by_family": summary, "output_csv": str(output_csv)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifacts",
        nargs="*",
        type=Path,
        default=[
            RESULTS_DIR / "golden_llm_eval_cx_gpt55_v3_full_v3b.json",
            RESULTS_DIR / "golden_llm_eval_deepseek_v4_full.json",
        ],
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=RESULTS_DIR / "error_analysis_by_family.csv",
    )
    args = parser.parse_args()
    summary = export_error_analysis(args.artifacts, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
