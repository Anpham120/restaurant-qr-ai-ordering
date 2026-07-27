"""Promote a clean raw pipeline-selection artifact into the deploy-approved form."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_raw_artifact(raw: dict[str, Any]) -> None:
    if raw.get("schema_version") != "pipeline-selection-v3":
        raise ValueError("raw artifact must use pipeline-selection-v3")
    if raw.get("working_tree_dirty") is True:
        raise ValueError("raw artifact must come from a clean source tree")
    if not raw.get("winner"):
        raise ValueError("raw artifact must contain a winner before approval")
    if not str(raw.get("research_commit_sha") or raw.get("commit_sha") or ""):
        raise ValueError("raw artifact is missing research commit")
    if not str(raw.get("research_input_hash") or "").startswith("sha256:"):
        raise ValueError("raw artifact is missing research input hash")
    if not str(raw.get("dataset_hash") or "").startswith("sha256:"):
        raise ValueError("raw artifact is missing dataset hash")
    if not raw.get("generated_at"):
        raise ValueError("raw artifact is missing generated_at")


def build_approved_artifact(
    raw: dict[str, Any],
    *,
    source_artifact_path: Path,
    source_run_id: int,
    source_artifact_name: str,
    approved_at: str | None = None,
) -> dict[str, Any]:
    _validate_raw_artifact(raw)
    approved = dict(raw)
    approved["profiles"] = [
        {
            "profile": str(item.get("profile") or ""),
            "metrics": dict(item.get("metrics") or {}),
        }
        for item in raw.get("profiles") or []
    ]
    approved["research_commit_sha"] = str(
        raw.get("research_commit_sha") or raw.get("commit_sha")
    )
    approved["approved_at"] = approved_at or datetime.now(timezone.utc).isoformat()
    approved["source_run_id"] = int(source_run_id)
    approved["source_artifact_name"] = source_artifact_name
    approved["source_artifact_sha256"] = _sha256(source_artifact_path)
    return approved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_artifact", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "approved" / "pipeline_selection.json",
    )
    parser.add_argument("--source-run-id", type=int, default=int(time.time()))
    parser.add_argument("--source-artifact-name")
    parser.add_argument("--approved-at")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw = _load_json(args.raw_artifact)
    source_artifact_name = args.source_artifact_name or args.raw_artifact.name
    approved = build_approved_artifact(
        raw,
        source_artifact_path=args.raw_artifact,
        source_run_id=args.source_run_id,
        source_artifact_name=source_artifact_name,
        approved_at=args.approved_at,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(approved, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "winner": approved["winner"],
                "output": str(args.output),
                "source_artifact_sha256": approved["source_artifact_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
