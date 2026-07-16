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
    DenseRetriever,
    EmbeddingEncoder,
    SentenceTransformerE5Encoder,
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
    DENSE_E5 = "dense_e5"
    HYBRID_RRF = "hybrid_rrf"


METHOD_ORDER_SEED = 20260713


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
    return run_retrieval_experiment(
        method=method.value,
        retriever_factory=retriever_factory,
        retriever_provenance=provenance,
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )


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
    if len(set(methods)) != len(methods):
        raise ValueError("Retrieval methods must be unique")
    validate_experiment_request(
        method=",".join(method.value for method in methods),
        split=split,
        top_k=top_k,
        allow_frozen_test=allow_frozen_test,
    )
    shared_encoder = encoder
    if shared_encoder is None and any(method is not RetrievalMethod.BM25 for method in methods):
        shared_encoder = SentenceTransformerE5Encoder()
    execution_order = list(methods)
    random.Random(METHOD_ORDER_SEED).shuffle(execution_order)
    executed_results = {
        method.value: run_method(
            method,
            split,
            top_k=top_k,
            allow_frozen_test=allow_frozen_test,
            encoder=shared_encoder,
        )
        for method in execution_order
    }
    results = {name: executed_results[name] for name in sorted(executed_results)}
    return {
        "split": split.value,
        "top_k": top_k,
        "methods": results,
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


def _build_method(
    method: RetrievalMethod,
    encoder: EmbeddingEncoder | None,
) -> tuple[RetrieverFactory, dict[str, object]]:
    if method is RetrievalMethod.BM25:
        return BM25Retriever, _bm25_provenance()

    resolved_encoder = encoder or SentenceTransformerE5Encoder()
    dense_provenance = {
        "model_name": resolved_encoder.model_name,
        "model_revision": resolved_encoder.model_revision,
        "dimension": resolved_encoder.dimension,
        "query_prefix": "query: ",
        "document_prefix": "passage: ",
        "normalized_embeddings": True,
    }
    if method is RetrievalMethod.DENSE_E5:
        return (
            lambda chunks: DenseRetriever(chunks, resolved_encoder),
            {
                "name": method.value,
                "implementation": "app.rag.embedding_retriever.DenseRetriever",
                "version": "repository",
                "parameters": dense_provenance,
            },
        )

    if method is RetrievalMethod.HYBRID_RRF:
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

    raise ValueError(f"Unsupported retrieval method: {method}")


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
        description="Compare BM25, multilingual E5, and hybrid RRF retrieval."
    )
    parser.add_argument(
        "--method",
        choices=["all", *(method.value for method in RetrievalMethod)],
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
        tuple(RetrievalMethod)
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
