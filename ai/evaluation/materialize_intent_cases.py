"""Materialize evaluation/intent_classification_cases.jsonl from the canonical catalog."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.intent_cases_catalog import build_intent_case_catalog, validate_cases

AI_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = AI_ROOT / "evaluation" / "intent_classification_cases.jsonl"


def materialize(output: Path = DEFAULT_OUT) -> int:
    cases = build_intent_case_catalog()
    issues = validate_cases(cases)
    if issues:
        raise SystemExit("Catalog validation failed:\n- " + "\n- ".join(issues))

    lines = [json.dumps(case, ensure_ascii=False) for case in cases]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    categories = sorted({case["category"] for case in cases})
    tiers = sorted({case["tier"] for case in cases})
    print(f"Wrote {len(cases)} cases -> {output}")
    print(f"Categories ({len(categories)}): {', '.join(categories)}")
    print(f"Tiers: {', '.join(tiers)}")
    return len(cases)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSONL path",
    )
    args = parser.parse_args()
    materialize(args.output)


if __name__ == "__main__":
    main()
