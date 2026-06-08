from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    content: str
    tags: tuple[str, ...]

    @property
    def citation(self) -> str:
        return f"{self.source}::{self.title}"


def load_markdown_knowledge_base(path: Path) -> list[KnowledgeChunk]:
    if not path.exists():
        return []

    chunks: list[KnowledgeChunk] = []
    for file_path in sorted(path.glob("*.md")):
        chunks.extend(_split_markdown_file(file_path))
    return chunks


def _split_markdown_file(file_path: Path) -> list[KnowledgeChunk]:
    lines = file_path.read_text(encoding="utf-8").splitlines()
    chunks: list[KnowledgeChunk] = []
    current_title = file_path.stem.replace("-", " ").title()
    current_lines: list[str] = []
    current_tags = _tags_from_filename(file_path)

    def flush() -> None:
        content = "\n".join(line.strip() for line in current_lines).strip()
        if content:
            chunks.append(
                KnowledgeChunk(
                    source=file_path.name,
                    title=current_title,
                    content=content,
                    tags=current_tags,
                )
            )

    for line in lines:
        if line.startswith("#"):
            flush()
            current_title = line.lstrip("#").strip() or current_title
            current_lines = []
            continue
        current_lines.append(line)

    flush()
    return chunks


def _tags_from_filename(file_path: Path) -> tuple[str, ...]:
    return tuple(part for part in file_path.stem.replace("_", "-").split("-") if part)
