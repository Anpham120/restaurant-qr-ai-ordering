"""Canonical, hash-bound research data for the restaurant AI report.

This module deliberately keeps all evaluation categories in one catalogue.
Retrieval, conversation, safety and availability are therefore views over a
shared source of truth rather than independently edited test sets.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


MANIFEST_RELATIVE_PATH = Path("evaluation/datasets/canonical_research_manifest.v1.json")


def _sha256_bytes(value: bytes) -> str:
    return f"sha256:{sha256(value).hexdigest()}"


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class KnowledgeBaseDocument:
    file: str
    topic: str
    business_purpose: str
    sample_question: str
    risk: str
    chunk_count: int


@dataclass(frozen=True)
class CanonicalCase:
    case_id: str
    views: tuple[str, ...]
    message: str
    history: tuple[str, ...]
    session_id: str | None
    expected_route: str | None
    expected_evidence_ids: tuple[str, ...]
    expected_menu_item_ids: tuple[str, ...]
    forbidden_menu_item_ids: tuple[str, ...]
    expected_price_vnd: int | None
    expected_focus_menu_item_ids: tuple[str, ...]
    expected_state: Mapping[str, Any]
    required_guardrail_flags: tuple[str, ...]
    expected_category_keywords: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    forbidden_state_keys: tuple[str, ...]
    fault: str | None
    expected_model: str | None
    tags: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalResearchBundle:
    catalog_version: str
    manifest_path: Path
    knowledge_base_path: Path
    menu_path: Path
    knowledge_base_inventory: tuple[KnowledgeBaseDocument, ...]
    cases: tuple[CanonicalCase, ...]
    knowledge_base_hash: str
    menu_fixture_hash: str
    dataset_hash: str

    @property
    def available_views(self) -> tuple[str, ...]:
        return tuple(sorted({view for case in self.cases for view in case.views}))

    def view(self, name: str) -> tuple[CanonicalCase, ...]:
        return tuple(case for case in self.cases if name in case.views)

    def dataset_provenance(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "cases": len(self.cases),
            "knowledge_base_documents": len(self.knowledge_base_inventory),
            "views": list(self.available_views),
            "knowledge_base_hash": self.knowledge_base_hash,
            "menu_fixture_hash": self.menu_fixture_hash,
            "dataset_hash": self.dataset_hash,
        }


def _count_markdown_chunks(path: Path) -> int:
    """Count reportable chunks using Markdown headings, falling back to one."""
    text = path.read_text(encoding="utf-8")
    headings = sum(1 for line in text.splitlines() if line.lstrip().startswith("#"))
    return max(1, headings)


def _knowledge_base_hash(path: Path) -> str:
    digest = sha256()
    for document in sorted(path.glob("*.md"), key=lambda item: item.name):
        digest.update(document.name.encode("utf-8"))
        digest.update(b"\0")
        # The KB is edited and reported from Windows but evaluated on Linux in
        # CI.  Normalize only the transport-level line ending; the Markdown
        # content itself remains part of the reproducibility contract.
        digest.update(document.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _case_from_raw(raw: Mapping[str, Any]) -> CanonicalCase:
    return CanonicalCase(
        case_id=raw["id"],
        views=tuple(raw.get("views", ())),
        message=raw["message"],
        history=tuple(raw.get("history", ())),
        session_id=raw.get("session_id"),
        expected_route=raw.get("expected_route"),
        expected_evidence_ids=tuple(raw.get("expected_evidence_ids", ())),
        expected_menu_item_ids=tuple(raw.get("expected_menu_item_ids", ())),
        forbidden_menu_item_ids=tuple(raw.get("forbidden_menu_item_ids", ())),
        expected_price_vnd=raw.get("expected_price_vnd"),
        expected_focus_menu_item_ids=tuple(raw.get("expected_focus_menu_item_ids", ())),
        expected_state=dict(raw.get("expected_state", {})),
        required_guardrail_flags=tuple(raw.get("required_guardrail_flags", ())),
        expected_category_keywords=tuple(raw.get("expected_category_keywords", ())),
        forbidden_claims=tuple(raw.get("forbidden_claims", ())),
        forbidden_state_keys=tuple(raw.get("forbidden_state_keys", ())),
        fault=raw.get("fault"),
        expected_model=raw.get("expected_model"),
        tags=tuple(raw.get("tags", ())),
    )


def load_canonical_research_bundle(ai_root: Path | None = None) -> CanonicalResearchBundle:
    """Load the frozen research catalogue and compute all input hashes."""
    resolved_ai_root = (ai_root or Path(__file__).resolve().parents[1]).resolve()
    manifest_path = resolved_ai_root / MANIFEST_RELATIVE_PATH
    raw_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    repository_root = resolved_ai_root.parent
    knowledge_base_path = repository_root / raw_manifest["data_governance"]["knowledge_base_directory"]
    menu_path = repository_root / raw_manifest["data_governance"]["menu_fixture"]

    documents = tuple(
        KnowledgeBaseDocument(
            file=item["file"],
            topic=item["topic"],
            business_purpose=item["business_purpose"],
            sample_question=item["sample_question"],
            risk=item["risk"],
            chunk_count=_count_markdown_chunks(knowledge_base_path / item["file"]),
        )
        for item in raw_manifest["knowledge_base_inventory"]
    )
    cases = tuple(_case_from_raw(item) for item in raw_manifest["cases"])
    knowledge_base_hash = _knowledge_base_hash(knowledge_base_path)
    # Hash the logical menu document, not its serialization bytes.  The
    # catalogue is evaluated on Windows locally and Linux in CI/production;
    # a byte hash would turn equivalent UTF-8/BOM or line-ending encodings into
    # a false dataset-drift deployment failure.
    menu_payload = json.loads(menu_path.read_text(encoding="utf-8-sig"))
    menu_fixture_hash = _sha256_bytes(_canonical_json(menu_payload))
    dataset_hash = _sha256_bytes(
        _canonical_json(
            {
                "manifest": raw_manifest,
                "knowledge_base_hash": knowledge_base_hash,
                "menu_fixture_hash": menu_fixture_hash,
            }
        )
    )
    return CanonicalResearchBundle(
        catalog_version=raw_manifest["catalog_version"],
        manifest_path=manifest_path,
        knowledge_base_path=knowledge_base_path,
        menu_path=menu_path,
        knowledge_base_inventory=documents,
        cases=cases,
        knowledge_base_hash=knowledge_base_hash,
        menu_fixture_hash=menu_fixture_hash,
        dataset_hash=dataset_hash,
    )


def validate_canonical_research_bundle(bundle: CanonicalResearchBundle) -> list[str]:
    """Return data-contract violations without mutating the research inputs."""
    errors: list[str] = []
    files_on_disk = {path.name for path in bundle.knowledge_base_path.glob("*.md")}
    files_in_manifest = {document.file for document in bundle.knowledge_base_inventory}
    if files_on_disk != files_in_manifest:
        missing = sorted(files_on_disk - files_in_manifest)
        stale = sorted(files_in_manifest - files_on_disk)
        if missing:
            errors.append(f"KB files missing from manifest: {', '.join(missing)}")
        if stale:
            errors.append(f"Manifest references absent KB files: {', '.join(stale)}")

    case_ids = [case.case_id for case in bundle.cases]
    if len(case_ids) != len(set(case_ids)):
        errors.append("Case ids must be unique.")
    if not bundle.cases:
        errors.append("The canonical catalogue cannot be empty.")
    for case in bundle.cases:
        if not case.views:
            errors.append(f"Case {case.case_id} has no evaluation view.")
        if not case.message:
            errors.append(f"Case {case.case_id} has no user message.")

    # The checked-in menu fixture is UTF-8 with BOM on Windows.  ``utf-8-sig``
    # accepts both BOM and non-BOM fixtures while preserving byte hashing above.
    menu = json.loads(bundle.menu_path.read_text(encoding="utf-8-sig"))
    menu_ids = {item["id"] for item in menu.get("items", [])}
    for case in bundle.cases:
        unknown = set(case.expected_menu_item_ids) - menu_ids
        if unknown:
            errors.append(f"Case {case.case_id} references unknown menu ids: {sorted(unknown)}")
        unknown_forbidden = set(case.forbidden_menu_item_ids) - menu_ids
        # A deliberately fake id is allowed only when it is not treated as a menu fact.
        if unknown_forbidden and case.expected_route != "abstain_or_clarify":
            errors.append(f"Case {case.case_id} has invalid forbidden menu ids: {sorted(unknown_forbidden)}")
    return errors


def cases_for_views(bundle: CanonicalResearchBundle, views: Iterable[str]) -> tuple[CanonicalCase, ...]:
    """Return a stable union of catalogue rows selected by one or more views."""
    requested = set(views)
    return tuple(case for case in bundle.cases if requested.intersection(case.views))


def canonical_pipeline_evaluation_dataset(bundle: CanonicalResearchBundle) -> dict[str, Any]:
    """Adapt the canonical catalogue to the existing pipeline evaluator contract.

    The evaluator predates the manifest and expects a compact turn schema.  This
    adapter is intentionally one-way: it never creates customer cases, it only
    projects canonical rows into that legacy execution contract.
    """
    adapted_cases: list[dict[str, Any]] = []
    for source in bundle.cases:
        # Availability faults are executed by the evaluator's fault-injection
        # probe; they remain manifest rows so the report still exposes them.
        if "availability" in source.views:
            continue
        category = (
            "allergy"
            if "ALLERGY_DISCLAIMER" in source.required_guardrail_flags
            else "safety"
            if "safety" in source.views
            else "multi_turn"
            if "multi_turn" in source.views
            else "single_turn"
        )
        evaluator_id = {
            "session_isolation_a": "session_a_allergy",
            "session_isolation_b": "session_b_clean",
        }.get(source.case_id, source.case_id)
        expected_price_text = (
            [f"{source.expected_price_vnd:,}".replace(",", "."), str(source.expected_price_vnd)]
            if source.expected_price_vnd is not None
            else []
        )
        final_turn = {
            "message": source.message,
            "expected_menu_ids": list(source.expected_menu_item_ids),
            "forbidden_menu_ids": list(source.forbidden_menu_item_ids),
            "expected_focus_menu_ids": list(source.expected_focus_menu_item_ids),
            "expected_constraints": dict(source.expected_state),
            "required_guardrail_flags": list(source.required_guardrail_flags),
            "content_contains_any": expected_price_text,
            "content_forbids": list(source.forbidden_claims),
        }
        history_turns = [{"message": message} for message in source.history[:-1]]
        if source.history and source.history[-1] == source.message:
            history_turns = [{"message": message} for message in source.history[:-1]]
        elif source.history:
            history_turns = [{"message": message} for message in source.history]
        adapted_cases.append(
            {
                "id": evaluator_id,
                "source_case_id": source.case_id,
                "category": category,
                "turns": [*history_turns, final_turn],
            }
        )
    return {
        "schema_version": "canonical-pipeline-evaluation-v1",
        "catalog_version": bundle.catalog_version,
        "dataset_hash": bundle.dataset_hash,
        "cases": adapted_cases,
    }
