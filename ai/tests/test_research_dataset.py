from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from evaluation.research_corpus import load_research_corpus, resolve_selectors
from evaluation.research_dataset import (
    DatasetSplit,
    DatasetValidationError,
    QueryFamily,
    RelevanceLabels,
    ResearchDataset,
    RetrievalTarget,
    assert_materialized_cases_match,
    assert_research_ready,
    audit_dataset,
    build_dataset_manifest,
    expand_families,
    load_materialized_cases,
    load_research_dataset,
)
from evaluation.run_research_baseline import FROZEN_TEST_SHA256


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    PROJECT_ROOT / "ai" / "evaluation" / "datasets" / "query_families.dev.v1.json"
)
CASES_PATH = (
    PROJECT_ROOT / "ai" / "evaluation" / "datasets" / "retrieval_cases.dev.v1.jsonl"
)


class ResearchDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents = load_research_corpus()
        cls.dataset = load_research_dataset(DATASET_PATH)
        cls.materialized_cases = load_materialized_cases(CASES_PATH)

    def test_v38_dev_dataset_has_125_cases(self) -> None:
        resolver = lambda selectors: resolve_selectors(selectors, self.documents)
        audit = audit_dataset(self.dataset, resolver)

        self.assertEqual([], list(audit.issues))
        self.assertEqual(25, audit.family_count)
        self.assertEqual(125, audit.case_count)
        self.assertEqual({"dev": 125}, audit.split_counts)
        assert_research_ready(
            self.dataset,
            audit,
            min_cases=125,
            required_intents={
                "availability",
                "budget",
                "combo",
                "menu_category",
                "menu_tag",
                "out_of_catalog",
                "party_size",
                "safety",
                "restaurant_policy",
            },
            required_splits=(DatasetSplit.DEV,),
        )

    def test_v38_jsonl_materialization_matches_family_source(self) -> None:
        assert_materialized_cases_match(self.dataset, self.materialized_cases)
        self.assertEqual(125, len(self.materialized_cases))

    def test_v38_frozen_test_artifacts_match_hashes_without_loading_labels(self) -> None:
        for path, expected_sha256 in FROZEN_TEST_SHA256.items():
            self.assertEqual(
                expected_sha256,
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )

    def test_v38_materialized_case_requires_reviewer_evidence(self) -> None:
        payload = json.loads(CASES_PATH.read_text(encoding="utf-8").splitlines()[0])
        payload.pop("reviewer_evidence")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.jsonl"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            with self.assertRaisesRegex(DatasetValidationError, "reviewer_evidence"):
                load_materialized_cases(path)

    def test_v38_corpus_uses_all_91_official_menu_items_including_drinks(self) -> None:
        menu_documents = [item for item in self.documents if item.target == "menu"]
        self.assertEqual(91, len(menu_documents))
        self.assertEqual(
            7,
            len(resolve_selectors(["menu-category:Hải sản"], self.documents)),
        )
        alcohol_documents = resolve_selectors(
            ["menu-category:Bia & Rượu"],
            self.documents,
        )
        self.assertEqual(7, len(alcohol_documents))
        self.assertEqual(
            {f"menu:m_{index:03d}" for index in range(85, 92)},
            alcohol_documents,
        )

    def test_v38_alcohol_canonical_fields_match_production_seed(self) -> None:
        seed_path = (
            PROJECT_ROOT
            / "backend"
            / "src"
            / "RestaurantQrAiOrdering.Api"
            / "Data"
            / "RestaurantMenuSeed.cs"
        )
        pattern = re.compile(
            r'Item\((8[5-9]|9[01]), "cat_alcohol", "([^"]+)", (\d+), '
            r'"([^"]+)"'
        )
        canonical = {
            f"m_{int(index):03d}": {
                "name": name,
                "price": int(price),
                "description": description,
            }
            for index, name, price, description in pattern.findall(
                seed_path.read_text(encoding="utf-8")
            )
        }
        menu_path = PROJECT_ROOT / "backend" / "data" / "menu-dataset.json"
        menu = json.loads(menu_path.read_text(encoding="utf-8-sig"))
        actual = {
            item["id"]: {
                "name": item["name"],
                "price": item["price"],
                "description": item["description"],
            }
            for item in menu["items"]
            if item["categoryId"] == "cat_alcohol"
        }

        self.assertEqual(canonical, actual)

    def test_v38_manifest_is_stable_for_the_same_source(self) -> None:
        first = build_dataset_manifest(self.dataset, DATASET_PATH, CASES_PATH)
        second = build_dataset_manifest(self.dataset, DATASET_PATH, CASES_PATH)
        self.assertEqual(first, second)

    def test_v38_duplicate_query_across_splits_is_rejected(self) -> None:
        dataset = ResearchDataset(
            version="test",
            description="test",
            annotation_origin="test",
            review_status="engineering-reviewed",
            reviewer_evidence="unit-test",
            families=(
                QueryFamily(
                    family_id="family-dev",
                    split=DatasetSplit.DEV,
                    target=RetrievalTarget.MENU,
                    intent="menu_tag",
                    queries=("Món cay",),
                    labels=RelevanceLabels(
                        expected_selectors=("menu-tag:cay nhe",)
                    ),
                ),
                QueryFamily(
                    family_id="family-test",
                    split=DatasetSplit.TEST,
                    target=RetrievalTarget.MENU,
                    intent="menu_tag",
                    queries=("mon cay",),
                    labels=RelevanceLabels(
                        expected_selectors=("menu-tag:cay nhe",)
                    ),
                ),
            ),
        )
        audit = audit_dataset(dataset)
        self.assertTrue(any("Duplicate normalized query" in issue for issue in audit.issues))

    def test_v38_family_can_override_annotation_provenance(self) -> None:
        dataset = ResearchDataset(
            version="test",
            description="test",
            annotation_origin="synthetic",
            review_status="engineering-reviewed",
            reviewer_evidence="dataset-default",
            families=(
                QueryFamily(
                    family_id="human-family",
                    split=DatasetSplit.DEV,
                    target=RetrievalTarget.MENU,
                    intent="menu_tag",
                    queries=("Món rau",),
                    labels=RelevanceLabels(expected_selectors=("menu-tag:rau",)),
                    annotation_origin="human-authored",
                    review_status="restaurant-reviewed",
                    reviewer_evidence="restaurant-review-2026-07-13",
                ),
            ),
        )

        case = expand_families(dataset)[0]

        self.assertEqual("human-authored", case.annotation_origin)
        self.assertEqual("restaurant-reviewed", case.review_status)
        self.assertEqual("restaurant-review-2026-07-13", case.reviewer_evidence)

    def test_v38_unknown_selector_kind_is_rejected(self) -> None:
        with self.assertRaises(DatasetValidationError):
            resolve_selectors(["unknown:value"], self.documents)

    def test_v38_case_ids_are_stable(self) -> None:
        cases = expand_families(self.dataset)
        self.assertEqual("category-khai-vi-01", cases[0].case_id)
        self.assertEqual(len(cases), len({case.case_id for case in cases}))


if __name__ == "__main__":
    unittest.main()
