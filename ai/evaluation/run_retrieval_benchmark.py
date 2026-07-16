"""Run Phase 3 retrieval benchmark against golden cases."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

AI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ROOT))

from app.rag.knowledge_base import KnowledgeChunk, load_markdown_knowledge_base  # noqa: E402
from evaluation.metrics import aggregate_metrics, bootstrap_ci, score_ranking  # noqa: E402


EVAL_ROOT = AI_ROOT / "evaluation"
GOLDEN_PATH = EVAL_ROOT / "golden" / "cases.jsonl"
RESULTS_DIR = EVAL_ROOT / "results"
KB_PATH = AI_ROOT / "knowledge-base"
DEFAULT_TOP_K = 10
DEFAULT_K_VALUES = (1, 3, 5, 10)


def load_cases(path: Path, *, split: str | None = None) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            if split is None or case.get("split") == split:
                cases.append(case)
    return cases


def chunk_key(chunk: KnowledgeChunk) -> str:
    return f"{chunk.source}::{chunk.title}"


def build_bm25_retriever(chunks: list[KnowledgeChunk]):
    from app.rag.retriever import BM25Retriever

    return BM25Retriever(chunks)


def try_build_hybrid_retriever(chunks: list[KnowledgeChunk]):
    try:
        from evaluation.retrieval_benchmark import HybridRrfRetriever

        return HybridRrfRetriever(chunks), "hybrid_rrf"
    except Exception:
        return None, None


def run_retriever(
    retriever: Any,
    cases: list[dict[str, Any]],
    *,
    top_k: int,
    k_values: tuple[int, ...],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    per_query_metrics: dict[str, dict[int, Any]] = {}
    per_case_rows: list[dict[str, Any]] = []
    latencies_ms: list[float] = []

    for case in cases:
        case_id = case["id"]
        query = case["query"]
        expected = [item for item in case.get("expected_chunk_ids", []) if item]
        if not expected:
            continue

        start = time.perf_counter()
        results = retriever.search(query, top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        latencies_ms.append(elapsed_ms)

        ranked_ids = [chunk_key(item.chunk) for item in results]
        metrics = score_ranking(ranked_ids, expected, k_values=k_values)
        per_query_metrics[case_id] = metrics
        per_case_rows.append(
            {
                "id": case_id,
                "family": case.get("family"),
                "split": case.get("split"),
                "query": query,
                "expected_chunk_ids": expected,
                "retrieved_chunk_ids": ranked_ids,
                "latency_ms": round(elapsed_ms, 4),
                "metrics": {
                    str(k): {
                        "hit": metrics[k].hit,
                        "mrr": metrics[k].mrr,
                        "ndcg": metrics[k].ndcg,
                    }
                    for k in k_values
                },
            }
        )

    summary_by_k = aggregate_metrics(per_query_metrics, k_values=k_values)
    bootstrap: dict[str, Any] = {}
    for k in k_values:
        if k not in summary_by_k:
            continue
        mrr_values = [row[k].mrr for row in per_query_metrics.values()]
        ndcg_values = [row[k].ndcg for row in per_query_metrics.values()]
        hit_values = [row[k].hit for row in per_query_metrics.values()]
        bootstrap[str(k)] = {
            "mrr": asdict(bootstrap_ci(mrr_values)),
            "ndcg": asdict(bootstrap_ci(ndcg_values)),
            "hit": asdict(bootstrap_ci(hit_values)),
        }

    summary = {
        "evaluated_cases": len(per_query_metrics),
        "skipped_cases_no_expected_chunks": len(cases) - len(per_query_metrics),
        "top_k": top_k,
        "k_values": list(k_values),
        "metrics": {
            str(k): {
                "hit": summary_by_k[k].hit,
                "mrr": summary_by_k[k].mrr,
                "ndcg": summary_by_k[k].ndcg,
            }
            for k in k_values
        },
        "bootstrap_ci": bootstrap,
        "latency_ms": {
            "samples": len(latencies_ms),
            "mean": round(sum(latencies_ms) / len(latencies_ms), 4) if latencies_ms else 0.0,
            "p50": round(sorted(latencies_ms)[len(latencies_ms) // 2], 4) if latencies_ms else 0.0,
        },
    }
    return summary, per_case_rows


def run_benchmark(
    *,
    split: str = "dev",
    top_k: int = DEFAULT_TOP_K,
    k_values: tuple[int, ...] = DEFAULT_K_VALUES,
    output_dir: Path = RESULTS_DIR,
) -> dict[str, Any]:
    chunks = load_markdown_knowledge_base(KB_PATH)
    cases = load_cases(GOLDEN_PATH, split=split)
    bm25 = build_bm25_retriever(chunks)

    methods: list[tuple[str, Any]] = [("bm25", bm25)]
    hybrid, hybrid_name = try_build_hybrid_retriever(chunks)
    dense_available = False
    if hybrid is not None and hybrid_name is not None:
        methods.append((hybrid_name, hybrid))
        dense_available = True

    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "split": split,
        "corpus": {
            "knowledge_base_path": str(KB_PATH.relative_to(AI_ROOT.parent)),
            "chunk_count": len(chunks),
        },
        "dataset": {
            "path": str(GOLDEN_PATH.relative_to(AI_ROOT.parent)),
            "case_count": len(cases),
        },
        "dense_retrieval_available": dense_available,
        "methods": {},
    }

    for method_name, retriever in methods:
        summary, per_case = run_retriever(
            retriever,
            cases,
            top_k=top_k,
            k_values=k_values,
        )
        payload["methods"][method_name] = summary

        per_case_path = output_dir / f"{split}_{method_name}_per_query.jsonl"
        with per_case_path.open("w", encoding="utf-8") as handle:
            for row in per_case:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")

    metrics_path = output_dir / f"{split}_retrieval_metrics.json"
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Directory for benchmark artifacts",
    )
    args = parser.parse_args(argv)

    if args.split == "all":
        for split in ("dev", "test"):
            run_benchmark(split=split, top_k=args.top_k, output_dir=args.output_dir)
    else:
        result = run_benchmark(split=args.split, top_k=args.top_k, output_dir=args.output_dir)
        print(json.dumps(result["methods"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
