from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from app.rag.knowledge_base import KnowledgeChunk  # noqa: E402
from app.rag.retriever import (  # noqa: E402
    BM25_B,
    BM25_K1,
    TAG_BOOST,
    TITLE_BOOST,
    BM25Retriever,
    Retriever,
)
from app.rag.menu_query_filters import (  # noqa: E402
    filter_menu_retrieval_results,
    menu_document_to_item,
)
from evaluation.research_corpus import (  # noqa: E402
    KnowledgeDocumentMetadata,
    MenuDocumentMetadata,
    build_corpus_manifest,
    load_research_corpus,
    resolve_selectors,
)
from evaluation.research_dataset import (  # noqa: E402
    DatasetSplit,
    RetrievalTarget,
    assert_materialized_cases_match,
    build_dataset_manifest,
    canonical_text_artifact_sha256,
    load_materialized_cases,
    load_research_dataset,
)
from evaluation.retrieval_metrics import evaluate_rankings  # noqa: E402


DATASET_ROOT = AI_ROOT / "evaluation" / "datasets"
FAMILY_DATASET_PATHS = {
    DatasetSplit.DEV: DATASET_ROOT / "query_families.dev.v1.json",
    DatasetSplit.TEST: DATASET_ROOT / "query_families.test.v1.json",
}
MATERIALIZED_CASES_PATHS = {
    DatasetSplit.DEV: DATASET_ROOT / "retrieval_cases.dev.v1.jsonl",
    DatasetSplit.TEST: DATASET_ROOT / "retrieval_cases.test.v1.jsonl",
}
FROZEN_TEST_SHA256 = {
    FAMILY_DATASET_PATHS[DatasetSplit.TEST]: (
        "6fdcc59a311b21c3c44070e5fd7fce2f70a85c245978f085e19be0c4a5e1ee28"
    ),
    MATERIALIZED_CASES_PATHS[DatasetSplit.TEST]: (
        "98a08679a6883b5531571482d95879fd4b2f5ec21f9f37135889f2d2c2aaafb5"
    ),
}


RetrieverFactory = Callable[[list[KnowledgeChunk]], Retriever]
LATENCY_WARMUP_QUERIES_PER_TARGET = 5
LATENCY_REPETITIONS = 7
LATENCY_CASE_ORDER_SEED = 20260713
PROVENANCE_PACKAGES = (
    "sentence-transformers",
    "transformers",
    "torch",
    "tokenizers",
    "huggingface-hub",
    "numpy",
    "scipy",
    "scikit-learn",
)


def run_baseline(
    split: DatasetSplit = DatasetSplit.DEV,
    *,
    top_k: int = 10,
    allow_frozen_test: bool = False,
) -> dict[str, object]:
    return run_retrieval_experiment(
        method="bm25",
        retriever_factory=BM25Retriever,
        retriever_provenance={
            "name": "bm25",
            "implementation": "app.rag.retriever.BM25Retriever",
            "version": "repository",
            "parameters": {
                "k1": BM25_K1,
                "b": BM25_B,
                "title_boost": TITLE_BOOST,
                "tag_boost": TAG_BOOST,
            },
        },
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )


