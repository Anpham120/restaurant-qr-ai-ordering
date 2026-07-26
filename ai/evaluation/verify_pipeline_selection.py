"""Fail closed when runtime configuration drifts from the research winner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from app.config import DEFAULT_LLM_MODEL, PIPELINE_PROFILES
from evaluation.pipeline_selection import passes_safety_gate
from evaluation.research_inputs import compute_research_input_hash

DEEPSEEK_MODEL = DEFAULT_LLM_MODEL
PROFILE_ORDER = tuple(sorted(PIPELINE_PROFILES))


def validate_artifact(
    artifact: dict[str, Any],
    *,
    expected_profile: str | None = None,
    expected_model: str = DEEPSEEK_MODEL,
    expected_research_input_hash: str | None = None,
) -> str:
    if artifact.get("schema_version") != "pipeline-selection-approved-v2":
        raise ValueError("unsupported pipeline selection artifact schema")
    if artifact.get("model") != expected_model:
        raise ValueError(
            f"model drift: artifact={artifact.get('model')!r}, expected={expected_model!r}"
        )
    if artifact.get("working_tree_dirty") is True:
        raise ValueError("dirty source tree cannot be deployed from a selection artifact")
    winner = str(artifact.get("winner") or "")
    if winner not in PROFILE_ORDER:
        raise ValueError("pipeline selection artifact has no valid winner")
    candidates = {
        str(item.get("profile") or ""): item
        for item in artifact.get("profiles") or []
    }
    candidate = candidates.get(winner)
    if candidate is None or not passes_safety_gate(candidate):
        raise ValueError(f"winner {winner!r} does not pass the safety hard gate")
    if expected_profile and winner != expected_profile:
        raise ValueError(
            f"pipeline profile drift: artifact winner={winner!r}, runtime={expected_profile!r}"
        )
    research_input_hash = str(artifact.get("research_input_hash") or "")
    if not research_input_hash.startswith("sha256:"):
        raise ValueError("pipeline selection artifact is missing research input hash")
    if (
        expected_research_input_hash
        and research_input_hash != expected_research_input_hash
    ):
        raise ValueError(
            "research input drift: "
            f"artifact={research_input_hash!r}, runtime={expected_research_input_hash!r}"
        )
    if not str(artifact.get("research_commit_sha") or ""):
        raise ValueError("pipeline selection artifact is missing research commit")
    if not str(artifact.get("dataset_hash") or "").startswith("sha256:"):
        raise ValueError("pipeline selection artifact is missing dataset hash")
    if not artifact.get("generated_at"):
        raise ValueError("pipeline selection artifact is missing generated_at")
    if not int(artifact.get("source_run_id") or 0):
        raise ValueError("pipeline selection artifact is missing source run")
    if not str(artifact.get("source_artifact_sha256") or "").startswith("sha256:"):
        raise ValueError("pipeline selection artifact is missing source artifact hash")
    return winner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--expected-profile", default=os.getenv("AI_PIPELINE_PROFILE"))
    parser.add_argument("--expected-model", default=DEEPSEEK_MODEL)
    parser.add_argument("--expected-research-input-hash")
    parser.add_argument("--verify-current-research-inputs", action="store_true")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--github-env", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    expected_research_input_hash = args.expected_research_input_hash
    if args.verify_current_research_inputs:
        current_hash = compute_research_input_hash(args.repository_root.resolve())
        if expected_research_input_hash and expected_research_input_hash != current_hash:
            raise ValueError(
                "explicit research input hash does not match the current checkout"
            )
        expected_research_input_hash = current_hash
    winner = validate_artifact(
        artifact,
        expected_profile=args.expected_profile,
        expected_model=args.expected_model,
        expected_research_input_hash=expected_research_input_hash,
    )
    if args.github_env:
        with args.github_env.open("a", encoding="utf-8") as handle:
            handle.write(f"AI_PIPELINE_PROFILE={winner}\n")
            handle.write(f"LLM_MODEL={DEEPSEEK_MODEL}\n")
            handle.write(f"PIPELINE_SELECTION_ARTIFACT={args.artifact}\n")
            handle.write(
                f"PIPELINE_RESEARCH_INPUT_HASH={artifact['research_input_hash']}\n"
            )
            handle.write(
                f"PIPELINE_RESEARCH_COMMIT={artifact['research_commit_sha']}\n"
            )
    print(f"validated pipeline winner: {winner}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
