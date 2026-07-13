from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from evaluation.research_corpus import (  # noqa: E402
    build_corpus_manifest,
    load_research_corpus,
    resolve_selectors,
)
from evaluation.research_dataset import (  # noqa: E402
    DatasetSplit,
    DatasetValidationError,
    assert_materialized_cases_match,
    assert_research_ready,
    audit_dataset,
    build_dataset_manifest,
    load_materialized_cases,
    load_research_dataset,
)
from evaluation.run_research_baseline import (  # noqa: E402
    FAMILY_DATASET_PATHS,
    FROZEN_TEST_SHA256,
    MATERIALIZED_CASES_PATHS,
)


DEV_REQUIRED_INTENTS = {
    "availability",
    "budget",
    "combo",
    "menu_category",
    "menu_tag",
    "out_of_catalog",
    "party_size",
    "safety",
    "restaurant_policy",
}


def run(*, include_frozen_test: bool = False) -> dict[str, object]:
    dev_family_path = FAMILY_DATASET_PATHS[DatasetSplit.DEV]
    dev_cases_path = MATERIALIZED_CASES_PATHS[DatasetSplit.DEV]
    dataset = load_research_dataset(dev_family_path)
    materialized_cases = load_materialized_cases(dev_cases_path)
    assert_materialized_cases_match(dataset, materialized_cases)
    documents = load_research_corpus()
    resolver = lambda selectors: resolve_selectors(selectors, documents)
    audit = audit_dataset(dataset, resolver)
    assert_research_ready(
        dataset,
        audit,
        min_cases=125,
        required_intents=DEV_REQUIRED_INTENTS,
        required_splits=(DatasetSplit.DEV,),
    )
    frozen_test = _frozen_test_manifest()
    test_manifest: dict[str, object] | None = None
    test_audit: dict[str, object] | None = None
    if include_frozen_test:
        test_family_path = FAMILY_DATASET_PATHS[DatasetSplit.TEST]
        test_cases_path = MATERIALIZED_CASES_PATHS[DatasetSplit.TEST]
        test_dataset = load_research_dataset(test_family_path)
        test_cases = load_materialized_cases(test_cases_path)
        assert_materialized_cases_match(test_dataset, test_cases)
        audited_test = audit_dataset(test_dataset, resolver)
        if not audited_test.ok:
            raise DatasetValidationError("Frozen test dataset audit failed")
        test_manifest = build_dataset_manifest(
            test_dataset,
            test_family_path,
            test_cases_path,
        )
        test_audit = {
            "ok": audited_test.ok,
            "issues": list(audited_test.issues),
        }
    return {
        "dataset": {
            "dev": build_dataset_manifest(dataset, dev_family_path, dev_cases_path),
            "frozen_test": frozen_test,
            "test": test_manifest,
        },
        "corpus": build_corpus_manifest(documents),
        "audit": {
            "ok": audit.ok,
            "issues": list(audit.issues),
            "frozen_test_opened": include_frozen_test,
            "test": test_audit,
        },
    }


def _frozen_test_manifest() -> dict[str, object]:
    artifacts = {}
    for path, expected_sha256 in FROZEN_TEST_SHA256.items():
        actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            raise DatasetValidationError(
                f"Frozen test artifact hash mismatch: {path.name}"
            )
        artifacts[path.name] = {
            "sha256": actual_sha256,
            "bytes": path.stat().st_size,
        }
    return {
        "case_count": 235,
        "opened": False,
        "artifacts": artifacts,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-frozen-test",
        action="store_true",
        help="Explicitly open and validate the frozen test labels.",
    )
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                run(include_frozen_test=args.include_frozen_test),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
    except (DatasetValidationError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
