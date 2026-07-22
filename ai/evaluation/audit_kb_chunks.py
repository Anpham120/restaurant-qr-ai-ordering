"""Audit knowledge-base chunk sizes and overlap for semantic chunking research."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AI_ROOT = PROJECT_ROOT / "ai"
sys.path.insert(0, str(AI_ROOT))

from app.rag.knowledge_base import load_markdown_knowledge_base  # noqa: E402


def audit_kb(*, kb_path: Path, max_chars: int = 1200) -> dict[str, object]:
    chunks = load_markdown_knowledge_base(kb_path)
    lengths = [len(chunk.content) for chunk in chunks]
    oversized = [
        {
            "source": chunk.source,
            "title": chunk.title,
            "chars": len(chunk.content),
        }
        for chunk in chunks
        if len(chunk.content) > max_chars
    ]
    by_source: dict[str, int] = {}
    for chunk in chunks:
        by_source[chunk.source] = by_source.get(chunk.source, 0) + 1
    return {
        "chunk_count": len(chunks),
        "source_count": len(by_source),
        "chars_mean": statistics.mean(lengths) if lengths else 0,
        "chars_p95": sorted(lengths)[int(len(lengths) * 0.95)] if lengths else 0,
        "max_chars_threshold": max_chars,
        "oversized_count": len(oversized),
        "oversized_samples": oversized[:20],
        "chunks_per_source": by_source,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kb-path",
        type=Path,
        default=AI_ROOT / "knowledge-base",
    )
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--output", type=Path, default=AI_ROOT / "evaluation" / "results" / "kb_chunk_audit.json")
    args = parser.parse_args()
    report = audit_kb(kb_path=args.kb_path, max_chars=args.max_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
