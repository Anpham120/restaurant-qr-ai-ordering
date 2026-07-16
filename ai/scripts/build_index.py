#!/usr/bin/env python3
"""Validate knowledge-base frontmatter and emit an index manifest.

Usage:
  PYTHONPATH=ai python ai/scripts/build_index.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.rag.knowledge_base import load_markdown_knowledge_base  # noqa: E402
from app.rag.knowledge_schema import validate_knowledge_base  # noqa: E402


def main() -> int:
    kb_path = ROOT / "knowledge-base"
    validations = validate_knowledge_base(kb_path)
    chunks = load_markdown_knowledge_base(kb_path)
    corpus = "\n".join(sorted(p.name for p in kb_path.glob("*.md")))
    digest = hashlib.sha256(corpus.encode("utf-8")).hexdigest()
    errors = [
        {"path": str(getattr(v, "path", "")), "errors": list(getattr(v, "errors", []) or [])}
        for v in validations
        if getattr(v, "errors", None)
    ]

    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(list(kb_path.glob("*.md"))),
        "chunk_count": len(chunks),
        "corpus_sha256": digest,
        "validation_error_count": len(errors),
        "validation_errors": errors[:50],
    }

    out = ROOT / "evaluation" / "results" / "knowledge_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
