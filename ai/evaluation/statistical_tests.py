from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class BootstrapComparison:
    mean_delta: float
    ci_lower: float
    ci_upper: float
    p_value: float
    iterations: int
    seed: int


@dataclass(frozen=True)
class McNemarResult:
    method_a_only: int
    method_b_only: int
    success_rate_delta: float
    p_value: float


@dataclass(frozen=True)
class WilcoxonResult:
    non_zero_pairs: int
    w_plus: float
    w_minus: float
    statistic: float
    p_value: float


def paired_bootstrap(
    method_a: Sequence[float],
    method_b: Sequence[float],
    *,
    iterations: int = 10_000,
    confidence: float = 0.95,
    seed: int = 20260713,
) -> BootstrapComparison:
    _validate_pairs(method_a, method_b)
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")

    deltas = [a - b for a, b in zip(method_a, method_b, strict=True)]
    randomizer = random.Random(seed)
    sample_means = sorted(
        statistics.fmean(
            deltas[randomizer.randrange(len(deltas))] for _ in range(len(deltas))
        )
        for _ in range(iterations)
    )
    alpha = 1 - confidence
    lower_index = max(0, math.floor((alpha / 2) * (iterations - 1)))
    upper_index = min(
        iterations - 1,
        math.ceil((1 - alpha / 2) * (iterations - 1)),
    )
    observed_delta = statistics.fmean(deltas)
    null_randomizer = random.Random(seed + 1)
    extreme_null_samples = sum(
        abs(
            statistics.fmean(
                delta if null_randomizer.random() < 0.5 else -delta
                for delta in deltas
            )
        )
        >= abs(observed_delta) - 1e-12
        for _ in range(iterations)
    )
    p_value = (extreme_null_samples + 1) / (iterations + 1)
    return BootstrapComparison(
        mean_delta=observed_delta,
        ci_lower=sample_means[lower_index],
        ci_upper=sample_means[upper_index],
        p_value=p_value,
        iterations=iterations,
        seed=seed,
    )


def mcnemar_exact(
    method_a_success: Sequence[bool],
    method_b_success: Sequence[bool],
) -> McNemarResult:
    _validate_pairs(method_a_success, method_b_success)
    method_a_only = sum(
        a and not b
        for a, b in zip(method_a_success, method_b_success, strict=True)
    )
    method_b_only = sum(
        b and not a
        for a, b in zip(method_a_success, method_b_success, strict=True)
    )
    discordant = method_a_only + method_b_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, index)
            for index in range(min(method_a_only, method_b_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    success_rate_delta = (
        sum(method_a_success) - sum(method_b_success)
    ) / len(method_a_success)
    return McNemarResult(
        method_a_only=method_a_only,
        method_b_only=method_b_only,
        success_rate_delta=success_rate_delta,
        p_value=p_value,
    )


def wilcoxon_signed_rank(
    method_a: Sequence[float],
    method_b: Sequence[float],
) -> WilcoxonResult:
    _validate_pairs(method_a, method_b)
    differences = [
        a - b
        for a, b in zip(method_a, method_b, strict=True)
        if not math.isclose(a, b, abs_tol=1e-12)
    ]
    if not differences:
        return WilcoxonResult(0, 0.0, 0.0, 0.0, 1.0)

    ranks = _average_ranks([abs(value) for value in differences])
    w_plus = sum(rank for rank, value in zip(ranks, differences, strict=True) if value > 0)
    w_minus = sum(rank for rank, value in zip(ranks, differences, strict=True) if value < 0)
    statistic = min(w_plus, w_minus)
    p_value = (
        _wilcoxon_exact_p_value(ranks, statistic)
        if len(differences) <= 20
        else _wilcoxon_normal_p_value(ranks, w_plus)
    )
    return WilcoxonResult(
        non_zero_pairs=len(differences),
        w_plus=w_plus,
        w_minus=w_minus,
        statistic=statistic,
        p_value=p_value,
    )


def holm_bonferroni(p_values: Mapping[str, float]) -> dict[str, float]:
    for name, value in p_values.items():
        if not 0 <= value <= 1:
            raise ValueError(f"p-value for {name!r} must be between 0 and 1")
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running_max = 0.0
    total = len(ordered)
    for index, (name, p_value) in enumerate(ordered):
        running_max = max(running_max, min(1.0, (total - index) * p_value))
        adjusted[name] = running_max
    return {name: adjusted[name] for name in p_values}


def _validate_pairs(method_a: Sequence, method_b: Sequence) -> None:
    if len(method_a) != len(method_b):
        raise ValueError("paired samples must have the same length")
    if not method_a:
        raise ValueError("paired samples cannot be empty")


def _average_ranks(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and math.isclose(
            ordered[end][1], ordered[index][1], abs_tol=1e-12
        ):
            end += 1
        average_rank = ((index + 1) + end) / 2
        for ordered_index in range(index, end):
            ranks[ordered[ordered_index][0]] = average_rank
        index = end
    return ranks


def _wilcoxon_exact_p_value(ranks: Sequence[float], observed: float) -> float:
    total_rank = sum(ranks)
    extreme = 0
    assignments = 1 << len(ranks)
    for mask in range(assignments):
        w_plus = sum(
            rank for index, rank in enumerate(ranks) if mask & (1 << index)
        )
        if min(w_plus, total_rank - w_plus) <= observed + 1e-12:
            extreme += 1
    return extreme / assignments


def _wilcoxon_normal_p_value(ranks: Sequence[float], w_plus: float) -> float:
    expected = sum(ranks) / 2
    variance = sum(rank * rank for rank in ranks) / 4
    if variance == 0:
        return 1.0
    z_score = (abs(w_plus - expected) - 0.5) / math.sqrt(variance)
    return math.erfc(max(0.0, z_score) / math.sqrt(2))
