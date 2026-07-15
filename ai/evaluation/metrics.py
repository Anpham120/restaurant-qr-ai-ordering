"""Retrieval metric helpers for Phase 3 evaluation harness."""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class CutoffMetrics:
    hit: float
    mrr: float
    ndcg: float


@dataclass(frozen=True)
class BootstrapInterval:
    estimate: float
    ci_lower: float
    ci_upper: float
    iterations: int
    seed: int


def hit_at_k(
    ranked_ids: Sequence[str],
    expected_ids: Sequence[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    expected = set(expected_ids)
    if not expected:
        return 0.0
    top = ranked_ids[:k]
    return 1.0 if any(item in expected for item in top) else 0.0


def mrr_at_k(
    ranked_ids: Sequence[str],
    expected_ids: Sequence[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    expected = set(expected_ids)
    if not expected:
        return 0.0
    for index, item in enumerate(ranked_ids[:k], start=1):
        if item in expected:
            return 1.0 / index
    return 0.0


def ndcg_at_k(
    ranked_ids: Sequence[str],
    expected_ids: Sequence[str],
    k: int,
) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    expected = set(expected_ids)
    if not expected:
        return 0.0
    dcg = sum(
        1.0 / math.log2(index + 1)
        for index, item in enumerate(ranked_ids[:k], start=1)
        if item in expected
    )
    ideal_hits = min(len(expected), k)
    ideal_dcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def score_ranking(
    ranked_ids: Sequence[str],
    expected_ids: Sequence[str],
    *,
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> dict[int, CutoffMetrics]:
    deduped = list(dict.fromkeys(ranked_ids))
    return {
        k: CutoffMetrics(
            hit=hit_at_k(deduped, expected_ids, k),
            mrr=mrr_at_k(deduped, expected_ids, k),
            ndcg=ndcg_at_k(deduped, expected_ids, k),
        )
        for k in k_values
    }


def aggregate_metrics(
    per_query: Mapping[str, dict[int, CutoffMetrics]],
    *,
    k_values: Sequence[int] = (1, 3, 5, 10),
) -> dict[int, CutoffMetrics]:
    if not per_query:
        return {k: CutoffMetrics(0.0, 0.0, 0.0) for k in k_values}
    return {
        k: CutoffMetrics(
            hit=statistics.fmean(row[k].hit for row in per_query.values()),
            mrr=statistics.fmean(row[k].mrr for row in per_query.values()),
            ndcg=statistics.fmean(row[k].ndcg for row in per_query.values()),
        )
        for k in k_values
    }


def bootstrap_ci(
    values: Sequence[float],
    *,
    statistic: str = "mean",
    iterations: int = 10_000,
    confidence: float = 0.95,
    seed: int = 20260714,
) -> BootstrapInterval:
    if not values:
        return BootstrapInterval(0.0, 0.0, 0.0, iterations, seed)
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if iterations <= 0:
        raise ValueError("iterations must be positive")

    rng = random.Random(seed)
    n = len(values)
    samples: list[float] = []
    for _ in range(iterations):
        draw = [values[rng.randrange(n)] for _ in range(n)]
        if statistic == "mean":
            samples.append(statistics.fmean(draw))
        elif statistic == "median":
            samples.append(statistics.median(draw))
        else:
            raise ValueError(f"Unsupported statistic: {statistic}")

    samples.sort()
    alpha = 1.0 - confidence
    lower_index = int(alpha / 2 * iterations)
    upper_index = int((1.0 - alpha / 2) * iterations) - 1
    lower_index = max(0, min(lower_index, iterations - 1))
    upper_index = max(0, min(upper_index, iterations - 1))
    return BootstrapInterval(
        estimate=statistics.fmean(values),
        ci_lower=samples[lower_index],
        ci_upper=samples[upper_index],
        iterations=iterations,
        seed=seed,
    )
