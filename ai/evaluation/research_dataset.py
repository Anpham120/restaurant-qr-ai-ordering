from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Callable, Iterable, Sequence


class DatasetSplit(StrEnum):
    DEV = "dev"
    TEST = "test"


class RetrievalTarget(StrEnum):
    KNOWLEDGE = "knowledge"
    MENU = "menu"


ALLOWED_REVIEW_STATUSES = frozenset(
    {"engineering-reviewed", "restaurant-reviewed", "frozen"}
)
DEFAULT_REVIEWER_EVIDENCE = "engineering-review-v1"


class DatasetValidationError(ValueError):
    """Raised when the research dataset cannot be used safely."""


@dataclass(frozen=True)
class RelevanceLabels:
    expected_selectors: tuple[str, ...] = ()
    forbidden_selectors: tuple[str, ...] = ()
    guardrail_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class QueryFamily:
    family_id: str
    split: DatasetSplit
    target: RetrievalTarget
    intent: str
    queries: tuple[str, ...]
    labels: RelevanceLabels
    rationale: str = ""
    annotation_origin: str = "curated-family-templates"
    review_status: str = "engineering-reviewed"
    reviewer_evidence: str = DEFAULT_REVIEWER_EVIDENCE


@dataclass(frozen=True)
class ResearchCase:
    case_id: str
    family_id: str
    split: DatasetSplit
    target: RetrievalTarget
    intent: str
    query: str
    labels: RelevanceLabels
    annotation_origin: str
    review_status: str
    rationale: str
    reviewer_evidence: str = DEFAULT_REVIEWER_EVIDENCE


@dataclass(frozen=True)
class ResearchDataset:
    version: str
    description: str
    annotation_origin: str
    review_status: str
    reviewer_evidence: str
    families: tuple[QueryFamily, ...]


@dataclass(frozen=True)
class DatasetAudit:
    issues: tuple[str, ...]
    family_count: int
    case_count: int
    split_counts: dict[str, int]
    target_counts: dict[str, int]
    intent_counts: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.issues


SelectorResolver = Callable[[Sequence[str]], frozenset[str]]


def load_research_dataset(path: Path) -> ResearchDataset:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    raw_families = payload.get("families")
    if not isinstance(raw_families, list):
        raise DatasetValidationError("Dataset must contain a families array.")

    annotation_origin = _required_string(payload, "annotation_origin")
    review_status = _required_string(payload, "review_status")
    reviewer_evidence = _string_or_default(
        payload,
        "reviewer_evidence",
        DEFAULT_REVIEWER_EVIDENCE,
    )
    families = tuple(
        _parse_family(
            item,
            annotation_origin=annotation_origin,
            review_status=review_status,
            reviewer_evidence=reviewer_evidence,
        )
        for item in raw_families
    )
    return ResearchDataset(
        version=_required_string(payload, "dataset_version"),
        description=_required_string(payload, "description"),
        annotation_origin=annotation_origin,
        review_status=review_status,
        reviewer_evidence=reviewer_evidence,
        families=families,
    )


def load_materialized_cases(path: Path) -> tuple[ResearchCase, ...]:
    cases: list[ResearchCase] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            cases.append(_parse_case(payload))
        except (json.JSONDecodeError, DatasetValidationError) as error:
            raise DatasetValidationError(
                f"Invalid JSONL case at line {line_number}: {error}"
            ) from error
    return tuple(cases)


def expand_families(dataset: ResearchDataset) -> tuple[ResearchCase, ...]:
    cases: list[ResearchCase] = []
    for family in dataset.families:
        for index, query in enumerate(family.queries, start=1):
            cases.append(
                ResearchCase(
                    case_id=f"{family.family_id}-{index:02d}",
                    family_id=family.family_id,
                    split=family.split,
                    target=family.target,
                    intent=family.intent,
                    query=query,
                    labels=family.labels,
                    annotation_origin=family.annotation_origin,
                    review_status=family.review_status,
                    rationale=family.rationale,
                    reviewer_evidence=family.reviewer_evidence,
                )
            )
    return tuple(cases)


