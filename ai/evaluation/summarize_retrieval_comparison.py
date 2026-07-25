"""Summarize multi-method retrieval comparison into a compact summary JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DEFAULT_KNOWLEDGE_MANIFEST = Path(__file__).resolve().parent / "results" / "knowledge_manifest.json"


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
            "latency_repetitions": (latency.get("protocol") or {}).get(
                "repetitions_per_query"
            ),
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
        "screening_protocol": comparison.get("screening_protocol"),
        "experiment_profile": comparison.get("experiment_profile"),
        "selection": {
            "provisional_method": ranked[0][0],
            "basis": (
                "Best dev point estimates for MRR@5, nDCG@5 and Hit@10; "
                "latency is screening-only when screening_protocol says so."
            ),
            "ranking": [name for name, _ in ranked],
        },
    }


def attach_knowledge_index_provenance(
    summary: dict[str, object],
    manifest: dict[str, object],
    *,
    manifest_sha256: str,
) -> dict[str, object]:
    """Link the full eval corpus to the exact versioned KB index artifact.

    The evaluation corpus also contains live-menu research documents, so its
    ``corpus_sha256`` is intentionally different from the KB-only index hash.
    Source hashes must still match before the relationship is recorded.
    """

    corpus = dict(summary.get("corpus") or {})
    eval_sources = corpus.get("knowledge_source_sha256") or {}
    index_sources = manifest.get("knowledge_source_sha256") or {}
    if not eval_sources or eval_sources != index_sources:
        raise ValueError(
            "Knowledge source hashes do not match the versioned index manifest"
        )
    index_corpus_sha256 = str(manifest.get("corpus_sha256") or "")
    index_sha256 = str(manifest.get("index_sha256") or "")
    if not index_corpus_sha256 or not index_sha256:
        raise ValueError("Knowledge index manifest is missing corpus/index hashes")
    corpus.update(
        {
            "knowledge_index_corpus_sha256": index_corpus_sha256,
            "knowledge_index_sha256": index_sha256,
            "knowledge_index_manifest_sha256": manifest_sha256,
        }
    )
    return {**summary, "corpus": corpus}


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize retrieval comparison JSON.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--knowledge-manifest",
        type=Path,
        default=DEFAULT_KNOWLEDGE_MANIFEST,
    )
    args = parser.parse_args()
    comparison = json.loads(args.input.read_text(encoding="utf-8"))
    summary = summarize_comparison(comparison)
    manifest_bytes = args.knowledge_manifest.read_bytes()
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    summary = attach_knowledge_index_provenance(
        summary,
        manifest,
        manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
