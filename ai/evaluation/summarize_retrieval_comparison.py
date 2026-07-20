"""Summarize multi-method retrieval comparison into a compact summary JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def summarize_comparison(comparison: dict[str, object]) -> dict[str, object]:
    methods = comparison["methods"]
    method_summaries = {}
    for name, payload in methods.items():
        metrics = payload["metrics"]["by_k"]
        latency = payload["latency_ms"]
        resource = payload.get("resource_profile") or {}
        retriever = payload["provenance"]["retriever"]
        dense_params = retriever.get("parameters", {})
        if isinstance(dense_params, dict) and "dense" in dense_params:
            dense_params = dense_params["dense"]
        method_summaries[name] = {
            "hit_at_1": metrics["1"]["hit_rate"],
            "hit_at_5": metrics["5"]["hit_rate"],
            "hit_at_10": metrics["10"]["hit_rate"],
            "mrr_at_5": metrics["5"]["mrr"],
            "ndcg_at_5": metrics["5"]["ndcg"],
            "forbidden_at_10": metrics["10"]["forbidden_hit_rate"],
            "p50_ms": latency["p50"],
            "p95_ms": latency["p95"],
            "estimated_encoder_memory_mb": dense_params.get("estimated_encoder_memory_mb")
            if isinstance(dense_params, dict)
            else resource.get("estimated_encoder_memory_mb"),
            "encoder_model": dense_params.get("model_name")
            if isinstance(dense_params, dict)
            else None,
        }

    ranked = sorted(
        method_summaries.items(),
        key=lambda item: (
            item[1]["mrr_at_5"],
            item[1]["ndcg_at_5"],
            item[1]["hit_at_10"],
        ),
        reverse=True,
    )
    return {
        "schema_version": "2.0.0",
        "scope": comparison.get("split", "dev"),
        "split": comparison.get("split"),
        "top_k": comparison.get("top_k"),
        "evaluated_cases": next(iter(methods.values()))["per_query_count"],
        "corpus": next(iter(methods.values()))["corpus"],
        "dataset": next(iter(methods.values()))["dataset"],
        "methods": method_summaries,
        "pairwise_statistics": comparison.get("pairwise_statistics"),
        "encoder_registry": comparison.get("encoder_registry"),
        "selection": {
            "provisional_method": ranked[0][0],
            "basis": "Best dev point estimates for MRR@5, nDCG@5 and Hit@10 with recorded latency/RAM trade-offs.",
            "ranking": [name for name, _ in ranked],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize retrieval comparison JSON.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    comparison = json.loads(args.input.read_text(encoding="utf-8"))
    summary = summarize_comparison(comparison)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