def run_retrieval_experiment(
    *,
    method: str,
    retriever_factory: RetrieverFactory,
    retriever_provenance: dict[str, object],
    split: DatasetSplit = DatasetSplit.DEV,
    top_k: int = 10,
    allow_frozen_test: bool = False,
) -> dict[str, object]:
    validate_experiment_request(
        method=method,
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )
    family_dataset_path, materialized_cases_path = _dataset_paths(split)

    dataset = load_research_dataset(family_dataset_path)
    cases = load_materialized_cases(materialized_cases_path)
    assert_materialized_cases_match(dataset, cases)
    documents = load_research_corpus()
    documents_by_target = {
        target: [document for document in documents if document.target is target]
        for target in RetrievalTarget
    }
    retrievers = {
        target: retriever_factory(
            [
                KnowledgeChunk(
                    source=document.document_id,
                    title=document.title,
                    content=document.text,
                    tags=_document_tags(document.metadata),
                )
                for document in target_documents
            ]
        )
        for target, target_documents in documents_by_target.items()
    }
    menu_items = [
        menu_document_to_item(document, document_id=document.document_id)
        for document in documents
        if document.target is RetrievalTarget.MENU
        and isinstance(document.metadata, MenuDocumentMetadata)
        and document.metadata.is_available
    ]

    evaluated_cases = [
        case
        for case in cases
        if case.split is split and case.labels.expected_selectors
    ]
    warmup_searches = 0
    for target, retriever in retrievers.items():
        warmup_cases = [case for case in evaluated_cases if case.target is target][
            :LATENCY_WARMUP_QUERIES_PER_TARGET
        ]
        for case in warmup_cases:
            retriever.search(case.query, top_k)
            warmup_searches += 1

    measurement_cases = list(evaluated_cases)
    random.Random(LATENCY_CASE_ORDER_SEED).shuffle(measurement_cases)
    rankings: dict[str, list[str]] = {}
    expected_by_case: dict[str, list[str]] = {}
    forbidden_by_case: dict[str, list[str]] = {}
    latencies_ms: list[float] = []
    case_records: dict[str, dict[str, object]] = {}
    for case in measurement_cases:
        expected_by_case[case.case_id] = sorted(
            resolve_selectors(case.labels.expected_selectors, documents)
        )
        forbidden_by_case[case.case_id] = sorted(
            resolve_selectors(case.labels.forbidden_selectors, documents)
        )
        latency_samples_ms = []
        results = []
        for repetition in range(LATENCY_REPETITIONS):
            started = time.perf_counter()
            current_results = retrievers[case.target].search(case.query, top_k)
            latency_samples_ms.append((time.perf_counter() - started) * 1000)
            if repetition == 0:
                results = current_results
                if case.target is RetrievalTarget.MENU:
                    results = filter_menu_retrieval_results(
                        case.query,
                        results,
                        menu_items,
                    )
        latency_ms = statistics.median(latency_samples_ms)
        latencies_ms.append(latency_ms)
        rankings[case.case_id] = [result.chunk.source for result in results]
        case_records[case.case_id] = {
            "case_id": case.case_id,
            "family_id": case.family_id,
            "target": case.target.value,
            "intent": case.intent,
            "query": case.query,
            "expected_document_ids": expected_by_case[case.case_id],
            "forbidden_document_ids": forbidden_by_case[case.case_id],
            "ranking": [
                {
                    "document_id": result.chunk.source,
                    "score": result.score,
                }
                for result in results
            ],
            "latency_ms": latency_ms,
            "latency_samples_ms": latency_samples_ms,
        }

    k_values = tuple(value for value in (1, 3, 5, 10) if value <= top_k)
    summary, per_query = evaluate_rankings(
        rankings,
        expected_by_case,
        forbidden_by_case,
        k_values=k_values,
    )
    metrics_by_case = {item.case_id: item for item in per_query}
    paired_observations = []
    for case_id in sorted(case_records):
        record = case_records[case_id]
        record["metrics"] = asdict(metrics_by_case[case_id])
        paired_observations.append(record)
    return {
        "method": method,
        "split": split.value,
        "top_k": top_k,
        "provenance": _runtime_provenance(retriever_provenance),
        "dataset": build_dataset_manifest(
            dataset,
            family_dataset_path,
            materialized_cases_path,
        ),
        "frozen_test_opened": split is DatasetSplit.TEST,
        "corpus": build_corpus_manifest(documents),
        "metrics": asdict(summary),
        "latency_ms": {
            "p50": statistics.median(latencies_ms) if latencies_ms else 0.0,
            "p95": _percentile(latencies_ms, 0.95),
            "samples": len(latencies_ms),
            "protocol": {
                "warmup_queries_per_target": LATENCY_WARMUP_QUERIES_PER_TARGET,
                "warmup_searches": warmup_searches,
                "repetitions_per_query": LATENCY_REPETITIONS,
                "per_query_aggregate": "median",
                "case_order": "deterministic-shuffle",
                "case_order_seed": LATENCY_CASE_ORDER_SEED,
            },
        },
        "per_query_count": len(per_query),
        "cases": paired_observations,
    }


