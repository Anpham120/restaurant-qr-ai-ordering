from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.data import documents_from_menu, load_policy_documents
from app.domain import SearchResult
from app.retrieval import (
    BM25Config,
    BM25Retriever,
    DenseEmbeddingRetriever,
    FastEmbedEncoder,
    HybridRrfRetriever,
    TfidfRetriever,
)
from research.menu_seed import load_snapshot


RANDOM_SEED = 20260710
TOP_K = 10
PRODUCTION_SELECTION_TOLERANCE = 0.005


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    group_id: str
    split: str
    slice: str
    question: str
    expected_ids: tuple[str, ...]
    expected_flags: tuple[str, ...]


@dataclass
class CaseResult:
    case_id: str
    split: str
    slice: str
    question: str
    expected_ids: list[str]
    retrieved_ids: list[str]
    top_score: float
    threshold: float
    latency_ms: float
    hit_at_1: float | None
    hit_at_3: float | None
    hit_at_5: float | None
    recall_at_5: float | None
    reciprocal_rank_at_10: float | None
    ndcg_at_10: float | None
    answerability_correct: float


def load_cases(path: Path) -> list[EvaluationCase]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            EvaluationCase(
                id=row["id"],
                group_id=row["group_id"],
                split=row["split"],
                slice=row["slice"],
                question=row["question"],
                expected_ids=tuple(value for value in row["expected_ids"].split(";") if value),
                expected_flags=tuple(value for value in row["expected_flags"].split(";") if value),
            )
            for row in csv.DictReader(handle)
        ]


def evaluate_raw(retriever, cases: list[EvaluationCase], repeats: int) -> list[dict[str, Any]]:
    ordered_cases = list(cases)
    random.Random(RANDOM_SEED).shuffle(ordered_cases)
    rows: list[dict[str, Any]] = []
    for case in ordered_cases:
        retriever.search(case.question, TOP_K)
        latencies: list[float] = []
        results: list[SearchResult] = []
        for _ in range(max(1, repeats)):
            started = time.perf_counter()
            results = retriever.search(case.question, TOP_K)
            latencies.append((time.perf_counter() - started) * 1000.0)
        rows.append(
            {
                "case": case,
                "results": results,
                "top_score": results[0].score if results else 0.0,
                "latency_ms": statistics.median(latencies),
            }
        )
    return sorted(rows, key=lambda row: row["case"].id)


def tune_threshold(raw_rows: list[dict[str, Any]]) -> float:
    scores = sorted({float(row["top_score"]) for row in raw_rows})
    candidates = [0.0]
    candidates.extend((left + right) / 2.0 for left, right in zip(scores, scores[1:]))
    if scores:
        candidates.extend([scores[0], scores[-1] + 1e-9])

    best_threshold = 0.0
    best_score = -1.0
    for threshold in sorted(set(candidates)):
        positives = [row for row in raw_rows if row["case"].expected_ids]
        negatives = [row for row in raw_rows if not row["case"].expected_ids]
        true_positive_rate = (
            sum(row["top_score"] >= threshold for row in positives) / len(positives) if positives else 1.0
        )
        true_negative_rate = (
            sum(row["top_score"] < threshold for row in negatives) / len(negatives) if negatives else 1.0
        )
        balanced_accuracy = (true_positive_rate + true_negative_rate) / 2.0
        if balanced_accuracy > best_score or (
            math.isclose(balanced_accuracy, best_score) and threshold < best_threshold
        ):
            best_score = balanced_accuracy
            best_threshold = threshold
    return float(best_threshold)


