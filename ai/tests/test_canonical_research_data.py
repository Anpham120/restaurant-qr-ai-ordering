"""Tests for the single, reproducible data bundle used by the research report.

The report may expose different *views* (retrieval, safety, multi-turn, ...),
but those views must always be filtered from one canonical case catalogue.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from evaluation.canonical_research_data import (
    canonical_pipeline_evaluation_dataset,
    load_canonical_research_bundle,
    validate_canonical_research_bundle,
)


AI_ROOT = Path(__file__).resolve().parents[1]


def test_canonical_bundle_is_complete_and_hash_bound() -> None:
    bundle = load_canonical_research_bundle(AI_ROOT)

    assert bundle.catalog_version == "canonical-research-v1"
    assert len(bundle.cases) >= 18
    assert bundle.knowledge_base_hash.startswith("sha256:")
    assert bundle.menu_fixture_hash.startswith("sha256:")
    assert bundle.dataset_hash.startswith("sha256:")
    assert validate_canonical_research_bundle(bundle) == []


def test_menu_fixture_hash_is_canonical_json_not_source_bytes() -> None:
    bundle = load_canonical_research_bundle(AI_ROOT)
    menu = json.loads(bundle.menu_path.read_text(encoding="utf-8-sig"))
    canonical_menu = json.dumps(
        menu,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert bundle.menu_fixture_hash == (
        f"sha256:{hashlib.sha256(canonical_menu).hexdigest()}"
    )


def test_all_evaluation_views_filter_the_same_case_catalogue() -> None:
    bundle = load_canonical_research_bundle(AI_ROOT)
    catalogue_ids = {case.case_id for case in bundle.cases}

    required_views = {
        "retrieval",
        "single_turn",
        "multi_turn",
        "safety",
        "availability",
    }
    assert required_views <= set(bundle.available_views)

    for view_name in required_views:
        view_ids = {case.case_id for case in bundle.view(view_name)}
        assert view_ids
        assert view_ids <= catalogue_ids


def test_production_regression_questions_and_context_cases_are_in_catalogue() -> None:
    bundle = load_canonical_research_bundle(AI_ROOT)
    messages = {case.message for case in bundle.cases}

    assert "Nhà hàng mình có những món phở gì nhỉ?" in messages
    assert "Gợi ý cho mình món phở tại nhà hàng đi" in messages
    assert "Mình có món nhậu không?" in messages

    ordinal = next(case for case in bundle.cases if case.case_id == "multi_ordinal_second_item")
    assert ordinal.history
    assert ordinal.expected_menu_item_ids == ("m_009",)


def test_pipeline_runner_receives_cases_adapted_only_from_the_catalogue() -> None:
    bundle = load_canonical_research_bundle(AI_ROOT)
    dataset = canonical_pipeline_evaluation_dataset(bundle)

    assert dataset["catalog_version"] == bundle.catalog_version
    assert dataset["dataset_hash"] == bundle.dataset_hash
    assert {case["source_case_id"] for case in dataset["cases"]} <= {
        case.case_id for case in bundle.cases
    }
    assert {"menu_pho_list", "menu_pho_recommend", "tag_nhau"} <= {
        case["source_case_id"] for case in dataset["cases"]
    }

    injection = next(
        case for case in dataset["cases"] if case["source_case_id"] == "prompt_injection"
    )
    assert injection["turns"][-1]["required_guardrail_flags"] == [
        "PROMPT_INJECTION_BLOCKED"
    ]
