"""Fail closed when runtime configuration drifts from the research winner."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from app.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_RATE_LIMIT_FALLBACK_MODEL,
    PIPELINE_PROFILES,
)
from evaluation.pipeline_selection import passes_safety_gate
from evaluation.research_inputs import compute_research_input_hash

DEEPSEEK_MODEL = DEFAULT_LLM_MODEL
FALLBACK_MODEL = DEFAULT_RATE_LIMIT_FALLBACK_MODEL
PROFILE_ORDER = tuple(sorted(PIPELINE_PROFILES))
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def validate_artifact(
    artifact: dict[str, Any],
    *,
    expected_profile: str | None = None,
    expected_primary_model: str = DEEPSEEK_MODEL,
    expected_fallback_model: str = FALLBACK_MODEL,
    expected_fallback_trigger: str = "http_429",
    expected_max_fallbacks: int = 1,
    require_fallback_enabled: bool = False,
    expected_research_input_hash: str | None = None,
) -> str:
    if artifact.get("schema_version") != "pipeline-selection-v3":
        raise ValueError("unsupported pipeline selection artifact schema")
    if artifact.get("model") != expected_primary_model:
        raise ValueError(
            f"primary model drift: artifact={artifact.get('model')!r}, expected={expected_primary_model!r}"
        )
    model_policy = dict(artifact.get("model_policy") or {})
    if model_policy.get("primary_model") != expected_primary_model:
        raise ValueError(
            "primary model drift: "
            f"artifact={model_policy.get('primary_model')!r}, "
            f"expected={expected_primary_model!r}"
        )
    if model_policy.get("fallback_model") != expected_fallback_model:
        raise ValueError(
            "fallback model drift: "
            f"artifact={model_policy.get('fallback_model')!r}, "
            f"expected={expected_fallback_model!r}"
        )
    if model_policy.get("fallback_trigger") != expected_fallback_trigger:
        raise ValueError(
            "fallback trigger drift: "
            f"artifact={model_policy.get('fallback_trigger')!r}, "
            f"expected={expected_fallback_trigger!r}"
        )
    if int(model_policy.get("max_fallbacks_per_operation") or 0) != int(
        expected_max_fallbacks
    ):
        raise ValueError(
            "max fallback drift: "
            f"artifact={model_policy.get('max_fallbacks_per_operation')!r}, "
            f"expected={expected_max_fallbacks!r}"
        )
    if require_fallback_enabled and not bool(model_policy.get("fallback_enabled")):
        raise ValueError("fallback must be enabled for this deployment")
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
    parser.add_argument("--expected-primary-model", default=DEEPSEEK_MODEL)
    parser.add_argument("--expected-fallback-model", default=FALLBACK_MODEL)
    parser.add_argument("--expected-fallback-trigger", default="http_429")
    parser.add_argument("--expected-max-fallbacks", type=int, default=1)
    parser.add_argument("--require-fallback-enabled", action="store_true")
    parser.add_argument("--expected-research-input-hash")
    parser.add_argument("--verify-current-research-inputs", action="store_true")
    parser.add_argument("--repository-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--github-env", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    model_policy = dict(artifact.get("model_policy") or {})
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
        expected_primary_model=args.expected_primary_model,
        expected_fallback_model=args.expected_fallback_model,
        expected_fallback_trigger=args.expected_fallback_trigger,
        expected_max_fallbacks=args.expected_max_fallbacks,
        require_fallback_enabled=args.require_fallback_enabled,
        expected_research_input_hash=expected_research_input_hash,
    )
    if args.github_env:
        with args.github_env.open("a", encoding="utf-8") as handle:
            handle.write(f"AI_PIPELINE_PROFILE={winner}\n")
            handle.write(f"LLM_MODEL={args.expected_primary_model}\n")
            handle.write(f"LLM_RATE_LIMIT_FALLBACK_MODEL={args.expected_fallback_model}\n")
            handle.write(
                "LLM_RATE_LIMIT_FALLBACK_ENABLED="
                f"{str(bool(model_policy.get('fallback_enabled'))).lower()}\n"
            )
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