def apply_threshold(raw_rows: list[dict[str, Any]], threshold: float) -> list[CaseResult]:
    rows: list[CaseResult] = []
    for raw in raw_rows:
        case: EvaluationCase = raw["case"]
        raw_results: list[SearchResult] = raw["results"]
        predicted_answerable = raw["top_score"] >= threshold
        # Ranking quality and answerability are different research questions.
        # Positive qrels are always ranked from the raw top-k list; the tuned
        # threshold is scored separately as an abstention/classification metric.
        results = raw_results if case.expected_ids or predicted_answerable else []
        retrieved = [result.document.id for result in results]
        expected = set(case.expected_ids)
        if expected:
            first_rank = next((rank for rank, document_id in enumerate(retrieved, start=1) if document_id in expected), None)
            relevance = [1 if document_id in expected else 0 for document_id in retrieved[:TOP_K]]
            ideal = [1] * min(len(expected), TOP_K)
            rows.append(
                CaseResult(
                    case_id=case.id,
                    split=case.split,
                    slice=case.slice,
                    question=case.question,
                    expected_ids=list(case.expected_ids),
                    retrieved_ids=retrieved,
                    top_score=float(raw["top_score"]),
                    threshold=threshold,
                    latency_ms=float(raw["latency_ms"]),
                    hit_at_1=float(first_rank == 1),
                    hit_at_3=float(first_rank is not None and first_rank <= 3),
                    hit_at_5=float(first_rank is not None and first_rank <= 5),
                    recall_at_5=len(expected.intersection(retrieved[:5])) / len(expected),
                    reciprocal_rank_at_10=1.0 / first_rank if first_rank is not None and first_rank <= 10 else 0.0,
                    ndcg_at_10=_dcg(relevance) / max(_dcg(ideal), 1.0),
                    answerability_correct=float(predicted_answerable),
                )
            )
        else:
            rows.append(
                CaseResult(
                    case_id=case.id,
                    split=case.split,
                    slice=case.slice,
                    question=case.question,
                    expected_ids=[],
                    retrieved_ids=retrieved,
                    top_score=float(raw["top_score"]),
                    threshold=threshold,
                    latency_ms=float(raw["latency_ms"]),
                    hit_at_1=None,
                    hit_at_3=None,
                    hit_at_5=None,
                    recall_at_5=None,
                    reciprocal_rank_at_10=None,
                    ndcg_at_10=None,
                    answerability_correct=float(not predicted_answerable),
                )
            )
    return rows


