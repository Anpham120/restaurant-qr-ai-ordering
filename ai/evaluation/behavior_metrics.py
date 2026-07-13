from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class BehaviorCaseMetrics:
    case_id: str
    expected_flag_count: int
    detected_flag_count: int
    flag_precision: float
    flag_recall: float
    flag_f1: float
    missing_flags: tuple[str, ...]
    unexpected_flags: tuple[str, ...]
    forbidden_suggestions: tuple[str, ...]


@dataclass(frozen=True)
class BehaviorSummary:
    evaluated_cases: int
    flag_evaluated_cases: int
    macro_flag_precision: float
    macro_flag_recall: float
    macro_flag_f1: float
    exact_flag_match_rate: float
    forbidden_suggestion_rate: float


def score_behavior_case(
    case_id: str,
    expected_flags: Sequence[str],
    detected_flags: Sequence[str],
    suggested_document_ids: Sequence[str] = (),
    forbidden_document_ids: Sequence[str] = (),
) -> BehaviorCaseMetrics:
    expected = set(expected_flags)
    detected = set(detected_flags)
    true_positive = len(expected.intersection(detected))
    precision = true_positive / len(detected) if detected else 0.0
    recall = true_positive / len(expected) if expected else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    forbidden = set(forbidden_document_ids)
    return BehaviorCaseMetrics(
        case_id=case_id,
        expected_flag_count=len(expected),
        detected_flag_count=len(detected),
        flag_precision=precision,
        flag_recall=recall,
        flag_f1=f1,
        missing_flags=tuple(sorted(expected - detected)),
        unexpected_flags=tuple(sorted(detected - expected)),
        forbidden_suggestions=tuple(
            document_id for document_id in suggested_document_ids if document_id in forbidden
        ),
    )


def summarize_behavior_metrics(
    metrics: Sequence[BehaviorCaseMetrics],
) -> BehaviorSummary:
    if not metrics:
        return BehaviorSummary(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)
    flag_metrics = [
        item
        for item in metrics
        if item.expected_flag_count > 0 or item.detected_flag_count > 0
    ]
    return BehaviorSummary(
        evaluated_cases=len(metrics),
        flag_evaluated_cases=len(flag_metrics),
        macro_flag_precision=(
            statistics.fmean(item.flag_precision for item in flag_metrics)
            if flag_metrics
            else 0.0
        ),
        macro_flag_recall=(
            statistics.fmean(item.flag_recall for item in flag_metrics)
            if flag_metrics
            else 0.0
        ),
        macro_flag_f1=(
            statistics.fmean(item.flag_f1 for item in flag_metrics)
            if flag_metrics
            else 0.0
        ),
        exact_flag_match_rate=statistics.fmean(
            1.0 if not item.missing_flags and not item.unexpected_flags else 0.0
            for item in metrics
        ),
        forbidden_suggestion_rate=statistics.fmean(
            1.0 if item.forbidden_suggestions else 0.0 for item in metrics
        ),
    )
