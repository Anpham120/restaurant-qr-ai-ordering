"""Retrieval confidence scoring.

Computes a confidence score (0.0–1.0) from retrieval results to determine
whether the RAG context is reliable enough for LLM generation.
Low confidence triggers fallback behavior instead of risking hallucination.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Sequence


# Thresholds
HIGH_CONFIDENCE = 0.7
MEDIUM_CONFIDENCE = 0.3
LOW_CONFIDENCE = 0.1


@dataclass(frozen=True)
class ConfidenceResult:
    """Result of confidence assessment."""
    score: float  # 0.0 to 1.0
    level: str  # "high", "medium", "low"
    reason: str
    should_call_llm: bool
    guardrail_flag: str | None  # flag to add, or None

    @staticmethod
    def from_score(score: float, reason: str) -> ConfidenceResult:
        if score >= HIGH_CONFIDENCE:
            return ConfidenceResult(
                score=score, level="high", reason=reason,
                should_call_llm=True, guardrail_flag=None,
            )
        elif score >= MEDIUM_CONFIDENCE:
            return ConfidenceResult(
                score=score, level="medium", reason=reason,
                should_call_llm=True, guardrail_flag="LOW_RETRIEVAL_CONFIDENCE",
            )
        elif score >= LOW_CONFIDENCE:
            return ConfidenceResult(
                score=score, level="low", reason=reason,
                should_call_llm=True, guardrail_flag="LOW_RETRIEVAL_CONFIDENCE",
            )
        else:
            return ConfidenceResult(
                score=score, level="very_low", reason=reason,
                should_call_llm=False, guardrail_flag="RETRIEVAL_FAILED",
            )


def compute_retrieval_confidence(
    results: Sequence[dict[str, Any] | Any],
    top_n: int = 3,
) -> ConfidenceResult:
    """Compute confidence from retrieval results.

    Factors:
    1. Top-1 score (absolute quality)
    2. Score gap between top-1 and top-3 (discrimination)
    3. Source diversity (multiple sources = more robust)
    4. Number of results (fewer = less confident)

    Args:
        results: List of retrieval results with .score attribute or 'score' key.
        top_n: Number of top results to consider.

    Returns:
        ConfidenceResult with score, level, and action recommendations.
    """
    if not results:
        return ConfidenceResult.from_score(0.0, "No retrieval results")

    scores = _extract_scores(results)
    if not scores:
        return ConfidenceResult.from_score(0.0, "No valid scores")

    top_scores = scores[:top_n]
    top1 = top_scores[0]

    # Factor 1: Top-1 absolute score (0-1 range)
    # BM25 scores can be >1, normalize
    score_weight = min(top1 / 10.0, 1.0) if top1 > 1.0 else top1

    # Factor 2: Score gap (top-1 vs rest) — higher gap = clearer winner
    if len(top_scores) >= 2:
        avg_rest = statistics.mean(top_scores[1:])
        gap = (top1 - avg_rest) / max(top1, 0.001)
        gap_factor = min(gap * 2, 1.0)  # normalize
    else:
        gap_factor = 0.5  # only 1 result, moderate confidence

    # Factor 3: Source diversity
    sources = _extract_sources(results[:top_n])
    unique_sources = len(set(sources))
    diversity = min(unique_sources / max(top_n, 1), 1.0)

    # Factor 4: Result count
    count_factor = min(len(scores) / top_n, 1.0)

    # Weighted combination
    confidence = (
        0.40 * score_weight
        + 0.25 * gap_factor
        + 0.20 * diversity
        + 0.15 * count_factor
    )
    confidence = max(0.0, min(1.0, confidence))

    reason = (
        f"top1_score={top1:.3f}, gap={gap_factor:.2f}, "
        f"diversity={unique_sources}/{top_n}, count={len(scores)}"
    )
    return ConfidenceResult.from_score(confidence, reason)


def _extract_scores(results: Sequence[Any]) -> list[float]:
    """Extract numeric scores from results, sorted descending."""
    scores: list[float] = []
    for r in results:
        if isinstance(r, dict):
            score = r.get("score", 0.0)
        elif hasattr(r, "score"):
            score = r.score
        else:
            continue
        try:
            scores.append(float(score))
        except (TypeError, ValueError):
            continue
    return sorted(scores, reverse=True)


def _extract_sources(results: Sequence[Any]) -> list[str]:
    """Extract source identifiers from results."""
    sources: list[str] = []
    for r in results:
        if isinstance(r, dict):
            source = r.get("source", "")
            if not source:
                chunk = r.get("chunk")
                if chunk and hasattr(chunk, "source"):
                    source = chunk.source
        elif hasattr(r, "chunk") and hasattr(r.chunk, "source"):
            source = r.chunk.source
        else:
            source = ""
        sources.append(str(source))
    return sources