def summarize(rows: list[CaseResult]) -> dict[str, Any]:
    positive = [row for row in rows if row.expected_ids]
    by_slice: dict[str, dict[str, float]] = {}
    for slice_name in sorted({row.slice for row in rows}):
        slice_rows = [row for row in rows if row.slice == slice_name]
        slice_positive = [row for row in slice_rows if row.expected_ids]
        by_slice[slice_name] = {
            "cases": len(slice_rows),
            "hit_at_5": _mean(row.hit_at_5 for row in slice_positive),
            "ndcg_at_10": _mean(row.ndcg_at_10 for row in slice_positive),
            "answerability_accuracy": _mean(row.answerability_correct for row in slice_rows),
        }
    positive_slice_scores = [metrics["ndcg_at_10"] for metrics in by_slice.values() if metrics["ndcg_at_10"] >= 0]
    latencies = sorted(row.latency_ms for row in rows)
    return {
        "cases": len(rows),
        "positive_cases": len(positive),
        "hit_at_1": _mean(row.hit_at_1 for row in positive),
        "hit_at_3": _mean(row.hit_at_3 for row in positive),
        "hit_at_5": _mean(row.hit_at_5 for row in positive),
        "recall_at_5": _mean(row.recall_at_5 for row in positive),
        "mrr_at_10": _mean(row.reciprocal_rank_at_10 for row in positive),
        "ndcg_at_10": _mean(row.ndcg_at_10 for row in positive),
        "macro_slice_ndcg_at_10": statistics.mean(positive_slice_scores) if positive_slice_scores else 0.0,
        "answerability_accuracy": _mean(row.answerability_correct for row in rows),
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "by_slice": by_slice,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parent
    parser.add_argument("--queries", type=Path, default=root / "queries.csv")
    parser.add_argument("--snapshot", type=Path, default=root / "menu_snapshot.json")
    parser.add_argument("--policies", type=Path, default=root.parent / "data" / "policies.json")
    parser.add_argument("--artifacts", type=Path, default=root / "artifacts")
    parser.add_argument("--embedding-model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    parser.add_argument("--embedding-model-path", type=Path)
    parser.add_argument("--embedding-cache", type=Path, default=Path(".cache/fastembed"))
    parser.add_argument("--latency-repeats", type=int, default=3)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args()

    cases = load_cases(args.queries)
    dev_cases = [case for case in cases if case.split == "dev"]
    test_cases = [case for case in cases if case.split == "test"]
    snapshot = load_snapshot(args.snapshot)
    documents = documents_from_menu(snapshot.items) + load_policy_documents(args.policies)
    args.artifacts.mkdir(parents=True, exist_ok=True)

    build_started = time.perf_counter()
    encoder = FastEmbedEncoder(
        model_name=args.embedding_model,
        cache_dir=args.embedding_cache,
        specific_model_path=args.embedding_model_path,
    )
    encoder_load_ms = (time.perf_counter() - build_started) * 1000.0

    dense_started = time.perf_counter()
    dense = DenseEmbeddingRetriever(documents, encoder)
    dense_build_ms = (time.perf_counter() - dense_started) * 1000.0
    tfidf_started = time.perf_counter()
    tfidf = TfidfRetriever(documents)
    tfidf_build_ms = (time.perf_counter() - tfidf_started) * 1000.0

    bm25_candidates = [
        BM25Config(k1=1.2, b=0.65, title_boost=1.0),
        BM25Config(k1=1.5, b=0.75, title_boost=1.2),
        BM25Config(k1=1.8, b=0.80, title_boost=1.5),
    ]
    bm25_dev_runs: list[tuple[BM25Config, BM25Retriever, float, list[CaseResult], dict[str, Any]]] = []
    for config in bm25_candidates:
        retriever = BM25Retriever(documents, config)
        raw = evaluate_raw(retriever, dev_cases, args.latency_repeats)
        threshold = tune_threshold(raw)
        rows = apply_threshold(raw, threshold)
        bm25_dev_runs.append((config, retriever, threshold, rows, summarize(rows)))
    best_bm25 = max(bm25_dev_runs, key=lambda value: value[4]["macro_slice_ndcg_at_10"])

    method_specs = {
        "tfidf": {"retriever": tfidf, "config": {}, "index_build_ms": tfidf_build_ms},
        "bm25": {
            "retriever": best_bm25[1],
            "config": asdict(best_bm25[0]),
            "index_build_ms": 0.0,
            "precomputed_dev": (best_bm25[2], best_bm25[3]),
        },
        "embedding": {
            "retriever": dense,
            "config": {"model": args.embedding_model},
            "index_build_ms": dense_build_ms,
        },
    }

    hybrid_candidates = [
        HybridRrfRetriever(
            best_bm25[1],
            dense,
            rrf_k=rrf_k,
            lexical_weight=lexical_weight,
            dense_weight=1.0,
        )
        for rrf_k in (20, 60)
        for lexical_weight in (1.0, 2.0, 4.0)
    ]
    hybrid_runs = []
    for retriever in hybrid_candidates:
        raw = evaluate_raw(retriever, dev_cases, args.latency_repeats)
        threshold = tune_threshold(raw)
        rows = apply_threshold(raw, threshold)
        hybrid_runs.append((retriever, threshold, rows, summarize(rows)))
    best_hybrid = max(hybrid_runs, key=lambda value: value[3]["macro_slice_ndcg_at_10"])
    method_specs["hybrid_rrf"] = {
        "retriever": best_hybrid[0],
        "config": {
            "rrf_k": best_hybrid[0].rrf_k,
            "lexical_weight": best_hybrid[0].lexical_weight,
            "dense_weight": best_hybrid[0].dense_weight,
            "bm25": asdict(best_bm25[0]),
            "model": args.embedding_model,
        },
        "index_build_ms": dense_build_ms,
        "precomputed_dev": (best_hybrid[1], best_hybrid[2]),
    }

    tfidf_hybrid_candidates = [
        HybridRrfRetriever(
            tfidf,
            dense,
            rrf_k=rrf_k,
            lexical_weight=lexical_weight,
            dense_weight=1.0,
        )
        for rrf_k in (20, 60)
        for lexical_weight in (1.0, 2.0, 4.0)
    ]
    tfidf_hybrid_runs = []
    for retriever in tfidf_hybrid_candidates:
        raw = evaluate_raw(retriever, dev_cases, args.latency_repeats)
        threshold = tune_threshold(raw)
        rows = apply_threshold(raw, threshold)
        tfidf_hybrid_runs.append((retriever, threshold, rows, summarize(rows)))
    best_tfidf_hybrid = max(tfidf_hybrid_runs, key=lambda value: value[3]["macro_slice_ndcg_at_10"])
    method_specs["hybrid_tfidf_embedding"] = {
        "retriever": best_tfidf_hybrid[0],
        "config": {
            "rrf_k": best_tfidf_hybrid[0].rrf_k,
            "lexical_weight": best_tfidf_hybrid[0].lexical_weight,
            "dense_weight": best_tfidf_hybrid[0].dense_weight,
            "model": args.embedding_model,
        },
        "index_build_ms": dense_build_ms + tfidf_build_ms,
        "precomputed_dev": (best_tfidf_hybrid[1], best_tfidf_hybrid[2]),
    }

    summaries: dict[str, Any] = {}
    all_test_rows: dict[str, list[CaseResult]] = {}
    selected_configs: dict[str, Any] = {}
    for method, spec in method_specs.items():
        if "precomputed_dev" in spec:
            threshold, dev_rows = spec["precomputed_dev"]
        else:
            dev_raw = evaluate_raw(spec["retriever"], dev_cases, args.latency_repeats)
            threshold = tune_threshold(dev_raw)
            dev_rows = apply_threshold(dev_raw, threshold)
        test_raw = evaluate_raw(spec["retriever"], test_cases, args.latency_repeats)
        test_rows = apply_threshold(test_raw, threshold)
        dev_summary = summarize(dev_rows)
        test_summary = summarize(test_rows)
        summaries[method] = {
            "config": spec["config"],
            "threshold": threshold,
            "index_build_ms": spec["index_build_ms"],
            "dev": dev_summary,
            "test": test_summary,
        }
        selected_configs[method] = spec["config"]
        all_test_rows[method] = test_rows

    winner = _select_winner(summaries)
    statistics_payload = _statistical_comparisons(
        all_test_rows,
        winner,
        bootstrap_samples=args.bootstrap_samples,
    )
    production_config = {
        "method": winner,
        "selection_rule": (
            "Highest development macro slice nDCG@10; methods within 0.005 use the lower P95 query latency. "
            "The frozen test set is used only for post-selection evaluation."
        ),
        "config": selected_configs[winner],
        "threshold": summaries[winner]["threshold"],
        "embedding_model": args.embedding_model if winner in {"embedding", "hybrid_rrf", "hybrid_tfidf_embedding"} else None,
        "embedding_model_sha256": FastEmbedEncoder.model_checksum(args.embedding_model_path),
    }
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "random_seed": RANDOM_SEED,
        "menu_snapshot_sha256": _sha256(args.snapshot),
        "queries_sha256": _sha256(args.queries),
        "policy_sha256": _sha256(args.policies),
        "embedding_model": args.embedding_model,
        "embedding_model_sha256": production_config["embedding_model_sha256"],
        "encoder_load_ms": encoder_load_ms,
        "case_counts": {"dev": len(dev_cases), "test": len(test_cases)},
        "document_count": len(documents),
        "latency_repeats": args.latency_repeats,
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "scikit-learn", "fastembed", "onnxruntime")
        },
        "evaluation_script_sha256": _sha256(Path(__file__)),
    }

    _write_json(
        args.artifacts / "summary.json",
        {"winner": winner, "selection_split": "dev", "methods": summaries},
    )
    _write_json(args.artifacts / "production_config.json", production_config)
    _write_json(args.artifacts / "statistical_tests.json", statistics_payload)
    _write_json(args.artifacts / "environment.json", environment)
    _write_rows(args.artifacts / "per_query_results.csv", all_test_rows)
    print(
        json.dumps(
            {"winner": winner, "selection_split": "dev", "test": summaries[winner]["test"]},
            ensure_ascii=False,
            indent=2,
        )
    )


