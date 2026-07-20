from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Sequence
from enum import Enum
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from app.rag.embedding_retriever import (  # noqa: E402
    ENCODER_REGISTRY,
    DenseRetriever,
    EmbeddingEncoder,
    create_encoder,
    estimate_encoder_memory_mb,
)
from app.rag.hybrid_retriever import HybridRrfRetriever  # noqa: E402
from app.rag.knowledge_base import KnowledgeChunk  # noqa: E402
from app.rag.retriever import (  # noqa: E402
    BM25_B,
    BM25_K1,
    TAG_BOOST,
    TITLE_BOOST,
    BM25Retriever,
    Retriever,
)
from evaluation.research_dataset import DatasetSplit  # noqa: E402
from evaluation.retrieval_comparison import compare_retrieval_results  # noqa: E402
from evaluation.run_research_baseline import (  # noqa: E402
    RetrieverFactory,
    run_retrieval_experiment,
    validate_experiment_request,
)


class RetrievalMethod(str, Enum):
    BM25 = "bm25"
    DENSE_E5_SMALL = "dense_e5_small"
    DENSE_MPNET = "dense_mpnet"
    DENSE_VI_BI = "dense_vi_bi"
    HYBRID_E5_SMALL = "hybrid_e5_small"
    HYBRID_MPNET = "hybrid_mpnet"
    HYBRID_VI_BI = "hybrid_vi_bi"

    # Backward-compatible aliases from earlier experiment exports.
    DENSE_E5 = "dense_e5_small"
    DENSE_E5_BASE = "dense_mpnet"
    HYBRID_RRF = "hybrid_e5_small"
    HYBRID_E5_BASE = "hybrid_mpnet"


METHOD_ORDER_SEED = 20260713
DEFAULT_METHODS = (
    RetrievalMethod.BM25,
    RetrievalMethod.DENSE_E5_SMALL,
    RetrievalMethod.DENSE_MPNET,
    RetrievalMethod.DENSE_VI_BI,
    RetrievalMethod.HYBRID_E5_SMALL,
    RetrievalMethod.HYBRID_MPNET,
    RetrievalMethod.HYBRID_VI_BI,
)


def run_method(
    method: RetrievalMethod,
    split: DatasetSplit = DatasetSplit.DEV,
    *,
    top_k: int = 10,
    allow_frozen_test: bool = False,
    encoder: EmbeddingEncoder | None = None,
) -> dict[str, object]:
    validate_experiment_request(
        method=method.value,
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )
    retriever_factory, provenance = _build_method(method, encoder)
    result = run_retrieval_experiment(
        method=method.value,
        retriever_factory=retriever_factory,
        retriever_provenance=provenance,
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )
    if encoder is not None and method is not RetrievalMethod.BM25:
        result["resource_profile"] = {
            "estimated_encoder_memory_mb": estimate_encoder_memory_mb(encoder),
            "embedding_dimension": encoder.dimension,
        }
    return result


def run_comparison(
    methods: Sequence[RetrievalMethod],
    split: DatasetSplit = DatasetSplit.DEV,
    *,
    top_k: int = 10,
    allow_frozen_test: bool = False,
    encoder: EmbeddingEncoder | None = None,
) -> dict[str, object]:
    if not methods:
        raise ValueError("At least one retrieval method is required")
    if len(set(method.value for method in methods)) != len(methods):
        raise ValueError("Retrieval methods must be unique")
    validate_experiment_request(
        method=",".join(method.value for method in methods),
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )

    encoder_cache: dict[str, EmbeddingEncoder] = {}
    execution_order = list(methods)
    random.Random(METHOD_ORDER_SEED).shuffle(execution_order)
    executed_results: dict[str, dict[str, object]] = {}
    for method in execution_order:
        method_encoder = encoder
        encoder_key = _method_encoder_key(method)
        if encoder_key is not None:
            if encoder_key not in encoder_cache:
                encoder_cache[encoder_key] = create_encoder(encoder_key)
            method_encoder = encoder_cache[encoder_key]
        executed_results[method.value] = run_method(
            method,
            split,
            top_k=top_k,
            allow_frozen_test=allow_frozen_test,
            encoder=method_encoder,
        )

    results = {name: executed_results[name] for name in sorted(executed_results)}
    return {
        "split": split.value,
        "top_k": top_k,
        "methods": results,
        "encoder_registry": {
            key: {
                "model_name": spec.model_name,
                "model_revision": spec.model_revision,
                "prefix_kind": spec.prefix_kind,
                "estimated_size_mb": spec.estimated_size_mb,
            }
            for key, spec in ENCODER_REGISTRY.items()
        },
        "method_order_protocol": {
            "strategy": "deterministic-shuffle",
            "seed": METHOD_ORDER_SEED,
            "execution_order": [method.value for method in execution_order],
        },
        "pairwise_statistics": compare_retrieval_results(
            results,
            cutoff=_comparison_cutoff(top_k),
        ),
    }


