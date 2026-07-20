from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Sequence

from app.rag.knowledge_base import load_markdown_knowledge_base

from app.rag.vietnamese_normalizer import normalize_query_text

from evaluation.research_dataset import (
    DatasetValidationError,
    RetrievalTarget,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MENU_PATH = PROJECT_ROOT / "backend" / "data" / "menu-dataset.json"
DEFAULT_KNOWLEDGE_BASE_PATH = PROJECT_ROOT / "ai" / "knowledge-base"


class SelectorKind(StrEnum):
    DOCUMENT = "document"
    MENU_CATEGORY = "menu-category"
    MENU_TAG = "menu-tag"
    KNOWLEDGE_SOURCE = "kb-source"


@dataclass(frozen=True)
class MenuDocumentMetadata:
    menu_item_id: str
    category_id: str
    category_name: str
    tags: tuple[str, ...]
    is_available: bool
    price: int | float


@dataclass(frozen=True)
class KnowledgeDocumentMetadata:
    source: str
    tags: tuple[str, ...]


DocumentMetadata = MenuDocumentMetadata | KnowledgeDocumentMetadata


@dataclass(frozen=True)
class ResearchDocument:
    document_id: str
    target: RetrievalTarget
    title: str
    text: str
    metadata: DocumentMetadata


def load_research_corpus(
    menu_path: Path = DEFAULT_MENU_PATH,
    knowledge_base_path: Path = DEFAULT_KNOWLEDGE_BASE_PATH,
) -> tuple[ResearchDocument, ...]:
    documents = tuple(
        [
            *_load_menu_documents(menu_path),
            *_load_knowledge_documents(knowledge_base_path),
        ]
    )
    issues = validate_research_corpus(documents)
    if issues:
        raise DatasetValidationError("\n".join(issues))
    return documents


def resolve_selectors(
    selectors: Sequence[str],
    documents: Sequence[ResearchDocument],
) -> frozenset[str]:
    selected: set[str] = set()
    for selector in selectors:
        raw_kind, separator, raw_value = selector.partition(":")
        if not separator or not raw_value.strip():
            raise DatasetValidationError(f"Invalid selector: {selector!r}")
        try:
            kind = SelectorKind(raw_kind)
        except ValueError as error:
            raise DatasetValidationError(
                f"Unsupported selector kind: {raw_kind!r}"
            ) from error

        value = raw_value.strip()
        normalized_value = normalize_query_text(value)
        if kind is SelectorKind.DOCUMENT:
            matches = [document for document in documents if document.document_id == value]
        elif kind is SelectorKind.MENU_CATEGORY:
            matches = [
                document
                for document in documents
                if isinstance(document.metadata, MenuDocumentMetadata)
                and normalize_query_text(document.metadata.category_name) == normalized_value
            ]
        elif kind is SelectorKind.MENU_TAG:
            matches = [
                document
                for document in documents
                if isinstance(document.metadata, MenuDocumentMetadata)
                and normalized_value in {normalize_query_text(tag) for tag in document.metadata.tags}
            ]
        else:
            matches = [
                document
                for document in documents
                if isinstance(document.metadata, KnowledgeDocumentMetadata)
                and normalize_query_text(document.metadata.source) == normalized_value
            ]
        selected.update(document.document_id for document in matches)
    return frozenset(selected)


def validate_research_corpus(documents: Sequence[ResearchDocument]) -> tuple[str, ...]:
    issues: list[str] = []
    seen: set[str] = set()
    for document in documents:
        if document.document_id in seen:
            issues.append(f"Duplicate document_id: {document.document_id}")
        seen.add(document.document_id)
        if not document.title.strip() or not document.text.strip():
            issues.append(f"{document.document_id}: title and text are required")
        if document.target is RetrievalTarget.MENU:
            if not isinstance(document.metadata, MenuDocumentMetadata):
                issues.append(f"{document.document_id}: invalid menu metadata")
            else:
                metadata = document.metadata
                if not metadata.menu_item_id or document.document_id != f"menu:{metadata.menu_item_id}":
                    issues.append(f"{document.document_id}: valid menu item ID is required")
                if not metadata.category_id or not metadata.category_name:
                    issues.append(f"{document.document_id}: menu category is required")
                if not all(isinstance(tag, str) and tag.strip() for tag in metadata.tags):
                    issues.append(f"{document.document_id}: menu tags must be non-empty strings")
                if not isinstance(metadata.is_available, bool):
                    issues.append(f"{document.document_id}: is_available must be boolean")
                if (
                    isinstance(metadata.price, bool)
                    or not isinstance(metadata.price, (int, float))
                    or not math.isfinite(metadata.price)
                    or metadata.price < 0
                ):
                    issues.append(f"{document.document_id}: price must be finite and non-negative")
        elif not isinstance(document.metadata, KnowledgeDocumentMetadata):
            issues.append(f"{document.document_id}: invalid knowledge metadata")
        elif not document.metadata.source:
            issues.append(f"{document.document_id}: knowledge source is required")
        elif not all(
            isinstance(tag, str) and tag.strip() for tag in document.metadata.tags
        ):
            issues.append(
                f"{document.document_id}: knowledge tags must be non-empty strings"
            )
    return tuple(issues)


def build_corpus_manifest(
    documents: Sequence[ResearchDocument],
    menu_path: Path = DEFAULT_MENU_PATH,
    knowledge_base_path: Path = DEFAULT_KNOWLEDGE_BASE_PATH,
) -> dict[str, object]:
    canonical = [
        {
            "document_id": document.document_id,
            "target": document.target.value,
            "title": document.title,
            "text": document.text,
            "metadata": asdict(document.metadata),
        }
        for document in sorted(documents, key=lambda item: item.document_id)
    ]
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    knowledge_sources = {
        path.relative_to(knowledge_base_path).as_posix(): _sha256_file(path)
        for path in sorted(knowledge_base_path.rglob("*.md"))
    }
    encoded_knowledge_sources = json.dumps(
        knowledge_sources,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "corpus_sha256": hashlib.sha256(encoded).hexdigest(),
        "menu_source_sha256": _sha256_file(menu_path),
        "knowledge_base_sha256": hashlib.sha256(encoded_knowledge_sources).hexdigest(),
        "knowledge_source_sha256": knowledge_sources,
        "document_count": len(documents),
        "menu_document_count": sum(
            1 for item in documents if item.target is RetrievalTarget.MENU
        ),
        "knowledge_document_count": sum(
            1 for item in documents if item.target is RetrievalTarget.KNOWLEDGE
        ),
    }


def _load_menu_documents(menu_path: Path) -> list[ResearchDocument]:
    payload = json.loads(menu_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise DatasetValidationError("Menu dataset must be an object.")
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise DatasetValidationError("Menu dataset must contain an items array.")

    documents: list[ResearchDocument] = []
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise DatasetValidationError(f"Menu item at index {index} must be an object.")
        item_id = _required_menu_string(item, "id", index)
        name = _required_menu_string(item, "name", index)
        category_id = _required_menu_string(item, "categoryId", index)
        category_name = _required_menu_string(item, "categoryName", index)
        description_value = item.get("description", "")
        if not isinstance(description_value, str):
            raise DatasetValidationError(
                f"Menu item {item_id}: description must be a string."
            )
        description = description_value.strip()
        raw_tags = item.get("tags")
        if not isinstance(raw_tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in raw_tags
        ):
            raise DatasetValidationError(
                f"Menu item {item_id}: tags must be an array of non-empty strings."
            )
        tags = tuple(tag.strip() for tag in raw_tags)
        is_available = item.get("isAvailable")
        if not isinstance(is_available, bool):
            raise DatasetValidationError(
                f"Menu item {item_id}: isAvailable must be boolean."
            )
        price = item.get("price")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price < 0
        ):
            raise DatasetValidationError(
                f"Menu item {item_id}: price must be finite and non-negative."
            )
        price_text = (
            f"{int(price):,} VND"
            if isinstance(price, (int, float)) and math.isfinite(price)
            else "unknown"
        )
        text = "\n".join(
            [
                name,
                f"Danh mục: {category_name}",
                f"Mô tả: {description}",
                f"Giá: {price_text}",
                f"Nhãn: {', '.join(tags)}",
                f"Trạng thái: {'đang bán' if is_available else 'tạm hết'}",
            ]
        )
        documents.append(
            ResearchDocument(
                document_id=f"menu:{item_id}",
                target=RetrievalTarget.MENU,
                title=name,
                text=text,
                metadata=MenuDocumentMetadata(
                    menu_item_id=item_id,
                    category_id=category_id,
                    category_name=category_name,
                    tags=tags,
                    is_available=is_available,
                    price=price,
                ),
            )
        )
    return documents


def _load_knowledge_documents(knowledge_base_path: Path) -> list[ResearchDocument]:
    documents: list[ResearchDocument] = []
    for chunk in load_markdown_knowledge_base(knowledge_base_path):
        slug = re.sub(r"[^a-z0-9]+", "-", normalize_query_text(chunk.title)).strip("-")
        documents.append(
            ResearchDocument(
                document_id=f"kb:{chunk.source}:{slug}",
                target=RetrievalTarget.KNOWLEDGE,
                title=chunk.title,
                text=chunk.content,
                metadata=KnowledgeDocumentMetadata(
                    source=chunk.source,
                    tags=tuple(chunk.tags),
                ),
            )
        )
    return documents


def _required_menu_string(item: dict, key: str, index: int) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DatasetValidationError(
            f"Menu item at index {index}: {key} must be a non-empty string."
        )
    return value.strip()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