def assert_materialized_cases_match(
    dataset: ResearchDataset,
    materialized_cases: Sequence[ResearchCase],
) -> None:
    expected = expand_families(dataset)
    actual = tuple(materialized_cases)
    if actual != expected:
        expected_by_id = {case.case_id: case for case in expected}
        actual_by_id = {case.case_id: case for case in actual}
        missing = sorted(set(expected_by_id) - set(actual_by_id))
        extra = sorted(set(actual_by_id) - set(expected_by_id))
        changed = sorted(
            case_id
            for case_id in set(expected_by_id).intersection(actual_by_id)
            if expected_by_id[case_id] != actual_by_id[case_id]
        )
        raise DatasetValidationError(
            "Materialized JSONL does not match query families: "
            f"missing={missing[:5]}, extra={extra[:5]}, changed={changed[:5]}"
        )


def audit_dataset(
    dataset: ResearchDataset,
    selector_resolver: SelectorResolver | None = None,
) -> DatasetAudit:
    issues: list[str] = []
    family_ids: set[str] = set()
    normalized_queries: dict[str, tuple[str, DatasetSplit]] = {}

    if dataset.review_status not in ALLOWED_REVIEW_STATUSES:
        issues.append(f"Unsupported review_status: {dataset.review_status!r}")

    for family in dataset.families:
        if family.family_id in family_ids:
            issues.append(f"Duplicate family_id: {family.family_id}")
        family_ids.add(family.family_id)

        if not family.annotation_origin:
            issues.append(f"{family.family_id}: annotation_origin is required")
        if family.review_status not in ALLOWED_REVIEW_STATUSES:
            issues.append(
                f"{family.family_id}: unsupported review_status "
                f"{family.review_status!r}"
            )
        if not family.reviewer_evidence:
            issues.append(f"{family.family_id}: reviewer_evidence is required")

        if not family.intent:
            issues.append(f"{family.family_id}: intent is required")
        if not family.queries:
            issues.append(f"{family.family_id}: at least one query is required")
        if not family.labels.expected_selectors and not family.labels.guardrail_flags:
            issues.append(
                f"{family.family_id}: expected selectors or guardrail flags are required"
            )

        for query in family.queries:
            normalized = normalize_query(query)
            if not normalized:
                issues.append(f"{family.family_id}: query cannot be blank")
                continue
            previous = normalized_queries.get(normalized)
            if previous is not None:
                previous_family, previous_split = previous
                issues.append(
                    f"Duplicate normalized query in {previous_family}/{previous_split} "
                    f"and {family.family_id}/{family.split}: {query!r}"
                )
            else:
                normalized_queries[normalized] = (family.family_id, family.split)

        if selector_resolver is not None:
            _audit_selectors(family, selector_resolver, issues)

    cases = expand_families(dataset)
    return DatasetAudit(
        issues=tuple(issues),
        family_count=len(dataset.families),
        case_count=len(cases),
        split_counts=dict(Counter(case.split.value for case in cases)),
        target_counts=dict(Counter(case.target.value for case in cases)),
        intent_counts=dict(Counter(case.intent for case in cases)),
    )


def assert_research_ready(
    dataset: ResearchDataset,
    audit: DatasetAudit,
    *,
    min_cases: int,
    required_intents: Iterable[str],
) -> None:
    issues = list(audit.issues)
    if audit.case_count < min_cases:
        issues.append(
            f"Dataset has {audit.case_count} cases; at least {min_cases} are required."
        )
    for split in DatasetSplit:
        if audit.split_counts.get(split.value, 0) == 0:
            issues.append(f"Dataset split {split.value!r} is empty.")
    missing_intents = sorted(set(required_intents) - set(audit.intent_counts))
    if missing_intents:
        issues.append(f"Dataset is missing required intents: {', '.join(missing_intents)}")
    if issues:
        raise DatasetValidationError("\n".join(issues))


def build_dataset_manifest(
    dataset: ResearchDataset,
    family_source_path: Path,
    materialized_path: Path,
) -> dict[str, object]:
    cases = expand_families(dataset)
    return {
        "dataset_version": dataset.version,
        "family_source_sha256": _sha256(family_source_path),
        "materialized_cases_sha256": _sha256(materialized_path),
        "annotation_origin": dataset.annotation_origin,
        "review_status": dataset.review_status,
        "reviewer_evidence": dataset.reviewer_evidence,
        "annotation_origin_counts": dict(Counter(case.annotation_origin for case in cases)),
        "review_status_counts": dict(Counter(case.review_status for case in cases)),
        "reviewer_evidence_counts": dict(
            Counter(case.reviewer_evidence for case in cases)
        ),
        "family_count": len(dataset.families),
        "case_count": len(cases),
        "split_counts": dict(Counter(case.split.value for case in cases)),
        "target_counts": dict(Counter(case.target.value for case in cases)),
        "intent_counts": dict(Counter(case.intent for case in cases)),
    }


