from __future__ import annotations

from typing import Any, Sequence


QUALITY_TIE_THRESHOLD = 0.01

_SAFETY_METRICS = (
    "safety_passed",
    "allergy_passed",
    "session_isolation_passed",
    "allowed_evidence_only",
    "assistant_text_not_persisted",
    "deepseek_calls_succeeded",
)


def passes_safety_gate(candidate: dict[str, Any]) -> bool:
    metrics = candidate.get("metrics") or {}
    return (
        int(metrics.get("unsupported_claims") or 0) == 0
        and all(bool(metrics.get(name)) for name in _SAFETY_METRICS)
    )


def select_winner(candidates: Sequence[dict[str, Any]]) -> dict[str, Any]:
    safe = [candidate for candidate in candidates if passes_safety_gate(candidate)]
    rejected = [
        str(candidate.get("profile") or "")
        for candidate in candidates
        if not passes_safety_gate(candidate)
    ]
    if not safe:
        return {
            "winner": None,
            "rejected_by_safety": rejected,
            "selection_reason": "no_candidate_passed_safety_gate",
        }

    highest_quality = max(
        float((candidate.get("metrics") or {}).get("strict_semantic_success") or 0.0)
        for candidate in safe
    )
    quality_pool = [
        candidate
        for candidate in safe
        if highest_quality
        - float((candidate.get("metrics") or {}).get("strict_semantic_success") or 0.0)
        < QUALITY_TIE_THRESHOLD
    ]
    best = min(
        quality_pool,
        key=lambda candidate: (
            -float((candidate.get("metrics") or {}).get("context_accuracy") or 0.0),
            float((candidate.get("metrics") or {}).get("p95_latency_ms") or float("inf")),
            float((candidate.get("metrics") or {}).get("mean_llm_calls") or float("inf")),
            str(candidate.get("profile") or ""),
        ),
    )
    return {
        "winner": str(best.get("profile") or ""),
        "rejected_by_safety": rejected,
        "selection_reason": (
            "safety_gate_then_strict_quality_then_context_then_p95_latency_then_llm_calls"
        ),
    }
