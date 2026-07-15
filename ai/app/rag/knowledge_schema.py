"""Validate YAML frontmatter for knowledge-base markdown units."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = (
    "id",
    "title",
    "domain",
    "tags",
    "language",
    "source",
    "reviewed_by",
    "reviewed_at",
    "expires_at",
    "safety_level",
)

ALLOWED_SAFETY_LEVELS = {"low", "medium", "high", "critical"}
ALLOWED_LANGUAGES = {"vi", "en", "vi-en", "en-vi"}

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class KnowledgeUnitValidation:
    path: str
    valid: bool
    errors: tuple[str, ...]
    metadata: dict[str, Any]


def validate_knowledge_unit(path: Path | str) -> KnowledgeUnitValidation:
    """Validate a markdown knowledge unit's YAML frontmatter."""
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    metadata, errors = parse_frontmatter(text)
    error_list = list(errors)

    for field in REQUIRED_FIELDS:
        if field not in metadata or metadata[field] in (None, "", []):
            error_list.append(f"missing required field: {field}")

    if metadata.get("language") and metadata["language"] not in ALLOWED_LANGUAGES:
        error_list.append(f"invalid language: {metadata['language']}")

    safety = metadata.get("safety_level")
    if safety and str(safety).casefold() not in ALLOWED_SAFETY_LEVELS:
        error_list.append(f"invalid safety_level: {safety}")

    for date_field in ("reviewed_at", "expires_at"):
        value = metadata.get(date_field)
        if value and not _is_iso_date(str(value)):
            error_list.append(f"invalid date for {date_field}: {value}")

    tags = metadata.get("tags")
    if tags is not None and not isinstance(tags, list):
        error_list.append("tags must be a YAML list")

    return KnowledgeUnitValidation(
        path=str(file_path),
        valid=not error_list,
        errors=tuple(error_list),
        metadata=metadata,
    )


def validate_knowledge_base(directory: Path | str) -> list[KnowledgeUnitValidation]:
    """Validate all markdown files in a knowledge-base directory."""
    base = Path(directory)
    return [validate_knowledge_unit(path) for path in sorted(base.glob("*.md"))]


def parse_frontmatter(text: str) -> tuple[dict[str, Any], list[str]]:
    """Parse simple YAML frontmatter without external dependencies."""
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}, ["missing YAML frontmatter delimiters"]

    metadata: dict[str, Any] = {}
    errors: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            errors.append(f"invalid frontmatter line: {stripped}")
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            metadata[key] = [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
        elif value.startswith('"') and value.endswith('"'):
            metadata[key] = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            metadata[key] = value[1:-1]
        else:
            metadata[key] = value
    return metadata, errors


def _is_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True
