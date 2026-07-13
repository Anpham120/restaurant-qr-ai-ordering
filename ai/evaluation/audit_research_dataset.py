from __future__ import annotations

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
    DatasetValidationError,
    assert_materialized_cases_match,
    assert_research_ready,
    audit_dataset,
    build_dataset_manifest,
    load_materialized_cases,
    load_research_dataset,
)


FAMILY_DATASET_PATH = AI_ROOT / "evaluation" / "datasets" / "query_families.v1.json"
MATERIALIZED_CASES_PATH = (
    AI_ROOT / "evaluation" / "datasets" / "retrieval_cases.v1.jsonl"
)
REQUIRED_INTENTS = {
    "adversarial",
    "availability",
    "budget",
    "combo",
    "follow_up",
    "menu_category",
    "menu_tag",
    "multi_intent",
    "out_of_catalog",
    "party_size",
    "rejection",
    "safety",
    "show_more",
    "restaurant_policy",
    "typo_no_accent",
}


def run() -> dict[str, object]:
    dataset = load_research_dataset(FAMILY_DATASET_PATH)
    materialized_cases = load_materialized_cases(MATERIALIZED_CASES_PATH)
    assert_materialized_cases_match(dataset, materialized_cases)
    documents = load_research_corpus()
    resolver = lambda selectors: resolve_selectors(selectors, documents)
    audit = audit_dataset(dataset, resolver)
    assert_research_ready(
        dataset,
        audit,
        min_cases=350,
        required_intents=REQUIRED_INTENTS,
    )
    return {
        "dataset": build_dataset_manifest(
            dataset,
            FAMILY_DATASET_PATH,
            MATERIALIZED_CASES_PATH,
        ),
        "corpus": build_corpus_manifest(documents),
        "audit": {
            "ok": audit.ok,
            "issues": list(audit.issues),
        },
    }


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
    except DatasetValidationError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