def validate_experiment_request(
    *,
    method: str,
    split: DatasetSplit,
    top_k: int,
    allow_frozen_test: bool,
) -> None:
    if not method.strip():
        raise ValueError("method must be a non-empty string")
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    if split is DatasetSplit.TEST and not allow_frozen_test:
        raise PermissionError(
            "Refusing to open frozen test split without explicit authorization."
        )


def _dataset_paths(split: DatasetSplit) -> tuple[Path, Path]:
    family_path = FAMILY_DATASET_PATHS[split]
    cases_path = MATERIALIZED_CASES_PATHS[split]
    if split is DatasetSplit.TEST:
        for path in (family_path, cases_path):
            actual = canonical_text_artifact_sha256(path)
            if actual != FROZEN_TEST_SHA256[path]:
                raise RuntimeError(f"Frozen test artifact hash mismatch: {path.name}")
    return family_path, cases_path


def _document_tags(
    metadata: MenuDocumentMetadata | KnowledgeDocumentMetadata,
) -> tuple[str, ...]:
    return metadata.tags


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if not 0 <= percentile <= 1:
        raise ValueError("percentile must be between 0 and 1")
    ordered = sorted(values)
    index = min(
        len(ordered) - 1,
        max(0, math.ceil(percentile * len(ordered)) - 1),
    )
    return ordered[index]


def _runtime_provenance(retriever_provenance: dict[str, object]) -> dict[str, object]:
    git_state = _git_state()
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **git_state,
        "evaluation_seed": 20260713,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "package_versions": _package_versions(),
        "retriever": dict(retriever_provenance),
    }


def _package_versions() -> dict[str, str]:
    versions = {}
    for package in PROVENANCE_PACKAGES:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def _git_state() -> dict[str, object]:
    configured = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
    try:
        git_sha = configured or _run_git("rev-parse", "HEAD").strip()
        status = _run_git_bytes(
            "status", "--porcelain=v1", "-z", "--untracked-files=all"
        )
        tracked_diff = _run_git_bytes("diff", "--binary", "HEAD")
        untracked_paths = sorted(
            path
            for path in _run_git_bytes(
                "ls-files", "-z", "--others", "--exclude-standard"
            ).split(b"\0")
            if path
        )
        records = [b"tracked-diff", tracked_diff]
        for raw_relative_path in untracked_paths:
            relative_path = os.fsdecode(raw_relative_path)
            records.extend(
                [
                    b"untracked-path",
                    raw_relative_path,
                    b"untracked-content",
                    (PROJECT_ROOT / relative_path).read_bytes(),
                ]
            )
        return {
            "git_sha": git_sha,
            "git_dirty": bool(status),
            "git_diff_sha256": _hash_framed_records(records),
        }
    except (OSError, subprocess.CalledProcessError):
        return {
            "git_sha": configured or "unknown",
            "git_dirty": None,
            "git_diff_sha256": "unknown",
        }


def _run_git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _run_git_bytes(*arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
    ).stdout


def _hash_framed_records(records: Sequence[bytes]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(len(record).to_bytes(8, byteorder="big", signed=False))
        digest.update(record)
    return digest.hexdigest()


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reproducible BM25 baseline.")
    parser.add_argument("--split", choices=[item.value for item in DatasetSplit], default="dev")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--allow-frozen-test",
        action="store_true",
        help="Required before opening the frozen test split.",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parse_args(arguments)
    selected_split = DatasetSplit(args.split)
    try:
        result = run_baseline(
            selected_split,
            top_k=args.top_k,
            allow_frozen_test=args.allow_frozen_test,
        )
    except PermissionError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