def _select_winner(summaries: dict[str, Any]) -> str:
    best_quality = max(value["dev"]["macro_slice_ndcg_at_10"] for value in summaries.values())
    finalists = [
        method
        for method, value in summaries.items()
        if best_quality - value["dev"]["macro_slice_ndcg_at_10"] <= PRODUCTION_SELECTION_TOLERANCE
    ]
    return min(finalists, key=lambda method: summaries[method]["dev"]["latency_p95_ms"])


def _statistical_comparisons(
    rows_by_method: dict[str, list[CaseResult]], winner: str, bootstrap_samples: int
) -> dict[str, Any]:
    winner_by_id = {row.case_id: row for row in rows_by_method[winner] if row.expected_ids}
    output: dict[str, Any] = {}
    for method, rows in rows_by_method.items():
        method_by_id = {row.case_id: row for row in rows if row.expected_ids}
        ids = sorted(set(winner_by_id).intersection(method_by_id))
        deltas = [
            float(winner_by_id[case_id].ndcg_at_10 or 0) - float(method_by_id[case_id].ndcg_at_10 or 0)
            for case_id in ids
        ]
        winner_only = sum(
            (winner_by_id[case_id].hit_at_5 or 0) > (method_by_id[case_id].hit_at_5 or 0) for case_id in ids
        )
        method_only = sum(
            (method_by_id[case_id].hit_at_5 or 0) > (winner_by_id[case_id].hit_at_5 or 0) for case_id in ids
        )
        output[method] = {
            "paired_ndcg_delta_winner_minus_method": statistics.mean(deltas) if deltas else 0.0,
            "paired_bootstrap_95_ci": _bootstrap_ci(deltas, bootstrap_samples),
            "mcnemar": {
                "winner_only_correct": winner_only,
                "method_only_correct": method_only,
                "exact_two_sided_p": _mcnemar_exact(winner_only, method_only),
            },
        }
    return output


