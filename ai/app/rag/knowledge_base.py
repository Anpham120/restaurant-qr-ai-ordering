from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.rag.knowledge_schema import parse_frontmatter


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    content: str
    tags: tuple[str, ...]
    chunk_id: str = ""
    document_id: str = ""
    parent_id: str | None = None
    section_path: tuple[str, ...] = ()
    content_hash: str = ""
    risk_tier: str = "standard"
    valid_from: str | None = None
    valid_to: str | None = None

    def __post_init__(self) -> None:
        content_hash = self.content_hash or _content_hash(self.content)
        document_id = self.document_id or self.source
        section_path = self.section_path or (self.title,)
        chunk_id = self.chunk_id or stable_chunk_id(
            document_id=document_id,
            section_path=section_path,
            content_hash=content_hash,
        )
        object.__setattr__(self, "content_hash", content_hash)
        object.__setattr__(self, "document_id", document_id)
        object.__setattr__(self, "section_path", section_path)
        object.__setattr__(self, "chunk_id", chunk_id)

    @property
    def citation(self) -> str:
        return f"{self.chunk_id}::{self.title}"

    @property
    def is_current(self) -> bool:
        now = datetime.now(timezone.utc)
        return _is_not_before(self.valid_from, now) and _is_not_after(self.valid_to, now)


def load_markdown_knowledge_base(path: Path) -> list[KnowledgeChunk]:
    if not path.exists():
        return []

    chunks: list[KnowledgeChunk] = []
    for file_path in sorted(path.glob("*.md")):
        chunks.extend(_split_markdown_file(file_path))
    return chunks


def _split_markdown_file(file_path: Path) -> list[KnowledgeChunk]:
    raw_text = file_path.read_text(encoding="utf-8")
    metadata, _ = parse_frontmatter(raw_text)
    raw_text = _strip_yaml_frontmatter(raw_text)
    lines = raw_text.splitlines()
    chunks: list[KnowledgeChunk] = []
    current_title = file_path.stem.replace("-", " ").title()
    current_path: list[str] = [current_title]
    current_lines: list[str] = []
    current_tags = tuple(str(tag) for tag in metadata.get("tags", [])) or _tags_from_filename(file_path)
    document_id = str(metadata.get("id") or file_path.name)
    risk_tier = str(metadata.get("safety_level") or "standard").casefold()
    valid_from = str(metadata.get("reviewed_at") or "") or None
    valid_to = str(metadata.get("expires_at") or "") or None
    path_occurrences: dict[tuple[str, ...], int] = {}
    chunk_ids_by_path: dict[tuple[str, ...], str] = {}

    def flush() -> None:
        content = "\n".join(line.strip() for line in current_lines).strip()
        if content:
            content_hash = _content_hash(content)
            resolved_path = tuple(current_path)
            occurrence = path_occurrences.get(resolved_path, 0) + 1
            path_occurrences[resolved_path] = occurrence
            chunk_id = stable_chunk_id(
                document_id=document_id,
                section_path=resolved_path,
                content_hash=content_hash,
                ordinal=occurrence,
            )
            chunks.append(
                KnowledgeChunk(
                    source=file_path.name,
                    title=current_title,
                    content=content,
                    tags=current_tags,
                    chunk_id=chunk_id,
                    document_id=document_id,
                    parent_id=chunk_ids_by_path.get(resolved_path[:-1]),
                    section_path=resolved_path,
                    content_hash=content_hash,
                    risk_tier=risk_tier,
                    valid_from=valid_from,
                    valid_to=valid_to,
                )
            )
            chunk_ids_by_path[resolved_path] = chunk_id

    for line in lines:
        if line.startswith("#"):
            flush()
            level = len(line) - len(line.lstrip("#"))
            heading = line.lstrip("#").strip() or current_title
            current_path = current_path[: max(level - 1, 0)]
            current_path.append(heading)
            current_title = heading
            current_lines = []
            continue
        current_lines.append(line)

    flush()
    return chunks


def _tags_from_filename(file_path: Path) -> tuple[str, ...]:
    return tuple(part for part in file_path.stem.replace("_", "-").split("-") if part)


def _strip_yaml_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :].lstrip("\n")


def stable_chunk_id(
    *,
    document_id: str,
    section_path: tuple[str, ...],
    content_hash: str,
    ordinal: int | None = None,
) -> str:
    section_slug = "-".join(_slug(part) for part in section_path if part.strip())
    section_slug = section_slug or "root"
    # Identity and content version are deliberately separate: editing text must
    # invalidate content_hash/index versions without changing external chunk IDs.
    suffix_source = f"{document_id}|{'/'.join(section_path)}|{ordinal or 1}"
    suffix = hashlib.sha256(suffix_source.encode("utf-8")).hexdigest()[:10]
    return f"kb:{document_id}:{section_slug}:{suffix}"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value.casefold()).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return normalized[:64] or "section"


def _is_not_before(value: str | None, now: datetime) -> bool:
    if not value:
        return True
    parsed = _parse_datetime(value)
    return parsed is None or parsed <= now


def _is_not_after(value: str | None, now: datetime) -> bool:
    if not value:
        return True
    parsed = _parse_datetime(value)
    return parsed is None or parsed >= now


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