def _comparison_cutoff(top_k: int) -> int:
    return max(value for value in (1, 3, 5, 10) if value <= top_k)


def _method_encoder_key(method: RetrievalMethod) -> str | None:
    mapping = {
        RetrievalMethod.DENSE_E5_SMALL: "e5_small",
        RetrievalMethod.DENSE_MPNET: "mpnet_base",
        RetrievalMethod.DENSE_E5_BASE: "mpnet_base",
        RetrievalMethod.DENSE_VI_BI: "vi_bi",
        RetrievalMethod.HYBRID_E5_SMALL: "e5_small",
        RetrievalMethod.HYBRID_MPNET: "mpnet_base",
        RetrievalMethod.HYBRID_E5_BASE: "mpnet_base",
        RetrievalMethod.HYBRID_VI_BI: "vi_bi",
        RetrievalMethod.DENSE_E5: "e5_small",
        RetrievalMethod.HYBRID_RRF: "e5_small",
    }
    return mapping.get(method)


def _build_method(
    method: RetrievalMethod,
    encoder: EmbeddingEncoder | None,
) -> tuple[RetrieverFactory, dict[str, object]]:
    if method is RetrievalMethod.BM25:
        return BM25Retriever, _bm25_provenance()

    encoder_key = _method_encoder_key(method)
    if encoder_key is None:
        raise ValueError(f"Unsupported retrieval method: {method}")

    resolved_encoder = encoder or create_encoder(encoder_key)
    dense_provenance = _dense_provenance(resolved_encoder, encoder_key)
    if method.value.startswith("dense_"):
        return (
            lambda chunks: DenseRetriever(chunks, resolved_encoder),
            {
                "name": method.value,
                "implementation": "app.rag.embedding_retriever.DenseRetriever",
                "version": "repository",
                "parameters": dense_provenance,
            },
        )

    def build_hybrid(chunks: list[KnowledgeChunk]) -> Retriever:
        return HybridRrfRetriever(
            [
                BM25Retriever(chunks),
                DenseRetriever(chunks, resolved_encoder),
            ],
            rrf_k=60,
            candidate_multiplier=4,
        )

    return (
        build_hybrid,
        {
            "name": method.value,
            "implementation": "app.rag.hybrid_retriever.HybridRrfRetriever",
            "version": "repository",
            "parameters": {
                "rrf_k": 60,
                "candidate_multiplier": 4,
                "weights": [1.0, 1.0],
                "lexical": _bm25_provenance()["parameters"],
                "dense": dense_provenance,
            },
        },
    )


def _dense_provenance(encoder: EmbeddingEncoder, encoder_key: str) -> dict[str, object]:
    spec = ENCODER_REGISTRY[encoder_key]
    return {
        "encoder_key": encoder_key,
        "model_name": encoder.model_name,
        "model_revision": encoder.model_revision,
        "dimension": encoder.dimension,
        "query_prefix": "query: " if spec.prefix_kind == "e5" else "",
        "document_prefix": "passage: " if spec.prefix_kind == "e5" else "",
        "normalized_embeddings": True,
        "estimated_encoder_memory_mb": estimate_encoder_memory_mb(encoder),
    }


def _bm25_provenance() -> dict[str, object]:
    return {
        "name": RetrievalMethod.BM25.value,
        "implementation": "app.rag.retriever.BM25Retriever",
        "version": "repository",
        "parameters": {
            "k1": BM25_K1,
            "b": BM25_B,
            "title_boost": TITLE_BOOST,
            "tag_boost": TAG_BOOST,
        },
    }


def _parse_args(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare BM25, dense encoders, and hybrid RRF retrieval."
    )
    parser.add_argument(
        "--method",
        choices=["all", *(method.value for method in DEFAULT_METHODS)],
        default="all",
    )
    parser.add_argument(
        "--split",
        choices=[split.value for split in DatasetSplit],
        default=DatasetSplit.DEV.value,
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-frozen-test",
        action="store_true",
        help="Required before opening the frozen test split.",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    args = _parse_args(arguments)
    methods = (
        tuple(DEFAULT_METHODS)
        if args.method == "all"
        else (RetrievalMethod(args.method),)
    )
    try:
        result = run_comparison(
            methods,
            DatasetSplit(args.split),
            top_k=args.top_k,
            allow_frozen_test=args.allow_frozen_test,
        )
    except (PermissionError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 2

    serialized = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is None:
        print(serialized)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