def _bootstrap_ci(values: list[float], samples: int) -> list[float]:
    if not values:
        return [0.0, 0.0]
    rng = np.random.default_rng(RANDOM_SEED)
    array = np.asarray(values, dtype=np.float64)
    means = np.asarray([rng.choice(array, size=len(array), replace=True).mean() for _ in range(samples)])
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def _mcnemar_exact(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(0, min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2**discordant))


def _dcg(relevance: list[int]) -> float:
    return sum(value / math.log2(rank + 1) for rank, value in enumerate(relevance, start=1))


def _mean(values) -> float:
    filtered = [float(value) for value in values if value is not None]
    return statistics.mean(filtered) if filtered else -1.0


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    index = min(len(values) - 1, max(0, math.ceil(quantile * len(values)) - 1))
    return float(values[index])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_rows(path: Path, rows_by_method: dict[str, list[CaseResult]]) -> None:
    fieldnames = ["method", *CaseResult.__dataclass_fields__.keys()]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for method, rows in rows_by_method.items():
            for row in rows:
                payload = asdict(row)
                payload["method"] = method
                payload["expected_ids"] = ";".join(payload["expected_ids"])
                payload["retrieved_ids"] = ";".join(payload["retrieved_ids"])
                writer.writerow(payload)


if __name__ == "__main__":
    main()
