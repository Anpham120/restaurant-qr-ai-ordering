"""Secret-safe comparison of two full-system LLM evaluation artifacts."""

from __future__ import annotations

import math
import statistics
from typing import Any


def compare_model_artifacts(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compare models on the same cases without copying queries or answers."""

    rows = [_model_row(profile, artifact) for profile, artifact in artifacts.items()]
    case_sets = {
        profile: {str(case.get("id")) for case in (artifact.get("cases") or [])}
        for profile, artifact in artifacts.items()
    }
    unique_sets = {frozenset(case_ids) for case_ids in case_sets.values()}
    paired: dict[str, Any]
    if len(rows) < 2:
        status = "incomplete_models"
        paired = _empty_paired(case_sets)
    elif len(unique_sets) != 1:
        status = "not_comparable_case_sets"
        paired = _empty_paired(case_sets)
    else:
        paired = _paired_comparison(artifacts)
        status = (
            "comparable"
            if paired["shared_llm_success_case_count"] > 0
            else "availability_only_no_shared_success"
        )
    return {
        "comparison_version": "dual-model-v2",
        "gateway": "9router",
        "comparison_status": status,
        "quality_definition": (
            "per-model composite_pass among llm_success cases; paired quality "
            "only where both models have llm_success"
        ),
        "retriever_runtime": _retriever_runtime_summary(artifacts),
        "generation_input_parity": _generation_input_parity(artifacts),
        "models": rows,
        "paired": paired,
    }


def _model_row(profile: str, artifact: dict[str, Any]) -> dict[str, Any]:
    cases = artifact.get("cases") or []
    has_call_markers = any("llm_called" in case for case in cases)
    attempted = (
        [case for case in cases if case.get("llm_called") is True]
        if has_call_markers
        else list(cases)
    )
    successful = [case for case in attempted if case.get("llm_success") is True]
    quality = [case for case in successful if case.get("composite_pass") is True]
    grounded = [case for case in successful if case.get("grounding_pass") is True]
    schema_valid = [case for case in successful if case.get("schema_valid") is True]
    faithfulness = [
        value
        for value in (_finite_float(case.get("faithfulness_score")) for case in successful)
        if value is not None
    ]
    latencies = []
    for case in successful:
        raw = case.get("latency_ms")
        value = raw.get("total") if isinstance(raw, dict) else raw
        finite = _finite_float(value)
        if finite is not None:
            latencies.append(finite)
    return {
        "profile": profile,
        "model": str((artifact.get("llm") or {}).get("model") or "unknown"),
        "provider": str((artifact.get("llm") or {}).get("provider") or "9router"),
        "split": str(artifact.get("split") or "unknown"),
        "evaluated_cases": len(cases),
        "llm_call_rate": _ratio(len(attempted), len(cases)),
        "availability": _ratio(len(successful), len(attempted)),
        "quality_on_success": _ratio(len(quality), len(successful)),
        "grounding_on_success": _ratio(len(grounded), len(successful)),
        "schema_valid_on_success": _ratio(len(schema_valid), len(successful)),
        "faithfulness_mean_on_success": (
            statistics.fmean(faithfulness) if faithfulness else None
        ),
        "latency_total_ms_on_success": _latency_summary(latencies),
    }


def _paired_comparison(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    profiles = list(artifacts)
    left, right = profiles[0], profiles[1]
    left_cases = {str(case.get("id")): case for case in artifacts[left].get("cases") or []}
    right_cases = {str(case.get("id")): case for case in artifacts[right].get("cases") or []}
    common = sorted(set(left_cases) & set(right_cases))
    availability_wins = {left: 0, right: 0}
    availability_ties = 0
    quality_wins = {left: 0, right: 0}
    quality_ties = 0
    shared_llm_success_case_count = 0
    faithfulness_deltas = []
    for case_id in common:
        left_case, right_case = left_cases[case_id], right_cases[case_id]
        left_success = left_case.get("llm_success") is True
        right_success = right_case.get("llm_success") is True
        if left_success and not right_success:
            availability_wins[left] += 1
        elif right_success and not left_success:
            availability_wins[right] += 1
        else:
            availability_ties += 1
        if not (left_success and right_success):
            continue
        shared_llm_success_case_count += 1
        left_pass = left_case.get("composite_pass") is True
        right_pass = right_case.get("composite_pass") is True
        if left_pass and not right_pass:
            quality_wins[left] += 1
        elif right_pass and not left_pass:
            quality_wins[right] += 1
        else:
            quality_ties += 1
        left_f = _finite_float(left_case.get("faithfulness_score"))
        right_f = _finite_float(right_case.get("faithfulness_score"))
        if left_f is not None and right_f is not None:
            faithfulness_deltas.append(left_f - right_f)
    return {
        "left_profile": left,
        "right_profile": right,
        "common_case_count": len(common),
        "shared_llm_success_case_count": shared_llm_success_case_count,
        "availability_wins": availability_wins,
        "availability_ties": availability_ties,
        "quality_wins": quality_wins,
        "quality_ties": quality_ties,
        # One-release compatibility aliases; these are quality-only by definition.
        "wins": quality_wins,
        "ties": quality_ties,
        "faithfulness_mean_delta_left_minus_right": (
            statistics.fmean(faithfulness_deltas) if faithfulness_deltas else None
        ),
    }


def _empty_paired(case_sets: dict[str, set[str]]) -> dict[str, Any]:
    common_case_count = len(set.intersection(*case_sets.values())) if case_sets else 0
    return {
        "common_case_count": common_case_count,
        "shared_llm_success_case_count": 0,
        "availability_wins": {},
        "availability_ties": 0,
        "quality_wins": {},
        "quality_ties": 0,
        "wins": {},
        "ties": 0,
    }


def _retriever_runtime_summary(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_profile = {
        profile: _normalized_retriever_runtime(artifact.get("retriever_runtime"))
        for profile, artifact in artifacts.items()
    }
    runtimes = {jsonable_tuple(runtime) for runtime in by_profile.values()}
    return {
        "same_runtime": bool(by_profile) and len(runtimes) == 1,
        "fallback_present": any(bool(runtime.get("fallback_used")) for runtime in by_profile.values()),
        "by_profile": by_profile,
    }


def _normalized_retriever_runtime(value: Any) -> dict[str, Any]:
    runtime = value if isinstance(value, dict) else {}
    return {
        "requested_method": str(runtime.get("requested_method") or "unknown"),
        "effective_method": str(runtime.get("effective_method") or "unknown"),
        "embedding_model": runtime.get("embedding_model"),
        "fallback_used": bool(runtime.get("fallback_used")),
        "fallback_error_type": runtime.get("fallback_error_type"),
    }


def _generation_input_parity(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    profiles = list(artifacts)
    if len(profiles) < 2:
        return _empty_generation_input_parity()

    left, right = profiles[0], profiles[1]
    left_cases = {
        str(case.get("id")): case
        for case in artifacts[left].get("cases") or []
        if case.get("llm_called") is True
    }
    right_cases = {
        str(case.get("id")): case
        for case in artifacts[right].get("cases") or []
        if case.get("llm_called") is True
    }
    common = sorted(set(left_cases) & set(right_cases))
    verifiable = 0
    matching = 0
    missing = 0
    mismatching = 0
    for case_id in common:
        left_hash = _valid_generation_input_hash(left_cases[case_id].get("generation_input_sha256"))
        right_hash = _valid_generation_input_hash(right_cases[case_id].get("generation_input_sha256"))
        if left_hash is None or right_hash is None:
            missing += 1
            continue
        verifiable += 1
        if left_hash == right_hash:
            matching += 1
        else:
            mismatching += 1

    generation_configs = {
        jsonable_tuple(_normalized_generation_config((artifact.get("llm") or {}).get("generation_config")))
        for artifact in artifacts.values()
    }
    same_generation_config = bool(artifacts) and len(generation_configs) == 1
    passed = bool(
        common
        and verifiable == len(common)
        and matching == len(common)
        and missing == 0
        and mismatching == 0
        and same_generation_config
    )
    return {
        "common_llm_called_pair_count": len(common),
        "verifiable_pair_count": verifiable,
        "matching_pair_count": matching,
        "missing_pair_count": missing,
        "mismatching_pair_count": mismatching,
        "same_generation_config": same_generation_config,
        "pass": passed,
    }


def _empty_generation_input_parity() -> dict[str, Any]:
    return {
        "common_llm_called_pair_count": 0,
        "verifiable_pair_count": 0,
        "matching_pair_count": 0,
        "missing_pair_count": 0,
        "mismatching_pair_count": 0,
        "same_generation_config": False,
        "pass": False,
    }


def _valid_generation_input_hash(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        return None
    return text


def _normalized_generation_config(value: Any) -> dict[str, Any]:
    config = value if isinstance(value, dict) else {}
    return {
        "max_tokens": config.get("max_tokens"),
        "reasoning_effort": config.get("reasoning_effort"),
        "llm_intent_classification_enabled": bool(
            config.get("llm_intent_classification_enabled")
        ),
    }


def jsonable_tuple(value: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((key, str(item)) for key, item in value.items()))


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _latency_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "p50": None, "p95": None}
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "p50": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)],
    }


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
