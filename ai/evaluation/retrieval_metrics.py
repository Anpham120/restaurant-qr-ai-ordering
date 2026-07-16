from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class QueryCutoffMetrics:
    reciprocal_rank: float
    ndcg: float
    hit: float
    precision: float
    recall: float
    forbidden_hits: tuple[str, ...]


@dataclass(frozen=True)
class SummaryCutoffMetrics:
    mrr: float
    ndcg: float
    hit_rate: float
    precision: float
    recall: float
    forbidden_hit_rate: float


@dataclass(frozen=True)
class QueryMetrics:
    case_id: str
    by_k: dict[int, QueryCutoffMetrics]


@dataclass(frozen=True)
class RetrievalSummary:
    evaluated_cases: int
    by_k: dict[int, SummaryCutoffMetrics]


def score_query(
    case_id: str,
    ranked_document_ids: Sequence[str],
    expected_document_ids: Sequence[str],
    forbidden_document_ids: Sequence[str] = (),
    *,
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> QueryMetrics:
    expected = set(expected_document_ids)
    forbidden = set(forbidden_document_ids)
    ranked = list(dict.fromkeys(ranked_document_ids))
    by_k: dict[int, QueryCutoffMetrics] = {}
    for k in k_values:
        if k <= 0:
            raise ValueError("k values must be positive integers")
        top = ranked[:k]
        positive_ranks = [
            index
            for index, document_id in enumerate(top, start=1)
            if document_id in expected
        ]
        relevant_count = len(positive_ranks)
        by_k[k] = QueryCutoffMetrics(
            reciprocal_rank=1 / positive_ranks[0] if positive_ranks else 0.0,
            ndcg=_ndcg(top, expected, k),
            hit=1.0 if relevant_count else 0.0,
            precision=relevant_count / k,
            recall=relevant_count / len(expected) if expected else 0.0,
            forbidden_hits=tuple(
                document_id for document_id in top if document_id in forbidden
            ),
        )

    return QueryMetrics(
        case_id=case_id,
        by_k=by_k,
    )


def summarize_query_metrics(
    metrics: Sequence[QueryMetrics],
    *,
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> RetrievalSummary:
    if not metrics:
        return RetrievalSummary(
            evaluated_cases=0,
            by_k={k: SummaryCutoffMetrics(0, 0, 0, 0, 0, 0) for k in k_values},
        )

    return RetrievalSummary(
        evaluated_cases=len(metrics),
        by_k={k: _aggregate_cutoff(metrics, k) for k in k_values},
    )


def evaluate_rankings(
    rankings: Mapping[str, Sequence[str]],
    expected_by_case: Mapping[str, Sequence[str]],
    forbidden_by_case: Mapping[str, Sequence[str]] | None = None,
    *,
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> tuple[RetrievalSummary, tuple[QueryMetrics, ...]]:
    forbidden_by_case = forbidden_by_case or {}
    per_query = tuple(
        score_query(
            case_id,
            rankings.get(case_id, ()),
            expected_ids,
            forbidden_by_case.get(case_id, ()),
            k_values=k_values,
        )
        for case_id, expected_ids in expected_by_case.items()
        if expected_ids
    )
    return summarize_query_metrics(per_query, k_values=k_values), per_query


def _aggregate_cutoff(
    metrics: Sequence[QueryMetrics], k: int
) -> SummaryCutoffMetrics:
    rows = [item.by_k[k] for item in metrics]
    return SummaryCutoffMetrics(
        mrr=statistics.fmean(item.reciprocal_rank for item in rows),
        ndcg=statistics.fmean(item.ndcg for item in rows),
        hit_rate=statistics.fmean(item.hit for item in rows),
        precision=statistics.fmean(item.precision for item in rows),
        recall=statistics.fmean(item.recall for item in rows),
        forbidden_hit_rate=statistics.fmean(
            1.0 if item.forbidden_hits else 0.0 for item in rows
        ),
    )


def _ndcg(ranked: Sequence[str], expected: set[str], k: int) -> float:
    dcg = sum(
        1 / math.log2(index + 1)
        for index, document_id in enumerate(ranked[:k], start=1)
        if document_id in expected
    )
    ideal_hits = min(len(expected), k)
    ideal_dcg = sum(1 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0
