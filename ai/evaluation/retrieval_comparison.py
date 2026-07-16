from __future__ import annotations

import statistics
from dataclasses import asdict
from itertools import combinations
from typing import Mapping

from evaluation.statistical_tests import (
    holm_bonferroni,
    mcnemar_exact,
    paired_bootstrap,
    wilcoxon_signed_rank,
)


def compare_retrieval_results(
    results_by_method: Mapping[str, dict[str, object]],
    *,
    cutoff: int = 5,
) -> dict[str, object]:
    """Run paired significance tests for every method pair on identical cases."""
    if cutoff <= 0:
        raise ValueError("cutoff must be positive")
    if len(results_by_method) < 2:
        return {
            "cutoff": cutoff,
            "correction": "holm-bonferroni",
            "correction_scope": "within each test family across method pairs",
            "comparison_count": 0,
            "adjusted_test_count": 0,
            "comparisons": {},
        }

    method_names = list(results_by_method)
    comparisons_by_name: dict[str, dict[str, object]] = {}
    raw_p_values_by_test: dict[str, dict[str, float]] = {
        "mrr_bootstrap": {},
        "ndcg_bootstrap": {},
        "hit_mcnemar": {},
        "rank_wilcoxon": {},
        "latency_wilcoxon": {},
    }

    for baseline, candidate in combinations(method_names, 2):
        method_a = candidate
        method_b = baseline
        comparison_name = f"{method_a}_vs_{method_b}"
        cases_a = _cases_by_id(results_by_method[method_a])
        cases_b = _cases_by_id(results_by_method[method_b])
        if set(cases_a) != set(cases_b):
            raise ValueError(f"Unpaired case IDs for {comparison_name}")

        case_ids = sorted(cases_a)
        reciprocal_ranks_a = [
            _metric(cases_a[case_id], cutoff, "reciprocal_rank")
            for case_id in case_ids
        ]
        reciprocal_ranks_b = [
            _metric(cases_b[case_id], cutoff, "reciprocal_rank")
            for case_id in case_ids
        ]
        ndcg_a = [_metric(cases_a[case_id], cutoff, "ndcg") for case_id in case_ids]
        ndcg_b = [_metric(cases_b[case_id], cutoff, "ndcg") for case_id in case_ids]
        hits_a = [_metric(cases_a[case_id], cutoff, "hit") > 0 for case_id in case_ids]
        hits_b = [_metric(cases_b[case_id], cutoff, "hit") > 0 for case_id in case_ids]
        latency_a = [_float_field(cases_a[case_id], "latency_ms") for case_id in case_ids]
        latency_b = [_float_field(cases_b[case_id], "latency_ms") for case_id in case_ids]

        mrr_bootstrap = paired_bootstrap(reciprocal_ranks_a, reciprocal_ranks_b)
        ndcg_bootstrap = paired_bootstrap(ndcg_a, ndcg_b)
        hit_mcnemar = mcnemar_exact(hits_a, hits_b)
        rank_wilcoxon = wilcoxon_signed_rank(reciprocal_ranks_a, reciprocal_ranks_b)
        latency_wilcoxon = wilcoxon_signed_rank(latency_a, latency_b)

        tests = {
            "mrr_bootstrap": mrr_bootstrap.p_value,
            "ndcg_bootstrap": ndcg_bootstrap.p_value,
            "hit_mcnemar": hit_mcnemar.p_value,
            "rank_wilcoxon": rank_wilcoxon.p_value,
            "latency_wilcoxon": latency_wilcoxon.p_value,
        }
        for test_name, value in tests.items():
            raw_p_values_by_test[test_name][comparison_name] = value
        comparisons_by_name[comparison_name] = {
            "method_a": method_a,
            "method_b": method_b,
            "delta_definition": "method_a - method_b",
            "case_count": len(case_ids),
            "mrr_bootstrap": asdict(mrr_bootstrap),
            "ndcg_bootstrap": asdict(ndcg_bootstrap),
            "hit_mcnemar": asdict(hit_mcnemar),
            "rank_wilcoxon": asdict(rank_wilcoxon),
            "latency": {
                "median_delta_ms": statistics.median(
                    left - right
                    for left, right in zip(latency_a, latency_b, strict=True)
                ),
                "wilcoxon": asdict(latency_wilcoxon),
            },
        }

    adjusted_by_test = {
        test_name: holm_bonferroni(p_values)
        for test_name, p_values in raw_p_values_by_test.items()
    }
    for comparison_name, comparison in comparisons_by_name.items():
        comparison["holm_adjusted_p_values"] = {
            test_name: adjusted_by_test[test_name][comparison_name]
            for test_name in (
                "mrr_bootstrap",
                "ndcg_bootstrap",
                "hit_mcnemar",
                "rank_wilcoxon",
                "latency_wilcoxon",
            )
        }

    return {
        "cutoff": cutoff,
        "correction": "holm-bonferroni",
        "correction_scope": "within each test family across method pairs",
        "comparison_count": len(comparisons_by_name),
        "adjusted_test_count": sum(len(values) for values in adjusted_by_test.values()),
        "comparisons": comparisons_by_name,
    }


def _cases_by_id(result: dict[str, object]) -> dict[str, dict[str, object]]:
    raw_cases = result.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("Retrieval result must contain a cases list")
    cases = {}
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict) or not isinstance(raw_case.get("case_id"), str):
            raise ValueError("Each retrieval case must contain a string case_id")
        cases[raw_case["case_id"]] = raw_case
    if len(cases) != len(raw_cases):
        raise ValueError("Duplicate case IDs in retrieval result")
    return cases


def _metric(case: dict[str, object], cutoff: int, field: str) -> float:
    metrics = case.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("Case metrics are required")
    by_k = metrics.get("by_k")
    if not isinstance(by_k, dict):
        raise ValueError("Case cutoff metrics are required")
    cutoff_metrics = by_k.get(cutoff, by_k.get(str(cutoff)))
    if not isinstance(cutoff_metrics, dict):
        raise ValueError(f"Missing metrics at cutoff {cutoff}")
    return _float_field(cutoff_metrics, field)


def _float_field(payload: dict[str, object], field: str) -> float:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    return float(value)
