#!/usr/bin/env python3
"""Validate knowledge-base frontmatter and emit an index manifest.

Usage:
  PYTHONPATH=ai python ai/scripts/build_index.py
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import load_config  # noqa: E402
from app.rag.embedding_retriever import ENCODER_REGISTRY, resolve_encoder_key  # noqa: E402
from app.rag.knowledge_base import load_markdown_knowledge_base  # noqa: E402
from app.rag.knowledge_schema import validate_knowledge_base  # noqa: E402


def main() -> int:
    started = time.perf_counter()
    kb_path = ROOT / "knowledge-base"
    config = load_config()
    validations = validate_knowledge_base(kb_path)
    manifest = build_manifest(kb_path, config, validations)
    manifest["build_duration_ms"] = round((time.perf_counter() - started) * 1000, 1)
    errors = manifest["validation_errors"]

    out = ROOT / "evaluation" / "results" / "knowledge_manifest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep the artifact UTF-8, but make console output safe on Windows shells
    # whose stdout still uses CP1252.
    print(json.dumps(manifest, ensure_ascii=True, indent=2))
    return 1 if errors else 0


def build_manifest(kb_path: Path, config: object, validations: list[object]) -> dict:
    chunks = load_markdown_knowledge_base(kb_path)
    sources = {
        path.relative_to(kb_path).as_posix(): _sha256_file(path)
        for path in sorted(kb_path.glob("*.md"))
    }
    corpus_payload = {
        "sources": sources,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "section_path": list(chunk.section_path),
                "content_hash": chunk.content_hash,
                "tags": list(chunk.tags),
                "risk_tier": chunk.risk_tier,
                "valid_from": chunk.valid_from,
                "valid_to": chunk.valid_to,
            }
            for chunk in sorted(chunks, key=lambda item: item.chunk_id)
        ],
        "chunking": {
            "strategy": "markdown-heading",
            "version": "v2-stable-chunk-id",
            "hierarchy": "parent-child",
            "heading_pattern": "^#+\\s+",
            "stable_identity_fields": ["document_id", "section_path", "ordinal"],
        },
    }
    digest = hashlib.sha256(
        json.dumps(corpus_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    errors = [
        {"path": str(getattr(v, "path", "")), "errors": list(getattr(v, "errors", []) or [])}
        for v in validations
        if getattr(v, "errors", None)
    ]

    embedding_key = resolve_encoder_key(str(getattr(config, "embedding_model")))
    embedding_spec = ENCODER_REGISTRY[embedding_key]
    index_payload = {
        "corpus_sha256": digest,
        "retrieval_method": getattr(config, "retrieval_method"),
        "embedding_key": embedding_key,
        "embedding_model": embedding_spec.model_name,
        "embedding_revision": embedding_spec.model_revision,
        "rag_config_id": getattr(config, "rag_config_id"),
    }
    index_sha256 = hashlib.sha256(
        json.dumps(index_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = {
        "manifest_version": "knowledge-index-v2",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(list(kb_path.glob("*.md"))),
        "chunk_count": len(chunks),
        "corpus_sha256": digest,
        "index_sha256": index_sha256,
        "knowledge_source_sha256": sources,
        "chunking_config": corpus_payload["chunking"],
        "git_sha": _git_sha(),
        "retrieval_method": getattr(config, "retrieval_method"),
        "embedding_key": embedding_key,
        "embedding_model": embedding_spec.model_name,
        "embedding_model_revision": embedding_spec.model_revision,
        "rag_config_id": getattr(config, "rag_config_id"),
        "pipeline": getattr(config, "pipeline_version"),
        "seed": int(os.getenv("AI_EVAL_SEED", "20260713")),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "hardware": {
            "cpu_count": os.cpu_count(),
            "processor": platform.processor() or "unknown",
            "machine": platform.machine(),
        },
        "chunks": corpus_payload["chunks"],
        "validation_error_count": len(errors),
        "validation_errors": errors[:50],
    }
    return manifest

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str:
    configured = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
    if configured:
        return configured
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT.parent,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
