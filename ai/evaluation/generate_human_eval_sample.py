"""Generate stratified human-eval sample CSV from golden dev cases."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = AI_ROOT / "evaluation" / "golden" / "cases.jsonl"
TEMPLATE = AI_ROOT / "evaluation" / "templates" / "human_eval_scores.csv"
DEFAULT_OUTPUT = AI_ROOT / "evaluation" / "templates" / "human_eval_sample_50.csv"

IMPORTANT_FAMILIES = (
    "allergy",
    "budget",
    "payment_faq",
    "ordering_policy",
    "recommend",
    "guardrail",
    "multi_turn",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    cases: list[dict] = []
    with GOLDEN_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            case = json.loads(line)
            if case.get("split") == "dev":
                cases.append(case)

    by_family: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        by_family[str(case.get("family") or "unknown")].append(case)

    picked: list[dict] = []
    per_family = max(2, args.limit // max(1, len(IMPORTANT_FAMILIES)))
    for family in IMPORTANT_FAMILIES:
        picked.extend(by_family.get(family, [])[:per_family])
    if len(picked) < args.limit:
        for family in sorted(by_family):
            if family in IMPORTANT_FAMILIES:
                continue
            for case in by_family[family]:
                if len(picked) >= args.limit:
                    break
                picked.append(case)
    picked = picked[: args.limit]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_id",
                "family",
                "query",
                "model",
                "score_groundedness",
                "score_safety",
                "score_brand_voice",
                "score_task_success",
                "score_fluency",
                "pass_overall",
                "reviewer",
                "notes",
            ]
        )
        for case in picked:
            writer.writerow(
                [
                    case.get("id"),
                    case.get("family"),
                    case.get("query"),
                    "cx/gpt-5.5",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
    print(f"Wrote {len(picked)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