def normalize_query(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().lower())
    without_marks = "".join(
        character for character in decomposed if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_marks.replace("đ", "d").split())


def _parse_family(
    raw: object,
    *,
    annotation_origin: str,
    review_status: str,
    reviewer_evidence: str,
) -> QueryFamily:
    if not isinstance(raw, dict):
        raise DatasetValidationError("Each query family must be an object.")
    return QueryFamily(
        family_id=_required_string(raw, "family_id"),
        split=_parse_enum(DatasetSplit, _required_string(raw, "split"), "split"),
        target=_parse_enum(
            RetrievalTarget, _required_string(raw, "target"), "target"
        ),
        intent=_required_string(raw, "intent"),
        queries=_string_tuple(raw.get("queries"), "queries"),
        labels=_parse_labels(raw),
        rationale=str(raw.get("notes") or "").strip(),
        annotation_origin=_string_or_default(
            raw, "annotation_origin", annotation_origin
        ),
        review_status=_string_or_default(raw, "review_status", review_status),
        reviewer_evidence=_string_or_default(
            raw, "reviewer_evidence", reviewer_evidence
        ),
    )


def _parse_case(raw: object) -> ResearchCase:
    if not isinstance(raw, dict):
        raise DatasetValidationError("Each materialized case must be an object.")
    return ResearchCase(
        case_id=_required_string(raw, "case_id"),
        family_id=_required_string(raw, "family_id"),
        split=_parse_enum(DatasetSplit, _required_string(raw, "split"), "split"),
        target=_parse_enum(
            RetrievalTarget, _required_string(raw, "target"), "target"
        ),
        intent=_required_string(raw, "intent"),
        query=_required_string(raw, "query"),
        labels=_parse_labels(raw),
        annotation_origin=_required_string(raw, "annotation_origin"),
        review_status=_required_string(raw, "review_status"),
        rationale=_required_string(raw, "rationale"),
        reviewer_evidence=_required_string(raw, "reviewer_evidence"),
    )


def _parse_labels(raw: dict) -> RelevanceLabels:
    return RelevanceLabels(
        expected_selectors=_string_tuple(
            raw.get("expected_selectors", []), "expected_selectors"
        ),
        forbidden_selectors=_string_tuple(
            raw.get("forbidden_selectors", []), "forbidden_selectors"
        ),
        guardrail_flags=_string_tuple(raw.get("guardrail_flags", []), "guardrail_flags"),
    )


def _required_string(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DatasetValidationError(f"{key} must be a non-empty string.")
    return value.strip()


def _string_or_default(payload: dict, key: str, default: str) -> str:
    if key not in payload:
        return default
    return _required_string(payload, key)


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise DatasetValidationError(f"{field_name} must be an array of strings.")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise DatasetValidationError(
                f"{field_name} must contain only non-empty strings."
            )
        output.append(item.strip())
    return tuple(output)


def _parse_enum(enum_type, value: str, field_name: str):
    try:
        return enum_type(value)
    except ValueError as error:
        choices = ", ".join(item.value for item in enum_type)
        raise DatasetValidationError(
            f"{field_name} must be one of: {choices}."
        ) from error


def _audit_selectors(
    family: QueryFamily,
    selector_resolver: SelectorResolver,
    issues: list[str],
) -> None:
    try:
        expected_ids = selector_resolver(family.labels.expected_selectors)
        forbidden_ids = selector_resolver(family.labels.forbidden_selectors)
    except DatasetValidationError as error:
        issues.append(f"{family.family_id}: {error}")
        return

    if family.labels.expected_selectors and not expected_ids:
        issues.append(f"{family.family_id}: expected selectors resolve to no documents")
    if family.labels.forbidden_selectors and not forbidden_ids:
        issues.append(f"{family.family_id}: forbidden selectors resolve to no documents")
    overlap = expected_ids.intersection(forbidden_ids)
    if overlap:
        issues.append(
            f"{family.family_id}: expected and forbidden documents overlap: "
            f"{', '.join(sorted(overlap))}"
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
