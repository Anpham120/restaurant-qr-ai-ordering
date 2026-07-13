from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.research_dataset import (  # noqa: E402
    DatasetSplit,
    ResearchCase,
    expand_families,
    load_research_dataset,
)


DATASET_ROOT = AI_ROOT / "evaluation" / "datasets"
LEGACY_FAMILY_PATH = DATASET_ROOT / "query_families.v1.json"
SPLIT_FAMILY_PATHS = {
    DatasetSplit.DEV: DATASET_ROOT / "query_families.dev.v1.json",
    DatasetSplit.TEST: DATASET_ROOT / "query_families.test.v1.json",
}
SPLIT_CASE_PATHS = {
    DatasetSplit.DEV: DATASET_ROOT / "retrieval_cases.dev.v1.jsonl",
    DatasetSplit.TEST: DATASET_ROOT / "retrieval_cases.test.v1.jsonl",
}


def migrate_legacy_family_file() -> None:
    payload = json.loads(LEGACY_FAMILY_PATH.read_text(encoding="utf-8-sig"))
    families = payload.get("families")
    if not isinstance(families, list):
        raise ValueError("Legacy dataset must contain a families array")

    for split, path in SPLIT_FAMILY_PATHS.items():
        split_payload = {
            **payload,
            "description": f"{payload['description']} Split: {split.value}.",
            "families": [family for family in families if family.get("split") == split],
        }
        path.write_text(
            json.dumps(split_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def materialize_split(split: DatasetSplit) -> int:
    dataset = load_research_dataset(SPLIT_FAMILY_PATHS[split])
    if any(family.split is not split for family in dataset.families):
        raise ValueError(f"{split.value} family file contains a different split")

    cases = expand_families(dataset)
    SPLIT_CASE_PATHS[split].write_text(
        "\n".join(
            json.dumps(_case_payload(case), ensure_ascii=False) for case in cases
        )
        + "\n",
        encoding="utf-8",
    )
    return len(cases)


def _case_payload(case: ResearchCase) -> dict[str, object]:
    return {
        "case_id": case.case_id,
        "family_id": case.family_id,
        "split": case.split.value,
        "target": case.target.value,
        "intent": case.intent,
        "query": case.query,
        "expected_selectors": list(case.labels.expected_selectors),
        "forbidden_selectors": list(case.labels.forbidden_selectors),
        "guardrail_flags": list(case.labels.guardrail_flags),
        "annotation_origin": case.annotation_origin,
        "review_status": case.review_status,
        "rationale": case.rationale,
        "reviewer_evidence": case.reviewer_evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--migrate-legacy",
        action="store_true",
        help="Split the legacy combined family file before materializing cases.",
    )
    parser.add_argument(
        "--include-frozen-test",
        action="store_true",
        help="Explicitly rematerialize the frozen test split.",
    )
    args = parser.parse_args()

    if args.migrate_legacy:
        migrate_legacy_family_file()

    splits = [DatasetSplit.DEV]
    if args.include_frozen_test or args.migrate_legacy:
        splits.append(DatasetSplit.TEST)
    counts = {split.value: materialize_split(split) for split in splits}
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
